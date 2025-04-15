import asyncio
import os

import gradio as gr
from run import LiteResearchMCPClient


def start():
    with gr.Blocks() as demo:
        gr.HTML(f"<h3><a href=\"https://github.com/modelscope/mcp-central\" target=\"_blank\">A Lite Research Tool with Pure MCP Servers</a></h3>")
        with gr.Row():
            with gr.Column(scale=1, min_width=200):
                gr.Markdown("### Model(OpenAI standard urls)")
                base_url = gr.Textbox(label="server", value='https://api-inference.modelscope.cn/v1')
                model = gr.Textbox(label="model", value='Qwen/Qwen2.5-72B-Instruct')
                token = gr.Textbox(label="token(Space has been set to `MODEL_TOKEN`)")
                with gr.Row():
                    submit = gr.Button(value='🚀Connect Server', scale=4)
                    connect_status = gr.Checkbox(label='🍎Closed', value=False, interactive=False)
                gr.Markdown("### Setting")
                top_p = gr.Slider(0.0, 1.0, value=0.7, label="top_p")
                temperature = gr.Slider(0.0, 1.0, value=0.4, label="temperature")
                max_completion_length = gr.Slider(256, 4096, value=1024, label="max_completion_length")
                default_system = gr.Textbox(value=LiteResearchMCPClient.default_system, lines=5, label='system')
                state = gr.State([])


                async def connect_server(base_url, model, token, state):
                    if state:
                        asyncio.run(state[0].cleanup())
                    if not token:
                        token = os.environ.get('MODEL_TOKEN', '')
                    assert token, 'Please input a token or use `MODEL_TOKEN` env.'
                    client = LiteResearchMCPClient(base_url=base_url, model=model,
                                                   token=token, mcp=['crawl4ai', 'planer', 'web-search'])
                    await client.connect_all_servers(None)
                    gr.Info('🚂Server started🏁')
                    return [client], gr.update(value=True, label='🍏Connected')


                submit.click(connect_server, [base_url, model, token, state], [state, connect_status])

            with gr.Column(scale=3):
                chat = gr.Chatbot(label="Chat", height=600)
                with gr.Row():
                    query = gr.Textbox(label="Query:", scale=10)
                    submit2 = gr.Button(value='🚀Send', scale=2)

                with gr.Row():
                    ex1 = gr.Button(value="请帮我搜索摩洛哥最好看的景点，尤其是从亚洲人的评论中", scale=6)
                    ex1.click(lambda x: x, [ex1], [query])
                    ex2 = gr.Button(value="Please give me some interesting stories in the Dify company, "
                                          "and summarize to a 1000 words report", scale=8)
                    ex2.click(lambda x: x, [ex2], [query])
                with gr.Row():
                    ex3 = gr.Button(value='Browse website, and find me a good joke', scale=4)
                    ex3.click(lambda x: x, [ex3], [query])
                    ex4 = gr.Button(value="给我找下2025年最受期待的游戏有哪些", scale=4)
                    ex4.click(lambda x: x, [ex4], [query])
                    ex5 = gr.Button(value="Write a paper of 1000 words to introduce Elon Mask.", scale=6)
                    ex5.click(lambda x: x, [ex5], [query])


        async def search(default_system, user_input, top_p, temperature, max_completion_length, state):
            if not state:
                raise gr.Error(f'Connect server first')
            yield [], ''
            history = [[user_input, '']]
            async for response in state[0].process_query(
                    default_system,
                    user_input,
                    system='o1' not in state[0].model,
                    top_p=top_p,
                    temperature=temperature,
                    max_completion_length=max_completion_length):
                query = ''
                if 'tool result:' in response:
                    response, query = response.split('tool result:')
                history[-1][-1] = response
                yield history, ''
                query = query.replace('<', '').replace('>', '')
                history.append([query, ''])


        submit2.click(search, [default_system, query, top_p, temperature,
                               max_completion_length, state], [chat, query])

    demo.launch(server_name='0.0.0.0', server_port=8000, inbrowser=True)


if __name__ == "__main__":
    start()