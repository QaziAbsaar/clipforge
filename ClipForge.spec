# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ClipForge – one-folder bundle."""
import os, sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
ROOT = os.path.abspath('.')

# Collect hidden imports that PyInstaller misses
hidden = (
    collect_submodules('uvicorn') +
    collect_submodules('fastapi') +
    collect_submodules('starlette') +
    collect_submodules('multipart') +
    collect_submodules('faster_whisper') +
    collect_submodules('ctranslate2') +
    collect_submodules('onnxruntime') +
    collect_submodules('streamlink') +
    collect_submodules('cv2') +
    collect_submodules('pydantic') +
    collect_submodules('pydantic_core') +
    collect_submodules('numpy') +
    collect_submodules('clipforge') +
    collect_submodules('clipforge_web') +
    collect_submodules('curl_cffi') +
    collect_submodules('rapidocr_onnxruntime') +
    collect_submodules('piper', filter=lambda n: not n.startswith(('piper.train', 'piper.http_server'))) +
    ['engineio.async_drivers.threading',
     'h11', 'httptools', 'websockets', 'websocket', 'wsproto',
     'email.mime.multipart', 'email.mime.text',
     'sqlite3', 'wave', 'json', 'csv', 'tempfile',
     'encodings', 'encodings.utf_8', 'encodings.ascii',
     'encodings.latin_1', 'encodings.cp1252',
     'yt_dlp']
)

# Data files to bundle
datas = [
    # ClipForge web static files
    (os.path.join(ROOT, 'clipforge_web', 'static'), os.path.join('clipforge_web', 'static')),
    # Audio library
    (os.path.join(ROOT, 'audio_library'), 'audio_library'),
]

if os.path.isfile(os.path.join(ROOT, 'cookies.txt')):
    datas += [(os.path.join(ROOT, 'cookies.txt'), '.')]

# Collect data from packages that need it
datas += collect_data_files('faster_whisper')
datas += collect_data_files('ctranslate2')
datas += collect_data_files('onnxruntime')
datas += collect_data_files('pydantic')
datas += collect_data_files('pydantic_core')
datas += collect_data_files('streamlink')
datas += collect_data_files('pycountry')
datas += collect_data_files('certifi')
datas += collect_data_files('curl_cffi')
datas += collect_data_files('rapidocr_onnxruntime')   # OCR models for GTA banners
datas += collect_data_files('piper')                  # espeak-ng-data for voice-over

# OpenCV haar cascades
import cv2
cv2_data = os.path.join(os.path.dirname(cv2.__file__), 'data')
if os.path.isdir(cv2_data):
    datas += [(cv2_data, os.path.join('cv2', 'data'))]

a = Analysis(
    ['clipforge_entry.py'],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pandas', 'IPython', 'notebook', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ClipForge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Windowed GUI application - no black console window
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='ClipForge',
)

