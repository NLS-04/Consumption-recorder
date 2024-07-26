# -*- mode: python ; coding: utf-8 -*-
# cspell:disable


block_cipher = None


a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('VERSION', '.'),
        ('LICENSE', '.'),
        ('rsc\\main.ico', 'rsc'),
        ('src\\main.py', '.'),
        ('src\\simpleTUI.py', '.'),
    ],
    hiddenimports=[
        "pynput.keyboard._win32",
        "pynput.keyboard._xorg",
        "pynput.keyboard._darwin"
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='rsc\\main.ico',
    #version='rsc\\resourceVersion.rc',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='consumption-recorder-win11',
)
