from __future__ import annotations

# import logging
# from telegram import Update
# from telegram.ext import (
#     ApplicationBuilder,
#     CommandHandler,
#     MessageHandler,
#     filters,
#     ContextTypes,
# )

import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


import asyncio
import logging
import os

from uuid import uuid4
from telegram import BotCommandScopeAllGroupChats, Update, constants
from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQueryResultArticle,
)
from telegram import InputTextMessageContent, BotCommand
from telegram.error import RetryAfter, TimedOut
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    InlineQueryHandler,
    CallbackQueryHandler,
    Application,
    ContextTypes,
    CallbackContext,
)


from connections.telegram.utils import (
    is_group_chat,
    get_thread_id,
    message_text,
    wrap_with_indicator,
    split_into_chunks,
    edit_message_with_retry,
    get_stream_cutoff_values,
    is_allowed,
    get_reply_to_message_id,
    add_chat_request_to_usage_tracker,
    error_handler,
    is_direct_result,
    handle_direct_result,
    cleanup_intermediate_files,
)
from connections.telegram.helper import localized_text


telegram_config = {
    "token": os.environ["TELEGRAM_BOT_TOKEN"],
    "stream": os.environ.get("STREAM", "true").lower() == "true",
    "bot_language": os.environ.get("BOT_LANGUAGE", "en"),
    "enable_quoting": os.environ.get("ENABLE_QUOTING", "true").lower() == "true",
}


class TelegramConnection:
    """
    Class representing a ChatGPT Telegram Bot.
    """

    def __init__(self, agent, config: dict = telegram_config):
        """
        Initializes the bot with the given configuration and GPT bot object.
        :param config: A dictionary containing the bot configuration
        :param openai: OpenAIHelper object
        """
        self.config = config
        self.agent = agent
        bot_language = self.config["bot_language"]
        self.commands = [
            BotCommand(
                command="help",
                description=localized_text("help_description", bot_language),
            ),
            BotCommand(
                command="reset",
                description=localized_text("reset_description", bot_language),
            ),
            BotCommand(
                command="resend",
                description=localized_text("resend_description", bot_language),
            ),
        ]

        self.group_commands = [
            BotCommand(
                command="chat",
                description=localized_text("chat_description", bot_language),
            )
        ] + self.commands
        self.disallowed_message = localized_text("disallowed", bot_language)
        self.budget_limit_message = localized_text("budget_limit", bot_language)
        self.usage = {}
        self.last_message = {}
        self.inline_queries_cache = {}

    async def help(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Shows the help menu.
        """
        commands = self.group_commands if is_group_chat(update) else self.commands
        commands_description = [
            f"/{command.command} - {command.description}" for command in commands
        ]
        bot_language = self.config["bot_language"]
        help_text = (
            localized_text("help_text", bot_language)[0]
            + "\n\n"
            + "\n".join(commands_description)
        )
        await update.message.reply_text(help_text, disable_web_page_preview=True)

    async def resend(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Resend the last request
        """
        if not await is_allowed(self.config, update, context):
            logging.warning(
                f"User {update.message.from_user.name}  (id: {update.message.from_user.id})"
                f" is not allowed to resend the message"
            )
            await self.send_disallowed_message(update, context)
            return

        chat_id = update.effective_chat.id
        if chat_id not in self.last_message:
            logging.warning(
                f"User {update.message.from_user.name} (id: {update.message.from_user.id})"
                f" does not have anything to resend"
            )
            await update.effective_message.reply_text(
                message_thread_id=get_thread_id(update),
                text=localized_text("resend_failed", self.config["bot_language"]),
            )
            return

        # Update message text, clear self.last_message and send the request to prompt
        logging.info(
            f"Resending the last prompt from user: {update.message.from_user.name} "
            f"(id: {update.message.from_user.id})"
        )
        with update.message._unfrozen() as message:
            message.text = self.last_message.pop(chat_id)

        await self.prompt(update=update, context=context)

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Resets the conversation.
        """
        if not await is_allowed(self.config, update, context):
            logging.warning(
                f"User {update.message.from_user.name} (id: {update.message.from_user.id}) "
                f"is not allowed to reset the conversation"
            )
            await self.send_disallowed_message(update, context)
            return

        logging.info(
            f"Resetting the conversation for user {update.message.from_user.name} "
            f"(id: {update.message.from_user.id})..."
        )

        chat_id = update.effective_chat.id
        reset_content = message_text(update.message)
        self.openai.reset_chat_history(chat_id=chat_id, content=reset_content)
        await update.effective_message.reply_text(
            message_thread_id=get_thread_id(update),
            text=localized_text("reset_done", self.config["bot_language"]),
        )

    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        React to incoming messages and respond accordingly.
        """
        print(update)
        if update.edited_message or not update.message or update.message.via_bot:
            return

        print(
            f"New message received from user {update.message.from_user.name} (id: {update.message.from_user.id})"
        )
        user_name = update.message.from_user.name
        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id
        prompt = message_text(update.message)
        self.last_message[chat_id] = prompt

        if is_group_chat(update):
            trigger_keyword = "@test_lotion_bot"

            if prompt.lower().startswith(
                trigger_keyword.lower()
            ) or update.message.text.lower().startswith("/chat"):
                if prompt.lower().startswith(trigger_keyword.lower()):
                    prompt = prompt[len(trigger_keyword) :].strip()

                if (
                    update.message.reply_to_message
                    and update.message.reply_to_message.text
                    and update.message.reply_to_message.from_user.id != context.bot.id
                ):
                    prompt = f'"{update.message.reply_to_message.text}" {prompt}'
            else:
                if (
                    update.message.reply_to_message
                    and update.message.reply_to_message.from_user.id == context.bot.id
                ):
                    logging.info("Message is a reply to the bot, allowing...")
                else:
                    logging.warning(
                        "Message does not start with trigger keyword, ignoring..."
                    )
                    return

        try:
            total_tokens = 0

            # if False:
            if self.config["stream"]:
                await update.effective_message.reply_chat_action(
                    action=constants.ChatAction.TYPING,
                    message_thread_id=get_thread_id(update),
                )
                stream_response = await self.agent.stream_execute(
                    session_id=str(f"telegram_{user_name}_{user_id}_{chat_id}"),
                    prompt=prompt,
                )
                i = 0
                prev = ""
                sent_message = None
                backoff = 0
                stream_chunk = 0
                all_content = ""
                async for msg, metadata in stream_response:
                    content = msg.content
                    if metadata["langgraph_node"] != "tools":
                        tokens = msg.usage_metadata["input_tokens"]
                    else:
                        continue
                    if is_direct_result(content):
                        return await handle_direct_result(self.config, update, content)

                    if len(content.strip()) == 0:
                        continue

                    stream_chunks = split_into_chunks(content)
                    if len(stream_chunks) > 1:
                        content = stream_chunks[-1]
                        if stream_chunk != len(stream_chunks) - 1:
                            stream_chunk += 1
                            try:
                                await edit_message_with_retry(
                                    context,
                                    chat_id,
                                    str(sent_message.message_id),
                                    stream_chunks[-2],
                                )
                            except:
                                pass
                            try:
                                all_content += content
                                sent_message = (
                                    await update.effective_message.reply_text(
                                        message_thread_id=get_thread_id(update),
                                        text=all_content if len(content) > 0 else "...",
                                    )
                                )
                            except:
                                pass
                            continue

                    cutoff = get_stream_cutoff_values(update, content)
                    cutoff += backoff

                    if i == 0:
                        try:
                            if sent_message is not None:
                                await context.bot.delete_message(
                                    chat_id=sent_message.chat_id,
                                    message_id=sent_message.message_id,
                                )
                            sent_message = await update.effective_message.reply_text(
                                message_thread_id=get_thread_id(update),
                                reply_to_message_id=get_reply_to_message_id(
                                    self.config, update
                                ),
                                text=content,
                            )
                            all_content += content
                        except:
                            continue

                    elif (
                        abs(len(content) - len(prev)) > cutoff
                        or tokens != "not_finished"
                    ):
                        prev = content
                        all_content += content
                        try:
                            use_markdown = tokens != "not_finished"
                            await edit_message_with_retry(
                                context,
                                chat_id,
                                str(sent_message.message_id),
                                text=all_content,
                                markdown=True,
                            )

                        except RetryAfter as e:
                            backoff += 5
                            await asyncio.sleep(e.retry_after)
                            continue

                        except TimedOut:
                            backoff += 5
                            await asyncio.sleep(0.5)
                            continue

                        except Exception:
                            backoff += 5
                            continue

                        await asyncio.sleep(0.01)

                    i += 1
                    if tokens != "not_finished":
                        total_tokens = int(tokens)

            else:

                async def _reply():
                    nonlocal total_tokens
                    response, total_tokens = (
                        await self.agent.prompt_llm(
                            session_id=str(f"telegram_{user_name}_{user_id}_{chat_id}"),
                            prompt=prompt,
                        ),
                        10,
                    )

                    if is_direct_result(response):
                        return await handle_direct_result(self.config, update, response)

                    # Split into chunks of 4096 characters (Telegram's message limit)
                    chunks = split_into_chunks(response)

                    for index, chunk in enumerate(chunks):
                        try:
                            await update.effective_message.reply_text(
                                message_thread_id=get_thread_id(update),
                                reply_to_message_id=(
                                    get_reply_to_message_id(self.config, update)
                                    if index == 0
                                    else None
                                ),
                                text=chunk,
                                parse_mode=constants.ParseMode.MARKDOWN,
                            )
                        except Exception:
                            try:
                                await update.effective_message.reply_text(
                                    message_thread_id=get_thread_id(update),
                                    reply_to_message_id=(
                                        get_reply_to_message_id(self.config, update)
                                        if index == 0
                                        else None
                                    ),
                                    text=chunk,
                                )
                            except Exception as exception:
                                raise exception

                await wrap_with_indicator(
                    update, context, _reply, constants.ChatAction.TYPING
                )

            add_chat_request_to_usage_tracker(
                self.usage, self.config, user_id, total_tokens
            )

        except Exception as e:
            logging.exception(e)
            await update.effective_message.reply_text(
                message_thread_id=get_thread_id(update),
                reply_to_message_id=get_reply_to_message_id(self.config, update),
                text=f"{localized_text('chat_fail', self.config['bot_language'])} {str(e)}",
                parse_mode=constants.ParseMode.MARKDOWN,
            )

    async def inline_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle the inline query. This is run when you type: @botusername <query>
        """
        query = update.inline_query.query
        if len(query) < 3:
            return
        callback_data_suffix = "gpt:"
        result_id = str(uuid4())
        self.inline_queries_cache[result_id] = query
        callback_data = f"{callback_data_suffix}{result_id}"

        await self.send_inline_query_result(
            update, result_id, message_content=query, callback_data=callback_data
        )

    async def send_inline_query_result(
        self, update: Update, result_id, message_content, callback_data=""
    ):
        """
        Send inline query result
        """
        try:
            reply_markup = None
            bot_language = self.config["bot_language"]
            if callback_data:
                reply_markup = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=f'🤖 {localized_text("answer_with_chatgpt", bot_language)}',
                                callback_data=callback_data,
                            )
                        ]
                    ]
                )

            inline_query_result = InlineQueryResultArticle(
                id=result_id,
                title=localized_text("ask_chatgpt", bot_language),
                input_message_content=InputTextMessageContent(message_content),
                description=message_content,
                thumb_url="https://user-images.githubusercontent.com/11541888/223106202-7576ff11-2c8e-408d-94ea"
                "-b02a7a32149a.png",
                reply_markup=reply_markup,
            )

            await update.inline_query.answer([inline_query_result], cache_time=0)
        except Exception as e:
            logging.error(
                f"An error occurred while generating the result card for inline query {e}"
            )

    async def handle_callback_inline_query(
        self, update: Update, context: CallbackContext
    ):
        """
        Handle the callback query from the inline query result
        """
        callback_data = update.callback_query.data
        user_id = update.callback_query.from_user.id
        inline_message_id = update.callback_query.inline_message_id
        name = update.callback_query.from_user.name
        callback_data_suffix = "gpt:"
        query = ""
        bot_language = self.config["bot_language"]
        answer_tr = localized_text("answer", bot_language)
        loading_tr = localized_text("loading", bot_language)

        try:
            if callback_data.startswith(callback_data_suffix):
                unique_id = callback_data.split(":")[1]
                total_tokens = 0

                # Retrieve the prompt from the cache
                query = self.inline_queries_cache.get(unique_id)
                if query:
                    self.inline_queries_cache.pop(unique_id)
                else:
                    error_message = (
                        f'{localized_text("error", bot_language)}. '
                        f'{localized_text("try_again", bot_language)}'
                    )
                    await edit_message_with_retry(
                        context,
                        chat_id=None,
                        message_id=inline_message_id,
                        text=f"{query}\n\n_{answer_tr}:_\n{error_message}",
                        is_inline=True,
                    )
                    return

                unavailable_message = localized_text(
                    "function_unavailable_in_inline_mode", bot_language
                )
                if self.config["stream"]:
                    stream_response = self.openai.get_chat_response_stream(
                        chat_id=user_id, query=query
                    )
                    i = 0
                    prev = ""
                    backoff = 0
                    async for content, tokens in stream_response:
                        if is_direct_result(content):
                            cleanup_intermediate_files(content)
                            await edit_message_with_retry(
                                context,
                                chat_id=None,
                                message_id=inline_message_id,
                                text=f"{query}\n\n_{answer_tr}:_\n{unavailable_message}",
                                is_inline=True,
                            )
                            return

                        if len(content.strip()) == 0:
                            continue

                        cutoff = get_stream_cutoff_values(update, content)
                        cutoff += backoff

                        if i == 0:
                            try:
                                await edit_message_with_retry(
                                    context,
                                    chat_id=None,
                                    message_id=inline_message_id,
                                    text=f"{query}\n\n{answer_tr}:\n{content}",
                                    is_inline=True,
                                )
                            except:
                                continue

                        elif (
                            abs(len(content) - len(prev)) > cutoff
                            or tokens != "not_finished"
                        ):
                            prev = content
                            try:
                                use_markdown = tokens != "not_finished"
                                divider = "_" if use_markdown else ""
                                text = f"{query}\n\n{divider}{answer_tr}:{divider}\n{content}"

                                # We only want to send the first 4096 characters. No chunking allowed in inline mode.
                                text = text[:4096]

                                await edit_message_with_retry(
                                    context,
                                    chat_id=None,
                                    message_id=inline_message_id,
                                    text=text,
                                    markdown=use_markdown,
                                    is_inline=True,
                                )

                            except RetryAfter as e:
                                backoff += 5
                                await asyncio.sleep(e.retry_after)
                                continue
                            except TimedOut:
                                backoff += 5
                                await asyncio.sleep(0.5)
                                continue
                            except Exception:
                                backoff += 5
                                continue

                            await asyncio.sleep(0.01)

                        i += 1
                        if tokens != "not_finished":
                            total_tokens = int(tokens)

                else:

                    async def _send_inline_query_response():
                        nonlocal total_tokens
                        # Edit the current message to indicate that the answer is being processed
                        await context.bot.edit_message_text(
                            inline_message_id=inline_message_id,
                            text=f"{query}\n\n_{answer_tr}:_\n{loading_tr}",
                            parse_mode=constants.ParseMode.MARKDOWN,
                        )

                        logging.info(f"Generating response for inline query by {name}")
                        response, total_tokens = await self.openai.get_chat_response(
                            chat_id=user_id, query=query
                        )

                        if is_direct_result(response):
                            cleanup_intermediate_files(response)
                            await edit_message_with_retry(
                                context,
                                chat_id=None,
                                message_id=inline_message_id,
                                text=f"{query}\n\n_{answer_tr}:_\n{unavailable_message}",
                                is_inline=True,
                            )
                            return

                        text_content = f"{query}\n\n_{answer_tr}:_\n{response}"

                        # We only want to send the first 4096 characters. No chunking allowed in inline mode.
                        text_content = text_content[:4096]

                        # Edit the original message with the generated content
                        await edit_message_with_retry(
                            context,
                            chat_id=None,
                            message_id=inline_message_id,
                            text=text_content,
                            is_inline=True,
                        )

                    await wrap_with_indicator(
                        update,
                        context,
                        _send_inline_query_response,
                        constants.ChatAction.TYPING,
                        is_inline=True,
                    )

                add_chat_request_to_usage_tracker(
                    self.usage, self.config, user_id, total_tokens
                )

        except Exception as e:
            logging.error(
                f"Failed to respond to an inline query via button callback: {e}"
            )
            logging.exception(e)
            localized_answer = localized_text("chat_fail", self.config["bot_language"])
            await edit_message_with_retry(
                context,
                chat_id=None,
                message_id=inline_message_id,
                text=f"{query}\n\n_{answer_tr}:_\n{localized_answer} {str(e)}",
                is_inline=True,
            )

    async def send_disallowed_message(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE, is_inline=False
    ):
        """
        Sends the disallowed message to the user.
        """
        if not is_inline:
            await update.effective_message.reply_text(
                message_thread_id=get_thread_id(update),
                text=self.disallowed_message,
                disable_web_page_preview=True,
            )
        else:
            result_id = str(uuid4())
            await self.send_inline_query_result(
                update, result_id, message_content=self.disallowed_message
            )

    async def post_init(self, application: Application) -> None:
        """
        Post initialization hook for the bot.
        """
        await application.bot.set_my_commands(
            self.group_commands, scope=BotCommandScopeAllGroupChats()
        )
        await application.bot.set_my_commands(self.commands)

    def run(self):
        """
        Runs the bot indefinitely until the user presses Ctrl+C
        """
        application = (
            ApplicationBuilder()
            .token(self.config["token"])
            .post_init(self.post_init)
            .concurrent_updates(True)
            .build()
        )

        application.add_handler(CommandHandler("reset", self.reset))
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(CommandHandler("start", self.help))
        application.add_handler(CommandHandler("resend", self.resend))
        application.add_handler(
            CommandHandler(
                "chat",
                self.prompt,
                filters=filters.ChatType.GROUP | filters.ChatType.SUPERGROUP,
            )
        )
        application.add_handler(
            MessageHandler(filters.TEXT & (~filters.COMMAND), self.prompt)
        )
        application.add_handler(
            InlineQueryHandler(
                self.inline_query,
                chat_types=[
                    constants.ChatType.GROUP,
                    constants.ChatType.SUPERGROUP,
                    constants.ChatType.PRIVATE,
                ],
            )
        )
        application.add_handler(CallbackQueryHandler(self.handle_callback_inline_query))

        application.add_error_handler(error_handler)

        application.run_polling()
