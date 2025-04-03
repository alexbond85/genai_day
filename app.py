import chainlit as cl


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
    It sends a welcome message to the user.
    """
    # Set up the avatars for the user and the assistant - Removing calls again
    # await Avatar(
    #     name="Assistant", 
    #     path="/assistant.png", # Try path relative to web root
    # ).send()
    # await Avatar(
    #     name="User", 
    #     path="/user.png", # Try path relative to web root
    # ).send()
    
    await cl.Message(
        content="👋 Hello! I'm your AI assistant. How can I help you today?"
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