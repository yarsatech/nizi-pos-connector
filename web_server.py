"""
Nizi POS Connector — Flask + Flask-SocketIO server (REST + realtime) for the UART display.
"""

import logging
import os
import threading
import time
from collections import deque
import io
from PIL import Image
Image.MAX_IMAGE_PIXELS = 2000 * 2000
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory, Response
from flask_socketio import SocketIO

from theme_support import get_web_theme_css, prefers_light_theme

from device_manager import DeviceManager, validate_serial_frame

import secrets

from config import config
from security import constant_time_compare
from ota.firmware_api import get_languages, build_update_url, extract_model_code

logger = logging.getLogger(__name__)

# ── Globals ──────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SECRET_KEY"] = config.api_key or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB limit

socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode="threading"
)

device = DeviceManager()

# ── Security & CORS Engine ───────────────────────────────────────────────

PUBLIC_PATHS = frozenset({"/", "/favicon.ico", "/api/theme.css"})
PUBLIC_PREFIXES = ("/assets/", "/static/")


ALLOWED_EXTENSION_SCHEMES = (
    "chrome-extension://",
    "moz-extension://",
    "safari-extension://",
    "safari-web-extension://",
    "ms-browser-extension://",
)


def is_origin_allowed(origin: str | None) -> bool:
    """
    Evaluate Origin against active CORS configuration.
    Non-browser (curl, desktop) requests have no Origin and are permitted.
    All browser extensions (Chrome, Firefox, Safari, Edge) are permitted and authenticated via API key.
    In 'allow_all' mode, all origins are permitted.
    In 'allowlist' mode, origin must match configured allowed list (case-insensitive).
    """
    if not origin:
        return True
    clean_origin = origin.rstrip("/").lower()
    if clean_origin.startswith(ALLOWED_EXTENSION_SCHEMES):
        return True
    if config.cors_mode == "allow_all":
        return True
    allowed = [o.rstrip("/").lower() for o in config.cors_allowed_origins]
    return clean_origin in allowed



# ── In-Memory Auth Rate Limiting / Brute-Force Throttle ───────────────────
_AUTH_LOCK = threading.Lock()
_FAILED_AUTH_LOG: dict[str, deque[float]] = {}
_BLOCKED_CLIENTS: dict[str, float] = {}

MAX_FAILED_AUTH_ATTEMPTS = 10
AUTH_WINDOW_SECONDS = 60.0
AUTH_BLOCK_DURATION_SECONDS = 60.0


def _is_client_rate_limited(client_ip: str) -> bool:
    """Check if the client IP is currently blocked due to excessive failed auth attempts."""
    now = time.time()
    with _AUTH_LOCK:
        block_until = _BLOCKED_CLIENTS.get(client_ip, 0.0)
        if now < block_until:
            return True
        if client_ip in _BLOCKED_CLIENTS:
            del _BLOCKED_CLIENTS[client_ip]
        return False


def _record_failed_auth(client_ip: str) -> bool:
    """Record a failed auth attempt. Blocks client if threshold (10 / min) is exceeded."""
    now = time.time()
    with _AUTH_LOCK:
        # Periodic pruning of expired entries to prevent memory exhaustion
        if len(_FAILED_AUTH_LOG) > 200:
            expired_cutoff = now - AUTH_WINDOW_SECONDS
            stale_ips = [ip for ip, atts in _FAILED_AUTH_LOG.items() if not atts or atts[-1] < expired_cutoff]
            for ip in stale_ips:
                del _FAILED_AUTH_LOG[ip]

        attempts = _FAILED_AUTH_LOG.setdefault(client_ip, deque())
        cutoff = now - AUTH_WINDOW_SECONDS
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        attempts.append(now)

        if len(attempts) >= MAX_FAILED_AUTH_ATTEMPTS:
            _BLOCKED_CLIENTS[client_ip] = now + AUTH_BLOCK_DURATION_SECONDS
            attempts.clear()
            logger.warning(
                "Excessive failed auth attempts from %s (%d in %.0fs). Client blocked for %.0fs.",
                client_ip,
                MAX_FAILED_AUTH_ATTEMPTS,
                AUTH_WINDOW_SECONDS,
                AUTH_BLOCK_DURATION_SECONDS,
            )
            return True
        return False


def _clear_failed_auth(client_ip: str) -> None:
    """Clear recorded failure timestamps upon successful authentication."""
    with _AUTH_LOCK:
        _FAILED_AUTH_LOG.pop(client_ip, None)


def reset_rate_limits() -> None:
    """Reset all in-memory rate limiting state (useful for tests and manual resets)."""
    with _AUTH_LOCK:
        _FAILED_AUTH_LOG.clear()
        _BLOCKED_CLIENTS.clear()


@app.before_request
def enforce_security_and_cors():
    """
    1. Reject requests from unauthorized Origins (CORS lockdown).
    2. Enforce default-deny authentication on all non-public endpoints.
    """
    origin = request.headers.get("Origin")
    if origin and not is_origin_allowed(origin):
        logger.warning(
            "Blocked request from unauthorized Origin: %s (mode: %s)",
            origin,
            config.cors_mode,
        )
        if request.method == "OPTIONS":
            return "", 403
        return jsonify({"success": False, "error": "Origin not allowed by policy"}), 403

    if request.method == "OPTIONS":
        return None

    # Public static and asset paths
    if request.path in PUBLIC_PATHS or any(request.path.startswith(p) for p in PUBLIC_PREFIXES):
        return None

    client_ip = request.remote_addr or "127.0.0.1"

    # Brute-force throttling / rate-limiting
    if _is_client_rate_limited(client_ip):
        logger.warning("Throttled request to %s from rate-limited client %s", request.path, client_ip)
        resp = jsonify({
            "success": False,
            "error": "Too Many Requests",
            "message": "Too many failed authentication attempts. Please wait before retrying."
        })
        resp.headers["Retry-After"] = str(int(AUTH_BLOCK_DURATION_SECONDS))
        return resp, 429

    # Enforce API key authentication (default-deny)
    expected_key = config.api_key
    if not expected_key:
        logger.error("API Key unreadable or uninitialized; failing closed")
        return jsonify({"success": False, "error": "Server credential unavailable"}), 503

    provided_key = request.headers.get("X-API-Key")
    if not constant_time_compare(provided_key, expected_key):
        if provided_key:
            _record_failed_auth(client_ip)
        logger.warning("Unauthorized request to %s from %s", request.path, client_ip)
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    _clear_failed_auth(client_ip)
    return None


@app.after_request
def add_cors_headers(response):
    """Reflect allowed Origin and inject standard banking-grade security headers."""
    origin = request.headers.get("Origin")
    if origin and is_origin_allowed(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
        response.headers["Vary"] = "Origin"

    # Banking-grade defensive HTTP headers (ISO 27001 A.14.1.2, OWASP A05:2021)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.socket.io; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self' ws: wss:;"
    )
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"

    return response


def _on_device_status(connected: bool, port: Optional[str]):
    """Push connection status to all connected browser clients."""
    socketio.emit(
        "device_status",
        {"connected": connected, "port": port, "device_id": device.device_id, "firmware_id": device.firmware_id},
    )


device.set_status_callback(_on_device_status)

# ── Static / UI ──────────────────────────────────────────────────────────


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory("assets", "icon.ico")

# Serve packaged assets (PyInstaller bundles repo-root `assets/`).
@app.route("/assets/<path:filename>")
def assets_file(filename: str):
    return send_from_directory("assets", filename)

@app.route("/client-config")
def client_config():
    return jsonify(
        {
            "contact_url": config.contact_url,
            "whatsapp_url": config.whatsapp_url,
            "cors_allowed_origins": config.cors_allowed_origins,
            "cors_mode": config.cors_mode,
        }
    )


# ── REST API ─────────────────────────────────────────────────────────────

@app.route("/api/theme.css")
def api_theme_css():
    """Dynamically serve CSS variables based on the centralized UI theme."""
    # We could also accept an overrides parameter or client pref, but for now rely on OS theme.
    is_light = prefers_light_theme()
    css_content = get_web_theme_css(is_light)
    return Response(css_content, mimetype="text/css")


@app.route("/api/status")
def api_status():
    return jsonify({
        "connected": device.connected,
        "port": device.port,
        "device_id": device.device_id,
        "firmware_id": device.firmware_id,
    })


@app.route("/api/connect", methods=["POST"])
def api_connect():
    data = request.get_json(silent=True) or {}
    port = data.get("port")  # None means auto-detect
    result = device.connect(port)
    return jsonify(result)


@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    result = device.disconnect()
    return jsonify(result)


@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json(silent=True) or {}
    command = data.get("command")
    if not isinstance(command, str) or not command.strip():
        return jsonify({"success": False, "error": "Invalid or missing command."}), 400

    try:
        clean_cmd = validate_serial_frame(command, allow_admin=False)
    except ValueError as err:
        logger.warning("Rejected invalid command: %s", err)
        return jsonify({"success": False, "error": str(err)}), 400

    result = device.send_command(clean_cmd)
    return jsonify(result)


@app.route("/api/firmware")
def api_firmware():
    """Return the device firmware version, update availability, and update URL."""
    firmware_id = device.firmware_id
    device_id = device.device_id
    connected = device.connected
    update_info = device.firmware_update_info or {}

    return jsonify({
        "connected": connected,
        "device_id": device_id,
        "firmware_id": firmware_id,
        "update_available": update_info.get("update_available", False),
        "latest_version": update_info.get("latest_clean"),
        "update_url": update_info.get("update_url"),
    })


@app.route("/api/upload-image", methods=["POST"])
def api_upload_image():
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided."}), 400
    file = request.files["image"]
    
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg'):
        return jsonify({"success": False, "error": "Only JPG/JPEG files are allowed."}), 400

    raw_data = file.read()
    if not raw_data:
        return jsonify({"success": False, "error": "Empty image file."}), 400

    try:
        # Load the image using Pillow and check format
        img = Image.open(io.BytesIO(raw_data))
        if img.format != 'JPEG':
             return jsonify({"success": False, "error": "Invalid JPEG content."}), 400
        if img.width > 2000 or img.height > 2000:
             return jsonify({"success": False, "error": "Image resolution exceeds 2000x2000 limit."}), 400
        
        # Convert to RGB (to ensure JPEG compatibility, discarding alpha layer if any)
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        # Resize to requested dimensions explicitly
        size_str = request.form.get("size", "320x480")
        try:
            width_str, height_str = size_str.split("x")
            width, height = int(width_str), int(height_str)
            # Security: cap dimensions
            if width > 800 or height > 800 or width < 10 or height < 10:
                width, height = 320, 480
        except ValueError:
            width, height = 320, 480
            
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Ensure it is under 30KB using a quality reduction loop
        max_size = 30 * 1024
        quality = 95
        jpeg_data = b""
        
        while quality > 5:
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=False)
            jpeg_data = output.getvalue()
            
            if len(jpeg_data) <= max_size:
                break
                
            quality -= 5
            
        if len(jpeg_data) > max_size:
            logger.warning(f"Could not compress image under 30KB (size: {len(jpeg_data)} bytes)")
            return jsonify({"success": False, "error": "Image complexity exceeds maximum 30KB transmission limit."}), 400

        logger.info(f"Image processed: {len(jpeg_data)} bytes at quality={quality}")

    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return jsonify({"success": False, "error": f"Invalid image format or processing failed: {e}"}), 400

    result = device.upload_image(jpeg_data)
    return jsonify(result)


def _parse_get_idle(response: str) -> dict:
    result = {}
    if not response:
        return result
    try:
        parts = response.split(",")
        for part in parts:
            if ":" in part:
                k, v = part.split(":", 1)
                result[k.strip().lower()] = v.strip()
            elif "=" in part:
                k, v = part.split("=", 1)
                result[k.strip().lower()] = v.strip()
    except Exception as e:
        logger.error(f"Error parsing GET_IDLE response {response!r}: {e}")
    return result


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "GET":
        settings = {}
        # 1. Volume
        res_vol = device.get_volume()
        if res_vol.get("success") and res_vol.get("response"):
            resp = res_vol["response"]
            if "**" in resp:
                try:
                    settings["volume"] = int(resp.split("**")[1])
                except ValueError:
                    pass
        # 2. Brightness
        res_bright = device.get_brightness()
        if res_bright.get("success") and res_bright.get("response"):
            resp = res_bright["response"]
            if "**" in resp:
                try:
                    settings["brightness"] = int(resp.split("**")[1])
                except ValueError:
                    pass
        # 3. BLE
        res_ble = device.is_ble_on()
        if res_ble.get("success") and res_ble.get("response"):
            settings["ble"] = (res_ble["response"] == "TRUE")
            
        # 4. Idle Mode
        res_idle = device.get_idle()
        if res_idle.get("success") and res_idle.get("response"):
            settings["idle_config"] = _parse_get_idle(res_idle["response"])
            
        return jsonify({"success": True, "settings": settings})

    data = request.get_json(silent=True) or {}
    results = {}

    try:
        if "volume" in data:
            val = int(data["volume"])
            if 0 <= val <= 100:
                results["volume"] = device.set_volume(val)
        if "brightness" in data:
            val = int(data["brightness"])
            if 0 <= val <= 100:
                results["brightness"] = device.set_brightness(val)
        if "screentime" in data:
            val = int(data["screentime"])
            if 1 <= val <= 3600:
                results["screentime"] = device.set_screentime(val)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid settings value type."}), 400

    if not results:
        return jsonify({"success": False, "error": "No valid settings provided."}), 400
    return jsonify({"success": True, "results": results})


@app.route("/api/timeout", methods=["POST"])
def api_timeout():
    """Set screen timeouts for QR and Pass/Fail displays (in seconds)."""
    data = request.get_json(silent=True) or {}
    try:
        qr_sec = int(data.get("qr_timeout", 300))
        pf_sec = int(data.get("pf_timeout", 20))
        if not (1 <= qr_sec <= 3600) or not (1 <= pf_sec <= 3600):
            return jsonify({"success": False, "error": "Timeout values must be between 1 and 3600."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid timeout value type."}), 400
    result = device.set_timeout(qr_sec * 1000, pf_sec * 1000)
    return jsonify(result)


@app.route("/api/buzzer", methods=["POST"])
def api_buzzer():
    """Enable or disable the buzzer (B30 has it disabled by default)."""
    data = request.get_json(silent=True) or {}
    try:
        enabled = int(data.get("enabled", 1))
        if enabled not in (0, 1):
            return jsonify({"success": False, "error": "Buzzer value must be 0 or 1."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid buzzer value."}), 400
    result = device.activate_buzzer(enabled)
    return jsonify(result)


@app.route("/api/idle-mode", methods=["POST"])
def api_idle_mode():
    """
    Set the device idle mode.
    Modes: SINGLE, CYCLE, SLEEP, SLEEP_WAKE
    """
    data = request.get_json(silent=True) or {}
    mode = (data.get("mode") or "").upper().strip()

    if mode == "SINGLE":
        image_name = data.get("image_name", "IMG1")
        result = device.set_idle_single(image_name)
    elif mode == "CYCLE":
        img1 = data.get("img1", "IMG1")
        time1 = int(data.get("time1", 60000))
        img2 = data.get("img2", "IMG2")
        time2 = int(data.get("time2", 60000))
        result = device.set_idle_cycle(img1, time1, img2, time2)
    elif mode == "SLEEP":
        image_name = data.get("image_name", "IMG1")
        inactivity_ms = max(30000, int(data.get("inactivity_ms", 30000)))
        result = device.set_idle_sleep(image_name, inactivity_ms)
    elif mode == "SLEEP_WAKE":
        image_name = data.get("image_name", "IMG1")
        wake_ms = int(data.get("wake_ms", 120000))
        sleep_ms = max(30000, int(data.get("sleep_ms", 30000)))
        result = device.set_idle_sleep_wake(image_name, sleep_ms, wake_ms)
    else:
        return jsonify({"success": False, "error": f"Unknown idle mode: {mode!r}. Use SINGLE, CYCLE, SLEEP, or SLEEP_WAKE."}), 400

    return jsonify(result)


@app.route("/api/upload-idle-image", methods=["POST"])
def api_upload_idle_image():
    """Upload a persistent idle image (IMG1 or IMG2) to the device."""
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided."}), 400
    file = request.files["image"]

    # Which slot: "1" (default) or "2"
    slot = request.form.get("slot", "1").strip()
    if slot not in ("1", "2"):
        return jsonify({"success": False, "error": "Slot must be '1' or '2'."}), 400

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg'):
        return jsonify({"success": False, "error": "Only JPG/JPEG files are allowed."}), 400

    raw_data = file.read()
    if not raw_data:
        return jsonify({"success": False, "error": "Empty image file."}), 400

    try:
        img = Image.open(io.BytesIO(raw_data))
        if img.format != 'JPEG':
            return jsonify({"success": False, "error": "Invalid JPEG content."}), 400
        if img.width > 2000 or img.height > 2000:
            return jsonify({"success": False, "error": "Image resolution exceeds 2000x2000 limit."}), 400

        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize to requested dimensions
        size_str = request.form.get("size", "320x480")
        try:
            width_str, height_str = size_str.split("x")
            width, height = int(width_str), int(height_str)
            if width > 800 or height > 800 or width < 10 or height < 10:
                width, height = 320, 480
        except ValueError:
            width, height = 320, 480

        img = img.resize((width, height), Image.Resampling.LANCZOS)

        # Compress to fit under 30KB
        max_size = 30 * 1024
        quality = 95
        jpeg_data = b""

        while quality > 5:
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=False)
            jpeg_data = output.getvalue()
            if len(jpeg_data) <= max_size:
                break
            quality -= 5

        if len(jpeg_data) > max_size:
            logger.warning(f"Could not compress idle image under 30KB (size: {len(jpeg_data)} bytes)")
            return jsonify({"success": False, "error": "Image complexity exceeds maximum 30KB transmission limit."}), 400

        logger.info(f"Idle image (slot {slot}) processed: {len(jpeg_data)} bytes at quality={quality}")

    except Exception as e:
        logger.error(f"Idle image processing error: {e}")
        return jsonify({"success": False, "error": f"Invalid image format or processing failed: {e}"}), 400

    if slot == "2":
        result = device.upload_wallpaper(jpeg_data, slot2=True)
    else:
        result = device.upload_wallpaper(jpeg_data, slot2=False)
    return jsonify(result)


@app.route("/api/get-volume", methods=["GET", "POST"])
def api_get_volume():
    """Query speaker volume level from the device."""
    result = device.get_volume()
    if result.get("success") and result.get("response"):
        resp = result["response"]
        if "**" in resp:
            try:
                result["volume"] = int(resp.split("**")[1])
            except ValueError:
                pass
    return jsonify(result)


@app.route("/api/get-brightness", methods=["GET", "POST"])
def api_get_brightness():
    """Query LCD backlight brightness level from the device."""
    result = device.get_brightness()
    if result.get("success") and result.get("response"):
        resp = result["response"]
        if "**" in resp:
            try:
                result["brightness"] = int(resp.split("**")[1])
            except ValueError:
                pass
    return jsonify(result)


@app.route("/api/get-ble", methods=["GET", "POST"])
def api_get_ble():
    """Query whether BLE stack is currently running."""
    result = device.is_ble_on()
    if result.get("success") and result.get("response"):
        result["ble_on"] = (result["response"] == "TRUE")
    return jsonify(result)


@app.route("/api/get-idle", methods=["GET", "POST"])
def api_get_idle():
    """Query the current idle configuration from the device."""
    result = device.get_idle()
    if result.get("success") and result.get("response"):
        result["idle_config"] = _parse_get_idle(result["response"])
    return jsonify(result)


@app.route("/api/languages", methods=["GET"])
def api_languages():
    """Get list of supported languages from Yarsa API."""
    langs = get_languages()
    return jsonify({"success": True, "languages": langs})


@app.route("/api/language-update-url", methods=["GET", "POST"])
def api_language_update_url():
    """Build update URL for specific language and model."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
    else:
        data = request.args
        
    lang = data.get("language")
    if not lang:
        return jsonify({"success": False, "error": "Missing 'language' parameter."}), 400
        
    model = getattr(device, "model", None) or extract_model_code(device.device_id)
    if not model:
        return jsonify({"success": False, "error": "Device model could not be determined. Please ensure device is connected."}), 400
        
    url = build_update_url(model=model, port=device.port, language=lang)
    return jsonify({"success": True, "url": url})


@app.route("/api/prepare-for-flash", methods=["POST"])
def api_prepare_for_flash():
    """Suspend auto-connection and disconnect serial port to free it for flashing."""
    data = request.get_json(silent=True) or {}
    try:
        duration = int(data.get("duration", 120))
    except (ValueError, TypeError):
        duration = 120
    
    device.suspend_auto_connect(duration)
    device.disconnect()
    return jsonify({"success": True, "suspended_for": duration})


@app.route("/api/ble", methods=["POST"])
def api_ble():
    """Enable or disable Bluetooth (BLE_ON / BLE_OFF)."""
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled")
    if enabled is None:
        return jsonify({"success": False, "error": "Missing 'enabled' field (true/false)."}), 400
    result = device.set_ble(bool(enabled))
    return jsonify(result)


# ── SocketIO events ──────────────────────────────────────────────────────


@socketio.on("connect")
def ws_connect(auth=None):
    """Verify origin and API token on SocketIO connection."""
    origin = request.headers.get("Origin")
    if origin and not is_origin_allowed(origin):
        logger.warning("Rejected SocketIO connection from disallowed Origin: %s", origin)
        return False

    client_ip = request.remote_addr or "127.0.0.1"
    if _is_client_rate_limited(client_ip):
        logger.warning("Rejected SocketIO connection due to rate limiting from %s", client_ip)
        return False

    token = (auth or {}).get("token")
    if not token or not constant_time_compare(token, config.api_key):
        _record_failed_auth(client_ip)
        logger.warning("Unauthorized SocketIO connection attempt from %s", client_ip)
        return False

    _clear_failed_auth(client_ip)

    socketio.emit(
        "device_status",
        {
            "connected": device.connected,
            "port": device.port,
            "device_id": device.device_id,
            "firmware_id": device.firmware_id,
            "update_available": (device.firmware_update_info or {}).get("update_available", False),
        },
    )


@socketio.on("send_command")
def ws_send_command(data):
    command = (data or {}).get("command", "")
    try:
        clean_cmd = validate_serial_frame(command, allow_admin=False)
    except ValueError as err:
        socketio.emit("command_result", {"command": command, "success": False, "error": str(err)})
        return
    result = device.send_command(clean_cmd)
    socketio.emit("command_result", {"command": clean_cmd, **result})


# ── Server lifecycle ────────────────────────────────────────────────────


def start_server(host=None, port=None):
    """Start the web server (blocking). Call from a thread."""
    try:
        h = host or config.server_host
        p = port or config.server_port
        logger.info(f"Starting web server on {h}:{p}")
        import waitress
        logger.info(f"Serving via production Waitress WSGI server on {h}:{p}")
        waitress.serve(app, host=h, port=p, threads=16, ident=None)
    except Exception as e:
        logger.error(f"CRITICAL: Web server failed to start: {e}", exc_info=True)


def start_server_thread(host=None, port=None) -> threading.Thread:
    """Start the web server in a daemon thread and return the thread."""
    t = threading.Thread(target=start_server, args=(host, port), daemon=True)
    t.start()
    return t


def get_device_manager() -> DeviceManager:
    """Return the singleton DeviceManager instance."""
    return device
