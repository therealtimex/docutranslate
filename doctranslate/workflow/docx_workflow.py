# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from doctranslate.exporter.base import ExporterConfig
from doctranslate.exporter.docx.docx2docx_exporter import Docx2DocxExporter
from doctranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig, Docx2HTMLExporter
from doctranslate.glossary.glossary import Glossary
from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig, DocxTranslator
from doctranslate.workflow.base import Workflow, WorkflowConfig
from doctranslate.workflow.interfaces import HTMLExportable, DocxExportable


@dataclass(kw_only=True)
class DocxWorkflowConfig(WorkflowConfig):
    translator_config: DocxTranslatorConfig
    html_exporter_config: Docx2HTMLExporterConfig


class DocxWorkflow(Workflow[DocxWorkflowConfig, Document, Document], HTMLExportable[Docx2HTMLExporterConfig],
                   DocxExportable[ExporterConfig]):
    def __init__(self, config: DocxWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self, document_original: Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = DocxTranslator(translate_config)
        return document, translator

    def translate(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        translator.translate(document)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    async def translate_async(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        await translator.translate_async(document)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    def export_to_html(self, config: Docx2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(Docx2HTMLExporter(config))
        return docu.content.decode()

    def export_to_docx(self, _: ExporterConfig | None = None) -> bytes:
        docu = self._export(Docx2DocxExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: Docx2HTMLExporter | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=Docx2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_docx(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Docx2DocxExporter(), name=name, output_dir=output_dir)
        return self
