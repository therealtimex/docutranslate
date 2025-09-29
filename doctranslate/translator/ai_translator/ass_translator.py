# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0

import asyncio
from dataclasses import dataclass
from typing import Self, Literal, List, Optional

import pysubs2

from doctranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class AssTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\\N"  # ASS line break is \N
    # Reserved for future use (styles/time ranges); currently translate all Dialogue lines
    translate_regions: Optional[List[str]] = None  # Not used currently


class AssTranslator(AiTranslator):
    def __init__(self, config: AssTranslatorConfig):
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
        self.translate_regions = config.translate_regions  # Not currently processed, interface reserved

    def _pre_translate(self, document: Document):
        """
        Parse ASS and extract text from Dialogue lines.
        Returns: subs object, items to translate, original texts.
        """
        try:
            content_str = document.content.decode('utf-8-sig')  # Common BOM
        except UnicodeDecodeError:
            content_str = document.content.decode('utf-8')

        subs = pysubs2.SSAFile.from_string(content_str)
        lines_to_translate = []

        for i, line in enumerate(subs):
            if line.type == "Dialogue":
                # Translate text only; keep styles and timing
                if isinstance(line.text, str) and line.text.strip():
                    lines_to_translate.append({
                        "index": i,  # position in subs
                        "original_text": line.text,
                        "line": line  # keep reference for modification
                    })

        original_texts = [item["original_text"] for item in lines_to_translate]
        return subs, lines_to_translate, original_texts

    def _after_translate(self, subs, lines_to_translate, translated_texts, original_texts):
        """
        Write translated text back into ASS according to insert_mode.
        """
        for i, item in enumerate(lines_to_translate):
            line = item["line"]
            translated_text = translated_texts[i]
            original_text = original_texts[i]

            if self.insert_mode == "replace":
                line.text = translated_text
            elif self.insert_mode == "append":
                line.text = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                line.text = translated_text + self.separator + original_text
            else:
                self.logger.error(f"Unsupported insert mode: {self.insert_mode}")

        # Output as string, then encode to bytes
        output_str = subs.to_string(format_="ass")
        return output_str.encode('utf-8-sig')  # with BOM for players

    def translate(self, document: Document) -> Self:
        subs, lines_to_translate, original_texts = self._pre_translate(document)

        if not lines_to_translate:
            print("\nNo subtitle lines found to translate.")
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        document.content = self._after_translate(subs, lines_to_translate, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        subs, lines_to_translate, original_texts = await asyncio.to_thread(self._pre_translate, document)

        if not lines_to_translate:
            print("\nNo subtitle lines found to translate.")
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        document.content = await asyncio.to_thread(
            self._after_translate, subs, lines_to_translate, translated_texts, original_texts
        )
        return self
