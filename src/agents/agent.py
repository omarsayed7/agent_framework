from models.agent import AgentCharacter
from helpers import load_character
from providers import get_model
from tools import get_websearch_tool

from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage


class State(TypedDict):
    messages: Annotated[list, add_messages]


class BaseAgent:
    def __init__(self, character_file_name: Optional[str] = "") -> None:
        # Determine the default path if none is supplied
        character_data = load_character(character_file_name)
        # Parse data into the AgentCharacter Pydantic model
        self.character = AgentCharacter(**character_data)
        self.llm = self._setup_llm_provide()
        self.tools = self._setup_tools()
        self.memory = MemorySaver()
        self.agent = self._build_graph()
        # Cache for system prompt
        self._system_prompt = None

    def _setup_llm_provide(self):
        return get_model(self.character.model_provider)

    def _setup_tools(self):
        self.tools = []
        self.character.tools.append("websearch_tool")
        for tool in self.character.tools:
            if tool == "websearch_tool":
                websearch_tool = get_websearch_tool("duck")
                if websearch_tool:
                    self.tools.append(websearch_tool)
        return self.tools

    def _build_graph(self):
        graph_builder = StateGraph(State)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        graph_builder.add_node("chatbot", self.call_model)
        tool_node = ToolNode(tools=self.tools)
        graph_builder.add_node("tools", tool_node)
        graph_builder.add_conditional_edges(
            "chatbot",
            tools_condition,
        )
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge(START, "chatbot")
        self.graph = graph_builder.compile(checkpointer=self.memory)
        """
        # warmup
        for event in self.graph.stream(
            {"messages": [("user", "What do you know about AI?")]},
            config={"configurable": {"thread_id": 42}},
            stream_mode="values",
        ):
            event["messages"][-1].pretty_print()
        """
        return self.graph

    def call_model(self, state: State):
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    def _construct_system_prompt(self) -> str:
        """Construct the system prompt from agent configuration"""
        if self._system_prompt is None:
            prompt_parts = []
            prompt_parts.append(f"You are {self.character.name} \n")
            prompt_parts.extend(self.character.bio)

            if self.character.message_examples:
                prompt_parts.append(
                    "\nHere are some examples of your style (Please avoid repeating any of these):"
                )
                if self.character.message_examples:
                    prompt_parts.extend(
                        f"- {example}" for example in self.character.message_examples
                    )

            self._system_prompt = "\n".join(prompt_parts)
        print(self._system_prompt)
        return self._system_prompt

    def prompt_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text using the configured LLM provider"""
        system_prompt = system_prompt or self._construct_system_prompt()
        if (
            len(
                self.graph.get_state(
                    config={"configurable": {"thread_id": 42}},
                ).values.get("messages", [])
            )
            == 0
        ):
            self.graph.update_state(
                {"configurable": {"thread_id": 42}},
                {"messages": [SystemMessage(content=system_prompt)]},
            )
        sent_message = HumanMessage(content=prompt)
        final_state = self.graph.invoke(
            {"messages": [sent_message]}, config={"configurable": {"thread_id": 42}}
        )
        return final_state["messages"][-1].content

    async def stream_execute(self) -> None:
        pass
