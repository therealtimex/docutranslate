# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from doctranslate.exporter.ass.base import AssExporter
from doctranslate.ir.document import Document


class Ass2AssExporter(AssExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
