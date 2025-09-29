# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0

from doctranslate.exporter.base import Exporter
from doctranslate.ir.document import Document

#TODO:Consider whether a separate document type needs to be created for EPUB
class EpubExporter(Exporter[Document]):

    def export(self,document:Document)->Document:
        ...