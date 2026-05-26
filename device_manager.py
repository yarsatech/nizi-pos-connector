"""
Serial (UART) device manager for the Nizi POS Connector–attached display.
"""

import struct
from typing import Optional
import threading
import time
import logging

import serial
import serial.tools.list_ports
import re

from ota.firmware_api import check_update_available

logger = logging.getLogger(__name__)

DEVICE_ID_COMMAND = "DEVICE_ID"
FIRMWARE_ID_COMMAND = "FIRMWARE_ID"
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
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._port: Optional[str] = None
        self._device_id: Optional[str] = None
        self._firmware_id: Optional[str] = None
        self._firmware_update_info: Optional[dict] = None  # cached update check result
        self._connected = False
        self._auto_connect = True  # Flag to enable/disable auto-connection polling
        self._auto_connect_suspend_until = 0.0
        self._on_status_change = None  # callback(connected: bool, port: str | None)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port(self) -> Optional[str]:
        return self._port

    @property
    def device_id(self) -> Optional[str]:
        return self._device_id

    @property
    def firmware_id(self) -> Optional[str]:
        return self._firmware_id

    @property
    def firmware_update_info(self) -> Optional[dict]:
        """Cached result of the last firmware update check, or None if not yet run."""
        return self._firmware_update_info

    def enable_auto_connect(self, enabled: bool):
        """Enable or disable the background auto-connect polling logic."""
        self._auto_connect = enabled
        logger.info(f"Auto-connect polling set to: {enabled}")

    def suspend_auto_connect(self, duration_sec: int):
        """Temporarily suspend auto-connect polling for the given duration."""
        self._auto_connect_suspend_until = time.time() + duration_sec
        logger.info(f"Auto-connect suspended for {duration_sec} seconds")

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
                if self._auto_connect and time.time() > self._auto_connect_suspend_until:
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

    def auto_detect(self) -> Optional[str]:
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

    def _probe_port(self, device: str) -> Optional[str]:
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

    def _extract_device_id(self, response: str) -> Optional[str]:
        if not response:
            return None
        m = DEVICE_ID_PATTERN.search(response)
        if not m:
            return None
        return m.group(0).upper().replace("_", "")

    def _query_device_id(self) -> Optional[str]:
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

    def _query_firmware_id(self) -> Optional[str]:
        """
        Query the connected device for its firmware version string.
        Returns the clean version as 'major.minor.patch' (e.g. '2.0.0'), or None.
        Any pre-release suffix (e.g. '-rc.2') is stripped.
        """
        if not self._serial or not self._serial.is_open:
            return None
        try:
            self._serial.reset_input_buffer()
            self._serial.write((FIRMWARE_ID_COMMAND + "\n").encode("utf-8"))
            self._serial.flush()
            response = self._serial.readline().decode("utf-8", errors="ignore").strip()
            if not response:
                return None
            fw = response.strip()
            # Strip leading 'V'/'v' prefix
            if fw.lower().startswith("v"):
                fw = fw[1:]
            # Strip any pre-release suffix (e.g. '-rc.2', '-beta.1')
            if "-" in fw:
                fw = fw.split("-", 1)[0]
            logger.info(f"Firmware ID: {fw!r}")
            return fw if fw else None
        except Exception as exc:
            logger.debug(f"Firmware ID query failed: {exc}")
            return None

    def query_firmware_id(self) -> dict:
        """
        Public method to re-query the firmware ID on-demand.
        Returns {"success": bool, "firmware_id": str | None, "error": str | None}.
        """
        with self._lock:
            if not self._connected or not self._serial or not self._serial.is_open:
                return {"success": False, "firmware_id": None, "error": "Device not connected."}
            try:
                self._firmware_id = self._query_firmware_id()
                return {"success": True, "firmware_id": self._firmware_id, "error": None}
            except Exception as exc:
                return {"success": False, "firmware_id": None, "error": str(exc)}

    def connect(self, port: Optional[str] = None) -> dict:
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
                self._firmware_id = self._query_firmware_id()
                self._port = port
                self._connected = True
                logger.info(f"Connected to {port} (device={self._device_id or 'unknown'}, firmware={self._firmware_id or 'unknown'})")
                self._notify_status()
                # Kick off firmware update check in background (non-blocking)
                threading.Thread(
                    target=self._background_firmware_check,
                    daemon=True,
                    name="firmware-update-check",
                ).start()
                return {"success": True, "port": port, "device_id": self._device_id, "firmware_id": self._firmware_id, "error": None}
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
            self._firmware_id = None
            self._firmware_update_info = None
            self._connected = False
            logger.info("Disconnected")
            self._notify_status()
            return {"success": True}

    def _background_firmware_check(self):
        """
        Run in a daemon thread after connect. Queries the Yarsa Tech firmware
        API to check if a newer firmware is available for this device.
        Caches the result in self._firmware_update_info.
        """
        # Snapshot values we need — avoid holding the lock during HTTP
        device_id = self._device_id
        firmware_id = self._firmware_id
        port = self._port

        if not device_id or not firmware_id:
            logger.debug("Skipping firmware update check: no device_id or firmware_id")
            return

        logger.info(f"Checking firmware update for {device_id} (installed: {firmware_id})")
        result = check_update_available(device_id, firmware_id, port)
        self._firmware_update_info = result

        if result.get("update_available"):
            logger.info(
                f"Firmware update available: {result['installed']} → {result['latest_clean']} "
                f"| {result['update_url']}"
            )
            # Re-emit status so UI/WebSocket picks up the update badge
            self._notify_status()
        elif result.get("error"):
            logger.debug(f"Firmware update check: {result['error']}")

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

    # ── Timeout & Buzzer ────────────────────────────────────────────────

    def set_timeout(self, qr_sec: int = 300, pf_sec: int = 20):
        """Set screen timeouts: QR display and Pass/Fail display (in seconds)."""
        return self.send_command(f"TIMEOUT**{qr_sec}**{pf_sec}")

    def activate_buzzer(self, enabled: int = 1):
        """Enable (1) or disable (0) the buzzer. B30 has buzzer disabled by default."""
        return self.send_command(f"ACTIVATE_BUZZER**{enabled}")

    # ── Bluetooth ───────────────────────────────────────────────────────

    def set_ble(self, enabled: bool):
        """Enable or disable Bluetooth (BLE_ON / BLE_OFF)."""
        return self.send_command("BLE_ON" if enabled else "BLE_OFF")

    # ── Idle mode commands ──────────────────────────────────────────────

    def get_idle(self):
        """Query the current idle configuration from the device."""
        return self.send_command("GET_IDLE")

    def set_idle_single(self, image_name: str = "IMG1"):
        """Fixed static background image idle mode."""
        return self.send_command(f"IDLE_SINGLE**{image_name}")

    def set_idle_cycle(self, img1: str = "IMG1", time1: int = 60000,
                       img2: str = "IMG2", time2: int = 60000):
        """Alternate between two images at defined intervals (ms)."""
        return self.send_command(f"IDLE_CYCLE**{img1}**{time1}**{img2}**{time2}")

    def set_idle_sleep(self, image_name: str = "IMG1", inactivity_ms: int = 30000):
        """Set idle mode to Sleep with persistent image name and inactivity timeout (ms)."""
        inactivity_ms = max(30000, inactivity_ms)
        return self.send_command(f"IDLE_SLEEP**{image_name}**{inactivity_ms}")

    def set_screentime(self, seconds: int = 30):
        """Set inactivity sleep timer in seconds (Min: 30s, Max: 300s, 0 to disable)."""
        return self.send_command(f"SCREENTIME**{seconds}")

    def set_idle_sleep_wake(self, image_name: str = "IMG1", sleep_ms: int = 30000, wake_ms: int = 120000):
        """Auto-cycle between Wake and Sleep states: IDLE_SLEEP_WAKE**[ImageName]**[SleepMS]**[WakeMS]."""
        sleep_ms = max(30000, sleep_ms)
        return self.send_command(f"IDLE_SLEEP_WAKE**{image_name}**{sleep_ms}**{wake_ms}")

    # ── Image upload ────────────────────────────────────────────────────

    def _upload_image_protocol(self, start_command: str, jpeg_data: bytes) -> dict:
        """
        Shared binary upload protocol for all image upload commands.
          1. Send start_command\\n
          2. Send MAGIC_FRAME (4 bytes) + JPEG length (4 bytes, little-endian)
          3. Wait for 'R' ready acknowledgement
          4. Send JPEG binary data
          5. Wait for 'K' (success) or 'E' (error)
        """
        with self._lock:
            if not self._connected or not self._serial or not self._serial.is_open:
                return {"success": False, "error": "Device not connected."}

            ser = self._serial
            orig_timeout = ser.timeout
            try:
                ser.timeout = 15.0
                ser.reset_input_buffer()

                # Step 1 – start command
                ser.write((start_command + "\n").encode("utf-8"))
                ser.flush()
                logger.info(f"Image upload: sent {start_command}")

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
            finally:
                ser.timeout = orig_timeout

    def upload_image(self, jpeg_data: bytes) -> dict:
        """Upload a JPEG image for real-time display (START_RTIMAGE)."""
        return self._upload_image_protocol(IMAGE_START_COMMAND, jpeg_data)

    def upload_wallpaper(self, jpeg_data: bytes, slot2: bool = False, progress_callback = None) -> dict:
        """
        Upload persistent wallpaper image (IMG1.jpg or IMG2.jpg) using the ESP32 chunked CRC32 protocol.
        """
        import zlib
        with self._lock:
            if not self._connected or not self._serial or not self._serial.is_open:
                return {"success": False, "error": "Device not connected."}

            ser = self._serial
            orig_timeout = ser.timeout
            try:
                ser.timeout = 5.0  # 5 seconds is plenty for individual chunk validation and read
                ser.reset_input_buffer()

                # Step 1: Send start command
                cmd = f"IMAGE_UPLOAD_2:{len(jpeg_data)}" if slot2 else f"IMAGE_UPLOAD:{len(jpeg_data)}"
                ser.write((cmd + "\n").encode("utf-8"))
                ser.flush()
                logger.info(f"Wallpaper upload: sent {cmd}")

                # Step 2: Wait for READY response
                start_time = time.time()
                ready_received = False
                while time.time() - start_time < 3.0:
                    if ser.in_waiting:
                        line = ser.readline().decode("utf-8", errors="ignore").strip()
                        if "READY" in line:
                            ready_received = True
                            break
                    time.sleep(0.05)

                if not ready_received:
                    return {"success": False, "error": "Device did not respond with READY."}
                logger.info("Wallpaper upload: device is READY")

                # Step 3: Send in chunks of 512 bytes
                chunk_size = 512
                offset = 0
                while offset < len(jpeg_data):
                    chunk = jpeg_data[offset : offset + chunk_size]
                    length = len(chunk)
                    
                    # Compute CRC32
                    crc = zlib.crc32(chunk) & 0xFFFFFFFF
                    crc_hex = f"{crc:08X}"

                    # Send CHUNK command
                    chunk_cmd = f"CHUNK:{offset},{length},{crc_hex}\n"
                    ser.write(chunk_cmd.encode("utf-8"))
                    ser.flush()

                    # Wait for CHUNK_START
                    start_time = time.time()
                    start_received = False
                    while time.time() - start_time < 3.0:
                        if ser.in_waiting:
                            line = ser.readline().decode("utf-8", errors="ignore").strip()
                            if "CHUNK_START" in line:
                                start_received = True
                                break
                        time.sleep(0.01)

                    if not start_received:
                        return {"success": False, "error": f"Device failed to prompt CHUNK_START at offset {offset}"}

                    # Send raw binary chunk data
                    ser.write(chunk)
                    ser.flush()

                    # Wait for CHUNK_OK
                    start_time = time.time()
                    ok_received = False
                    while time.time() - start_time < 3.0:
                        if ser.in_waiting:
                            line = ser.readline().decode("utf-8", errors="ignore").strip()
                            if "CHUNK_OK" in line:
                                ok_received = True
                                break
                            elif "CHUNK_FAIL" in line:
                                break
                        time.sleep(0.01)

                    if not ok_received:
                        return {"success": False, "error": f"Chunk verify failed at offset {offset}"}

                    offset += length
                    if progress_callback:
                        progress_callback(offset, len(jpeg_data))

                # Step 4: Wait for UPLOAD_DONE
                start_time = time.time()
                done_received = False
                while time.time() - start_time < 5.0:
                    if ser.in_waiting:
                        line = ser.readline().decode("utf-8", errors="ignore").strip()
                        if "UPLOAD_DONE" in line:
                            done_received = True
                            break
                    time.sleep(0.05)

                if not done_received:
                    logger.warning("All chunks sent OK but did not see UPLOAD_DONE confirmation.")

                logger.info("Wallpaper upload: SUCCESS")
                return {"success": True, "error": None}

            except Exception as exc:
                logger.error(f"Wallpaper upload error: {exc}")
                return {"success": False, "error": str(exc)}
            finally:
                ser.timeout = orig_timeout

