import json
import os
from typing import Any, List, Dict
from openai import OpenAI, OpenAIError
import base64
from PIL import Image
from io import BytesIO
import requests

import requests
import os

client = OpenAI()

def get_color_palette_from_content(prompt_content: List[Dict[str, str | bytes]]) -> list[dict]:
    """
    Accepts a list of prompt parts (text or image), and returns a list of 5 colors.
    Each part is a dict with 'type': 'text' or 'resource', and associated data.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a JSON-only assistant. You must respond ONLY with valid raw JSON — no markdown, no explanations, no backticks. "
                "Given a visual and/or descriptive prompt, respond in this **exact** format with 5 named colors:\n"
                "{ \"palette\": [ { \"name\": \"Sunset Orange\", \"hex\": \"#FD5E53\" }, ... ] }"
            )
        }
    ]

    user_parts = []

    for item in prompt_content:
        if item["type"] == "text":
            user_parts.append({
                "type": "text",
                "text": item["text"]
            })
        elif item["type"] == "resource":
            print(item["mime_type"])
            b64_img = base64.b64encode(item["contents"]).decode("utf-8")
            user_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{item['mime_type']};base64,{b64_img}"
                }
            })

    messages.append({
        "role": "user",
        "content": user_parts
    })
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )

    raw = response.choices[0].message.content.strip()

    try:
        if raw.startswith("```json"):
            raw = raw.removeprefix("```json").removesuffix("```").strip()

        # Ensure we're not parsing an empty or natural-language response
        if not raw.startswith("{"):
            raise ValueError(f"Expected JSON but got: {raw[:100]}")

        return json.loads(raw)["palette"]
    except Exception as e:
        raise ValueError(f"Failed to parse palette: {e}")


def generate_palette_image(colors: List[Dict[str, str]], width: int = 510, height: int = 128) -> bytes:
    """
    Generate a horizontal PNG palette image using Pillow from 5 hex colors.
    Returns image data as bytes (PNG format), ready to upload.
    """
    if len(colors) != 5:
        raise ValueError("Expected exactly 5 colors")

    block_width = width // 5
    img = Image.new("RGB", (width, height))

    for i, color in enumerate(colors):
        hex_code = color["hex"]
        block = Image.new("RGB", (block_width, height), hex_code)
        img.paste(block, (i * block_width, 0))

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
