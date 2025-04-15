import inspect
import json
import os
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
        time.sleep(1)
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
        for i in range(3):
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
                if '418' in str(e):
                    _e = e
                    continue
                else:
                    _e = e
                    break
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
                    if 'mcp.py' in args[idx]:
                        args[idx] = os.path.join(mcp_abs_path, 'mcp.py')
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

    async def process_query(self, default_system, query: str, system=True, **kwargs) -> str:
        if not default_system:
            default_system = self.default_system
        if system:
            messages = [{'role': 'system', 'content': default_system}, {"role": "user", "content": query}]
        else:
            messages = [{"role": "user", "content": default_system + self.connector + query}]
        tools = []
        for key, session in self.sessions.items():
            response = await session.list_tools()
            available_tools = [
                {
                    "name": key + '---' + tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in response.tools if tool.name != 'tavily-extract'
            ]
            tools.extend(available_tools)

        task_done_cnt = 0
        while True:
            response = self.generate_response(messages, self.model, tools=tools, **kwargs)
            message = response.choices[0].message
            try:
                reasoning = message.model_extra['reasoning_content']
            except:
                reasoning = ''
            content = reasoning + (message.content or '')
            if '<task_done>' in content or (not content.strip() and not message.tool_calls) or task_done_cnt >= 4:
                break
            messages.append({
                "role": "assistant",
                "content": content,
                'tool_calls': message.tool_calls if not message.tool_calls else [message.tool_calls[0]],
            })
            if message.tool_calls:
                for tool in message.tool_calls:
                    name = tool.function.name
                    args = tool.function.arguments
                    key, tool_name = name.split('---')
                    args = json.loads(args)
                    try:
                        if tool.function.name == 'planer---save_query':
                            user_query = args.get('user_query', '')
                            user_query = user_query.split(self.connector)
                            if len(user_query) > 1:
                                user_query = user_query[1]
                                args['user_query'] = user_query
                        elif tool.function.name == 'planer---task_done':
                            task_done_cnt += 1
                        result = await self.sessions[key].call_tool(tool_name, args)
                        _print_result = result.content[0].text or ''
                        if len(_print_result) > 1024:
                            _print_result = _print_result[:1024] + '...'
                        yield f'{content}\n\n tool call: {name}, {args}\n\n tool result: {_print_result}'
                    except Exception as e:
                        messages.append({
                            'role': 'tool',
                            'content': f'Tool {name} called with error: ' + str(e),
                            'tool_call_id': tool.id,
                        })
                    else:
                        messages.append({
                            'role': 'tool',
                            'content': result.content[0].text or '',
                            'tool_call_id': tool.id,
                        })
                    break
            else:
                yield content
                continue

    async def connect_all_servers(self, query):
        config = self.generate_config(self.mcp)
        if not self.mcp:
            keys = config.keys()
            messages = [dict(role='system',
                             content=(
                                 'You are an assistant which helps me to finish a complex job. '
                                 'Tools may be given to you '
                                 'and you must choose which tools are required list them in a '
                                 'json array and wraps it in a <box></box>, at least you should use planer, '
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
