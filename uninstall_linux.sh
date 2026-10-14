#!/bin/bash
# -----------------------------------------------------------------------------
# Nizi POS Connector — Linux Uninstaller
# Stops the application, removes binaries from /opt, cleans desktop launchers,
# autostart configurations, and purges user configuration/API keys.
# -----------------------------------------------------------------------------

set -e

echo "============================================="
echo " Uninstalling Nizi POS Connector (Linux)"
echo "============================================="

# 1. Terminate running instances
echo "Stopping running instances..."
pkill -f "NiziPOSConnector" 2>/dev/null || true

# 2. Remove binaries and symlinks
INSTALL_PREFIX="/opt/NiziPOSConnector"
if [ -d "$INSTALL_PREFIX" ]; then
    echo "Removing $INSTALL_PREFIX..."
    rm -rf "$INSTALL_PREFIX"
fi

if [ -f "/usr/bin/NiziPOSConnector" ]; then
    echo "Removing /usr/bin/NiziPOSConnector..."
    rm -f "/usr/bin/NiziPOSConnector"
fi

# 3. Remove Desktop and Autostart entries
rm -f /usr/share/applications/NiziPOSConnector.desktop
rm -f /etc/xdg/autostart/NiziPOSConnector.desktop
rm -f "$HOME/.config/autostart/NiziPOSConnector.desktop" 2>/dev/null || true
rm -f "$HOME/.local/share/applications/NiziPOSConnector.desktop" 2>/dev/null || true
rm -f /usr/share/icons/hicolor/256x256/apps/NiziPOSConnector.png

# Update desktop databases if tools available
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi

# 4. Remove user configuration, settings, and protected API key
# On Linux, platformdirs user_config_dir is: ~/.config/Nizi POS Connector
USER_CONFIG_DIR="$HOME/.config/Nizi POS Connector"
if [ -d "$USER_CONFIG_DIR" ]; then
    echo "Removing user configuration and saved API key ($USER_CONFIG_DIR)..."
    rm -rf "$USER_CONFIG_DIR"
fi

echo "============================================="
echo "✅ Uninstallation complete! All files and keys removed."
echo "============================================="
