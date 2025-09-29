# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from io import BytesIO, StringIO

import openpyxl
import csv
from doctranslate.exporter.xlsx.base import XlsxExporter
from doctranslate.ir.document import Document


class Xlsx2CsvExporter(XlsxExporter):

    def export(self, document: Document) -> Document:
        workbook = openpyxl.load_workbook(BytesIO(document.content))
        sheet = workbook.active

        # 2. 使用 StringIO 作为文本缓冲区
        text_buffer = StringIO()

        # 3. 直接将缓冲区传递给 csv.writer
        writer = csv.writer(text_buffer)

        # 遍历工作表中的每一行
        for row in sheet.rows:
            writer.writerow([cell.value for cell in row])

        # 4. 将文本缓冲区的内容编码为 bytes
        output_bytes = text_buffer.getvalue().encode('utf-8')

        # 5. 返回一个后缀为 .csv 的 Document
        return Document.from_bytes(content=output_bytes, suffix=".csv", stem=document.stem)




