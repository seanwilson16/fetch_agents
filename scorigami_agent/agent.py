from uagents import Agent
from chat_proto import chat_proto, struct_output_client_proto

# Create the Scorigami Agent
scorigami_agent = Agent(
    name="ScorigamiAgent",
    port=8000,
    seed="scorigami agent secret phrase",  # optional but keeps address stable
    mailbox=True,  # ✅ Enables remote message routing via UAgents mailbox
)

# Include the chat and structured output protocols
scorigami_agent.include(chat_proto)
scorigami_agent.include(struct_output_client_proto)

# Start the agent
if __name__ == "__main__":
    scorigami_agent.run()
