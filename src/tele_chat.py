import logging
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from dotenv import load_dotenv

load_dotenv()

from core import AgentRuntime


class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.application = (
            ApplicationBuilder().token(self.token).concurrent_updates(True).build()
        )
        self.setup_handlers()

    def setup_handlers(self):
        # Command handler for the /start command
        start_handler = CommandHandler("start", self.start)
        self.application.add_handler(start_handler)

        # Message handler for echoing received messages
        echo_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo)
        self.application.add_handler(echo_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Hello! I am your bot. How can I assist you today?"
        )

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        received_text = update.message.text
        agent = BaseAgent(character_file_name="default_character.json")
        print(agent.tools)
        # Run tasks concurrently using asyncio.gather
        result = await agent.prompt_llm(session_id="11", prompt=received_text)
        await update.message.reply_text(f"{result}")

    def run(self):
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        self.application.run_polling()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    if not BOT_TOKEN:
        raise ValueError(
            "No BOT_TOKEN provided. Please set it in the environment variables."
        )
    runtime = AgentRuntime()
    print(runtime)
    runtime.run()
    # bot = TelegramBot(BOT_TOKEN)
    # bot.run()
    # print("hello")
