# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import argparse
import os
from pathlib import Path
import sys  # Used to check command line argument count
from typing import Any
import time
import json

from doctranslate.translator import default_params
from doctranslate.global_values.conditional_import import DOCLING_EXIST
from doctranslate.utils.dotenv import load_env_file
from doctranslate.utils.i18n import t

# Exit codes for orchestration environments
EC_OK = 0
EC_INVALID_INPUT = 10
EC_DEP_MISSING = 20
EC_LLM_ERROR = 30
EC_EXPORT_ERROR = 40


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
    if s in {".ass"}:
        return "ass"
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
                'doctranslate.agents.glossary_agent', fromlist=['GlossaryAgentConfig']
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
    html_cfg_ass = None

    if workflow_type == "markdown_based":
        from doctranslate.exporter.md.types import ConvertEngineType
        from doctranslate.workflow.md_based_workflow import (
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
            from doctranslate.converter.x2md.converter_mineru import ConverterMineruConfig
            token = ns.mineru_token or os.getenv("MINERU_TOKEN")
            if not token:
                raise SystemExit("mineru convert engine requires --mineru-token or MINERU_TOKEN env")
            converter_cfg = ConverterMineruConfig(
                mineru_token=token,
                formula_ocr=ns.mineru_formula_ocr,
                model_version=ns.mineru_model_version,
            )
        elif convert_engine == "mineru_local":
            from doctranslate.converter.x2md.converter_mineru_local import ConverterMineruLocalConfig
            converter_cfg = ConverterMineruLocalConfig(
                mode=ns.mineru_local_mode,
                cmd=ns.mineru_local_cmd,
                args_template=ns.mineru_local_args,
                md_filename=ns.mineru_local_md_file,
            )
        elif convert_engine == "docling":
            from doctranslate.global_values.conditional_import import DOCLING_EXIST
            if not DOCLING_EXIST:
                raise SystemExit("docling is not installed. Use mineru or install optional 'docling' extras.")
            if getattr(ns, 'preserve_layout', False):
                from doctranslate.workflow.docling_html_workflow import (
                    DoclingHTMLWorkflow, DoclingHTMLWorkflowConfig,
                )
                from doctranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig
                translator_cfg_html = HtmlTranslatorConfig(
                    **common_ai_args,
                    insert_mode=ns.insert_mode,
                    separator=ns.separator,
                )
                wf_cfg_html = DoclingHTMLWorkflowConfig(translator_config=translator_cfg_html)
                return DoclingHTMLWorkflow(config=wf_cfg_html)
            else:
                from doctranslate.converter.x2md.converter_docling import ConverterDoclingConfig
                converter_cfg = ConverterDoclingConfig()
        elif convert_engine == "identity":
            converter_cfg = None
        else:
            raise SystemExit(f"Unsupported convert engine: {convert_engine}")

        from doctranslate.translator.ai_translator.md_translator import MDTranslatorConfig
        translator_cfg = MDTranslatorConfig(**common_ai_args)
        wf_cfg = MarkdownBasedWorkflowConfig(
            convert_engine=convert_engine, converter_config=converter_cfg,
            translator_config=translator_cfg, html_exporter_config=html_cfg_md,
        )
        return MarkdownBasedWorkflow(config=wf_cfg)

    if workflow_type == "txt":
        from doctranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig
        from doctranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
        from doctranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
        translator_cfg = TXTTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        html_cfg_txt = TXT2HTMLExporterConfig(cdn=True)
        wf_cfg = TXTWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_txt)
        return TXTWorkflow(config=wf_cfg)

    if workflow_type == "json":
        from doctranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
        from doctranslate.workflow.json_workflow import JsonWorkflow, JsonWorkflowConfig
        from doctranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
        json_paths = ns.json_path or ["$..*"]
        translator_cfg = JsonTranslatorConfig(
            **common_ai_args,
            json_paths=json_paths,
        )
        html_cfg_json = Json2HTMLExporterConfig(cdn=True)
        wf_cfg = JsonWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_json)
        return JsonWorkflow(config=wf_cfg)

    if workflow_type == "xlsx":
        from doctranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
        from doctranslate.workflow.xlsx_workflow import XlsxWorkflow, XlsxWorkflowConfig
        from doctranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
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
        from doctranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
        from doctranslate.workflow.docx_workflow import DocxWorkflow, DocxWorkflowConfig
        from doctranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
        translator_cfg = DocxTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        html_cfg_docx = Docx2HTMLExporterConfig(cdn=True)
        wf_cfg = DocxWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_docx)
        return DocxWorkflow(config=wf_cfg)

    if workflow_type == "srt":
        from doctranslate.exporter.srt.srt2html_exporter import Srt2HTMLExporterConfig
        from doctranslate.workflow.srt_workflow import SrtWorkflow, SrtWorkflowConfig
        from doctranslate.translator.ai_translator.srt_translator import SrtTranslatorConfig
        translator_cfg = SrtTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        html_cfg_srt = Srt2HTMLExporterConfig(cdn=True)
        wf_cfg = SrtWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_srt)
        return SrtWorkflow(config=wf_cfg)

    if workflow_type == "epub":
        from doctranslate.exporter.epub.epub2html_exporter import Epub2HTMLExporterConfig
        from doctranslate.workflow.epub_workflow import EpubWorkflow, EpubWorkflowConfig
        from doctranslate.translator.ai_translator.epub_translator import EpubTranslatorConfig
        translator_cfg = EpubTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        html_cfg_epub = Epub2HTMLExporterConfig(cdn=True)
        wf_cfg = EpubWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_epub)
        return EpubWorkflow(config=wf_cfg)

    if workflow_type == "html":
        from doctranslate.workflow.html_workflow import HtmlWorkflow, HtmlWorkflowConfig
        from doctranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig
        translator_cfg = HtmlTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        wf_cfg = HtmlWorkflowConfig(translator_config=translator_cfg)
        return HtmlWorkflow(config=wf_cfg)

    if workflow_type == "ass":
        from doctranslate.exporter.ass.ass2html_exporter import Ass2HTMLExporterConfig
        from doctranslate.workflow.ass_workflow import AssWorkflow, AssWorkflowConfig
        from doctranslate.translator.ai_translator.ass_translator import AssTranslatorConfig
        translator_cfg = AssTranslatorConfig(
            **common_ai_args,
            insert_mode=ns.insert_mode,
            separator=ns.separator,
        )
        html_cfg_ass = Ass2HTMLExporterConfig(cdn=True)
        wf_cfg = AssWorkflowConfig(translator_config=translator_cfg, html_exporter_config=html_cfg_ass)
        return AssWorkflow(config=wf_cfg)

    raise SystemExit(f"Unsupported workflow type: {workflow_type}")


def _export_outputs(input_path: Path, workflow: Any, out_dir: Path, explicit_formats: list[str] | None, *, save_attachments: bool=False, lang: str = "en"):
    stem = input_path.stem
    suffix = input_path.suffix.lower()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build export map similar to the web app
    from doctranslate.workflow.interfaces import (
        HTMLExportable, MDFormatsExportable, TXTExportable, JsonExportable,
        XlsxExportable, CsvExportable, DocxExportable, SrtExportable, EpubExportable, AssExportable,
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
    if isinstance(workflow, AssExportable):
        export_map["ass"] = (workflow.export_to_ass, f"{stem}_translated.ass", True)

    selected = explicit_formats or list(export_map.keys())
    outputs: list[dict[str, Any]] = []
    for ftype in selected:
        if ftype not in export_map:
            print(t("skip_unsupported_format", lang=lang, ftype=ftype))
            continue
        export_func, filename, is_text = export_map[ftype]
        try:
            content = export_func()
            data = content.encode("utf-8") if is_text else content
            (out_dir / filename).write_bytes(data)
            print(t("generated", lang=lang, path=str((out_dir / filename).resolve())))
            outputs.append({
                "type": ftype,
                "path": str((out_dir / filename).resolve()),
                "is_text": is_text,
            })
        except ModuleNotFoundError as e:
            missing = str(e).split("'")[-2] if "'" in str(e) else str(e)
            print(t("skip_export_missing_dep", lang=lang, ftype=ftype, missing=missing))
        except Exception as e:
            print(t("export_failed", lang=lang, ftype=ftype, error=str(e)))

    # Save attachments (like glossary) if requested
    attachments: list[dict[str, Any]] = []
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
                print(t("attachment_generated", lang=lang, path=str((out_dir / att_name).resolve()), identifier=identifier))
                attachments.append({
                    "identifier": identifier,
                    "path": str((out_dir / att_name).resolve()),
                    "suffix": doc.suffix,
                })
    return {"outputs": outputs, "attachments": attachments}


def _add_translate_subparser(subparsers: argparse._SubParsersAction) -> None:
    sp = subparsers.add_parser(
        "translate",
        help="Translate a file and export results",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sp.add_argument("input", help="Path to the input file")
    sp.add_argument("--out-dir", default="output", help="Output directory")
    sp.add_argument("--workflow", choices=[
        "markdown_based", "txt", "json", "xlsx", "docx", "srt", "epub", "html", "ass"
    ], help="Override the inferred workflow type")
    sp.add_argument("--formats", nargs="*", help="Export formats, e.g. html markdown markdown_zip json xlsx csv docx srt epub")
    sp.add_argument("--preserve-layout", action="store_true", help="(PDF) Use Docling native HTML to better preserve layout")
    sp.add_argument("--save-attachments", action="store_true", help="Save attachments (e.g., docling.md, glossary)")
    sp.add_argument("--docpkg", action="store_true", help="Input is a document package directory (e.g., from docling CLI). Auto-detect index.html or document.md")
    sp.add_argument("--emit-manifest", help="Write JSON manifest to this path")
    sp.add_argument("--progress", choices=["none", "jsonl"], default="none", help="Emit step-by-step progress events")

    # AI and behavior
    sp.add_argument("--skip-translate", action="store_true", help="Parse/export only; do not call LLM")
    sp.add_argument("--base-url", help="LLM API base URL; defaults to OPENAI_BASE_URL")
    sp.add_argument("--api-key", help="LLM API key; defaults to OPENAI_API_KEY")
    sp.add_argument("--model-id", help="Model ID; defaults to OPENAI_MODEL")
    sp.add_argument("--to-lang", dest="to_lang", default="English", help="Target language")
    sp.add_argument("--custom-prompt", help="Custom translation prompt")

    sp.add_argument("--chunk-size", type=int, default=default_params["chunk_size"], help="Chunk size")
    sp.add_argument("--concurrent", type=int, default=default_params["concurrent"], help="Concurrency")
    sp.add_argument("--temperature", type=float, default=default_params["temperature"], help="Temperature")
    sp.add_argument("--timeout", type=int, default=default_params["timeout"], help="Timeout (seconds)")
    sp.add_argument("--thinking", choices=["default", "enable", "disable"], default=default_params["thinking"], help="Thinking mode (provider-specific)")
    sp.add_argument("--retry", type=int, default=default_params["retry"], help="Retry count on failure")

    # Insert mode for structured types
    sp.add_argument("--insert-mode", choices=["replace", "append", "prepend"], default="replace",
                    help="Insert mode (for txt/xlsx/docx/srt/epub/html)")
    sp.add_argument("--separator", default="\n", help="Separator used in append/prepend modes")

    # JSON options
    sp.add_argument("--json-path", action="append", help="JSONPath expression; can be repeated. Default: $..*")

    # XLSX options
    sp.add_argument("--xlsx-regions", nargs="*", help="XLSX translation regions, e.g. Sheet1!A1:B10 C:D E5 …")

    # Markdown-based convert options
    sp.add_argument("--convert-engine", choices=["mineru", "mineru_local", "docling", "identity"], help="markdown_based convert engine")
    sp.add_argument("--mineru-token", help="MinerU API token (or env MINERU_TOKEN)")
    sp.add_argument("--mineru-formula-ocr", action="store_true", help="MinerU formula OCR switch")
    sp.add_argument("--mineru-model-version", choices=["pipeline", "vlm"], default="vlm", help="MinerU model version")
    # mineru_local options
    sp.add_argument("--mineru-local-mode", choices=["cli_dir", "cli_zip"], default="cli_dir",
                    help="Local MinerU run mode: output directory or output zip")
    sp.add_argument("--mineru-local-cmd", default="mineru", help="Local MinerU executable command or path")
    sp.add_argument("--mineru-local-args", default="--input {input} --output {output}",
                    help="Local MinerU argument template, use {input} and {output} placeholders")
    sp.add_argument("--mineru-local-md-file", default="full.md", help="Markdown filename in local MinerU output")

    # Glossary options
    sp.add_argument("--glossary-enable", action="store_true", help="Enable glossary generation agent")
    sp.add_argument("--glossary-base-url", help="Glossary agent base URL (defaults to main)")
    sp.add_argument("--glossary-api-key", help="Glossary agent API key (defaults to main)")
    sp.add_argument("--glossary-model-id", help="Glossary agent model ID (defaults to main)")

    sp.set_defaults(cmd="translate")


def main():
    parser = argparse.ArgumentParser(
        description="doctranslate: Document translation tool (CLI + optional GUI)",
        epilog=(
            "Examples:\n"
            "  doctranslate gui -p 8081\n"
            "  doctranslate translate ./file.docx --to-lang English --base-url https://api.openai.com/v1 --model-id gpt-4o\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="cmd")

    # gui subcommand
    gui = subparsers.add_parser("gui", help="Start local Web UI")
    gui.add_argument("-p", "--port", type=int, default=None, help="Port (default: 8010)")
    gui.set_defaults(cmd="gui")

    # translate subcommand
    _add_translate_subparser(subparsers)

    # version subcommand
    ver = subparsers.add_parser("version", help="Show version")
    ver.set_defaults(cmd="version")

    # backward-compatible top-level flags (minimal)
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Equivalent to subcommand: gui"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=None, help="Port when using --interactive"
    )
    parser.add_argument(
        "--env-file", help="Load environment variables from file (default: ./.env)", default=None
    )
    parser.add_argument(
        "--no-env", action="store_true", help="Do not auto-load .env from current directory"
    )
    parser.add_argument(
        "--lang", choices=["en", "zh"], default=os.getenv("doctranslate_LANG", "en"), help="Language for CLI messages (default: en)"
    )

    # No-arg hint
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Load env vars from .env unless disabled
    env_path_used = None
    if not getattr(args, 'no_env', False):
        env_path_used, loaded_keys = load_env_file(args.env_file)
        if env_path_used and args.cmd == 'translate' and args.progress == 'jsonl':
            # emit a meta event to aid orchestration
            print(json.dumps({"event": "env_loaded", "path": env_path_used, "count": len(loaded_keys), "ts": time.time()}, ensure_ascii=False))

    # Back-compat: doctranslate -i [-p]
    if args.interactive and args.cmd is None:
        try:
            from doctranslate.app import run_app
        except ModuleNotFoundError as e:
            missing = str(e).split("'")[-2] if "'" in str(e) else str(e)
            print(t("missing_optional_dependency", lang=args.lang, missing=missing))
            raise SystemExit(EC_DEP_MISSING)
        except Exception as e:
            print(t("missing_optional_dependency", lang=args.lang, missing=str(e)))
            raise SystemExit(EC_DEP_MISSING)
        run_app(port=args.port)
        return

    if args.cmd == "gui":
        try:
            from doctranslate.app import run_app
        except ModuleNotFoundError as e:
            missing = str(e).split("'")[-2] if "'" in str(e) else str(e)
            print(t("missing_optional_dependency", lang=args.lang, missing=missing))
            raise SystemExit(EC_DEP_MISSING)
        except Exception as e:
            print(t("missing_optional_dependency", lang=args.lang, missing=str(e)))
            raise SystemExit(EC_DEP_MISSING)
        run_app(port=args.port)
        return

    if args.cmd == "version":
        from doctranslate import __version__
        print(__version__)
        return

    if args.cmd == "translate":
        def _emit(event: str, data: dict[str, Any] | None = None):
            if args.progress == "jsonl":
                payload = {"event": event, "ts": time.time()}
                if data:
                    payload.update(data)
                print(json.dumps(payload, ensure_ascii=False))

        original_input = Path(args.input)
        # Support document package input directory
        if args.docpkg or original_input.is_dir():
            if not original_input.exists() or not original_input.is_dir():
                print(t("docpkg_not_found", lang=args.lang, path=str(original_input)))
                raise SystemExit(EC_INVALID_INPUT)
            # Prefer layout-preserving HTML if exists, else Markdown
            html_candidate = original_input / "index.html"
            md_candidate = original_input / "document.md"
            chosen = None
            if html_candidate.exists():
                chosen = html_candidate
                args.workflow = args.workflow or "html"
            elif md_candidate.exists():
                chosen = md_candidate
                args.workflow = args.workflow or "markdown_based"
            else:
                # Fallback to first .md under directory
                for p in sorted(original_input.glob("*.md")):
                    chosen = p
                    args.workflow = args.workflow or "markdown_based"
                    break
            if not chosen:
                print(t("docpkg_missing_entry", lang=args.lang, path=str(original_input)))
                raise SystemExit(EC_INVALID_INPUT)
            input_path = chosen
        else:
            input_path = original_input
            if not input_path.exists() or not input_path.is_file():
                print(t("file_not_found", lang=args.lang, path=str(input_path)))
                raise SystemExit(EC_INVALID_INPUT)

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
            print(t("generated", lang=args.lang, path=str(out_path.resolve())))
            # Optional emit progress and manifest for orchestration
            if args.progress == "jsonl":
                print(json.dumps({"event": "build_workflow_start", "ts": time.time(), "path": str(input_path)}, ensure_ascii=False))
                print(json.dumps({"event": "build_workflow_end", "ts": time.time(), "workflow": "PassthroughMD"}, ensure_ascii=False))
                print(json.dumps({"event": "read_start", "ts": time.time()}))
                print(json.dumps({"event": "read_end", "ts": time.time(), "ms": 0}))
                print(json.dumps({"event": "translate_start", "ts": time.time()}))
                print(json.dumps({"event": "translate_end", "ts": time.time(), "ms": 0}))
                print(json.dumps({"event": "export_start", "ts": time.time()}))
                print(json.dumps({"event": "export_end", "ts": time.time(), "ms": 0, "count": 1}))
            if args.emit_manifest:
                from doctranslate import __version__
                manifest = {
                    "version": __version__,
                    "input": {
                        "path": str(input_path.resolve()),
                        "suffix": input_path.suffix.lower(),
                        "size": input_path.stat().st_size,
                        "docpkg_root": str(original_input.resolve()) if (args.docpkg or original_input.is_dir()) else None,
                    },
                    "workflow": "PassthroughMD",
                    "settings": {
                        "to_lang": args.to_lang,
                        "skip_translate": args.skip_translate,
                        "formats": ["markdown"],
                        "concurrent": args.concurrent,
                        "chunk_size": args.chunk_size,
                        "model_id": args.model_id or os.getenv("OPENAI_MODEL") or "",
                        "env_file": env_path_used,
                    },
                    "outputs": [{"type": "markdown", "path": str(out_path.resolve()), "is_text": True}],
                    "attachments": [],
                    "metrics": {"read_ms": 0, "translate_ms": 0, "export_ms": 0, "total_ms": 0},
                }
                man_path = Path(args.emit_manifest)
                man_path.parent.mkdir(parents=True, exist_ok=True)
                man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                print(t("generated", lang=args.lang, path=str(man_path.resolve())))
            return

        _emit("build_workflow_start", {"path": str(input_path)})
        try:
            wf = _build_workflow(input_path, args)
        except ModuleNotFoundError as e:
            _emit("error", {"stage": "build", "error": str(e)})
            print(t("missing_dependency", lang=args.lang, missing=str(e)))
            raise SystemExit(EC_DEP_MISSING)
        except SystemExit as e:
            # Map common dependency-related exit to a stable code
            msg = str(e)
            if "docling is not installed" in msg or "mineru" in msg:
                _emit("error", {"stage": "build", "error": msg})
                raise SystemExit(EC_DEP_MISSING)
            raise
        _emit("build_workflow_end", {"workflow": wf.__class__.__name__})

        _emit("read_start")
        t_read0 = time.time()
        wf.read_path(input_path)
        t_read1 = time.time()
        _emit("read_end", {"ms": int((t_read1 - t_read0) * 1000)})

        # run translate synchronously
        _emit("translate_start")
        t_tr0 = time.time()
        try:
            wf.translate()
        except Exception as e:
            _emit("error", {"stage": "translate", "error": str(e)})
            print(f"Translation failed: {e}")
            raise SystemExit(EC_LLM_ERROR)
        t_tr1 = time.time()
        _emit("translate_end", {"ms": int((t_tr1 - t_tr0) * 1000)})

        out_dir = Path(args.out_dir)
        formats = args.formats
        _emit("export_start")
        t_ex0 = time.time()
        result = _export_outputs(input_path, wf, out_dir, formats, save_attachments=args.save_attachments, lang=args.lang)
        t_ex1 = time.time()
        _emit("export_end", {"ms": int((t_ex1 - t_ex0) * 1000), "count": len(result.get("outputs", []))})

        # Optional manifest
        if args.emit_manifest:
            from doctranslate import __version__
            manifest = {
                "version": __version__,
                "input": {
                    "path": str(input_path.resolve()),
                    "suffix": input_path.suffix.lower(),
                    "size": input_path.stat().st_size,
                    "docpkg_root": str(original_input.resolve()) if (args.docpkg or original_input.is_dir()) else None,
                },
                "workflow": wf.__class__.__name__,
                "settings": {
                    "to_lang": args.to_lang,
                    "skip_translate": args.skip_translate,
                    "formats": formats,
                    "concurrent": args.concurrent,
                    "chunk_size": args.chunk_size,
                    "model_id": args.model_id or os.getenv("OPENAI_MODEL") or "",
                    "env_file": env_path_used,
                    "lang": args.lang,
                    "lang": args.lang,
                },
                "outputs": result.get("outputs", []),
                "attachments": result.get("attachments", []),
                "metrics": {
                    "read_ms": int((t_read1 - t_read0) * 1000),
                    "translate_ms": int((t_tr1 - t_tr0) * 1000),
                    "export_ms": int((t_ex1 - t_ex0) * 1000),
                    "total_ms": int((t_ex1 - t_read0) * 1000),
                },
            }
            man_path = Path(args.emit_manifest)
            man_path.parent.mkdir(parents=True, exist_ok=True)
            man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            print(t("generated", lang=args.lang, path=str(man_path.resolve())))
        # If nothing exported, treat as exporter error
        if not result.get("outputs"):
            _emit("error", {"stage": "export", "error": "no outputs generated"})
            raise SystemExit(EC_EXPORT_ERROR)
        return

    # Unknown / fallthrough
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
