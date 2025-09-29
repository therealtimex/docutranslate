# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Self, Literal, List

from doctranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class TXTTranslatorConfig(AiTranslatorConfig):
    """
    Configuration class for TXTTranslator.

    Attributes:
        insert_mode (Literal["replace", "append", "prepend"]):
            Specifies the mode for inserting translated text.
            - "replace": Replace original text with translated text.
            - "append": Append translated text after original text.
            - "prepend": Prepend translated text before original text.
            Default is "replace".
        separator (str):
            String used to separate original and translated text in "append" or "prepend" modes.
            Default is newline character "\n".
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class TXTTranslator(AiTranslator):
    """
    A translator for plain text (.txt) files.
    It reads file content line by line, translates each line, and writes back the translated text according to configuration.
    """

    def __init__(self, config: TXTTranslatorConfig):
        """
        Initialize TXTTranslator.

        Args:
            config (TxtTranslatorConfig): Configuration for the translator.
        """
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

    def _pre_translate(self, document: Document) -> List[str]:
        """
        Preprocessing step: Parse TXT file and split text by lines.

        Args:
            document (Document): Document object to be processed.

        Returns:
            List[str]: List of original text lines to be translated.
        """
        try:
            # Use utf-8-sig decoding to handle possible BOM (Byte Order Mark)
            txt_content = document.content.decode('utf-8-sig')
        except (UnicodeDecodeError, AttributeError) as e:
            self.logger.error(f"Unable to decode TXT file content, please ensure file encoding is UTF-8: {e}")
            return []

        # Split text by lines and preserve empty lines as they may be part of formatting
        original_texts = txt_content.splitlines()

        return original_texts

    def _after_translate(self, translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        Post-translation step: Merge translated text with original text according to configuration mode and generate new TXT file content.

        Args:
            translated_texts (List[str]): List of translated text lines.
            original_texts (List[str]): List of original text lines.

        Returns:
            bytes: Byte stream of new TXT file content.
        """
        processed_lines = []
        for i, original_text in enumerate(original_texts):
            # If original text is empty line or contains only whitespace, keep it as is without translation processing
            if not original_text.strip():
                processed_lines.append(original_text)
                continue

            translated_text = translated_texts[i]

            # Update content according to insert mode
            if self.insert_mode == "replace":
                processed_lines.append(translated_text)
            elif self.insert_mode == "append":
                # strip() to avoid extra whitespace between original and translated text
                processed_lines.append(original_text.strip() + self.separator + translated_text.strip())
            elif self.insert_mode == "prepend":
                processed_lines.append(translated_text.strip() + self.separator + original_text.strip())
            else:
                self.logger.error(f"Incorrect TxtTranslatorConfig parameter: insert_mode='{self.insert_mode}'")
                # Default fallback to replace mode to avoid program interruption
                processed_lines.append(translated_text)

        # Reassemble all processed lines into a single string, separated by newlines
        new_txt_content_str = "\n".join(processed_lines)

        # Return UTF-8 encoded byte stream
        return new_txt_content_str.encode('utf-8')

    def translate(self, document: Document) -> Self:
        """
        Synchronously translate TXT document.

        Args:
            document (Document): Document object to be translated.

        Returns:
            Self: Returns translator instance to support method chaining.
        """
        original_texts = self._pre_translate(document)

        if not original_texts:
            self.logger.info("\nNo translatable text content found in the file.")
            return self

        # Filter out lines containing only whitespace to avoid unnecessary translation API calls
        texts_to_translate = [text for text in original_texts if text.strip()]

        # --- Step 1: (Optional) Terminology extraction ---
        if self.glossary_agent and texts_to_translate:
            self.glossary_dict_gen = self.glossary_agent.send_segments(texts_to_translate, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # --- Step 2: Call translation Agent ---
        translated_texts_map = {}
        if self.translate_agent and texts_to_translate:
            translated_segments = self.translate_agent.send_segments(texts_to_translate, self.chunk_size)
            translated_texts_map = dict(zip(texts_to_translate, translated_segments))

        # Map translation results back to original line list, keeping non-translated lines unchanged
        final_translated_texts = [translated_texts_map.get(text, text) for text in original_texts]

        # --- Step 3: Post-processing and update document content ---
        document.content = self._after_translate(final_translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        Asynchronously translate TXT document.

        Args:
            document (Document): Document object to be translated.

        Returns:
            Self: Returns translator instance to support method chaining.
        """
        # Run I/O intensive operations in thread
        original_texts = await asyncio.to_thread(self._pre_translate, document)

        if not original_texts:
            self.logger.info("\nNo translatable text content found in the file.")
            return self

        # Filter out lines containing only whitespace
        texts_to_translate = [text for text in original_texts if text.strip()]

        # --- Step 1: (Optional) Terminology extraction (async) ---
        if self.glossary_agent and texts_to_translate:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(texts_to_translate, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # --- Step 2: Call translation Agent (async) ---
        translated_texts_map = {}
        if self.translate_agent and texts_to_translate:
            translated_segments = await self.translate_agent.send_segments_async(texts_to_translate, self.chunk_size)
            translated_texts_map = dict(zip(texts_to_translate, translated_segments))

        # Map translation results back to original line list
        final_translated_texts = [translated_texts_map.get(text, text) for text in original_texts]

        # --- Step 3: Post-processing and update document content (I/O intensive) ---
        document.content = await asyncio.to_thread(
            self._after_translate, final_translated_texts, original_texts
        )
        return self