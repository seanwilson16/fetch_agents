from uagents import Agent
from chat_proto import chat_proto

agent = Agent(
    name="animejs_agent_v2",
    seed="animejs_agent_v2",
    port=8011,
    mailbox=True,
)

agent.include(chat_proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
