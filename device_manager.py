"""
Serial (UART) device manager for the Nizi POS Connector–attached display.
"""

import struct
import threading
import time
import logging

import serial
import serial.tools.list_ports
import re

logger = logging.getLogger(__name__)

DEVICE_ID_COMMAND = "DEVICE_ID"
# Hardware IDs: `NIZIPOS_B3X` / `NIZI_POS_B3X` (X = 0–9) — UART protocol, not the app display name.
DEVICE_ID_PATTERN = re.compile(r"NIZI_?POS_B3\d", re.IGNORECASE)
DEFAULT_BAUD_RATE = 115200
SERIAL_TIMEOUT = 2  # seconds

# Image upload constants
IMAGE_START_COMMAND = "START_RTIMAGE"
IMAGE_MAGIC_FRAME = struct.pack("<I", 0xAA55CC33) # 0xAA55CC33
IMAGE_ACK_OK = b"K"
IMAGE_ACK_ERR = b"E"
IMAGE_READY = b"R"

# CH340 Chipset Identifiers (for optimized discovery)
CH340_VID = 0x1A86
CH340_PIDS = [0x7523, 0x5523, 0x5512, 0x7522]


class DeviceManager:
    """Thread-safe UART communication with the connected display."""

    def __init__(self):
        self._serial: serial.Serial | None = None
        self._lock = threading.Lock()
        self._port: str | None = None
        self._device_id: str | None = None
        self._connected = False
        self._auto_connect = True  # Flag to enable/disable auto-connection polling
        self._on_status_change = None  # callback(connected: bool, port: str | None)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port(self) -> str | None:
        return self._port

    @property
    def device_id(self) -> str | None:
        return self._device_id

    def enable_auto_connect(self, enabled: bool):
        """Enable or disable the background auto-connect polling logic."""
        self._auto_connect = enabled
        logger.info(f"Auto-connect polling set to: {enabled}")

    def set_status_callback(self, callback):
        """Set a callback for connection status changes: callback(connected, port)."""
        self._on_status_change = callback

    def _notify_status(self):
        if self._on_status_change:
            try:
                self._on_status_change(self._connected, self._port)
            except Exception:
                pass

    def start_auto_connect(self):
        """Start a background thread that polls for the device if disconnected."""
        def _poll():
            while True:
                if self._auto_connect:
                    if not self.connected:
                        port = self.auto_detect()
                        if port:
                            self.connect(port)
                    else:
                        # Check if the currently connected port is physically still attached
                        active_ports = [p.device for p in serial.tools.list_ports.comports()]
                        if self.port not in active_ports:
                            logger.warning(f"Device physically unplugged: {self.port}")
                            self.disconnect()
                time.sleep(3)
                
        t = threading.Thread(target=_poll, daemon=True)
        t.start()

    # ── Connection ──────────────────────────────────────────────────────

    def auto_detect(self) -> str | None:
        """
        Scan COM ports, prioritizing CH340 chipsets.
        Sends DEVICE_ID and returns the port that responds with NIZI_POS_B31.
        """
        all_ports = serial.tools.list_ports.comports()
        
        # 1. Prioritize ports with CH340 VID/PID or "CH340" in description
        priority_ports = []
        other_ports = []
        
        for p in all_ports:
            is_ch340 = (
                p.vid == CH340_VID or 
                (p.pid in CH340_PIDS) or 
                "CH340" in (p.description or "").upper() or
                "CH340" in (p.hwid or "").upper()
            )
            if is_ch340:
                priority_ports.append(p)
            else:
                other_ports.append(p)

        # 2. Probe priority ports first
        for p in priority_ports:
            port_name = self._probe_port(p.device)
            if port_name:
                return port_name

        # 3. Fallback to other ports if priority ones didn't work
        # (Optional: user's environment might have multiple ports and they want it fast, 
        # so we only probe others if no priority ports were even found)
        if not priority_ports:
            logger.info("No CH340 devices matched, scanning other ports...")
            for p in other_ports:
                port_name = self._probe_port(p.device)
                if port_name:
                    return port_name
        
        return None

    def get_available_ports(self) -> list[dict]:
        """
        Return a list of available serial ports with metadata.
        Each entry: {"port": str, "description": str, "is_ch340": bool}
        """
        ports = []
        for p in serial.tools.list_ports.comports():
            is_ch340 = (
                p.vid == CH340_VID or 
                (p.pid in CH340_PIDS) or 
                "CH340" in (p.description or "").upper() or
                "CH340" in (p.hwid or "").upper()
            )
            ports.append({
                "port": p.device,
                "description": p.description,
                "is_ch340": is_ch340
            })
        return ports

    def _probe_port(self, device: str) -> str | None:
        """Internal helper to probe a specific port for the device ID."""
        try:
            logger.info(f"Probing {device} ...")
            ser = serial.Serial(
                device,
                baudrate=DEFAULT_BAUD_RATE,
                timeout=SERIAL_TIMEOUT,
            )
            time.sleep(0.1)  # let device settle

            ser.reset_input_buffer()
            ser.write((DEVICE_ID_COMMAND + "\n").encode("utf-8"))
            ser.flush()

            response = ser.readline().decode("utf-8", errors="ignore").strip()
            # Use ASCII arrows to avoid mojibake in some Windows consoles/log viewers.
            logger.info(f"  <- {response!r}")

            device_id = self._extract_device_id(response)
            if device_id:
                ser.close()
                return device

            ser.close()
        except (serial.SerialException, OSError) as exc:
            logger.debug(f"  skip {device}: {exc}")
        return None

    def _extract_device_id(self, response: str) -> str | None:
        if not response:
            return None
        m = DEVICE_ID_PATTERN.search(response)
        if not m:
            return None
        return m.group(0).upper().replace("_", "")

    def _query_device_id(self) -> str | None:
        """
        Query current connected serial for DEVICE_ID and return normalized value
        like NIZIPOSB31, or None on failure.
        """
        if not self._serial or not self._serial.is_open:
            return None
        try:
            self._serial.reset_input_buffer()
            self._serial.write((DEVICE_ID_COMMAND + "\n").encode("utf-8"))
            self._serial.flush()
            response = self._serial.readline().decode("utf-8", errors="ignore").strip()
            return self._extract_device_id(response)
        except Exception:
            return None

    def connect(self, port: str | None = None) -> dict:
        """
        Connect to the device.  If *port* is None, auto-detect is used.
        Returns {"success": bool, "port": str | None, "error": str | None}.
        """
        with self._lock:
            if self._connected:
                return {"success": True, "port": self._port, "device_id": self._device_id, "error": None}

            if port is None:
                port = self.auto_detect()
                if port is None:
                    return {
                        "success": False,
                        "port": None,
                        "error": "No matching display device found on any COM port.",
                    }

            try:
                self._serial = serial.Serial(
                    port,
                    baudrate=DEFAULT_BAUD_RATE,
                    timeout=SERIAL_TIMEOUT,
                )
                time.sleep(0.1)
                self._device_id = self._query_device_id()
                self._port = port
                self._connected = True
                logger.info(f"Connected to {port} ({self._device_id or 'unknown device id'})")
                self._notify_status()
                return {"success": True, "port": port, "device_id": self._device_id, "error": None}
            except serial.SerialException as exc:
                return {"success": False, "port": port, "device_id": None, "error": str(exc)}

    def disconnect(self) -> dict:
        """Disconnect from the device."""
        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except Exception:
                    pass
            self._serial = None
            self._port = None
            self._device_id = None
            self._connected = False
            logger.info("Disconnected")
            self._notify_status()
            return {"success": True}

    # ── Commands ────────────────────────────────────────────────────────

    def send_command(self, command: str) -> dict:
        """
        Send a text command to the device (newline-terminated).
        Returns {"success": bool, "error": str | None}.
        """
        with self._lock:
            if not self._connected or not self._serial or not self._serial.is_open:
                return {"success": False, "error": "Device not connected."}
            try:
                self._serial.reset_input_buffer()
                self._serial.write((command + "\n").encode("utf-8"))
                self._serial.flush()
                logger.info(f"Sent: {command}")
                return {"success": True, "error": None}
            except serial.SerialException as exc:
                logger.error(f"Send error: {exc}")
                self._connected = False
                self._notify_status()
                return {"success": False, "error": str(exc)}

    # ── Convenience command helpers ─────────────────────────────────────

    def send_idle(self):
        return self.send_command("IDLE")

    def send_text(self, title: str, subtitle: str, message: str):
        return self.send_command(f"TEXT**{title}**{subtitle}**{message}")

    def send_qr(self, amount: str, scan_text: str, payload: str):
        return self.send_command(f"QR**{amount}**{scan_text}**{payload}")

    def send_wait(self, amount: str, message: str):
        return self.send_command(f"WAIT**{amount}**{message}")

    def send_pass(self, title: str, message: str):
        return self.send_command(f"PASS**{title}**{message}")

    def send_fail(self, amount: str, message: str):
        return self.send_command(f"FAIL**{amount}**{message}")

    def send_warn(self, title: str, message: str):
        return self.send_command(f"WARN**{title}**{message}")

    def send_info(self, title: str, message: str):
        return self.send_command(f"INFO**{title}**{message}")

    def send_reset(self):
        return self.send_command("RESET")

    def send_format(self):
        return self.send_command("FORMAT")

    def send_wake(self):
        return self.send_command("WAKE")

    def set_volume(self, value: int):
        return self.send_command(f"VOLUME**{value}")

    def set_brightness(self, value: int):
        return self.send_command(f"BRIGHTNESS**{value}")

    def set_screentime(self, value: int):
        return self.send_command(f"SCREENTIME**{value}")

    # ── Image upload ────────────────────────────────────────────────────

    def upload_image(self, jpeg_data: bytes) -> dict:
        """
        Upload a JPEG image to the device following the documented protocol:
          1. Send START_RTIMAGE\\n
          2. Send MAGIC_FRAME (4 bytes) + JPEG length (4 bytes, little-endian)
          3. Wait for 'R' ready acknowledgement
          4. Send JPEG binary data
          5. Wait for 'K' (success) or 'E' (error)
        """
        with self._lock:
            if not self._connected or not self._serial or not self._serial.is_open:
                return {"success": False, "error": "Device not connected."}

            try:
                ser = self._serial
                ser.reset_input_buffer()

                # Step 1 – start command
                ser.write((IMAGE_START_COMMAND + "\n").encode("utf-8"))
                ser.flush()
                logger.info("Image upload: sent START_RTIMAGE")

                # The device needs time to create xTaskCreate and get ready
                time.sleep(0.15)

                # Step 2 – magic frame + length
                length_bytes = struct.pack("<I", len(jpeg_data))
                ser.write(IMAGE_MAGIC_FRAME + length_bytes)
                ser.flush()
                logger.info(f"Image upload: sent header (size={len(jpeg_data)})")

                # Step 3 – wait for ready signal
                time.sleep(0.1) # Wait slightly just in case
                ready = ser.read(1)
                if ready != IMAGE_READY:
                    # Let's read a little more to see if it's a longer message like 'FAIL'
                    time.sleep(0.1)
                    rest = ser.read(ser.in_waiting) if ser.in_waiting else b""
                    return {
                        "success": False,
                        "error": f"Device not ready (got {(ready + rest)!r}).",
                    }
                logger.info("Image upload: device ready")

                # Step 4 – send JPEG binary data in chunks
                chunk_size = 1024
                offset = 0
                while offset < len(jpeg_data):
                    chunk = jpeg_data[offset : offset + chunk_size]
                    ser.write(chunk)
                    offset += len(chunk)
                ser.flush()
                logger.info("Image upload: binary data sent")

                # Step 5 – wait for acknowledgement
                ack = ser.read(1)
                if ack == IMAGE_ACK_OK:
                    logger.info("Image upload: SUCCESS")
                    return {"success": True, "error": None}
                elif ack == IMAGE_ACK_ERR:
                    return {"success": False, "error": "Device reported image error."}
                else:
                    return {
                        "success": False,
                        "error": f"Unexpected ack: {ack!r}",
                    }

            except serial.SerialException as exc:
                logger.error(f"Image upload error: {exc}")
                self._connected = False
                self._notify_status()
                return {"success": False, "error": str(exc)}
