from pathlib import Path
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QRadioButton,
    QButtonGroup,
    QListWidget,
    QListWidgetItem,
    QFrame,
)

from theme_support import (
    get_dialog_stylesheet,
    get_progress_dialog_stylesheet,
    get_theme_tokens,
    prefers_light_theme,
)

class ModernPromptDialog(QDialog):
    """A reusable, themed prompt dialog (Yes/No)."""
    def __init__(self, parent=None, title="Prompt", headline_text="", info_text="", min_width=420, min_height=160):
        super().__init__(parent)
        self._accepted = False
        
        is_light = prefers_light_theme()
        colors = get_theme_tokens(is_light)
        
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setMinimumWidth(min_width)
        self.setMinimumHeight(min_height)

        headline = QLabel(headline_text)
        headline.setStyleSheet(f"color:{colors['text_primary']}; font-size: 13.5pt; font-weight: 800;")

        info_lbl = QLabel(info_text)
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color:{colors['text_muted']}; font-size: 11pt; font-weight: 600;")

        yes_btn = QPushButton("Yes")
        yes_btn.setObjectName("yesBtn")
        no_btn = QPushButton("No")
        no_btn.setObjectName("noBtn")

        def _accept():
            self._accepted = True
            self.accept()

        yes_btn.clicked.connect(_accept)
        no_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(colors['spacing_lg'])
        btn_row.addStretch(1)
        btn_row.addWidget(yes_btn)
        btn_row.addWidget(no_btn)
        btn_row.addStretch(1)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            colors['layout_margin_lg'],
            colors['layout_margin_lg'],
            colors['layout_margin_lg'],
            colors['layout_margin_md']
        )
        root.setSpacing(colors['spacing_md'])
        root.addWidget(headline)
        root.addWidget(info_lbl)
        root.addLayout(btn_row)

        self.setStyleSheet(get_dialog_stylesheet(is_light))
        self.adjustSize()
        self.setFixedSize(self.size())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._accepted = False
        self.reject()
        event.accept()
        
    @property
    def is_accepted(self) -> bool:
        return self._accepted


class ModernProgressDialog(QProgressDialog):
    """A reusable, themed progress dialog."""
    def __init__(self, parent=None, title="Progress", label_text="Loading...", min_width=480, min_height=210):
        super().__init__(label_text, "Cancel", 0, 0, parent)
        is_light = prefers_light_theme()
        
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setMinimumDuration(0)
        self.setAutoClose(True)
        self.setAutoReset(False)
        self.setMinimumWidth(min_width)
        self.setMinimumHeight(min_height)
        
def _resolve_asset_path(filename: str) -> str:
    """Resolve an asset file path safely whether running from source or frozen executable."""
    import sys
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "assets" / filename)
    candidates.append(Path(__file__).resolve().parent / "assets" / filename)
    candidates.append(Path.cwd() / "assets" / filename)
    candidates.append(Path(sys.executable).parent / "assets" / filename)
    for c in candidates:
        if c.exists():
            return c.as_posix()
    return (Path(__file__).resolve().parent / "assets" / filename).as_posix()


def setup_pin_visibility_toggle(line_edit: QLineEdit):
    """Add a clickable visibility toggle (eye / eye-off icon) inside a password QLineEdit."""
    eye_icon = QIcon(_resolve_asset_path("eye.svg"))
    eye_off_icon = QIcon(_resolve_asset_path("eye_off.svg"))

    action = line_edit.addAction(eye_icon, QLineEdit.ActionPosition.TrailingPosition)
    action.setToolTip("Show PIN")

    def _toggle():
        if line_edit.echoMode() == QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            action.setIcon(eye_off_icon)
            action.setToolTip("Hide PIN")
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            action.setIcon(eye_icon)
            action.setToolTip("Show PIN")

    action.triggered.connect(_toggle)
    return action


class BleChangePinDialog(QDialog):
    """A themed dialog for changing the BLE PIN (Old PIN + New PIN)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._old_pin = ""
        self._new_pin = ""

        is_light = prefers_light_theme()
        colors = get_theme_tokens(is_light)

        self.setWindowTitle("Change BLE PIN")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setMinimumWidth(420)
        self.setMinimumHeight(200)

        headline = QLabel("Change BLE PIN")
        headline.setStyleSheet(f"color:{colors['text_primary']}; font-size: 13.5pt; font-weight: 800;")

        info_lbl = QLabel("Enter your current PIN and the new PIN you'd like to set.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color:{colors['text_muted']}; font-size: 11pt; font-weight: 600;")

        self.old_pin_input = QLineEdit()
        self.old_pin_input.setPlaceholderText("Current PIN")
        self.old_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_pin_toggle = setup_pin_visibility_toggle(self.old_pin_input)

        self.new_pin_input = QLineEdit()
        self.new_pin_input.setPlaceholderText("New PIN")
        self.new_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pin_toggle = setup_pin_visibility_toggle(self.new_pin_input)

        change_btn = QPushButton("Change")
        change_btn.setObjectName("yesBtn")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("noBtn")

        def _accept():
            old = self.old_pin_input.text().strip()
            new = self.new_pin_input.text().strip()
            if not old or not new:
                return  # Don't accept if fields are empty
            self._old_pin = old
            self._new_pin = new
            self.accept()

        change_btn.clicked.connect(_accept)
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(colors['spacing_lg'])
        btn_row.addStretch(1)
        btn_row.addWidget(change_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            colors['layout_margin_lg'],
            colors['layout_margin_lg'],
            colors['layout_margin_lg'],
            colors['layout_margin_md']
        )
        root.setSpacing(colors['spacing_md'])
        root.addWidget(headline)
        root.addWidget(info_lbl)
        root.addWidget(self.old_pin_input)
        root.addWidget(self.new_pin_input)
        root.addLayout(btn_row)

        self.setStyleSheet(get_dialog_stylesheet(is_light))
        self.adjustSize()
        self.setFixedSize(self.size())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._old_pin = ""
        self._new_pin = ""
        self.reject()
        event.accept()

    @property
    def old_pin(self) -> str:
        return self._old_pin

    @property
    def new_pin(self) -> str:
        return self._new_pin


def _get_settings_dialog_stylesheet(is_light: bool) -> str:
    """Complete, dedicated stylesheet for SettingsDialog ensuring perfect visual hierarchy and rendering."""
    c = get_theme_tokens(is_light)
    bg = "#ffffff" if is_light else "#0f172a"
    card_bg = "#f8fafc" if is_light else "#111827"
    input_bg = "#ffffff" if is_light else "#0b1220"
    border = "#e2e8f0" if is_light else "#334155"
    border_focus = "#ef4444"
    text_pri = "#0f172a" if is_light else "#f1f5f9"
    text_mut = "#64748b" if is_light else "#94a3b8"
    item_hover_bg = "#f1f5f9" if is_light else "#1e293b"
    item_hover_text = "#0f172a" if is_light else "#ffffff"
    item_sel_bg = "#fef2f2" if is_light else "#1e293b"
    item_sel_text = "#dc2626" if is_light else "#ffffff"

    return f"""
        QDialog {{
            background-color: {bg};
            color: {text_pri};
            border: none;
        }}
        QLabel {{
            background: transparent;
        }}
        QLineEdit {{
            font-size: 10pt;
            padding: 7px 11px;
            border: 1px solid {border};
            border-radius: 6px;
            background-color: {input_bg};
            color: {text_pri};
        }}
        QLineEdit:focus {{
            border: 1px solid {border_focus};
        }}
        QLineEdit:disabled {{
            background-color: {card_bg};
            color: {text_mut};
            border-color: {border};
        }}
        QListWidget {{
            background-color: {input_bg};
            border: 1px solid {border};
            border-radius: 6px;
            color: {text_pri};
            font-size: 12px;
            font-family: Consolas, 'Courier New', monospace;
            padding: 4px;
            outline: none;
        }}
        QListWidget:disabled {{
            background-color: {card_bg};
            color: {text_mut};
            border-color: {border};
        }}
        QListWidget::item {{
            padding: 6px 10px;
            border-radius: 4px;
            border: none;
            outline: none;
            color: {text_pri};
        }}
        QListWidget::item:hover {{
            background-color: {item_hover_bg};
            color: {item_hover_text};
        }}
        QListWidget::item:selected {{
            background-color: {item_sel_bg};
            color: {item_sel_text};
            border-left: 3px solid #ef4444;
            outline: none;
        }}
        QRadioButton {{
            font-size: 13px;
            font-weight: 500;
            color: {text_pri};
            spacing: 10px;
            padding: 4px 0px;
            outline: none;
        }}
        QRadioButton:hover {{
            color: {text_pri};
        }}
        QRadioButton::indicator {{
            width: 14px;
            height: 14px;
            border: 2px solid {border};
            border-radius: 9px;
            background-color: transparent;
        }}
        QRadioButton::indicator:hover {{
            border-color: #94a3b8;
        }}
        QRadioButton::indicator:checked {{
            border: 2px solid #ef4444;
            background: qradialgradient(cx:0.5, cy:0.5, radius:0.45, fx:0.5, fy:0.5, stop:0 #ef4444, stop:0.55 #ef4444, stop:0.6 transparent, stop:1 transparent);
        }}
        QPushButton#actionBtn {{
            background-color: {card_bg};
            color: {text_pri};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 7px 14px;
            font-size: 9.5pt;
            font-weight: 600;
            min-height: 16px;
        }}
        QPushButton#actionBtn:hover {{
            background-color: {border};
            color: {text_pri};
        }}
        QPushButton#actionBtn:pressed {{
            background-color: {card_bg};
        }}
        QPushButton#actionBtn:disabled {{
            background-color: {bg};
            border-color: {border};
            color: {text_mut};
        }}
        QPushButton#saveBtn {{
            background-color: #ef4444;
            color: #ffffff;
            border: none;
            border-radius: 7px;
            padding: 8px 22px;
            font-size: 10pt;
            font-weight: 700;
            min-width: 100px;
        }}
        QPushButton#saveBtn:hover {{
            background-color: #dc2626;
        }}
        QPushButton#saveBtn:pressed {{
            background-color: #b91c1c;
        }}
        QPushButton#cancelBtn {{
            background-color: {card_bg};
            color: {text_mut};
            border: 1px solid {border};
            border-radius: 7px;
            padding: 8px 18px;
            font-size: 10pt;
            font-weight: 600;
            min-width: 80px;
        }}
        QPushButton#cancelBtn:hover {{
            background-color: {border};
            color: {text_pri};
        }}
    """


class SettingsDialog(QDialog):
    """
    Polished, secure Settings dialog providing:
    1. Extension API key inspection and copy with visible Show/Hide toggle.
    2. Dynamic CORS policy configuration (Allowlist mode vs Allow All mode).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        from config import config
        self.config = config

        is_light = prefers_light_theme()
        colors = get_theme_tokens(is_light)

        self.setWindowTitle("Settings")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 18)
        root.setSpacing(14)

        headline = QLabel("Settings")
        headline.setStyleSheet(f"color:{colors['text_primary']}; font-size: 14pt; font-weight: 800; padding: 2px 0px;")
        root.addWidget(headline)

        # ── 1. Extension API Key Section ──
        key_section_lbl = QLabel("Extension API Key")
        key_section_lbl.setStyleSheet(f"color:{colors['text_primary']}; font-size: 11pt; font-weight: 700; padding: 2px 0px;")
        root.addWidget(key_section_lbl)

        key_desc_lbl = QLabel("Authenticate the browser extension with this connector.")
        key_desc_lbl.setStyleSheet(f"color:{colors['text_muted']}; font-size: 9pt; padding: 0px 0px 2px 0px;")
        root.addWidget(key_desc_lbl)

        key_row = QHBoxLayout()
        key_row.setSpacing(10)

        self.btn_copy_key = QPushButton("Copy Key")
        self.btn_copy_key.setObjectName("actionBtn")
        self.btn_copy_key.clicked.connect(self._copy_key)
        key_row.addWidget(self.btn_copy_key)

        self.btn_regenerate_key = QPushButton("Regenerate Key")
        self.btn_regenerate_key.setObjectName("actionBtn")
        self.btn_regenerate_key.clicked.connect(self._regenerate_key)
        key_row.addWidget(self.btn_regenerate_key)
        key_row.addStretch()

        root.addLayout(key_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {colors.get('border', '#334155')}; max-height: 1px;")
        root.addWidget(sep)

        # ── 2. CORS & Web Access Policy Section ──
        cors_lbl = QLabel("Web Access & CORS Policy")
        cors_lbl.setStyleSheet(f"color:{colors['text_primary']}; font-size: 10.5pt; font-weight: 700;")
        root.addWidget(cors_lbl)

        self.radio_allowlist = QRadioButton("Restricted Allowlist (Recommended)")
        self.radio_allow_all = QRadioButton("Allow All Origins (Custom POS / Local Dev)")
        self.cors_group = QButtonGroup(self)
        self.cors_group.addButton(self.radio_allowlist)
        self.cors_group.addButton(self.radio_allow_all)

        current_mode = self.config.cors_mode
        if current_mode == "allow_all":
            self.radio_allow_all.setChecked(True)
        else:
            self.radio_allowlist.setChecked(True)

        self.radio_allowlist.toggled.connect(self._on_cors_mode_changed)

        root.addWidget(self.radio_allowlist)
        root.addWidget(self.radio_allow_all)

        # Origins editor (showing 5-6 rows comfortably)
        self.origins_list = QListWidget()
        self.origins_list.setMinimumHeight(175)
        self.origins_list.setMaximumHeight(210)
        for origin in self.config.cors_allowed_origins:
            self.origins_list.addItem(origin)
        root.addWidget(self.origins_list)

        add_origin_row = QHBoxLayout()
        add_origin_row.setSpacing(8)
        self.new_origin_input = QLineEdit()
        self.new_origin_input.setPlaceholderText("https://your-custom-pos.com")
        add_origin_row.addWidget(self.new_origin_input, 1)

        self.btn_add_origin = QPushButton("Add")
        self.btn_add_origin.setObjectName("actionBtn")
        self.btn_add_origin.clicked.connect(self._add_origin)
        add_origin_row.addWidget(self.btn_add_origin)

        self.btn_remove_origin = QPushButton("Remove Selected")
        self.btn_remove_origin.setObjectName("actionBtn")
        self.btn_remove_origin.clicked.connect(self._remove_origin)
        add_origin_row.addWidget(self.btn_remove_origin)
        root.addLayout(add_origin_row)

        self._on_cors_mode_changed(self.radio_allowlist.isChecked())

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setObjectName("saveBtn")
        self.btn_save.clicked.connect(self._save_and_close)
        btn_row.addWidget(self.btn_save)
        root.addLayout(btn_row)

        self.setStyleSheet(_get_settings_dialog_stylesheet(is_light))
        self.adjustSize()

    def _regenerate_key(self):
        prompt = ModernPromptDialog(
            parent=self,
            title="Regenerate API Key",
            headline_text="Regenerate Extension API Key?",
            info_text=(
                "Generating a new API key will invalidate the current key. "
                "You will need to update the key in the browser extension settings. "
                "Are you sure you want to continue?"
            ),
        )
        prompt.exec()
        if not prompt.is_accepted:
            return

        self.config.regenerate_api_key()
        self.btn_regenerate_key.setText("Key Regenerated!")
        QTimer.singleShot(2000, lambda: self.btn_regenerate_key.setText("Regenerate Key"))

    def _on_cors_mode_changed(self, is_allowlist_checked: bool):
        self.origins_list.setEnabled(is_allowlist_checked)
        self.new_origin_input.setEnabled(is_allowlist_checked)
        self.btn_add_origin.setEnabled(is_allowlist_checked)
        self.btn_remove_origin.setEnabled(is_allowlist_checked)

    def _copy_key(self):
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self.config.api_key or "")
            self.btn_copy_key.setText("Copied!")
            QTimer.singleShot(2000, lambda: self.btn_copy_key.setText("Copy Key"))

    def _add_origin(self):
        new_org = self.new_origin_input.text().strip().rstrip("/")
        if not new_org:
            return
        # Avoid duplicate entries
        for i in range(self.origins_list.count()):
            if self.origins_list.item(i).text() == new_org:
                return
        self.origins_list.addItem(new_org)
        self.new_origin_input.clear()

    def _remove_origin(self):
        for item in self.origins_list.selectedItems():
            self.origins_list.takeItem(self.origins_list.row(item))

    def _save_and_close(self):
        prompt = ModernPromptDialog(
            parent=self,
            title="Save Settings",
            headline_text="Save Configuration Changes?",
            info_text="Are you sure you want to save the updated allowed origins policy?",
        )
        prompt.exec()
        if not prompt.is_accepted:
            return

        mode = "allow_all" if self.radio_allow_all.isChecked() else "allowlist"
        origins = []
        for i in range(self.origins_list.count()):
            origins.append(self.origins_list.item(i).text())
        self.config.set_cors_settings(mode, origins)
        self.accept()
