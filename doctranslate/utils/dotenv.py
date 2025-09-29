# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Tuple, List, Optional


def _strip_quotes(val: str) -> str:
    val = val.strip()
    if not val:
        return val
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val


def _parse_env_lines(lines: Iterable[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.lower().startswith('export '):
            line = line[7:].lstrip()
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = _strip_quotes(value)
        # strip inline comments only when not quoted (already stripped)
        if ' #' in value:
            value = value.split(' #', 1)[0].rstrip()
        pairs.append((key, value))
    return pairs


def load_env_file(path: str | Path | None = None, *, override: bool = False) -> tuple[Optional[str], List[str]]:
    """
    Load environment variables from a .env file.

    Resolution order when path is None:
    1) $doctranslate_ENV_FILE if set
    2) ./.env in the current working directory

    Returns (path_used, loaded_keys).
    """
    candidate: Optional[Path]
    if path is not None:
        candidate = Path(path)
    else:
        env_hint = os.getenv('doctranslate_ENV_FILE')
        candidate = Path(env_hint) if env_hint else Path.cwd() / '.env'

    if not candidate.exists() or not candidate.is_file():
        return None, []

    keys: list[str] = []
    try:
        content = candidate.read_text(encoding='utf-8')
    except Exception:
        return None, []

    for k, v in _parse_env_lines(content.splitlines()):
        if override or k not in os.environ:
            os.environ[k] = v
            keys.append(k)
    return str(candidate), keys

