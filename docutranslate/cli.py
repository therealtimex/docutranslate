# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import argparse
import os
from pathlib import Path
import sys  # 用于检查命令行参数数量
from typing import Any

from docutranslate.translator import default_params
from docutranslate.global_values.conditional_import import DOCLING_EXIST


def _infer_workflow_type_from_suffix(suffix: str) -> str:
    s = suffix.lower()
    if s in {".md"}:
        return "markdown_based"
    if s in {".pdf", ".doc", ".ppt", ".pptx", ".png", ".jpg", ".jpeg"}:
        return "markdown_based"
    if s in {".txt"}:
        return "txt"
    if s in {".json"}:
        return "json"
    if s in {".xlsx", ".csv"}:
        return "xlsx"
    if s in {".docx"}:
        return "docx"
    if s in {".srt"}:
        return "srt"
    if s in {".epub"}:
        return "epub"
    if s in {".html", ".htm"}:
        return "html"
    # default: try markdown-based converter
    return "markdown_based"


def _fill_common_ai_args(ns: argparse.Namespace) -> dict:
    # pull defaults from env if not provided
    api_key = ns.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    base_url = ns.base_url or os.getenv("OPENAI_BASE_URL") or os.getenv("BASE_URL")
    model_id = ns.model_id or os.getenv("OPENAI_MODEL")

    return {
        "skip_translate": ns.skip_translate,
        "base_url": base_url,
        "api_key": api_key,
        "model_id": model_id,
        "to_lang": ns.to_lang,
        "custom_prompt": ns.custom_prompt,
        "chunk_size": ns.chunk_size,
        "concurrent": ns.concurrent,
        "temperature": ns.temperature,
        "timeout": ns.timeout,
        "thinking": ns.thinking,
        "retry": ns.retry,
        "glossary_dict": None,
        "glossary_generate_enable": ns.glossary_enable,
        "glossary_agent_config": (
            __import__(
                'docutranslate.agents.glossary_agent', fromlist=['GlossaryAgentConfig']
            ).GlossaryAgentConfig(
                base_url=ns.glossary_base_url or base_url,
                api_key=ns.glossary_api_key or api_key,
                model_id=ns.glossary_model_id or (model_id or ""),
                to_lang=ns.to_lang,
                temperature=ns.temperature,
                concurrent=ns.concurrent,
                timeout=ns.timeout,
                thinking=ns.thinking,
                retry=ns.retry,
            ) if ns.glossary_enable else None
        ),
    }


def _build_workflow(input_path: Path, ns: argparse.Namespace):
    suffix = input_path.suffix
    inferred = _infer_workflow_type_from_suffix(suffix)
    workflow_type = ns.workflow or inferred

    common_ai_args = _fill_common_ai_args(ns)

    # Exporter html configs with CDN on by default (lazily imported per workflow)
    html_cfg_md = None
    html_cfg_txt = None
    html_cfg_json = None
    html_cfg_xlsx = None
    html_cfg_docx = None
    html_cfg_srt = None
    html_cfg_epub = None

    if workflow_type == "markdown_based":
        from docutranslate.exporter.md.types import ConvertEngineType
        from docutranslate.workflow.md_based_workflow import (
            MarkdownBasedWorkflow,
            MarkdownBasedWorkflowConfig,
        )
        # choose convert engine
        convert_engine: ConvertEngineType
        converter_cfg = None
        if suffix.lower() == ".md":
            convert_engine = "identity"
        else:
            # Prefer docling if available, otherwise fall back to mineru
            convert_engine = ns.convert_engine or ("docling" if DOCLING_EXIST else "mineru")
        if convert_engine == "mineru":
            from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
            token = ns.mineru_token or os.getenv("MINERU_TOKEN")
            if not token:
                raise SystemExit("mineru convert engine requires --mineru-token or MINERU_TOKEN env")
            converter_cfg = ConverterMineruConfig(
                mineru_token=token,
                formula_ocr=ns.mineru_formula_ocr,
                model_version=ns.mineru_model_version,
            )
        elif convert_engine == "mineru_local":
            from docutranslate.converter.x2md.converter_mineru_local import ConverterMineruLocalConfig
            converter_cfg = ConverterMineruLocalConfig(
                mode=ns.mineru_local_mode,
                cmd=ns.mineru_local_cmd,
                args_template=ns.mineru_local_args,
                md_filename=ns.mineru_local_md_file,
            )
        elif convert_engine == "docling":
            from docutranslate.global_values.conditional_import import DOCLING_EXIST
            if not DOCLING_EXIST:
                raise SystemExit("docling is not installed. Use mineru or install optional 'docling' extras.")
            if getattr(ns, 'preserve_layout', False):
                from docutranslate.workflow.docling_html_workflow import (
                    DoclingHTMLWorkflow, DoclingHTMLWorkflowConfig,
                )
                from docutranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig
                translator_cfg_html = HtmlTranslatorConfig(
                    **common_ai_args,
                    insert_mode=ns.insert_mode,
                    separator=ns.separator,
                )
                wf_cfg_html = DoclingHTMLWorkflowConfig(translator_config=translator_cfg_html)
                return DoclingHTMLWorkflow(config=wf_cfg_html)
            else:
                from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig
                converter_cfg = ConverterDoclingConfig()
        elif convert_engine == "identity":
            converter_cfg = None
        else:
            raise SystemExit(f"Unsupported convert engine: {convert_engine}")

        from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
        translator_cfg = MDTranslatorConfig(**common_ai_args)
        wf_cfg = MarkdownBasedWorkflowConfig(
            convert_engine=convert_engine, converter_config=converter_cfg,
            translator_config=translator_cfg, html_exporter_config=html_cfg_md,
        )
        return MarkdownBasedWorkflow(config=wf_cfg)

    if workflow_type == "txt":
        from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig
        from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
        from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
        translator_cfg = TXTTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        html_cfg_txt = TXT2HTMLExporterConfig(cdn=True)
        wf_cfg = TXTWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_txt)
        return TXTWorkflow(config=wf_cfg)

    if workflow_type == "json":
        from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
        from docutranslate.workflow.json_workflow import JsonWorkflow, JsonWorkflowConfig
        from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
        json_paths = ns.json_path or ["$..*"]
        translator_cfg = JsonTranslatorConfig(
            **common_ai_args,
            json_paths=json_paths,
        )
        html_cfg_json = Json2HTMLExporterConfig(cdn=True)
        wf_cfg = JsonWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_json)
        return JsonWorkflow(config=wf_cfg)

    if workflow_type == "xlsx":
        from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
        from docutranslate.workflow.xlsx_workflow import XlsxWorkflow, XlsxWorkflowConfig
        from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
        translator_cfg = XlsxTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
            translate_regions=ns.xlsx_regions,
        )
        html_cfg_xlsx = Xlsx2HTMLExporterConfig(cdn=True)
        wf_cfg = XlsxWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_xlsx)
        return XlsxWorkflow(config=wf_cfg)

    if workflow_type == "docx":
        from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
        from docutranslate.workflow.docx_workflow import DocxWorkflow, DocxWorkflowConfig
        from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
        translator_cfg = DocxTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        html_cfg_docx = Docx2HTMLExporterConfig(cdn=True)
        wf_cfg = DocxWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_docx)
        return DocxWorkflow(config=wf_cfg)

    if workflow_type == "srt":
        from docutranslate.exporter.srt.srt2html_exporter import Srt2HTMLExporterConfig
        from docutranslate.workflow.srt_workflow import SrtWorkflow, SrtWorkflowConfig
        from docutranslate.translator.ai_translator.srt_translator import SrtTranslatorConfig
        translator_cfg = SrtTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        html_cfg_srt = Srt2HTMLExporterConfig(cdn=True)
        wf_cfg = SrtWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_srt)
        return SrtWorkflow(config=wf_cfg)

    if workflow_type == "epub":
        from docutranslate.exporter.epub.epub2html_exporter import Epub2HTMLExporterConfig
        from docutranslate.workflow.epub_workflow import EpubWorkflow, EpubWorkflowConfig
        from docutranslate.translator.ai_translator.epub_translator import EpubTranslatorConfig
        translator_cfg = EpubTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        html_cfg_epub = Epub2HTMLExporterConfig(cdn=True)
        wf_cfg = EpubWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_epub)
        return EpubWorkflow(config=wf_cfg)

    if workflow_type == "html":
        from docutranslate.workflow.html_workflow import HtmlWorkflow, HtmlWorkflowConfig
        from docutranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig
        translator_cfg = HtmlTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        wf_cfg = HtmlWorkflowConfig(translator_config=translator_cfg)
        return HtmlWorkflow(config=wf_cfg)

    raise SystemExit(f"Unsupported workflow type: {workflow_type}")


def _export_outputs(input_path: Path, workflow: Any, out_dir: Path, explicit_formats: list[str] | None, *, save_attachments: bool=False):
    stem = input_path.stem
    suffix = input_path.suffix.lower()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build export map similar to the web app
    from docutranslate.workflow.interfaces import (
        HTMLExportable, MDFormatsExportable, TXTExportable, JsonExportable,
        XlsxExportable, CsvExportable, DocxExportable, SrtExportable, EpubExportable,
    )

    export_map: dict[str, tuple[callable, str, bool]] = {}
    # HTML
    if isinstance(workflow, HTMLExportable):
        export_map["html"] = (workflow.export_to_html, f"{stem}_translated.html", True)
    if isinstance(workflow, MDFormatsExportable):
        export_map["markdown"] = (workflow.export_to_markdown, f"{stem}_translated.md", True)
        export_map["markdown_zip"] = (workflow.export_to_markdown_zip, f"{stem}_translated.zip", False)
    if isinstance(workflow, TXTExportable):
        export_map["txt"] = (workflow.export_to_txt, f"{stem}_translated.txt", True)
    if isinstance(workflow, JsonExportable):
        export_map["json"] = (workflow.export_to_json, f"{stem}_translated.json", True)
    if isinstance(workflow, XlsxExportable):
        export_map["xlsx"] = (workflow.export_to_xlsx, f"{stem}_translated.xlsx", False)
    if isinstance(workflow, CsvExportable):
        export_map["csv"] = (workflow.export_to_csv, f"{stem}_translated.csv", False)
    if isinstance(workflow, DocxExportable):
        export_map["docx"] = (workflow.export_to_docx, f"{stem}_translated.docx", False)
    if isinstance(workflow, SrtExportable):
        export_map["srt"] = (workflow.export_to_srt, f"{stem}_translated.srt", True)
    if isinstance(workflow, EpubExportable):
        export_map["epub"] = (workflow.export_to_epub, f"{stem}_translated.epub", False)

    selected = explicit_formats or list(export_map.keys())
    for ftype in selected:
        if ftype not in export_map:
            print(f"跳过不支持的导出格式: {ftype}")
            continue
        export_func, filename, is_text = export_map[ftype]
        try:
            content = export_func()
            data = content.encode("utf-8") if is_text else content
            (out_dir / filename).write_bytes(data)
            print(f"已生成: {(out_dir / filename).resolve()}")
        except ModuleNotFoundError as e:
            missing = str(e).split("'")[-2] if "'" in str(e) else str(e)
            print(f"跳过 {ftype} 导出，缺少依赖: {missing}. 可通过 pip install -e . 安装依赖后重试。")
        except Exception as e:
            print(f"导出 {ftype} 失败: {e}")

    # Save attachments (like glossary) if requested
    if save_attachments:
        attachment = workflow.get_attachment()
        if attachment and attachment.attachment_dict:
            for identifier, doc in attachment.attachment_dict.items():
                # Default name from document, else compose from identifier and suffix
                att_name = doc.name or f"{identifier}{doc.suffix}"
                # Rename known artifacts for clarity
                if identifier == "docling" and doc.suffix == ".md":
                    att_name = "docling_raw.md"
                (out_dir / att_name).write_bytes(doc.content)
                print(f"附件已生成: {(out_dir / att_name).resolve()} ({identifier})")


def _add_translate_subparser(subparsers: argparse._SubParsersAction) -> None:
    sp = subparsers.add_parser(
        "translate",
        help="翻译一个文件并导出结果",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sp.add_argument("input", help="要翻译的文件路径")
    sp.add_argument("--out-dir", default="output", help="输出目录")
    sp.add_argument("--workflow", choices=[
        "markdown_based", "txt", "json", "xlsx", "docx", "srt", "epub", "html"
    ], help="覆盖自动推断的工作流类型")
    sp.add_argument("--formats", nargs="*", help="指定导出格式，如 html markdown markdown_zip json xlsx csv docx srt epub")
    sp.add_argument("--preserve-layout", action="store_true", help="(PDF) 使用Docling原生HTML以尽量保留版式")
    sp.add_argument("--save-attachments", action="store_true", help="保存附件（如 docling.md、术语表等）")

    # AI and behavior
    sp.add_argument("--skip-translate", action="store_true", help="只做解析/导出，不调用LLM")
    sp.add_argument("--base-url", help="LLM API基地址，默认读取 OPENAI_BASE_URL")
    sp.add_argument("--api-key", help="LLM API密钥，默认读取 OPENAI_API_KEY")
    sp.add_argument("--model-id", help="模型ID，默认读取 OPENAI_MODEL")
    sp.add_argument("--to-lang", dest="to_lang", default="中文", help="目标语言")
    sp.add_argument("--custom-prompt", help="自定义翻译Prompt文本")

    sp.add_argument("--chunk-size", type=int, default=default_params["chunk_size"], help="分块大小")
    sp.add_argument("--concurrent", type=int, default=default_params["concurrent"], help="并发数量")
    sp.add_argument("--temperature", type=float, default=default_params["temperature"], help="温度参数")
    sp.add_argument("--timeout", type=int, default=default_params["timeout"], help="超时(秒)")
    sp.add_argument("--thinking", choices=["default", "enable", "disable"], default=default_params["thinking"], help="思考模式")
    sp.add_argument("--retry", type=int, default=default_params["retry"], help="失败重试次数")

    # Insert mode for structured types
    sp.add_argument("--insert-mode", choices=["replace", "append", "prepend"], default="replace",
                    help="译文插入模式(适用于txt/xlsx/docx/srt/epub/html)")
    sp.add_argument("--separator", default="\n", help="append/prepend时使用的分隔符")

    # JSON options
    sp.add_argument("--json-path", action="append", help="JSONPath表达式，可多次指定。默认 $..*")

    # XLSX options
    sp.add_argument("--xlsx-regions", nargs="*", help="XLSX 翻译区域列表，如 Sheet1!A1:B10 C:D E5 …")

    # Markdown-based convert options
    sp.add_argument("--convert-engine", choices=["mineru", "mineru_local", "docling", "identity"], help="markdown_based解析引擎")
    sp.add_argument("--mineru-token", help="MinerU API token，或使用环境变量 MINERU_TOKEN")
    sp.add_argument("--mineru-formula-ocr", action="store_true", help="MinerU公式OCR开关")
    sp.add_argument("--mineru-model-version", choices=["pipeline", "vlm"], default="vlm", help="MinerU模型版本")
    # mineru_local options
    sp.add_argument("--mineru-local-mode", choices=["cli_dir", "cli_zip"], default="cli_dir",
                    help="本地MinerU运行模式: 输出目录或输出zip")
    sp.add_argument("--mineru-local-cmd", default="mineru", help="本地MinerU可执行命令或路径")
    sp.add_argument("--mineru-local-args", default="--input {input} --output {output}",
                    help="本地MinerU参数模板，使用 {input} 和 {output} 占位符")
    sp.add_argument("--mineru-local-md-file", default="full.md", help="本地MinerU输出中的Markdown文件名")

    # Glossary options
    sp.add_argument("--glossary-enable", action="store_true", help="启用术语表生成Agent")
    sp.add_argument("--glossary-base-url", help="术语Agent的LLM基础URL(默认同主翻译)")
    sp.add_argument("--glossary-api-key", help="术语Agent的LLM密钥(默认同主翻译)")
    sp.add_argument("--glossary-model-id", help="术语Agent的模型ID(默认同主翻译)")

    sp.set_defaults(cmd="translate")


def main():
    parser = argparse.ArgumentParser(
        description="DocuTranslate: 文档翻译工具 (CLI + GUI)",
        epilog=(
            "示例:\n"
            "  docutranslate gui -p 8081\n"
            "  docutranslate translate ./file.docx --to-lang 中文 --base-url https://api.openai.com/v1 --model-id gpt-4o\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="cmd")

    # gui subcommand
    gui = subparsers.add_parser("gui", help="启动图形界面(本地Web UI)")
    gui.add_argument("-p", "--port", type=int, default=None, help="指定端口号(默认: 8010)")
    gui.set_defaults(cmd="gui")

    # translate subcommand
    _add_translate_subparser(subparsers)

    # version subcommand
    ver = subparsers.add_parser("version", help="显示版本号")
    ver.set_defaults(cmd="version")

    # backward-compatible top-level flags (minimal)
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="等价于子命令: gui"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=None, help="与 --interactive 搭配时的端口号"
    )

    # No-arg hint
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Back-compat: docutranslate -i [-p]
    if args.interactive and args.cmd is None:
        from docutranslate.app import run_app
        run_app(port=args.port)
        return

    if args.cmd == "gui":
        from docutranslate.app import run_app
        run_app(port=args.port)
        return

    if args.cmd == "version":
        from docutranslate import __version__
        print(__version__)
        return

    if args.cmd == "translate":
        input_path = Path(args.input)
        if not input_path.exists() or not input_path.is_file():
            raise SystemExit(f"找不到文件: {input_path}")

        # Fast path: .md passthrough when skip-translate and only need markdown output
        if (
            input_path.suffix.lower() == ".md"
            and args.skip_translate
            and (args.formats is None or set(args.formats) == {"markdown"})
        ):
            out_dir = Path(args.out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{input_path.stem}_translated.md"
            out_path.write_bytes(input_path.read_bytes())
            print(f"已生成: {out_path.resolve()}")
            return

        wf = _build_workflow(input_path, args)
        wf.read_path(input_path)
        # run translate synchronously
        wf.translate()

        out_dir = Path(args.out_dir)
        formats = args.formats
        _export_outputs(input_path, wf, out_dir, formats, save_attachments=args.save_attachments)
        return

    # Unknown / fallthrough
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
