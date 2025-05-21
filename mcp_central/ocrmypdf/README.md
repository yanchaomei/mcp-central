# OCRMYPDF MCP

This is an MCP tool for performing OCR (Optical Character Recognition) on PDF files. You can use this tool to process PDF files and extract text content.

## Features

1. Use `ocrmypdf` to perform OCR on input PDF files.
2. Support multiple languages (English and Simplified Chinese).
3. Force OCR processing even if the PDF file already contains text layers.
4. Return the path of the processed PDF file.

## Installation

Ensure you have installed `ocrmypdf` and `tesseract`, and that `tesseract` supports English and Simplified Chinese.

### Install `ocrmypdf` and `tesseract`

#### On Debian/Ubuntu

```shell
apt install ocrmypdf
```
#### macos

```shell
brew install tesseract-lang
```
#### windows

```shell
python3 -m pip install ocrmypdf
```
###For more detailed installation instructions, please visit the [official website](https://ocrmypdf.readthedocs.io/en/latest/index.html).


```json
{
  "mcpServers": {
    "ocrmypdf": {
      "command": "/path/to/fastmcp",
      "args": [
        "run",
        "/path/to/crawl4ai/ocrmypdf.py"
      ]
    }
  }
}
```
You can add this configuration to your chatbot or agent configuration files to use ocr-mcp.

## Implementation Details
### OCR Language Support
Uses --language eng+chi_sim parameter to support mixed English and Simplified Chinese recognition.

### Force OCR Mode
Enabled via --force-ocr parameter to ensure OCR is applied to all pages, even if the PDF already contains text layers.

### Error Handling

Catches subprocess.CalledProcessError exceptions
Outputs stderr for debugging
Returns structured JSON format results
### Execution Flow
```shell
subprocess.run(
    ['ocrmypdf', '--language', 'eng+chi_sim', '--force-ocr', input_pdf, output_pdf],
    check=True,
    capture_output=True,
    text=True
)

```

## Functions
ocr_pdf: A tool to perform OCR on a PDF file and return the path of the processed PDF file.
Input:
input_pdf(str): Path to the input PDF file.
output_pdf(str): Path to the output PDF file.
Output:
Path to the processed PDF file.
