from pydantic import BaseModel, Field


class TelegramBotInfo(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    username: str
    can_join_groups: bool
    can_read_all_group_messages: bool
    supports_inline_queries: bool
