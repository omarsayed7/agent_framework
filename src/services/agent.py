import logging
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from bson import ObjectId
from connections import mongodb
from models import AgentResponse, AgentCharacter
from typing import List, Annotated, Any
from datetime import datetime, UTC
from fastapi.responses import StreamingResponse
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from uuid import UUID, uuid4
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from services import router
from agents import BaseAgent


logger = logging.getLogger(__name__)


@router.post("/", tags=["agents"])
async def create_agent(agent: AgentCharacter):
    """Create a new agent."""
    now = datetime.now(UTC)
    print("sss")
    new_agent = agent.dict()
    new_agent.update({"created_at": now, "updated_at": now})
    print(new_agent)
    result = await mongodb.db["agents"].insert_one(new_agent)
    new_agent["_id"] = str(result.inserted_id)
    return new_agent


@router.get("/{agent_id}", tags=["agents"])
async def get_agent(agent_id: str):
    """Get details of an agent."""
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID")
    agent = await mongodb.db["agents"].find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.pop("_id")
    agent["id"] = agent_id
    return agent


@router.put("/{agent_id}", tags=["agents"])
async def update_agent(agent_id: str, updated_agent: AgentCharacter):
    """Update an agent's details."""
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID")
    now = datetime.now(UTC)
    result = await mongodb.db["agents"].update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": {**updated_agent.dict(), "updated_at": now}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = await mongodb.db["agents"].find_one({"_id": ObjectId(agent_id)})
    agent["id"] = str(agent["_id"])
    return agent


@router.delete("/{agent_id}", tags=["agents"])
async def delete_agent(agent_id: str):
    """Delete an agent."""
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID")
    result = await mongodb.db["agents"].delete_one({"_id": ObjectId(agent_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": f"Agent {agent_id} deleted successfully"}


def _parse_input(user_input) -> tuple[dict[str, Any], UUID]:
    run_id = uuid4()
    thread_id = 1
    kwargs = {
        "input": {"messages": [HumanMessage(content=user_input)]},
        "config": RunnableConfig(
            configurable={"thread_id": thread_id},
            run_id=run_id,
        ),
    }
    return kwargs, run_id


async def message_generator(
    user_input: str, agent_id: str = 1
) -> AsyncGenerator[str, None]:
    """
    Generate a stream of messages from the agent.

    This is the workhorse method for the /stream endpoint.
    """
    agent = BaseAgent(character_file_name="default_character.json")
    agent: CompiledStateGraph = agent.agent
    kwargs, run_id = _parse_input(user_input)

    # Process streamed events from the graph and yield messages over the SSE stream.
    async for event in agent.astream_events(**kwargs, version="v2"):
        if not event:
            continue

        new_messages = []
        # Yield messages written to the graph state after node execution finishes.
        if (
            event["event"] == "on_chain_end"
            # on_chain_end gets called a bunch of times in a graph execution
            # This filters out everything except for "graph node finished"
            and any(t.startswith("graph:step:") for t in event.get("tags", []))
            and "messages" in event["data"]["output"]
        ):
            new_messages = event["data"]["output"]["messages"]

        # Also yield intermediate messages from agents.utils.CustomData.adispatch().
        if event["event"] == "on_custom_event" and "custom_data_dispatch" in event.get(
            "tags", []
        ):
            new_messages = [event["data"]]

        for message in new_messages:
            try:
                chat_message = langchain_to_chat_message(message)
                chat_message.run_id = str(run_id)
            except Exception as e:
                logger.error(f"Error parsing message: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': 'Unexpected error'})}\n\n"
                continue
            # LangGraph re-sends the input message, which feels weird, so drop it
            if (
                chat_message.type == "human"
                and chat_message.content == user_input.message
            ):
                continue
            yield f"data: {json.dumps({'type': 'message', 'content': chat_message.model_dump()})}\n\n"

        # Yield tokens streamed from LLMs.
        if (
            event["event"] == "on_chat_model_stream"
            and user_input.stream_tokens
            and "llama_guard" not in event.get("tags", [])
        ):
            content = remove_tool_calls(event["data"]["chunk"].content)
            if content:
                # Empty content in the context of OpenAI usually means
                # that the model is asking for a tool to be invoked.
                # So we only print non-empty content.
                yield f"data: {json.dumps({'type': 'token', 'content': convert_message_content_to_string(content)})}\n\n"
            continue

    yield "data: [DONE]\n\n"


def _sse_response_example() -> dict[int, Any]:
    return {
        status.HTTP_200_OK: {
            "description": "Server Sent Event Response",
            "content": {
                "text/event-stream": {
                    "example": "data: {'type': 'token', 'content': 'Hello'}\n\ndata: {'type': 'token', 'content': ' World'}\n\ndata: [DONE]\n\n",
                    "schema": {"type": "string"},
                }
            },
        }
    }


@router.post(
    "stream",
    response_class=StreamingResponse,
    responses=_sse_response_example(),
    tags=["stream"],
)
async def stream(user_input) -> StreamingResponse:
    """
    Stream an agent's response to a user input, including intermediate messages and tokens.

    If agent_id is not provided, the default agent will be used.
    Use thread_id to persist and continue a multi-turn conversation. run_id kwarg
    is also attached to all messages for recording feedback.

    Set `stream_tokens=false` to return intermediate messages but not token-by-token.
    """
    return StreamingResponse(
        message_generator(user_input, agent_id=1),
        media_type="text/event-stream",
    )


@router.post("/invoke", tags=["invoke"])
async def invoke(user_input, agent_id: str = "1"):
    """
    Invoke an agent with user input to retrieve a final response.

    If agent_id is not provided, the default agent will be used.
    Use thread_id to persist and continue a multi-turn conversation. run_id kwarg
    is also attached to messages for recording feedback.
    """
    agent = BaseAgent(character_file_name="default_character.json")
    agent: CompiledStateGraph = agent.agent
    kwargs, run_id = _parse_input(user_input)
    try:
        response = await agent.ainvoke(**kwargs)
        output = response["messages"][-1]
        output.run_id = str(run_id)
        return output
    except Exception as e:
        logger.error(f"An exception occurred: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error")
