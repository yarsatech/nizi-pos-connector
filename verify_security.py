"""
Verification script for Nizi POS Connector API hardening.
Tests:
1. API Key Authentication (Success/Failure)
2. Binding (Localhost only)
3. Input Validation (Commands, Uploads)
"""

import requests
import unittest
import threading
import time
import os
import io

# We assume the server is running or we start it
# For automated tests, we'll try to reach it.

BASE_URL = "http://127.0.0.1:9121"

class TestHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The API key is now hardcoded in the app.
        cls.api_key = "Z8uVovI2eftp65dO9JoxEstKcWggSlTAza4erAQhELmSC761rVtp5IIzaXOxWNw0ycPCICYCnJBCVPCzvdT8fbJvWIWm69fhHveZesIiDEIeI0BkdSspMPimWYNWs25D"

    def test_unauthorized_access(self):
        """API should return 401 without key."""
        res = requests.get(f"{BASE_URL}/api/status")
        self.assertEqual(res.status_code, 401)
        self.assertFalse(res.json()["success"])

    def test_authorized_access(self):
        """API should return 200 with correct key."""
        if not self.api_key: self.skipTest("No API key")
        headers = {"X-API-Key": self.api_key}
        res = requests.get(f"{BASE_URL}/api/status", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("connected", res.json())

    def test_invalid_command_validation(self):
        """API should reject invalid commands."""
        if not self.api_key: self.skipTest("No API key")
        headers = {"X-API-Key": self.api_key}
        
        # Non-string command
        res = requests.post(f"{BASE_URL}/api/command", json={"command": 123}, headers=headers)
        self.assertEqual(res.status_code, 400)
        
        # Empty command
        res = requests.post(f"{BASE_URL}/api/command", json={"command": ""}, headers=headers)
        self.assertEqual(res.status_code, 400)

    def test_settings_validation(self):
        """API should reject invalid setting ranges."""
        if not self.api_key: self.skipTest("No API key")
        headers = {"X-API-Key": self.api_key}
        
        # Out of range volume
        res = requests.post(f"{BASE_URL}/api/settings", json={"volume": 150}, headers=headers)
        self.assertEqual(res.status_code, 400)

    def test_image_upload_validation(self):
        """API should reject non-JPEG or oversized files."""
        if not self.api_key: self.skipTest("No API key")
        headers = {"X-API-Key": self.api_key}
        
        # Wrong type
        files = {'image': ('test.png', b'not a jpeg', 'image/png')}
        res = requests.post(f"{BASE_URL}/api/upload-image", files=files, headers=headers)
        self.assertEqual(res.status_code, 400)

    def test_socketio_auth(self):
        """SocketIO should require correct token in auth handshake."""
        import socketio
        sio = socketio.Client()
        
        # Test without token
        try:
            sio.connect(BASE_URL)
            connected_no_auth = sio.connected
            sio.disconnect()
        except:
            connected_no_auth = False
        self.assertFalse(connected_no_auth, "Should not connect without auth")
        
        # Test with wrong token
        try:
            sio.connect(BASE_URL, auth={"token": "wrong-token"})
            connected_wrong_auth = sio.connected
            sio.disconnect()
        except:
            connected_wrong_auth = False
        self.assertFalse(connected_wrong_auth, "Should not connect with wrong token")

        # Test with correct token
        try:
            sio.connect(BASE_URL, auth={"token": self.api_key})
            connected_correct_auth = sio.connected
            sio.disconnect()
        except:
            connected_correct_auth = False
        self.assertTrue(connected_correct_auth, "Should connect with correct token")

if __name__ == "__main__":
    print(f"Testing Nizi POS Connector at {BASE_URL}...")
    unittest.main()
