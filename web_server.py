"""
Nizi POS Connector — Flask + Flask-SocketIO server (REST + realtime) for the UART display.
"""

import logging
import os
import threading
import io
from PIL import Image

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO

from device_manager import DeviceManager

from config import config
from ota.github import normalize_github_repo

logger = logging.getLogger(__name__)

# ── Globals ──────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SECRET_KEY"] = config.api_key
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB limit

# Restrict CORS to localhost
# Use 'threading' async mode which is the most compatible with PyInstaller standard builds
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode="threading"
)

device = DeviceManager()

# ── Authentication ───────────────────────────────────────────────────────

@app.before_request
def require_api_key():
    """Verify X-API-Key header for all /api/ requests."""
    # Skip auth for CORS preflight (OPTIONS) requests
    if request.method == "OPTIONS":
        return

    if request.path.startswith("/api/"):
        # Check header
        api_key = request.headers.get("X-API-Key")
        if api_key != config.api_key:
            logger.warning(f"Unauthorized API request to {request.path} from {request.remote_addr}")
            return jsonify({"success": False, "error": "Unauthorized"}), 401


@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses to allow interaction with any origin."""
    origin = request.headers.get('Origin')
    if origin:
        # We allow any origin to connect, as long as it provides the correct API key.
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
    return response


def _on_device_status(connected: bool, port: str | None):
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

# Lightweight client config for UI (no API-key required).
@app.route("/client-config")
def client_config():
    return jsonify(
        {
            "contact_url": config.contact_url,
            "whatsapp_url": config.whatsapp_url,
        }
    )


# ── REST API ─────────────────────────────────────────────────────────────


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
    
    # Basic sanitization: check for allowed characters if needed
    # For now just ensure it's not too long
    if len(command) > 512:
         return jsonify({"success": False, "error": "Command too long."}), 400

    result = device.send_command(command.strip())
    return jsonify(result)


@app.route("/api/firmware")
def api_firmware():
    """Return the device firmware version and an update URL if available."""
    firmware_id = device.firmware_id
    device_id = device.device_id
    connected = device.connected

    # Build the firmware releases URL from the configured GitHub repo
    update_url = None
    repo_raw = getattr(config, "github_repo", "") or ""
    repo = normalize_github_repo(repo_raw)
    if repo:
        # Link to GitHub releases page filtered by the device model
        filter_query = device_id or ""
        update_url = f"https://github.com/{repo}/releases?q=firmware+{filter_query}"

    return jsonify({
        "connected": connected,
        "device_id": device_id,
        "firmware_id": firmware_id,
        "update_url": update_url,
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

        logger.info(f"Image processed: {len(jpeg_data)} bytes at quality={quality}")

    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return jsonify({"success": False, "error": f"Invalid image format or processing failed: {e}"}), 400

    result = device.upload_image(jpeg_data)
    return jsonify(result)


@app.route("/api/settings", methods=["POST"])
def api_settings():
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
    result = device.set_timeout(qr_sec, pf_sec)
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
        result = device.set_idle_sleep(image_name)
    elif mode == "SLEEP_WAKE":
        image_name = data.get("image_name", "IMG1")
        sleep_ms = int(data.get("sleep_ms", 30000))
        wake_ms = int(data.get("wake_ms", 120000))
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

        logger.info(f"Idle image (slot {slot}) processed: {len(jpeg_data)} bytes at quality={quality}")

    except Exception as e:
        logger.error(f"Idle image processing error: {e}")
        return jsonify({"success": False, "error": f"Invalid image format or processing failed: {e}"}), 400

    if slot == "2":
        result = device.upload_idle_image_2(jpeg_data)
    else:
        result = device.upload_idle_image(jpeg_data)
    return jsonify(result)


# ── SocketIO events ──────────────────────────────────────────────────────


@socketio.on("connect")
def ws_connect(auth=None):
    """Verify API token on SocketIO connection."""
    if not auth or auth.get("token") != config.api_key:
        logger.warning(f"Unauthorized SocketIO connection attempt from {request.remote_addr}")
        return False  # Disconnects the client
    
    socketio.emit(
        "device_status",
        {"connected": device.connected, "port": device.port, "device_id": device.device_id, "firmware_id": device.firmware_id},
    )


@socketio.on("send_command")
def ws_send_command(data):
    command = data.get("command", "")
    result = device.send_command(command)
    socketio.emit("command_result", {"command": command, **result})


# ── Server lifecycle ────────────────────────────────────────────────────


def start_server(host=None, port=None):
    """Start the web server (blocking). Call from a thread."""
    try:
        h = host or config.server_host
        p = port or config.server_port
        logger.info(f"Starting web server on {h}:{p}")
        # When frozen, we want to ensure we don't accidentally use reloader
        socketio.run(app, host=h, port=p, use_reloader=False, allow_unsafe_werkzeug=True)
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
