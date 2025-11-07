from uagents import Agent
from chat_proto import chat_proto

# Create the agent with mailbox enabled
agent = Agent(
    name="A2rchi Agent",
    seed="a2rchi secret phrase",  # Use a real secure seed in production
    mailbox=True
)

# Attach the chat protocol
agent.include(chat_proto)

# Run the agent
if __name__ == "__main__":
    agent.run()
