; Inno Setup script for "Local Dictation" (Windows x64).
;
; Packages the PyInstaller onedir build into a single setup .exe.
;
; Expects the built app folder at:
;     dist\Local Dictation\           (contains "Local Dictation.exe" + deps)
; relative to the repo root, and is invoked from the repo root in CI:
;
;     iscc /DAppVersion=1.0.0 desktop\windows\installer.iss
;
; AppVersion is passed in by CI (read from dictate\__init__.py). It defaults to
; 0.0.0 so the script also compiles standalone for local testing.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "Local Dictation"
#define AppPublisher "Local Dictation"
#define AppExeName "Local Dictation.exe"
; Stable AppId GUID — keeps upgrades/uninstall consistent across versions.
; Do NOT change this once shipped.
#define AppId "{{8E5C1F2A-3B47-4D9E-9C21-7A1F0B6E4D55}"

[Setup]
; Inno resolves relative [Files] Source and OutputDir against SourceDir, which
; defaults to this script's own folder (desktop\windows). The PyInstaller build
; lives at the repo root, so anchor SourceDir there: {#SourcePath} is this .iss
; file's directory, and ..\.. walks up to the repo root. This makes the compile
; independent of the working directory it's invoked from.
SourceDir={#SourcePath}..\..
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Per-machine install into Program Files -> needs admin.
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=LocalDictationSetup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startup"; Description: "Start {#AppName} automatically when I sign in (background tray app)"; GroupDescription: "Startup:"

[Files]
; The entire PyInstaller onedir output. recursesubdirs + createallsubdirs pulls
; in every bundled DLL/data file beside the exe.
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Optional "run at login": HKCU Run key (current user only -> no admin needed
; at login time). Removed automatically on uninstall via uninsdeletevalue.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: startup

[Run]
; Offer to launch the tray app right after install. nowait + skipifsilent so an
; unattended/CI install doesn't block.
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up anything the app writes into its install dir at runtime.
Type: filesandordirs; Name: "{app}\__pycache__"
