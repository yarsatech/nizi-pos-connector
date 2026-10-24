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
        # macOS and Linux: atomic creation with restrictive 0600 POSIX permissions
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = 0o600
        fd = os.open(str(tmp), flags, mode)
        try:
            with open(fd, "wb", closefd=True) as f:
                f.write(raw)
        except Exception:
            try:
                os.unlink(str(tmp))
            except OSError:
                pass
            raise
        os.replace(tmp, path)



def _load_protected_key(path: Path) -> bytes:
    current_os = platform.system()
    raw_bytes = path.read_bytes()
    if current_os == "Windows":
        return _win_decrypt(raw_bytes)
    return raw_bytes


def _parse_loaded_key(raw: bytes) -> str:
    """Parse loaded protected key, supporting custom string keys and legacy raw bytes."""
    if raw.startswith(b"STR:"):
        return raw[4:].decode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


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
        return _parse_loaded_key(raw)
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


import math
from collections import Counter


def calculate_shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy (bits per symbol) of a given string."""
    if not s:
        return 0.0
    counts = Counter(s)
    total = len(s)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _detect_sequential_patterns(s: str, min_len: int = 4) -> bool:
    """Detect ascending/descending ASCII character runs using first-order delta arithmetic."""
    s_lower = s.lower()
    for i in range(len(s_lower) - min_len + 1):
        chunk = s_lower[i : i + min_len]
        diffs = [ord(chunk[j + 1]) - ord(chunk[j]) for j in range(len(chunk) - 1)]
        if all(d == 1 for d in diffs) or all(d == -1 for d in diffs):
            return True
    return False


def _detect_repeating_patterns(s: str) -> bool:
    """Detect repeating cyclical chunks using string periodicity decomposition."""
    n = len(s)
    for chunk_len in range(1, (n // 2) + 1):
        chunk = s[:chunk_len]
        repeats = n // chunk_len
        remainder = n % chunk_len
        reconstructed = (chunk * repeats) + chunk[:remainder]
        if reconstructed == s and repeats >= 2:
            return True
    return False


def validate_custom_api_key(key: str) -> str:
    """
    Algorithmic passkey validation using information theory and pattern arithmetic:
    - Length: 16 to 32 characters (rejects short/truncated codes).
    - Character Diversity: Requires a mixture of character types (letters combined with numbers/symbols).
    - Sequential Pattern Analysis: Rejects ascending/descending runs (e.g. '1234', 'abcd') via ASCII delta math.
    - Periodicity Analysis: Rejects cyclical repeating patterns (e.g. 'a1a1a1a1', 'term1term1').
    - Shannon Entropy Analysis: Requires minimum information density (>= 2.2 bits/char and >= 20.0 bits total entropy).
    """
    cleaned = (key or "").strip()
    if not cleaned:
        raise ValueError("API key cannot be empty.")
    if len(cleaned) < 16 or len(cleaned) > 32:
        raise ValueError("API key must be between 16 and 32 characters long.")

    has_alpha = any(c.isalpha() for c in cleaned)
    has_non_alpha = any(not c.isalpha() for c in cleaned)

    if not has_alpha or not has_non_alpha:
        raise ValueError(
            "API key requires a mix of character types: must combine letters with numbers or special characters."
        )

    # 1. Sequential character runs via delta arithmetic (no static lists)
    if _detect_sequential_patterns(cleaned, min_len=4):
        raise ValueError(
            "API key contains predictable sequential characters (e.g. '1234' or 'abcd')."
        )

    # 2. String periodicity / repeating cyclical patterns
    if _detect_repeating_patterns(cleaned):
        raise ValueError("API key contains repeating or cyclical patterns. Please increase key complexity.")

    # 3. Information entropy assessment (Shannon entropy)
    entropy = calculate_shannon_entropy(cleaned)
    total_entropy = entropy * len(cleaned)
    if entropy < 2.2 or total_entropy < 20.0 or len(set(cleaned)) < 4:
        raise ValueError("API key entropy is too low. Key is too predictable; please use a more diverse passphrase.")

    return cleaned


def save_custom_api_key(config_dir: Path, custom_key: str) -> str:
    """
    Persist an authenticated custom API key securely (DPAPI on Windows, 0600 on POSIX).
    Provides a uniform merchant authentication secret for local billing applications.
    Enforces algorithmic passkey validation (Shannon entropy, sequential delta math,
    and cyclical periodicity elimination).
    """
    cleaned = validate_custom_api_key(custom_key)
    key_file = _key_file_path(config_dir)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    raw = b"STR:" + cleaned.encode("utf-8")
    _save_protected_key(key_file, raw)
    logger.info("Saved custom installation API key (%s)", platform.system())
    return cleaned


def is_custom_api_key(config_dir: Path) -> bool:
    """Return True if the currently persisted key is a custom integration key."""
    key_file = _key_file_path(config_dir)
    if not key_file.exists():
        return False
    try:
        raw = _load_protected_key(key_file)
        return raw.startswith(b"STR:")
    except Exception:
        return False


def constant_time_compare(provided: str | None, expected: str | None) -> bool:
    """Timing-safe equality comparison preventing timing side-channel attacks."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
