import html

import trafilatura
from crawl4ai import *
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.browser_manager import BrowserManager
from fastmcp import FastMCP

mcp = FastMCP("crawl4ai")


async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.close()
    # Fix: https://github.com/unclecode/crawl4ai/issues/842
    BrowserManager._playwright_instance = None


AsyncPlaywrightCrawlerStrategy.__aexit__ = __aexit__


@mcp.tool()
async def crawl4ai(website: str) -> str:
    if not website.startswith('http'):
        website = 'http://' + website
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=website,
            )
            markdown = html.escape(trafilatura.extract(str(result.markdown)))
            return {"content": markdown}
    except Exception:
        import traceback
        return f'Error: {traceback.format_exc()}'


if __name__ == "__main__":
    mcp.run(transport="stdio")
