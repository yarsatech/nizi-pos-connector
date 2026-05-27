"""
Shared theme helpers for light/dark preference and shared OTA/Web/UI color tokens.
"""

from __future__ import annotations

import os
import platform
import subprocess
from typing import Optional


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
    for key in ("GTK_THEME", "QT_STYLE_OVERRIDE", "COLORFGBG"):
        val = (os.environ.get(key) or "").lower()
        if "dark" in val:
            return True
    return False


def prefers_light_theme(*, palette_lightness: Optional[int] = None) -> bool:
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


def get_theme_tokens(is_light: bool) -> dict[str, str | int]:
    """Centralized tokens for all UI components (PyQt app + Web server)."""
    # Common structural metrics
    metrics = {
        "border_radius_md": "6px",
        "border_radius_lg": "12px",
        
        "layout_margin_lg": 18,
        "layout_margin_md": 14,
        "spacing_lg": 16,
        "spacing_md": 10,

        # Component metrics
        "border_radius_sm": "4px",
        "font_family": "'Segoe UI', 'Inter', 'Arial', sans-serif",
        "font_size_base": "10pt",
        "font_size_sm": "9pt",
        "font_size_xs": "8pt",
        "font_size_lg": "11pt",
        "font_size_xl": "16pt",
        "dropdown_padding": "2px",
        "dropdown_item_padding": "2px 6px",
        "dropdown_item_margin": "0px",
        "dropdown_item_min_height": "20px",
        "input_padding": "6px 12px",
        "button_padding": "8px 16px",
    }
    
    if is_light:
        colors = {
            "window_bg": "#ffffff",
            "card_bg": "#f9fafb",
            "card_bg_hover": "#f3f4f6",
            "input_bg": "#ffffff",
            "border": "#e5e7eb",
            "border_active": "#fca5a5",
            "text_primary": "#111827",
            "text_secondary": "#374151",
            "text_muted": "#6b7280",
            "selection_bg": "#f3f4f6",
            "selection_text": "#ef4444",
            "placeholder": "#9ca3af",
            "secondary_hover_bg": "#f3f4f6",
            "secondary_hover_border": "#fca5a5",
            
            "accent": "#ef4444",
            "accent_bright": "#dc2626",
            "accent_pressed": "#b91c1c",
            "accent_disabled": "#7f1d1d",
            "accent_glow": "rgba(239, 68, 68, 0.3)",
            
            "success": "#10b981",
            "success_text": "#16a34a",
            "success_bg": "rgba(16, 185, 129, 0.1)",
            
            "danger": "#ef4444",
            "danger_bg": "#fef2f2",
            "danger_text": "#dc2626",
            "danger_border": "#fecaca",
            
            "warning": "#f59e0b",
            "warning_bg": "#fffbeb",
            "warning_text": "#d97706",
            "warning_border": "#fde68a",
            
            "info": "#3b82f6",
            "info_bg": "rgba(59, 130, 246, 0.1)",
            
            "ghost_text": "#9ca3af",
            "ghost_hover_text": "#ef4444",
            "radio_border": "#d1d5db",
            "radio_hover_border": "#fca5a5",
            
            "progress_bg": "#ffffff",
            "progress_bar_bg": "#f1f5f9",
            
            "dialog_bg": "#ffffff",
        }
    else:
        colors = {
            "window_bg": "#0f172a",
            "card_bg": "#111827",
            "card_bg_hover": "#1e293b",
            "input_bg": "#0b1220",
            "border": "#334155",
            "border_active": "#475569",
            "text_primary": "#e5e7eb",
            "text_secondary": "#cbd5e1",
            "text_muted": "#94a3b8",
            "selection_bg": "#1f2937",
            "selection_text": "#e5e7eb",
            "placeholder": "#94a3b8",
            "secondary_hover_bg": "#1e293b",
            "secondary_hover_border": "#475569",
            
            "accent": "#ef4444",
            "accent_bright": "#f87171",
            "accent_pressed": "#b91c1c",
            "accent_disabled": "#7f1d1d",
            "accent_glow": "rgba(239, 68, 68, 0.3)",
            
            "success": "#10b981",
            "success_text": "#10b981",
            "success_bg": "rgba(16, 185, 129, 0.1)",
            
            "danger": "#ef4444",
            "danger_bg": "#1f1215",
            "danger_text": "#fca5a5",
            "danger_border": "#7f1d1d",
            
            "warning": "#f59e0b",
            "warning_bg": "#1a160a",
            "warning_text": "#fcd34d",
            "warning_border": "#a16207",
            
            "info": "#3b82f6",
            "info_bg": "rgba(59, 130, 246, 0.1)",
            
            "ghost_text": "#94a3b8",
            "ghost_hover_text": "#f87171",
            "radio_border": "#475569",
            "radio_hover_border": "#fca5a5",
            
            "progress_bg": "#0b1220",
            "progress_bar_bg": "#0f172a",
            
            "dialog_bg": "#111827",
        }
        
    return {**metrics, **colors}


def get_flyout_stylesheet(is_light: bool, arrow_path: str) -> str:
    """Generates the comprehensive PyQt stylesheet for the TrayFlyout."""
    c = get_theme_tokens(is_light)
    return f"""
* {{ font-family: {c['font_family']}; }}
QWidget#mainWindow {{ background-color: {c['window_bg']}; }}
QLabel#headerTitle {{ font-size: {c['font_size_xl']}; font-weight: 700; color: {c['text_primary']}; }}
QLabel#versionLabel {{ font-size: {c['font_size_sm']}; font-weight: 600; color: {c['text_muted']}; }}
QLabel#statusLabel {{ font-size: {c['font_size_lg']}; font-weight: 600; background: transparent; border: none; color: {c['text_primary']}; }}
QLabel#statusLabel[state="connected"] {{ color: {c['success_text']}; }}
QLabel#statusLabel[state="disconnected"] {{ color: {c['text_muted']}; }}
QLabel#instructionLabel {{ font-size: {c['font_size_sm']}; color: {c['text_muted']}; background: transparent; border: none; }}
QLabel#sectionTitle {{ font-size: {c['font_size_base']}; font-weight: 600; color: {c['text_primary']}; background: transparent; }}
QLabel#fieldLabel {{ font-size: {c['font_size_xs']}; color: {c['text_muted']}; font-weight: 500; margin-top: 12px; margin-bottom: 0px; background: transparent; }}
QLabel#modeLabel {{ font-size: {c['font_size_sm']}; color: {c['text_secondary']}; font-weight: 600; margin-top: 0px; background: transparent; }}
QFrame#statusCard {{ background-color: {c['card_bg']}; border: 1px solid {c['border']}; border-radius: {c['border_radius_lg']}; }}
QFrame#separator {{ background-color: {c['border']}; max-height: 1px; border: none; }}
QLabel#imagePreview {{ border: 2px dashed {c['border']}; border-radius: {c['border_radius_md']}; background-color: {c['input_bg']}; color: {c['placeholder']}; font-weight: 500; }}
QTextEdit#logDisplay {{ background-color: {c['input_bg']}; border: 1px solid {c['border']}; font-family: monospace; color: {c['text_primary']}; }}
QComboBox {{
    font-size: {c['font_size_base']}; padding: {c['input_padding']}; border: 1px solid {c['border']};
    border-radius: {c['border_radius_md']}; background-color: {c['input_bg']}; color: {c['text_primary']}; min-height: 20px;
}}
QComboBox:hover {{ border-color: {c['border_active']}; }}
QComboBox:focus {{ border-color: {c['accent']}; background-color: {c['input_bg']}; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 30px; border: none; background: transparent; }}
QComboBox::down-arrow {{ image: url({arrow_path}); width: 14px; height: 14px; }}
QComboBox QAbstractItemView {{
    font-size: {c['font_size_base']}; border: 1px solid {c['border']};
    background-color: {c['input_bg']}; selection-background-color: {c['selection_bg']}; selection-color: {c['selection_text']};
    outline: 0; padding: {c['dropdown_padding']};
}}
QComboBox QAbstractItemView::item {{
    padding: {c['dropdown_item_padding']}; margin: {c['dropdown_item_margin']}; min-height: {c['dropdown_item_min_height']};
    border-radius: {c['border_radius_sm']}; color: {c['text_primary']};
}}
QComboBox QAbstractItemView::item:hover {{ background-color: {c['selection_bg']}; color: {c['text_primary']}; }}
QComboBox QAbstractItemView::item:selected {{ background-color: {c['danger_bg']}; color: {c['danger_text']}; font-weight: 600; }}
QLineEdit {{
    font-size: {c['font_size_base']}; padding: {c['input_padding']}; border: 1px solid {c['border']};
    border-radius: {c['border_radius_md']}; background-color: {c['input_bg']}; color: {c['text_primary']};
}}
QLineEdit:focus {{ border-color: {c['accent']}; background-color: {c['input_bg']}; }}
QLineEdit::placeholder {{ color: {c['placeholder']}; }}
QLineEdit::selection, QTextEdit::selection {{ background-color: {c['accent']}; color: #ffffff; }}
QTextEdit {{
    font-size: {c['font_size_base']}; padding: {c['input_padding']}; border: 1px solid {c['border']};
    border-radius: {c['border_radius_md']}; background-color: {c['input_bg']}; color: {c['text_primary']};
}}
QTextEdit:focus {{ border-color: {c['accent']}; }}
QPushButton#primaryBtn, QPushButton#connectBtn {{
    font-size: {c['font_size_base']}; padding: {c['button_padding']}; background-color: {c['accent']}; color: #ffffff;
    border: none; border-radius: {c['border_radius_md']}; font-weight: 600;
}}
QPushButton#primaryBtn:hover, QPushButton#connectBtn:hover {{ background-color: {c['accent_bright']}; }}
QPushButton#primaryBtn:pressed, QPushButton#connectBtn:pressed {{ background-color: {c['accent_pressed']}; }}
QPushButton#primaryBtn:disabled, QPushButton#connectBtn:disabled {{ background-color: {c['accent_disabled']}; color: #fee2e2; }}
QPushButton#secondaryBtn, QPushButton#disconnectBtn {{
    font-size: {c['font_size_base']}; padding: {c['button_padding']}; background-color: {c['window_bg']}; color: {c['text_primary']};
    border: 1px solid {c['border']}; border-radius: {c['border_radius_md']}; font-weight: 500;
}}
QPushButton#secondaryBtn:hover, QPushButton#disconnectBtn:hover {{ background-color: {c['secondary_hover_bg']}; border-color: {c['secondary_hover_border']}; }}
QPushButton#dangerBtn {{ font-size: {c['font_size_base']}; padding: {c['button_padding']}; background-color: {c['danger_bg']}; color: {c['danger_text']}; border: 1px solid {c['danger_border']}; border-radius: {c['border_radius_md']}; font-weight: 500; }}
QPushButton#dangerBtn:hover {{ filter: brightness(1.1); }}
QPushButton#warningBtn {{ font-size: {c['font_size_base']}; padding: {c['button_padding']}; background-color: {c['warning_bg']}; color: {c['warning_text']}; border: 1px solid {c['warning_border']}; border-radius: {c['border_radius_md']}; font-weight: 500; }}
QPushButton#warningBtn:hover {{ filter: brightness(1.1); }}
QPushButton#ghostBtn {{ font-size: {c['font_size_sm']}; padding: {c['dropdown_item_padding']}; background: transparent; color: {c['ghost_text']}; border: none; }}
QPushButton#ghostBtn:hover {{ color: {c['ghost_hover_text']}; }}
QRadioButton {{ font-size: {c['font_size_base']}; color: {c['text_primary']}; spacing: 8px; padding: 4px; }}
QRadioButton::indicator {{ width: 18px; height: 18px; border: 2px solid {c['radio_border']}; border-radius: 9px; background: {c['input_bg']}; }}
QRadioButton::indicator:hover {{ border-color: {c['radio_hover_border']}; }}
QRadioButton::indicator:checked {{
    border-color: {c['accent']}; background-color: {c['accent']};
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjUiLz48L3N2Zz4=);
}}
QRadioButton:disabled {{ color: {c['text_muted']}; }}
QRadioButton::indicator:disabled {{ border-color: {c['border']}; background-color: {c['card_bg']}; }}
QSlider::groove:horizontal {{ border-radius: {c['border_radius_sm']}; height: 8px; background: {c['border']}; }}
QSlider::sub-page:horizontal {{ background: {c['accent']}; border-radius: {c['border_radius_sm']}; }}
QSlider::handle:horizontal {{ background: {c['text_primary']}; border: none; width: 16px; margin-top: -4px; margin-bottom: -4px; border-radius: 8px; }}
QSlider::handle:horizontal:hover {{ background: {c['accent']}; }}
QSlider::handle:horizontal:pressed {{ background: {c['accent_pressed']}; }}
QDialog {{ background-color: {c['window_bg']}; }}
    """

def get_dialog_stylesheet(is_light: bool) -> str:
    """Generates the PyQt stylesheet for dialog prompts (like exit and update)."""
    c = get_theme_tokens(is_light)
    return f"""
        QDialog {{
            background-color: {c['dialog_bg']};
            color: {c['text_primary']};
            border: none;
        }}
        QPushButton#yesBtn {{
            background-color: {c['accent']};
            color: #ffffff;
            border: 0px;
            border-radius: 10px;
            padding: 9px 26px;
            font-weight: 800;
            min-width: 120px;
        }}
        QPushButton#noBtn {{
            background-color: {c['card_bg']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 9px 26px;
            font-weight: 800;
            min-width: 120px;
        }}
        QPushButton:pressed {{
            transform: translateY(1px);
        }}
    """

def get_progress_dialog_stylesheet(is_light: bool) -> str:
    """Generates the PyQt stylesheet for progress dialogs (like the OTA download)."""
    c = get_theme_tokens(is_light)
    return f"""
        QProgressDialog {{
            background-color: {c['progress_bg']};
            color: {c['text_primary']};
            border: none;
            padding: 22px;
        }}
        QLabel {{
            color: {c['text_muted']};
            font-size: 14pt;
            font-weight: 800;
            margin-bottom: 10px;
        }}
        QPushButton {{
            border-radius: 12px;
            padding: 10px 26px;
            font-weight: 700;
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            background-color: {c['window_bg']};
        }}
        QProgressBar {{
            height: 16px;
            border-radius: 8px;
            background-color: {c['progress_bar_bg']};
            border: 1px solid {c['border']};
            margin: 8px 0px 18px 0px;
            qproperty-alignment: AlignCenter;
            font-size: 12pt;
            qproperty-textVisible: false;
        }}
        QProgressBar::chunk {{
            border-radius: 6px;
            background-color: {c['accent']};
        }}
    """

def get_web_theme_css(is_light: bool) -> str:
    """Generates the dynamic CSS variables block for the web server."""
    t = get_theme_tokens(is_light)
    # Using RGB hexes as is, for rgba usage web might need actual parsing or just use direct hexes where possible.
    # The existing CSS uses raw hex for most backgrounds.
    return f"""
/* Auto-generated theme tokens from theme_support.py */
:root {{
    --bg-primary: {t['window_bg']};
    --bg-secondary: {t['dialog_bg']};
    --bg-card: {t['card_bg']};
    --bg-card-hover: {t['card_bg_hover']};
    --bg-input: {t['input_bg']};
    --border-color: {t['border']};
    --border-active: {t['border_active']};
    --text-primary: {t['text_primary']};
    --text-secondary: {t['text_secondary']};
    --text-muted: {t['text_muted']};
    --accent: {t['accent']};
    --accent-bright: {t['accent_bright']};
    --accent-glow: {t['accent_glow']};
    --success: {t['success']};
    --success-bg: {t['success_bg']};
    --danger: {t['danger']};
    --danger-bg: {t['danger_bg']};
    --warning: {t['warning']};
    --warning-bg: {t['warning_bg']};
    --info: {t['info']};
    --info-bg: {t['info_bg']};
    --radius: {t['border_radius_lg']};
    --radius-sm: {t['border_radius_md']};
    --shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
    --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}}
"""
