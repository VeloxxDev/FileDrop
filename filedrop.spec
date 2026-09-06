# -*- mode: python ; coding: utf-8 -*-
"""Fichier de spécification PyInstaller pour FileDrop."""

import os
import sys
from pathlib import Path

block_cipher = None

project_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(project_dir, 'resources'), 'resources'),
]

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt6',
        'paramiko',
        'cryptography',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'win32':
    icon_file = os.path.join(project_dir, 'resources', 'icons', 'icon.ico')
else:
    icon_file = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FileDrop',
    debug=False,
    icon=icon_file,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FileDrop',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='FileDrop.app',
        icon=icon_file,
        bundle_identifier='com.filedrop.app',
    )
