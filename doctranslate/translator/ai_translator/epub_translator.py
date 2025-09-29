# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import asyncio
import os
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any

from bs4 import BeautifulSoup

from doctranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class EpubTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class EpubTranslator(AiTranslator):
    """
    A translator for content in EPUB files.
    This version uses built-in `zipfile` and `xml` libraries, without depending on `ebooklib`.
    """

    def __init__(self, config: EpubTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        if not self.skip_translate:
            agent_config = SegmentsTranslateAgentConfig(
                custom_prompt=config.custom_prompt,
                to_lang=config.to_lang,
                base_url=config.base_url,
                api_key=config.api_key,
                model_id=config.model_id,
                temperature=config.temperature,
                thinking=config.thinking,
                concurrent=config.concurrent,
                timeout=config.timeout,
                logger=self.logger,
                glossary_dict=config.glossary_dict,
                retry=config.retry,
                system_proxy_enable=config.system_proxy_enable
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> tuple[
        Dict[str, bytes], List[Dict[str, Any]], List[str]
    ]:
        """
        Preprocess EPUB file and extract all text that needs translation.
        """
        all_files = {}
        items_to_translate = []
        original_texts = []

        # --- Step 1: Use zipfile to read EPUB content into memory ---
        with zipfile.ZipFile(BytesIO(document.content), 'r') as zf:
            for filename in zf.namelist():
                all_files[filename] = zf.read(filename)

        # --- Step 2: Parse metadata to find content files ---
        # 2.1: Parse container.xml to find .opf file path
        container_xml = all_files.get('META-INF/container.xml')
        if not container_xml:
            raise ValueError("Invalid EPUB: META-INF/container.xml not found")

        root = ET.fromstring(container_xml)
        # XML namespace, must be used when parsing
        ns = {'cn': 'urn:oasis:names:tc:opendocument:xmlns:container'}
        opf_path = root.find('cn:rootfiles/cn:rootfile', ns).get('full-path')
        opf_dir = os.path.dirname(opf_path)

        # 2.2: Parse .opf file to find manifest and spine
        opf_xml = all_files.get(opf_path)
        if not opf_xml:
            raise ValueError(f"Invalid EPUB: {opf_path} not found")

        opf_root = ET.fromstring(opf_xml)
        ns_opf = {'opf': 'http://www.idpf.org/2007/opf'}

        manifest_items = {}
        for item in opf_root.findall('opf:manifest/opf:item', ns_opf):
            item_id = item.get('id')
            href = item.get('href')
            # Path needs to be relative to .opf file location
            full_href = os.path.join(opf_dir, href).replace('\\', '/')
            manifest_items[item_id] = {'href': full_href, 'media_type': item.get('media-type')}

        spine_itemrefs = [item.get('idref') for item in opf_root.findall('opf:spine/opf:itemref', ns_opf)]

        # --- Step 3: Extract translatable content ---
        # Here we simply translate all xhtml/html files in the manifest
        for item_id, item_data in manifest_items.items():
            media_type = item_data['media_type']
            if media_type in ['application/xhtml+xml', 'text/html']:
                file_path = item_data['href']
                content_bytes = all_files.get(file_path)
                if not content_bytes:
                    self.logger.warning(f"File not found in EPUB: {file_path}")
                    continue

                soup = BeautifulSoup(content_bytes, "html.parser")
                for text_node in soup.find_all(string=True):
                    if (
                            text_node.parent.name not in ['style', 'script', 'head', 'title', 'meta', '[document]']
                            and not text_node.isspace()
                    ):
                        text = text_node.get_text(strip=True)
                        if text:
                            item_info = {
                                "file_path": file_path,
                                "text_node": text_node,
                                "original_text": text,
                            }
                            items_to_translate.append(item_info)
                            original_texts.append(text)

        return all_files, items_to_translate, original_texts

    def _after_translate(
            self,
            all_files: Dict[str, bytes],
            items_to_translate: List[Dict[str, Any]],
            translated_texts: List[str],
            original_texts: List[str],
    ) -> bytes:
        """
        Write translated text back and repackage as EPUB file.
        """
        modified_soups = {}  # Cache soup objects for each file

        for i, item_info in enumerate(items_to_translate):
            file_path = item_info["file_path"]
            text_node = item_info["text_node"]
            translated_text = translated_texts[i]
            original_text = original_texts[i]

            # Get or create soup object for this file
            if file_path not in modified_soups:
                # Find the root soup object that this node belongs to
                modified_soups[file_path] = text_node.find_parent('html')

            if self.insert_mode == "replace":
                new_text = translated_text
            elif self.insert_mode == "append":
                new_text = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                new_text = translated_text + self.separator + original_text
            else:
                new_text = translated_text

            text_node.replace_with(new_text)

        # Convert modified soup objects back to byte strings
        for file_path, soup in modified_soups.items():
            all_files[file_path] = str(soup).encode('utf-8')

        # --- Step 4: Create new EPUB (ZIP) file ---
        output_buffer = BytesIO()
        with zipfile.ZipFile(output_buffer, 'w') as zf_out:
            # Critical: mimetype must be the first file and cannot be compressed
            if 'mimetype' in all_files:
                zf_out.writestr('mimetype', all_files['mimetype'], compress_type=zipfile.ZIP_STORED)

            # Write all other files
            for filename, content in all_files.items():
                if filename != 'mimetype':
                    zf_out.writestr(filename, content, compress_type=zipfile.ZIP_DEFLATED)

        return output_buffer.getvalue()

    def translate(self, document: Document) -> Self:
        """
        Synchronously translate EPUB document.
        """
        all_files, items_to_translate, original_texts = self._pre_translate(document)
        if not items_to_translate:
            self.logger.info("\nNo plain text content found in file that needs translation.")
            return self
        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        document.content = self._after_translate(
            all_files, items_to_translate, translated_texts, original_texts
        )
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        Asynchronously translate EPUB document.
        """
        all_files, items_to_translate, original_texts = await asyncio.to_thread(
            self._pre_translate, document
        )
        if not items_to_translate:
            self.logger.info("\nNo plain text content found in file that needs translation.")
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(
                original_texts, self.chunk_size
            )
        else:
            translated_texts = original_texts
        document.content = await asyncio.to_thread(
            self._after_translate, all_files, items_to_translate, translated_texts, original_texts
        )
        return self
