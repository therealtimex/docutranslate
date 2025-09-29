# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0

import asyncio
import os
import shlex
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Hashable, Literal

from doctranslate.converter.x2md.base import X2MarkdownConverter, X2MarkdownConverterConfig
from doctranslate.ir.attachment_manager import AttachMent
from doctranslate.ir.document import Document
from doctranslate.ir.markdown_document import MarkdownDocument
from doctranslate.utils.markdown_utils import embed_inline_image_from_zip, find_markdown_in_zip


@dataclass(kw_only=True)
class ConverterMineruLocalConfig(X2MarkdownConverterConfig):
    mode: Literal["cli_dir", "cli_zip"] = "cli_dir"
    cmd: str = "mineru"
    args_template: str = "--input {input} --output {output}"
    md_filename: str = "full.md"

    def gethash(self) -> Hashable:
        return self.mode, self.cmd, self.args_template, self.md_filename


class ConverterMineruLocal(X2MarkdownConverter):
    def __init__(self, config: ConverterMineruLocalConfig):
        super().__init__(config=config)
        self.attachments: list[AttachMent] = []

    def _run_cli(self, input_path: Path, output_target: Path):
        args_list = shlex.split(self.config.args_template.format(
            input=str(input_path), output=str(output_target)
        ))
        cmd = [self.config.cmd, *args_list]
        self.logger.info(f"Running local MinerU: {' '.join(shlex.quote(x) for x in cmd)}")
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )
            if res.stdout:
                self.logger.info(res.stdout.strip())
            if res.stderr:
                self.logger.debug(res.stderr.strip())
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Local MinerU executable not found: {self.config.cmd}. Please install and ensure it's in PATH, or use --mineru-local-cmd to specify the path."
            ) from e
        except subprocess.CalledProcessError as e:
            msg = e.stderr or e.stdout or str(e)
            raise RuntimeError(f"Local MinerU execution failed: {msg}")

    def _zip_dir(self, dir_path: Path) -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in dir_path.rglob('*'):
                if p.is_file():
                    zf.write(p, arcname=p.relative_to(dir_path))
        return buffer.getvalue()

    def _convert_common(self, document: Document) -> MarkdownDocument:
        with tempfile.TemporaryDirectory(prefix="mineru_local_") as tmp:
            tmpdir = Path(tmp)
            # Prepare input file
            if document.path and Path(document.path).exists():
                input_path = Path(document.path)
            else:
                input_path = tmpdir / (document.name or f"input{document.suffix}")
                input_path.write_bytes(document.content)

            if self.config.mode == "cli_zip":
                out_zip = tmpdir / "out.zip"
                self._run_cli(input_path, out_zip)
                zip_bytes = out_zip.read_bytes()
                try:
                    md_name = self.config.md_filename or find_markdown_in_zip(zip_bytes)
                except Exception:
                    md_name = "full.md"
                content = embed_inline_image_from_zip(zip_bytes, filename_in_zip=md_name)
                # Preserve zip as attachment
                self.attachments.append(AttachMent("mineru", Document.from_bytes(zip_bytes, ".zip", "mineru")))
                md_doc = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md",
                                                     stem=document.stem)
                return md_doc

            elif self.config.mode == "cli_dir":
                out_dir = tmpdir / "out"
                out_dir.mkdir(parents=True, exist_ok=True)
                self._run_cli(input_path, out_dir)
                # Try find markdown file
                md_path = out_dir / self.config.md_filename
                if not md_path.exists():
                    md_candidates = list(out_dir.rglob("*.md"))
                    if len(md_candidates) == 1:
                        md_path = md_candidates[0]
                    elif len(md_candidates) == 0:
                        raise RuntimeError("No .md files found in local MinerU output directory")
                    else:
                        raise RuntimeError("Multiple .md files found in local MinerU output directory, please specify via md_filename")

                # Pack dir to zip and reuse embed helper
                zip_bytes = self._zip_dir(out_dir)
                md_name_in_zip = str(md_path.relative_to(out_dir)).replace(os.sep, "/")
                content = embed_inline_image_from_zip(zip_bytes, filename_in_zip=md_name_in_zip)
                # Preserve zip as attachment
                self.attachments.append(AttachMent("mineru", Document.from_bytes(zip_bytes, ".zip", "mineru")))
                md_doc = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md",
                                                     stem=document.stem)
                return md_doc

            else:
                raise ValueError(f"Unsupported mode: {self.config.mode}")

    def convert(self, document: Document) -> MarkdownDocument:
        self.logger.info("Converting file to Markdown using local MinerU")
        return self._convert_common(document)

    async def convert_async(self, document: Document) -> MarkdownDocument:
        self.logger.info("(Async) Converting file to Markdown using local MinerU")
        return await asyncio.to_thread(self._convert_common, document)

    def support_format(self) -> list[str]:
        return [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg"]
