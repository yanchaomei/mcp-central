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


@mcp.tool(description='A crawl tool to get the content of a website page, '
                      'and simplify the content to pure html content. This tool can be used to get the detail '
                      'information in the url')
async def crawl4ai(website: str) -> str:
    if not website.startswith('http'):
        website = 'http://' + website
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=website,
            )
            html = trafilatura.extract(str(result.html))
            if not html:
                html = 'Cannot crawl this web page, please try another web page instead'
            return html
    except Exception:
        import traceback
        print(traceback.format_exc())
        return 'Cannot crawl this web page, please try another web page instead'


if __name__ == "__main__":
    mcp.run(transport="stdio")
