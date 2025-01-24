import os
import time
import requests
from datetime import datetime
from telegram import Bot

# Replace with your bot token
BOT_TOKEN = "8006131622:AAFS8eDDcAnE0lGjtk9ysCKGstd4mwEhQiE"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"


# Function to set the bot's name
def set_bot_name(bot_name):
    url = BASE_URL + "setMyCommands"
    payload = {
        "commands": [
            {"command": "start", "description": "Start interacting with the bot"},
            {"command": "help", "description": "Get help using this bot"},
        ]
    }
    response = requests.post(url, json=payload)
    return response.json()


# Function to set the bot's description
def set_bot_description(description):
    url = BASE_URL + "userProfilePhoto"
    payload = {"description": description}
    response = requests.post(url, json=payload)
    return response.json()


# Function to set the bot's about text
def set_bot_about(about_text):
    url = BASE_URL + "setMyShortDescription"
    payload = {"short_description": about_text}
    response = requests.post(url, json=payload)
    return response.json()


# Function to set the bot's profile picture
def set_bot_profile_picture(photo_path):
    bot = Bot(token=BOT_TOKEN)

    with open(photo_path, "rb") as photo:
        bot.set_user_profile_photo(photo=photo)


# Example usage
def main():
    bot_name = "MyPersonalBot"
    description = "This bot helps you automate tasks and have fun!"
    about_text = "Your friendly personal assistant bot."
    profile_picture_path = (
        "/home/omar.sayed@ad.cyshield/Personal/AI/lotionAI/dev/AI Agents/logo.png"
    )

    # print("Setting bot commands...")
    # print(set_bot_name(bot_name))

    print("Setting bot description...")
    print(set_bot_description(description))

    print("Setting bot about text...")
    print(set_bot_about(about_text))

    print("Setting bot profile picture...")
    print(set_bot_profile_picture(profile_picture_path))


def receive_telegram_message(after_timestamp):
    # TOKEN = os.getenv("TELEGRAM_TOKEN")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    response = requests.get(url).json()
    if not response["result"]:
        return []

    new_messages = []
    for update in response["result"]:
        if "message" in update:
            message = update["message"]
            if message["date"] > after_timestamp:
                new_messages.append(
                    {
                        "text": message["text"],
                        "date": datetime.fromtimestamp(message["date"]).strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                    }
                )

    return new_messages


if __name__ == "__main__":
    main()
    initial_timestamp = int(time.time())
    while True:
        print(receive_telegram_message(initial_timestamp))
