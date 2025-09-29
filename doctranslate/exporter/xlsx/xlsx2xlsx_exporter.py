# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from doctranslate.exporter.xlsx.base import XlsxExporter
from doctranslate.ir.document import Document


class Xlsx2XlsxExporter(XlsxExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
