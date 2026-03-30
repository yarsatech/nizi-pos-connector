"""
Nizi POS Connector — configuration.

Distribution metadata (name, version, OTA defaults, etc.) is loaded from
repository-root ``config.json`` (also bundled next to the frozen exe).
Per-user settings use a separate file: ``user_config_dir(APP_NAME, APP_AUTHOR) / "config.json"``.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
from pathlib import Path

from platformdirs import user_config_dir

logger = logging.getLogger(__name__)

_DIST_CONFIG_FILENAME = "config.json"

# Defaults used only if bundled/repo ``config.json`` is missing or a key is absent.
_DIST_DEFAULTS: dict = {
    "app_name": "Nizi POS Connector",
    "app_author": "Yarsa Tech",
    "version": "1.0.0",
    "contact_url": "https://yarsa.tech/contact",
    "whatsapp_url": "https://wa.me/9779800959042?text=Hi%20Yarsa%20Tech.%20Please%20provide%20me%20the%20API%20for%20the%20Nizi%20POS%20Connector.",
    "github_repo": "",
    "main_exe_basename": "NiziPOSConnector.exe",
    "updater_exe_basename": "ota_updater.exe",
    "ota_http_user_agent": "Nizi-POS-Connector-OTA",
    "ota_temp_dir_name": "nizi_pos_connector_ota",
    "ota_staging_dir_prefix": "nizi_pos_connector_ota_staging_",
    "install_backup_dir_prefix": "NiziPOSConnector_backup_",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _dist_config_paths() -> list[Path]:
    if getattr(sys, "frozen", False):
        base = Path(os.path.dirname(sys.executable))
        # PyInstaller can materialize `datas` either as:
        # - <base>/config.json (direct file), or
        # - <base>/_internal/config.json/config.json (folder + file),
        # so we check both.
        return [
            base / _DIST_CONFIG_FILENAME,
            base / "_internal" / _DIST_CONFIG_FILENAME,
            base / "_internal" / _DIST_CONFIG_FILENAME / _DIST_CONFIG_FILENAME,
        ]
    return [_repo_root() / _DIST_CONFIG_FILENAME]


def _load_dist_config_merged() -> dict:
    raw: dict = {}
    for path in _dist_config_paths():
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                break
        except Exception as e:
            logger.warning("Could not read %s: %s", path, e)
    out = dict(_DIST_DEFAULTS)
    for k, v in raw.items():
        if v is not None and str(v).strip() != "":
            out[k] = v
    return out


_DIST = _load_dist_config_merged()


def _dist_str(key: str) -> str:
    return str(_DIST.get(key) or _DIST_DEFAULTS[key]).strip()


APP_NAME = _dist_str("app_name")
APP_AUTHOR = _dist_str("app_author")
APP_VERSION = _dist_str("version")

CONTACT_URL = _dist_str("contact_url")
WHATSAPP_URL = _dist_str("whatsapp_url")

MAIN_EXE_BASENAME = _dist_str("main_exe_basename")
UPDATER_EXE_BASENAME = _dist_str("updater_exe_basename")

OTA_HTTP_USER_AGENT = _dist_str("ota_http_user_agent")
UPDATE_WINDOW_TITLE = f"{APP_NAME} Update"
UPDATE_ERROR_CAPTION = UPDATE_WINDOW_TITLE
OTA_HELPER_CAPTION = f"{APP_NAME} OTA Update"
OTA_TEMP_DIR_NAME = _dist_str("ota_temp_dir_name")
OTA_STAGING_DIR_PREFIX = _dist_str("ota_staging_dir_prefix")
INSTALL_BACKUP_DIR_PREFIX = _dist_str("install_backup_dir_prefix")


def embedded_github_repo() -> str:
    """GitHub ``owner/repo`` or URL from bundled ``config.json`` (no env / user file)."""
    return str(_DIST.get("github_repo") or "").strip()


class Config:
    def __init__(self):
        self.config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
        self.config_file = self.config_dir / "config.json"
        self._config = {}
        self.load()

    def load(self):
        """Load configuration from disk, creating defaults if missing."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self._config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self._config = {}
        else:
            self._config = {}

    def save(self):
        """Save configuration to disk."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    @property
    def api_key(self) -> str:
        return "Z8uVovI2eftp65dO9JoxEstKcWggSlTAza4erAQhELmSC761rVtp5IIzaXOxWNw0ycPCICYCnJBCVPCzvdT8fbJvWIWm69fhHveZesIiDEIeI0BkdSspMPimWYNWs25D"

    @property
    def is_windows(self) -> bool:
        return platform.system() == "Windows"

    @property
    def is_macos(self) -> bool:
        return platform.system() == "Darwin"

    @property
    def is_linux(self) -> bool:
        return platform.system() == "Linux"

    @property
    def server_host(self) -> str:
        return "127.0.0.1"

    @property
    def server_port(self) -> int:
        return 9121

    @property
    def github_repo(self) -> str:
        """
        GitHub repo ``owner/name`` for OTA.

        1) ``NIZI_POS_CONNECTOR_GITHUB_REPO``
        2) User ``config.json`` key ``github_repo``
        3) ``github_repo`` in bundled/repo ``config.json`` (distribution metadata)
        """
        return (
            os.environ.get("NIZI_POS_CONNECTOR_GITHUB_REPO")
            or self._config.get("github_repo")
            or embedded_github_repo()
        )

    @property
    def contact_url(self) -> str:
        return self._config.get("contact_url") or CONTACT_URL

    @property
    def whatsapp_url(self) -> str:
        return self._config.get("whatsapp_url") or WHATSAPP_URL


config = Config()
