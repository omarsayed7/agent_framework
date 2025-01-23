from models.providers import AllModelEnum
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime


class Connection(BaseModel):
    name: str
    actions: list


class AgentCharacter(BaseModel):
    """
    AgentCharacter model
    """

    name: str = Field(
        description="Character name.",
        examples=["Kira Faye"],
    )
    age: int = Field(description="Character age.", examples=[27])
    bio: List[str] = Field(
        description="Character biography or description",
        examples=["What is the weather in Tokyo?"],
    )
    personality: List[str] = Field(
        description="Character personality traits summarized in a single list.",
        examples=["Warm yet commanding, razor-sharp wit, empathetic and loyal."],
    )
    backstory: List[str] = Field(
        description="Storyline or backstory element",
        examples=["What is the weather in Tokyo?"],
    )
    message_examples: List[str] = Field(
        description="Message examples for the character agent",
        examples=["What is the weather in Tokyo?"],
    )
    style: List[str] = Field(
        description="Descriptions of how the character communicates in different contexts.",
        examples=[
            "Professional: Confident, calm, and approachable.",
            "With Friends: Playful, teasing, and relaxed.",
            "In Private: Reflective and poetic.",
        ],
    )
    traits: List[str] = Field(
        description="List of the character's core qualities, quirks, or special attributes.",
        examples=[
            "Warm and Commanding Voice",
            "Witty, Playful, and Sharp",
            "Polished Yet Street-Smart",
        ],
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
