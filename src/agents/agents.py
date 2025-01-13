from dataclasses import dataclass

from langgraph.graph.state import CompiledStateGraph

from agents.chatbot import chatbot

DEFAULT_AGENT = "research-assistant"


@dataclass
class Agent:
    description: str
    graph: CompiledStateGraph


agents: dict[str, Agent] = {
    "chatbot": Agent(description="A simple chatbot.", graph=chatbot),
}


def get_agent(agent_id: str) -> CompiledStateGraph:
    print("here", agents[agent_id].graph)
    return agents[agent_id].graph
