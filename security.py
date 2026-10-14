"""
Nizi POS Connector - Cross-Platform Credential Management & Security Utilities
Protects local credentials across Windows (DPAPI), macOS (0600 POSIX), and Linux (0600 POSIX).
"""
from __future__ import annotations

import base64
import ctypes
import hmac
import logging
import os
import platform
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

_KEY_FILE_NAME = "api_key.protected"


if platform.system() == "Windows":
    from ctypes import wintypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    def _win_encrypt(data: bytes) -> bytes:
        b_data = (ctypes.c_byte * len(data))(*data)
        blob_in = _DATA_BLOB(len(data), b_data)
        blob_out = _DATA_BLOB()
        desc = "NiziPOSConnector API Key"
        if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            desc,
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out),
        ):
            raise ctypes.WinError()
        res = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return res

    def _win_decrypt(data: bytes) -> bytes:
        b_data = (ctypes.c_byte * len(data))(*data)
        blob_in = _DATA_BLOB(len(data), b_data)
        blob_out = _DATA_BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out),
        ):
            raise ctypes.WinError()
        res = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return res


def _key_file_path(config_dir: Path) -> Path:
    return config_dir / _KEY_FILE_NAME


def _save_protected_key(path: Path, raw: bytes) -> None:
    current_os = platform.system()
    tmp = path.with_suffix(".tmp")
    if current_os == "Windows":
        encrypted = _win_encrypt(raw)
        tmp.write_bytes(encrypted)
        os.replace(tmp, path)
    else:
        # macOS and Linux: restrictive 0600 POSIX permissions
        tmp.write_bytes(raw)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, path)


def _load_protected_key(path: Path) -> bytes:
    current_os = platform.system()
    raw_bytes = path.read_bytes()
    if current_os == "Windows":
        return _win_decrypt(raw_bytes)
    return raw_bytes


def get_or_create_api_key(config_dir: Path) -> str:
    """
    Retrieve or generate installation-unique 256-bit API key.
    Windows: Encrypted via DPAPI (CryptProtectData).
    Linux/macOS: Restrictive filesystem permissions (0600).
    Fails closed if encrypted key is unreadable.
    """
    key_file = _key_file_path(config_dir)
    key_file.parent.mkdir(parents=True, exist_ok=True)

    if key_file.exists():
        raw = _load_protected_key(key_file)
    else:
        raw = secrets.token_bytes(32)  # 256-bit cryptographic entropy
        _save_protected_key(key_file, raw)
        logger.info("Generated new installation-unique API key (%s)", platform.system())

    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def regenerate_api_key(config_dir: Path) -> str:
    """Generate and persist a new 256-bit installation API key."""
    key_file = _key_file_path(config_dir)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    raw = secrets.token_bytes(32)
    _save_protected_key(key_file, raw)
    logger.info("Regenerated installation API key (%s)", platform.system())
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def constant_time_compare(provided: str | None, expected: str | None) -> bool:
    """Timing-safe equality comparison preventing timing side-channel attacks."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
