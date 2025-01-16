from models.providers import AllModelEnum
from typing import List
from pydantic import BaseModel, Field


class AgentCharacter(BaseModel):
    """
    Info about the model (Role-play) kind of agents"""

    name: str = Field(
        description="Character name.",
        examples="Eliza",
    )
    bio: List[str] = Field(description="Character biography or description")
    backstory: List[str] = Field(description="Storyline or backstory element")
    message_examples: List[str] = Field(
        description="Message examples for the character agent"
    )
    model_provider: AllModelEnum = Field(description="Select the LLM to the agent")
    tools: List[str] = Field(description="List of tools that the LLM is gonna use")
