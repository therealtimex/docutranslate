# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from doctranslate.exporter.txt.base import TXTExporter
from doctranslate.ir.document import Document


class TXT2TXTExporter(TXTExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
