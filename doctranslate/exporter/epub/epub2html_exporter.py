# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import base64
import io
import os
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree
from pathlib import Path
import re
import mimetypes

from bs4 import BeautifulSoup

from doctranslate.exporter.base import ExporterConfig
from doctranslate.exporter.epub.base import EpubExporter
from doctranslate.ir.document import Document


@dataclass
class Epub2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True


class Epub2HTMLExporter(EpubExporter):
    def __init__(self, config: Epub2HTMLExporterConfig = None):
        config = config or Epub2HTMLExporterConfig()
        super().__init__(config=config)

    def _extract_opf_path(self, zip_file):
        """从 META-INF/container.xml 中提取 OPF 文件路径"""
        try:
            container_xml = zip_file.read('META-INF/container.xml')
            container_root = ElementTree.fromstring(container_xml)

            # 查找 rootfile 元素
            rootfile = container_root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
            if rootfile is not None:
                return rootfile.get('full-path')
        except (KeyError, ElementTree.ParseError):
            pass

        # 如果无法从 container.xml 获取，尝试常见的路径
        for common_path in ['content.opf', 'OEBPS/content.opf', 'OPS/content.opf']:
            try:
                zip_file.getinfo(common_path)
                return common_path
            except KeyError:
                continue

        raise FileNotFoundError("无法找到 OPF 文件")

    def _parse_opf(self, opf_content):
        """解析 OPF 文件，获取阅读顺序和文件信息"""
        root = ElementTree.fromstring(opf_content)

        # 定义命名空间
        ns = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }

        # 获取 manifest 中的所有项目
        manifest_items = {}
        manifest = root.find('.//opf:manifest', ns)
        if manifest is not None:
            for item in manifest.findall('opf:item', ns):
                item_id = item.get('id')
                href = item.get('href')
                media_type = item.get('media-type')
                manifest_items[item_id] = {
                    'href': href,
                    'media-type': media_type
                }

        # 获取 spine 中的阅读顺序
        reading_order = []
        spine = root.find('.//opf:spine', ns)
        if spine is not None:
            for itemref in spine.findall('opf:itemref', ns):
                idref = itemref.get('idref')
                if idref in manifest_items:
                    reading_order.append(manifest_items[idref]['href'])

        return manifest_items, reading_order

    def _process_html_content(self, html_content, zip_file, base_path, manifest_items):
        """处理 HTML 内容，内嵌图片和样式"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # 处理图片
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                # 构建完整路径
                img_path = self._resolve_path(base_path, src)
                try:
                    img_data = zip_file.read(img_path)
                    # 获取 MIME 类型
                    mime_type, _ = mimetypes.guess_type(img_path)
                    if mime_type:
                        # 转换为 base64 data URI
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        data_uri = f"data:{mime_type};base64,{img_base64}"
                        img['src'] = data_uri
                except KeyError:
                    # 如果图片不存在，保持原路径
                    pass

        # 处理内联样式 (<style> 标签)
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                # 处理 CSS 中的 url() 引用
                style_tag.string = self._process_css_urls(
                    style_tag.string, zip_file, base_path
                )

        # 处理外部样式表
        for link in soup.find_all('link', {'rel': 'stylesheet'}):
            href = link.get('href')
            if href:
                css_path = self._resolve_path(base_path, href)
                try:
                    css_content = zip_file.read(css_path).decode('utf-8')
                    # 处理 CSS 中的 URL 引用
                    css_content = self._process_css_urls(css_content, zip_file, base_path)

                    # 替换 link 标签为 style 标签
                    style_tag = soup.new_tag('style')
                    style_tag.string = css_content
                    link.replace_with(style_tag)
                except (KeyError, UnicodeDecodeError):
                    # 如果样式表不存在或无法解码，移除 link 标签
                    link.decompose()

        return str(soup)

    def _process_css_urls(self, css_content, zip_file, base_path):
        """处理 CSS 中的 url() 引用"""

        def replace_url(match):
            url = match.group(1).strip('\'"')
            if url.startswith(('http://', 'https://', 'data:')):
                return match.group(0)  # 保持外部链接不变

            try:
                resource_path = self._resolve_path(base_path, url)
                resource_data = zip_file.read(resource_path)
                mime_type, _ = mimetypes.guess_type(resource_path)
                if mime_type:
                    resource_base64 = base64.b64encode(resource_data).decode('utf-8')
                    return f'url("data:{mime_type};base64,{resource_base64}")'
            except KeyError:
                pass

            return match.group(0)  # 保持原样

        # 匹配 url() 函数
        return re.sub(r'url\(([^)]+)\)', replace_url, css_content)

    def _resolve_path(self, base_path, relative_path):
        """解析相对路径为绝对路径"""
        if relative_path.startswith('/'):
            return relative_path.lstrip('/')

        base_dir = os.path.dirname(base_path)
        if base_dir:
            return os.path.join(base_dir, relative_path).replace('\\', '/')
        else:
            return relative_path

    def _find_html_files(self, zip_file):
        """查找 EPUB 中的所有 HTML 文件"""
        html_files = []
        for file_info in zip_file.filelist:
            filename = file_info.filename
            if filename.lower().endswith(('.html', '.htm', '.xhtml')) and not filename.startswith('META-INF/'):
                html_files.append(filename)
        return sorted(html_files)

    # def _debug_epub_structure(self, zip_file):
        """调试 EPUB 结构，打印所有文件"""
        print("=== EPUB 文件结构 ===")
        for file_info in zip_file.filelist:
            print(f"文件: {file_info.filename}")
        print("==================")

    def export(self, document: Document) -> Document:
        """
        将 EPUB 文件的二进制内容转换为单个 HTML 文件。

        :param document: 包含 EPUB 二进制内容的 Document 对象。
        :return: 包含单个 HTML 文件内容的 Document 对象。
        """
        epub_bytes = document.content

        with zipfile.ZipFile(io.BytesIO(epub_bytes), 'r') as zip_file:
            # 调试：打印 EPUB 结构
            # self._debug_epub_structure(zip_file)

            try:
                # 1. 提取 OPF 文件路径
                opf_path = self._extract_opf_path(zip_file)
                opf_content = zip_file.read(opf_path)

                # 2. 解析 OPF 文件
                manifest_items, reading_order = self._parse_opf(opf_content)

                # print(f"OPF 路径: {opf_path}")
                # print(f"阅读顺序: {reading_order}")
                # print(f"清单项目: {list(manifest_items.keys())}")

                # 3. 按阅读顺序读取和处理 HTML 文件
                combined_html_parts = []
                base_path = os.path.dirname(opf_path)

                # 尝试处理阅读顺序中的文件
                processed_files = set()
                for html_file in reading_order:
                    html_path = self._resolve_path(base_path, html_file)

                    # 尝试多种路径变体
                    possible_paths = [
                        html_path,
                        html_file,  # 原始路径
                        html_file.replace('.html', ''),  # 去掉 .html 后缀
                        html_file.replace('.htm.html', '.htm'),  # 处理双后缀
                    ]

                    file_found = False
                    for path_variant in possible_paths:
                        try:
                            html_content = zip_file.read(path_variant).decode('utf-8')
                            processed_html = self._process_html_content(
                                html_content, zip_file, path_variant, manifest_items
                            )

                            # 提取 body 内容（如果存在）
                            soup = BeautifulSoup(processed_html, 'html.parser')
                            body = soup.find('body')
                            if body:
                                combined_html_parts.append(str(body))
                            else:
                                combined_html_parts.append(processed_html)

                            processed_files.add(path_variant)
                            file_found = True
                            # print(f"成功处理文件: {path_variant}")
                            break

                        except (KeyError, UnicodeDecodeError):
                            continue

                    # if not file_found:
                    #     print(f"警告：无法找到文件 {html_file}，尝试的路径: {possible_paths}")

            except Exception as e:
                # print(f"解析 OPF 失败，使用备用方法: {e}")
                combined_html_parts = []
                processed_files = set()

            # 4. 如果没有成功处理任何文件，尝试直接处理所有 HTML 文件
            if not combined_html_parts:
                # print("使用备用方法：处理所有发现的 HTML 文件")
                html_files = self._find_html_files(zip_file)

                for html_file in html_files:
                    if html_file in processed_files:
                        continue  # 跳过已处理的文件

                    try:
                        html_content = zip_file.read(html_file).decode('utf-8')
                        processed_html = self._process_html_content(
                            html_content, zip_file, html_file, {}
                        )

                        # 提取 body 内容（如果存在）
                        soup = BeautifulSoup(processed_html, 'html.parser')
                        body = soup.find('body')
                        if body:
                            combined_html_parts.append(str(body))
                        else:
                            combined_html_parts.append(processed_html)

                        # print(f"备用方法成功处理: {html_file}")

                    except (KeyError, UnicodeDecodeError) as e:
                        # print(f"备用方法处理失败 {html_file}: {e}")
                        continue

            # 5. 组合成完整的 HTML 文档
            if combined_html_parts:
                # 创建基本的 HTML 结构
                html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{document.stem}</title>
    <style>
        body {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        .chapter {{
            margin-bottom: 2em;
            page-break-after: always;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
    <div class="epub-content">
{''.join(f'<div class="chapter">{part}</div>' for part in combined_html_parts)}
    </div>
</body>
</html>"""
                # print(f"成功组合 {len(combined_html_parts)} 个部分的内容")
            else:
                html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>{document.stem}</title>
</head>
<body>
    <h1>错误：无法提取 EPUB 内容</h1>
    <p>未能找到有效的 HTML 内容文件。</p>
    <p>请检查 EPUB 文件格式是否正确。</p>
</body>
</html>"""
                # print("警告：没有找到任何有效的 HTML 内容")

        return Document.from_bytes(content=html_content.encode("utf-8"), suffix=".html", stem=document.stem)


if __name__ == '__main__':
    from pathlib import Path

    doc_original = Document.from_path(r"C:\Users\jxgm\Downloads\pg6593-images.epub")
    html_exp = Epub2HTMLExporter().export(doc_original)
    Path(r"C:\Users\jxgm\Desktop\translate\doctranslate\tests\output\output.html").write_bytes(html_exp.content)