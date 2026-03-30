#!/bin/bash
# -----------------------------------------------------------------------------
# NiziPOS Linux Unified Package Builder
# Consolidates .deb, .rpm, and .tar.zst (Arch) builds.
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

# Use the exe basename directly for package names (preserves CamelCase)
APP_NAME="$MAIN_EXE_BASENAME"
APP_DISPLAY="$APP_FULL_NAME"

# Build target (deb|rpm|tarzst|all) comes from first argument.
BUILD_TARGET="${1:-all}"

# App version must be provided via env var or second positional argument.
# Examples:
#   APP_VERSION=1.2.3 ./build_linux.sh all
#   ./build_linux.sh all 1.2.3
APP_VERSION="${APP_VERSION:-${2:-}}"
if [ -z "$APP_VERSION" ]; then
    echo "ERROR: APP_VERSION is required."
    echo "Provide it via env var or second parameter."
    echo "Example: APP_VERSION=1.2.3 ./build_linux.sh all"
    echo "Example: ./build_linux.sh all 1.2.3"
    exit 1
fi

# Common Metadata
PUBLISHER=$(read_config "app_author")
PUBLISHER_EMAIL=$(read_config "author_email")
PUBLISHER_URL=$(read_config "contact_url")
DESCRIPTION=$(read_config "description")
ARCHITECTURE_DEB="amd64"
ARCHITECTURE_RPM="x86_64"
ARCHITECTURE_ARCH="x86_64"

PYINSTALLER_DIR="dist/${MAIN_EXE_BASENAME}"
OUTPUT_DIR="dist"
INSTALL_PREFIX="/opt/${MAIN_EXE_BASENAME}"

# --- 2. Sanity Checks ---
if [ ! -d "$PYINSTALLER_DIR" ]; then
    echo "ERROR: PyInstaller output not found at '$PYINSTALLER_DIR'"
    echo "Run: pyinstaller build.spec first."
    exit 1
fi

# Function to build DEB
build_deb() {
    echo "Building .deb package..."
    PKGDIR="build/${APP_NAME}-${APP_VERSION}-${ARCHITECTURE_DEB}"
    
    rm -rf "$PKGDIR"
    mkdir -p "$PKGDIR${INSTALL_PREFIX}"
    mkdir -p "$PKGDIR/usr/share/applications"
    mkdir -p "$PKGDIR/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$PKGDIR/usr/bin"
    mkdir -p "$PKGDIR/etc/xdg/autostart"
    mkdir -p "$PKGDIR/DEBIAN"

    # Copy application files
    cp -r "$PYINSTALLER_DIR/." "$PKGDIR${INSTALL_PREFIX}/"
    chmod +x "$PKGDIR${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}"

    # Wrapper script
    cat >"$PKGDIR/usr/bin/${APP_NAME}" <<EOF
#!/bin/bash
exec "${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}" "\$@"
EOF
    chmod +x "$PKGDIR/usr/bin/${APP_NAME}"

    # Desktop entry
    cat >"$PKGDIR/usr/share/applications/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Name=${APP_DISPLAY}
Exec=${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}
Icon=${APP_NAME}
Type=Application
Categories=Office;Finance;
Comment=${DESCRIPTION}
StartupNotify=true
EOF

    # Autostart entry
    cat >"$PKGDIR/etc/xdg/autostart/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Name=${APP_DISPLAY}
Exec=${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}
Icon=${APP_NAME}
Type=Application
Comment=${DESCRIPTION}
X-GNOME-Autostart-enabled=true
EOF

    # Icon
    if [ -f "assets/icon.png" ]; then
        cp "assets/icon.png" "$PKGDIR/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    elif [ -f "assets/setup-icon.ico" ]; then
        echo "Converting .ico to .png (requires imagemagick)..."
        convert "assets/setup-icon.ico[5]" "$PKGDIR/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    fi

    # Control file
    INSTALLED_SIZE=$(du -sk "$PKGDIR${INSTALL_PREFIX}" | cut -f1)
    cat >"$PKGDIR/DEBIAN/control" <<EOF
Package: ${APP_NAME}
Version: ${APP_VERSION}
Section: misc
Priority: optional
Architecture: ${ARCHITECTURE_DEB}
Installed-Size: ${INSTALLED_SIZE}
Maintainer: ${PUBLISHER} <${PUBLISHER_EMAIL}>
Homepage: ${PUBLISHER_URL}
Description: ${DESCRIPTION}
EOF

    # Post-install script
    cat >"$PKGDIR/DEBIAN/postinst" <<EOF
#!/bin/bash
set -e
if command -v update-desktop-database &>/dev/null; then
  update-desktop-database /usr/share/applications
fi
if command -v gtk-update-icon-cache &>/dev/null; then
  gtk-update-icon-cache -f /usr/share/icons/hicolor
fi
EOF
    chmod 755 "$PKGDIR/DEBIAN/postinst"

    # Post-remove script
    cat >"$PKGDIR/DEBIAN/postrm" <<EOF
#!/bin/bash
set -e
if [ "\$1" = "purge" ]; then
  rm -rf "${INSTALL_PREFIX}"
fi
if command -v update-desktop-database &>/dev/null; then
  update-desktop-database /usr/share/applications
fi
EOF
    chmod 755 "$PKGDIR/DEBIAN/postrm"

    # Build the package
    mkdir -p "$OUTPUT_DIR"
    dpkg-deb --build --root-owner-group "$PKGDIR" "${OUTPUT_DIR}/${APP_NAME}-${APP_VERSION}-${ARCHITECTURE_DEB}.deb"
    echo "✅ Done: ${OUTPUT_DIR}/${APP_NAME}-${APP_VERSION}-${ARCHITECTURE_DEB}.deb"
}

# Function to build RPM
build_rpm() {
    echo "Building .rpm package..."
    if ! command -v rpmbuild &>/dev/null; then
        echo "ERROR: rpmbuild not found."
        return 1
    fi

    RPMBUILD_DIR="$(pwd)/build/rpmbuild"
    STAGED_ROOT="${RPMBUILD_DIR}/STAGED"
    
    rm -rf "$RPMBUILD_DIR"
    mkdir -p "${STAGED_ROOT}${INSTALL_PREFIX}"
    mkdir -p "${STAGED_ROOT}/usr/share/applications"
    mkdir -p "${STAGED_ROOT}/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "${STAGED_ROOT}/usr/bin"
    mkdir -p "${STAGED_ROOT}/etc/xdg/autostart"
    mkdir -p "${RPMBUILD_DIR}/SPECS"
    mkdir -p "${RPMBUILD_DIR}/BUILD"
    mkdir -p "${RPMBUILD_DIR}/BUILDROOT"
    mkdir -p "${RPMBUILD_DIR}/RPMS"
    mkdir -p "${RPMBUILD_DIR}/SRPMS"

    # Copy application files
    cp -r "$PYINSTALLER_DIR/." "${STAGED_ROOT}${INSTALL_PREFIX}/"
    chmod +x "${STAGED_ROOT}${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}"

    # Wrapper script
    cat >"${STAGED_ROOT}/usr/bin/${APP_NAME}" <<EOF
#!/bin/bash
exec "${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}" "\$@"
EOF
    chmod +x "${STAGED_ROOT}/usr/bin/${APP_NAME}"

    # Desktop entry
    cat >"${STAGED_ROOT}/usr/share/applications/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Name=${APP_DISPLAY}
Exec=${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}
Icon=${APP_NAME}
Type=Application
Categories=Office;Finance;
Comment=${DESCRIPTION}
StartupNotify=true
EOF

    # Autostart entry
    cat >"${STAGED_ROOT}/etc/xdg/autostart/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Name=${APP_DISPLAY}
Exec=${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}
Icon=${APP_NAME}
Type=Application
Comment=${DESCRIPTION}
X-GNOME-Autostart-enabled=true
EOF

    # Icon
    if [ -f "assets/icon.png" ]; then
        cp "assets/icon.png" "${STAGED_ROOT}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    elif [ -f "assets/setup-icon.ico" ]; then
        convert "assets/setup-icon.ico[5]" "${STAGED_ROOT}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    fi

    # Spec file
    SPEC_FILE="${RPMBUILD_DIR}/SPECS/${APP_NAME}.spec"
    cat >"$SPEC_FILE" <<SPECEOF
Name:           ${APP_NAME}
Version:        ${APP_VERSION//-/_}
Release:        1
Summary:        ${DESCRIPTION}
License:        Proprietary
URL:            ${PUBLISHER_URL}
Packager:       ${PUBLISHER} <${PUBLISHER_EMAIL}>
AutoReqProv:    no

%description
${DESCRIPTION}

%install
mkdir -p %{buildroot}
cp -r ${STAGED_ROOT}/. %{buildroot}/

%post
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor
fi

%postun
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications
fi
if [ "\$1" = "0" ]; then
    rm -rf "${INSTALL_PREFIX}"
fi

%files
%defattr(-,root,root,-)
${INSTALL_PREFIX}
/usr/bin/${APP_NAME}
/usr/share/applications/${APP_NAME}.desktop
/etc/xdg/autostart/${APP_NAME}.desktop
/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png
SPECEOF

    rpmbuild -bb --define "_topdir ${RPMBUILD_DIR}" "$SPEC_FILE"
    
    mkdir -p "$OUTPUT_DIR"
    BUILT_RPM=$(find "${RPMBUILD_DIR}/RPMS" -name "*.rpm" | head -1)

    # Normalize output filename to remove RPM release suffix (e.g. "-1").
    RPM_BASENAME=$(basename "$BUILT_RPM")
    RPM_NORMALIZED_NAME=$(echo "$RPM_BASENAME" | sed -E 's/^(.+)-([0-9]+(\.[0-9]+)*)-[^-]+\.([^.]+)\.rpm$/\1-\2-\4.rpm/')
    cp "$BUILT_RPM" "${OUTPUT_DIR}/${RPM_NORMALIZED_NAME}"
    echo "✅ Done: ${OUTPUT_DIR}/${RPM_NORMALIZED_NAME}"
}

# Function to build TARZST
build_tarzst() {
    echo "Building .tar.zst package..."
    if ! command -v zstd &>/dev/null; then
        echo "ERROR: zstd not found."
        return 1
    fi

    PKGDIR="build/${APP_NAME}-${APP_VERSION}-pkg"
    PKG_FILENAME="${APP_NAME}-${APP_VERSION}-${ARCHITECTURE_ARCH}.pkg.tar.zst"
    
    rm -rf "$PKGDIR"
    mkdir -p "${PKGDIR}${INSTALL_PREFIX}"
    mkdir -p "${PKGDIR}/usr/share/applications"
    mkdir -p "${PKGDIR}/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "${PKGDIR}/usr/bin"
    mkdir -p "${PKGDIR}/etc/xdg/autostart"

    # Copy application files
    cp -r "$PYINSTALLER_DIR/." "${PKGDIR}${INSTALL_PREFIX}/"
    chmod +x "${PKGDIR}${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}"

    # Wrapper script
    cat >"${PKGDIR}/usr/bin/${APP_NAME}" <<EOF
#!/bin/bash
exec "${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}" "\$@"
EOF
    chmod +x "${PKGDIR}/usr/bin/${APP_NAME}"

    # Desktop entry
    cat >"${PKGDIR}/usr/share/applications/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Name=${APP_DISPLAY}
Exec=${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}
Icon=${APP_NAME}
Type=Application
Categories=Office;Finance;
Comment=${DESCRIPTION}
StartupNotify=true
EOF

    # Autostart entry
    cat >"${PKGDIR}/etc/xdg/autostart/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Name=${APP_DISPLAY}
Exec=${INSTALL_PREFIX}/${MAIN_EXE_BASENAME}
Icon=${APP_NAME}
Type=Application
Comment=${DESCRIPTION}
X-GNOME-Autostart-enabled=true
EOF

    # Icon
    if [ -f "assets/icon.png" ]; then
        cp "assets/icon.png" "${PKGDIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
        elif [ -f "assets/setup-icon.ico" ]; then
        convert "assets/setup-icon.ico[5]" "${PKGDIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    fi

    # .PKGINFO
    INSTALLED_SIZE=$(du -sb "${PKGDIR}" | cut -f1)
    FILE_LIST=$(find "${PKGDIR}" -not -type d | sed "s|${PKGDIR}/||" | sort)
    
    cat >"${PKGDIR}/.PKGINFO" <<EOF
pkgname = ${APP_NAME}
pkgver = ${APP_VERSION}
pkgdesc = ${DESCRIPTION}
url = ${PUBLISHER_URL}
builddate = $(date +%s)
packager = ${PUBLISHER} <${PUBLISHER_EMAIL}>
size = ${INSTALLED_SIZE}
arch = ${ARCHITECTURE_ARCH}
$(echo "$FILE_LIST" | sed 's|^|file = |')
EOF

    # .INSTALL
    cat >"${PKGDIR}/.INSTALL" <<EOF
post_install() {
  if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications
  fi
  if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor
  fi
}
post_upgrade() { post_install; }
post_remove() {
  rm -rf "${INSTALL_PREFIX}"
  if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications
  fi
}
EOF

    mkdir -p "$OUTPUT_DIR"
    pushd "$PKGDIR" > /dev/null
    find . -not -name '.PKGINFO' -not -name '.INSTALL' -not -type d -print0 \
    | tar --zstd -cf "../../${OUTPUT_DIR}/${PKG_FILENAME}" --null -T - --transform 's|^\./||' .PKGINFO .INSTALL
    popd > /dev/null
    
    echo "✅ Done: ${OUTPUT_DIR}/${PKG_FILENAME}"
}

# --- 3. Execution ---
case "$BUILD_TARGET" in
    deb)
        build_deb
        ;;
    rpm)
        build_rpm
        ;;
    tarzst)
        build_tarzst
        ;;
    all|*)
        build_deb
        build_rpm
        build_tarzst
        ;;
esac
