"""
Yarsa Tech ESP32 Firmware Public API client.

Checks whether a newer firmware version is available for the connected
device and builds the redirect URL to the web flash page.

Base URL: https://yarsa.tech/api/method/inventory_procurement.api.esp32_firmware_api
"""

import re
import logging
import urllib.request
import urllib.parse
import json

logger = logging.getLogger(__name__)

_BASE_URL = (
    "https://yarsa.tech/api/method/"
    "inventory_procurement.api.esp32_firmware_api"
)
_FIRMWARE_UPDATE_PAGE = "https://yarsa.tech/firmware-update"

# Timeout for all HTTP requests (seconds)
_REQUEST_TIMEOUT = 10


# ── Model extraction ─────────────────────────────────────────────────────────

_MODEL_PATTERN = re.compile(r"B3\d", re.IGNORECASE)


def extract_model_code(device_id: str) -> str | None:
    """
    Extract the model code (e.g. 'B31') from a raw device_id string.

    Examples:
        "NIZIPOSB31"   → "B31"
        "NIZI_POS_B30" → "B30"
        "NIZIPOSB32"   → "B32"
    """
    if not device_id:
        return None
    normalized = device_id.upper().replace("_", "")
    match = _MODEL_PATTERN.search(normalized)
    return match.group(0).upper() if match else None


# ── Version helpers ───────────────────────────────────────────────────────────

def _strip_firmware_prefix(version: str) -> str:
    """
    Strip any leading non-numeric prefix from a firmware version string so
    it can be compared as a plain major.minor.patch tuple.

    Examples:
        "FW-B31-v1.2.0" → "1.2.0"
        "v2.0.0"        → "2.0.0"
        "2.0.0"         → "2.0.0"
    """
    # Find the first digit and take everything from there
    match = re.search(r"\d+\.\d+", version or "")
    if not match:
        return version
    return version[match.start():]


def _parse_version_tuple(v: str) -> tuple[int, ...]:
    """Parse a clean version string like '1.2.0' into a comparable tuple."""
    v = (v or "").strip().lstrip("vV")
    v = re.sub(r"[^0-9.]", "", v)
    parts = [p for p in v.split(".") if p]
    nums: list[int] = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    return tuple(nums)


def _is_newer(latest: str, current: str) -> bool:
    """Return True if *latest* version is strictly newer than *current*."""
    return _parse_version_tuple(latest) > _parse_version_tuple(current)


# ── API client ───────────────────────────────────────────────────────────────

def get_firmware_by_model(model: str) -> dict:
    """
    Call GET /get_firmware_by_model?model=<model> and return the parsed
    ``data`` dict on success.

    Returns a dict with keys:
        model, item_code, item_prefix, firmware_version,
        firmware_zip_url, remark

    Raises ``RuntimeError`` on HTTP/network/parse errors.
    """
    params = urllib.parse.urlencode({"model": model})
    url = f"{_BASE_URL}.get_firmware_by_model?{params}"
    logger.debug(f"Firmware API request: {url}")

    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "NiziPOSConnector"},
        )
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        raise RuntimeError(f"Firmware API request failed: {exc}") from exc

    try:
        payload = json.loads(raw)
        envelope = payload.get("message", {})
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Firmware API returned invalid JSON: {exc}") from exc

    if not envelope.get("success"):
        err = envelope.get("error") or {}
        code = err.get("code", "UNKNOWN") if isinstance(err, dict) else str(err)
        msg = envelope.get("message", "Unknown error")
        raise RuntimeError(f"Firmware API error [{code}]: {msg}")

    data = envelope.get("data", {})
    if not data:
        raise RuntimeError("Firmware API returned empty data")

    logger.debug(f"Firmware API response for {model}: {data}")
    return data


# ── Update check ─────────────────────────────────────────────────────────────

def check_update_available(
    device_id: str,
    installed_version: str,
    port: str | None = None,
) -> dict:
    """
    High-level check: given the connected device_id and its installed
    firmware version, query the API and determine if an update is available.

    Returns a dict:
    {
        "update_available": bool,
        "model": "B31" | None,
        "installed": "2.0.0",
        "latest": "FW-B31-v1.2.0",       # raw API value
        "latest_clean": "1.2.0",          # stripped for display
        "update_url": "https://...",       # ready-to-open browser link
        "error": None | "error message"   # set on failure, update_available=False
    }
    """
    result: dict = {
        "update_available": False,
        "model": None,
        "installed": installed_version or "",
        "latest": None,
        "latest_clean": None,
        "update_url": None,
        "error": None,
    }

    model = extract_model_code(device_id)
    result["model"] = model

    if not model:
        result["error"] = f"Could not extract model code from device_id: {device_id!r}"
        logger.warning(result["error"])
        return result

    try:
        data = get_firmware_by_model(model)
    except RuntimeError as exc:
        result["error"] = str(exc)
        logger.warning(f"Firmware update check failed: {exc}")
        return result

    latest_raw = data.get("firmware_version") or ""
    latest_clean = _strip_firmware_prefix(latest_raw)

    result["latest"] = latest_raw
    result["latest_clean"] = latest_clean
    result["update_url"] = build_update_url(model, latest_raw, port)

    if not latest_clean:
        result["error"] = "API returned empty firmware version"
        return result

    installed_clean = _strip_firmware_prefix(installed_version or "")
    result["update_available"] = _is_newer(latest_clean, installed_clean)

    logger.info(
        f"Firmware check [{model}]: installed={installed_clean!r} "
        f"latest={latest_clean!r} update_available={result['update_available']}"
    )
    return result


# ── URL builder ───────────────────────────────────────────────────────────────

def build_update_url(
    model: str,
    firmware_version: str,
    port: str | None = None,
) -> str:
    """
    Build the firmware-update web page URL with query parameters.

    Example:
        https://yarsa.tech/firmware-update?model=B31&firmware=FW-B31-v1.2.0&port=COM15
    """
    params: dict[str, str] = {}
    if model:
        params["model"] = model
    if firmware_version:
        params["firmware"] = firmware_version
    if port:
        params["port"] = port

    if params:
        return f"{_FIRMWARE_UPDATE_PAGE}?{urllib.parse.urlencode(params)}"
    return _FIRMWARE_UPDATE_PAGE
