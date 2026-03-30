# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Nizi POS Connector (main app + OTA helper).
Build with:  pyinstaller build.spec
"""

import os

import platform

# Identify platform details
is_mac = platform.system() == "Darwin"

base_dir = os.path.dirname(os.path.abspath(SPEC))

main_script = os.path.join(base_dir, "main.py")
updater_script = os.path.join(base_dir, "ota", "ota_updater.py")

a_main = Analysis(
    [main_script],
    pathex=[base_dir],
    binaries=[],
    datas=[
        (os.path.join(base_dir, 'static'), 'static'),
        (os.path.join(base_dir, 'assets'), 'assets'),
        (os.path.join(base_dir, 'config.json'), '.'),
    ],
    hiddenimports=[
        'flask',
        'flask_socketio',
        'engineio.async_drivers.threading',
        'engineio.async_drivers.eventlet',
        'eventlet',
        'bidict',
        'engineio',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'PyQt6',
        'PIL',
        'platformdirs',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pystray'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz_main = PYZ(a_main.pure, a_main.zipped_data)

exe_main = EXE(
    pyz_main,
    a_main.scripts,
    [],                      # Move binaries/zipfiles/datas to COLLECT for non-onefile macOS bundle
    exclude_binaries=True,   # Required for BUNDLE on macOS sometimes
    name='NiziPOSConnector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(base_dir, 'assets', 'icon.ico'),
)

#
# Updater helper (OTA replacement tool)
#
a_updater = Analysis(
    [updater_script],
    pathex=[base_dir],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pystray'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz_updater = PYZ(a_updater.pure, a_updater.zipped_data)

exe_updater = EXE(
    pyz_updater,
    a_updater.scripts,
    [],
    exclude_binaries=True,
    name="ota_updater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(base_dir, 'assets', 'icon.ico'),
)

coll = COLLECT(
    exe_main,
    exe_updater,
    a_main.binaries + a_updater.binaries,
    a_main.zipfiles + a_updater.zipfiles,
    a_main.datas + a_updater.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NiziPOSConnector',
)

# Added BUNDLE for macOS to create a proper .app and hide terminal
if is_mac:
    app = BUNDLE(
        coll,                # Use collective binaries
        name='NiziPOSConnector.app',
        icon=os.path.join(base_dir, 'assets', 'icon.ico'),
        bundle_identifier='com.yarsatech.nizi-pos-connector',
        info_plist={
            'LSUIElement': True,
            'NSHighResolutionCapable': 'True'
        },
    )
