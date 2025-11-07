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

from election_results import get_results_from_state_yr, ResultsRequest, ResultsResponse, CandidateResult

# AI Agent Address for structured output processing
AI_AGENT_ADDRESS = 'agent1q0h70caed8ax769shpemapzkyk65uscw4xwk6dc4t3emvp5jdcvqs9xs32y'

if not AI_AGENT_ADDRESS:
    raise ValueError("AI_AGENT_ADDRESS not set")

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
            ctx.logger.info(f"{ResultsRequest.schema()}")
            await ctx.send(
                AI_AGENT_ADDRESS,
                StructuredOutputPrompt(
                    prompt=item.text, output_schema=ResultsRequest.schema()
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
        results_request = ResultsRequest.parse_obj(msg.output)
        state = results_request.state
        year = results_request.year

        if state == "<UNKNOWN>" and year == "<UNKNOWN>":
            await ctx.send(
                session_sender,
                create_text_chat("Please include both a valid U.S. state and presidential election year.")
            )
            return
        if state == "<UNKNOWN>":
            await ctx.send(
                session_sender,
                create_text_chat("Sorry, I couldn't find a valid U.S. state in your query.")
            )
            return
        if year == "<UNKNOWN>":
            await ctx.send(
                session_sender,
                create_text_chat("Sorry, I couldn't find a valid election year in your query.")
            )
            return

        # Get the raw structured results for this state and year
        response: ResultsResponse = await get_results_from_state_yr(state, year)
        results: list[CandidateResult] = response.results

        if not results:
            await ctx.send(
                session_sender,
                create_text_chat(f"No results found for {state.title()} in {year}.")
            )
            return

        # Format the results
        winner = results[0]
        summary = (
            f"{winner.party_detailed} candidate {winner.candidate} won {state.title()} in {year}. "
            f"{winner.totalvotes:,} people voted in total."
        )

        vote_lines = ["Here are the vote totals:"]
        for i, row in enumerate(results, start=1):
            vote_lines.append(
                f"{i}. {row.candidate} ({row.party_detailed}): {row.candidatevotes:,} votes"
            )

        full_text = summary + "\n\n" + "\n".join(vote_lines)
        await ctx.send(session_sender, create_text_chat(full_text))

    except Exception as err:
        ctx.logger.error(err)
        await ctx.send(
            session_sender,
            create_text_chat(
                "Sorry, I couldn't check the election results. Please try again later."
            ),
        )
        return
