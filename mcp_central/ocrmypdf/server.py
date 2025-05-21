import json
import subprocess
from fastmcp import FastMCP

# 创建 FastMCP 实例
mcp = FastMCP("ocr_server")

@mcp.tool(description='A tool to perform OCR on a PDF file and return the extracted text.')
async def ocr_pdf(input_pdf: str, output_pdf: str) -> str:
    try:
        # 构建 ocrmypdf 命令
        command = [
            'ocrmypdf',
            '--language', 'eng+chi_sim',  # 指定语言，这里假设是英语和简体中文
            '--force-ocr',  # 强制进行 OCR 处理
            input_pdf,
            output_pdf
        ]

        # 执行命令
        result = subprocess.run(command, check=True, capture_output=True, text=True)

        # 输出结果
        print("OCR 完成:")
        print(result.stdout)
        if result.stderr:
            print("错误信息:")
            print(result.stderr)

        return f"OCR 完成: {output_pdf}"

    except subprocess.CalledProcessError as e:
        print(f"OCR 失败: {e}")
        print(f"错误输出: {e.stderr}")
        return f"OCR 失败: {e.stderr}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
