from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
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
        
        self.setStyleSheet(get_progress_dialog_stylesheet(is_light))
