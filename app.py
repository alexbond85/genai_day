import chainlit as cl
from toolbox.bq_service import BigQueryService
import re # Add import for regex


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
    response = ""
    user_message = message.content.strip()

    # Initialize the BigQuery service (consider initializing once per session if needed)
    bq_service = BigQueryService()

    # Handle table description request
    if user_message.lower().startswith("describe "):
        # Extract table identifier (handle potential extra spaces)
        match = re.match(r"describe\s+(.+)", user_message, re.IGNORECASE)
        if match:
            table_identifier = match.group(1).strip()
            if not table_identifier:
                 response = "Please provide a table identifier after 'describe '."
            else:
                cl.Message(content=f"Fetching details for `{table_identifier}`...").send() # Inform user
                details = bq_service.describe_table(table_identifier)

                if "error" in details:
                    response = f"Error describing table `{table_identifier}`: {details['error']}"
                else:
                    schema = details.get("schema", [])
                    full_table_id = details.get("full_table_id", table_identifier)
                    partitioning = details.get("partitioning")
                    clustering = details.get("clustering_fields")

                    response = f"**Details for `{full_table_id}`:**\n\n"

                    # Partitioning Info
                    if partitioning:
                        part_type = partitioning.get('type')
                        part_field = partitioning.get('field')
                        part_details = partitioning.get('partitioning_type', '') # e.g., DAY for time partitioning
                        response += f"**Partitioning:**\n"
                        response += f"- Type: `{part_type}`\n"
                        response += f"- Field: `{part_field}`\n"
                        if part_details:
                            response += f"- Granularity: `{part_details}`\n"
                        response += "\n"
                    else:
                        response += "**Partitioning:** None\n\n"

                    # Clustering Info
                    if clustering:
                        response += f"**Clustering Fields:**\n- `{'`, `'.join(clustering)}`\n\n"
                    else:
                        response += "**Clustering Fields:** None\n\n"

                    # Schema Info
                    response += "**Schema:**\n"
                    if schema:
                        for field in schema:
                            description = f" (Description: *{field.get('description')}*)" if field.get('description') else ""
                            response += f"- `{field.get('name')}`: `{field.get('type')}` ({field.get('mode')}){description}\n"
                    else:
                        response += "*No schema information found.*\n"

                    # Example Query (if partitioned)
                    if partitioning and partitioning.get("type") == "TIME":
                        part_field = partitioning.get("field")
                        # Construct a basic example query predicate
                        example_predicate = f"WHERE DATE({part_field}) = CURRENT_DATE() - INTERVAL 1 DAY" # Example: yesterday
                        response += f"\n**Example Query Predicate (using partition):**\n```sql\nSELECT * \nFROM `{full_table_id}` \n{example_predicate}\nLIMIT 10;\n```"
                    elif partitioning and partitioning.get("type") == "RANGE":
                         part_field = partitioning.get("field")
                         # Cannot provide a generic range predicate easily without knowing range details
                         response += f"\n**Note:** Table is range-partitioned on `{part_field}`. Filter on this field for better performance."

        else:
             # Should not happen if starts with "describe " but handle defensively
             response = "Invalid 'describe' command format. Use `describe <table_identifier>`."

    # Keep the old specific command handler if needed, or remove if 'describe' covers it
    # Let's make the old command use the new describe logic
    elif user_message == "dq_lineage_exp":
        table_identifier = "dq_lineage_exp" # Hardcoded table for this specific command
        await cl.Message(content=f"Fetching details for `{table_identifier}`...").send()
        details = bq_service.describe_table(table_identifier)
        # (Replicate the formatting logic from the 'describe' block above)
        if "error" in details:
            response = f"Error describing table `{table_identifier}`: {details['error']}"
        else:
            # ... [Copy/paste or refactor the formatting logic here] ...
            # For brevity, let's just provide a simpler message for this specific case for now
            response = f"Use `describe {table_identifier}` for detailed info. Found details for `{details.get('full_table_id', table_identifier)}`."

    else:
        # Default response: echo the message
        response = f"You said: {user_message}"

    # Send the response back to the user
    await cl.Message(content=response).send() 