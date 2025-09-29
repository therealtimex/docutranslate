# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all
import doctranslate

# Initialize lists
datas = []
binaries = []
hiddenimports = ['markdown.extensions.tables', 'pymdownx.arithmatex',
                'pymdownx.superfences', 'pymdownx.highlight', 'pygments']

# First collect third-party package resources
for package in ['easyocr', 'docling', 'pygments']:
    try:
        tmp_ret = collect_all(package)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Failed to collect resources for {package}: {e}")

# Then add your custom resources (avoid duplicates)
custom_datas = [
    ('./.venv/Lib/site-packages/docling_parse/pdf_resources_v2', 'docling_parse/pdf_resources_v2'),
    ('./doctranslate/static', 'doctranslate/static'),
    ('./doctranslate/template', 'doctranslate/template')
]

# Avoid adding duplicate data
for data in custom_datas:
    if data not in datas:
        datas.append(data)

a = Analysis(
    ['doctranslate/app.py'],  # Use forward slashes
    pathex=[],  # Add current working directory to pathex
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hiddenimports)),  # Remove duplicates
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'doctranslate_full-{doctranslate.__version__}-win',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='doctranslate.ico',
)