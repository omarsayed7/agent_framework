from functools import cache
from typing import TypeAlias

from langchain_community.tools import (
    DuckDuckGoSearchRun,
    TavilySearchResults,
)


_WEBSEARCH_TABLE = {
    "tavily": TavilySearchResults,
    "duck": DuckDuckGoSearchRun,
}

WebSearchT: TypeAlias = DuckDuckGoSearchRun | TavilySearchResults


@cache
def get_websearch_tool(websearch_tool: str) -> WebSearchT:
    WebSearchRef = _WEBSEARCH_TABLE.get("duck")
    return WebSearchRef()
