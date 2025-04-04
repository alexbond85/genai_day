import chainlit as cl
from toolbox.bq_service import BigQueryService


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
    ).send()

@cl.on_message
async def main(message: cl.Message):
    """
    This function is called every time a user sends a message.
    Args:
        message: The message sent by the user.
    """
    # Process the message and send a response
    # Remove the fox emoji prefix
    response = message.content
    
    # Send the response back to the user
    await cl.Message(content=response).send() 