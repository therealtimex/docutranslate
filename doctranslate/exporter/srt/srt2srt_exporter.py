# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from doctranslate.exporter.srt.base import SrtExporter
from doctranslate.ir.document import Document


class Srt2SrtExporter(SrtExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
