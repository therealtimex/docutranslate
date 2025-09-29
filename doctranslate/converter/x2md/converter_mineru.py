# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import time
import zipfile
from dataclasses import dataclass
from typing import Hashable, Literal

import httpx

from doctranslate.converter.x2md.base import X2MarkdownConverter, X2MarkdownConverterConfig
from doctranslate.ir.attachment_manager import AttachMent
from doctranslate.ir.document import Document
from doctranslate.ir.markdown_document import MarkdownDocument
from doctranslate.utils.markdown_utils import embed_inline_image_from_zip

URL = 'https://mineru.net/api/v4/file-urls/batch'


@dataclass(kw_only=True)
class ConverterMineruConfig(X2MarkdownConverterConfig):
    mineru_token: str
    formula_ocr: bool = True
    model_version: Literal["pipeline", "vlm"] = "vlm"

    def gethash(self) -> Hashable:
        return self.formula_ocr, self.model_version


timeout = httpx.Timeout(
    connect=5.0,  # 连接超时 (建立连接的最长时间)
    read=200.0,  # 读取超时 (等待服务器响应的最长时间)
    write=200.0,  # 写入超时 (发送数据的最长时间)
    pool=1.0  # 从连接池获取连接的超时时间
)
# if USE_PROXY:
#     client = httpx.Client(proxies=get_httpx_proxies(), timeout=timeout, verify=False)
#     client_async = httpx.AsyncClient(proxies=get_httpx_proxies(), timeout=timeout, verify=False)
# else:
#     client = httpx.Client(trust_env=False, timeout=timeout, proxy=None, verify=False)
#     client_async = httpx.AsyncClient(trust_env=False, timeout=timeout, proxy=None, verify=False)

limits = httpx.Limits(max_connections=500, max_keepalive_connections=20)
client = httpx.Client(limits=limits, trust_env=False, timeout=timeout, proxy=None, verify=False)
client_async = httpx.AsyncClient(limits=limits, trust_env=False, timeout=timeout, proxy=None, verify=False)


class ConverterMineru(X2MarkdownConverter):
    def __init__(self, config: ConverterMineruConfig):
        super().__init__(config=config)
        self.mineru_token = config.mineru_token.strip()
        self.formula = config.formula_ocr
        self.model_version = config.model_version
        self.attachments: list[AttachMent] = []

    def _get_header(self):
        return {
            'Content-Type': 'application/json',
            "Authorization": f"Bearer {self.mineru_token}"
        }

    def _get_upload_data(self, document: Document):
        return {
            "enable_formula": self.formula,
            "language": "auto",
            "enable_table": True,
            "model_version": self.model_version,
            "files": [
                {"name": f"{document.name}", "is_ocr": True}
            ]
        }

    def upload(self, document: Document):
        # 获取上传链接
        response = client.post(URL, headers=self._get_header(), json=self._get_upload_data(document))
        response.raise_for_status()
        result = response.json()
        # print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            # print('batch_id:{},urls:{}'.format(batch_id, urls))
            # 获取
            res_upload = client.put(urls[0], content=document.content)
            res_upload.raise_for_status()
            # print(f"{urls[0]} upload success")
            return batch_id
        else:
            raise Exception('apply upload url failed,reason:{}'.format(result))

    async def upload_async(self, document: Document):
        # 获取上传链接
        response = await client_async.post(URL, headers=self._get_header(), json=self._get_upload_data(document))
        response.raise_for_status()
        result = response.json()
        # print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            # print('batch_id:{},urls:{}'.format(batch_id, urls))
            # 获取
            res_upload = await client_async.put(urls[0], content=document.content)
            res_upload.raise_for_status()
            # print(f"{urls[0]} upload success")
            return batch_id
        else:
            raise Exception('apply upload url failed,reason:{}'.format(result))

    def get_file_url(self, batch_id: str) -> str:
        while True:
            url = f'https://mineru.net/api/v4/extract-results/batch/{batch_id}'
            header = self._get_header()
            res = client.get(url, headers=header)
            res.raise_for_status()
            fileinfo = res.json()["data"]["extract_result"][0]
            if fileinfo["state"] == "done":
                file_url = fileinfo["full_zip_url"]
                return file_url
            else:
                time.sleep(3)

    async def get_file_url_async(self, batch_id: str) -> str:
        while True:
            url = f'https://mineru.net/api/v4/extract-results/batch/{batch_id}'
            header = self._get_header()
            res = await client_async.get(url, headers=header)
            res.raise_for_status()
            fileinfo = res.json()["data"]["extract_result"][0]
            if fileinfo["state"] == "done":
                file_url = fileinfo["full_zip_url"]
                return file_url
            else:
                await asyncio.sleep(3)

    def convert(self, document: Document) -> MarkdownDocument:
        self.logger.info(f"正在将文档转换为markdown,model_version:{self.model_version}")
        time1 = time.time()
        batch_id = self.upload(document)
        file_url = self.get_file_url(batch_id)
        content, mineru_parsed = get_md_from_zip_url_with_inline_images(zip_url=file_url)
        if mineru_parsed:
            self.attachments.append(AttachMent("mineru",Document.from_bytes(content=mineru_parsed, suffix=".zip", stem="mineru")))
        self.logger.info(f"已转换为markdown，耗时{time.time() - time1}秒")
        md_document = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md", stem=document.stem)
        return md_document

    async def convert_async(self, document: Document) -> MarkdownDocument:
        self.logger.info(f"正在将文档转换为markdown,model_version:{self.model_version}")
        time1 = time.time()
        batch_id = await self.upload_async(document)
        file_url = await self.get_file_url_async(batch_id)
        content, mineru_parsed = await get_md_from_zip_url_with_inline_images_async(zip_url=file_url)
        if mineru_parsed:
            self.attachments.append(AttachMent("mineru",Document.from_bytes(content=mineru_parsed, suffix=".zip", stem="mineru")))
        self.logger.info(f"已转换为markdown，耗时{time.time() - time1}秒")
        md_document = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md", stem=document.stem)
        return md_document

    def support_format(self) -> list[str]:
        return [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg"]


def get_md_from_zip_url_with_inline_images(
        zip_url: str,
        filename_in_zip: str = "full.md",
        encoding: str = "utf-8"
) -> tuple[str, bytes]:
    """
    从给定的ZIP文件URL中下载并提取指定文件的内容，
    并将Markdown文件中的相对路径图片转换为内联Base64图片。

    Args:
        zip_url (str): ZIP文件的下载链接。
        filename_in_zip (str): ZIP压缩包内目标Markdown文件的名称（包括路径）。
                               默认为 "full.md"。
        encoding (str): 目标文件的预期编码。默认为 "utf-8"。
    """
    try:
        print(f"正在从 {zip_url} 下载ZIP文件 (使用 httpx.get)...")
        response = client.get(zip_url)  # 增加超时
        response.raise_for_status()
        print("ZIP文件下载完成。")
        return embed_inline_image_from_zip(response.content, filename_in_zip=filename_in_zip,
                                           encoding=encoding), response.content


    except httpx.HTTPStatusError as e:
        raise Exception(
            f"HTTP 错误 (httpx): {e.response.status_code} - {e.request.url}\n响应内容: {e.response.text[:200]}...")
    except httpx.RequestError as e:
        raise Exception(f"下载ZIP文件时发生错误 (httpx): {e}")
    except zipfile.BadZipFile:
        raise Exception("错误: 下载的文件不是一个有效的ZIP压缩文件或已损坏。")
    except UnicodeDecodeError:
        raise Exception(f"错误: 无法使用 '{encoding}' 编码解码文件 '{filename_in_zip}' 的内容。")
    except Exception as e:
        import traceback
        traceback.print_exc()  # 打印完整的堆栈跟踪，便于调试
        raise Exception(f"发生未知错误: {e}")


async def get_md_from_zip_url_with_inline_images_async(
        zip_url: str,
        filename_in_zip: str = "full.md",
        encoding: str = "utf-8"
) -> tuple[str, bytes]:
    """
    从给定的ZIP文件URL中下载并提取指定文件的内容，
    并将Markdown文件中的相对路径图片转换为内联Base64图片。

    Args:
        zip_url (str): ZIP文件的下载链接。
        filename_in_zip (str): ZIP压缩包内目标Markdown文件的名称（包括路径）。
                               默认为 "full.md"。
        encoding (str): 目标文件的预期编码。默认为 "utf-8"。

    Returns:
        str : 如果成功，返回处理后的Markdown文本内容。
    """
    try:
        print(f"正在从 {zip_url} 下载ZIP文件 (使用 httpx.get)...")
        response = await client_async.get(zip_url)  # 增加超时
        response.raise_for_status()
        print("ZIP文件下载完成。")
        return await asyncio.to_thread(embed_inline_image_from_zip, response.content, filename_in_zip=filename_in_zip,
                                       encoding=encoding), response.content


    except httpx.HTTPStatusError as e:
        raise Exception(
            f"HTTP 错误 (httpx): {e.response.status_code} - {e.request.url}\n响应内容: {e.response.text[:200]}...")
    except httpx.RequestError as e:
        raise Exception(f"下载ZIP文件时发生错误 (httpx): {e}")
    except zipfile.BadZipFile:
        raise Exception("错误: 下载的文件不是一个有效的ZIP压缩文件或已损坏。")
    except UnicodeDecodeError:
        raise Exception(f"错误: 无法使用 '{encoding}' 编码解码文件 '{filename_in_zip}' 的内容。")
    except Exception as e:
        import traceback
        traceback.print_exc()  # 打印完整的堆栈跟踪，便于调试
        raise Exception(f"发生未知错误: {e}")


if __name__ == '__main__':
    pass
