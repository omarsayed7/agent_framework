from pymongo import AsyncMongoClient
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from typing import Literal
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

load_dotenv()


@tool
def get_weather(city: Literal["nyc", "sf"]):
    """Use this to get weather information."""
    if city == "nyc":
        return "It might be cloudy in nyc"
    elif city == "sf":
        return "It's always sunny in sf"
    else:
        raise AssertionError("Unknown city")


tools = [get_weather]
model = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    streaming=True,
    # other params...
)


MONGODB_URI = "mongodb+srv://testdb:12345@cluster0.k6ymn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongodb_client = MongoClient(MONGODB_URI)

checkpointer = MongoDBSaver(mongodb_client)
graph = create_react_agent(model, tools=tools, checkpointer=checkpointer)
config = {"configurable": {"thread_id": "2"}}
response = graph.invoke({"messages": [("user", "What is my name?")]}, config)
print(response)
