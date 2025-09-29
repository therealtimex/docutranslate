# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Self, Literal

import srt  # Import srt library to process subtitle files

from doctranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class SrtTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class SrtTranslator(AiTranslator):
    """
    A translator for SRT (.srt) subtitle files.
    It extracts text content from each subtitle block, translates it, and writes back the translated text according to configuration.
    """

    def __init__(self, config: SrtTranslatorConfig):
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

    def _pre_translate(self, document: Document):
        """
        Preprocessing step: Parse SRT file and extract all subtitle text.

        Returns:
            tuple: (List of parsed subtitle objects, List of original texts to be translated)
        """
        try:
            # Use utf-8-sig decoding to handle possible BOM (Byte Order Mark)
            srt_content = document.content.decode('utf-8-sig')
        except (UnicodeDecodeError, AttributeError) as e:
            self.logger.error(f"Unable to decode SRT file content, please ensure file encoding is UTF-8: {e}")
            return [], []

        # Use srt library to parse content
        try:
            subtitles = list(srt.parse(srt_content))
        except srt.SRTParseError as e:
            self.logger.error(f"Failed to parse SRT file: {e}")
            return [], []

        # Extract all original texts, prepare for batch translation
        original_texts = [sub.content for sub in subtitles]

        return subtitles, original_texts

    def _after_translate(self, subtitles: list[srt.Subtitle], translated_texts: list[str],
                         original_texts: list[str]) -> bytes:
        """
        Post-translation step: Write translated text back to subtitle objects according to configuration mode and generate new SRT file content.

        Returns:
            bytes: Byte stream of new SRT file content.
        """
        for i, sub in enumerate(subtitles):
            translated_text = translated_texts[i]
            original_text = original_texts[i]

            # Update subtitle content according to insert mode
            if self.insert_mode == "replace":
                sub.content = translated_text
            elif self.insert_mode == "append":
                # strip() to avoid extra whitespace between original and translated text
                sub.content = original_text.strip() + self.separator + translated_text.strip()
            elif self.insert_mode == "prepend":
                sub.content = translated_text.strip() + self.separator + original_text.strip()
            else:
                self.logger.error(f"Incorrect SrtTranslatorConfig parameter: insert_mode='{self.insert_mode}'")
                # Default fallback to replace mode to avoid program interruption
                sub.content = translated_text

        # Use srt library to recompose modified subtitle object list into SRT format string
        new_srt_content_str = srt.compose(subtitles)

        # Return UTF-8 encoded byte stream
        return new_srt_content_str.encode('utf-8')

    def translate(self, document: Document) -> Self:
        """
        Synchronously translate SRT document.
        """
        subtitles, original_texts = self._pre_translate(document)

        if not original_texts:
            self.logger.info("\nNo subtitle content found in the file that needs translation.")
            return self
        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        # --- Step 2: Call translation Agent ---
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # --- Step 3: Post-processing and update document content ---
        document.content = self._after_translate(subtitles, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        Asynchronously translate SRT document.
        """
        # Run I/O intensive operations in thread
        subtitles, original_texts = await asyncio.to_thread(self._pre_translate, document)

        if not original_texts:
            self.logger.info("\nNo subtitle content found in the file that needs translation.")
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # --- Step 2: Call translation Agent (async) ---
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # --- Step 3: Post-processing and update document content (I/O intensive) ---
        document.content = await asyncio.to_thread(
            self._after_translate, subtitles, translated_texts, original_texts
        )
        return self
