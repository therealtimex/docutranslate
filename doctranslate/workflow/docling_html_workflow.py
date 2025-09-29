# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0

import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self

from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import DocumentStream
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.settings import settings
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode

from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig, HtmlTranslator
from doctranslate.workflow.base import Workflow, WorkflowConfig
from doctranslate.workflow.interfaces import HTMLExportable


@dataclass(kw_only=True)
class DoclingHTMLWorkflowConfig(WorkflowConfig):
    converter_artifact: str | None = None
    translator_config: HtmlTranslatorConfig | None = None


class DoclingHTMLWorkflow(Workflow[DoclingHTMLWorkflowConfig, Document, Document], HTMLExportable):
    def __init__(self, config: DoclingHTMLWorkflowConfig):
        super().__init__(config=config)
        self.translator = HtmlTranslator(config.translator_config or HtmlTranslatorConfig(skip_translate=True))
        # Docling pipeline options
        self.pipeline_options = PdfPipelineOptions(artifacts_path=(config.converter_artifact or None))
        self.pipeline_options.do_ocr = False
        self.pipeline_options.images_scale = 4
        self.pipeline_options.generate_picture_images = True
        self.pipeline_options.table_structure_options.do_cell_matching = False

    def _convert_to_html(self, document: Document) -> Document:
        assert isinstance(document.name, str)
        self.logger.info("Using docling to generate layout-preserving HTML")
        settings.debug.profile_pipeline_timings = True
        converter = DocumentConverter(format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=self.pipeline_options)
        })
        result = converter.convert(DocumentStream(name=document.name, stream=BytesIO(document.content)))
        html_str = result.document.export_to_html(image_mode=ImageRefMode.EMBEDDED)
        return Document.from_bytes(content=html_str.encode("utf-8"), suffix=".html", stem=document.stem)

    def translate(self) -> Self:
        html_doc = self._convert_to_html(self.document_original)
        # translate in-place via HtmlTranslator
        self.translator.translate(html_doc)
        self.document_translated = html_doc
        return self

    async def translate_async(self) -> Self:
        html_doc = await asyncio.to_thread(self._convert_to_html, self.document_original)
        await self.translator.translate_async(html_doc)
        self.document_translated = html_doc
        return self

    def export_to_html(self, _=None) -> str:
        if self.document_translated is None:
            raise RuntimeError("Not translated yet. Please call translate or translate_async first.")
        return self.document_translated.content.decode("utf-8")

    def save_as_html(self, name: str = None, output_dir: str = "./output", _=None) -> Self:
        if self.document_translated is None:
            raise RuntimeError("Not translated yet. Please call translate or translate_async first.")
        from pathlib import Path
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = name or f"{self.document_translated.stem}.html"
        (out_dir / filename).write_bytes(self.document_translated.content)
        self.logger.info(f"File saved to {(out_dir / filename).resolve()}")
        return self
