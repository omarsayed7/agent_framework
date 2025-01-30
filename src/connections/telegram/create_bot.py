import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendMessageRequest
import time


class CreateTelegramBot:
    """
    Create a TelegramBot using Telegram user webapp.
    """

    def __init__(
        self, api_id: str, api_hash: str, phone_number: str, coolDown_secs: int = 5
    ):
        """
        Initializes the CreateTelegramBot class with the necessary credentials and settings.

        Args:
            api_id (str): The API ID for the Telegram client.
            api_hash (str): The API hash for the Telegram client.
            phone_number (str): The phone number associated with the Telegram account.
            coolDown_secs (int): The cooldown time in seconds between actions.
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.coolDown_secs = coolDown_secs
        self.client = TelegramClient("session_name", api_id, api_hash)

    async def create_bot(self, bot_name, bot_avatar_path):
        """
        Creates a new Telegram bot with the given name and avatar.

        Args:
            bot_name (str): The name of the bot.
            bot_avatar_path (str): Path to the bot's avatar image file.

        Returns:
            str: The bot token if successful, or "bad_bot_name" if the bot name is already taken.
        """
        await self.client.start(self.phone_number)
        time.sleep(self.coolDown_secs)
        # Send /newbot command to @BotFather
        bot_father_username = "BotFather"
        await self.client(SendMessageRequest(bot_father_username, "/newbot"))
        time.sleep(self.coolDown_secs)

        # Flag to track if the bot name is invalid
        invalid_bot_name = False

        @self.client.on(events.NewMessage(from_users=bot_father_username))
        async def handler(event):
            nonlocal invalid_bot_name
            global bot_username, token
            bot_username = f"{bot_name.lower().replace(' ', '_')}_bot"
            token = ""
            if "Alright, a new bot" in event.message.message:
                # Step 1: Enter the bot name
                await event.reply(bot_name)
                time.sleep(self.coolDown_secs)

            elif "Good. Now let's choose a username" in event.message.message:
                # Step 2: Enter the bot username (appending '_bot' to the name)
                # bot_username = f"{bot_name.lower().replace(' ', '_')}_bot"
                await event.reply(bot_username)
                time.sleep(self.coolDown_secs)
            elif "Sorry, this username is already taken" in event.message.message:
                # Handle the case where the bot username is already taken
                print("bad_bot_name")
                invalid_bot_name = True
                await self.client.disconnect()
                time.sleep(self.coolDown_secs)
            elif "Done! Congratulations" in event.message.message:
                # Step 3: Extract the bot token
                token = event.message.message.split("HTTP API:")[1].split(" ")[0]
                print(f"Bot Token: {token}")

                # Step 4: Set the bot's avatar
                if bot_avatar_path:
                    try:
                        await self.client(
                            SendMessageRequest(bot_father_username, "/setuserpic")
                        )
                        time.sleep(self.coolDown_secs)
                        await self.client(
                            SendMessageRequest(bot_father_username, f"@{bot_username}")
                        )
                        time.sleep(self.coolDown_secs)
                        # Send the image as a document
                        await self.client.send_file(
                            bot_father_username, bot_avatar_path
                        )
                        time.sleep(self.coolDown_secs)
                        print("Bot avatar set successfully!")
                    except Exception as e:
                        print(f"Failed to set bot avatar: {e}")

                await self.client.disconnect()
                time.sleep(self.coolDown_secs)

        # Keep the client running until the token is received or the bot name is invalid
        await self.client.run_until_disconnected()
        time.sleep(self.coolDown_secs)
        # Return "bad_bot_name" if the bot name was invalid
        if invalid_bot_name:
            return "bad_bot_name"

    async def run(self, bot_name, bot_avatar_path):
        """
        Runs the bot creation process.

        Args:
            bot_name (str): The name of the bot.
            bot_avatar_path (str): Path to the bot's avatar image file.
        """
        result = await self.create_bot(bot_name, bot_avatar_path)
        if result:
            print(result)


# Example usage
if __name__ == "__main__":
    api_id = ""
    api_hash = ""
    phone_number = ""

    bot_creator = CreateTelegramBot(api_id, api_hash, phone_number)
    bot_name = ""  # Replace with your desired bot name
    bot_avatar_path = ""  # Replace with the path to your bot's avatar image

    with bot_creator.client:
        bot_creator.client.loop.run_until_complete(
            bot_creator.run(bot_name, bot_avatar_path)
        )
