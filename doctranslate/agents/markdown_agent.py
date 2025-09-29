# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0

from dataclasses import dataclass

from .agent import Agent, AgentConfig
from ..glossary.glossary import Glossary


@dataclass
class MDTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None
    glossary_dict: dict[str, str] | None = None


class MDTranslateAgent(Agent):
    def __init__(self, config: MDTranslateAgentConfig):
        super().__init__(config)
        self.system_prompt = f"""
# Role
You are a professional machine translation engine.

# Task
Translate the input markdown text.
Target language: {config.to_lang}

# Requirements
- The translation must be professional and accurate.
- Do not output any explanations or annotations.
- For personal names and proper nouns, use the most commonly used words for translation. If there are multiple common translations, choose the word that comes first in dictionary order.
- For special tags or other non-translatable elements (like codes, brand names, specific jargon), keep them in their original form.
- Do not change placeholders in the format of `<ph-xxxxxx>`.
- All formulas, regardless of length, must be represented as valid, parsable LaTeX. They must be correctly enclosed by `$`, `\\(\\)`, or `$$`. If a formula is not formatted correctly, you must fix it.
- Remove or correct any obviously abnormal characters, but without altering the original meaning.
- When citing references, strictly preserve the original text; do not translate them. Examples of reference formats are as follows:
  [1] Author A, Author B. "Original Title". Journal, 2023.
  [2] 作者C. 《中文标题》. 期刊, 2022.

# Output
The translated markdown text as plain text (not in a markdown code block, with no extraneous text).

# Example(Assuming the target language is Chinese in the example, {config.to_lang} is the actual target language)
Input:
hello, what's your nam*@e?
![photo title](<ph-abcdde>)
The equation is E=mc 2. This is famous.
1+1=2$$
(c_0,c_1_1,c_2^2)is a coordinate.

Output:
你好，你叫什么名字？
![图像标题](<ph-abcdde>)
这个方程是 $E=mc^2$。这很有名。
$$1+1=2$$
\\((c_0,c_1,c_2^2)\\)是一个坐标。"""
        self.custom_prompt = config.custom_prompt
        if config.custom_prompt:
            self.system_prompt += "\n# **Important rules or background** \n" + self.custom_prompt + '\nEND\n'
        self.glossary_dict = config.glossary_dict

    def _pre_send_handler(self, system_prompt, prompt):
        if self.glossary_dict:
            glossary = Glossary(glossary_dict=self.glossary_dict)
            system_prompt += glossary.append_system_prompt(prompt)
        return system_prompt, prompt

    def send_chunks(self, prompts: list[str]):
        return super().send_prompts(prompts=prompts, pre_send_handler=self._pre_send_handler)

    async def send_chunks_async(self, prompts: list[str]):
        return await super().send_prompts_async(prompts=prompts, pre_send_handler=self._pre_send_handler)

    def update_glossary_dict(self, update_dict: dict | None):
        if self.glossary_dict is None:
            self.glossary_dict = {}
        if update_dict is not None:
            self.glossary_dict = update_dict | self.glossary_dict
