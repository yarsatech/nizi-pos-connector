"""
Nizi POS Connector — system tray icon and menu (connect / dashboard / quit).
"""

import logging
import webbrowser
import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject
from PIL import Image, ImageDraw
import io

from config import APP_NAME

logger = logging.getLogger(__name__)

WEB_PORT = 9121
ICON_SIZE = 64


def _create_qicon(connected: bool) -> QIcon:
    """Generate a simple colored icon: green if connected, gray if not, as a QIcon."""
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    bg_color = (16, 185, 129, 255) if connected else (100, 116, 139, 255)
    draw.ellipse([4, 4, ICON_SIZE - 4, ICON_SIZE - 4], fill=bg_color)

    # Inner "N" letter approximation using lines
    inner_color = (255, 255, 255, 255)
    m = 18  # margin
    # N shape: left bar, diagonal, right bar
    draw.line([(m, ICON_SIZE - m), (m, m)], fill=inner_color, width=4)
    draw.line([(m, m), (ICON_SIZE - m, ICON_SIZE - m)], fill=inner_color, width=4)
    draw.line([(ICON_SIZE - m, ICON_SIZE - m), (ICON_SIZE - m, m)], fill=inner_color, width=4)

    # Convert PIL Image to QIcon via bytes
    byte_array = io.BytesIO()
    img.save(byte_array, format="PNG")
    from PyQt6.QtGui import QPixmap
    pixmap = QPixmap()
    pixmap.loadFromData(byte_array.getvalue())
    return QIcon(pixmap)


class TrayApp(QObject):
    """System tray shell for the background connector service (PyQt6)."""

    def __init__(self, device_manager, ui_app=None, on_quit=None):
        super().__init__()
        self._device = device_manager
        self._ui_app = ui_app
        self._on_quit = on_quit
        self._connected = device_manager.connected

        # Initialize QSystemTrayIcon
        self._tray_icon = QSystemTrayIcon(self)
        self._update_icon()
        self._tray_icon.setContextMenu(self._build_menu())
        
        # Connect activation signal (e.g. double click)
        self._tray_icon.activated.connect(self._on_tray_activated)
        
        self._tray_icon.show()

        # Listen for device status changes
        original_callback = device_manager._on_status_change

        def _status_wrapper(connected, port):
            self._connected = connected
            self._update_icon()
            if original_callback:
                original_callback(connected, port)

        device_manager.set_status_callback(_status_wrapper)

    def _update_icon(self):
        """Update the tray icon image to reflect connection state."""
        icon_path = os.path.join("assets", "icon.ico")
        
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                if not self._connected:
                    # Convert to grayscale but preserve alpha channel
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                    # Split into R, G, B, A
                    r, g, b, a = img.split()
                    # Convert RGB part to grayscale
                    gray = img.convert("L")
                    # Merge back: use the same gray for R, G, B channels, keep original A
                    img = Image.merge("RGBA", (gray, gray, gray, a))
                
                # Convert PIL Image to QIcon via bytes
                byte_array = io.BytesIO()
                img.save(byte_array, format="PNG")
                from PyQt6.QtGui import QPixmap
                pixmap = QPixmap()
                pixmap.loadFromData(byte_array.getvalue())
                self._tray_icon.setIcon(QIcon(pixmap))
            except Exception as e:
                logger.error(f"Failed to process tray icon: {e}")
                self._tray_icon.setIcon(_create_qicon(self._connected))
        else:
            self._tray_icon.setIcon(_create_qicon(self._connected))
            
        tip = f"{APP_NAME} — Connected" if self._connected else f"{APP_NAME} — Disconnected"
        self._tray_icon.setToolTip(tip)

    def _on_tray_activated(self, reason):
        """Handle tray icon click."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._on_toggle_ui()

    def _on_connect(self):
        """Menu: Connect device (auto-detect)."""
        import threading
        def _do():
            result = self._device.connect()
            if result["success"]:
                logger.info(f"Tray: connected on {result['port']}")
            else:
                logger.warning(f"Tray: connect failed — {result['error']}")
        threading.Thread(target=_do, daemon=True).start()

    def _on_disconnect(self):
        """Menu: Disconnect device."""
        self._device.disconnect()

    def _on_toggle_ui(self):
        """Menu: Show the native popup UI."""
        if self._ui_app:
            self._ui_app.toggle()

    def _on_exit(self):
        """Menu: Quit the application."""
        logger.info("Tray: quit requested")
        self._tray_icon.hide()
        if self._on_quit:
            self._on_quit()

    def _build_menu(self):
        menu = QMenu()
        
        show_action = QAction("Show Menu", self)
        show_action.triggered.connect(self._on_toggle_ui)
        show_action.setCheckable(False)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        connect_action = QAction("Connect Device", self)
        connect_action.triggered.connect(self._on_connect)
        menu.addAction(connect_action)
        
        disconnect_action = QAction("Disconnect", self)
        disconnect_action.triggered.connect(self._on_disconnect)
        menu.addAction(disconnect_action)
        
        menu.addSeparator()
        
        quit_action = QAction(f"Quit {APP_NAME}", self)
        quit_action.triggered.connect(self._on_exit)
        menu.addAction(quit_action)
        
        return menu

    def stop(self):
        """Stop the tray icon programmatically."""
        self._tray_icon.hide()
