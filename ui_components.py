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
    """A reusable, themed prompt dialog (Confirm/Cancel)."""
    def __init__(self, parent=None, title="Prompt", headline_text="", info_text="", yes_text="Yes", no_text="No", min_width=440, min_height=170):
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

        headline = QLabel(headline_text)
        headline.setStyleSheet(f"color:{colors['text_primary']}; font-size: 13.5pt; font-weight: 800;")

        info_lbl = QLabel(info_text)
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color:{colors['text_muted']}; font-size: 9.5pt; line-height: 1.4;")

        yes_btn = QPushButton(yes_text)
        yes_btn.setObjectName("yesBtn")
        yes_btn.setFixedHeight(36)
        yes_btn.setMinimumWidth(85)

        no_btn = QPushButton(no_text)
        no_btn.setObjectName("noBtn")
        no_btn.setFixedHeight(36)
        no_btn.setMinimumWidth(80)

        def _accept():
            self._accepted = True
            self.accept()

        yes_btn.clicked.connect(_accept)
        no_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)
        btn_row.addWidget(no_btn)
        btn_row.addWidget(yes_btn)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(headline)
        root.addWidget(info_lbl)
        root.addSpacing(10)
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

        info_lbl = QLabel("Enter the current PIN and the new 6-digit PIN.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color:{colors['text_muted']}; font-size: 9.5pt;")

        self.old_pin_input = QLineEdit()
        self.old_pin_input.setPlaceholderText("Current PIN")
        self.old_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_pin_input.setFixedHeight(34)
        self.old_pin_toggle = setup_pin_visibility_toggle(self.old_pin_input)

        self.new_pin_input = QLineEdit()
        self.new_pin_input.setPlaceholderText("New PIN")
        self.new_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pin_input.setFixedHeight(34)
        self.new_pin_toggle = setup_pin_visibility_toggle(self.new_pin_input)

        change_btn = QPushButton("Change")
        change_btn.setObjectName("yesBtn")
        change_btn.setFixedHeight(36)
        change_btn.setMinimumWidth(85)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("noBtn")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setMinimumWidth(80)

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
        btn_row.setSpacing(10)
        btn_row.addStretch(1)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(change_btn)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(headline)
        root.addWidget(info_lbl)
        root.addWidget(self.old_pin_input)
        root.addWidget(self.new_pin_input)
        root.addSpacing(8)
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


class CustomApiKeyDialog(QDialog):
    """Themed dialog for setting a user-defined custom API key."""
    def __init__(self, parent=None, current_key: str = ""):
        super().__init__(parent)
        self._accepted = False
        self._custom_key = ""

        is_light = prefers_light_theme()
        colors = get_theme_tokens(is_light)

        self.setWindowTitle("Custom API Key")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setMinimumWidth(500)

        headline = QLabel("Custom API Key")
        headline.setStyleSheet(f"color:{colors['text_primary']}; font-size: 13.5pt; font-weight: 800;")

        info_lbl = QLabel(
            "Configure a merchant-managed secret key for this connector terminal. "
            "Must be 16–32 characters with verified entropy, avoiding repetitive or sequential character patterns."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color:{colors['text_muted']}; font-size: 9.5pt;")

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Enter custom key (16–32 characters)")
        self.key_input.setMaxLength(32)
        self.key_input.setFixedHeight(34)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #ef4444; font-size: 9pt; font-weight: 600;")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.hide()

        save_btn = QPushButton("Save Key")
        save_btn.setObjectName("saveBtn")
        save_btn.setFixedHeight(36)
        save_btn.setMinimumWidth(95)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setMinimumWidth(80)

        from security import validate_custom_api_key

        def _on_save():
            val = self.key_input.text().strip()
            try:
                validate_custom_api_key(val)
            except ValueError as e:
                self.error_lbl.setText(str(e))
                self.error_lbl.show()
                return
            self._custom_key = val
            self._accepted = True
            self.accept()

        save_btn.clicked.connect(_on_save)
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(headline)
        root.addWidget(info_lbl)
        root.addWidget(self.key_input)
        root.addWidget(self.error_lbl)
        root.addSpacing(8)
        root.addLayout(btn_row)

        self.setStyleSheet(_get_settings_dialog_stylesheet(is_light))
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

    @property
    def custom_key(self) -> str:
        return self._custom_key


def _get_settings_dialog_stylesheet(is_light: bool) -> str:
    """Delegates to the centralized, unified Material Design dialog stylesheet."""
    return get_dialog_stylesheet(is_light)


class SettingsDialog(QDialog):
    """
    Polished, secure Settings dialog providing:
    1. API key inspection, regeneration, and custom merchant key configuration.
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
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)

        headline = QLabel("Settings")
        headline.setStyleSheet(f"color:{colors['text_primary']}; font-size: 13.5pt; font-weight: 800; padding: 0px 0px 2px 0px;")
        root.addWidget(headline)

        # ── 1. API Key Section ──
        key_header_row = QHBoxLayout()
        key_header_row.setContentsMargins(0, 0, 0, 0)
        key_header_row.setSpacing(8)

        key_section_lbl = QLabel("API Key")
        key_section_lbl.setStyleSheet(f"color:{colors['text_primary']}; font-size: 11pt; font-weight: 700;")
        key_header_row.addWidget(key_section_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        key_header_row.addStretch()

        self.key_badge = QLabel()
        self.key_badge.setObjectName("keyBadge")
        key_header_row.addWidget(self.key_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(key_header_row)

        key_desc_lbl = QLabel("Authentication credential for connected applications and browser extensions.")
        key_desc_lbl.setStyleSheet(f"color:{colors['text_muted']}; font-size: 9pt;")
        root.addWidget(key_desc_lbl)

        # Primary Standard Actions Row (Auto-Generated 256-bit Key)
        key_primary_row = QHBoxLayout()
        key_primary_row.setSpacing(8)

        self.btn_copy_key = QPushButton("Copy Key")
        self.btn_copy_key.setObjectName("tonalActionBtn")
        self.btn_copy_key.setFixedHeight(34)
        self.btn_copy_key.setIcon(QIcon(_resolve_asset_path("icons/content_copy.svg")))
        self.btn_copy_key.clicked.connect(self._copy_key)
        key_primary_row.addWidget(self.btn_copy_key, 2)

        self.btn_regenerate_key = QPushButton("Regenerate Key")
        self.btn_regenerate_key.setObjectName("actionBtn")
        self.btn_regenerate_key.setFixedHeight(34)
        self.btn_regenerate_key.setIcon(QIcon(_resolve_asset_path("icons/refresh.svg")))
        self.btn_regenerate_key.clicked.connect(self._regenerate_key)
        key_primary_row.addWidget(self.btn_regenerate_key, 1)

        root.addLayout(key_primary_row)

        # ── Advanced / Legacy Integration Section (Lower Hierarchy) ──
        legacy_card = QFrame()
        legacy_card.setObjectName("legacyCard")
        legacy_card.setStyleSheet(
            f"QFrame#legacyCard {{ "
            f"background-color: {'rgba(241, 245, 249, 0.6)' if is_light else 'rgba(30, 41, 59, 0.35)'}; "
            f"border: 1px dashed {'#cbd5e1' if is_light else '#334155'}; "
            f"border-radius: 6px; padding: 8px 10px; }}"
        )
        legacy_layout = QVBoxLayout(legacy_card)
        legacy_layout.setContentsMargins(10, 8, 10, 8)
        legacy_layout.setSpacing(6)

        legacy_header_row = QHBoxLayout()
        legacy_title = QLabel("Third-Party Integrations")
        legacy_title.setStyleSheet(f"color:{colors['text_secondary']}; font-size: 8.5pt; font-weight: 700;")
        legacy_header_row.addWidget(legacy_title)
        legacy_header_row.addStretch()
        legacy_layout.addLayout(legacy_header_row)

        legacy_desc = QLabel(
            "Standard merchants use the auto-generated 256-bit token. "
            "Configure a custom key only if your third-party software requires a fixed pre-shared credential."
        )
        legacy_desc.setWordWrap(True)
        legacy_desc.setStyleSheet(f"color:{colors['text_muted']}; font-size: 8pt; line-height: 1.3;")
        legacy_layout.addWidget(legacy_desc)

        legacy_btn_row = QHBoxLayout()
        legacy_btn_row.setSpacing(8)

        self.btn_set_custom_key = QPushButton("Set Custom Key...")
        self.btn_set_custom_key.setObjectName("subtleActionBtn")
        self.btn_set_custom_key.setIcon(QIcon(_resolve_asset_path("icons/key.svg")))
        self.btn_set_custom_key.setToolTip("Configure a custom secret key for third-party integrations")
        self.btn_set_custom_key.setFixedHeight(30)
        self.btn_set_custom_key.clicked.connect(self._set_custom_key)
        legacy_btn_row.addWidget(self.btn_set_custom_key)

        self.btn_revert_auto_key = QPushButton("Revert to Auto Key")
        self.btn_revert_auto_key.setObjectName("subtleActionBtn")
        self.btn_revert_auto_key.setIcon(QIcon(_resolve_asset_path("icons/refresh.svg")))
        self.btn_revert_auto_key.setFixedHeight(30)
        self.btn_revert_auto_key.clicked.connect(self._revert_to_auto_key)
        legacy_btn_row.addWidget(self.btn_revert_auto_key)
        legacy_btn_row.addStretch()

        legacy_layout.addLayout(legacy_btn_row)
        root.addWidget(legacy_card)

        # Separator
        border_col = colors.get('border', '#334155')
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {border_col}; border: none; margin: 4px 0px;")
        root.addWidget(sep)

        # ── 2. CORS & Web Access Policy Section ──
        cors_lbl = QLabel("Web Access & CORS Policy")
        cors_lbl.setStyleSheet(f"color:{colors['text_primary']}; font-size: 11pt; font-weight: 700;")
        root.addWidget(cors_lbl)

        self.radio_allowlist = QRadioButton("Restricted Allowlist (Recommended)")
        self.radio_allow_all = QRadioButton("Allow All Origins (Custom Applications / Local Dev)")
        self.cors_group = QButtonGroup(self)
        self.cors_group.addButton(self.radio_allowlist)
        self.cors_group.addButton(self.radio_allow_all)

        current_mode = self.config.cors_mode
        if current_mode == "allow_all":
            self.radio_allow_all.setChecked(True)
        else:
            self.radio_allowlist.setChecked(True)

        self.radio_allowlist.toggled.connect(self._on_cors_mode_changed)

        radio_layout = QVBoxLayout()
        radio_layout.setSpacing(6)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.addWidget(self.radio_allowlist)
        radio_layout.addWidget(self.radio_allow_all)
        root.addLayout(radio_layout)

        # Origins editor (showing 5-6 rows comfortably)
        self.origins_list = QListWidget()
        self.origins_list.setMinimumHeight(150)
        self.origins_list.setMaximumHeight(180)
        for origin in self.config.cors_allowed_origins:
            self.origins_list.addItem(origin)
        root.addWidget(self.origins_list)

        add_origin_row = QHBoxLayout()
        add_origin_row.setSpacing(8)
        self.new_origin_input = QLineEdit()
        self.new_origin_input.setPlaceholderText("https://your-custom-pos.com")
        self.new_origin_input.setFixedHeight(34)
        add_origin_row.addWidget(self.new_origin_input, 1)

        self.btn_add_origin = QPushButton("Add")
        self.btn_add_origin.setObjectName("actionBtn")
        self.btn_add_origin.setFixedHeight(34)
        self.btn_add_origin.setMinimumWidth(70)
        self.btn_add_origin.clicked.connect(self._add_origin)
        add_origin_row.addWidget(self.btn_add_origin)

        self.btn_remove_origin = QPushButton("Remove Selected")
        self.btn_remove_origin.setObjectName("actionBtn")
        self.btn_remove_origin.setFixedHeight(34)
        self.btn_remove_origin.setMinimumWidth(130)
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
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setMinimumWidth(85)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setObjectName("saveBtn")
        self.btn_save.setFixedHeight(36)
        self.btn_save.setMinimumWidth(115)
        self.btn_save.clicked.connect(self._save_and_close)
        btn_row.addWidget(self.btn_save)
        root.addSpacing(8)
        root.addLayout(btn_row)

        self.setStyleSheet(_get_settings_dialog_stylesheet(is_light))
        self._update_key_badge()
        self.adjustSize()

    def _update_key_badge(self):
        is_custom = getattr(self.config, "is_custom_api_key", False)
        if hasattr(self, "btn_revert_auto_key"):
            self.btn_revert_auto_key.setVisible(is_custom)
        if is_custom:
            self.key_badge.setText("● Active Key: Custom Merchant Key")
            self.key_badge.setStyleSheet(
                "color: #10b981; font-size: 8.5pt; font-weight: 700; "
                "background-color: rgba(16, 185, 129, 0.12); "
                "border: 1px solid rgba(16, 185, 129, 0.35); "
                "border-radius: 9px; padding: 2px 8px;"
            )
        else:
            self.key_badge.setText("● Active Key: Auto-Generated (256-bit)")
            self.key_badge.setStyleSheet(
                "color: #38bdf8; font-size: 8.5pt; font-weight: 700; "
                "background-color: rgba(56, 189, 248, 0.12); "
                "border: 1px solid rgba(56, 189, 248, 0.35); "
                "border-radius: 9px; padding: 2px 8px;"
            )

    def _revert_to_auto_key(self):
        prompt = ModernPromptDialog(
            parent=self,
            title="Revert to Auto Key",
            headline_text="Revert to Auto-Generated Key",
            info_text=(
                "Invalidates the active custom merchant key and restores a cryptographically secure "
                "256-bit auto-generated credential."
            ),
            yes_text="Revert Key",
            no_text="Cancel",
        )
        prompt.exec()
        if not prompt.is_accepted:
            return

        self.config.regenerate_api_key()
        self._update_key_badge()
        self.btn_revert_auto_key.setText("Key Restored!")
        QTimer.singleShot(2000, lambda: self.btn_revert_auto_key.setText("Revert to Auto Key"))

    def _regenerate_key(self):
        prompt = ModernPromptDialog(
            parent=self,
            title="Regenerate API Key",
            headline_text="Regenerate API Key",
            info_text=(
                "Invalidates the active API key immediately. "
                "Connected applications and browser extensions must be reconfigured with the newly generated key."
            ),
            yes_text="Regenerate",
            no_text="Cancel",
        )
        prompt.exec()
        if not prompt.is_accepted:
            return

        self.config.regenerate_api_key()
        self._update_key_badge()
        self.btn_regenerate_key.setText("Key Regenerated!")
        QTimer.singleShot(2000, lambda: self.btn_regenerate_key.setText("Regenerate Key"))

    def _set_custom_key(self):
        dlg = CustomApiKeyDialog(self)
        dlg.exec()
        if not (dlg.is_accepted and dlg.custom_key):
            return

        prompt = ModernPromptDialog(
            parent=self,
            title="Custom API Key",
            headline_text="Apply Custom API Key",
            info_text=(
                "Replaces the active API key with the user-defined secret. "
                "Connected applications and browser extensions must be updated to maintain authentication."
            ),
            yes_text="Apply",
            no_text="Cancel",
        )
        prompt.exec()
        if not prompt.is_accepted:
            return

        self.config.set_custom_api_key(dlg.custom_key)
        self._update_key_badge()
        self.btn_set_custom_key.setText("Key Saved!")
        QTimer.singleShot(2000, lambda: self.btn_set_custom_key.setText("Set Custom Key..."))

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
            headline_text="Save Origin Policy",
            info_text="Apply the updated CORS origin policy to incoming local HTTP and WebSocket requests.",
            yes_text="Save",
            no_text="Cancel",
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
