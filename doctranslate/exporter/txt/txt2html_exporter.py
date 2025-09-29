# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass

import jinja2

from doctranslate.exporter.base import ExporterConfig
from doctranslate.exporter.txt.base import TXTExporter
from doctranslate.ir.document import Document
from doctranslate.utils.resource_utils import resource_path


@dataclass
class TXT2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True


class TXT2HTMLExporter(TXTExporter):
    def __init__(self, config: TXT2HTMLExporterConfig = None):
        config = config or TXT2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: Document) -> Document:
        cdn = self.cdn
        html_template = resource_path("template/txt.html").read_text(encoding="utf-8")

        # language=html
        pico = f'<style>{resource_path("static/pico.css").read_text(encoding="utf-8")}</style>' if not cdn else r'<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/picocss/2.1.1/pico.min.css" integrity="sha512-+4kjFgVD0n6H3xt19Ox84B56MoS7srFn60tgdWFuO4hemtjhySKyW4LnftYZn46k3THUEiTTsbVjrHai+0MOFw==" crossorigin="anonymous" referrerpolicy="no-referrer" />'

        body='\n'.join([r'<p>'+para+'</p>' for para in document.content.decode().split("\n")])
        render = jinja2.Template(html_template).render(
            title=document.stem,
            pico=pico,
            body=body,
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)
