<p align="center">
  <img src="./doctranslate.png" alt="Project Logo" style="width: 150px">
</p>

<h1 align="center">doctranslate</h1>

<p align="center">
  <a href="https://github.com/therealtimex/doctranslate/stargazers"><img src="https://img.shields.io/github/stars/therealtimex/doctranslate?style=flat-square&logo=github&color=blue" alt="GitHub stars"></a>
  <a href="https://github.com/therealtimex/doctranslate/releases"><img src="https://img.shields.io/github/downloads/therealtimex/doctranslate/total?logo=github&style=flat-square" alt="GitHub Downloads"></a>
  <a href="https://pypi.org/project/doctranslate/"><img src="https://img.shields.io/pypi/v/doctranslate?style=flat-square" alt="PyPI version"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white&style=flat-square" alt="Python Version"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/github/license/therealtimex/doctranslate?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="/README_ZH.md"><strong>简体中文</strong></a> / <a href="/README.md"><strong>English</strong></a> / <a href="/README_JP.md"><strong>日本語</strong></a>
</p>

<p align="center">
  A lightweight local file translation tool based on a large language model.
</p>

- ✅ **Supports Multiple Formats**: Can translate various files such as `pdf`, `docx`, `xlsx`, `md`, `txt`, `json`,
  `epub`, `srt`, and more.
- ✅ **Automatic Glossary Generation**: Supports automatic generation of glossaries to ensure term alignment.
- ✅ **PDF Table, Formula, and Code Recognition**: With the `docling` and `mineru` PDF parsing engines, it can recognize
  and translate tables, formulas, and code frequently found in academic papers.
- ✅ **JSON Translation**: Supports specifying the values to be translated in JSON via JSON paths (using `jsonpath-ng`
  syntax).
- ✅ **Word/Excel Format-Preserving Translation**: Supports translating `docx` and `xlsx` files (currently not `doc` or
  `xls` files) while preserving the original formatting.
- ✅ **Multi-AI Platform Support**: Supports most AI platforms, enabling high-performance, concurrent AI translation with
  custom prompts.
- ✅ **Asynchronous Support**: Designed for high-performance scenarios, it offers complete asynchronous support,
  providing service interfaces for parallel multitasking.
- ✅ **LAN and Multi-user Support**: Supports simultaneous use by multiple users on a local area network.
- ✅ **Interactive Web Interface**: Provides an out-of-the-box Web UI and RESTful API for easy integration and use.
- ✅ **Small-Footprint, Multi-Platform "Lazy" Packages**: Windows and Mac "lazy" packages under 40MB (for versions not
  using `docling` for local PDF parsing).

> When translating `pdf` files, they are first converted to Markdown, which will **lose** the original layout. Users
> with layout requirements should take note.

> QQ Discussion Group: 1047781902

**UI Interface**:
![Translation Effect](/images/UI界面.png)

**Thesis Translation**:
![Translation Effect](/images/论文翻译.png)

**Novel Translation**:![Translation Effect](/images/小说翻译.png)

## All-in-One Packages

For users who want to get started quickly, we provide all-in-one packages
on [GitHub Releases](https://github.com/therealtimex/doctranslate/releases). Simply download, unzip, and enter your AI
platform API-Key to start using.

- **doctranslate**: Standard version, uses the online `minerU` engine to parse PDF documents. Choose this version if
  you don't need local PDF parsing (recommended).
- **doctranslate_full**: Full version, includes the built-in `docling` local PDF parsing engine. Choose this version if
  you need local PDF parsing.

## Installation

### Using pip

```bash
# CLI only (no GUI deps)
pip install doctranslate

# GUI/Web UI support
pip install "doctranslate[webui]"

# Add docling for local PDF parsing (optional)
pip install "doctranslate[docling]"
# With both GUI and docling
pip install "doctranslate[webui,docling]"
```

### Using uv

```bash
# Initialize environment
uv init

# CLI only
uv add doctranslate

# GUI support
uv add "doctranslate[webui]"

# docling extension
uv add "doctranslate[docling]"
```

### Using git

```bash
# Initialize environment
git clone https://github.com/therealtimex/doctranslate.git

cd doctranslate

uv sync
```

## Core Concept: Workflow

The core of the new doctranslate is the **Workflow**. Each workflow is a complete, end-to-end translation pipeline
designed specifically for a particular file type. You no longer interact with a monolithic class; instead, you select
and configure a suitable workflow based on your file type.

**The basic usage process is as follows:**

1. **Select a Workflow**: Choose a workflow based on your input file type (e.g., PDF/Word or TXT), such as
   `MarkdownBasedWorkflow` or `TXTWorkflow`.
2. **Build the Configuration**: Create the corresponding configuration object for the selected workflow (e.g.,
   `MarkdownBasedWorkflowConfig`). This configuration object contains all the necessary sub-configurations, such as:
    * **Converter Config**: Defines how to convert the original file (e.g., PDF) to Markdown.
    * **Translator Config**: Defines which LLM, API-Key, target language, etc., to use.
    * **Exporter Config**: Defines specific options for the output format (e.g., HTML).
3. **Instantiate the Workflow**: Create a workflow instance using the configuration object.
4. **Execute the Translation**: Call the workflow's `.read_*()` and `.translate()` / `.translate_async()` methods.
5. **Export/Save the Result**: Call the `.export_to_*()` or `.save_as_*()` methods to get or save the translation
   result.

## Available Workflows

| Workflow                    | Use Case                                                                                                              | Input Formats                                | Output Formats         | Core Config Class             |
|:----------------------------|:----------------------------------------------------------------------------------------------------------------------|:---------------------------------------------|:-----------------------|:------------------------------|
| **`MarkdownBasedWorkflow`** | Processes rich text documents like PDF, Word, images, etc. The process is: `File -> Markdown -> Translate -> Export`. | `.pdf`, `.docx`, `.md`, `.png`, `.jpg`, etc. | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`**           | Processes plain text documents. The process is: `txt -> Translate -> Export`.                                         | `.txt` and other plain text formats          | `.txt`, `.html`        | `TXTWorkflowConfig`           |
| **`JsonWorkflow`**          | Processes JSON files. The process is: `json -> Translate -> Export`.                                                  | `.json`                                      | `.json`, `.html`       | `JsonWorkflowConfig`          |
| **`DocxWorkflow`**          | Processes docx files. The process is: `docx -> Translate -> Export`.                                                  | `.docx`                                      | `.docx`, `.html`       | `docxWorkflowConfig`          |
| **`XlsxWorkflow`**          | Processes xlsx files. The process is: `xlsx -> Translate -> Export`.                                                  | `.xlsx`, `.csv`                              | `.xlsx`, `.html`       | `XlsxWorkflowConfig`          |
| **`SrtWorkflow`**           | Processes srt files. The process is: `srt -> Translate -> Export`.                                                    | `.srt`                                       | `.srt`, `.html`        | `SrtWorkflowConfig`           |
| **`EpubWorkflow`**          | Processes epub files. The process is: `epub -> Translate -> Export`.                                                  | `.epub`                                      | `.epub`, `.html`       | `EpubWorkflowConfig`          |
| **`HtmlWorkflow`**          | Processes html files. The process is: `html -> Translate -> Export`.                                                  | `.html`, `.htm`                              | `.html`                | `HtmlWorkflowConfig`          |

> In the interactive interface, you can export to PDF format.

## Starting the Web UI and API Service

For ease of use, doctranslate provides a full-featured Web interface and RESTful API.

**Starting the Service:**

```bash
# Install GUI support first: pip install "doctranslate[webui]"

# Start the service, listening on port 8010 by default
doctranslate gui

# Start on a specific port
doctranslate gui -p 8011

# You can also specify the port via an environment variable
export doctranslate_PORT=8011
doctranslate -i
```

- **Interactive Interface**: After starting the service, please visit `http://127.0.0.1:8010` (or your specified port)
  in your browser.
- **API Documentation**: The complete API documentation (Swagger UI) is available at `http://127.0.0.1:8010/docs`.

## CLI

doctranslate now ships with a first-class CLI. It auto-detects workflow type from the input file extension and exports suitable outputs.

- Env fallbacks: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `MINERU_TOKEN`.

Basic examples

```bash
# Show version
doctranslate version

# Start GUI (requires webui extra)
doctranslate gui -p 8011

# Translate a DOCX (exports .docx and .html)
doctranslate translate ./paper.docx \
  --base-url https://api.openai.com/v1 \
  --api-key $OPENAI_API_KEY \
  --model-id gpt-4o \
  --to-lang 中文

# Translate a TXT (exports .txt and .html)
doctranslate translate ./notes.txt --to-lang English

# Translate a JSON (exports .json and .html). Default path is $..*
doctranslate translate ./data.json --json-path '$.items[*].name' --json-path '$.items[*].desc'

# Translate an XLSX (exports .xlsx, .csv, .html). Select regions if needed
doctranslate translate ./sheet.xlsx --xlsx-regions Sheet1!A1:C20 C:D

# Translate a PDF via minerU (exports .md, .zip, .html)
export MINERU_TOKEN=your_mineru_token
doctranslate translate ./paper.pdf --to-lang 中文

# Force a specific workflow and formats
doctranslate translate ./index.html --workflow html --formats html
```

Key flags

- `--skip-translate`: parse and export without calling an LLM
- `--insert-mode [replace|append|prepend]` and `--separator`: for txt/xlsx/docx/srt/epub/html
- `--convert-engine [mineru|docling|identity]`: for markdown-based workflow (PDF/MD/images)
- `--glossary-enable` plus `--glossary-*-*` options to enable a glossary generation agent

## Usage

### Example 1: Translating a PDF File (using `MarkdownBasedWorkflow`)

This is the most common use case. We will use the `minerU` engine to convert the PDF to Markdown, and then use an LLM
for translation. Here is an example using the asynchronous approach.

```python
import asyncio
from doctranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from doctranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from doctranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from doctranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. Build the translator configuration
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AI platform Base URL
        api_key="YOUR_ZHIPU_API_KEY",  # AI platform API Key
        model_id="glm-4-air",  # Model ID
        to_lang="English",  # Target language
        chunk_size=3000,  # Text chunk size
        concurrent=10,  # Concurrency
        # glossary_generate_enable=True, # Enable automatic glossary generation
        # glossary_dict={"Jobs":"乔布斯"} # Pass in a glossary
    )

    # 2. Build the converter configuration (using minerU)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # Your minerU Token
        formula_ocr=True  # Enable formula recognition
    )

    # 3. Build the main workflow configuration
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # Specify the parsing engine
        converter_config=converter_config,  # Pass in the converter configuration
        translator_config=translator_config,  # Pass in the translator configuration
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTML export configuration
    )

    # 4. Instantiate the workflow
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. Read the file and execute the translation
    print("Starting to read and translate the file...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # Or use the synchronous method
    # workflow.translate()
    print("Translation complete!")

    # 6. Save the results
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # Markdown with embedded images
    print("Files have been saved to the ./output folder.")

    # Or get the content strings directly
    html_content = workflow.export_to_html()
    markdown_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```

### Example 2: Translating a TXT File (using `TXTWorkflow`)

For plain text files, the process is simpler as it doesn't require a document parsing (conversion) step. Here is an
example using the asynchronous approach.

```python
import asyncio
from doctranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from doctranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from doctranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig


async def main():
    # 1. Build the translator configuration
    translator_config = TXTTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Chinese",
    )

    # 2. Build the main workflow configuration
    workflow_config = TXTWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=TXT2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = TXTWorkflow(config=workflow_config)

    # 4. Read the file and execute the translation
    workflow.read_path("path/to/your/notes.txt")
    await workflow.translate_async()
    # Or use the synchronous method
    # workflow.translate()

    # 5. Save the result
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXT file has been saved.")

    # You can also export the translated plain text
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```

### Example 3: Translating a JSON File (using `JsonWorkflow`)

Here is an example using the asynchronous approach. The `json_paths` item in `JsonTranslatorConfig` needs to specify the
JSON paths to be translated (satisfying the `jsonpath-ng` syntax). Only values matching the JSON paths will be
translated.

```python
import asyncio

from doctranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from doctranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from doctranslate.workflow.json_workflow import JsonWorkflowConfig, JsonWorkflow


async def main():
    # 1. Build the translator configuration
    translator_config = JsonTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Chinese",
        json_paths=["$.*", "$.name"]  # Satisfies jsonpath-ng syntax, values at matching paths will be translated
    )

    # 2. Build the main workflow configuration
    workflow_config = JsonWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Json2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = JsonWorkflow(config=workflow_config)

    # 4. Read the file and execute the translation
    workflow.read_path("path/to/your/notes.json")
    await workflow.translate_async()
    # Or use the synchronous method
    # workflow.translate()

    # 5. Save the result
    workflow.save_as_json(name="translated_notes.json")
    print("JSON file has been saved.")

    # You can also export the translated JSON text
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```

### Example 4: Translating a docx File (using `DocxWorkflow`)

Here is an example using the asynchronous approach.

```python
import asyncio

from doctranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from doctranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from doctranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow


async def main():
    # 1. Build the translator configuration
    translator_config = DocxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Chinese",
        insert_mode="replace",  # Options: "replace", "append", "prepend"
        separator="\n",  # Separator used in "append" and "prepend" modes
    )

    # 2. Build the main workflow configuration
    workflow_config = DocxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Docx2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = DocxWorkflow(config=workflow_config)

    # 4. Read the file and execute the translation
    workflow.read_path("path/to/your/notes.docx")
    await workflow.translate_async()
    # Or use the synchronous method
    # workflow.translate()

    # 5. Save the result
    workflow.save_as_docx(name="translated_notes.docx")
    print("docx file has been saved.")

    # You can also export the translated docx as binary
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```

### Example 5: Translating a xlsx File (using `XlsxWorkflow`)

Here is an example using the asynchronous approach.

```python
import asyncio

from doctranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from doctranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from doctranslate.workflow.xlsx_workflow import XlsxWorkflowConfig, XlsxWorkflow


async def main():
    # 1. Build the translator configuration
    translator_config = XlsxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Chinese",
        insert_mode="replace",  # Options: "replace", "append", "prepend"
        separator="\n",  # Separator used in "append" and "prepend" modes
    )

    # 2. Build the main workflow configuration
    workflow_config = XlsxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Xlsx2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = XlsxWorkflow(config=workflow_config)

    # 4. Read the file and execute the translation
    workflow.read_path("path/to/your/notes.xlsx")
    await workflow.translate_async()
    # Or use the synchronous method
    # workflow.translate()

    # 5. Save the result
    workflow.save_as_xlsx(name="translated_notes.xlsx")
    print("xlsx file has been saved.")

    # You can also export the translated xlsx as binary
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```

## Prerequisites and Configuration Details

### 1. Get a Large Language Model API Key

The translation functionality relies on large language models. You need to obtain a `base_url`, `api_key`, and
`model_id` from the respective AI platform.

> Recommended models: Volcengine's `doubao-seed-1-6-250615`, `doubao-seed-1-6-flash-250715`, Zhipu's `glm-4-flash`,
> Alibaba Cloud's `qwen-plus`, `qwen-turbo`, Deepseek's `deepseek-chat`, etc.

| Platform Name         | Get API Key                                                                                   | baseurl                                                  |
|-----------------------|-----------------------------------------------------------------------------------------------|----------------------------------------------------------|
| ollama                |                                                                                               | http://127.0.0.1:11434/v1                                |
| lm studio             |                                                                                               | http://127.0.0.1:1234/v1                                 |
| openrouter            | [Click to get](https://openrouter.ai/settings/keys)                                           | https://openrouter.ai/api/v1                             |
| openai                | [Click to get](https://platform.openai.com/api-keys)                                          | https://api.openai.com/v1/                               |
| gemini                | [Click to get](https://aistudio.google.com/u/0/apikey)                                        | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek              | [Click to get](https://platform.deepseek.com/api_keys)                                        | https://api.deepseek.com/v1                              |
| Zhipu AI              | [Click to get](https://open.bigmodel.cn/usercenter/apikeys)                                   | https://open.bigmodel.cn/api/paas/v4                     |
| Tencent Hunyuan       | [Click to get](https://console.cloud.tencent.com/hunyuan/api-key)                             | https://api.hunyuan.cloud.tencent.com/v1                 |
| Alibaba Cloud Bailian | [Click to get](https://bailian.console.aliyun.com/?tab=model#/api-key)                        | https://dashscope.aliyuncs.com/compatible-mode/v1        |
| Volcengine            | [Click to get](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3                 |
| SiliconFlow           | [Click to get](https://cloud.siliconflow.cn/account/ak)                                       | https://api.siliconflow.cn/v1                            |
| DMXAPI                | [Click to get](https://www.dmxapi.cn/token)                                                   | https://www.dmxapi.cn/v1                                 |

### 2. PDF Parsing Engine (ignore if not translating PDFs)

### 2.1 Get a minerU Token (online PDF parsing, free, recommended)

If you choose `mineru` as the document parsing engine (`convert_engine="mineru"`), you need to apply for a free token.

1. Visit the [minerU official website](https://mineru.net/apiManage/docs) to register and apply for an API.
2. Create a new API Token in the [API Token management interface](https://mineru.net/apiManage/token).

> **Note**: minerU tokens have a 14-day validity period. Please re-create them after they expire.

### 2.2. docling Engine Configuration (local PDF parsing)

If you choose `docling` as the document parsing engine (`convert_engine="docling"`), it will download the required
models from Hugging Face on first use.

> A better option is to download `docling_artifact.zip`
> from [GitHub releases](https://github.com/therealtimex/doctranslate/releases) and unzip it to your working directory.

**Solution for network issues when downloading `docling` models:**

1. **Set a Hugging Face mirror (recommended)**:

* **Method A (environment variable)**: Set the system environment variable `HF_ENDPOINT` and restart your IDE or
  terminal.
   ```
   HF_ENDPOINT=https://hf-mirror.com
   ```
* **Method B (set in code)**: Add the following code at the beginning of your Python script.

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

2. **Offline use (download the model package in advance)**:

* Download `docling_artifact.zip` from [GitHub Releases](https://github.com/therealtimex/doctranslate/releases).
* Unzip it to your project directory.
* Specify the model path in the configuration (if the model is not in the same directory as the script):

```python
from doctranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # Point to the unzipped folder
    code_ocr=True,
    formula_ocr=True
)
```

## FAQ

**Q: What if port 8010 is occupied?**
A: Use the `-p` parameter to specify a new port, or set the `doctranslate_PORT` environment variable.

**Q: Does it support translation of scanned PDFs?**
A: Yes. Please use the `mineru` parsing engine, which has powerful OCR capabilities.

**Q: Why is the first PDF translation so slow?**
A: If you are using the `docling` engine, it needs to download models from Hugging Face on its first run. Please refer
to the "Network Issues Solution" above to speed up this process.

**Q: How to use it in an intranet (offline) environment?**
A: It is entirely possible. You need to meet the following conditions:

1. **Local LLM**: Use tools like [Ollama](https://ollama.com/) or [LM Studio](https://lmstudio.ai/) to deploy a language
   model locally, and fill in the `base_url` of the local model in `TranslatorConfig`.
2. **Local PDF parsing engine** (only needed for parsing PDFs): Use the `docling` engine and follow the "Offline use"
   instructions above to download the model package in advance.

**Q: How does the PDF parsing cache mechanism work?**
A: `MarkdownBasedWorkflow` automatically caches the results of document parsing (file to Markdown conversion) to avoid
repeated parsing that consumes time and resources. The cache is stored in memory by default and records the last 10
parses. You can modify the cache size using the `doctranslate_CACHE_NUM` environment variable.

**Q: How to make the software go through a proxy?**
A: The software does not use a proxy by default. You can enable it by setting the environment variable
`doctranslate_PROXY_ENABLED` to `true`.

## Star History

<a href="https://www.star-history.com/#therealtimex/doctranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=therealtimex/doctranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=therealtimex/doctranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=therealtimex/doctranslate&type=Date" />
 </picture>
</a>

## Support the Author

Welcome to support the author. Please kindly mention the reason for your appreciation in the notes. ❤

<p align="center">
  <img src="./images/赞赏码.jpg" alt="赞赏码" style="width: 250px;">
</p>
