import base64
import os
import requests
from uuid import uuid4
from datetime import datetime
from pydantic.v1 import UUID4

from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    Resource,
    ResourceContent,
    MetadataContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)
from uagents_core.storage import ExternalStorage
from color_palette import get_color_palette_from_content, generate_palette_image

AGENTVERSE_API_KEY = os.getenv("AGENTVERSE_API_KEY")
STORAGE_URL = os.getenv("AGENTVERSE_URL", "https://agentverse.ai") + "/v1/storage"
if AGENTVERSE_API_KEY is None:
    raise ValueError("You need to provide an API_TOKEN.")
SUPPORTED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


external_storage = ExternalStorage(api_token=AGENTVERSE_API_KEY, storage_url=STORAGE_URL)

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

def create_resource_chat(asset_id: str, uri: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[
            ResourceContent(
                type="resource",
                resource_id=UUID4(asset_id),
                resource=Resource(
                    uri=uri,
                    metadata={
                        "mime_type": "image/png",
                        "role": "generated-image"
                    }
                )
            )
        ]
    )

def create_metadata(metadata: dict[str, str]) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[MetadataContent(
            type="metadata",
            metadata=metadata,
        )],
    )

chat_proto = Protocol(spec=chat_protocol_spec)

@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id),
    )

    prompt_content = []
    for item in msg.content:
        if isinstance(item, StartSessionContent):
            await ctx.send(sender, create_metadata({
                "attachments": "true",
                "attachments_required": "false"
            }))
            return
        elif isinstance(item, TextContent):
            prompt_content.append({"text": item.text, "type": "text"})
        elif isinstance(item, ResourceContent):
            try:
                data = external_storage.download(str(item.resource_id))
                contents = data["contents"]
                mime_type = data["mime_type"]

                # FIX: if it's a base64-encoded string, decode it back to bytes
                if isinstance(contents, str):
                    contents = base64.b64decode(contents)

                if mime_type not in SUPPORTED_MIME_TYPES:
                    ctx.logger.warning(f"Unsupported image type received: {mime_type}")
                    await ctx.send(sender, create_text_chat(
                        "Unsupported image type. Please upload a PNG, JPEG, GIF, or WebP file."
                    ))
                    return  # Skip this item and don't append to prompt_content

                prompt_content.append({
                    "type": "resource",
                    "mime_type": data["mime_type"],
                    "contents": contents,
                })

            except Exception as ex:
                ctx.logger.error(f"Failed to download resource: {ex}")
                await ctx.send(sender, create_text_chat("Failed to download resource."))

        else:
            ctx.logger.warning(f"Got unexpected content from {sender}")

    if prompt_content:
        colors_response = get_color_palette_from_content(prompt_content)
        image_data = generate_palette_image(colors_response)

        asset_id = external_storage.create_asset(
            name=f"palette-{uuid4()}",
            content=image_data,
            mime_type="image/png"
        )

        external_storage.set_permissions(asset_id=asset_id, agent_address=sender)
        palette_url = f"agent-storage://{external_storage.storage_url}/{asset_id}"

    await ctx.send(sender, create_resource_chat(asset_id, palette_url))

    bullet_lines = "\n".join(
    f"- {color['name']}: {color['hex']}" for color in colors_response
)
    full_message = f"Your color palette (from left to right) is:\n{bullet_lines}"

    await ctx.send(sender, create_text_chat(full_message))


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Got an acknowledgement from {sender} for {msg.acknowledged_msg_id}")
