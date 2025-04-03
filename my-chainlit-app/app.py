import chainlit as cl

@cl.on_chat_start
async def start():
    """
    This function is called when a new chat session starts.
    It sends a welcome message to the user.
    """
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
    response = f"You said: {message.content}"
    
    # Send the response back to the user
    await cl.Message(content=response).send() 