# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from doctranslate.ir.document import Document


class MarkdownDocument(Document):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.suffix=".md"