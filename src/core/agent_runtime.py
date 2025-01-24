from agents import BaseAgent
from connections.telegram import TelegramConnection


class AgentRuntime:
    def __init__(self) -> None:
        self.agent = BaseAgent(character_file_name="kira_character.json")
        self.telegram_connection = TelegramConnection(agent=self.agent)

    def run(self):
        while True:
            self.telegram_connection.run()
