; ---------------------------------------
; Nizi POS Connector — Inno Setup installer
; Requires Inno Setup Compiler
; ---------------------------------------
;
; Pass installer version via Inno Setup define, e.g. /DAppVer=1.2.3

#ifndef AppVer
#define AppVer "1.0.0"
#endif

#ifndef AppArch
#define AppArch "x64"
#endif

[Setup]
AppName=Nizi POS Connector
AppVersion={#AppVer}
AppPublisher=Yarsa Tech
AppPublisherURL=https://yarsa.tech/
DefaultDirName={localappdata}\NiziPOSConnector
DefaultGroupName=Nizi POS Connector
OutputDir=dist
OutputBaseFilename=NiziPOSConnector-Installer-{#AppVer}-{#AppArch}
SetupIconFile=assets\\setup-icon.ico
UninstallDisplayIcon={app}\NiziPOSConnector.exe
DisableProgramGroupPage=yes
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "dist\NiziPOSConnector\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "dist\NiziPOSConnector\ota-updater.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Nizi POS Connector"; Filename: "{app}\NiziPOSConnector.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Nizi POS Connector"; Filename: "{app}\NiziPOSConnector.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: autostart; Description: "Start Nizi POS Connector automatically at login"

[Run]
Filename: "{app}\NiziPOSConnector.exe"; Description: "Launch Nizi POS Connector"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
ValueType: string; ValueName: "NiziPOSConnector"; ValueData: "{app}\NiziPOSConnector.exe"; Flags: uninsdeletevalue; Tasks: autostart

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
