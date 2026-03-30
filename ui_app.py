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
    QRadioButton, QButtonGroup, QDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QGuiApplication, QIcon

from config import APP_NAME
from theme_support import flyout_dark_stylesheet, prefers_light_theme

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
    margin-top: 2px;
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

/* ── Dropdown (QComboBox) ─────────────────────────────── */

QComboBox {
    font-size: 10pt;
    padding: 8px 14px;
    border: 1px solid #d1d5db;
    border-radius: 10px;
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
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background-color: #ffffff;
    selection-background-color: #eef2ff;
    selection-color: #b91c1c;
    outline: 0;
    padding: 4px;
}
QComboBox QAbstractItemView::item {
    padding: 6px 12px;
    min-height: 22px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #f3f4f6;
}

/* ── Inputs ───────────────────────────────────────────── */

QLineEdit {
    font-size: 10pt;
    padding: 9px 14px;
    border: 1px solid #d1d5db;
    border-radius: 10px;
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
    padding: 8px 12px;
    border: 1px solid #d1d5db;
    border-radius: 10px;
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
    padding: 10px 20px;
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 10px;
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
    padding: 10px 20px;
    background-color: #ffffff;
    color: #374151;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    font-weight: 500;
}
QPushButton#secondaryBtn:hover {
    background-color: #f3f4f6;
    border-color: #fca5a5;
}

QPushButton#dangerBtn {
    font-size: 10pt;
    padding: 10px 20px;
    background-color: #fef2f2;
    color: #dc2626;
    border: 1px solid #fecaca;
    border-radius: 10px;
    font-weight: 500;
}
QPushButton#dangerBtn:hover {
    background-color: #fee2e2;
    border-color: #f87171;
}

QPushButton#warningBtn {
    font-size: 10pt;
    padding: 10px 20px;
    background-color: #fffbeb;
    color: #d97706;
    border: 1px solid #fde68a;
    border-radius: 10px;
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

QDialog {
    background-color: #ffffff;
}
"""






class TrayFlyout(QWidget):
    status_updated = pyqtSignal(bool, str)
    upload_status_updated = pyqtSignal(str, str, bool)
    toggle_visibility = pyqtSignal()

    def __init__(self, device_manager, web_port=9121, on_quit=None):
        super().__init__()
        self.device = device_manager
        self.web_port = web_port
        self.on_quit_callback = on_quit

        self.setWindowTitle(APP_NAME)
        self.setObjectName("mainWindow")
        self.setMinimumWidth(400)
        self.setMaximumWidth(460)
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
        self.toggle_visibility.connect(self._toggle_internal)

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

    # ── UI Construction ──────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(16)

        # Header
        title = QLabel("NIZI POS")
        title.setObjectName("headerTitle")
        root.addWidget(title)

        # Status card
        card = QFrame()
        card.setObjectName("statusCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

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
        self.page_selector.addItems([
            "Status Screen",
            "QR Display",
            "Text Display",
            "Image Upload",
            "Quick Actions",
        ])
        self.page_selector.setMinimumWidth(160)
        self.page_selector.currentIndexChanged.connect(self._switch_page)
        section_row.addWidget(self.page_selector)
        commands_layout.addLayout(section_row)

        # Stacked pages
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        commands_layout.addWidget(self.stack)

        self._build_page_status()
        self._build_page_qr()
        self._build_page_text()
        self._build_page_image()
        self._build_page_quick()

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
        layout.setSpacing(8)

        layout.addWidget(self._make_field_label("Type"))
        self.status_type = QComboBox()
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

        self.btn_send_status = QPushButton("Send")
        self.btn_send_status.setObjectName("primaryBtn")
        self.btn_send_status.clicked.connect(self._send_status)
        layout.addWidget(self.btn_send_status)

        self.stack.addWidget(page)

    def _build_page_qr(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

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

        self.btn_send_qr = QPushButton("Send")
        self.btn_send_qr.setObjectName("primaryBtn")
        self.btn_send_qr.clicked.connect(self._send_qr)
        layout.addWidget(self.btn_send_qr)

        self.stack.addWidget(page)

    def _build_page_text(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

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

        self.btn_send_text = QPushButton("Send")
        self.btn_send_text.setObjectName("primaryBtn")
        self.btn_send_text.clicked.connect(self._send_text)
        layout.addWidget(self.btn_send_text)

        self.stack.addWidget(page)

    def _build_page_image(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.img_file_path = None

        self.btn_select_img = QPushButton("Browse Image…")
        self.btn_select_img.setObjectName("secondaryBtn")
        self.btn_select_img.clicked.connect(self._select_image)
        layout.addWidget(self.btn_select_img)

        self.img_label = QLabel("No image selected")
        self.img_label.setObjectName("instructionLabel")
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.img_label)

        layout.addWidget(self._make_field_label("Screen Size"))
        self.img_size_dropdown = QComboBox()
        self.img_size_dropdown.addItems(["2.8 inch (240×320)", "3.5 inch (320×480)"])
        layout.addWidget(self.img_size_dropdown)

        self.btn_upload_img = QPushButton("Upload to Device")
        self.btn_upload_img.setObjectName("primaryBtn")
        self.btn_upload_img.clicked.connect(self._upload_image)
        self.btn_upload_img.setEnabled(False)
        layout.addWidget(self.btn_upload_img)

        self.stack.addWidget(page)

    def _build_page_quick(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        row1 = QHBoxLayout()
        self.btn_idle = QPushButton("💤  IDLE")
        self.btn_idle.setObjectName("secondaryBtn")
        self.btn_idle.clicked.connect(lambda: self.device.send_command("IDLE"))
        row1.addWidget(self.btn_idle)

        self.btn_wake = QPushButton("☀️  WAKE")
        self.btn_wake.setObjectName("secondaryBtn")
        self.btn_wake.clicked.connect(lambda: self.device.send_command("WAKE"))
        row1.addWidget(self.btn_wake)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_reset = QPushButton("🔄  RESET")
        self.btn_reset.setObjectName("warningBtn")
        self.btn_reset.clicked.connect(lambda: self.device.send_command("RESET"))
        row2.addWidget(self.btn_reset)

        self.btn_format = QPushButton("🗑  FORMAT")
        self.btn_format.setObjectName("dangerBtn")
        self.btn_format.clicked.connect(lambda: self.device.send_command("FORMAT"))
        row2.addWidget(self.btn_format)
        layout.addLayout(row2)

        self.stack.addWidget(page)

    # ── Page switching ───────────────────────────────────────────────────

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
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

    def _select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "JPEG (*.jpg *.jpeg)")
        if path:
            self.img_file_path = path
            self.img_label.setText(os.path.basename(path))
            self.img_label.setStyleSheet("color: #374151;")
            if self.device.connected:
                self.btn_upload_img.setEnabled(True)

    def _upload_image(self):
        if not self.img_file_path:
            return
        self.btn_upload_img.setEnabled(False)
        self.btn_upload_img.setText("Uploading…")

        size_text = self.img_size_dropdown.currentText()
        width, height = (320, 480) if "3.5" in size_text else (240, 320)

        def _work():
            try:
                with open(self.img_file_path, "rb") as f:
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
                    self.upload_status_updated.emit("✓ Uploaded", "#16a34a", True)
                else:
                    self.upload_status_updated.emit(f"Error: {res.get('error', '?')}", "#dc2626", True)
            except Exception as e:
                logger.error(f"Image error: {e}")
                self.upload_status_updated.emit("Processing error", "#dc2626", True)

        threading.Thread(target=_work, daemon=True).start()

    def _rescan_ports(self):
        """Populate the port dropdown with available serial ports."""
        self.port_dropdown.clear()
        ports = self.device.get_available_ports()
        
        if not ports:
            self.port_dropdown.addItem("No ports found")
            return

        for p in ports:
            label = f"{p['port']} - {p['description']}"
            if p["is_ch340"]:
                label += f" ({APP_NAME})"
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
        Auto-select image target size from device ID:
        - B30/B31 -> 2.8" (240x320)
        - B32/B33 -> 3.5" (320x480)
        """
        device_id = (getattr(self.device, "device_id", None) or "").upper().replace("_", "")
        if "B30" in device_id or "B31" in device_id:
            self.img_size_dropdown.setCurrentIndex(0)
            self.img_size_dropdown.setEnabled(False)
            return
        if "B32" in device_id or "B33" in device_id:
            self.img_size_dropdown.setCurrentIndex(1)
            self.img_size_dropdown.setEnabled(False)
            return
        # Unknown device id: allow manual selection.
        self.img_size_dropdown.setEnabled(True)

    # ── Slot handlers ────────────────────────────────────────────────────

    @pyqtSlot(str, str, bool)
    def _on_upload_status(self, text, color, enable):
        self.img_label.setText(text)
        self.img_label.setStyleSheet(f"color: {color};")
        self.btn_upload_img.setText("Upload to Device")
        self.btn_upload_img.setEnabled(enable)

    @pyqtSlot(bool, str)
    def _on_status_updated(self, connected, port):
        if connected:
            self._apply_device_screen_profile()
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #16a34a; font-size: 15px; font-weight: 600;")
            self.instruction_label.setText(f"Communicating on {port}")
            self.btn_action.setText("Disconnect")
            self.btn_action.setObjectName("disconnectBtn")
            self.btn_action.setStyleSheet("")  # re-apply from stylesheet
            self.btn_action.style().unpolish(self.btn_action)
            self.btn_action.style().polish(self.btn_action)
            self.btn_action.setEnabled(True)

            self.commands_container.setVisible(True)
            self.port_selection_container.setVisible(False)
            if self.img_file_path:
                self.btn_upload_img.setEnabled(True)
        else:
            self.img_size_dropdown.setEnabled(True)
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: #64748b; font-size: 15px; font-weight: 600;")
            self.instruction_label.setText("Plug in device to get started.")
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
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + (geo.height() - self.height()) // 2
        self.move(x, y)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._is_visible = True

    def hide(self):
        super().hide()
        self._is_visible = False
