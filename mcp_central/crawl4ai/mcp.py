from crawl4ai import *
from fastmcp import FastMCP

mcp = FastMCP("crawl4ai server")


@mcp.tool()
async def crawl4ai(website: str) -> str:
    if not website.startswith('http'):
        website = 'http://' + website
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=website,
        )
        return result.markdown


if __name__ == "__main__":
    mcp.run(transport="stdio")
