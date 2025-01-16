from agents import BaseAgent
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    agent = BaseAgent(character_file_name="default_character.json")
    print(agent.prompt_llm("Hello! What is your name?"))
