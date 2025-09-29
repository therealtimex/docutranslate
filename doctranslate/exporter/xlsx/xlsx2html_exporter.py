# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from io import BytesIO

from xlsx2html import xlsx2html

from doctranslate.exporter.base import ExporterConfig
from doctranslate.exporter.xlsx.base import XlsxExporter
from doctranslate.ir.document import Document


@dataclass
class Xlsx2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True


class Xlsx2HTMLExporter(XlsxExporter):
    def __init__(self, config: Xlsx2HTMLExporterConfig = None):
        config = config or Xlsx2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: Document) -> Document:
        html_content = xlsx2html(BytesIO(document.content), output=None).getvalue()
        return Document.from_bytes(content=html_content.encode("utf-8"), suffix=".html", stem=document.stem)
