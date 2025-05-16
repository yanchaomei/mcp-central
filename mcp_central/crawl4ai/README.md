# Crawl4AI MCP

This is a mcp tool for [crawl4ai](https://github.com/unclecode/crawl4ai). You can use this tool to crawl a website and get its useful content.

What we do:

1. Use crawler.arun to fetch a url.
2. Use trafilatura to simplify the result html, if the content length is larger then 2048, clip it to 2048.
3. If there are media in the page, construct a dict payload to carry the media information. Each media link will match a description with the max length 100.

## Installation

```shell
pip install -r requirements.txt
crawl4ai-setup
crawl4ai-doctor
```

## MCP config:

```json
{
  "mcpServers": {
    "crawl4ai": {
      "command": "/path/to/fastmcp",
      "args": [
        "run",
        "/path/to/crawl4ai/server.py"
      ]
    }
  }
}
```

You can add this config to your chatbot or agent config files to use crawl4ai-mcp.

## Function

- crawl_website: A crawl tool to get the content of a website page, and simplify the content to pure html content. This tool can be used to get the detail information in the url.
  - Input: 
    - website(str): The website url.
    - Output:
      - A dict containing the website content.
    
          ```json
              {
                "text": "the html content",
                "media": [
                    {
                        "type": "image/video/audio",
                        "description": "A picture with the west lake inside it.",
                        "link": "https://xxx"
                    },
                    ...
                ]
              }   
          ```