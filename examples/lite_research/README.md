## A Lite research tool with pure mcp tools:

- A plan tool to PUA model do the right thing
- A crawler
- A web-searcher

## Installation

The [web-search tool](https://www.modelscope.cn/mcp/servers/@tavily-ai/tavily-mcp) need an API key, please get here:

https://app.tavily.com/home

```shell
cd examples/lite_research
sh requirements.sh
```

## How-to-use

CLI:

```shell
cd examples/lite_research
TAVILY_API_KEY=xxx python run.py --token xxx --model Qwen/Qwen2.5-72B-Instruct --base_url https://api-inference.modelscope.cn/v1
```

UI:

```shell
cd examples/lite_research
MODEL_TOKEN=xxx TAVILY_API_KEY=xxx python app.py
```