# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from doctranslate.exporter.md.base import MDExporter
from doctranslate.ir.markdown_document import MarkdownDocument, Document
from doctranslate.utils.markdown_utils import unembed_base64_images_to_zip


class MD2MDZipExporter(MDExporter):

    def export(self, document: MarkdownDocument) -> Document:
        return Document.from_bytes(suffix=".zip", content=unembed_base64_images_to_zip(document.content.decode(),
                                                                                       markdown_name=document.name),
                                   stem=document.stem)
