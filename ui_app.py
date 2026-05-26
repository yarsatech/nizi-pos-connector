"""
Nizi POS Connector — floating PyQt6 control panel.
"""

import sys
import os
import io
import threading
import logging
from PIL import Image
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QFileDialog,
    QFrame, QApplication, QStackedWidget, QSizePolicy,
    QRadioButton, QButtonGroup, QDialog, QMessageBox,
    QSlider, QListView
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtGui import QFont, QGuiApplication, QIcon, QDesktopServices, QPixmap

from config import APP_NAME
from theme_support import flyout_dark_stylesheet, prefers_light_theme
from ota.firmware_api import get_languages, build_update_url, extract_model_code

logger = logging.getLogger(__name__)

# Note: we intentionally do not show app version inside the UI.

# ── Modern Stylesheet ────────────────────────────────────────────────────

STYLESHEET = """
* {
    font-family: 'Segoe UI', 'Arial', sans-serif;
}

QWidget#mainWindow {
    background-color: #ffffff;
}

QLabel#headerTitle {
    font-size: 16pt;
    font-weight: 700;
    color: #111827;
}

QLabel#statusLabel {
    font-size: 11pt;
    font-weight: 600;
    background: transparent;
    border: none;
}

QLabel#instructionLabel {
    font-size: 9pt;
    color: #6b7280;
    background: transparent;
    border: none;
}

QLabel#sectionTitle {
    font-size: 10pt;
    font-weight: 600;
    color: #111827;
    background: transparent;
}

QLabel#fieldLabel {
    font-size: 8pt;
    color: #6b7280;
    font-weight: 500;
    margin-top: 12px;
    margin-bottom: 0px;
    background: transparent;
}

QLabel#modeLabel {
    font-size: 9pt;
    color: #374151;
    font-weight: 600;
    margin-top: 0px;
    background: transparent;
}

QFrame#statusCard {
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
}

QFrame#separator {
    background-color: #e5e7eb;
    max-height: 1px;
    border: none;
}

QLabel#imagePreview {
    border: 2px dashed #cbd5e1;
    border-radius: 8px;
    background-color: #f8fafc;
    color: #94a3b8;
    font-weight: 500;
}

QTextEdit#logDisplay {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    font-family: monospace;
}

/* ── Dropdown (QComboBox) ─────────────────────────────── */

QComboBox {
    font-size: 10pt;
    padding: 6px 12px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background-color: #ffffff;
    color: #111827;
    min-height: 20px;
}
QComboBox:hover {
    border-color: #fca5a5;
}
QComboBox:focus {
    border-color: #ef4444;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 30px;
    border: none;
    background: transparent;
}
QComboBox::down-arrow {
    image: url({ARROW_PATH});
    width: 14px;
    height: 14px;
}
QComboBox QAbstractItemView {
    font-size: 10pt;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background-color: #ffffff;
    selection-background-color: #f3f4f6;
    selection-color: #ef4444;
    outline: 0;
    padding: 6px;
}
QComboBox QAbstractItemView::item {
    padding: 10px 16px;
    margin: 2px 0px;
    border-radius: 8px;
    color: #374151;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #f3f4f6;
    color: #ef4444;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #fef2f2;
    color: #ef4444;
    font-weight: 600;
}

/* ── Inputs ───────────────────────────────────────────── */

QLineEdit {
    font-size: 10pt;
    padding: 6px 12px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background-color: #ffffff;
    color: #111827;
}
QLineEdit:focus {
    border-color: #ef4444;
    background-color: #fefefe;
}
QLineEdit::placeholder {
    color: #9ca3af;
}

QLineEdit::selection {
    background-color: #ef4444;
    color: #ffffff;
}

QTextEdit {
    font-size: 10pt;
    padding: 6px 12px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background-color: #ffffff;
    color: #111827;
}
QTextEdit:focus {
    border-color: #ef4444;
}

QTextEdit::selection {
    background-color: #ef4444;
    color: #ffffff;
}

/* ── Buttons ──────────────────────────────────────────── */

QPushButton#primaryBtn {
    font-size: 10pt;
    padding: 8px 16px;
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #dc2626;
}
QPushButton#primaryBtn:pressed {
    background-color: #b91c1c;
}
QPushButton#primaryBtn:disabled {
    background-color: #7f1d1d;
    color: #fee2e2;
}

QPushButton#secondaryBtn {
    font-size: 10pt;
    padding: 8px 16px;
    background-color: #ffffff;
    color: #374151;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-weight: 500;
}
QPushButton#secondaryBtn:hover {
    background-color: #f3f4f6;
    border-color: #fca5a5;
}

QPushButton#dangerBtn {
    font-size: 10pt;
    padding: 8px 16px;
    background-color: #fef2f2;
    color: #dc2626;
    border: 1px solid #fecaca;
    border-radius: 8px;
    font-weight: 500;
}
QPushButton#dangerBtn:hover {
    background-color: #fee2e2;
    border-color: #f87171;
}

QPushButton#warningBtn {
    font-size: 10pt;
    padding: 8px 16px;
    background-color: #fffbeb;
    color: #d97706;
    border: 1px solid #fde68a;
    border-radius: 8px;
    font-weight: 500;
}
QPushButton#warningBtn:hover {
    background-color: #fef3c7;
    border-color: #f59e0b;
}

QPushButton#ghostBtn {
    font-size: 9pt;
    padding: 8px 12px;
    background: transparent;
    color: #9ca3af;
    border: none;
}
QPushButton#ghostBtn:hover {
    color: #ef4444;
}

QPushButton#connectBtn {
    font-size: 10pt;
    padding: 10px 20px;
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton#connectBtn:hover {
    background-color: #dc2626;
}
QPushButton#connectBtn:disabled {
    background-color: #7f1d1d;
    color: #fee2e2;
}

QPushButton#disconnectBtn {
    font-size: 10pt;
    padding: 10px 20px;
    background-color: #ffffff;
    color: #6b7280;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    font-weight: 500;
}
QPushButton#disconnectBtn:hover {
    border-color: #fca5a5;
    color: #374151;
}

/* ── Radio Buttons ────────────────────────────────────── */

QRadioButton {
    font-size: 10pt;
    color: #374151;
    spacing: 8px;
    padding: 4px;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #d1d5db;
    border-radius: 11px;
    background: #ffffff;
}
QRadioButton::indicator:hover {
    border-color: #fca5a5;
}
QRadioButton::indicator:checked {
    border-color: #ef4444;
    background-color: #ef4444;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjUiLz48L3N2Zz4=);
}
QRadioButton:disabled {
    color: #9ca3af;
}
QRadioButton::indicator:disabled {
    border-color: #e5e7eb;
    background-color: #f9fafb;
}

/* ── Sliders ──────────────────────────────────────────── */

QSlider::groove:horizontal {
    border-radius: 4px;
    height: 8px;
    background: #e5e7eb;
}
QSlider::sub-page:horizontal {
    background: #ef4444;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #d1d5db;
    width: 18px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 9px;
}
QSlider::handle:horizontal:hover {
    background: #f9fafb;
    border-color: #fca5a5;
}
QSlider::handle:horizontal:pressed {
    background: #fef2f2;
    border-color: #ef4444;
}

QDialog {
    background-color: #ffffff;
}
"""






class TrayFlyout(QWidget):
    status_updated = pyqtSignal(bool, str)
    upload_status_updated = pyqtSignal(str, str, bool)
    wallpaper_upload_status_updated = pyqtSignal(str, str, bool)
    toggle_visibility = pyqtSignal()
    languages_loaded = pyqtSignal(list)

    def __init__(self, device_manager, web_port=9121, on_quit=None):
        super().__init__()
        self.device = device_manager
        self.web_port = web_port
        self.on_quit_callback = on_quit

        self.setWindowTitle(APP_NAME)
        self.setObjectName("mainWindow")
        self.setMinimumWidth(400)
        self.setMaximumWidth(460)
        
        # Constrain max height to 80% of screen to avoid overflow
        screen_height = QGuiApplication.primaryScreen().availableGeometry().height()
        self.setMaximumHeight(int(screen_height * 0.8))

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        # Ensure minimize/maximize are disabled across platforms.
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        # Resolve arrow icon path and inject into stylesheet
        _base = Path(__file__).resolve().parent
        _arrow = (_base / "assets" / "dropdown_arrow.svg").as_posix()
        app = QApplication.instance()
        palette_lightness = None
        if app is not None:
            palette_lightness = app.palette().window().color().lightness()
        self._light_theme = prefers_light_theme(palette_lightness=palette_lightness)
        stylesheet = STYLESHEET.replace("{ARROW_PATH}", _arrow)
        if not self._light_theme:
            stylesheet += "\n" + flyout_dark_stylesheet()
        self.setStyleSheet(stylesheet)

        self.status_updated.connect(self._on_status_updated)
        self.upload_status_updated.connect(self._on_upload_status)
        self.wallpaper_upload_status_updated.connect(self._on_wallpaper_upload_status)
        self.toggle_visibility.connect(self._toggle_internal)
        self.languages_loaded.connect(self._on_languages_loaded)

        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self._build_ui()
        self._is_visible = False

        original_callback = self.device._on_status_change

        def _on_status_wrapper(connected, port):
            self.status_updated.emit(connected, port or "")
            if original_callback:
                original_callback(connected, port)

        self.device.set_status_callback(_on_status_wrapper)
        self._on_status_updated(self.device.connected, self.device.port or "")

        threading.Thread(target=self._fetch_languages, daemon=True).start()

    # ── UI Construction ──────────────────────────────────────────────────

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget#scrollContent { background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        self.scroll_content = scroll_content
        
        root = QVBoxLayout(scroll_content)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Header
        title = QLabel("NIZI POS")
        title.setObjectName("headerTitle")
        root.addWidget(title)

        # Status card
        card = QFrame()
        card.setObjectName("statusCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        # Mode Selection (Radio Group)
        self.mode_container = QHBoxLayout()
        self.mode_container.setSpacing(20)
        
        mode_lbl = QLabel("Auto-Connect:")
        mode_lbl.setObjectName("modeLabel")
        self.mode_container.addWidget(mode_lbl)

        self.radio_auto = QRadioButton("Auto")
        self.radio_manual = QRadioButton("Manual")
        self.radio_auto.setChecked(True)
        
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_auto)
        self.mode_group.addButton(self.radio_manual)
        self.mode_group.buttonClicked.connect(self._on_mode_changed)

        self.mode_container.addWidget(self.radio_auto)
        self.mode_container.addWidget(self.radio_manual)
        self.mode_container.addStretch()
        
        card_layout.addLayout(self.mode_container)

        self.status_label = QLabel("Disconnected")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)

        self.instruction_label = QLabel("Plug in device to get started.")
        self.instruction_label.setObjectName("instructionLabel")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.instruction_label)

        self.firmware_label = QLabel("")
        self.firmware_label.setObjectName("instructionLabel")
        self.firmware_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.firmware_label.setVisible(False)
        card_layout.addWidget(self.firmware_label)

        self.update_available_label = QLabel("⚠ Firmware update available")
        self.update_available_label.setObjectName("instructionLabel")
        self.update_available_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_available_label.setStyleSheet("color: #d97706; font-weight: 600;")
        self.update_available_label.setVisible(False)
        card_layout.addWidget(self.update_available_label)

        self.btn_update_firmware = QPushButton("🔄  Open Update Page")
        self.btn_update_firmware.setObjectName("warningBtn")
        self.btn_update_firmware.clicked.connect(self._open_firmware_update_page)
        self.btn_update_firmware.setVisible(False)
        card_layout.addWidget(self.btn_update_firmware)

        self.btn_action = QPushButton("Connect Now")
        self.btn_action.setObjectName("connectBtn")
        self.btn_action.clicked.connect(self._manual_connect)
        card_layout.addWidget(self.btn_action)

        # Port selection area (only visible when disconnected)
        self.port_selection_container = QWidget()
        port_layout = QVBoxLayout(self.port_selection_container)
        port_layout.setContentsMargins(0, 8, 0, 0)
        port_layout.setSpacing(8)

        port_header = QHBoxLayout()
        port_header.addWidget(self._make_field_label("Select Port Manually"))
        port_header.addStretch()
        
        self.btn_rescan = QPushButton("Rescan")
        self.btn_rescan.setObjectName("ghostBtn")
        self.btn_rescan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rescan.clicked.connect(self._rescan_ports)
        port_header.addWidget(self.btn_rescan)
        port_layout.addLayout(port_header)

        self.port_dropdown = QComboBox()
        self.port_dropdown.setView(QListView())
        self.port_dropdown.setPlaceholderText("Select a port...")
        port_layout.addWidget(self.port_dropdown)
        
        card_layout.addWidget(self.port_selection_container)

        root.addWidget(card)

        # ── Commands area (hidden when disconnected) ─────────────────────
        self.commands_container = QWidget()
        commands_layout = QVBoxLayout(self.commands_container)
        commands_layout.setContentsMargins(0, 0, 0, 0)
        commands_layout.setSpacing(12)

        # Separator
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        commands_layout.addWidget(sep)

        # Section title + dropdown row
        section_row = QHBoxLayout()
        section_lbl = QLabel("Send Command")
        section_lbl.setObjectName("sectionTitle")
        section_row.addWidget(section_lbl)
        section_row.addStretch()

        self.page_selector = QComboBox()
        self.page_selector.setView(QListView())
        self.page_selector.addItems([
            "Quick Actions",
            "Device Config",
            "Upload Images",
            "Status Screen",
            "QR Display",
            "Text Display",
            "Idle Mode",
        ])
        self.page_selector.setMinimumWidth(128)
        self.page_selector.setMaxVisibleItems(4)
        self.page_selector.currentIndexChanged.connect(self._switch_page)
        section_row.addWidget(self.page_selector)
        commands_layout.addLayout(section_row)

        # Stacked pages — order must match addItems above
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        commands_layout.addWidget(self.stack)

        self._build_page_quick()          # index 0 — Quick Actions
        self._build_page_device_config()  # index 1 — Device Config
        self._build_page_upload_images()  # index 2 — Upload Images
        self._build_page_status()         # index 3 — Status Screen
        self._build_page_qr()             # index 4 — QR Display
        self._build_page_text()           # index 5 — Text Display
        self._build_page_idle_mode()      # index 6 — Idle Mode

        self.page_selector.setCurrentIndex(0)  # default: Quick Actions
        root.addWidget(self.commands_container)

        # Footer
        root.addStretch()
        
        footer_layout = QHBoxLayout()
        
        footer_layout.addStretch()
        
        self.btn_quit = QPushButton("Quit")
        self.btn_quit.setObjectName("ghostBtn")
        self.btn_quit.clicked.connect(self._quit_app)
        footer_layout.addWidget(self.btn_quit)
        
        root.addLayout(footer_layout)

    # ── Page Builders ────────────────────────────────────────────────────

    def _make_field_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    def _build_page_status(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(self._make_field_label("Type"))
        self.status_type = QComboBox()
        self.status_type.setView(QListView())
        self.status_type.addItems([
            "INFO — Information",
            "PASS — Payment Successful",
            "WAIT — Please Wait",
            "FAIL — Payment Failed",
            "WARN — Warning",
        ])
        self.status_type.currentTextChanged.connect(self._on_status_type_change)
        layout.addWidget(self.status_type)

        layout.addWidget(self._make_field_label("Title / Amount"))
        # Default to INFO so the initial dropdown selection matches fields.
        self.status_field1 = QLineEdit("Important")
        layout.addWidget(self.status_field1)

        layout.addWidget(self._make_field_label("Message"))
        self.status_field2 = QLineEdit("Keep device connected")
        layout.addWidget(self.status_field2)

        # Ensure fields match the dropdown initial selection (especially after reordering).
        self._on_status_type_change(self.status_type.currentText())

        layout.addSpacing(12)
        self.btn_send_status = QPushButton("Send")
        self.btn_send_status.setObjectName("primaryBtn")
        self.btn_send_status.clicked.connect(self._send_status)
        layout.addWidget(self.btn_send_status)

        self.stack.addWidget(page)

    def _build_page_qr(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(self._make_field_label("Amount"))
        self.qr_amount = QLineEdit("Rs. 123.45")
        layout.addWidget(self.qr_amount)

        layout.addWidget(self._make_field_label("Scan Text"))
        self.qr_scan_text = QLineEdit("SCAN TO PAY")
        layout.addWidget(self.qr_scan_text)

        layout.addWidget(self._make_field_label("QR Payload"))
        self.qr_payload = QTextEdit()
        self.qr_payload.setPlaceholderText("Paste QR payload data here...")
        self.qr_payload.setMaximumHeight(70)
        layout.addWidget(self.qr_payload)

        layout.addSpacing(12)
        self.btn_send_qr = QPushButton("Send")
        self.btn_send_qr.setObjectName("primaryBtn")
        self.btn_send_qr.clicked.connect(self._send_qr)
        layout.addWidget(self.btn_send_qr)

        self.stack.addWidget(page)

    def _build_page_text(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(self._make_field_label("Title"))
        self.text_title = QLineEdit("Main Title")
        layout.addWidget(self.text_title)

        layout.addWidget(self._make_field_label("Subtitle"))
        self.text_subtitle = QLineEdit("Subtitle")
        layout.addWidget(self.text_subtitle)

        layout.addWidget(self._make_field_label("Message"))
        self.text_msg = QTextEdit()
        self.text_msg.setPlainText("Message body")
        self.text_msg.setMaximumHeight(70)
        layout.addWidget(self.text_msg)

        layout.addSpacing(12)
        self.btn_send_text = QPushButton("Send")
        self.btn_send_text.setObjectName("primaryBtn")
        self.btn_send_text.clicked.connect(self._send_text)
        layout.addWidget(self.btn_send_text)

        self.stack.addWidget(page)

    def _build_page_upload_images(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── SECTION 1: Wallpaper Image (Saves on Device) ──────────────────
        wall_card = QFrame()
        wall_card.setObjectName("statusCard")
        wall_card_layout = QVBoxLayout(wall_card)
        wall_card_layout.setContentsMargins(12, 12, 12, 12)
        wall_card_layout.setSpacing(6)

        wall_title = QLabel("Wallpaper Image (Saves on Device)")
        wall_title.setStyleSheet("font-weight: 700; color: #ef4444; font-size: 10pt;")
        wall_card_layout.addWidget(wall_title)

        self.wallpaper_file_path = None

        wall_card_layout.addWidget(self._make_field_label("Wallpaper Slot"))
        self.wallpaper_slot = QComboBox()
        self.wallpaper_slot.setView(QListView())
        self.wallpaper_slot.addItems(["IMG1 — Primary", "IMG2 — Secondary (for Cycle mode)"])
        wall_card_layout.addWidget(self.wallpaper_slot)

        self.btn_select_wallpaper = QPushButton("Browse Wallpaper…")
        self.btn_select_wallpaper.setObjectName("secondaryBtn")
        self.btn_select_wallpaper.clicked.connect(self._select_wallpaper)
        wall_card_layout.addWidget(self.btn_select_wallpaper)

        # Wallpaper Preview
        self.wallpaper_preview = QLabel("No Wallpaper Selected")
        self.wallpaper_preview.setObjectName("imagePreview")
        self.wallpaper_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wallpaper_preview.setFixedSize(160, 120)
        
        preview_container_wall = QWidget()
        preview_layout_wall = QHBoxLayout(preview_container_wall)
        preview_layout_wall.setContentsMargins(0, 2, 0, 2)
        preview_layout_wall.addWidget(self.wallpaper_preview, 0, Qt.AlignmentFlag.AlignCenter)
        wall_card_layout.addWidget(preview_container_wall)

        self.wallpaper_label = QLabel("No wallpaper selected")
        self.wallpaper_label.setObjectName("instructionLabel")
        self.wallpaper_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wall_card_layout.addWidget(self.wallpaper_label)

        wall_card_layout.addWidget(self._make_field_label("Screen Size"))
        self.wallpaper_size = QComboBox()
        self.wallpaper_size.setView(QListView())
        self.wallpaper_size.addItems(["B30/B31 — 2.8 inch (240×320)", "B32/B33 — 3.5 inch (320×480)"])
        wall_card_layout.addWidget(self.wallpaper_size)

        self.btn_upload_wallpaper = QPushButton("Save Wallpaper to Device")
        self.btn_upload_wallpaper.setObjectName("primaryBtn")
        self.btn_upload_wallpaper.clicked.connect(self._upload_wallpaper)
        self.btn_upload_wallpaper.setEnabled(False)
        wall_card_layout.addWidget(self.btn_upload_wallpaper)

        layout.addWidget(wall_card)

        # ── SECTION 2: Temporary Image (Real-time Preview) ────────────────
        temp_card = QFrame()
        temp_card.setObjectName("statusCard")
        temp_card_layout = QVBoxLayout(temp_card)
        temp_card_layout.setContentsMargins(12, 12, 12, 12)
        temp_card_layout.setSpacing(6)

        temp_title = QLabel("Temporary Image (Real-time Preview)")
        temp_title.setStyleSheet("font-weight: 700; color: #ef4444; font-size: 10pt;")
        temp_card_layout.addWidget(temp_title)

        self.preview_file_path = None

        self.btn_select_preview = QPushButton("Browse Preview Image…")
        self.btn_select_preview.setObjectName("secondaryBtn")
        self.btn_select_preview.clicked.connect(self._select_preview_image)
        temp_card_layout.addWidget(self.btn_select_preview)

        # Preview Image Preview
        self.preview_image_preview = QLabel("No Preview Selected")
        self.preview_image_preview.setObjectName("imagePreview")
        self.preview_image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_preview.setFixedSize(160, 120)
        
        preview_container_temp = QWidget()
        preview_layout_temp = QHBoxLayout(preview_container_temp)
        preview_layout_temp.setContentsMargins(0, 2, 0, 2)
        preview_layout_temp.addWidget(self.preview_image_preview, 0, Qt.AlignmentFlag.AlignCenter)
        temp_card_layout.addWidget(preview_container_temp)

        self.preview_label = QLabel("No preview image selected")
        self.preview_label.setObjectName("instructionLabel")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        temp_card_layout.addWidget(self.preview_label)

        temp_card_layout.addWidget(self._make_field_label("Screen Size"))
        self.preview_size = QComboBox()
        self.preview_size.setView(QListView())
        self.preview_size.addItems(["B30/B31 — 2.8 inch (240×320)", "B32/B33 — 3.5 inch (320×480)"])
        temp_card_layout.addWidget(self.preview_size)

        self.btn_upload_preview = QPushButton("Show Preview on Device")
        self.btn_upload_preview.setObjectName("primaryBtn")
        self.btn_upload_preview.clicked.connect(self._upload_preview_image)
        self.btn_upload_preview.setEnabled(False)
        temp_card_layout.addWidget(self.btn_upload_preview)

        layout.addWidget(temp_card)

        self.stack.addWidget(page)

    def _build_page_idle_mode(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(self._make_field_label("Idle Mode"))
        self.idle_mode_dropdown = QComboBox()
        self.idle_mode_dropdown.setView(QListView())
        self.idle_mode_dropdown.addItems([
            "SLEEP_WAKE — Sleep/Wake Cycle (Default)",
            "SINGLE — Static Image",
            "CYCLE — Alternate Two Images",
            "SLEEP — Sleep After Inactivity",
        ])
        self.idle_mode_dropdown.currentIndexChanged.connect(self._on_idle_mode_change)
        layout.addWidget(self.idle_mode_dropdown)

        # Dynamic fields container
        self.idle_fields_container = QWidget()
        self.idle_fields_layout = QVBoxLayout(self.idle_fields_container)
        self.idle_fields_layout.setContentsMargins(0, 4, 0, 0)
        self.idle_fields_layout.setSpacing(8)

        self.idle_img1_label = self._make_field_label("Image Name")
        self.idle_img1 = QComboBox()
        self.idle_img1.setView(QListView())
        self.idle_img1.addItems(["IMG1", "IMG2"])
        self.idle_fields_layout.addWidget(self.idle_img1_label)
        self.idle_fields_layout.addWidget(self.idle_img1)

        self.idle_sleep_ms_label = self._make_field_label("Sleep Duration (ms)")
        self.idle_sleep_ms = QLineEdit("30000")
        self.idle_fields_layout.addWidget(self.idle_sleep_ms_label)
        self.idle_fields_layout.addWidget(self.idle_sleep_ms)

        self.idle_screentime_label = self._make_field_label("Inactivity Timeout (s)")
        self.idle_screentime = QLineEdit("30")
        self.idle_fields_layout.addWidget(self.idle_screentime_label)
        self.idle_fields_layout.addWidget(self.idle_screentime)

        self.idle_wake_ms_label = self._make_field_label("Wake Duration (ms)")
        self.idle_wake_ms = QLineEdit("120000")
        self.idle_fields_layout.addWidget(self.idle_wake_ms_label)
        self.idle_fields_layout.addWidget(self.idle_wake_ms)

        self.idle_img2_label = self._make_field_label("Image 2 Name")
        self.idle_img2 = QComboBox()
        self.idle_img2.setView(QListView())
        self.idle_img2.addItems(["IMG1", "IMG2"])
        self.idle_img2.setCurrentIndex(1)  # Default to IMG2
        self.idle_fields_layout.addWidget(self.idle_img2_label)
        self.idle_fields_layout.addWidget(self.idle_img2)

        self.idle_time1_label = self._make_field_label("Image 1 Duration (ms)")
        self.idle_time1 = QLineEdit("60000")
        self.idle_fields_layout.addWidget(self.idle_time1_label)
        self.idle_fields_layout.addWidget(self.idle_time1)

        self.idle_time2_label = self._make_field_label("Image 2 Duration (ms)")
        self.idle_time2 = QLineEdit("60000")
        self.idle_fields_layout.addWidget(self.idle_time2_label)
        self.idle_fields_layout.addWidget(self.idle_time2)

        layout.addWidget(self.idle_fields_container)

        layout.addSpacing(12)
        self.btn_set_idle = QPushButton("Set Idle Mode")
        self.btn_set_idle.setObjectName("primaryBtn")
        self.btn_set_idle.clicked.connect(self._send_idle_mode)
        layout.addWidget(self.btn_set_idle)

        self.idle_mode_feedback = QLabel("")
        self.idle_mode_feedback.setObjectName("instructionLabel")
        self.idle_mode_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.idle_mode_feedback.setVisible(False)
        layout.addWidget(self.idle_mode_feedback)

        # Initialize field visibility
        self._on_idle_mode_change(0)

        self.stack.addWidget(page)



    def _build_page_device_config(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── Volume ──────────────────────────────────────────────────────
        vol_header = QHBoxLayout()
        vol_header.addWidget(self._make_field_label("Volume"))
        vol_header.addStretch()
        self.volume_val_label = QLabel("80%")
        self.volume_val_label.setStyleSheet("color: #374151; font-weight: 600; font-size: 9pt;")
        vol_header.addWidget(self.volume_val_label)
        layout.addLayout(vol_header)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(lambda v: self.volume_val_label.setText(f"{v}%"))
        self.volume_slider.sliderReleased.connect(self._send_volume)
        layout.addWidget(self.volume_slider)

        self.volume_feedback = QLabel("")
        self.volume_feedback.setObjectName("instructionLabel")
        self.volume_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.volume_feedback.setVisible(False)
        layout.addWidget(self.volume_feedback)

        # ── Brightness ──────────────────────────────────────────────────
        bright_header = QHBoxLayout()
        bright_header.addWidget(self._make_field_label("Brightness"))
        bright_header.addStretch()
        self.brightness_val_label = QLabel("80%")
        self.brightness_val_label.setStyleSheet("color: #374151; font-weight: 600; font-size: 9pt;")
        bright_header.addWidget(self.brightness_val_label)
        layout.addLayout(bright_header)

        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(80)
        self.brightness_slider.valueChanged.connect(lambda v: self.brightness_val_label.setText(f"{v}%"))
        self.brightness_slider.sliderReleased.connect(self._send_brightness)
        layout.addWidget(self.brightness_slider)

        self.brightness_feedback = QLabel("")
        self.brightness_feedback.setObjectName("instructionLabel")
        self.brightness_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brightness_feedback.setVisible(False)
        layout.addWidget(self.brightness_feedback)

        # Separator
        sep1 = QFrame()
        sep1.setObjectName("separator")
        sep1.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep1)

        # ── Timeouts ────────────────────────────────────────────────────
        layout.addWidget(self._make_field_label("QR Screen Timeout (seconds)"))
        self.timeout_qr = QLineEdit("300")
        layout.addWidget(self.timeout_qr)

        layout.addWidget(self._make_field_label("Pass/Fail Screen Timeout (seconds)"))
        self.timeout_pf = QLineEdit("20")
        layout.addWidget(self.timeout_pf)

        self.btn_set_timeout = QPushButton("Set Timeouts")
        self.btn_set_timeout.setObjectName("primaryBtn")
        self.btn_set_timeout.clicked.connect(self._send_timeout)
        layout.addWidget(self.btn_set_timeout)

        self.timeout_feedback = QLabel("")
        self.timeout_feedback.setObjectName("instructionLabel")
        self.timeout_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timeout_feedback.setVisible(False)
        layout.addWidget(self.timeout_feedback)

        # Separator
        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        # ── Bluetooth ───────────────────────────────────────────────────
        layout.addWidget(self._make_field_label("Bluetooth"))
        ble_row = QHBoxLayout()
        self.btn_ble_on = QPushButton("📡  BLE ON")
        self.btn_ble_on.setObjectName("secondaryBtn")
        self.btn_ble_on.clicked.connect(lambda: self._send_ble(True))
        ble_row.addWidget(self.btn_ble_on)

        self.btn_ble_off = QPushButton("📡  BLE OFF")
        self.btn_ble_off.setObjectName("secondaryBtn")
        self.btn_ble_off.clicked.connect(lambda: self._send_ble(False))
        ble_row.addWidget(self.btn_ble_off)
        layout.addLayout(ble_row)

        self.ble_feedback = QLabel("")
        self.ble_feedback.setObjectName("instructionLabel")
        self.ble_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ble_feedback.setVisible(False)
        layout.addWidget(self.ble_feedback)

        # Separator
        sep3 = QFrame()
        sep3.setObjectName("separator")
        sep3.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep3)

        # ── Language Firmware ───────────────────────────────────────────
        layout.addWidget(self._make_field_label("Language Firmware Update"))
        self.language_dropdown = QComboBox()
        self.language_dropdown.setView(QListView())
        self.language_dropdown.addItem("Loading languages...")
        self.language_dropdown.setEnabled(False)
        layout.addWidget(self.language_dropdown)

        layout.addSpacing(12)
        self.btn_update_language = QPushButton("🔄 Download Language Firmware")
        self.btn_update_language.setObjectName("secondaryBtn")
        self.btn_update_language.clicked.connect(self._open_language_update_page)
        self.btn_update_language.setEnabled(False)
        layout.addWidget(self.btn_update_language)

        # Separator
        sep4 = QFrame()
        sep4.setObjectName("separator")
        sep4.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep4)

        # ── Buzzer (B30/B32 only) ───────────────────────────────────────
        self.buzzer_section_label = self._make_field_label("Buzzer (B30/B32 only)")
        layout.addWidget(self.buzzer_section_label)

        self.buzzer_container = QWidget()
        buzzer_inner = QVBoxLayout(self.buzzer_container)
        buzzer_inner.setContentsMargins(0, 0, 0, 0)
        buzzer_inner.setSpacing(8)

        buzzer_row = QHBoxLayout()
        self.btn_buzzer_on = QPushButton("🔔  Enable")
        self.btn_buzzer_on.setObjectName("secondaryBtn")
        self.btn_buzzer_on.clicked.connect(self._send_buzzer_on)
        buzzer_row.addWidget(self.btn_buzzer_on)

        self.btn_buzzer_off = QPushButton("🔕  Disable")
        self.btn_buzzer_off.setObjectName("secondaryBtn")
        self.btn_buzzer_off.clicked.connect(self._send_buzzer_off)
        buzzer_row.addWidget(self.btn_buzzer_off)
        buzzer_inner.addLayout(buzzer_row)

        self.buzzer_feedback = QLabel("")
        self.buzzer_feedback.setObjectName("instructionLabel")
        self.buzzer_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.buzzer_feedback.setVisible(False)
        buzzer_inner.addWidget(self.buzzer_feedback)

        layout.addWidget(self.buzzer_container)

        # Separator for Logs
        sep5 = QFrame()
        sep5.setObjectName("separator")
        sep5.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep5)

        # Application Logs Section
        layout.addWidget(self._make_field_label("Application Logs"))

        log_btn_row = QHBoxLayout()
        self.btn_open_log = QPushButton("📂 Open Log File")
        self.btn_open_log.setObjectName("secondaryBtn")
        self.btn_open_log.clicked.connect(self._open_log_file)
        log_btn_row.addWidget(self.btn_open_log)

        self.btn_refresh_log = QPushButton("🔄 Refresh Logs")
        self.btn_refresh_log.setObjectName("secondaryBtn")
        self.btn_refresh_log.clicked.connect(self._refresh_logs)
        log_btn_row.addWidget(self.btn_refresh_log)
        layout.addLayout(log_btn_row)

        self.log_display = QTextEdit()
        self.log_display.setObjectName("logDisplay")
        self.log_display.setReadOnly(True)
        self.log_display.setMinimumHeight(120)
        layout.addWidget(self.log_display)

        self.stack.addWidget(page)

    def _build_page_quick(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        row1 = QHBoxLayout()
        self.btn_idle = QPushButton("💤 IDLE")
        self.btn_idle.setObjectName("secondaryBtn")
        self.btn_idle.clicked.connect(lambda: self.device.send_command("IDLE"))
        row1.addWidget(self.btn_idle)

        self.btn_wake = QPushButton("☀️ WAKE")
        self.btn_wake.setObjectName("secondaryBtn")
        self.btn_wake.clicked.connect(lambda: self.device.send_command("WAKE"))
        row1.addWidget(self.btn_wake)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_reset = QPushButton("🔄 RESET")
        self.btn_reset.setObjectName("warningBtn")
        self.btn_reset.clicked.connect(lambda: self.device.send_command("RESET"))
        row2.addWidget(self.btn_reset)

        self.btn_format = QPushButton("🗑 FORMAT")
        self.btn_format.setObjectName("dangerBtn")
        self.btn_format.clicked.connect(lambda: self.device.send_command("FORMAT"))
        row2.addWidget(self.btn_format)
        layout.addLayout(row2)

        self.btn_quick_qr = QPushButton("📲 Send QR")
        self.btn_quick_qr.setObjectName("secondaryBtn")
        self.btn_quick_qr.clicked.connect(self._send_qr)
        layout.addWidget(self.btn_quick_qr)

        self.btn_quick_wait = QPushButton("⏳ WAIT")
        self.btn_quick_wait.setObjectName("secondaryBtn")
        self.btn_quick_wait.clicked.connect(self._quick_send_wait)
        layout.addWidget(self.btn_quick_wait)

        self.btn_quick_pass = QPushButton("✅ PASS")
        self.btn_quick_pass.setObjectName("secondaryBtn")
        self.btn_quick_pass.clicked.connect(self._quick_send_pass)
        layout.addWidget(self.btn_quick_pass)



        self.stack.addWidget(page)

    # ── Page switching ───────────────────────────────────────────────────

    def _switch_page(self, index):
        for i in range(self.stack.count()):
            self.stack.widget(i).setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.stack.widget(index).setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        self.stack.setCurrentIndex(index)
        
        QApplication.processEvents()
        if hasattr(self, 'scroll_content'):
            ideal_h = self.scroll_content.sizeHint().height()
            self.resize(self.width(), min(ideal_h, self.maximumHeight()))
        else:
            self.adjustSize()

    # ── Command logic ────────────────────────────────────────────────────

    def _on_status_type_change(self, choice):
        if "PASS" in choice:
            self.status_field1.setText("SUCCESS!")
            self.status_field2.setText("Payment successful")
        elif "WAIT" in choice:
            self.status_field1.setText("Rs. 560.50")
            self.status_field2.setText("Please wait...")
        elif "FAIL" in choice:
            self.status_field1.setText("Rs. 560.50")
            self.status_field2.setText("Payment Failed")
        elif "WARN" in choice:
            self.status_field1.setText("Device Not Ready")
            self.status_field2.setText("Please wait")
        elif "INFO" in choice:
            self.status_field1.setText("Important")
            self.status_field2.setText("Keep device connected")

    def _send_status(self):
        cmd = self.status_type.currentText().split()[0]
        self.device.send_command(f"{cmd}**{self.status_field1.text()}**{self.status_field2.text()}")

    def _quick_send_wait(self):
        index = self.status_type.findText("WAIT", Qt.MatchFlag.MatchContains)
        if index >= 0:
            self.status_type.setCurrentIndex(index)
        self._send_status()

    def _quick_send_pass(self):
        index = self.status_type.findText("PASS", Qt.MatchFlag.MatchContains)
        if index >= 0:
            self.status_type.setCurrentIndex(index)
        self._send_status()

    def _send_qr(self):
        self.device.send_command(
            f"QR**{self.qr_amount.text()}**{self.qr_scan_text.text()}"
            f"**{self.qr_payload.toPlainText().strip()}"
        )

    def _send_text(self):
        self.device.send_command(
            f"TEXT**{self.text_title.text()}**{self.text_subtitle.text()}"
            f"**{self.text_msg.toPlainText().strip()}"
        )

    def _select_preview_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Preview Image", "", "JPEG (*.jpg *.jpeg)")
        if path:
            self.preview_file_path = path
            self.preview_label.setText(os.path.basename(path))
            self.preview_label.setStyleSheet("color: #374151;")
            
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.preview_image_preview.setPixmap(pixmap.scaled(
                    self.preview_image_preview.width() - 4,
                    self.preview_image_preview.height() - 4,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            
            if self.device.connected:
                self.btn_upload_preview.setEnabled(True)

    def _upload_preview_image(self):
        if not self.preview_file_path:
            return
        self.btn_upload_preview.setEnabled(False)
        self.btn_upload_preview.setText("Uploading…")

        size_text = self.preview_size.currentText()
        width, height = (320, 480) if "3.5" in size_text else (240, 320)

        def _work():
            try:
                with open(self.preview_file_path, "rb") as f:
                    raw = f.read()
                img = Image.open(io.BytesIO(raw))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img = img.resize((width, height), Image.Resampling.LANCZOS)

                quality, jpeg_data = 95, b""
                while quality > 5:
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=quality, optimize=False)
                    jpeg_data = buf.getvalue()
                    if len(jpeg_data) <= 30 * 1024:
                        break
                    quality -= 5

                res = self.device.upload_image(jpeg_data)
                if res.get("success"):
                    self.upload_status_updated.emit("✓ Preview loaded on device", "#16a34a", True)
                else:
                    self.upload_status_updated.emit(f"Error: {res.get('error', '?')}", "#dc2626", True)
            except Exception as e:
                logger.error(f"Preview image error: {e}")
                self.upload_status_updated.emit("Processing error", "#dc2626", True)

        threading.Thread(target=_work, daemon=True).start()

    def _select_wallpaper(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Wallpaper Image", "", "JPEG (*.jpg *.jpeg)")
        if path:
            self.wallpaper_file_path = path
            self.wallpaper_label.setText(os.path.basename(path))
            self.wallpaper_label.setStyleSheet("color: #374151;")
            
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.wallpaper_preview.setPixmap(pixmap.scaled(
                    self.wallpaper_preview.width() - 4,
                    self.wallpaper_preview.height() - 4,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            
            if self.device.connected:
                self.btn_upload_wallpaper.setEnabled(True)

    def _upload_wallpaper(self):
        if not self.wallpaper_file_path:
            return
        self.btn_upload_wallpaper.setEnabled(False)
        self.btn_upload_wallpaper.setText("Uploading…")

        size_text = self.wallpaper_size.currentText()
        width, height = (320, 480) if "3.5" in size_text else (240, 320)
        slot2 = self.wallpaper_slot.currentIndex() == 1

        def _work():
            try:
                with open(self.wallpaper_file_path, "rb") as f:
                    raw = f.read()
                img = Image.open(io.BytesIO(raw))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img = img.resize((width, height), Image.Resampling.LANCZOS)

                quality, jpeg_data = 95, b""
                while quality > 5:
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=quality, optimize=False)
                    jpeg_data = buf.getvalue()
                    if len(jpeg_data) <= 30 * 1024:
                        break
                    quality -= 5

                res = self.device.upload_wallpaper(jpeg_data, slot2=slot2)
                if res.get("success"):
                    self.wallpaper_upload_status_updated.emit("✓ Wallpaper saved to device", "#16a34a", True)
                else:
                    self.wallpaper_upload_status_updated.emit(f"Error: {res.get('error', '?')}", "#dc2626", True)
            except Exception as e:
                logger.error(f"Wallpaper image error: {e}")
                self.wallpaper_upload_status_updated.emit("Processing error", "#dc2626", True)

        threading.Thread(target=_work, daemon=True).start()

    def _on_idle_mode_change(self, index):
        """Show/hide fields based on selected idle mode."""
        # Modes: 0=SLEEP_WAKE, 1=SINGLE, 2=CYCLE, 3=SLEEP
        is_sleep_wake = (index == 0)
        is_single = (index == 1)
        is_cycle = (index == 2)
        is_sleep = (index == 3)
        is_sleep_wake = (index == 0)

        # Image name — shown for ALL modes
        self.idle_img1_label.setVisible(True)
        self.idle_img1.setVisible(True)

        # Sleep/Wake durations — only SLEEP_WAKE
        self.idle_sleep_ms_label.setVisible(is_sleep_wake)
        self.idle_sleep_ms.setVisible(is_sleep_wake)
        self.idle_wake_ms_label.setVisible(is_sleep_wake)
        self.idle_wake_ms.setVisible(is_sleep_wake)

        # Screentime — only SLEEP
        if hasattr(self, 'idle_screentime_label'):
            self.idle_screentime_label.setVisible(is_sleep)
            self.idle_screentime.setVisible(is_sleep)

        # Second image + durations — only CYCLE
        self.idle_img2_label.setVisible(is_cycle)
        self.idle_img2.setVisible(is_cycle)
        self.idle_time1_label.setVisible(is_cycle)
        self.idle_time1.setVisible(is_cycle)
        self.idle_time2_label.setVisible(is_cycle)
        self.idle_time2.setVisible(is_cycle)

        QApplication.processEvents()
        if hasattr(self, 'scroll_content'):
            ideal_h = self.scroll_content.sizeHint().height()
            self.resize(self.width(), min(ideal_h, self.maximumHeight()))
        else:
            self.adjustSize()

    def _send_idle_mode(self):
        """Send the selected idle mode command."""
        index = self.idle_mode_dropdown.currentIndex()
        img1 = self.idle_img1.currentText()

        if index == 0:  # SLEEP_WAKE
            try:
                wake_ms = int(self.idle_wake_ms.text())
                sleep_ms = int(self.idle_sleep_ms.text())
            except ValueError:
                wake_ms, sleep_ms = 120000, 30000
            self.device.set_idle_sleep_wake(img1, sleep_ms, wake_ms)
        elif index == 1:  # SINGLE
            self.device.set_idle_single(img1)
        elif index == 2:  # CYCLE
            img2 = self.idle_img2.currentText()
            try:
                time1 = int(self.idle_time1.text())
                time2 = int(self.idle_time2.text())
            except ValueError:
                time1, time2 = 60000, 60000
            self.device.set_idle_cycle(img1, time1, img2, time2)
        elif index == 3:  # SLEEP
            try:
                screentime_s = int(self.idle_screentime.text())
            except ValueError:
                screentime_s = 30
            self.device.set_idle_sleep(img1)
            self.device.set_screentime(screentime_s)
        self._show_feedback(self.idle_mode_feedback, "✓ Command sent")

    def _send_timeout(self):
        """Send the timeout command."""
        try:
            qr_sec = int(self.timeout_qr.text())
            pf_sec = int(self.timeout_pf.text())
        except ValueError:
            qr_sec, pf_sec = 300, 20
        self.device.set_timeout(qr_sec, pf_sec)
        self._show_feedback(self.timeout_feedback, "✓ Command sent")

    def _send_buzzer_on(self):
        self.device.activate_buzzer(1)
        self._show_feedback(self.buzzer_feedback, "✓ Buzzer enabled")

    def _send_buzzer_off(self):
        self.device.activate_buzzer(0)
        self._show_feedback(self.buzzer_feedback, "✓ Buzzer disabled")

    def _send_volume(self):
        val = self.volume_slider.value()
        self.device.set_volume(val)
        self._show_feedback(self.volume_feedback, f"✓ Volume set to {val}%")

    def _send_brightness(self):
        val = self.brightness_slider.value()
        self.device.set_brightness(val)
        self._show_feedback(self.brightness_feedback, f"✓ Brightness set to {val}%")

    def _send_ble(self, enabled: bool):
        self.device.set_ble(enabled)
        label = "ON" if enabled else "OFF"
        self._show_feedback(self.ble_feedback, f"✓ Bluetooth {label}")

    def _show_feedback(self, label, text, color="#16a34a"):
        """Show a brief feedback message on a label, auto-hide after 3s."""
        label.setText(text)
        label.setStyleSheet(f"color: {color};")
        label.setVisible(True)
        # Auto-hide after 3 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: label.setVisible(False))



    def _fetch_languages(self):
        langs = get_languages()
        self.languages_loaded.emit(langs)

    @pyqtSlot(list)
    def _on_languages_loaded(self, langs: list[str]):
        self.language_dropdown.clear()
        if langs:
            self.language_dropdown.addItems(langs)
            self.language_dropdown.setEnabled(True)
            self.btn_update_language.setEnabled(True)
        else:
            self.language_dropdown.addItem("Failed to load languages")

    def _open_language_update_page(self):
        lang = self.language_dropdown.currentText()
        if not lang or "Loading" in lang or "Failed" in lang:
            return

        model = getattr(self.device, "model", None)
        if not model:
            model = extract_model_code(self.device.device_id)
        if not model:
            model = "B31"

        url = build_update_url(model=model, port=self.device.port, language=lang)

        # Suspend auto-connection for 2 minutes (120 seconds) to let the flasher work
        self.device.suspend_auto_connect(120)

        # Disconnect so the web flasher can claim the serial port
        if self.device.connected:
            threading.Thread(target=self.device.disconnect, daemon=True).start()

        self.showMinimized()
        QDesktopServices.openUrl(QUrl(url))

    def _open_firmware_update_page(self):
        """
        Disconnect the device (freeing the COM port for the web flasher),
        minimize the app, then open the firmware-update page in the browser.
        """
        update_info = getattr(self.device, "firmware_update_info", None) or {}
        url = update_info.get("update_url") or "https://yarsa.tech/firmware-update"

        # Suspend auto-connection for 2 minutes (120 seconds) to let the flasher work
        self.device.suspend_auto_connect(120)

        # Disconnect so the web flasher can claim the serial port
        if self.device.connected:
            threading.Thread(target=self.device.disconnect, daemon=True).start()

        # Minimize out of the way
        self.showMinimized()

        # Open browser
        QDesktopServices.openUrl(QUrl(url))

    def _rescan_ports(self):
        """Populate the port dropdown with available serial ports."""
        self.port_dropdown.clear()
        ports = self.device.get_available_ports()
        
        # Filter for CH340/CH341 type devices
        ch340_ports = [p for p in ports if p["is_ch340"]]
        
        if not ch340_ports:
            self.port_dropdown.addItem("No Nizi devices found")
            return

        for p in ch340_ports:
            label = f"{p['port']} - {p['description']} ({APP_NAME})"
            self.port_dropdown.addItem(label, p["port"])

    def _on_mode_changed(self, button):
        """Handle auto/manual mode switching."""
        is_auto = button == self.radio_auto
        self.device.enable_auto_connect(is_auto)
        
        # If switching to manual while disconnected, ensure port UI is visible
        # If switching to auto while disconnected, polling will start
        self._on_status_updated(self.device.connected, self.device.port or "")

    def _apply_device_screen_profile(self):
        """
        Auto-select image target size and buzzer visibility from device ID:
        - B30/B31 -> 2.8" (240x320)
        - B32/B33 -> 3.5" (320x480)
        - Buzzer: only available on B30 and B32
        """
        device_id = (getattr(self.device, "device_id", None) or "").upper().replace("_", "")
        if "B30" in device_id or "B31" in device_id:
            self.preview_size.setCurrentIndex(0)
            self.preview_size.setEnabled(False)
            self.wallpaper_size.setCurrentIndex(0)
            self.wallpaper_size.setEnabled(False)
        elif "B32" in device_id or "B33" in device_id:
            self.preview_size.setCurrentIndex(1)
            self.preview_size.setEnabled(False)
            self.wallpaper_size.setCurrentIndex(1)
            self.wallpaper_size.setEnabled(False)
        else:
            # Unknown device id: allow manual selection.
            self.preview_size.setEnabled(True)
            self.wallpaper_size.setEnabled(True)

        # Buzzer is only available on B30 and B32
        has_buzzer = "B30" in device_id or "B32" in device_id
        self.buzzer_container.setVisible(has_buzzer)
        self.buzzer_section_label.setVisible(has_buzzer)

    # ── Slot handlers ────────────────────────────────────────────────────

    @pyqtSlot(str, str, bool)
    def _on_upload_status(self, text, color, enable):
        self.preview_label.setText(text)
        self.preview_label.setStyleSheet(f"color: {color};")
        self.btn_upload_preview.setText("Show Preview on Device")
        self.btn_upload_preview.setEnabled(enable)

    @pyqtSlot(str, str, bool)
    def _on_wallpaper_upload_status(self, text, color, enable):
        self.wallpaper_label.setText(text)
        self.wallpaper_label.setStyleSheet(f"color: {color};")
        self.btn_upload_wallpaper.setText("Save Wallpaper to Device")
        self.btn_upload_wallpaper.setEnabled(enable)

    @pyqtSlot(bool, str)
    def _on_status_updated(self, connected, port):
        if connected:
            self._apply_device_screen_profile()
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #16a34a; font-size: 15px; font-weight: 600;")
            self.instruction_label.setText(f"Communicating on {port}")

            # Show firmware version if available
            fw = getattr(self.device, "firmware_id", None)
            if fw:
                self.firmware_label.setText(f"Firmware: {fw}")
                self.firmware_label.setVisible(True)
            else:
                self.firmware_label.setVisible(False)

            # Show update badge if a newer firmware is available
            update_info = getattr(self.device, "firmware_update_info", None) or {}
            if update_info.get("update_available"):
                latest = update_info.get("latest_clean", "")
                self.update_available_label.setText(f"⚠ Update available: {latest}")
                self.update_available_label.setVisible(True)
                self.btn_update_firmware.setVisible(True)
            else:
                self.update_available_label.setVisible(False)
                self.btn_update_firmware.setVisible(False)

            self.btn_action.setText("Disconnect")
            self.btn_action.setObjectName("disconnectBtn")
            self.btn_action.setStyleSheet("")  # re-apply from stylesheet
            self.btn_action.style().unpolish(self.btn_action)
            self.btn_action.style().polish(self.btn_action)
            self.btn_action.setEnabled(True)

            self.commands_container.setVisible(True)
            self.port_selection_container.setVisible(False)
            if hasattr(self, 'preview_file_path') and self.preview_file_path:
                self.btn_upload_preview.setEnabled(True)
            if hasattr(self, 'wallpaper_file_path') and self.wallpaper_file_path:
                self.btn_upload_wallpaper.setEnabled(True)
        else:
            self.preview_size.setEnabled(True)
            self.wallpaper_size.setEnabled(True)
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: #64748b; font-size: 15px; font-weight: 600;")
            self.instruction_label.setText("Plug in device to get started.")
            self.firmware_label.setVisible(False)
            self.update_available_label.setVisible(False)
            self.btn_update_firmware.setVisible(False)
            self.btn_action.setText("Connect Now")
            self.btn_action.setObjectName("connectBtn")
            self.btn_action.setStyleSheet("")
            self.btn_action.style().unpolish(self.btn_action)
            self.btn_action.style().polish(self.btn_action)
            self.btn_action.setEnabled(True)

            self.commands_container.setVisible(False)
            
            # Port selection only visible in Manual mode when disconnected
            is_manual = self.radio_manual.isChecked()
            self.port_selection_container.setVisible(is_manual)
            self.instruction_label.setVisible(not is_manual)
            
            if is_manual:
                self._rescan_ports()

        self.adjustSize()

    def _manual_connect(self):
        if self.device.connected:
            self.device.disconnect()
        else:
            selected_port = self.port_dropdown.currentData()
            
            self.btn_action.setEnabled(False)
            self.btn_action.setText("Connecting…")

            def _do():
                res = self.device.connect(port=selected_port)
                if not res.get("success", False):
                    self.status_updated.emit(self.device.connected, self.device.port or "")

            threading.Thread(target=_do, daemon=True).start()

    def _quit_app(self):
        self.hide()
        if self.on_quit_callback:
            self.on_quit_callback()

    def _open_log_file(self):
        from config import config
        log_file = config.config_dir / "app.log"
        if log_file.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(log_file.as_posix()))

    def _refresh_logs(self):
        from config import config
        log_file = config.config_dir / "app.log"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                # Show last 50 lines
                self.log_display.setPlainText("".join(lines[-50:]))
            except Exception as e:
                self.log_display.setPlainText(f"Failed to read log: {e}")
        else:
            self.log_display.setPlainText("Log file does not exist yet.")

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_logs()

    # ── Window management ────────────────────────────────────────────────

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    @pyqtSlot()
    def _toggle_internal(self):
        if self._is_visible:
            self.hide()
        else:
            self.show_window()

    def toggle(self):
        self.toggle_visibility.emit()

    def show_window(self):
        self.adjustSize()
        if hasattr(self, 'scroll_content'):
            # Calculate the ideal height to show all controls without scrolling
            ideal_h = self.scroll_content.sizeHint().height() + 40
            self.resize(self.width(), min(ideal_h, self.maximumHeight()))
            
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + (geo.height() - self.height()) // 2
        self.move(x, y)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._is_visible = True
        
        # Force foreground focus on macOS for background agents (LSUIElement=True)
        import platform
        if platform.system() == "Darwin":
            import os
            os.system("osascript -e 'tell application \"System Events\" to set frontmost of every process whose name is \"NiziPOSConnector\" to true' >/dev/null 2>&1")

    def hide(self):
        super().hide()
        self._is_visible = False
