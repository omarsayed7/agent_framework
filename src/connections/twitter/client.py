# import asyncio
import os
import asyncio
from twikit import Client
from twikit.utils import build_query
from dotenv import load_dotenv

load_dotenv()

# USERNAME = "os.environ.get("TWITTER_USERNAME")
# EMAIL = os.environ.get("TWITTER_EMAIL")
# PASSWORD = os.environ.get("TWITTER_PASSWORD")

# # Initialize client
# client = Client("en-US")


# async def main():
#     await client.login(auth_info_1=USERNAME, auth_info_2=EMAIL, password=PASSWORD)
#     print(await client.get_trends("trending"))
#     # Create a tweet with the provided text and attached media
#     await client.create_tweet(text="Example Tweet")


# asyncio.run(main())


class AsyncTwitterBot:
    def __init__(
        self, username: str, email: str, password: str, session_cookie: dict = None
    ):
        self.client = Client("en-US")
        self.credentials = {
            "username": username,
            "email": email,
            "password": password,
            "session_cookie": session_cookie,
        }

    async def initialize(self):
        """Async initialization with authentication"""
        if self.credentials["session_cookie"]:
            self.client.set_session_cookies(self.credentials["session_cookie"])
        else:
            print("creds", self.credentials)
            await self.client.login(
                auth_info_1=self.credentials["username"],
                auth_info_2=self.credentials["email"],
                password=self.credentials["password"],
            )

    async def post_tweet(
        self, text: str, media_path: str = None, media_type: str = "image/png"
    ) -> str:
        """Post a tweet with optional media attachment"""
        media_ids = []

        if media_path:
            print("media")
            media_id = await self.client.upload_media(media_path)
            media_ids.append(media_id)

        tweet = await self.client.create_tweet(text=text, media_ids=media_ids)
        print(tweet, "tweet")
        return tweet.id

    async def reply_to_tweet(
        self, tweet_id: str, text: str, media_path: str = None
    ) -> str:
        """Reply to a specific tweet"""
        media_ids = []

        if media_path:
            media = await self.client.upload_media(media_path, "image/jpeg")
            media_ids.append(media.media_id)
        tweet = await self.client.get_tweet_by_id(tweet_id)
        reply = await tweet.reply(text=text, media_ids=media_ids)
        return reply.id

    async def like_tweet(self, tweet_id: str) -> bool:
        """Like a specific tweet"""
        tweet = await self.client.get_tweet_by_id(tweet_id)
        await tweet.favorite()
        return True


# Async usage example
async def main():
    # Initialize bot with your credentials
    bot = AsyncTwitterBot(
        username=os.environ.get("TWITTER_USERNAME"),
        email=os.environ.get("TWITTER_EMAIL"),
        password=os.environ.get("TWITTER_PASSWORD"),
    )
    await bot.initialize()

    # Example usage
    try:
        # # Post a regular tweet
        # new_tweet_id = await bot.post_tweet("Hello Async Twitter!")
        # print(new_tweet_id)
        # Post a tweet with image
        media_tweet_id = await bot.post_tweet(
            "Check this out!",
            "/home/omar.sayed@ad.cyshield/Personal/AI/lotionAI/dev//tt.jpeg",
        )

        # Reply to a tweet
        reply_id = await bot.reply_to_tweet("1697744920366256128", "Great point!")

        # Like a tweet
        await bot.like_tweet("1697744920366256128")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
