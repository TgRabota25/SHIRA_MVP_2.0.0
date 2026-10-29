# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('D:/S H I R A/SHIRA_MVP_2.0.0/S H I R A/build_assets/icon.png', 'app'), ('D:/S H I R A/SHIRA_MVP_2.0.0/S H I R A/build_assets/icon.ico', 'app'), ('D:/S H I R A/SHIRA_MVP_2.0.0/S H I R A/app/tesseract', 'app/tesseract'), ('D:/S H I R A/SHIRA_MVP_2.0.0/S H I R A/tools/frame_preview.py', 'tools'), ('D:/S H I R A/SHIRA_MVP_2.0.0/S H I R A/README_RU.md', '.'), ('D:/S H I R A/SHIRA_MVP_2.0.0/S H I R A/licenses', 'licenses')]
binaries = []
hiddenimports = ['main', 'config', 'storage', 'engine', 'recognition', 'platform_ui', 'imageview', 'legacy_import', 'windows_job', 'studio_ui', 'premium_windows', 'archive_delete']
tmp_ret = collect_all('cv2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('zxingcpp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('psutil')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['D:/S H I R A/SHIRA_MVP_2.0.0/S H I R A/launcher.py'],
    pathex=['D:/S H I R A/SHIRA_MVP_2.0.0/S H I R A/app'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='SHIRA',
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
    icon=['D:/S H I R A/SHIRA_MVP_2.0.0/S H I R A/build_assets/icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SHIRA',
)
