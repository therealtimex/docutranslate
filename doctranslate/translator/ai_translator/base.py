# SPDX-FileCopyrightText: 2025 RealTimeX
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
        metadata={"description": "OpenAI compatible address, required when skip_translate is False"},
    )
    model_id: str | None = field(
        default=None, metadata={"description": "Required when skip_translate is False"}
    )
    to_lang: str = "Simplified Chinese"
    custom_prompt: str | None = None
    chunk_size: int = 3000
    glossary_dict: dict[str, str] | None = field(default=None)
    glossary_generate_enable: bool = False
    glossary_agent_config: '_GlossaryAgentConfig | None' = None  # type: ignore[name-defined]
    skip_translate: bool = False  # When skip_translate is False, base_url, api_key, model_id are required


T = TypeVar("T", bound=Document)


class AiTranslator(Translator[T]):
    """
    Translate intermediate text (in-place replacement), Translator does not perform format conversion
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
