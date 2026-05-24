#!/bin/bash
# -----------------------------------------------------------------------------
# NiziPOS macOS Package Builder
# Builds the macOS .app bundle and packages it into a .pkg installer.
# -----------------------------------------------------------------------------

set -e

# --- 1. Load configuration from config.json ---
if [ ! -f "config.json" ]; then
    echo "ERROR: config.json not found in the current directory."
    exit 1
fi

# Use Python to parse config.json safely
read_config() {
    python3 -c "import json; print(json.load(open('config.json'))['$1'])"
}

APP_FULL_NAME=$(read_config "app_name")
MAIN_EXE_BASENAME=$(read_config "main_exe_basename")

APP_NAME="$MAIN_EXE_BASENAME"
APP_DISPLAY="$APP_FULL_NAME"

# App version can be read from config.json, or passed via second parameter / env var
APP_VERSION=$(read_config "version")
APP_VERSION="${2:-${APP_VERSION:-1.0.0}}"

echo "============================================="
echo " Building macOS Installer for $APP_DISPLAY"
echo " Version: $APP_VERSION"
echo "============================================="

# --- 2. Setup Virtual Environment & Install Dependencies ---
echo "Setting up python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

echo "Upgrading pip and installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# --- 3. Build macOS Native .icns Icon ---
echo "Generating macOS native .icns icon..."
python create_icns.py

# --- 4. Build .app Bundle with PyInstaller ---
echo "Building macOS application bundle with PyInstaller..."
pyinstaller --clean -y build.spec

# Verify build output
APP_BUNDLE_PATH="dist/${APP_NAME}.app"
if [ ! -d "$APP_BUNDLE_PATH" ]; then
    echo "ERROR: PyInstaller failed to generate .app bundle at '$APP_BUNDLE_PATH'"
    exit 1
fi
echo "✅ Successfully built: $APP_BUNDLE_PATH"

# --- 5. Prepare Package Staging Directory ---
echo "Staging files for .pkg installer..."
PKG_ROOT="pkg_staging/pkg_root"
PKG_SCRIPTS="pkg_staging/pkg_scripts"

rm -rf "$PKG_ROOT" "$PKG_SCRIPTS"
mkdir -p "$PKG_ROOT/Applications"
mkdir -p "$PKG_SCRIPTS"

# Copy the .app bundle to /Applications staging dir
cp -R "$APP_BUNDLE_PATH" "$PKG_ROOT/Applications/"

# --- 6. Create postinstall Script for Auto-Start & Immediate Run ---
echo "Generating postinstall script..."
POSTINSTALL_PATH="$PKG_SCRIPTS/postinstall"

cat << 'EOF' > "$POSTINSTALL_PATH"
#!/bin/bash

# Log file for debugging postinstall
LOGFILE="/private/var/log/nizi-pos-connector-postinstall.log"
exec >> "$LOGFILE" 2>&1

echo "--------------------------------------------------"
echo "Starting postinstall script: $(date)"
echo "--------------------------------------------------"

PLIST_PATH="/Library/LaunchAgents/com.yarsatech.niziposconnector.plist"

# 1. Create LaunchAgent for Autostart at login
cat << 'LAUNCHAGENT' > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yarsatech.niziposconnector</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/NiziPOSConnector.app/Contents/MacOS/NiziPOSConnector</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
LAUNCHAGENT

# 2. Fix ownership and permissions (standard for LaunchAgents)
chmod 644 "$PLIST_PATH"
chown root:wheel "$PLIST_PATH"
echo "LaunchAgent created and configured at $PLIST_PATH"

# 3. Determine current logged-in console user
CURRENT_USER=$(stat -f '%Su' /dev/console)
USER_ID=$(id -u "$CURRENT_USER")

echo "Current logged-in user: $CURRENT_USER (UID: $USER_ID)"

# 4. Load agent and launch application immediately in user's GUI session
if [ "$CURRENT_USER" != "loginwindow" ] && [ -n "$CURRENT_USER" ]; then
    # Unload existing launch agent first to avoid duplicate load errors
    echo "Unloading existing LaunchAgent (if any) as $CURRENT_USER..."
    sudo -u "$CURRENT_USER" launchctl unload "$PLIST_PATH" >/dev/null 2>&1
    
    # Load the LaunchAgent in the user's GUI session
    echo "Loading LaunchAgent for $CURRENT_USER..."
    sudo -u "$CURRENT_USER" launchctl load "$PLIST_PATH"
    
    # Add to user's Login Items (Open at Login)
    echo "Adding NiziPOSConnector to Login Items for $CURRENT_USER..."
    sudo -u "$CURRENT_USER" osascript -e 'tell application "System Events" to delete (every login item whose name is "NiziPOSConnector")' >/dev/null 2>&1
    sudo -u "$CURRENT_USER" osascript -e 'tell application "System Events" to make new login item at end with properties {path:"/Applications/NiziPOSConnector.app", name:"NiziPOSConnector", hidden:false}' >/dev/null 2>&1

    # Launch the application immediately
    echo "Launching NiziPOSConnector app for $CURRENT_USER..."
    sudo -u "$CURRENT_USER" open -a "/Applications/NiziPOSConnector.app"
else
    echo "No active GUI session found (user is not logged in). Skipping immediate launch."
fi

echo "Postinstall script finished successfully."
exit 0
EOF

# Make the postinstall script executable
chmod +x "$POSTINSTALL_PATH"

# --- 7. Generate & Customize Component Plist to Disable Bundle Relocation ---
echo "Analyzing bundle components to disable relocation..."
COMPONENTS_PLIST="pkg_staging/components.plist"
pkgbuild --analyze --root "$PKG_ROOT" "$COMPONENTS_PLIST"

# Use python to set BundleIsRelocatable to false for all components
python3 -c "
import plistlib
with open('$COMPONENTS_PLIST', 'rb') as f:
    data = plistlib.load(f)
for item in data:
    if 'BundleIsRelocatable' in item:
        item['BundleIsRelocatable'] = False
with open('$COMPONENTS_PLIST', 'wb') as f:
    plistlib.dump(data, f)
"
echo "Component plist updated. Relocation disabled."

# --- 8. Build PKG Installer Using pkgbuild ---
echo "Building the final .pkg installer..."
OUTPUT_PKG="dist/${APP_NAME}-Installer-${APP_VERSION}-macOS.pkg"

pkgbuild --root "$PKG_ROOT" \
         --component-plist "$COMPONENTS_PLIST" \
         --scripts "$PKG_SCRIPTS" \
         --identifier "com.yarsatech.nizi-pos-connector" \
         --version "$APP_VERSION" \
         --install-location "/" \
         "$OUTPUT_PKG"

echo "============================================="
echo "✅ Build complete!"
echo "Package located at: $OUTPUT_PKG"
echo "============================================="
