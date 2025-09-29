# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from doctranslate.exporter.base import ExporterConfig
from doctranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig, Json2HTMLExporter
from doctranslate.exporter.js.json2json_exporter import Json2JsonExporter
from doctranslate.glossary.glossary import Glossary
from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.json_translator import JsonTranslatorConfig, JsonTranslator
from doctranslate.workflow.base import Workflow, WorkflowConfig
from doctranslate.workflow.interfaces import HTMLExportable, JsonExportable


@dataclass(kw_only=True)
class JsonWorkflowConfig(WorkflowConfig):
    translator_config: JsonTranslatorConfig
    html_exporter_config: Json2HTMLExporterConfig


class JsonWorkflow(Workflow[JsonWorkflowConfig, Document, Document], HTMLExportable[Json2HTMLExporterConfig],
                   JsonExportable[ExporterConfig]):
    def __init__(self, config: JsonWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self, document_original: Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = JsonTranslator(translate_config)
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

    def export_to_html(self, config: Json2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(Json2HTMLExporter(config))
        return docu.content.decode()

    def export_to_json(self, _: ExporterConfig | None = None) -> str:
        docu = self._export(Json2JsonExporter())
        return docu.content.decode()

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: Json2HTMLExporter | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=Json2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_json(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Json2JsonExporter(), name=name, output_dir=output_dir)
        return self
