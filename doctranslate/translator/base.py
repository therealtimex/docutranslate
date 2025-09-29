# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from abc import ABC, abstractmethod
from dataclasses import dataclass
from logging import Logger
from typing import TypeVar, Generic

from doctranslate.ir.document import Document
from doctranslate.logger import global_logger


@dataclass(kw_only=True)
class TranslatorConfig:
    logger: Logger = global_logger


T = TypeVar('T', bound=Document)


class Translator(ABC, Generic[T]):
    """
    Translate intermediate text (in-place replacement), Translator does not perform format conversion
    """

    def __init__(self, config: TranslatorConfig | None = None):
        self.config = config
        self.logger = config.logger or global_logger

    @abstractmethod
    def translate(self, document: T) -> Document:
        ...

    @abstractmethod
    async def translate_async(self, document: T) -> Document:
        ...
