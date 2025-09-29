# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from doctranslate.exporter.ass.ass2ass_exporter import Ass2AssExporter
from doctranslate.exporter.ass.ass2html_exporter import Ass2HTMLExporterConfig, Ass2HTMLExporter
from doctranslate.exporter.base import ExporterConfig
from doctranslate.glossary.glossary import Glossary
from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.ass_translator import AssTranslatorConfig, AssTranslator
from doctranslate.workflow.base import WorkflowConfig, Workflow
from doctranslate.workflow.interfaces import HTMLExportable, AssExportable





@dataclass(kw_only=True)
class AssWorkflowConfig(WorkflowConfig):
    translator_config: AssTranslatorConfig
    html_exporter_config: Ass2HTMLExporterConfig


class AssWorkflow(Workflow[AssWorkflowConfig, Document, Document], HTMLExportable[Ass2HTMLExporterConfig],
                  AssExportable[ExporterConfig]):
    def __init__(self, config: AssWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self,document_original:Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = AssTranslator(translate_config)
        return document,translator


    def translate(self) -> Self:
        document, translator=self._pre_translate(self.document_original)
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

    def export_to_html(self, config: Ass2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(Ass2HTMLExporter(config))
        return docu.content.decode()

    def export_to_ass(self, _: ExporterConfig | None = None) -> str:
        docu = self._export(Ass2AssExporter())
        return docu.content.decode()

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: Ass2HTMLExporterConfig | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=Ass2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_ass(self, name: str = None, output_dir: Path | str = "./output",
                    _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Ass2AssExporter(), name=name, output_dir=output_dir)
        return self
