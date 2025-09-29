# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0

import asyncio
import json
from dataclasses import dataclass
from json import JSONDecodeError
from logging import Logger

import json_repair

from doctranslate.agents import AgentConfig, Agent
from doctranslate.agents.agent import AgentResultError
from doctranslate.utils.json_utils import segments2json_chunks


@dataclass
class GlossaryAgentConfig(AgentConfig):
    to_lang: str


class GlossaryAgent(Agent):
    def __init__(self, config: GlossaryAgentConfig):
        super().__init__(config)
        self.to_lang = config.to_lang
        self.system_prompt = f"""
# Role
You are a professional glossary extractor

# Task
You will receive a JSON-formatted list of paragraphs where keys are paragraph numbers and values are paragraph contents.
You need to extract person names and location names from these paragraphs and translate these terms into {self.to_lang}.
Finally, output a glossary of original terms:translated terms

# Requirements
- The original language is identified based on the context.The target language is {self.to_lang}
- The src in the output glossary must exactly match the original term in original language, while dst is the {self.to_lang} translation of the term
- Do not include special tags or tags formatted as `<ph-xxxxxx>` in the glossary
- The same src should only appear once in the glossary without repetition
- Do not include common nouns in the glossary.

# Output
The output format should be plain JSON text in a list format
{[{"src": "<Original Term>", "dst": "<Translated Term>"}]}

# Example1(Assuming the source language is English and the target language is Chinese in the example)
## Input
{{"0":"Jobs likes apples","1":"Bill Gates is sunbathing in Shanghai."}}
## Output
{r'[{"src": "Jobs", "dst": "乔布斯"}, {"src": "Bill Gates", "dst": "比尔盖茨"}, {"src": "Shanghai", "dst": "上海"}]'}
"""

    def _result_handler(self, result: str, origin_prompt: str, logger: Logger):
        if result == "":
            if origin_prompt.strip()!="":
                logger.error("Result is empty but original text is not empty")
                raise AgentResultError("Result is empty but original text is not empty")
            return []
        try:
            repaired_result = json_repair.loads(result)
            if not isinstance(repaired_result, list):
                raise AgentResultError(f"GlossaryAgent returned result is not in list JSON format, result: {result}")
            return repaired_result
        except (RuntimeError, JSONDecodeError) as e:
            # Wrap parsing error as ValueError so it can be caught and retried by send method
            raise AgentResultError(f"Result cannot be parsed correctly: {e.__repr__()}")

    def _error_result_handler(self, origin_prompt: str, logger: Logger):
        if origin_prompt == "":
            return []
        try:
            return json_repair.loads(origin_prompt)
        except (RuntimeError, JSONDecodeError):
            logger.error(f"Original prompt is also not in valid JSON format: {origin_prompt}")
            return [] # Return empty list if original prompt is also invalid

    def send_segments(self, segments: list[str], chunk_size: int):
        self.logger.info(f"Starting glossary extraction, to_lang:{self.to_lang}")
        result = {}
        indexed_originals, chunks, merged_indices_list = segments2json_chunks(segments, chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
        translated_chunks = super().send_prompts(prompts=prompts,
                                                 result_handler=self._result_handler,
                                                 error_result_handler=self._error_result_handler)
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, list):
                    self.logger.error(f"Received chunk is not a valid list, skipped: {chunk}")
                    continue
                glossary_dict = {d["src"]: d["dst"] for d in chunk if isinstance(d, dict) and "src" in d and "dst" in d}
                result = glossary_dict | result
            except (TypeError, KeyError) as e:
                self.logger.error(f"Key or type error occurred while processing glossary chunk, skipped. Chunk: {chunk}, Error: {e.__repr__()}")
            except Exception as e:
                self.logger.error(f"Unknown error occurred while processing glossary chunk: {e.__repr__()}")

        self.logger.info("Glossary extraction completed")
        return result

    async def send_segments_async(self, segments: list[str], chunk_size: int):
        self.logger.info(f"Starting glossary extraction, to_lang:{self.to_lang}")
        result = {}
        indexed_originals, chunks, merged_indices_list = await asyncio.to_thread(segments2json_chunks, segments,
                                                                                 chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
        translated_chunks = await super().send_prompts_async(prompts=prompts,
                                                             result_handler=self._result_handler,
                                                             error_result_handler=self._error_result_handler)
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, list):
                    self.logger.error(f"Received chunk is not a valid list, skipped: {chunk}")
                    continue
                glossary_dict = {d["src"]: d["dst"] for d in chunk if isinstance(d, dict) and "src" in d and "dst" in d}
                result = result | glossary_dict
            except (TypeError, KeyError) as e:
                self.logger.error(f"Key or type error occurred while processing glossary chunk, skipped. Chunk: {chunk}, Error: {e.__repr__()}")
            except Exception as e:
                self.logger.error(f"Unknown error occurred while processing glossary chunk: {e.__repr__()}")

        self.logger.info("Glossary extraction completed")
        return result