# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TypeVar, TYPE_CHECKING
from doctranslate.ir.document import Document
from doctranslate.translator.base import Translator, TranslatorConfig
from doctranslate.agents.agent import AgentConfig


if TYPE_CHECKING:
    # only for type checking to avoid importing heavy agents at runtime
    from doctranslate.agents.glossary_agent import GlossaryAgentConfig as _GlossaryAgentConfig


@dataclass(kw_only=True)
class AiTranslatorConfig(TranslatorConfig, AgentConfig):
    base_url: str | None = field(
        default=None,
        metadata={"description": "OpenAI兼容地址，当skip_translate为False时为必填项"},
    )
    model_id: str | None = field(
        default=None, metadata={"description": "当skip_translate为False时为必填项"}
    )
    to_lang: str = "简体中文"
    custom_prompt: str | None = None
    chunk_size: int = 3000
    glossary_dict: dict[str, str] | None = field(default=None)
    glossary_generate_enable: bool = False
    glossary_agent_config: '_GlossaryAgentConfig | None' = None  # type: ignore[name-defined]
    skip_translate: bool = False  # 当skip_translate为False时base_url、api_key、model_id为必填项


T = TypeVar("T", bound=Document)


class AiTranslator(Translator[T]):
    """
    翻译中间文本（原地替换），Translator不做格式转换
    """

    def __init__(self, config: AiTranslatorConfig):
        super().__init__(config=config)
        self.skip_translate = config.skip_translate
        self.glossary_agent = None
        self.glossary_dict_gen = None
        if not self.skip_translate and (
            config.base_url is None or config.api_key is None or config.model_id is None
        ):
            raise ValueError(
                "When skip_translate is False, base_url, api_key, and model_id are required"
            )

        if config.glossary_generate_enable:
            from doctranslate.agents.glossary_agent import GlossaryAgent, GlossaryAgentConfig
            if config.glossary_agent_config:
                self.glossary_agent = GlossaryAgent(config.glossary_agent_config)
            else:
                glossary_agent_config = GlossaryAgentConfig(
                    to_lang=config.to_lang,
                    base_url=config.base_url,
                    api_key=config.api_key,
                    model_id=config.model_id,
                    temperature=config.temperature,
                    thinking=config.thinking,
                    concurrent=config.concurrent,
                    timeout=config.timeout,
                    logger=self.logger,
                    retry=config.retry,
                    system_proxy_enable=config.system_proxy_enable,
                )
                self.glossary_agent = GlossaryAgent(glossary_agent_config)

    @abstractmethod
    def translate(self, document: T) -> Document: ...

    @abstractmethod
    async def translate_async(self, document: T) -> Document: ...
