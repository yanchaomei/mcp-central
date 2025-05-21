import json
import subprocess
from fastmcp import FastMCP

mcp = FastMCP("ocrmypdf_server")

@mcp.tool(description='A tool to perform OCR on a PDF file and return the extracted text.')
async def ocr_pdf(input_pdf: str, output_pdf: str) -> str:
    try:
        command = [
            'ocrmypdf',
            '--language', 'eng+chi_sim',  # language
            '--force-ocr',  # Force OCR processing
            input_pdf,
            output_pdf
        ]


        result = subprocess.run(command, check=True, capture_output=True, text=True)


        print("OCR completed:")
        print(result.stdout)
        if result.stderr:
            print("Error messages:")
            print(result.stderr)

        return f"OCR completed: {output_pdf}"

    except subprocess.CalledProcessError as e:
        print(f"OCR failed: {e}")
        print(f"Error output: {e.stderr}")
        return f"OCR failed: {e.stderr}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
