import asyncio
import argparse
import os
from datetime import datetime
from base import MCPClient


class LiteResearchMCPClient(MCPClient):
    default_system = f"""You are an assistant that helps generate comprehensive documnetations or webpages from gathered information. Today is {datetime.now().strftime("%Y-%m-%d")}.

## Planning

You need to create a CONCISE, FOCUSED plan with ONLY meaningful, actionable steps, rely on the plan after you made it.

If you are making website, just make one single step for writing code to avoid too much messages.

Give your final result(documentation/code) in <result></result> block.

Here shows a plan example:

 ```
1. Research & Content Gathering:
   1.1. Search and collect comprehensive information on [topic] using user's language
   1.2. Identify and crawl authoritative sources for detailed content
   1.3. Crawl enough high-quality medias(e.g. image links) from compatible platforms

2. Content Creation & Organization:
   2.1. Develop main content sections with complete information
   2.3. Organize information with logical hierarchy and flow

3. Design & Animation Implementation:
   3.1. Create responsive layout with modern aesthetic, with all the useful information collected
   3.2. Implement key animations for enhanced user experience
   3.3. Write the final code...
```

History messages of the previous main step will not be kept, so you need to WRITE a concise but essential summary_and_result when calling `notebook---advance_to_next_step` for each sub-step.
In the later steps, you can only see the plans you made and the summary_and_result from the previous steps. So you must MINIMIZE DEPENDENCIES between the the steps in the plan.

Here shows a summary_and_result example:
```
MAIN FINDINGS:
• Topic X has three primary categories: A, B, and C
• Latest statistics show 45% increase in adoption since 2023
• Expert consensus indicates approach Y is most effective

COLLECTED RESOURCES:
• Primary source: https://example.com/comprehensive-guide (contains detailed sections on implementation)
• Images: ["https://example.com/image1.jpg", "https://example.com/image2.jpg", "https://example.com/diagram.png"]
• Reference documentation: https://docs.example.com/api (sections 3.2-3.4 particularly relevant)

DECISIONS MADE:
• Will focus on mobile-first approach due to 78% of users accessing via mobile devices
• Selected blue/green color scheme based on industry standards and brand compatibility
• Decided to implement tabbed interface for complex data presentation

CODE:
```
...
```
"""


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_url", type=str, default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    parser.add_argument("--model", type=str, default="claude-3-7-sonnet-20250219")
    parser.add_argument("--token", type=str, default="")
    args = parser.parse_args()
    if not args.token:
        args.token = os.environ.get('MODEL_TOKEN', '')
    client = LiteResearchMCPClient(base_url=args.base_url, token=args.token, model=args.model,
                                   mcp=['crawl4ai', 'notebook', 'web-search', 'edgeone-pages-mcp-server'])
    try:
        user_input = input('>>> Please input your query:')
        await client.connect_all_servers(None)
        async for response in client.process_query(None, user_input, system=True):
            print(response)
            print('\n')
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
