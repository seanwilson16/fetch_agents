from datetime import datetime
from uuid import uuid4

from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

from a2rchi import answer_physics_question

HISTORY_KEY = lambda session: f"{session}:history"

# Create the chat protocol using the standard chat spec
chat_proto = Protocol(spec=chat_protocol_spec)

# Helper to build chat responses
def create_text_chat(text: str, end_session: bool = False) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    if end_session:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=content,
    )

# Required: handle incoming chat messages
@chat_proto.on_message(model=ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info(f"📩 Received ChatMessage from {sender}")
    ctx.storage.set(str(ctx.session), sender)

    # Acknowledge receipt
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.utcnow(),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    # Load history from storage
    history_key = HISTORY_KEY(ctx.session)
    history = ctx.storage.get(history_key) or []

    for item in msg.content:
        if isinstance(item, StartSessionContent):
            ctx.logger.info("🟢 New chat session started")
            continue
        elif isinstance(item, TextContent):
            question = item.text
            ctx.logger.info(f"🧠 User asked: {question}")

            response = await answer_physics_question(question, ctx, history)
            await ctx.send(sender, create_text_chat(response))

            # Append user question and assistant reply
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": response})

            # Save back to session storage
            ctx.storage.set(history_key, history)

        else:
            ctx.logger.info(f"⚠️ Ignoring unknown content type from {sender}")

# Optional: handle acknowledgements from others
@chat_proto.on_message(model=ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(
        f"✅ Got acknowledgement from {sender} for message {msg.acknowledged_msg_id}"
    )
