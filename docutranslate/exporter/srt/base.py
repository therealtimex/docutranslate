from docutranslate.exporter.base import Exporter
from docutranslate.ir.document import Document

#TODO:看情况是否需要为TXT单独写一个document类型
class SrtExporter(Exporter[Document]):

    def export(self,document:Document)->Document:
        ...