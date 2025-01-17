from fastapi import APIRouter, HTTPException
from bson import ObjectId
from connections import mongodb
from models import AgentResponse, AgentCharacter
from typing import List
from datetime import datetime, UTC
from services import router


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
