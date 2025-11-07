from datetime import datetime
from uuid import uuid4
from typing import Any
from uagents import Context, Model, Protocol
from pydantic import ValidationError
import requests
import os
import io

# Import the necessary components of the chat protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

from boltz2 import (
    get_prediction,
    validate_request,
    Boltz2Request,
    Boltz2Response,
    Modification,
    MoleculeType,
    ConstraintType,
    Contact,
    PocketConstraint,
    Atom,
    BondConstraint,
    Format,
    AlignmentFileRecord,
    Polymer,
    Ligand,
    Metric,
    Structure,
)

AI_AGENT_ADDRESS = "agent1qtlpfshtlcxekgrfcpmv7m9zpajuwu7d5jfyachvpa4u3dkt6k0uwwp2lct"

if not AI_AGENT_ADDRESS:
    raise ValueError("AI_AGENT_ADDRESS not set")

AGENT_PROMPT = """You are generating a structured object representing a protein design request for the MIT Boltz2 API. The user will provide a natural language input describing one or more biological polymers, ligands, or constraints.

Your job is to use the information that the user provides to fill out the given output schema.

If the user does not specify a field, omit that field from your response. It is VERY important that you do not hallucinate values. The code will apply defaults for you.

ONLY fill fields the user provides information for.

It is very important that if the user says something completely unrelated to the schema, return an empty dictionary.

However, if the user refers to a field in the schema, you must include the information they provide for that field in the output.

If the user requests the structure of a polymer by name, i.e. Human Insulin, please fill in the molecule_type and sequence attributes to the best of your knowledge. **Never abbreviate the sequence. Always include the FULL sequence in capital letter format as ONE STRING. DO NOT cut off the sequence before it is complete.**

If the user asks for a certain number of predictions or structures, assume they are referring to diffusion_samples

When including the 'msa' field in the polymers, structure it as a nested dictionary in the format:
{
  "msa": {
    "<database_name>": {
      "<format>": {
        "alignment": "<alignment_string>",
        "format": "<format_string>"
      }
    }
  }
}

**NEVER return any fields from the schema itself (including 'title': 'Boltz2Request'). You are solely supposed to fill in the schema. If you are unsure of what to return, just return an empty dictionary.**

Example:
If the user says:
"Predict the structure of the following protein: MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAG"

Then output:
{
  "polymers": [
    {
      "molecule_type": "protein",
      "sequence": "MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAG"
    }
  ]
}

If the user says:
"Hello!"

Then output:
{}
"""

def create_text_chat(text: str, end_session: bool = False) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    if end_session:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=content,
    )

chat_proto = Protocol(spec=chat_protocol_spec)
struct_output_client_proto = Protocol(
    name="StructuredOutputClientProtocol", version="0.1.0"
)

class StructuredOutputPrompt(Model):
    prompt: str
    output_schema: dict[str, Any]

class StructuredOutputResponse(Model):
    output: dict[str, Any]

@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info(f"Got a message from {sender}: {msg}")
    ctx.storage.set(str(ctx.session), sender)
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
            ctx.storage.set(str(ctx.session), sender)
            await ctx.send(
                AI_AGENT_ADDRESS,
                StructuredOutputPrompt(
                    prompt=f"{AGENT_PROMPT} Here is the user's prompt: {item.text}", output_schema=Boltz2Request.schema()
                ),
            )
        else:
            ctx.logger.info(f"Got unexpected content from {sender}")

@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(
        f"Got an acknowledgement from {sender} for {msg.acknowledged_msg_id}"
    )

@struct_output_client_proto.on_message(StructuredOutputResponse)
async def handle_structured_output_response(
    ctx: Context, sender: str, msg: StructuredOutputResponse
):
    session_sender = ctx.storage.get(str(ctx.session))
    if session_sender is None:
        ctx.logger.error(
            "Discarding message because no session sender found in storage"
        )
        return

    try:
        ctx.logger.info(f"Raw structured output received:\n{msg.output}.")

        issues = validate_request(ctx, msg.output)

        if issues:
            if len(issues) > 1:
                resolve_message = "\n\n🛠️ Please resolve these issues and re-enter your prompt!"
            else:
                resolve_message = "\n\n🛠️ Please resolve this issue and re-enter your prompt!"
            await ctx.send(
                session_sender,
                create_text_chat("⚠️ " + "\n\n⚠️".join(issues) + resolve_message)
            )
            return

        ctx.logger.info("Got to validate_request")


        validated = Boltz2Request.model_validate(msg.output)

        ctx.logger.info(f"Validated Request Model: {validated}")


        output_format = validated.output_format.lower()  # e.g., "mmcif" or "pdb"

        ctx.logger.info(f"Made it to message output; putting it together")
        # Get the raw structured results for this request
        response: Boltz2Response | str = await get_prediction(ctx, validated)
        if isinstance(response, str):
            await ctx.send(
                session_sender,
                create_text_chat(f"⚠️ {response}\n\n🔁 Please try a different prompt.")
            )
            return

        ctx.logger.info(f"{len(response.structures)} structure(s) found in response.")

        if len(response.structures) > 1:
            message_lines = ["🔬 Boltz2 predicted the following biological structures from your query:\n"]
        else:
            message_lines = ["🔬 Boltz2 predicted the following biological structure from your query:\n"]

        for i, structure in enumerate(response.structures):
            name = structure.name or f"Structure {i+1}"
            filename = f"structure_{uuid4()}.{output_format}"
            ctx.logger.info(f"Processing structure {i+1}: {name}")

            structure_str = structure.structure

            payload = {
                "description": "Boltz2-predicted structure",
                "public": True,
                "files": {
                    filename: {"content": structure_str}
                }
            }
            ctx.logger.info(f"Created payload")
            headers = {
                "Authorization": f"token {os.getenv('GITHUB_PAT')}",
                "Accept": "application/vnd.github.v3+json"
            }
            ctx.logger.info(f"Wrote headers")

            # Step 3: Send to GitHub
            github_response = requests.post("https://api.github.com/gists", headers=headers, json=payload)
            github_response.raise_for_status()

            ctx.logger.info(f"Sent to github")

            raw_url = github_response.json()["files"][filename]["raw_url"]
            ctx.logger.info(f"Got file url: {raw_url}")

            molstar_url = f"https://molstar.org/viewer/?structure-url={raw_url}&structure-url-format={output_format}"
            score = response.confidence_scores[i]
            message_lines.append(f"🧬 **{name}** (avg. confidence: {score:.2f})  | 🔗 [Click to view in 3D]({molstar_url})\n")

        full_message = "\n".join(message_lines)
        ctx.logger.info("Sending final message to user...")
        await ctx.send(session_sender, create_text_chat(full_message))
        ctx.logger.info("Message sent successfully.")

    except Exception as err:
        ctx.logger.error(err)
        await ctx.send(
            session_sender,
            create_text_chat(
                "Sorry, I couldn't output the structure of your request. Please try again later."
            ),
        )
        return
