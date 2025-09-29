# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import re  # <--- 步骤 1: 导入 re 模块
from dataclasses import dataclass
import jinja2
import markdown
from doctranslate.exporter.md.base import MDExporter, MDExporterConfig
from doctranslate.ir.document import Document
from doctranslate.ir.markdown_document import MarkdownDocument
from doctranslate.utils.resource_utils import resource_path


@dataclass
class MD2HTMLExporterConfig(MDExporterConfig):
    cdn: bool = True


class MD2HTMLExporter(MDExporter):
    def __init__(self, config: MD2HTMLExporterConfig = None):
        config = config or MD2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: MarkdownDocument) -> Document:
        cdn = self.cdn
        # language=html
        pico = f'<style>{resource_path("static/pico.css").read_text(encoding="utf-8")}</style>' if not cdn else r'<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/picocss/2.1.1/pico.min.css" integrity="sha512-+4kjFgVD0n6H3xt19Ox84B56MoS7srFn60tgdWFuO4hemtjhySKyW4LnftYZn46k3THUEiTTsbVjrHai+0MOFw==" crossorigin="anonymous" referrerpolicy="no-referrer" />'
        html_template = resource_path("template/markdown.html").read_text(encoding="utf-8")
        katex_css = f'<link rel="stylesheet" href="/static/katex/katex.css"/>' if not cdn else r"""<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/katex.min.css" integrity="sha512-fHwaWebuwA7NSF5Qg/af4UeDx9XqUpYpOGgubo3yWu+b2IQR4UeQwbb42Ti7gVAjNtVoI/I9TEoYeu9omwcC6g==" crossorigin="anonymous" referrerpolicy="no-referrer" />"""
        katex_js = f'<script src="/static/katex/katex.js"></script>' if not cdn else r"""<script src="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/katex.min.js" integrity="sha512-LQNxIMR5rXv7o+b1l8+N1EZMfhG7iFZ9HhnbJkTp4zjNr5Wvst75AqUeFDxeRUa7l5vEDyUiAip//r+EFLLCyA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>"""
        auto_render = f'<script>{resource_path("static/autoRender.js").read_text(encoding="utf-8")}</script>' if not cdn else r"""<script src="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js" integrity="sha512-iWiuBS5nt6r60fCz26Nd0Zqe0nbk1ZTIQbl3Kv7kYsX+yKMUFHzjaH2+AnM6vp2Xs+gNmaBAVWJjSmuPw76Efg==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>"""

        # 这是正确且推荐的 JS 配置，它与 pymdownx.arithmatex 配合工作
        # 它只寻找 arithmatex 生成的 \(...\) 和 \[...\]
        # language=javascript
        render_math_in_element = r"""
        <script>
            document.addEventListener("DOMContentLoaded", function () {
                renderMathInElement(document.body, {
                    delimiters: [
                        {left: '\\[', right: '\\]', display: true},
                        {left: '\\(', right: '\\)', display: false}
                    ],
                    throwOnError: false,
                    errorColor: '#F5CF27',
                    macros: {
                        "\\f": "#1f(#2)"
                    },
                    trust: true,
                    strict: false
                })
            });
        </script>"""

        mermaid = f'<script>{resource_path("static/mermaid.js").read_text(encoding="utf-8")}</script>'

        # 扩展配置保持不变，我们仍然使用 arithmatex
        extensions = [
            'markdown.extensions.tables',
            'pymdownx.arithmatex',
            'pymdownx.superfences'
        ]

        extension_configs = {
            'pymdownx.arithmatex': {
                'generic': True,
                'block_tag': 'div',
                'inline_tag': 'span',
                'block_syntax': ['dollar', 'square'],
                'inline_syntax': ['dollar', 'round'],
                'tex_inline_wrap': ['\\(', '\\)'],
                'tex_block_wrap': ['\\[', '\\]'],
                'smart_dollar': True
            },
            'pymdownx.superfences': {
                'custom_fences': [
                    {
                        'name': 'mermaid',
                        'class': 'mermaid',
                        'format': lambda source, language, css_class, options, md,
                                         **kwargs: f'<pre class="{css_class}">{source}</pre>'
                    }
                ]
            }
        }

        content = document.content.decode()

        html_content = markdown.markdown(
            content,
            extensions=extensions,
            extension_configs=extension_configs
        )

        render = jinja2.Template(html_template).render(
            title=document.stem,
            pico=pico,
            katexCss=katex_css,
            katexJs=katex_js,
            autoRender=auto_render,
            markdown=html_content,
            renderMathInElement=render_math_in_element,
            mermaid=mermaid,
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)

if __name__ == '__main__':
    from pathlib import Path

    # d = Document.from_path(r"C:\Users\jxgm\Desktop\mcp文件夹\学习笔记\互联网认证授权机制\互联网认证授权机制.md")
    # d = Document.from_path(r"C:\Users\jxgm\Desktop\matrixcalc_translated.md")
    d = Document.from_path(r"C:\Users\jxgm\Desktop\full_translated.md")
    exporter = MD2HTMLExporter()
    d1 = exporter.export(d)
    path = Path(r"C:\Users\jxgm\Desktop\a.html")
    path.write_bytes(d1.content)