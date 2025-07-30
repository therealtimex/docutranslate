from docutranslate.exporter.txt.base import TXTExporter
from docutranslate.ir.document import Document


class TXT2TXTExporter(TXTExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
