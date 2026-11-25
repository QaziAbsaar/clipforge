; Windows installer for ClipForge. Built by .github/workflows/windows.yml (needs Inno Setup 6).
#define AppVer GetEnv("CLIPFORGE_VERSION")
#if AppVer == ""
  #define AppVer "0.0.0"
#endif

[Setup]
AppId={{6F3C2A57-1D4B-4E8A-9C61-CF0A7E5B2D19}
AppName=ClipForge
AppVersion={#AppVer}
AppPublisher=ClipForge
; Per-user install: no admin prompt, and ClipForge can write its data folder next to the exe
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\ClipForge
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=ClipForge-Setup-{#AppVer}
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\ClipForge.exe
CloseApplications=yes

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[InstallDelete]
; Remove the old program files on update. The data folder (your clips) is kept.
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\bin"

[Files]
Source: "..\dist\ClipForge\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\ClipForge"; Filename: "{app}\ClipForge.exe"
Name: "{autodesktop}\ClipForge"; Filename: "{app}\ClipForge.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ClipForge.exe"; Description: "Start ClipForge"; Flags: nowait postinstall skipifsilent
