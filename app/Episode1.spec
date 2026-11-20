# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('../arm/armctl.py', 'arm'), ('../arm/config/joints.json', 'arm/config'), ('../kinematics/__init__.py', 'kinematics'), ('../kinematics/episode1_model.py', 'kinematics'), ('assets/icon.png', 'assets')],
    hiddenimports=['numpy', 'x42s_stepper', 'can', 'serial'],
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
    [],
    exclude_binaries=True,
    name='Episode1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Episode1',
)
app = BUNDLE(
    coll,
    name='Episode1.app',
    icon='assets/icon.icns',
    bundle_identifier='com.tsu.episode1',
)
