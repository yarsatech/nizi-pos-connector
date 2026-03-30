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
        {"connected": connected, "port": port, "device_id": device.device_id},
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
    return jsonify({"connected": device.connected, "port": device.port, "device_id": device.device_id})


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


# ── SocketIO events ──────────────────────────────────────────────────────


@socketio.on("connect")
def ws_connect(auth=None):
    """Verify API token on SocketIO connection."""
    if not auth or auth.get("token") != config.api_key:
        logger.warning(f"Unauthorized SocketIO connection attempt from {request.remote_addr}")
        return False  # Disconnects the client
    
    socketio.emit(
        "device_status",
        {"connected": device.connected, "port": device.port, "device_id": device.device_id},
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
