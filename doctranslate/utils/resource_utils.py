# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import sys
from pathlib import Path

def resource_path(relative_path):
    """ Get the absolute path of a resource, suitable for both development environment and PyInstaller packaged environment """
    try:
        base_path = Path(sys._MEIPASS)/"doctranslate"
    except Exception:
        base_path = Path(__file__).resolve().parent.parent # During development
        # More robust development path (if your resources are relative to project root directory)
        # base_path = Path(os.path.abspath("."))
        # Or, if your static directory is always at the same level as app.py (during development)
        # base_path = Path(__file__).resolve().parent
    # print(f"base_path:{base_path}")
    return base_path / relative_path