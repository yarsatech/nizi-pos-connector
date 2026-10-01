from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
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
