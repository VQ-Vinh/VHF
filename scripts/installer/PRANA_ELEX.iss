#define MyAppName "PRANA ELEX"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DLV Corporation"
#define MyAppExeName "PRANA_ELEX.exe"

[Setup]
AppId={{8E90F556-4D50-4D80-A729-3D6246E2DDBD}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\PRANA ELEX
DefaultGroupName=PRANA ELEX
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\..\release
OutputBaseFilename=PRANA_ELEX_Setup_{#MyAppVersion}_x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "standard"; Description: "Standard installation"; Flags: iscustom

[Components]
Name: "application"; Description: "PRANA ELEX application"; Types: standard; Flags: fixed

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "autostart"; Description: "Start PRANA ELEX when I sign in"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\..\dist\PRANA_ELEX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: application

[Icons]
Name: "{group}\PRANA ELEX"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\PRANA ELEX"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\PRANA ELEX"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch PRANA ELEX"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\settings.json"
Type: filesandordirs; Name: "{app}\.secrets"

[Code]
var
  DataDirPage: TInputDirWizardPage;
  CredentialsPage: TInputFileWizardPage;

procedure InitializeWizard;
var
  RequestedDataDir: String;
begin
  DataDirPage := CreateInputDirPage(
    wpSelectTasks,
    'Choose Data Location',
    'Where should PRANA ELEX store recordings and results?',
    'Select a folder outside the application directory, then click Next.',
    False,
    ''
  );
  DataDirPage.Add('Data folder:');
  RequestedDataDir := ExpandConstant('{param:DATADIR|}');
  if RequestedDataDir = '' then
    RequestedDataDir := ExpandConstant('{userdocs}\PRANA ELEX Data');
  DataDirPage.Values[0] := RequestedDataDir;

  CredentialsPage := CreateInputFilePage(
    DataDirPage.ID,
    'Google Cloud Credentials',
    'Select the service-account JSON used by PRANA ELEX.',
    'The key is copied during installation but is never embedded in the Setup file.'
  );
  CredentialsPage.Add('Service-account JSON:', 'JSON files|*.json|All files|*.*', '.json');
  CredentialsPage.Values[0] := ExpandConstant('{param:CREDENTIALS|}');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = DataDirPage.ID then
  begin
    if Trim(DataDirPage.Values[0]) = '' then
    begin
      MsgBox('Please select a data folder.', mbError, MB_OK);
      Result := False;
    end;
  end;
  if CurPageID = CredentialsPage.ID then
  begin
    if (Trim(CredentialsPage.Values[0]) = '') or
       (not FileExists(CredentialsPage.Values[0])) then
    begin
      MsgBox('Please select a valid Google service-account JSON file.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DataPath: String;
  CredentialsPath: String;
  InstalledCredentialsPath: String;
  SettingsJson: String;
begin
  if CurStep = ssPostInstall then
  begin
    DataPath := DataDirPage.Values[0];
    ForceDirectories(DataPath);

    CredentialsPath := CredentialsPage.Values[0];
    InstalledCredentialsPath := ExpandConstant('{app}\.secrets\gcs-service-account.json');
    ForceDirectories(ExtractFileDir(InstalledCredentialsPath));
    if not FileCopy(CredentialsPath, InstalledCredentialsPath, False) then
      RaiseException('Could not copy the Google service-account JSON.');

    StringChangeEx(DataPath, '\', '/', True);
    StringChangeEx(InstalledCredentialsPath, '\', '/', True);
    SettingsJson := '{' + #13#10 +
      '  "data_dir": "' + DataPath + '",' + #13#10 +
      '  "credentials_path": "' + InstalledCredentialsPath + '"' + #13#10 +
      '}' + #13#10;
    SaveStringToFile(ExpandConstant('{app}\settings.json'), SettingsJson, False);
  end;
end;
