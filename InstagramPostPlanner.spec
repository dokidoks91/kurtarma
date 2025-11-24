# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Instagram Post Planner
Build command: pyinstaller InstagramPostPlanner.spec
"""

a = Analysis(
    ['gui_app_v2.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.py', '.'),
        ('validator.py', '.'),
        ('constraint_analyzer.py', '.'),
        ('planner.py', '.'),
        ('instagram_auto_post.py', '.'),
        ('best_effort_analyzer.py', '.'),
        ('product_helpers.py', '.'),
    ],
    hiddenimports=[
        'openpyxl',
        'openpyxl.cell._writer',
        'pandas',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'config',
        'validator',
        'constraint_analyzer',
        'planner',
        'instagram_auto_post',
        'best_effort_analyzer',
        'product_helpers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='InstagramPostPlanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
