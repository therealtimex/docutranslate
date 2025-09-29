# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import os


MESSAGES = {
    "en": {
        "generated": "Generated: {path}",
        "attachment_generated": "Attachment generated: {path} ({identifier})",
        "skip_unsupported_format": "Skip unsupported export format: {ftype}",
        "skip_export_missing_dep": "Skipped {ftype} export, missing dependency: {missing}. Install extras and retry.",
        "export_failed": "Export {ftype} failed: {error}",
        "missing_optional_dependency": "Missing optional dependency: {missing}. To start GUI, install: pip install \"doctranslate[webui]\"",
        "missing_dependency": "Missing dependency: {missing}",
        "file_not_found": "File not found: {path}",
        "docpkg_not_found": "Document package not found: {path}",
        "docpkg_missing_entry": "No index.html or document.md found in document package: {path}",
    },
    "zh": {
        "generated": "已生成: {path}",
        "attachment_generated": "附件已生成: {path} ({identifier})",
        "skip_unsupported_format": "跳过不支持的导出格式: {ftype}",
        "skip_export_missing_dep": "跳过 {ftype} 导出，缺少依赖: {missing}. 可安装相关依赖后重试。",
        "export_failed": "导出 {ftype} 失败: {error}",
        "missing_optional_dependency": "缺少可选依赖: {missing}. 如需启动图形界面，请安装: pip install \"doctranslate[webui]\"",
        "missing_dependency": "缺少依赖: {missing}",
        "file_not_found": "找不到文件: {path}",
        "docpkg_not_found": "找不到文档包目录: {path}",
        "docpkg_missing_entry": "文档包中未找到 index.html 或 document.md: {path}",
    },
}


def t(key: str, *, lang: str | None = None, **kwargs) -> str:
    l = (lang or os.getenv("doctranslate_LANG") or "en").lower()
    if l not in MESSAGES:
        l = "en"
    msg = MESSAGES.get(l, {}).get(key) or MESSAGES["en"].get(key) or key
    try:
        return msg.format(**kwargs)
    except Exception:
        return msg
