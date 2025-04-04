import chainlit as cl
import os
# Re-add vertexai import as it's needed for initialization
import vertexai
# Remove direct vertexai SDK imports if no longer needed elsewhere
# from vertexai.generative_models import GenerativeModel, ChatSession, Part, FinishReason
import logging
from typing import TypedDict, Annotated, Sequence, Literal
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
# --- Add Tool import ---
from langchain_core.tools import Tool
# --- Switch to StructuredTool --- 
from langchain_core.tools import StructuredTool
# --- Remove Pydantic import for schema (no longer needed for this tool) --- 
# from pydantic import BaseModel 
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import StateGraph, END
# --- Correct ToolExecutor/ToolNode import ---
from langgraph.prebuilt import ToolNode # Import ToolNode instead
from langgraph.checkpoint.memory import MemorySaver # For potential state management later

# --- Import BigQueryService ---
from toolbox.bq_service import BigQueryService, TableDescription, TableError # Import necessary types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Attempt to get project and location from environment variables
# Fallback to defaults if not set (update defaults if needed)
DEFAULT_PROJECT_ID = "sandbox-shippeo-hackathon-cc0a"
DEFAULT_LOCATION = "europe-west1" # Belgium region
MODEL_NAME = "gemini-2.0-flash" # Or choose another Gemini model

try:
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
    LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")

    if not PROJECT_ID:
        logger.warning(f"GOOGLE_CLOUD_PROJECT env var not set. Falling back to default: {DEFAULT_PROJECT_ID}")
        PROJECT_ID = DEFAULT_PROJECT_ID
    if not LOCATION:
        logger.warning(f"GOOGLE_CLOUD_LOCATION env var not set. Falling back to default: {DEFAULT_LOCATION}")
        LOCATION = DEFAULT_LOCATION

    # Initialize Vertex AI SDK (Keep this for ChatVertexAI initialization)
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    logger.info(f"Vertex AI initialized for project '{PROJECT_ID}' in location '{LOCATION}'")

except Exception as e:
    logger.error(f"Error initializing Vertex AI: {e}", exc_info=True)
    # Handle critical initialization failure (e.g., exit or disable functionality)
    # For Chainlit, we might send an error message on chat start instead of exiting


# --- Initialize BigQuery Service ---
bq_service = BigQueryService()

# --- Define a wrapper function for the tool --- 
def run_list_tables():
    """Wrapper function to call the BigQueryService method."""
    logger.info("DEBUG APP: run_list_tables() called by ToolNode.") # Add log here
    try:
        result = bq_service.list_accessible_tables()
        logger.info(f"DEBUG APP: bq_service.list_accessible_tables() returned: {result}") # Add log here
        return result
    except Exception as e:
        logger.error(f"DEBUG APP: Error calling bq_service.list_accessible_tables: {e}", exc_info=True)
        return f"Error executing list_tables: {e}"

# --- Define LangChain Tools ---
# Wrap BQ methods in LangChain Tools
# Ensure docstrings are informative as the LLM uses them!

# --- Use StructuredTool for list_tables_tool --- 
list_tables_tool = StructuredTool.from_function(
    func=run_list_tables,
    name="list_bigquery_tables",
    description="Lists all available BigQuery tables. Takes no arguments.",
    # args_schema is inferred from function signature (no args)
)

describe_table_tool = Tool(
    name="describe_bigquery_table",
    description="Gets schema, partitioning, and clustering details for a specific BigQuery table. Input doesn't need to be the full table identifier, just the table name.",
    func=lambda table_id: bq_service.describe_table(table_id).to_str(), # Use lambda to call to_str()
)

execute_query_tool = Tool(
    name="execute_bigquery_query",
    description="Executes a BigQuery SQL query and returns the results as a string representation of a pandas DataFrame, or an error message. Use this for data retrieval or exploration. Ensure the query is valid SQL.",
    func=lambda query: str(bq_service.execute_query(query)), # Convert DataFrame/error to string
)

# --- Tool Executor ---
tools = [list_tables_tool, describe_table_tool, execute_query_tool]
# tool_executor = ToolExecutor(tools) # No longer need separate executor instance


# --- Langgraph State Definition ---
class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


# --- Langgraph Nodes ---

def call_model(state: State):
    """Invokes the LLM with the current conversation state and tools."""
    messages = state['messages']
    llm = cl.user_session.get("llm_with_tools") # Get the LLM with tools bound
    if not llm:
        logger.error("LLM with tools not found in user session during call_model.")
        error_message = AIMessage(content="Error: LLM not properly initialized with tools.")
        return {"messages": [error_message]}

    # --- Log Input --- 
    logger.info("--- LLM Input ---")
    for msg in messages:
        logger.info(f"Type: {type(msg).__name__}, Content: {msg.content}, Tool Calls: {getattr(msg, 'tool_calls', 'N/A')}")
    logger.info("-----------------")
    # logger.info(f"Calling model with {len(messages)} messages.") # Redundant with loop above

    # The LLM decides whether to respond directly or use a tool
    response = llm.invoke(messages)

    # --- Log Output --- 
    logger.info("--- LLM Output ---")
    logger.info(f"Type: {type(response).__name__}, Content: {response.content}, Tool Calls: {getattr(response, 'tool_calls', 'N/A')}")
    # Attempt to log token usage
    if hasattr(response, 'response_metadata') and 'token_usage' in response.response_metadata:
        token_usage = response.response_metadata['token_usage']
        logger.info(f"Token Usage: {token_usage}")
    else:
        logger.info("Token Usage: Not available in response_metadata.")
    logger.info("------------------")
    # logger.info(f"Model response received: {type(response)}") # Redundant

    # Append the response (AIMessage or AIMessageChunk with tool_calls) to the state
    return {"messages": [response]}


# --- Langgraph Conditional Edge ---

def should_continue(state: State) -> Literal["tools", "__end__"]:
    """Determines the next step: call tools or end the conversation turn."""
    last_message = state['messages'][-1]
    # If the LLM made tool calls, route to the tool node
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        logger.info("Routing to tools.")
        return "tools"
    # Otherwise, respond to the user and end the turn
    logger.info("Routing to end.")
    return "__end__"


# --- Build the Graph ---

# Define the workflow
workflow = StateGraph(State)

# Add nodes
workflow.add_node("llm", call_model)
# --- Use ToolNode --- 
workflow.add_node("tools", ToolNode(tools)) # Use ToolNode directly

# Set entry point
workflow.set_entry_point("llm")

# Add conditional edges
workflow.add_conditional_edges(
    "llm",  # Source node
    should_continue,  # Function to decide the next node
    {
        "tools": "tools",  # If should_continue returns "tools", go to "tools" node
        "__end__": END,    # If should_continue returns "__end__", finish the graph execution
    },
)

# Add edge from tool node back to LLM
workflow.add_edge("tools", "llm")

# Compile the graph (moved to on_chat_start to bind LLM correctly)


@cl.on_chat_start
async def start_chat():
    """Initializes the Langgraph workflow, LLM with tools, and BQ Service."""
    logger.info("Chat started. Initializing Langgraph workflow, LLM with tools, and BQ Service.")
    try:
        if not PROJECT_ID or not LOCATION:
             await cl.Message(content="Error: Vertex AI Project ID or Location not configured.").send()
             return

        # Initialize the Langchain Chat Model
        llm = ChatVertexAI(model_name=MODEL_NAME, project=PROJECT_ID, location=LOCATION, streaming=False)
        # Bind the tools to the LLM
        llm_with_tools = llm.bind_tools(tools)
        cl.user_session.set("llm_with_tools", llm_with_tools) # Store the LLM with tools bound
        logger.info(f"ChatVertexAI model initialized ({MODEL_NAME}) and tools bound.")

        # Compile the graph
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        cl.user_session.set("app", app)
        logger.info("Langgraph workflow compiled with tool integration.")

        await cl.Message(
            content=f"Hello! I'm powered by Gemini (`{MODEL_NAME}`) with BigQuery tools via Langgraph. Ask me about your data!"
        ).send()

    except Exception as e:
        logger.error(f"Error starting chat session: {e}", exc_info=True)
        await cl.Message(
            content=f"Sorry, I couldn't initialize the chat session. Error: {e}"
        ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handles incoming user messages using the Langgraph tool-enabled workflow."""
    app = cl.user_session.get("app")

    if not app:
        logger.warning("Langgraph app not found in user session.")
        await cl.Message(
            content="It seems the chat session wasn't initialized correctly. Please try refreshing or restarting the chat."
        ).send()
        return

    user_message_content = message.content
    logger.info(f"Received message: {user_message_content}")

    # Use a unique thread_id per session if desired, or keep it simple
    # Consider using cl.user_session.id or similar for multi-user scenarios
    # thread_id = "main_thread_" + cl.user_session.id # Example: unique ID per session - Incorrect
    thread_id = "main_chat_thread" # Use a consistent ID; MemorySaver handles isolation
    config = {"configurable": {"thread_id": thread_id}}

    inputs = {"messages": [HumanMessage(content=user_message_content)]}

    response_message = cl.Message(content="") # Start with empty UI message
    await response_message.send()

    try:
        logger.info(f"Invoking Langgraph app for thread: {thread_id}...")
        # Use ainvoke for the final result after potential tool calls
        final_state = await app.ainvoke(inputs, config=config)

        # The final response from the LLM is the last message in the state
        ai_response = final_state['messages'][-1]

        # Ensure we're sending the actual content string
        if isinstance(ai_response, AIMessage):
            response_content = ai_response.content
        else:
            # Handle cases where the last message might be unexpected (e.g., ToolMessage)
            logger.warning(f"Unexpected last message type: {type(ai_response)}. Displaying full state.")
            response_content = f"Debug: Final state ended unexpectedly. Last message: {ai_response}"


        logger.info("Langgraph app invocation complete.")
        response_message.content = response_content
        await response_message.update()

    except Exception as e:
        logger.error(f"Error invoking Langgraph app: {e}", exc_info=True)
        response_message.content = f"Sorry, an error occurred while processing your message: {e}"
        await response_message.update()