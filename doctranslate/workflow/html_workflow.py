# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from doctranslate.exporter.base import ExporterConfig
from doctranslate.exporter.html.html2html_exporter import Html2HtmlExporter
from doctranslate.glossary.glossary import Glossary

from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig, HtmlTranslator
from doctranslate.workflow.base import Workflow, WorkflowConfig
from doctranslate.workflow.interfaces import HTMLExportable


@dataclass(kw_only=True)
class HtmlWorkflowConfig(WorkflowConfig):
    translator_config: HtmlTranslatorConfig



class HtmlWorkflow(Workflow[HtmlWorkflowConfig, Document, Document], HTMLExportable):
    def __init__(self, config: HtmlWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self, document_original: Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = HtmlTranslator(translate_config)
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

    def export_to_html(self, _: ExporterConfig = None) -> str:

        docu = self._export(Html2HtmlExporter())
        return docu.content.decode()


    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Html2HtmlExporter(), name=name, output_dir=output_dir)
        return self
