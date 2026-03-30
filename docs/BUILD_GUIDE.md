# Nizi POS Connector Build Guide

Compile **Nizi POS Connector** into a standalone executable for Windows, macOS, or Linux. PyInstaller does not cross-compile: build on the OS you target.

## Prerequisites

1. **Python 3.10+**
2. **Virtual environment** (recommended):
   ```bash
   python -m venv venv
   ```
3. **Activate**
   - Windows: `.\venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`
4. **Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

## Distribution metadata

Repo-root **`config.json`** (distribution metadata) holds app name, author, version, embedded `github_repo` for OTA, main/updater exe names, and OTA folder prefixes. CI updates `version` and `github_repo` on release builds. It is bundled by PyInstaller next to the executable. This is not the same file as the per-user `config.json` under the OS app data directory.

For **Inno Setup**, keep this **`config.json`** as **single-line JSON** (or ensure the first line contains `"version":"…"`) so the compiler can read `AppVersion`.

## Build

```bash
pyinstaller build.spec
```

### Output layout

| Platform | Main output |
|----------|-------------|
| **Windows** | `dist/NiziPOSConnector/NiziPOSConnector.exe` (onedir — same folder includes `ota_updater.exe`, `static/`, etc.) |
| **Linux** | `dist/NiziPOSConnector/NiziPOSConnector` |
| **macOS** | `dist/NiziPOSConnector.app` |

## Inno Setup (Windows installer)

After a successful PyInstaller build, from the repo root:

```powershell
iscc win_setup.iss
```

The installer expects `dist\NiziPOSConnector\` to exist.

## Troubleshooting

- **Linux tray**: Install `libappindicator3-1` (or equivalent) if the tray icon is missing.
- **Hooks**: `build.spec` already lists common hidden imports (`flask_socketio`, serial, PyQt6, etc.).
