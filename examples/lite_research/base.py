import inspect
import json
import os
import re
import shutil
import time
from contextlib import AsyncExitStack
from typing import Dict, List, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from openai.types.chat import ChatCompletion


class MCPClient:
    default_system = ('You are an assistant which helps me to finish a complex job. Tools may be given to you '
                      'and you must choose some of them one per round to finish my request.')

    connector = '\n\nHere gives the user query:\n\n'

    def __init__(self, base_url, token, model, mcp):
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.current_server = None
        self.token = token
        self.model = model
        self.base_url = base_url
        self.mcp = mcp
        self.client = OpenAI(
            api_key=self.token,
            base_url=self.base_url,
        )

    def generate_response(self, messages, model, tools=None, **kwargs) -> ChatCompletion:
        time.sleep(0.5)
        if tools:
            tools = [
                {
                    'type': 'function',
                    'function': {
                        'name': tool['name'],
                        'description': tool['description'],
                        'parameters': tool['input_schema']
                    }
                } for tool in tools
            ]

        _e = None
        completion = None
        parameters = inspect.signature(self.client.chat.completions.create).parameters
        kwargs = {key: value for key, value in kwargs.items() if key in parameters}
        for i in range(20):
            try:
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    parallel_tool_calls=False,
                    **kwargs
                )
                _e = None
                break
            except Exception as e:
                print(str(e))
                _e = e
                time.sleep(20)
                continue
        if _e:
            raise _e
        return completion

    @staticmethod
    def generate_config(mcp_servers: List[str]) -> Dict[str, Any]:
        mcp_path = os.path.abspath('../../')
        if not mcp_servers:
            for base_dir, dirs, files in os.walk('../../mcp_central'):
                mcp_servers = dirs
                break
        config_json = {}
        for mcp_server in mcp_servers:
            mcp_abs_path = os.path.join(mcp_path, 'mcp_central', mcp_server)
            config_file = os.path.join(mcp_abs_path, 'config.json')
            if not os.path.exists(config_file):
                continue
            with open(config_file, 'r') as f:
                content = json.load(f)
                mcp_content = content[mcp_server]
                command = mcp_content['command']
                if 'fastmcp' in command:
                    command = shutil.which("fastmcp")
                    if not command:
                        raise FileNotFoundError(f'Cannot locate the fastmcp command file, '
                                                f'please install fastmcp by `pip install fastmcp`')
                    mcp_content['command'] = command
                if 'uv' in command:
                    command = shutil.which("uv")
                    if not command:
                        raise FileNotFoundError(f'Cannot locate the uv command, '
                                                f'please consider your installation of Python.')

                args = mcp_content['args']
                for idx in range(len(args)):
                    if 'server.py' in args[idx]:
                        args[idx] = os.path.join(mcp_abs_path, 'server.py')
            config_json[mcp_server] = mcp_content

        if os.path.exists('./config.json'):
            with open('./config.json', 'r') as f:
                content = json.load(f)
                for key, value in content['mcpServers'].items():
                    config_json[key] = value

        return config_json

    async def connect_to_server(self, command, args, env=None, server_name: str = None):
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )

        await session.initialize()

        # Store session
        self.sessions[server_name] = session

        # Set as current if it's the first one
        if self.current_server is None:
            self.current_server = server_name

        # List available tools
        response = await session.list_tools()
        tools = response.tools
        print(f"\nConnected to server '{server_name}' with tools:", [tool.name for tool in tools])

        return server_name

    async def switch_server(self, server_name: str):
        """Switch to a different connected server"""
        if server_name not in self.sessions:
            raise ValueError(f"Server '{server_name}' not connected. Available servers: {list(self.sessions.keys())}")

        self.current_server = server_name
        print(f"Switched to server: {server_name}")

        # List available tools on current server
        response = await self.sessions[server_name].list_tools()
        tools = response.tools
        print(f"Available tools:", [tool.name for tool in tools])

    async def list_servers(self):
        """List all connected servers"""
        if not self.sessions:
            print("No servers connected")
            return

        print("\nConnected servers:")
        for name in self.sessions.keys():
            marker = "* " if name == self.current_server else "  "
            print(f"{marker}{name}")

    def summary(self, query, content, **kwargs):
        prompt = """Based on the query: "{query}", filter this content to keep only the most relevant information.

Your task is to:
1. Mandatory: Retain ALL information directly relevant to the query
2. Mandatory: Keep URLs and links that provide useful resources related to the query
3. Mandatory: Filter out URLs and content that are not helpful for addressing the query
4. Mandatory: Preserve technical details, specifications, and instructions related to the query
5. Mandatory: Maintain the connection between relevant information and its corresponding URLs

Format your response as a JSON object without code block markers, containing:
- "title": A descriptive title reflecting the query focus (5-12 words)
- "summary": Filtered content with only query-relevant information and URLs
- "status": "success" if the content is relevant to the query, "error" if the content is irrelevant or contains incorrect information

Content to process:
{content}

Filtering guidelines:
- Keep URLs that provide resources, tools, downloads, or information directly related to the query
- Remove URLs to general pages, social media, promotional content, or unrelated material
- Keep all technical specifications, code samples, or detailed instructions that address the query
- Preserve product names, model numbers, and version information relevant to the query
- Remove generic content, filler text, or background information that doesn't help answer the query
- When evaluating a URL, consider where it leads and whether that destination would help someone with this query

Error detection guidelines:
- Set "status" to "error" if the content appears to be in a different language than expected
- Set "status" to "error" if the content is about a completely different topic than the query (e.g., query about technology but content about tourism)
- Set "status" to "error" if the content contains obvious factual errors or contradictions
- Set "status" to "error" if URLs lead to unrelated content like tourism sites when querying for technical information
- Set "status" to "error" if the content appears to be machine-translated or unintelligible
- When setting "status" to "error", include a brief explanation in the summary field

The goal is intelligent filtering with error detection - keeping all information and links that would be valuable for someone with this specific query, while removing everything else and flagging irrelevant or incorrect content.
DO NOT add any other parts like ```json which may cause parse error of json."""

        query = prompt.replace("{query}", query).replace("{content}", content)
        messages = [{'role': 'user', 'content': query}]
        if len(query) < 80000:
            response = self.generate_response(messages, self.model, **kwargs)
            content = response.choices[0].message.content
        else:
            content = 'Content too long, you need to try another website or search another keyword'
        return content

    async def process_query(self, default_system, query: str, system=True, **kwargs) -> str:
        if not default_system:
            default_system = self.default_system
        if system:
            messages = [{'role': 'system', 'content': default_system}, {"role": "user", "content": query}]
        else:
            messages = [{"role": "user", "content": default_system + self.connector + query}]
        tools = []
        for key, session in self.sessions.items():
            if key == 'edgeone-pages-mcp-server':
                continue
            response = await session.list_tools()
            available_tools = [
                {
                    "name": key + '---' + tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in response.tools if tool.name not in ('tavily-extract')
            ]
            tools.extend(available_tools)

        task_done_cnt = 0
        final_result = ''
        result_section = False
        while True:
            response = self.generate_response(messages, self.model, tools=tools, **kwargs)
            message = response.choices[0].message
            try:
                reasoning = message.model_extra['reasoning_content']
            except:
                reasoning = ''
            content = reasoning + (message.content or '')
            if '<task_done>' in content or task_done_cnt >= 4:
                break
            if '<result>' in content and '</result>' in content:
                pattern = r"<result>(.*?)</result>"
                final_result = re.findall(pattern, content, re.DOTALL)
            elif '<result>' in content:
                result_section = True
                final_result += content.split('<result>')[1]
            elif '</result>' in content:
                final_result += content.split('</result>')[0]
                result_section = False
            elif result_section:
                final_result += content
            if content.strip() or message.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": content.strip(),
                    'tool_calls': message.tool_calls if not message.tool_calls else [message.tool_calls[0]],
                })
            if message.tool_calls:
                for tool in message.tool_calls:
                    try:
                        name = tool.function.name
                        args = tool.function.arguments
                        if name == 'advance_to_next_step':
                            name = 'notebook---advance_to_next_step'
                        key, tool_name = name.split('---')
                        args = json.loads(args)
                        if tool.function.name == 'notebook---initialize_task':
                            user_query = args.get('user_query', '')
                            user_query = user_query.split(self.connector)
                            if len(user_query) > 1:
                                user_query = user_query[1]
                                args['user_query'] = user_query
                        elif tool.function.name == 'notebook---verify_task_completion':
                            task_done_cnt += 1
                        if 'advance_to_next_step' in tool.function.name:
                            start = 1
                            _messages = [messages[0]]
                            if messages[0]['role'] == 'system':
                                start = 2
                                _messages.append(messages[1])
                            for i in range(start, len(messages)-1, 2):
                                resp = messages[i]
                                qry = messages[i+1]
                                if resp.get('tool_calls') and 'advance_to_next_step' in resp['tool_calls'][0].function.name:
                                    continue
                                _messages.append(resp)
                                _messages.append(qry)
                            if _messages[-1] is not messages[-1]:
                                _messages.append(messages[-1])
                            messages = _messages

                        # if tool.function.name == 'notebook---store_intermediate_results':
                        #     args['data'] = messages[-2]['content']
                        #     tool.function.arguments = 'Arguments removed to brief context.'
                        if tool.function.name == 'web-search---tavily-search':
                            args['include_domains'] = []
                            args['include_raw_content'] = False
                        result = await self.sessions[key].call_tool(tool_name, args)
                        # if len(result.content[0].text) > 20000:
                        #     result.content[0].text += ('\n\nContent too long, '
                        #                                'Call notebook---store_intermediate_results to summarize.')
                        tool_result = (result.content[0].text or '').strip()
                        if key in ('web-search'):
                            _args: dict = self.summary(query, tool_result, **kwargs)
                            _print_origin_result = tool_result
                            if len(_print_origin_result) > 512:
                                _print_origin_result = _print_origin_result[:512] + '...'
                            print(tool_name, args, _print_origin_result)
                            tool_result = str(_args)
                        # if tool.function.name == 'notebook---store_intermediate_results':
                        #     messages[-2]['content'] = f'Tool result cached to notebook with title: {args["title"]}'
                        if 'advance_to_next_step' in tool.function.name:
                            content_and_system = json.loads(tool_result)
                            tool_result = content_and_system[0]
                            system = content_and_system[1]
                            if 'Previous main task done' in tool_result:
                                _messages = [messages[0]]
                                if messages[0]['role'] == 'system':
                                    _messages.append(messages[1])
                                messages = _messages
                            if 'Previous main task done' in tool_result:
                                messages.append({
                                    'role': 'user',
                                    'content': tool_result,
                                })
                            else:
                                messages.append({
                                    'role': 'tool',
                                    'content': tool_result,
                                    'tool_call_id': tool.id,
                                })
                        else:
                            messages.append({
                                'role': 'tool',
                                'content': tool_result,
                                'tool_call_id': tool.id,
                            })
                        _print_result = tool_result  # result.content[0].text or ''
                        yield f'{content}\n\n tool call: {name}, {args}\n\n tool result: {_print_result}'
                    except Exception as e:
                        import traceback
                        print(traceback.format_exc())
                        messages.append({
                            'role': 'tool',
                            'content': f'Tool {name} called with error: ' + str(e),
                            'tool_call_id': tool.id,
                        })
                    print(f'messages len: {len(str(messages))}')
                    break
            else:
                if content:
                    yield content
                continue

        print(final_result)
        if 'edgeone-pages-mcp-server' in self.sessions:
            # our api has a problem with dealing `edgeone-pages-mcp-server`
            # so we call it manually.
            session = self.sessions['edgeone-pages-mcp-server']
            response = await session.list_tools()
            result = await session.call_tool(response.tools[0].name, {'value': final_result})
            print(result)

    async def connect_all_servers(self, query):
        config = self.generate_config(self.mcp)
        if not self.mcp:
            keys = config.keys()
            messages = [dict(role='system',
                             content=(
                                 'You are an assistant which helps me to finish a complex job. '
                                 'Tools may be given to you '
                                 'and you must choose which tools are required list them in a '
                                 'json array and wraps it in a <box></box>, at least you should use notebook, '
                                 'a google-search tool and a crawler.')),
                        {
                            'role': 'user',
                            'content': f'The user job: {query}, all available tools: {list(keys)}',
                        }]
            response = self.generate_response(messages, self.model)
            content = response.choices[0].message.content
            _, tools = content.split('<box>')
            tools, _ = tools.split('</box>')
            tools = tools.strip()
            tools = json.loads(tools)
        else:
            tools = self.mcp

        for tool in tools:
            cmd = config[tool]
            env_dict = cmd.get('env', {})
            env_dict = {key: value if value else os.environ.get(key, '') for key, value in env_dict.items()}
            await self.connect_to_server(cmd['command'], cmd['args'], env_dict, server_name=tool)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
