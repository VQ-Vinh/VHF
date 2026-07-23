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
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableWelcomePage=no
UsePreviousAppDir=no
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\prana-elex.ico
WizardImageFile=assets\wizard-banner.png
WizardSmallImageFile=assets\wizard-logo.png
WizardImageStretch=yes
WizardKeepAspectRatio=yes
WizardSizePercent=110
OutputDir=..\..\..\..\installers\windows
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

english.LocationsPageTitle=Installation Locations
vietnamese.LocationsPageTitle=Vị trí cài đặt
english.LocationsPageDescription=Choose separate locations for the application and your data.
vietnamese.LocationsPageDescription=Chọn riêng nơi cài ứng dụng và nơi lưu dữ liệu của bạn.
english.AppSectionTitle=APPLICATION FILES
vietnamese.AppSectionTitle=TỆP ỨNG DỤNG
english.AppIntro=Contains PRANA ELEX, libraries, and program files. This folder may be removed when the application is uninstalled.
vietnamese.AppIntro=Chứa PRANA ELEX, thư viện và các tệp chương trình. Thư mục này có thể bị xóa khi gỡ ứng dụng.
english.AppFolderLabel=Application folder
vietnamese.AppFolderLabel=Thư mục cài ứng dụng
english.AppBrowseTitle=Select PRANA ELEX Application Folder
vietnamese.AppBrowseTitle=Chọn thư mục cài ứng dụng PRANA ELEX
english.AppRequired=Please select an application folder.
vietnamese.AppRequired=Vui lòng chọn thư mục cài ứng dụng.
english.DataSectionTitle=USER DATA
vietnamese.DataSectionTitle=DỮ LIỆU NGƯỜI DÙNG
english.DataIntro=Contains WAV recordings, translation JSON, history, and account-specific local data.
vietnamese.DataIntro=Chứa bản ghi WAV, JSON kết quả dịch, lịch sử và dữ liệu cục bộ theo tài khoản.
english.DataFolderLabel=Data folder
vietnamese.DataFolderLabel=Thư mục dữ liệu
english.BrowseButton=Browse...
vietnamese.BrowseButton=Duyệt...
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
english.AppInsideDataRejected=The application folder must be outside the data folder.
vietnamese.AppInsideDataRejected=Thư mục cài ứng dụng phải nằm ngoài thư mục dữ liệu.
english.DataCreateFailed=Setup could not create the selected data folder. Choose a location you can write to.
vietnamese.DataCreateFailed=Không thể tạo thư mục dữ liệu đã chọn. Hãy chọn vị trí mà bạn có quyền ghi.
english.DataWriteFailed=Setup cannot write to the selected data folder. Choose another location.
vietnamese.DataWriteFailed=Không thể ghi vào thư mục dữ liệu đã chọn. Hãy chọn vị trí khác.
english.ReadyDataFolder=Data folder:
vietnamese.ReadyDataFolder=Thư mục dữ liệu:
english.ReadyApplicationFolder=Application folder:
vietnamese.ReadyApplicationFolder=Thư mục cài ứng dụng:
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
Source: "..\..\..\..\build\buildwin\dist\PRANA_ELEX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: application

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
  LocationsPage: TWizardPage;
  AppSectionLabel: TNewStaticText;
  AppIntroLabel: TNewStaticText;
  AppFolderLabel: TNewStaticText;
  AppPathEdit: TNewEdit;
  AppBrowseButton: TNewButton;
  DataSectionLabel: TNewStaticText;
  DataIntroLabel: TNewStaticText;
  DataFolderLabel: TNewStaticText;
  DataPathEdit: TNewEdit;
  DataBrowseButton: TNewButton;
  DataRetentionLabel: TNewStaticText;

function NormalizedPath(Path: String): String;
begin
  Result := RemoveBackslashUnlessRoot(ExpandFileName(Trim(Path)));
end;

function GetSelectedAppDir: String;
begin
  if Trim(AppPathEdit.Text) = '' then
    Result := ''
  else
    Result := NormalizedPath(AppPathEdit.Text);
end;

function GetSelectedDataDir(Param: String): String;
begin
  if Trim(DataPathEdit.Text) = '' then
    Result := ''
  else
    Result := NormalizedPath(DataPathEdit.Text);
end;

function IsPathInside(ChildPath, ParentPath: String): Boolean;
begin
  Result := Pos(
    Uppercase(AddBackslash(NormalizedPath(ParentPath))),
    Uppercase(AddBackslash(NormalizedPath(ChildPath)))
  ) = 1;
end;

procedure BrowseForAppFolder(Sender: TObject);
var
  SelectedPath: String;
begin
  SelectedPath := AppPathEdit.Text;
  if BrowseForFolder(CustomMessage('AppBrowseTitle'), SelectedPath, True) then
    AppPathEdit.Text := SelectedPath;
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
  LocationsPage := CreateCustomPage(
    wpSelectDir,
    CustomMessage('LocationsPageTitle'),
    CustomMessage('LocationsPageDescription')
  );

  AppSectionLabel := TNewStaticText.Create(LocationsPage.Surface);
  AppSectionLabel.Parent := LocationsPage.Surface;
  AppSectionLabel.Left := 0;
  AppSectionLabel.Top := ScaleY(4);
  AppSectionLabel.Font.Style := [fsBold];
  AppSectionLabel.Font.Color := $42340A;
  AppSectionLabel.Caption := CustomMessage('AppSectionTitle');

  AppIntroLabel := TNewStaticText.Create(LocationsPage.Surface);
  AppIntroLabel.Parent := LocationsPage.Surface;
  AppIntroLabel.Left := 0;
  AppIntroLabel.Top := ScaleY(26);
  AppIntroLabel.Width := LocationsPage.SurfaceWidth;
  AppIntroLabel.Height := ScaleY(32);
  AppIntroLabel.AutoSize := False;
  AppIntroLabel.WordWrap := True;
  AppIntroLabel.Caption := CustomMessage('AppIntro');

  AppFolderLabel := TNewStaticText.Create(LocationsPage.Surface);
  AppFolderLabel.Parent := LocationsPage.Surface;
  AppFolderLabel.Left := 0;
  AppFolderLabel.Top := ScaleY(64);
  AppFolderLabel.Caption := CustomMessage('AppFolderLabel');

  AppPathEdit := TNewEdit.Create(LocationsPage.Surface);
  AppPathEdit.Parent := LocationsPage.Surface;
  AppPathEdit.Left := 0;
  AppPathEdit.Top := ScaleY(84);
  AppPathEdit.Width := LocationsPage.SurfaceWidth - ScaleX(104);
  AppPathEdit.Height := ScaleY(30);
  AppPathEdit.Text := WizardDirValue;

  AppBrowseButton := TNewButton.Create(LocationsPage.Surface);
  AppBrowseButton.Parent := LocationsPage.Surface;
  AppBrowseButton.Left := LocationsPage.SurfaceWidth - ScaleX(96);
  AppBrowseButton.Top := AppPathEdit.Top - ScaleY(1);
  AppBrowseButton.Width := ScaleX(96);
  AppBrowseButton.Height := ScaleY(32);
  AppBrowseButton.Caption := CustomMessage('BrowseButton');
  AppBrowseButton.OnClick := @BrowseForAppFolder;

  DataSectionLabel := TNewStaticText.Create(LocationsPage.Surface);
  DataSectionLabel.Parent := LocationsPage.Surface;
  DataSectionLabel.Left := 0;
  DataSectionLabel.Top := ScaleY(128);
  DataSectionLabel.Font.Style := [fsBold];
  DataSectionLabel.Font.Color := $988A00;
  DataSectionLabel.Caption := CustomMessage('DataSectionTitle');

  DataIntroLabel := TNewStaticText.Create(LocationsPage.Surface);
  DataIntroLabel.Parent := LocationsPage.Surface;
  DataIntroLabel.Left := 0;
  DataIntroLabel.Top := ScaleY(150);
  DataIntroLabel.Width := LocationsPage.SurfaceWidth;
  DataIntroLabel.Height := ScaleY(32);
  DataIntroLabel.AutoSize := False;
  DataIntroLabel.WordWrap := True;
  DataIntroLabel.Caption := CustomMessage('DataIntro');

  DataFolderLabel := TNewStaticText.Create(LocationsPage.Surface);
  DataFolderLabel.Parent := LocationsPage.Surface;
  DataFolderLabel.Left := 0;
  DataFolderLabel.Top := ScaleY(188);
  DataFolderLabel.Caption := CustomMessage('DataFolderLabel');

  DataPathEdit := TNewEdit.Create(LocationsPage.Surface);
  DataPathEdit.Parent := LocationsPage.Surface;
  DataPathEdit.Left := 0;
  DataPathEdit.Top := ScaleY(208);
  DataPathEdit.Width := LocationsPage.SurfaceWidth - ScaleX(104);
  DataPathEdit.Height := ScaleY(30);

  DataBrowseButton := TNewButton.Create(LocationsPage.Surface);
  DataBrowseButton.Parent := LocationsPage.Surface;
  DataBrowseButton.Left := LocationsPage.SurfaceWidth - ScaleX(96);
  DataBrowseButton.Top := DataPathEdit.Top - ScaleY(1);
  DataBrowseButton.Width := ScaleX(96);
  DataBrowseButton.Height := ScaleY(32);
  DataBrowseButton.Caption := CustomMessage('BrowseButton');
  DataBrowseButton.OnClick := @BrowseForDataFolder;

  DataRetentionLabel := TNewStaticText.Create(LocationsPage.Surface);
  DataRetentionLabel.Parent := LocationsPage.Surface;
  DataRetentionLabel.Left := 0;
  DataRetentionLabel.Top := ScaleY(246);
  DataRetentionLabel.Width := LocationsPage.SurfaceWidth;
  DataRetentionLabel.Height := ScaleY(32);
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

function ValidateLocations: Boolean;
var
  AppPath: String;
  DataPath: String;
  DriveRoot: String;
  ProbePath: String;
begin
  Result := False;
  AppPath := GetSelectedAppDir;
  if AppPath = '' then
  begin
    MsgBox(CustomMessage('AppRequired'), mbError, MB_OK);
    Exit;
  end;

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

  if (CompareText(DataPath, AppPath) = 0) or IsPathInside(DataPath, AppPath) then
  begin
    MsgBox(CustomMessage('DataInsideAppRejected'), mbError, MB_OK);
    Exit;
  end;

  if IsPathInside(AppPath, DataPath) then
  begin
    MsgBox(CustomMessage('AppInsideDataRejected'), mbError, MB_OK);
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
  WizardForm.DirEdit.Text := AppPath;
  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = LocationsPage.ID then
    Result := ValidateLocations;
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

  Result := CustomMessage('ReadyApplicationFolder') + NewLine + Space + GetSelectedAppDir + NewLine + NewLine +
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
