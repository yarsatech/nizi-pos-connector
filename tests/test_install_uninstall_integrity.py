"""
Formal automated test suite verifying installation, packaging, and uninstallation
scripts across Windows, macOS, and Linux targets against ISO 25010 maintainability
and operational safety specifications.
"""

import os
import re
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class TestInstallUninstallIntegrity(unittest.TestCase):
    """Validates installer definitions, uninstaller scripts, and autostart policies."""

    def test_linux_uninstaller_script(self):
        """uninstall_linux.sh must cleanly purge binaries, autostart, and credentials."""
        script_path = BASE_DIR / "uninstall_linux.sh"
        self.assertTrue(script_path.exists(), "uninstall_linux.sh must exist")

        content = script_path.read_text(encoding="utf-8")

        # 1. Process termination
        self.assertIn("pkill", content)
        self.assertIn("NiziPOSConnector", content)

        # 2. Binary cleanup
        self.assertIn("/opt/NiziPOSConnector", content)
        self.assertIn("/usr/bin/NiziPOSConnector", content)

        # 3. Desktop and autostart cleanup
        self.assertIn("/usr/share/applications/NiziPOSConnector.desktop", content)
        self.assertIn("/etc/xdg/autostart/NiziPOSConnector.desktop", content)
        self.assertIn("/usr/share/icons/hicolor", content)

        # 4. User configuration and API key purge
        self.assertIn(".config/Nizi POS Connector", content)

        # 5. Fault-tolerant cleanup (ensures scripts do not abort prematurely on missing files)
        self.assertIn("|| true", content)

    def test_macos_uninstaller_script(self):
        """uninstall_mac.sh must unload LaunchAgents, remove login items, and delete bundle."""
        script_path = BASE_DIR / "uninstall_mac.sh"
        self.assertTrue(script_path.exists(), "uninstall_mac.sh must exist")

        content = script_path.read_text(encoding="utf-8")

        # 1. Process termination
        self.assertIn("pkill", content)
        self.assertIn("NiziPOSConnector", content)

        # 2. LaunchAgent unloading and plist removal
        self.assertIn("launchctl unload", content)
        self.assertIn("com.yarsatech.niziposconnector.plist", content)

        # 3. Login Items removal
        self.assertIn("osascript", content)
        self.assertIn("login item", content)

        # 4. Application bundle removal
        self.assertIn("/Applications/NiziPOSConnector.app", content)

        # 5. User configuration and keychain/API key directory cleanup
        self.assertIn("Library/Application Support/Nizi POS Connector", content)

    def test_windows_inno_setup_installer_specification(self):
        """win_setup.iss must enforce mutual exclusion, admin rights, and clean uninstallation."""
        iss_path = BASE_DIR / "win_setup.iss"
        self.assertTrue(iss_path.exists(), "win_setup.iss must exist")

        content = iss_path.read_text(encoding="utf-8")

        # 1. Application naming and mutual exclusion mutex
        self.assertIn("AppName=Nizi POS Connector", content)
        self.assertIn("AppMutex=NiziPOSConnectorMutex", content)

        # 2. Administrative privileges
        self.assertIn("PrivilegesRequired=admin", content)

        # 3. Output directories
        self.assertIn("OutputDir=dist", content)
        self.assertIn("OutputBaseFilename=NiziPOSConnector-Installer", content)

        # 4. In-place upgrade cleanup ([InstallDelete])
        self.assertIn("[InstallDelete]", content)
        self.assertIn('{app}\\*', content)

        # 5. Uninstallation cleanup of data and encrypted credential store
        self.assertIn("[UninstallDelete]", content)
        self.assertIn('{app}', content)
        self.assertIn('{localappdata}\\Yarsa Tech\\Nizi POS Connector', content)
        self.assertIn('{userappdata}\\Yarsa Tech\\Nizi POS Connector', content)

        # 6. Autostart registry persistence
        self.assertIn('Software\\Microsoft\\Windows\\CurrentVersion\\Run', content)

    def test_build_mac_specification(self):
        """build_mac.sh must disable bundle relocation and configure user LaunchAgent."""
        script_path = BASE_DIR / "build_mac.sh"
        self.assertTrue(script_path.exists(), "build_mac.sh must exist")

        content = script_path.read_text(encoding="utf-8")

        # 1. Native ICNS generation
        self.assertIn("create_icns.py", content)

        # 2. PyInstaller invocation
        self.assertIn("pyinstaller", content)
        self.assertIn("build.spec", content)

        # 3. Bundle relocation prevention (pkgbuild component plist modification)
        self.assertIn("BundleIsRelocatable", content)

        # 4. Postinstall script and LaunchAgent autostart setup
        self.assertIn("com.yarsatech.niziposconnector.plist", content)
        self.assertIn("launchctl load", content)
        self.assertIn("pkgbuild", content)

    def test_build_linux_specification(self):
        """build_linux.sh must support deb, rpm, and tar.zst packages with desktop entry."""
        script_path = BASE_DIR / "build_linux.sh"
        self.assertTrue(script_path.exists(), "build_linux.sh must exist")

        content = script_path.read_text(encoding="utf-8")

        # Packaging targets
        self.assertIn("BUILD_TARGET", content)
        self.assertIn("ARCHITECTURE_DEB", content)
        self.assertIn("ARCHITECTURE_RPM", content)
        self.assertIn("INSTALL_PREFIX", content)

        # Desktop entry and permissions
        self.assertIn("Categories=Office;Finance;", content)
        self.assertIn("chmod", content)


if __name__ == "__main__":
    unittest.main()
