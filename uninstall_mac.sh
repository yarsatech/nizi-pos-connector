#!/bin/bash
# -----------------------------------------------------------------------------
# Nizi POS Connector — macOS Uninstaller
# Stops the application, unloads the LaunchAgent, and removes all app files,
# autostart configurations, and saved configuration/API keys.
# -----------------------------------------------------------------------------

set -e

echo "============================================="
echo " Uninstalling Nizi POS Connector (macOS)"
echo "============================================="

# 1. Terminate running instances
echo "Stopping running instances..."
pkill -f "NiziPOSConnector" 2>/dev/null || true

# 2. Unload & remove LaunchAgent
PLIST_PATH="/Library/LaunchAgents/com.yarsatech.niziposconnector.plist"
if [ -f "$PLIST_PATH" ]; then
    echo "Unloading LaunchAgent..."
    CURRENT_USER=$(stat -f '%Su' /dev/console 2>/dev/null || echo "$USER")
    sudo -u "$CURRENT_USER" launchctl unload "$PLIST_PATH" 2>/dev/null || true
    echo "Removing LaunchAgent plist..."
    rm -f "$PLIST_PATH"
fi

# 3. Remove login item
if [ -n "$CURRENT_USER" ]; then
    echo "Removing Login Item..."
    sudo -u "$CURRENT_USER" osascript -e 'tell application "System Events" to delete (every login item whose name is "NiziPOSConnector")' 2>/dev/null || true
fi

# 4. Remove /Applications bundle
if [ -d "/Applications/NiziPOSConnector.app" ]; then
    echo "Removing /Applications/NiziPOSConnector.app..."
    rm -rf "/Applications/NiziPOSConnector.app"
fi

# 5. Remove user configuration, cached settings, and protected API key
# On macOS, platformdirs user_config_dir is: ~/Library/Application Support/Nizi POS Connector
USER_CONFIG_DIR="$HOME/Library/Application Support/Nizi POS Connector"
if [ -d "$USER_CONFIG_DIR" ]; then
    echo "Removing configuration and saved API key ($USER_CONFIG_DIR)..."
    rm -rf "$USER_CONFIG_DIR"
fi

echo "============================================="
echo "✅ Uninstallation complete! All files and keys removed."
echo "============================================="
