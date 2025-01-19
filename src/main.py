import asyncio
from agents import BaseAgent
from dotenv import load_dotenv

load_dotenv()


# async def main():
#     agent = BaseAgent(character_file_name="default_character.json")
#     # Run tasks concurrently using asyncio.gather
#     await asyncio.gather(
#         agent.prompt_llm(session_id="11", prompt="Hello! What is your name?")
#     )


# if __name__ == "__main__":
#     # Run the main function
#     asyncio.run(main())


# Run the application with uvicorn:
# uvicorn main:app --reload
import uvicorn
from dotenv import load_dotenv


load_dotenv()

if __name__ == "__main__":
    uvicorn.run("app:app", reload=True)
