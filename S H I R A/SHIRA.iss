#define MyAppName "SHIRA"
#define MyAppVersion "2.0.0"
#if !FileExists(SourcePath + "\\dist\\SHIRA\\SHIRA.exe")
  #error First run 03_BUILD_EXE.cmd and test the EXE
#endif
#if !FileExists(SourcePath + "\\build_assets\\icon.png")
  #error Run 03_BUILD_EXE.cmd first: build_assets\\icon.png is required for installer branding
#endif

[Setup]
AppId={{9C212F98-B44C-40E6-BE11-E748B30A9659}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=SHIRA
DefaultDirName={localappdata}\\Programs\\SHIRA
DefaultGroupName=SHIRA
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
WizardResizable=yes
WizardSmallImageFile=build_assets\\icon.png
SetupIconFile=build_assets\\icon.ico
UninstallDisplayIcon={app}\\SHIRA.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=SHIRA_Setup_2.0.0_x64
CloseApplications=yes
DisableProgramGroupPage=yes
ShowLanguageDialog=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[CustomMessages]
WelcomeLabel2=Локальный видеоархив и распознавание этикеток.%n%nПрограмма будет установлена только для текущего пользователя Windows.%n%nНажмите «Далее», чтобы продолжить.
FinishedHeadingLabel=SHIRA готов к работе
FinishedLabelNoIcons=Установка SHIRA завершена.%n%nПользовательские базы, резервные копии и исходные видео не удаляются при деинсталляции.
FinishedLabel=Установка SHIRA завершена.%n%nПользовательские базы, резервные копии и исходные видео не удаляются при деинсталляции.

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: unchecked

[Files]
Source: "dist\\SHIRA\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\SHIRA"; Filename: "{app}\\SHIRA.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\\SHIRA"; Filename: "{app}\\SHIRA.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\\SHIRA.exe"; Description: "Запустить SHIRA"; Flags: nowait postinstall skipifsilent

[Code]
const
  ShellBackground = $00362B00;
  ShellPanel = $00423607;
  ShellText = $00F0EDE3;
  ShellMuted = $00B6AF9A;
  ShellAccent = $00A78716;

procedure InitializeWizard();
begin
  WizardForm.Color := ShellBackground;
  WizardForm.WelcomePage.Color := ShellBackground;
  WizardForm.InnerPage.Color := ShellBackground;
  WizardForm.FinishedPage.Color := ShellBackground;
  WizardForm.MainPanel.Color := ShellPanel;
  WizardForm.Bevel.Color := ShellPanel;
  WizardForm.Bevel1.Color := ShellPanel;
  WizardForm.InnerNotebook.Color := ShellBackground;
  WizardForm.WelcomeLabel1.Font.Color := ShellText;
  WizardForm.WelcomeLabel2.Font.Color := ShellText;
  WizardForm.FinishedHeadingLabel.Font.Color := ShellText;
  WizardForm.FinishedLabel.Font.Color := ShellText;
  WizardForm.PageNameLabel.Font.Color := ShellText;
  WizardForm.PageDescriptionLabel.Font.Color := ShellMuted;
  WizardForm.NextButton.Font.Color := clWhite;
  WizardForm.BackButton.Font.Color := ShellText;
  WizardForm.CancelButton.Font.Color := ShellText;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpWelcome then
  begin
    WizardForm.WelcomeLabel1.Caption := 'SHIRA ' + ExpandConstant('{#MyAppVersion}');
    WizardForm.WelcomeLabel2.Caption := ExpandConstant('{cm:WelcomeLabel2}');
  end;
end;
