# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import json
from dataclasses import dataclass
from typing import Self, Any, Tuple, List

from jsonpath_ng.ext import parse

from doctranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from doctranslate.ir.document import Document
from doctranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class JsonTranslatorConfig(AiTranslatorConfig):
    json_paths: list[str]


class JsonTranslator(AiTranslator):
    def __init__(self, config: JsonTranslatorConfig):
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
        self.json_paths = config.json_paths

    def _get_key_or_index_from_path(self, path) -> Any:
        """Extract key or index from jsonpath_ng Path object."""
        if hasattr(path, 'fields') and path.fields:
            return path.fields[0]
        if hasattr(path, 'index'):
            return path.index
        return None

    def _collect_strings_for_translation(self, content: dict) -> Tuple[List[str], List[Tuple[Any, Any]]]:
        """
        Find matches based on jsonpath and recursively collect all strings from them for translation.
        To prevent duplicates, track the exact position of each string.

        Returns:
            - original_texts: A list containing all strings to be translated.
            - update_targets: A list containing target information for updates, each element is (container, key_or_index).
        """
        original_texts = []
        update_targets = []
        # Use (id(container), key_or_index) to uniquely identify a position, preventing duplicate additions
        seen_targets = set()

        # Helper recursive function for traversing json objects
        def _traverse(node: Any, container: Any, key_or_index: Any):
            # If current node is a string and its position hasn't been recorded yet
            target_id = (id(container), key_or_index)
            if isinstance(node, str):
                if target_id not in seen_targets:
                    original_texts.append(node)
                    update_targets.append((container, key_or_index))
                    seen_targets.add(target_id)
            # If it's a dictionary, traverse all its child nodes
            elif isinstance(node, dict):
                for k, v in node.items():
                    _traverse(v, node, k)
            # If it's a list, traverse all its child nodes
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    _traverse(item, node, i)

        # 1. Find all top-level matches
        all_matches = []
        for path_str in self.json_paths:
            jsonpath_expr = parse(path_str)
            all_matches.extend(jsonpath_expr.find(content))

        # 2. Traverse matches and start recursive collection
        for match in all_matches:
            parent = match.context.value if match.context else None
            key_or_index = self._get_key_or_index_from_path(match.path)

            # Start traversal directly on the matched value
            _traverse(match.value, parent, key_or_index)

        return original_texts, update_targets

    def _apply_translations(self, update_targets: List[Tuple[Any, Any]], translated_texts: List[str]):
        """
        Update original JSON content with translated text.
        """
        if len(update_targets) != len(translated_texts):
            raise ValueError("The number of translation targets does not match the number of translated texts.")

        for target, text in zip(update_targets, translated_texts):
            container, key_or_index = target
            # Ensure container and key/index are valid, then perform update
            if container is not None and key_or_index is not None:
                container[key_or_index] = text

    def translate(self, document: Document) -> Self:
        """
        Main method: Extract, translate and update specified content in JSON document.

        Process:
        1. Parse input JSON document.
        2. Find matching objects based on jsonpath and recursively traverse them to extract all strings.
        3. Send extracted strings for batch translation.
        4. Update translated text back to JSON object according to their original positions.
        5. Write updated content back to document.
        """
        content = json.loads(document.content.decode())

        # Step 1: Extract all strings that need translation and their positions
        original_texts, update_targets = self._collect_strings_for_translation(content)

        if not original_texts:
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # Step 2: Batch translate extracted text
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        if len(original_texts) != len(translated_texts):
            raise ValueError("The number of items returned by translation service does not match the number sent.")

        # Step 3: Write translation results back to original JSON object
        self._apply_translations(update_targets, translated_texts)

        document.content = json.dumps(content, ensure_ascii=False, indent=2).encode('utf-8')

        return self

    async def translate_async(self, document: Document) -> Self:
        content = json.loads(document.content.decode())

        # Step 1: Extract all strings that need translation and their positions
        original_texts, update_targets = self._collect_strings_for_translation(content)

        if not original_texts:
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # Step 2: Batch translate extracted text
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        if len(original_texts) != len(translated_texts):
            raise ValueError("The number of items returned by translation service does not match the number sent.")

        # Step 3: Write translation results back to original JSON object
        self._apply_translations(update_targets, translated_texts)

        document.content = json.dumps(content, ensure_ascii=False, indent=2).encode('utf-8')
        return self
