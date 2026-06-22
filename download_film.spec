# download_film.spec
import sys

icon_file = "icon.icns" if sys.platform == "darwin" else "icon.ico"

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "HdRezkaApi",
        "httpx",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["aiogram", "peewee", "aiohttp"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MovieDownloader",
    icon=icon_file,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # no terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Mac: wrap in .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="MovieDownloader.app",
        icon="icon.icns",
        bundle_identifier="com.moviedownloader.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
            "CFBundleDisplayName": "MovieDownloader",
        },
    )
