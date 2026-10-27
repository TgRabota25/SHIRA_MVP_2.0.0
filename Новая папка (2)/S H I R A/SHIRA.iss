#define MyAppName "SHIRA"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "SHIRA"
#define MyAppExeName "SHIRA.exe"

#if !FileExists(SourcePath + "\\dist\\SHIRA\\SHIRA.exe")
  #error First run 03_BUILD_EXE.cmd and test the EXE
#endif
#if !FileExists(SourcePath + "\\build_assets\\icon.png")
  #error Run 03_BUILD_EXE.cmd first: build_assets\\icon.png is required for installer branding
#endif
#if !FileExists(SourcePath + "\\build_assets\\icon.ico")
  #error Run 03_BUILD_EXE.cmd first: build_assets\\icon.ico is required for installer icon
#endif

[Setup]
AppId={{9C212F98-B44C-40E6-BE11-E748B30A9659}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\\Programs\\SHIRA
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
WizardResizable=yes
WizardSmallImageFile=build_assets\\icon.png
SetupIconFile=build_assets\\icon.ico
UninstallDisplayIcon={app}\\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=SHIRA_Setup_2.0.0_x64
CloseApplications=yes
ShowLanguageDialog=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: unchecked

[Files]
Source: "dist\\SHIRA\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "Запустить SHIRA"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\\_internal"
