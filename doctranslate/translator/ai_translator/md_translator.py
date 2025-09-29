# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Self
from doctranslate.context.md_mask_context import MDMaskUrisContext
from doctranslate.ir.markdown_document import MarkdownDocument
from doctranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator
from doctranslate.utils.markdown_splitter import split_markdown_text, join_markdown_texts


@dataclass
class MDTranslatorConfig(AiTranslatorConfig):
    ...


class MDTranslator(AiTranslator):
    def __init__(self, config: MDTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        if not self.skip_translate:
            from doctranslate.agents.markdown_agent import MDTranslateAgentConfig
            from doctranslate.agents import MDTranslateAgent
            agent_config = MDTranslateAgentConfig(custom_prompt=config.custom_prompt,
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
                                                  system_proxy_enable=config.system_proxy_enable)
            self.translate_agent = MDTranslateAgent(agent_config)

    def translate(self, document: MarkdownDocument) -> Self:
        self.logger.info("Translating markdown")
        with MDMaskUrisContext(document):
            chunks: list[str] = split_markdown_text(document.content.decode(), self.chunk_size)
            if self.glossary_agent:
                self.glossary_dict_gen = self.glossary_agent.send_segments(chunks, self.chunk_size)
                if self.translate_agent:
                    self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
            self.logger.info(f"Markdown split into {len(chunks)} chunks")
            if self.translate_agent:
                result: list[str] = self.translate_agent.send_chunks(chunks)
            else:
                result = chunks
            content = join_markdown_texts(result)
            # Perform some robustness enhancement operations
            content = content.replace(r'\（', r'\(')
            content = content.replace(r'\）', r'\)')

            document.content = content.encode()
        self.logger.info("Translation completed")
        return self

    async def translate_async(self, document: MarkdownDocument) -> Self:
        self.logger.info("Translating markdown")
        with MDMaskUrisContext(document):
            chunks: list[str] = split_markdown_text(document.content.decode(), self.chunk_size)

            if self.glossary_agent:
                self.glossary_dict_gen = await self.glossary_agent.send_segments_async(chunks, self.chunk_size)
                if self.translate_agent:
                    self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

            self.logger.info(f"Markdown split into {len(chunks)} chunks")
            if self.translate_agent:
                result: list[str] = await self.translate_agent.send_chunks_async(chunks)
            else:
                result = chunks

            def run():
                content = join_markdown_texts(result)
                # Perform some robustness enhancement operations
                content = content.replace(r'\（', r'\(')
                content = content.replace(r'\）', r'\)')
                document.content = content.encode()

            await asyncio.to_thread(run)
        self.logger.info("Translation completed")
        return self
