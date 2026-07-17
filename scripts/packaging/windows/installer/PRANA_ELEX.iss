#define MyAppName "PRANA ELEX"
#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif
#define MyAppPublisher "DLV Corporation"
#define MyAppExeName "PRANA_ELEX.exe"
#define MyAppDescription "Marine VHF Transcription and Translation"

[Setup]
AppId={{8E90F556-4D50-4D80-A729-3D6246E2DDBD}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments={#MyAppDescription}
DefaultDirName={autopf}\PRANA ELEX
DefaultGroupName=PRANA ELEX
DisableProgramGroupPage=yes
DisableWelcomePage=no
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\prana-elex.ico
WizardImageFile=assets\wizard-banner.png
WizardSmallImageFile=assets\wizard-logo.png
WizardImageStretch=yes
WizardKeepAspectRatio=yes
WizardSizePercent=110
OutputDir=..\..\..\..\release\windows
OutputBaseFilename=PRANA_ELEX_Setup_{#MyAppVersion}_x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
Compression=lzma2
SolidCompression=yes
WizardStyle=modern windows11 includetitlebar
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "vietnamese"; MessagesFile: "compiler:Default.isl,languages\Vietnamese.isl"

[CustomMessages]
english.StandardInstallation=Standard installation
vietnamese.StandardInstallation=Cài đặt tiêu chuẩn
english.ApplicationComponent=PRANA ELEX application
vietnamese.ApplicationComponent=Ứng dụng PRANA ELEX
english.DesktopShortcut=Create a desktop shortcut
vietnamese.DesktopShortcut=Tạo lối tắt trên màn hình nền
english.AutostartTask=Start PRANA ELEX when I sign in
vietnamese.AutostartTask=Khởi động PRANA ELEX khi tôi đăng nhập Windows
english.AdditionalShortcuts=Additional options:
vietnamese.AdditionalShortcuts=Tùy chọn bổ sung:
english.LaunchApp=Launch PRANA ELEX
vietnamese.LaunchApp=Mở PRANA ELEX

english.DataPageTitle=Choose Data Location
vietnamese.DataPageTitle=Chọn nơi lưu dữ liệu
english.DataPageDescription=Choose where recordings and translation results are stored.
vietnamese.DataPageDescription=Chọn nơi lưu bản ghi âm và kết quả dịch.
english.DataIntro=PRANA ELEX stores WAV recordings, translation results, and account-specific local data in this folder.
vietnamese.DataIntro=PRANA ELEX lưu bản ghi WAV, kết quả dịch và dữ liệu cục bộ theo tài khoản trong thư mục này.
english.DataFolderLabel=Data folder
vietnamese.DataFolderLabel=Thư mục dữ liệu
english.DataBrowse=Browse...
vietnamese.DataBrowse=Duyệt...
english.DataRetentionNote=Your data is kept when PRANA ELEX is uninstalled. Choose a location outside the application folder.
vietnamese.DataRetentionNote=Dữ liệu vẫn được giữ khi gỡ PRANA ELEX. Hãy chọn vị trí bên ngoài thư mục ứng dụng.
english.DataBrowseTitle=Select PRANA ELEX Data Folder
vietnamese.DataBrowseTitle=Chọn thư mục dữ liệu PRANA ELEX
english.DataRequired=Please select a data folder.
vietnamese.DataRequired=Vui lòng chọn thư mục dữ liệu.
english.DataRootRejected=The root of a drive cannot be used as the data folder. Please choose or create a subfolder.
vietnamese.DataRootRejected=Không thể dùng thư mục gốc của ổ đĩa làm nơi lưu dữ liệu. Vui lòng chọn hoặc tạo một thư mục con.
english.DataInsideAppRejected=The data folder must be outside the application installation folder.
vietnamese.DataInsideAppRejected=Thư mục dữ liệu phải nằm ngoài thư mục cài đặt ứng dụng.
english.DataCreateFailed=Setup could not create the selected data folder. Choose a location you can write to.
vietnamese.DataCreateFailed=Không thể tạo thư mục dữ liệu đã chọn. Hãy chọn vị trí mà bạn có quyền ghi.
english.DataWriteFailed=Setup cannot write to the selected data folder. Choose another location.
vietnamese.DataWriteFailed=Không thể ghi vào thư mục dữ liệu đã chọn. Hãy chọn vị trí khác.
english.ReadyDataFolder=Data folder:
vietnamese.ReadyDataFolder=Thư mục dữ liệu:
english.ReadyInstallScope=Install scope:
vietnamese.ReadyInstallScope=Phạm vi cài đặt:
english.ScopeAllUsers=All users
vietnamese.ScopeAllUsers=Mọi người dùng
english.ScopeCurrentUser=Current user only
vietnamese.ScopeCurrentUser=Chỉ người dùng hiện tại

[Types]
Name: "standard"; Description: "{cm:StandardInstallation}"; Flags: iscustom

[Components]
Name: "application"; Description: "{cm:ApplicationComponent}"; Types: standard; Flags: fixed

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopShortcut}"; GroupDescription: "{cm:AdditionalShortcuts}"
Name: "autostart"; Description: "{cm:AutostartTask}"; GroupDescription: "{cm:AdditionalShortcuts}"; Flags: unchecked

[Files]
Source: "..\..\..\..\dist\windows\PRANA_ELEX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: application

[Dirs]
Name: "{code:GetSelectedDataDir}"; Permissions: users-modify; Check: IsAdminInstallMode

[Icons]
Name: "{group}\PRANA ELEX"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\PRANA ELEX"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\PRANA ELEX"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DataPage: TWizardPage;
  DataIntroLabel: TNewStaticText;
  DataFolderLabel: TNewStaticText;
  DataPathEdit: TNewEdit;
  DataBrowseButton: TNewButton;
  DataRetentionLabel: TNewStaticText;

function NormalizedPath(Path: String): String;
begin
  Result := RemoveBackslashUnlessRoot(ExpandFileName(Trim(Path)));
end;

function GetSelectedDataDir(Param: String): String;
begin
  if Trim(DataPathEdit.Text) = '' then
    Result := ''
  else
    Result := NormalizedPath(DataPathEdit.Text);
end;

procedure BrowseForDataFolder(Sender: TObject);
var
  SelectedPath: String;
begin
  SelectedPath := DataPathEdit.Text;
  if BrowseForFolder(CustomMessage('DataBrowseTitle'), SelectedPath, True) then
    DataPathEdit.Text := SelectedPath;
end;

procedure InitializeWizard;
var
  RequestedDataDir: String;
begin
  DataPage := CreateCustomPage(
    wpSelectDir,
    CustomMessage('DataPageTitle'),
    CustomMessage('DataPageDescription')
  );

  DataIntroLabel := TNewStaticText.Create(DataPage.Surface);
  DataIntroLabel.Parent := DataPage.Surface;
  DataIntroLabel.Left := 0;
  DataIntroLabel.Top := ScaleY(8);
  DataIntroLabel.Width := DataPage.SurfaceWidth;
  DataIntroLabel.Height := ScaleY(42);
  DataIntroLabel.AutoSize := False;
  DataIntroLabel.WordWrap := True;
  DataIntroLabel.Caption := CustomMessage('DataIntro');

  DataFolderLabel := TNewStaticText.Create(DataPage.Surface);
  DataFolderLabel.Parent := DataPage.Surface;
  DataFolderLabel.Left := 0;
  DataFolderLabel.Top := ScaleY(64);
  DataFolderLabel.Caption := CustomMessage('DataFolderLabel');

  DataPathEdit := TNewEdit.Create(DataPage.Surface);
  DataPathEdit.Parent := DataPage.Surface;
  DataPathEdit.Left := 0;
  DataPathEdit.Top := ScaleY(84);
  DataPathEdit.Width := DataPage.SurfaceWidth - ScaleX(104);
  DataPathEdit.Height := ScaleY(30);

  DataBrowseButton := TNewButton.Create(DataPage.Surface);
  DataBrowseButton.Parent := DataPage.Surface;
  DataBrowseButton.Left := DataPage.SurfaceWidth - ScaleX(96);
  DataBrowseButton.Top := DataPathEdit.Top - ScaleY(1);
  DataBrowseButton.Width := ScaleX(96);
  DataBrowseButton.Height := ScaleY(32);
  DataBrowseButton.Caption := CustomMessage('DataBrowse');
  DataBrowseButton.OnClick := @BrowseForDataFolder;

  DataRetentionLabel := TNewStaticText.Create(DataPage.Surface);
  DataRetentionLabel.Parent := DataPage.Surface;
  DataRetentionLabel.Left := 0;
  DataRetentionLabel.Top := ScaleY(132);
  DataRetentionLabel.Width := DataPage.SurfaceWidth;
  DataRetentionLabel.Height := ScaleY(48);
  DataRetentionLabel.AutoSize := False;
  DataRetentionLabel.WordWrap := True;
  { TColor uses BGR byte order: this is brand teal #005E68. }
  DataRetentionLabel.Font.Color := $685E00;
  DataRetentionLabel.Caption := CustomMessage('DataRetentionNote');

  RequestedDataDir := ExpandConstant('{param:DATADIR|}');
  if RequestedDataDir = '' then
  begin
    if IsAdminInstallMode then
      RequestedDataDir := ExpandConstant('{commonappdata}\PRANA ELEX\Data')
    else
      RequestedDataDir := ExpandConstant('{userdocs}\PRANA ELEX Data');
  end;
  DataPathEdit.Text := RequestedDataDir;
end;

function ValidateDataDirectory: Boolean;
var
  AppPath: String;
  DataPath: String;
  DriveRoot: String;
  ProbePath: String;
begin
  Result := False;
  DataPath := GetSelectedDataDir('');
  if DataPath = '' then
  begin
    MsgBox(CustomMessage('DataRequired'), mbError, MB_OK);
    Exit;
  end;

  DriveRoot := AddBackslash(ExtractFileDrive(DataPath));
  if CompareText(DataPath, DriveRoot) = 0 then
  begin
    MsgBox(CustomMessage('DataRootRejected'), mbError, MB_OK);
    Exit;
  end;

  AppPath := NormalizedPath(WizardDirValue);
  if (CompareText(DataPath, AppPath) = 0) or
     (Pos(Uppercase(AddBackslash(AppPath)), Uppercase(AddBackslash(DataPath))) = 1) then
  begin
    MsgBox(CustomMessage('DataInsideAppRejected'), mbError, MB_OK);
    Exit;
  end;

  if not ForceDirectories(DataPath) then
  begin
    MsgBox(CustomMessage('DataCreateFailed'), mbError, MB_OK);
    Exit;
  end;

  ProbePath := AddBackslash(DataPath) + '.prana-elex-write-test.tmp';
  if not SaveStringToFile(ProbePath, 'write-test', False) then
  begin
    MsgBox(CustomMessage('DataWriteFailed'), mbError, MB_OK);
    Exit;
  end;
  DeleteFile(ProbePath);
  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = DataPage.ID then
    Result := ValidateDataDirectory;
end;

function UpdateReadyMemo(
  Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String
): String;
var
  ScopeText: String;
begin
  if IsAdminInstallMode then
    ScopeText := CustomMessage('ScopeAllUsers')
  else
    ScopeText := CustomMessage('ScopeCurrentUser');

  Result := MemoDirInfo + NewLine + NewLine +
    CustomMessage('ReadyDataFolder') + NewLine + Space + GetSelectedDataDir('') + NewLine + NewLine +
    CustomMessage('ReadyInstallScope') + NewLine + Space + ScopeText;
  if MemoTasksInfo <> '' then
    Result := Result + NewLine + NewLine + MemoTasksInfo;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DataPath: String;
  SettingsLines: TArrayOfString;
  SettingsPath: String;
begin
  if CurStep = ssInstall then
  begin
    { Remove stale per-user shortcuts before recreating them for this scope. }
    DeleteFile(ExpandConstant('{userdesktop}\PRANA ELEX.lnk'));
    DeleteFile(ExpandConstant('{userprograms}\PRANA ELEX\PRANA ELEX.lnk'));
  end;

  if CurStep = ssPostInstall then
  begin
    DataPath := GetSelectedDataDir('');
    ForceDirectories(DataPath);

    StringChangeEx(DataPath, '\', '/', True);
    SetArrayLength(SettingsLines, 3);
    SettingsLines[0] := '{';
    SettingsLines[1] := '  "data_dir": "' + DataPath + '"';
    SettingsLines[2] := '}';
    if IsAdminInstallMode then
      SettingsPath := ExpandConstant('{commonappdata}\PRANA ELEX\settings.json')
    else
      SettingsPath := ExpandConstant('{localappdata}\PRANA ELEX\settings.json');
    ForceDirectories(ExtractFileDir(SettingsPath));
    SaveStringsToUTF8File(SettingsPath, SettingsLines, False);
  end;
end;
