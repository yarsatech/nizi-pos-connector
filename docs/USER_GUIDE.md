# Nizi POS Connector User Guide

Nizi POS Connector is a background service that allows web applications and local systems to communicate with the UART display device.

## Getting Started

### 1. Launching the App
On Windows, run **`NiziPOSConnector.exe`** (from the installer or the PyInstaller `dist/NiziPOSConnector` folder). The app uses a fixed secret token for secure API access.

### 2. System Tray
Look for the Nizi POS Connector icon in your system tray:
- **Green Icon**: Device is connected.
- **Gray Icon**: Device is disconnected.

**Right-click the icon to:**
- **Show Menu**: Open the floating dashboard.
- **Connect Device**: Trigger auto-detection of the UART device.
- **Disconnect**: Safely disconnect the current device.
- **Quit Nizi POS Connector**: Shut down the service.

---

## Using the Dashboard

The dashboard provides a quick way to interact with your device.

### Connection
You can enter a specific COM port (e.g., `COM3` on Windows or `/dev/ttyUSB0` on Linux) or leave it blank to let Nizi POS Connector auto-detect the hardware.

### Display Controls
- **Status Screens**: Send pre-formatted Success, Waiting, or Error screens to the hardware.
- **QR Codes**: Display payment or information QR codes by pasting the payload.
- **Text Display**: Show custom titles, subtitles, and messages.
- **Image Upload**: Drag and drop a JPEG image to display it on the device. Nizi POS Connector handles resizing and compression automatically.

### System Actions
- **IDLE/WAKE**: Put the display into low-power mode or wake it up.
- **RESET**: Reboot the device.
- **FORMAT**: Clear internal flash storage (use with caution).

---

## Remote Access & Integration

Nizi POS Connector runs a local web server on `http://127.0.0.1:9121`.

- **Web Dashboard**: Open your browser to `http://localhost:9121` to access the full control panel.
- **API**: Third-party POS systems can send commands using the REST API. See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md).

---

## Security
- Nizi POS Connector is bound to **localhost only**. It cannot be accessed by other computers on your network.
- Every API request requires the valid **fixed API Key** provided to you.
