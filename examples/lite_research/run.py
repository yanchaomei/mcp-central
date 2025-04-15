import asyncio
import argparse
import os
from datetime import datetime
from examples.lite_research.base import MCPClient


class LiteResearchMCPClient(MCPClient):

    default_system = f"""You are an assistant that helps me generate summary reports based on webpage information, today is {datetime.now().strftime("%Y-%m-%d")}. You can utilize various tools and call the appropriate tools at the appropriate times.

Among the tools you select, you must include at least the following tools:

1. **Web search tool**, used to find corresponding information from search engines.

2. **Web scraping tool**, used to obtain specific content from web pages, but you need to pay attention to **the timeliness and authenticity of the information on the web page**.

3. **Plan-making tool (planer)**, used to break down, check, and redo plans if necessary, and output your report before finally calling `task_done`.

You need to perform at least the following steps (and can perform more steps to complete the task more meticulously):

1. Analyze based on the user's question, provide the conditions required to meet the user's needs, and the aspects of information that need to be collected, and call planer to store the analysis results.

2. Break down the steps based on the user's question, forming a **detailed** plan list, and call planer to manage your steps. You can **further break down the steps into sub-steps**.

3. If you call tools, please give the reason and the reasoning for calling them.

4. Use the content obtained from web search, and summarize it into article paragraphs based on your understanding, give a report satisfies the user requirements before calling `task_done`."""


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_url", type=str, default="https://api-inference.modelscope.cn/v1")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-72B-Instruct")
    parser.add_argument("--token", type=str)
    args = parser.parse_args()
    if not args.token:
        args.token = os.environ.get('MODEL_TOKEN', '')
    client = LiteResearchMCPClient(base_url=args.base_url, token=args.token, model=args.model,
                                   mcp=['crawl4ai', 'planer', 'web-search'])
    try:
        user_input = input('>>> Please input your query:')
        # user_input = 'Please give me some interesting stories in the Dify company, and summarize to a 5000 words report'
        await client.connect_all_servers(None)
        async for response in client.process_query(None, user_input):
            print(response)
            print('\n')
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
