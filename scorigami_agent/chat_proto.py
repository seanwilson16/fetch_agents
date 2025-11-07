from datetime import datetime
from uuid import uuid4
from typing import Any

from uagents import Context, Model, Protocol

# Import the necessary components of the chat protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

from scorigami import get_scorigami_from_score, scorigamiRequest, scorigamiResponse

# AI Agent Address for structured output processing
AI_AGENT_ADDRESS = 'agent1qtlpfshtlcxekgrfcpmv7m9zpajuwu7d5jfyachvpa4u3dkt6k0uwwp2lct'

if not AI_AGENT_ADDRESS:
    raise ValueError("AI_AGENT_ADDRESS not set")

def parse_latest_game(latest: str | None) -> tuple[str, str, str]:
    """
    Parses: "Team A vs. Team B Month Day Year"
    Returns: team1, team2, formatted_date
    E.g., "Seattle Seahawks vs. 49ers November 17 2024" →
          ('Seattle Seahawks', '49ers', 'November 17th, 2024')
    """
    if not latest:
        return "", "", ""

    try:
        parts = latest.rsplit(" ", 3)
        if len(parts) != 4:
            return "", "", latest.strip()

        game_str, month, day_str, year = parts
        team1, team2 = game_str.split(" vs. ")

        # Add ordinal suffix to day
        day = int(day_str)
        if 10 < day % 100 < 14:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        day_with_suffix = f"{day}{suffix}"
        date = f"{month} {day_with_suffix}, {year}"

        return team1.strip(), team2.strip(), date
    except Exception:
        return "", "", latest.strip()

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
            ctx.storage.set(str(ctx.session) + ":raw_prompt", item.text.lower())
            await ctx.send(
                AI_AGENT_ADDRESS,
                StructuredOutputPrompt(
                    prompt=item.text, output_schema=scorigamiRequest.schema()
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
        # Parse the structured output to get state and year
        scorigami_request = scorigamiRequest.parse_obj(msg.output)
        score1 = scorigami_request.team1_score
        score2 = scorigami_request.team2_score

        # Reject if both scores are 0 AND the original user message didn't contain anything that looks like a score
        raw_prompt = ctx.storage.get(str(ctx.session) + ":raw_prompt")
        if score1 == 0 and score2 == 0:
            if not any(keyword in raw_prompt for keyword in ["0", "zero"]):
                await ctx.send(
                    session_sender,
                    create_text_chat("I couldn't understand your message. Try giving an NFL final score.")
                )
                return

        score1_invalid = not isinstance(score1, int) or score1 < 0 or score1 >= 100
        score2_invalid = not isinstance(score2, int) or score2 < 0 or score2 >= 100

        if score1_invalid and score2_invalid:
            await ctx.send(
                session_sender,
                create_text_chat(
                    "You provided 0 valid scores! Please provide 2 positive integer scores less than 100."
                ),
            )
            return

        elif score1_invalid or score2_invalid:
            await ctx.send(
                session_sender,
                create_text_chat(
                    "You only provided 1 valid score! Please provide 1 more positive integer score less than 100."
                ),
            )
            return

        response: scorigamiResponse = await get_scorigami_from_score(score1, score2)

        # Format the results
        if not response.possible:
            summary = f"The final score {response.score} has never occurred in NFL history because it is impossible!"

        elif not response.occurred:
            summary = f"The final score {response.score} is possible but has never occurred in NFL history!"

        else:
            winner, loser, date = parse_latest_game(response.latest)
            if score1 == score2:
                latest_summary = f"This score most recently occurred when the {winner} tied the {loser} {response.score} on {date}."
            else:
                latest_summary = f"This score most recently occurred when the {winner} defeated the {loser} {response.score} on {date}."
            if response.count == 1:
                summary = f"The final score {response.score} has occurred {response.count} time in NFL history.\n{latest_summary}"
            else:
                summary = f"The final score {response.score} has occurred {response.count} times throughout NFL history.\n{latest_summary}"


        await ctx.send(session_sender, create_text_chat(summary))

    except Exception as err:
        ctx.logger.error(err)
        await ctx.send(
            session_sender,
            create_text_chat(
                "Sorry, I couldn't check the provided score. Please try again later."
            ),
        )
        return
