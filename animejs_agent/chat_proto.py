from uuid import uuid4
from datetime import datetime

from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    Resource,
    ResourceContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

from animejs import generate_code, generate_livecodes_link

def create_text_chat(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text)],
    )

def create_end_session_chat() -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[EndSessionContent(type="end-session")],
    )

chat_proto = Protocol(spec=chat_protocol_spec)

@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id),
    )

    for item in msg.content:
        if isinstance(item, StartSessionContent):
            ctx.logger.info(f"Got a start session message from {sender}")
            continue
        elif isinstance(item, TextContent):
            ctx.logger.info(f"Got a message from {sender}: {item.text}")

            prompt = msg.content[0].text
            try:
                ctx.logger.info(f"Checking prompt: {prompt}")
                code = await generate_code(ctx, prompt)

                ctx.logger.info(f"Got JS response: {code}")
                link = await generate_livecodes_link(code["html"], code["css"], code["js"])

                pretty_output = (
                    "✨ Here’s the JavaScript using the **anime.js** library to bring your request to life:\n\n"
                    f"```javascript\n{code['js']}\n```\n\n"
                    f"🚀 [**Click here to run it instantly on LiveCodes**]({link}) \n\n"
                    "🎨 When you open it, you can also explore and edit the corresponding **HTML** and **CSS** for full customization!"
                )

                await ctx.send(
                    sender,
                    create_text_chat(pretty_output)
                )

            except Exception as err:
                ctx.logger.error(err)
                await ctx.send(
                    sender,
                    create_text_chat(
                        "Sorry, I couldn't process your request. Please try again later."
                    ),
                )
                return

        else:
            ctx.logger.info(f"Got unexpected content from {sender}")


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Got an acknowledgement from {sender} for {msg.acknowledged_msg_id}")
