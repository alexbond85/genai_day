import chainlit as cl
from toolbox.bq_service import BigQueryService, TableDescription, TableError # Update imports (PartitioningInfo, SchemaField no longer needed here)
import re # Add import for regex
import json # Add import for json formatting
import pandas as pd # Add pandas import


@cl.set_chat_profiles
async def chat_profile():
    return [
        cl.ChatProfile(
            name="Assistant",
            markdown_description="Votre assistant virtuel.",
            icon="./public/avatars/assistant.png",
        )
    ]

@cl.on_chat_start
async def start():
    """
    This function is called when a new chat session starts.
    It sends a welcome message including the list of accessible BigQuery tables.
    """
    # Initialize the BigQuery service
    bq_service = BigQueryService()
    
    # Get the list of accessible tables
    accessible_tables = bq_service.list_accessible_tables()
    
    # Format the list for display
    if accessible_tables:
        if accessible_tables[0].startswith("Error") or accessible_tables[0] == "No accessible tables found.":
            tables_list_str = f"\n*Note: {accessible_tables[0]}*"
        else:
            tables_list_str = "\n\nHere are the accessible BigQuery tables:\n" + "\n".join([f"- `{table}`" for table in accessible_tables])
    else:
        # Should not happen based on current bq_service logic, but handle defensively
        tables_list_str = "\n*Could not retrieve table list.*"

    await cl.Message(
        content=f"👋 Hello! I'm your AI assistant. How can I help you today?{tables_list_str}"
        + "\n\nTo get details about a specific table (schema, partitioning), type `describe <table_identifier>` (e.g., `describe my_dataset.my_table`)."
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """
    This function is called every time a user sends a message.
    Handles requests for table descriptions and other commands.
    Args:
        message: The message sent by the user.
    """
    user_message = message.content.strip()
    bq_service = BigQueryService()
    
    # Determine which table to describe or query to execute
    table_identifier = None
    query_to_execute = None
    response = None # Initialize response
    
    if user_message.lower().startswith("describe "):
        match = re.match(r"describe\s+(.+)", user_message, re.IGNORECASE)
        if match:
            table_identifier = match.group(1).strip()
            if not table_identifier:
                response = "Please provide a table identifier after 'describe '."
            # No else needed, table_identifier will be processed below if valid
        else:
            response = "Invalid 'describe' command format. Use `describe <table_identifier>`."
            
    elif user_message.lower().startswith("execute bq "):
        # Extract query after "execute bq "
        query_to_execute = user_message[len("execute bq "):].strip()
        if not query_to_execute:
            response = "Please provide a BigQuery SQL query after 'execute bq '."
        # No else needed, query_to_execute will be processed below if valid

    elif user_message == "dq_lineage_exp":
        table_identifier = "dq_lineage_exp"  # Hardcoded table
    
    # Process table description request if we have a table identifier AND no response yet
    if table_identifier and response is None:
        await cl.Message(content=f"Fetching details for `{table_identifier}`...").send()
        details = bq_service.describe_table(table_identifier)
        
        # Convert the result to string representation
        if isinstance(details, (TableDescription, TableError)):
            response = details.to_str()
        else:
            response = f"Received unexpected result type when describing `{table_identifier}`."
            
    # Process query execution request if we have a query AND no response yet
    elif query_to_execute and response is None:
        await cl.Message(content=f"Executing BigQuery query...").send()
        results = bq_service.execute_query(query_to_execute)
        
        # Default content message
        content_msg = "Query executed successfully."
        elements = [] # Initialize elements list

        if isinstance(results, str): # It's an error message
            response = f"Error executing query:\n```\n{results}\n```"
        elif isinstance(results, pd.DataFrame):
            if not results.empty:
                 # Create a Dataframe element
                 elements = [cl.Dataframe(data=results, display="inline", name="Query Results")]
                 content_msg = f"Query returned {len(results)} rows:"
                 response = None # Clear response to use elements
            else:
                 response = "Query executed successfully, but returned no results."
        else:
            response = "Received an unexpected result type from query execution."
            
        # Send message with elements if a dataframe was generated, otherwise send text response
        if elements:
             await cl.Message(content=content_msg, elements=elements).send()
             return # Exit after sending the dataframe message
        # else: response variable holds the text message (error or no results)

    # Default response if no command was processed and no error message was set
    elif response is None:
        response = f"Unknown command. Try `describe <table_id>` or `execute bq <query>`."

    # Send the response back to the user (only if it's a string response)
    if response:
        await cl.Message(content=response).send() 