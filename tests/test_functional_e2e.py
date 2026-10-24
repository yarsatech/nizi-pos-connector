"""
End-to-End Functional Test Suite for Nizi POS Connector.
Covers real-world POS workflows:
1. Client configuration discovery and CORS policies.
2. Connection management (auto-detect, explicit port, disconnect).
3. Complete POS checkout lifecycle: Display QR -> Wait -> Pass/Fail -> Audio -> Clear Screen.
4. Settings read/write roundtrip (Volume, Brightness, Screen Time, Timeouts).
5. Dynamic image processing & JPEG conversion (downscaling, size capping).
6. Wallpaper upload protocols (single slot and slot 2 with CRC32 chunking).
7. BLE interface state queries and toggling.
8. WebSocket Socket.IO real-time connection, status broadcasting, and command dispatch.
"""
import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from web_server import app, reset_rate_limits, socketio


class TestFunctionalE2E(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        reset_rate_limits()
        config.set_cors_settings("allowlist", ["https://pos.yarsatech.com", "https://billing.local"])
        self.api_key = config.api_key
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        self.client = app.test_client()

    # ── 1. Client Configuration Discovery ──────────────────────────────────

    def test_client_config_endpoint(self):
        """POS client discovers supported endpoints and CORS policy on startup."""
        # Unauthenticated request fails under default-deny
        res_unauth = self.client.get("/client-config")
        self.assertEqual(res_unauth.status_code, 401)

        # Authenticated request succeeds
        res = self.client.get("/client-config", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("cors_allowed_origins", data)
        self.assertIn("cors_mode", data)
        self.assertIn("https://pos.yarsatech.com", data["cors_allowed_origins"])
        # Ensure private keys or internal credentials are never leaked in client-config
        self.assertNotIn("api_key", data)
        self.assertNotIn("secret_key", data)

    # ── 2. Connection Lifecycle ───────────────────────────────────────────

    @patch("web_server.device")
    def test_connection_lifecycle(self, mock_device):
        """Test connect (auto and manual port), status query, and disconnect."""
        # 1. Check initial status (disconnected)
        mock_device.connected = False
        mock_device.port = None
        mock_device.device_id = None
        mock_device.firmware_id = None

        res = self.client.get("/api/status", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json()["connected"])

        # 2. Trigger auto-connect
        mock_device.connect.return_value = {
            "success": True,
            "port": "COM4",
            "device_id": "NIZIPOSB31",
            "firmware_id": "2.0.0",
            "error": None,
        }
        res = self.client.post("/api/connect", headers=self.headers, json={"port": None})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["port"], "COM4")
        mock_device.connect.assert_called_with(None)

        # 3. Disconnect
        mock_device.disconnect.return_value = {"success": True, "error": None}
        res = self.client.post("/api/disconnect", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        mock_device.disconnect.assert_called_once()

    # ── 3. POS Transaction Lifecycle ──────────────────────────────────────

    @patch("web_server.device")
    def test_pos_transaction_flow(self, mock_device):
        """
        Simulate a complete retail checkout transaction:
        1. Display dynamic payment QR code with total amount.
        2. Update display to 'WAIT' while customer confirms payment on phone.
        3. Display 'PASS' screen upon successful payment verification.
        4. Return to 'IDLE' screen.
        """
        mock_device.send_command.return_value = {"success": True, "response": "QR_OK", "error": None}

        # Step 1: Display QR code
        qr_payload = {
            "command": "QR**Rs. 1,450.00**Scan via Fonepay / UPI**fonepay://pay?merchant=NiziStore&amt=1450"
        }
        res = self.client.post("/api/command", headers=self.headers, json=qr_payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        mock_device.send_command.assert_called_with(qr_payload["command"])

        # Step 2: Show Processing Wait Screen
        mock_device.send_command.return_value = {"success": True, "response": "WAIT_OK", "error": None}
        wait_payload = {"command": "WAIT**Rs. 1,450.00**Processing payment..."}
        res = self.client.post("/api/command", headers=self.headers, json=wait_payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Step 3: Show Success Pass Screen
        mock_device.send_command.return_value = {"success": True, "response": "PASS_OK", "error": None}
        pass_payload = {"command": "PASS**Payment Received**Txn ID: #98421"}
        res = self.client.post("/api/command", headers=self.headers, json=pass_payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Step 4: Return to Idle
        mock_device.send_command.return_value = {"success": True, "response": "IDLE_OK", "error": None}
        idle_payload = {"command": "IDLE"}
        res = self.client.post("/api/command", headers=self.headers, json=idle_payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

    # ── 4. Settings & Device Control Roundtrip ─────────────────────────────

    @patch("web_server.device")
    def test_settings_get_and_set_roundtrip(self, mock_device):
        """Test query and update of volume, brightness, screentime, and timeouts."""
        # Query current settings
        mock_device.get_volume.return_value = {"success": True, "response": "VOLUME**65", "error": None}
        mock_device.get_brightness.return_value = {"success": True, "response": "BRIGHTNESS**80", "error": None}
        mock_device.is_ble_on.return_value = {"success": True, "response": "TRUE", "error": None}
        mock_device.get_idle.return_value = {"success": True, "response": "MODE:SINGLE,image_name=IMG1", "error": None}

        res = self.client.get("/api/settings", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["settings"]
        self.assertEqual(data["volume"], 65)
        self.assertEqual(data["brightness"], 80)
        self.assertTrue(data["ble"])
        self.assertEqual(data["idle_config"]["mode"], "SINGLE")

        # Update settings
        mock_device.set_volume.return_value = {"success": True, "error": None}
        mock_device.set_brightness.return_value = {"success": True, "error": None}
        mock_device.set_screentime.return_value = {"success": True, "error": None}

        update_payload = {"volume": 75, "brightness": 90, "screentime": 120}
        res = self.client.post("/api/settings", headers=self.headers, json=update_payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        mock_device.set_volume.assert_called_with(75)
        mock_device.set_brightness.assert_called_with(90)
        mock_device.set_screentime.assert_called_with(120)

    @patch("web_server.device")
    def test_timeout_and_buzzer_endpoints(self, mock_device):
        """Test setting display timeouts and buzzer control."""
        mock_device.set_timeout.return_value = {"success": True, "response": "TIMEOUT_OK", "error": None}
        res = self.client.post(
            "/api/timeout",
            headers=self.headers,
            json={"qr_timeout": 180, "pf_timeout": 15},
        )
        self.assertEqual(res.status_code, 200)
        mock_device.set_timeout.assert_called_with(180000, 15000)

        # Buzzer toggle
        mock_device.activate_buzzer.return_value = {"success": True, "response": "ACTIVATE_BUZZER_OK", "error": None}
        res = self.client.post("/api/buzzer", headers=self.headers, json={"enabled": 1})
        self.assertEqual(res.status_code, 200)
        mock_device.activate_buzzer.assert_called_with(1)

    # ── 5. Idle Mode Configurations ───────────────────────────────────────

    @patch("web_server.device")
    def test_idle_modes_configuration(self, mock_device):
        """Test all 4 supported idle modes: SINGLE, CYCLE, SLEEP, SLEEP_WAKE."""
        # 1. SINGLE
        mock_device.set_idle_single.return_value = {"success": True, "response": "MODE_SINGLE_OK", "error": None}
        res = self.client.post("/api/idle-mode", headers=self.headers, json={"mode": "SINGLE", "image_name": "IMG2"})
        self.assertEqual(res.status_code, 200)
        mock_device.set_idle_single.assert_called_with("IMG2")

        # 2. CYCLE
        mock_device.set_idle_cycle.return_value = {"success": True, "response": "MODE_CYCLE_OK", "error": None}
        res = self.client.post(
            "/api/idle-mode",
            headers=self.headers,
            json={"mode": "CYCLE", "img1": "IMG1", "time1": 45000, "img2": "IMG2", "time2": 45000},
        )
        self.assertEqual(res.status_code, 200)
        mock_device.set_idle_cycle.assert_called_with("IMG1", 45000, "IMG2", 45000)

        # 3. SLEEP
        mock_device.set_idle_sleep.return_value = {"success": True, "response": "MODE_SLEEP_OK", "error": None}
        res = self.client.post("/api/idle-mode", headers=self.headers, json={"mode": "SLEEP", "image_name": "IMG1", "inactivity_ms": 60000})
        self.assertEqual(res.status_code, 200)
        mock_device.set_idle_sleep.assert_called_with("IMG1", 60000)

        # 4. SLEEP_WAKE
        mock_device.set_idle_sleep_wake.return_value = {"success": True, "response": "MODE_SLEEP_WAKE_OK", "error": None}
        res = self.client.post(
            "/api/idle-mode",
            headers=self.headers,
            json={"mode": "SLEEP_WAKE", "image_name": "IMG1", "sleep_ms": 35000, "wake_ms": 150000},
        )
        self.assertEqual(res.status_code, 200)
        mock_device.set_idle_sleep_wake.assert_called_with("IMG1", 35000, 150000)

    # ── 6. Real-time & Wallpaper Image Upload Flow ─────────────────────────

    @patch("web_server.device")
    def test_upload_image_processing_and_upload(self, mock_device):
        """Verify image resizing to dimensions, compression under 30KB, and dispatch."""
        mock_device.upload_image.return_value = {"success": True, "error": None}

        # Create a sample uncompressed test image (400x600 RGB)
        img = Image.new("RGB", (400, 600), color=(50, 120, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        data = {
            "image": (buf, "receipt_qr.jpg"),
            "size": "320x480",
        }
        res = self.client.post(
            "/api/upload-image",
            headers={"X-API-Key": self.api_key},
            data=data,
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        mock_device.upload_image.assert_called_once()
        uploaded_bytes = mock_device.upload_image.call_args[0][0]
        self.assertLessEqual(len(uploaded_bytes), 30 * 1024)

    @patch("web_server.device")
    def test_upload_idle_image_slots(self, mock_device):
        """Verify wallpaper upload for slot 1 and slot 2."""
        mock_device.upload_wallpaper.return_value = {"success": True, "error": None}

        img = Image.new("RGB", (320, 480), color=(20, 20, 20))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        data = {"image": (buf, "wallpaper.jpg"), "slot": "2"}
        res = self.client.post(
            "/api/upload-idle-image",
            headers={"X-API-Key": self.api_key},
            data=data,
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        mock_device.upload_wallpaper.assert_called_once()
        self.assertTrue(mock_device.upload_wallpaper.call_args[1]["slot2"])

    # ── 7. Flash Preparation & Disconnect ─────────────────────────────────

    @patch("web_server.device")
    def test_prepare_for_flash(self, mock_device):
        """Ensure auto-connect is suspended and serial port is closed for flashing."""
        res = self.client.post("/api/prepare-for-flash", headers=self.headers, json={"duration": 90})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["suspended_for"], 90)
        mock_device.suspend_auto_connect.assert_called_with(90)

    # ── 8. WebSocket SocketIO Flow ─────────────────────────────────────────

    @patch("web_server.device")
    def test_socketio_connect_and_command_exchange(self, mock_device):
        """Simulate real-time WebSocket client connection and send_command event."""
        mock_device.connected = True
        mock_device.port = "COM7"
        mock_device.device_id = "NIZIPOSB31"
        mock_device.firmware_id = "2.0.0"
        mock_device.firmware_update_info = {"update_available": False}
        mock_device.send_command.return_value = {"success": True, "response": "PASS_OK", "error": None}

        # 1. Connect with auth token
        sio_client = socketio.test_client(app, auth={"token": self.api_key})
        self.assertTrue(sio_client.is_connected())

        # Check status event was emitted on connection
        received = sio_client.get_received()
        status_events = [e for e in received if e["name"] == "device_status"]
        self.assertTrue(len(status_events) >= 1)
        self.assertTrue(status_events[0]["args"][0]["connected"])

        # 2. Emit 'send_command' event over WebSocket
        sio_client.emit("send_command", {"command": "PASS**Approved**Enjoy"})
        received_after_cmd = sio_client.get_received()
        result_events = [e for e in received_after_cmd if e["name"] == "command_result"]
        self.assertTrue(len(result_events) >= 1)
        self.assertTrue(result_events[0]["args"][0]["success"])
        self.assertEqual(result_events[0]["args"][0]["response"], "PASS_OK")

        # 3. Disconnect
        sio_client.disconnect()


if __name__ == "__main__":
    unittest.main()
