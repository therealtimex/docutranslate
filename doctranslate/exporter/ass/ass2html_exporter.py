# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass

import jinja2

from doctranslate.exporter.ass.base import AssExporter
from doctranslate.exporter.base import ExporterConfig

from doctranslate.ir.document import Document
from doctranslate.utils.resource_utils import resource_path


@dataclass
class Ass2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True


class Ass2HTMLExporter(AssExporter):
    def __init__(self, config: Ass2HTMLExporterConfig = None):
        config = config or Ass2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: Document) -> Document:
        cdn = self.cdn

        html_template = resource_path("template/ass.html").read_text(encoding="utf-8")

        render = jinja2.Template(html_template).render(
            ass_data=document.content.decode("utf-8")
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)


