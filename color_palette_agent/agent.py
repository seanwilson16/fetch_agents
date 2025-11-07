from uagents import Agent
from chat_proto import chat_proto

agent = Agent(
    name="color_palette_agent",
    seed="colorpaletteagentsecretphrase",
    mailbox=True,
    port=8001
)

agent.include(chat_proto)

if __name__ == "__main__":
    agent.run()
