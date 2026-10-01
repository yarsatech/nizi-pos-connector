# Nizi POS Connector User Guide

Nizi POS Connector is a cross-platform background service that allows web applications and local systems to communicate with the UART display device.

## Getting Started

### 1. Launching the App
- **Windows**: Run **`NiziPOSConnector.exe`** (from the installer or the PyInstaller `dist/NiziPOSConnector` directory).
- **macOS**: Launch **`NiziPOSConnector.app`** (runs as a lightweight menu bar accessory).
- **Linux**: Execute **`./NiziPOSConnector`** from your terminal or desktop launcher.

The app uses a fixed secret token for secure API access.

### 2. System Tray / Menu Bar
Look for the Nizi POS Connector icon in your system tray or macOS menu bar:
- **Green Icon**: Device is connected and ready.
- **Gray Icon**: Device is disconnected.

**Right-click (or click) the icon to:**
- **Show Menu / Dashboard**: Open the floating settings flyout.
- **Connect Device**: Trigger auto-detection of the UART device.
- **Disconnect**: Safely disconnect the current device.
- **Quit Nizi POS Connector**: Shut down the service.

---

## Using the Dashboard

The dashboard provides a quick, interactive way to control and configure your device.

### Connection
You can enter a specific serial port (e.g., `COM3` on Windows, `/dev/ttyUSB0` on Linux, or `/dev/cu.usbserial-*` on macOS) or leave it on Auto to let Nizi POS Connector detect the hardware.

### Display Controls
- **Status Screens**: Send pre-formatted Success, Waiting, or Error screens to the hardware.
- **QR Codes**: Display payment or information QR codes by pasting the payload.
- **Text Display**: Show custom titles, subtitles, and messages.
- **Image Upload**: Drag and drop a JPEG image to display it on the device. Nizi POS Connector handles resizing and compression automatically.

### System Actions & Settings
- **Volume & Brightness**: Sliders to adjust hardware speaker volume and LCD backlight brightness.
- **Idle Modes**: Configure Single Image, Dual Image Cycle, Sleep, or Scheduled Sleep/Wake.
- **IDLE/WAKE**: Put the display into low-power mode or wake it up.
- **RESET**: Soft-reboot the device.
- **FORMAT**: Clear internal flash storage (use with caution).

### Bluetooth & BLE PIN Security
- **Toggle BLE**: Turn Bluetooth on or off directly from the dashboard.
- **Default PIN Warning**: If BLE is enabled while the device is still using its factory default PIN, the connector presents a security warning recommending a PIN update.
- **Change PIN**: Enter your current PIN and set a new one using the built-in dialog (with password visibility toggles). The device reboots on success.
- **Reset PIN**: Reset the PIN back to the default MAC-derived PIN with a single confirmation.

---

## Automatic Updates (OTA)

Nizi POS Connector includes built-in Over-The-Air (OTA) updater support:
- **Update Checks**: Automatically checks GitHub releases for newer app versions and firmware updates.
- **Multi-Platform Support**: Seamlessly downloads and applies updates across Windows, macOS, and Linux with native relaunching.

---

## Remote Access & Integration

Nizi POS Connector runs a local web server on `http://127.0.0.1:9121`.

- **Web Dashboard**: Open your browser to `http://localhost:9121` to access the full control panel.
- **API**: Third-party POS systems can send commands using the REST API. See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md).

---

## Security
- Nizi POS Connector is bound to **localhost only**. It cannot be accessed by external computers on your local network.
- Every API request requires the valid **fixed API Key** provided to you in the `X-API-Key` header.
