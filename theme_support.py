"""
Shared theme helpers for light/dark preference and shared OTA color tokens.
"""

from __future__ import annotations

import os
import platform
import subprocess


def _windows_prefers_light_theme() -> bool:
    try:
        import winreg

        personalize = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, personalize) as key:
            apps_use_light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return int(apps_use_light) == 1
    except Exception:
        return False


def _macos_prefers_dark_theme() -> bool:
    try:
        # Returns "Dark" in dark mode and non-zero when unset.
        res = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode == 0 and "dark" in (res.stdout or "").strip().lower()
    except Exception:
        return False


def _linux_prefers_dark_theme() -> bool:
    # Heuristic; desktop environments differ.
    for key in ("GTK_THEME", "QT_STYLE_OVERRIDE", "COLORFGBG"):
        val = (os.environ.get(key) or "").lower()
        if "dark" in val:
            return True
    return False


def prefers_light_theme(*, palette_lightness: int | None = None) -> bool:
    """
    True if the OS/app likely prefers a light theme.
    """
    sys_name = platform.system()
    if sys_name == "Windows":
        return _windows_prefers_light_theme()
    if sys_name == "Darwin":
        return not _macos_prefers_dark_theme()
    if sys_name == "Linux":
        return not _linux_prefers_dark_theme()
    if palette_lightness is not None:
        return palette_lightness > 127
    return True


def ota_theme_colors(is_light: bool) -> dict[str, str]:
    accent = "#ef4444"
    if is_light:
        return {
            "dialog_bg": "#ffffff",
            "text": "#0f172a",
            "muted": "#475569",
            "border": "#e5e7eb",
            "secondary_bg": "#f1f5f9",
            "progress_bg": "#ffffff",
            "progress_bar_bg": "#f1f5f9",
            "chunk": accent,
            "cancel_bg": "#f8fafc",
            "cancel_border": "#e5e7eb",
        }
    return {
        "dialog_bg": "#111827",
        "text": "#e5e7eb",
        "muted": "#cbd5e1",
        "border": "#334155",
        "secondary_bg": "#0f172a",
        "progress_bg": "#0b1220",
        "progress_bar_bg": "#0f172a",
        "chunk": accent,
        "cancel_bg": "#0f172a",
        "cancel_border": "#334155",
    }


def flyout_dark_theme_tokens() -> dict[str, str]:
    """
    Shared dark token map for the TrayFlyout styles.
    """
    return {
        "window_bg": "#0f172a",
        "text_primary": "#e5e7eb",
        "text_muted": "#cbd5e1",
        "card_bg": "#111827",
        "border": "#334155",
        "input_bg": "#0b1220",
        "selection_bg": "#1f2937",
        "placeholder": "#94a3b8",
        "secondary_hover_bg": "#1e293b",
        "secondary_hover_border": "#475569",
        "danger_bg": "#1f1215",
        "danger_text": "#fca5a5",
        "danger_border": "#7f1d1d",
        "warning_bg": "#1a160a",
        "warning_text": "#fcd34d",
        "warning_border": "#a16207",
        "ghost_text": "#94a3b8",
        "ghost_hover_text": "#f87171",
        "radio_border": "#475569",
        "radio_hover_border": "#fca5a5",
    }


def flyout_dark_stylesheet(tokens: dict[str, str] | None = None) -> str:
    c = tokens or flyout_dark_theme_tokens()
    return f"""
QWidget#mainWindow {{ background-color: {c['window_bg']}; }}
QLabel#headerTitle, QLabel#sectionTitle {{ color: {c['text_primary']}; }}
QLabel#statusLabel {{ color: {c['text_primary']}; }}
QLabel#instructionLabel, QLabel#fieldLabel, QLabel#modeLabel {{ color: {c['text_muted']}; }}
QFrame#statusCard {{ background-color: {c['card_bg']}; border: 1px solid {c['border']}; }}
QFrame#separator {{ background-color: {c['border']}; }}
QComboBox, QLineEdit, QTextEdit {{
    background-color: {c['input_bg']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
}}
/* Override light-theme focus rules that set white backgrounds. */
QComboBox:focus, QLineEdit:focus, QTextEdit:focus {{
    background-color: {c['input_bg']};
    border-color: {c['danger_border']};
}}
QComboBox QAbstractItemView {{
    background-color: {c['input_bg']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    selection-background-color: {c['selection_bg']};
    selection-color: {c['text_primary']};
}}
QComboBox QAbstractItemView::item:hover {{ background-color: {c['selection_bg']}; }}
QLineEdit::placeholder {{ color: {c['placeholder']}; }}
QLineEdit::selection {{
    background-color: {c['danger_bg']};
    color: #ffffff;
}}
QTextEdit::selection {{
    background-color: {c['danger_bg']};
    color: #ffffff;
}}
QPushButton#secondaryBtn, QPushButton#disconnectBtn {{
    background-color: {c['window_bg']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
}}
QPushButton#secondaryBtn:hover, QPushButton#disconnectBtn:hover {{
    background-color: {c['secondary_hover_bg']};
    border-color: {c['secondary_hover_border']};
}}
QPushButton#dangerBtn {{ background-color: {c['danger_bg']}; color: {c['danger_text']}; border: 1px solid {c['danger_border']}; }}
QPushButton#warningBtn {{ background-color: {c['warning_bg']}; color: {c['warning_text']}; border: 1px solid {c['warning_border']}; }}
QPushButton#ghostBtn {{ color: {c['ghost_text']}; }}
QPushButton#ghostBtn:hover {{ color: {c['ghost_hover_text']}; }}
QRadioButton {{ color: {c['text_primary']}; }}
QRadioButton::indicator {{ border: 2px solid {c['radio_border']}; background: {c['input_bg']}; }}
QRadioButton::indicator:hover {{ border-color: {c['radio_hover_border']}; }}
QDialog {{ background-color: {c['window_bg']}; }}
"""
