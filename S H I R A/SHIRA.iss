#define MyAppName "SHIRA"
#define MyAppVersion "2.0.0"
#if !FileExists(SourcePath + "\dist\SHIRA\SHIRA.exe")
  #error First run 03_BUILD_EXE.cmd and test the EXE
#endif
[Setup]
AppId={{9C212F98-B44C-40E6-BE11-E748B30A9659}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=SHIRA
DefaultDirName={localappdata}\Programs\SHIRA
DefaultGroupName=SHIRA
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=SHIRA_Setup_2.0.0_x64
SetupIconFile=build_assets\icon.ico
UninstallDisplayIcon={app}\SHIRA.exe
CloseApplications=yes
DisableProgramGroupPage=yes
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
[Files]
Source: "dist\SHIRA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\SHIRA"; Filename: "{app}\SHIRA.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\SHIRA"; Filename: "{app}\SHIRA.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\SHIRA.exe"; Description: "Запустить SHIRA"; Flags: nowait postinstall skipifsilent
