from docutranslate.exporter.base import Exporter
from docutranslate.ir.document import Document

#TODO:看情况是否需要为json单独写一个document类型
class JsonExporter(Exporter[Document]):

    def export(self,document:Document)->Document:
        ...