pip install -r ../../mcp_central/crawl4ai/requirements.txt
python -m playwright install --with-deps chromium
crawl4ai-setup
crawl4ai-doctor
pip install gradio mcp openai -U
