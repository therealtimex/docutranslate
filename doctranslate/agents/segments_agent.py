# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0

import asyncio
import json
from dataclasses import dataclass
from json import JSONDecodeError
from logging import Logger

from json_repair import json_repair

from doctranslate.agents import AgentConfig, Agent
from doctranslate.agents.agent import PartialAgentResultError, AgentResultError
from doctranslate.glossary.glossary import Glossary
from doctranslate.utils.json_utils import segments2json_chunks, fix_json_string


@dataclass
class SegmentsTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None
    glossary_dict: dict[str, str] | None = None


class SegmentsTranslateAgent(Agent):
    def __init__(self, config: SegmentsTranslateAgentConfig):
        super().__init__(config)
        self.system_prompt = f"""
# Role
- You are a professional machine translation engine.
# Task
- You will receive a sequence of segments to be translated, represented in JSON format. The keys are the segment IDs, and the values are the segments for translation.
- You need to translate these segments into the target language.
- Target language: {config.to_lang}
# Requirements
- The translation must be professional and accurate.
- Do not output any explanations or annotations.
- For personal names and proper nouns, use the most commonly used words for translation. 
- For special tags or other non-translatable elements (like codes, brand names, specific jargon), keep them in their original form.
- If a segment is already in the target language({config.to_lang}), keep it as is.
- Do not merge multiple segment translations into one translation.
- (very important) All keys that appear in the input JSON must exist in the output JSON.
# Output
- The translated sequence of segments, represented as JSON text (note: not a code block). The keys are the segment IDs, and the values are the translated segments.
- The response must be a JSON object with the following structure: 
{{
"<segment_id>": "<translation>"
}}
- (very important) The segment IDs in the output must exactly match those in the input. And all segment IDs in input must appear in the output.
# Example(Assuming the target language is English in the example, {config.to_lang} is the actual target language)
## Input
{{
"21": "汤姆说：“你好”",
"22": "苹果",
"23": "错误",
"24": "香蕉"
}}
## Correct Output
{{
"21": "Tom says:\\\"hello\\\"",
"22": "apple",
"23": "error",
"24": "banana"
}}
"""
        self.custom_prompt = config.custom_prompt
        if config.custom_prompt:
            self.system_prompt += "\n# **Important rules or background** \n" + self.custom_prompt + '\nEND\n'
        self.glossary_dict = config.glossary_dict

    def _pre_send_handler(self, system_prompt, prompt):
        if self.glossary_dict:
            glossary = Glossary(glossary_dict=self.glossary_dict)
            system_prompt += glossary.append_system_prompt(prompt)
        return system_prompt, prompt

    def _result_handler(self, result: str, origin_prompt: str, logger: Logger):
        """
        Handle a successful API response.
        - If keys fully match, return translations.
        - If keys mismatch, construct a partial result and raise PartialAgentResultError to trigger retry.
        - For hard errors (e.g., JSON parsing), raise an AgentResultError.
        """
        if result == "":
            if origin_prompt.strip() != "":
                raise AgentResultError("Empty result while original is non-empty")
            return {}
        try:
            result = fix_json_string(result)
            original_chunk = json.loads(origin_prompt)
            repaired_result = json_repair.loads(result)

            if not isinstance(repaired_result, dict):
                raise AgentResultError(f"Agent returned non-dict JSON, result: {result}")

            if repaired_result == original_chunk:
                raise AgentResultError("Translation equals original; likely failed. Will retry.")

            original_keys = set(original_chunk.keys())
            result_keys = set(repaired_result.keys())

            # If keys mismatch
            if original_keys != result_keys:
                # Build best-effort partial result
                final_chunk = {}
                common_keys = original_keys.intersection(result_keys)
                missing_keys = original_keys - result_keys
                extra_keys = result_keys - original_keys

                logger.warning("Key mismatch between original and result; will retry.")
                if missing_keys: logger.warning(f"Missing keys: {missing_keys}")
                if extra_keys: logger.warning(f"Extra keys: {extra_keys}")

                for key in common_keys:
                    final_chunk[key] = str(repaired_result[key])
                for key in missing_keys:
                    final_chunk[key] = str(original_chunk[key])

                # Raise partial result error to trigger retry
                raise PartialAgentResultError("Key mismatch; trigger retry", partial_result=final_chunk)

            # 如果键完全匹配（理想情况），正常返回
            for key, value in repaired_result.items():
                repaired_result[key] = str(value)

            return repaired_result

        except (RuntimeError, JSONDecodeError) as e:
            # Hard errors (e.g., JSON parse)
            raise AgentResultError(f"Result handling failed: {e!r}")

    def _error_result_handler(self, origin_prompt: str, logger: Logger):
        """
        Handle requests that failed after all retries.
        As a fallback, return original content with values coerced to strings.
        """
        if origin_prompt == "":
            return {}
        try:
            original_chunk = json.loads(origin_prompt)
            # 此处逻辑保留，作为最终的兜底方案
            for key, value in original_chunk.items():
                original_chunk[key] = f"{value}"
            return original_chunk
        except (RuntimeError, JSONDecodeError):
            logger.error(f"Original prompt is not valid JSON: {origin_prompt}")
            # Original prompt invalid as well; return an explicit error object
            return {"error": f"{origin_prompt}"}

    def send_segments(self, segments: list[str], chunk_size: int) -> list[str]:
        indexed_originals, chunks, merged_indices_list = segments2json_chunks(segments, chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False, indent=0) for chunk in chunks]

        translated_chunks = super().send_prompts(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                 result_handler=self._result_handler,
                                                 error_result_handler=self._error_result_handler)

        indexed_translated = indexed_originals.copy()
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, dict):
                    self.logger.warning(f"Chunk is not a valid dict; skipped: {chunk}")
                    continue
                for key, val in chunk.items():
                    if key in indexed_translated:
                        indexed_translated[key] = val
                    else:
                        self.logger.warning(f"Unknown key in results chunk '{key}'; ignored.")
            except (AttributeError, TypeError) as e:
                self.logger.error(f"Type/attribute error while processing chunk; skipped. Chunk: {chunk}, error: {e!r}")
            except Exception as e:
                self.logger.error(f"Unknown error while processing chunk: {e!r}")

        # 重建最终列表
        result = []
        last_end = 0
        ls = list(indexed_translated.values())
        for start, end in merged_indices_list:
            result.extend(ls[last_end:start])
            merged_item = "".join(map(str, ls[start:end]))
            result.append(merged_item)
            last_end = end

        result.extend(ls[last_end:])
        return result

    async def send_segments_async(self, segments: list[str], chunk_size: int) -> list[str]:
        indexed_originals, chunks, merged_indices_list = await asyncio.to_thread(segments2json_chunks, segments,
                                                                                 chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False, indent=0) for chunk in chunks]

        translated_chunks = await super().send_prompts_async(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                             result_handler=self._result_handler,
                                                             error_result_handler=self._error_result_handler)

        indexed_translated = indexed_originals.copy()
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, dict):
                    self.logger.error(f"Chunk is not a valid dict; skipped: {chunk}")
                    continue
                for key, val in chunk.items():
                    if key in indexed_translated:
                        # 此处不再需要 str(val)，因为 _result_handler 已经处理好了
                        indexed_translated[key] = val
                    else:
                        self.logger.warning(f"Unknown key in results chunk '{key}'; ignored.")
            except (AttributeError, TypeError) as e:
                self.logger.error(f"Type/attribute error while processing chunk; skipped. Chunk: {chunk}, error: {e!r}")
            except Exception as e:
                self.logger.error(f"Unknown error while processing chunk: {e!r}")

        # 重建最终列表
        result = []
        last_end = 0
        ls = list(indexed_translated.values())
        for start, end in merged_indices_list:
            result.extend(ls[last_end:start])
            merged_item = "".join(map(str, ls[start:end]))
            result.append(merged_item)
            last_end = end

        result.extend(ls[last_end:])
        return result

    def update_glossary_dict(self, update_dict: dict | None):
        if self.glossary_dict is None:
            self.glossary_dict = {}
        if update_dict is not None:
            self.glossary_dict = update_dict | self.glossary_dict
