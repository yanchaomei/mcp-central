from crawl4ai import *
from fastmcp import FastMCP

mcp = FastMCP("crawl4ai")


@mcp.tool()
async def crawl4ai(website: str) -> str:
    if not website.startswith('http'):
        website = 'http://' + website
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=website,
            )
            return result.metadata['description']
    except Exception:
        import traceback
        return f'Error: {traceback.format_exc()}'


if __name__ == "__main__":
    mcp.run(transport="stdio")
