# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0

from doctranslate.exporter.docx.base import DocxExporter
from doctranslate.ir.document import Document


class Docx2DocxExporter(DocxExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
