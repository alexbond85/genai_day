import chainlit as cl
import os
from vertexai.generative_models import GenerativeModel, ChatSession, Part, FinishReason
import vertexai
import logging

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

    # Initialize Vertex AI SDK
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    logger.info(f"Vertex AI initialized for project '{PROJECT_ID}' in location '{LOCATION}'")

except Exception as e:
    logger.error(f"Error initializing Vertex AI: {e}", exc_info=True)
    # Handle critical initialization failure (e.g., exit or disable functionality)
    # For Chainlit, we might send an error message on chat start instead of exiting


@cl.on_chat_start
async def start_chat():
    """Initializes the chat session with the Gemini model."""
    logger.info("Chat started. Initializing Gemini chat session.")
    try:
        # Ensure Vertex AI is initialized before proceeding
        if not PROJECT_ID or not LOCATION:
             await cl.Message(content="Error: Vertex AI Project ID or Location not configured.").send()
             return

        model = GenerativeModel(MODEL_NAME)
        # Start a new chat session. The SDK's ChatSession object manages history.
        chat = model.start_chat()
        cl.user_session.set("chat_session", chat)
        logger.info(f"Gemini chat session started with model: {MODEL_NAME}")

        await cl.Message(
            content=f"Hello! I'm powered by Gemini (`{MODEL_NAME}`). How can I assist you today?"
        ).send()

    except Exception as e:
        logger.error(f"Error starting chat session: {e}", exc_info=True)
        await cl.Message(
            content=f"Sorry, I couldn't initialize the chat session. Error: {e}"
        ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handles incoming user messages and interacts with the Gemini model."""
    chat_session = cl.user_session.get("chat_session") # type: ChatSession | None

    if not chat_session:
        logger.warning("Chat session not found in user session.")
        await cl.Message(
            content="It seems the chat session wasn't initialized correctly. Please try refreshing or restarting the chat."
        ).send()
        return

    user_message = message.content
    logger.info(f"Received message: {user_message}")

    # Prepare an empty message to stream the response into
    response_message = cl.Message(content="")
    await response_message.send() # Send the empty message holder first

    try:
        logger.info("Sending message to Gemini model...")
        # Use send_message from the ChatSession object; it handles history.
        # Stream the response for a better UX.
        response_stream = await chat_session.send_message_async(user_message, stream=True)

        # Iterate through the streamed chunks
        async for chunk in response_stream:
            try:
                # Check safety ratings - skip unsafe content chunks if necessary
                # Accessing candidates directly might be fragile depending on SDK version
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    candidate = chunk.candidates[0]

                    # --- Stream Text Content ---
                    # Ensure content and parts exist before trying to stream text
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, 'text'):
                            await response_message.stream_token(part.text)

                    # --- Check Finish Reason (if present and meaningful) ---
                    # Check if finish_reason exists on the candidate
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason_val = candidate.finish_reason
                        # A finish_reason value > 0 typically indicates a terminal state (STOP, MAX_TOKENS, SAFETY, etc.)
                        # FinishReason.FINISH_REASON_UNSPECIFIED is often 0.
                        if finish_reason_val > 0:
                            try:
                                # Attempt to convert the numeric value to its string name
                                finish_reason_str = FinishReason(finish_reason_val).name
                                logger.info(f"Gemini response finished. Reason: {finish_reason_str}")
                                # Handle the specific case where the finish reason is SAFETY
                                if finish_reason_str == "SAFETY":
                                    await response_message.stream_token("\n\n_[Response stopped due to safety concerns.]_")
                            except ValueError:
                                # Log a warning if the finish reason value doesn't map to a known enum name
                                logger.warning(f"Received unknown finish reason value: {finish_reason_val}")

            except AttributeError as ae:
                 logger.warning(f"Attribute error while processing chunk: {ae}. Chunk: {chunk}", exc_info=False)
                 # Fallback or skip chunk if structure is unexpected
            except Exception as chunk_exc:
                logger.error(f"Error processing response chunk: {chunk_exc}", exc_info=True)
                await response_message.stream_token(f"\n_[Error processing response part: {chunk_exc}]_")


        # Final update after streaming is complete (optional, can be empty if all streamed)
        await response_message.update()
        logger.info("Finished streaming Gemini response.")

    except Exception as e:
        logger.error(f"Error sending message or processing response: {e}", exc_info=True)
        # Update the message content with the error
        response_message.content = f"Sorry, an error occurred while communicating with the AI: {e}"
        await response_message.update()