from models.providers import AllModelEnum
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime


class Connection(BaseModel):
    name: str
    actions: list


class AgentCharacter(BaseModel):
    name: str = Field(
        description="Character name.",
        examples=["Eliza"],
    )
    bio: List[str] = Field(
        description="Character biography or description",
        examples=["What is the weather in Tokyo?"],
    )
    backstory: List[str] = Field(
        description="Storyline or backstory element",
        examples=["What is the weather in Tokyo?"],
    )
    message_examples: List[str] = Field(
        description="Message examples for the character agent",
        examples=["What is the weather in Tokyo?"],
    )
    model_provider: AllModelEnum = Field(
        description="Select the LLM to the agent",
        examples=["gemini-1.5-flash"],
    )
    tools: List[str] = Field(
        description="List of tools that the LLM is gonna use",
        examples=["What is the weather in Tokyo?"],
    )
    connections: List[Connection] = Field(
        description="List of connections that the agent will interacte with",
        examples=[{"name": "telegram", "actions": ["handle_messages"]}],
    )


class AgentResponse(AgentCharacter):
    id: str
    created_at: datetime
    updated_at: datetime
