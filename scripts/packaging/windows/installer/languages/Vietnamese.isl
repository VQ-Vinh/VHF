; PRANA ELEX Vietnamese language overlay for Inno Setup 6.5+
; UTF-8, no BOM. Unlisted low-level messages fall back to compiler:Default.isl.

[LangOptions]
LanguageName=Tiếng Việt
LanguageID=$042A
LanguageCodePage=0
DialogFontName=Segoe UI
DialogFontSize=9
WelcomeFontName=Segoe UI
WelcomeFontSize=14

[Messages]
SetupAppTitle=Cài đặt
SetupWindowTitle=Cài đặt - %1
UninstallAppTitle=Gỡ cài đặt
UninstallAppFullTitle=Gỡ cài đặt %1
InformationTitle=Thông tin
ConfirmTitle=Xác nhận
ErrorTitle=Lỗi
SetupLdrStartupMessage=Chương trình sẽ cài đặt %1. Bạn có muốn tiếp tục không?
LdrCannotCreateTemp=Không thể tạo tệp tạm. Quá trình cài đặt đã dừng
LdrCannotExecTemp=Không thể chạy tệp trong thư mục tạm. Quá trình cài đặt đã dừng
SetupFileMissing=Thiếu tệp %1 trong thư mục cài đặt. Vui lòng tải lại bộ cài đặt.
SetupFileCorrupt=Các tệp cài đặt đã hỏng. Vui lòng tải lại bộ cài đặt.
SetupFileCorruptOrWrongVer=Các tệp cài đặt đã hỏng hoặc không tương thích. Vui lòng tải lại bộ cài đặt.
InvalidParameter=Tham số dòng lệnh không hợp lệ:%n%n%1
SetupAlreadyRunning=Chương trình cài đặt đang chạy.
WindowsVersionNotSupported=Chương trình không hỗ trợ phiên bản Windows trên máy tính này.
OnlyOnTheseArchitectures=Chương trình chỉ có thể cài đặt trên Windows dành cho các kiến trúc bộ xử lý sau:%n%n%1
WinVersionTooLowError=Chương trình yêu cầu %1 phiên bản %2 trở lên.
AdminPrivilegesRequired=Bạn phải đăng nhập bằng tài khoản quản trị viên để cài đặt chương trình.
SetupAppRunningError=Trình cài đặt phát hiện %1 đang chạy.%n%nHãy đóng ứng dụng rồi bấm OK để tiếp tục, hoặc bấm Hủy để thoát.
UninstallAppRunningError=Trình gỡ cài đặt phát hiện %1 đang chạy.%n%nHãy đóng ứng dụng rồi bấm OK để tiếp tục, hoặc bấm Hủy để thoát.

PrivilegesRequiredOverrideTitle=Chọn phạm vi cài đặt
PrivilegesRequiredOverrideInstruction=Chọn phạm vi cài đặt
PrivilegesRequiredOverrideText1=%1 có thể được cài cho mọi người dùng (cần quyền quản trị viên), hoặc chỉ cho tài khoản của bạn.
PrivilegesRequiredOverrideText2=%1 có thể được cài chỉ cho tài khoản của bạn, hoặc cho mọi người dùng (cần quyền quản trị viên).
PrivilegesRequiredOverrideAllUsers=Cài cho &mọi người dùng
PrivilegesRequiredOverrideAllUsersRecommended=Cài cho &mọi người dùng (khuyến nghị)
PrivilegesRequiredOverrideCurrentUser=Chỉ cài cho &tôi
PrivilegesRequiredOverrideCurrentUserRecommended=Chỉ cài cho &tôi (khuyến nghị)

ErrorCreatingDir=Không thể tạo thư mục "%1"
ExitSetupTitle=Thoát cài đặt
ExitSetupMessage=Quá trình cài đặt chưa hoàn tất. Nếu thoát bây giờ, chương trình sẽ không được cài đặt.%n%nBạn có muốn thoát không?
ButtonBack=< &Quay lại
ButtonNext=&Tiếp theo >
ButtonInstall=&Cài đặt
ButtonOK=OK
ButtonCancel=Hủy
ButtonYes=&Có
ButtonYesToAll=Có với &tất cả
ButtonNo=&Không
ButtonNoToAll=K&hông với tất cả
ButtonFinish=&Hoàn tất
ButtonBrowse=&Duyệt...
ButtonWizardBrowse=D&uyệt...
ButtonNewFolder=&Tạo thư mục mới

SelectLanguageTitle=Chọn ngôn ngữ cài đặt
SelectLanguageLabel=Chọn ngôn ngữ sử dụng trong quá trình cài đặt.
ClickNext=Bấm Tiếp theo để tiếp tục, hoặc Hủy để thoát.
BrowseDialogTitle=Chọn thư mục
BrowseDialogLabel=Chọn một thư mục trong danh sách rồi bấm OK.
NewFolderName=Thư mục mới

WelcomeLabel1=Chào mừng đến với trình cài đặt [name]
WelcomeLabel2=Chương trình sẽ cài đặt [name/ver] trên máy tính.%n%nBạn nên đóng các ứng dụng khác trước khi tiếp tục.

WizardSelectDir=Chọn thư mục cài đặt
SelectDirDesc=[name] sẽ được cài đặt ở đâu?
SelectDirLabel3=Chương trình sẽ cài [name] vào thư mục sau.
SelectDirBrowseLabel=Bấm Tiếp theo để tiếp tục. Để chọn thư mục khác, bấm Duyệt.
DiskSpaceGBLabel=Cần ít nhất [gb] GB dung lượng trống.
DiskSpaceMBLabel=Cần ít nhất [mb] MB dung lượng trống.
CannotInstallToNetworkDrive=Không thể cài đặt vào ổ đĩa mạng.
CannotInstallToUNCPath=Không thể cài đặt vào đường dẫn UNC.
InvalidPath=Bạn phải nhập đường dẫn đầy đủ kèm ký tự ổ đĩa, ví dụ:%n%nC:\APP
InvalidDrive=Ổ đĩa hoặc vị trí đã chọn không tồn tại hay không thể truy cập. Vui lòng chọn vị trí khác.
DiskSpaceWarningTitle=Không đủ dung lượng
DiskSpaceWarning=Trình cài đặt cần ít nhất %1 KB nhưng ổ đĩa chỉ còn %2 KB.%n%nBạn vẫn muốn tiếp tục không?
DirNameTooLong=Tên hoặc đường dẫn thư mục quá dài.
InvalidDirName=Tên thư mục không hợp lệ.
DirExistsTitle=Thư mục đã tồn tại
DirExists=Thư mục sau đã tồn tại:%n%n%1%n%nBạn có muốn cài đặt vào thư mục này không?
DirDoesntExistTitle=Thư mục chưa tồn tại
DirDoesntExist=Thư mục sau chưa tồn tại:%n%n%1%n%nBạn có muốn tạo thư mục này không?

WizardSelectComponents=Chọn thành phần
SelectComponentsDesc=Những thành phần nào sẽ được cài đặt?
SelectComponentsLabel2=Chọn các thành phần cần cài đặt rồi bấm Tiếp theo.
FullInstallation=Cài đặt đầy đủ
CompactInstallation=Cài đặt thu gọn
CustomInstallation=Cài đặt tùy chỉnh
WizardSelectTasks=Chọn tùy chọn bổ sung
SelectTasksDesc=Những tùy chọn bổ sung nào sẽ được thực hiện?
SelectTasksLabel2=Chọn các tùy chọn cần thực hiện khi cài [name], sau đó bấm Tiếp theo.
WizardSelectProgramGroup=Chọn thư mục Start Menu
SelectStartMenuFolderDesc=Đặt lối tắt của chương trình ở đâu?
SelectStartMenuFolderLabel3=Trình cài đặt sẽ tạo lối tắt trong thư mục Start Menu sau.
SelectStartMenuFolderBrowseLabel=Bấm Tiếp theo để tiếp tục. Để chọn thư mục khác, bấm Duyệt.
NoProgramGroupCheck2=&Không tạo thư mục Start Menu

WizardReady=Sẵn sàng cài đặt
ReadyLabel1=Trình cài đặt đã sẵn sàng cài [name] trên máy tính.
ReadyLabel2a=Bấm Cài đặt để tiếp tục, hoặc bấm Quay lại để xem và thay đổi thiết lập.
ReadyLabel2b=Bấm Cài đặt để tiếp tục.
ReadyMemoUserInfo=Thông tin người dùng:
ReadyMemoDir=Thư mục cài đặt:
ReadyMemoType=Kiểu cài đặt:
ReadyMemoComponents=Thành phần đã chọn:
ReadyMemoGroup=Thư mục Start Menu:
ReadyMemoTasks=Tùy chọn bổ sung:

WizardPreparing=Đang chuẩn bị cài đặt
PreparingDesc=Đang chuẩn bị cài [name] trên máy tính.
PreviousInstallNotCompleted=Quá trình cài đặt hoặc gỡ cài đặt trước chưa hoàn tất. Bạn cần khởi động lại máy tính rồi chạy lại bộ cài.
CannotContinue=Không thể tiếp tục. Bấm Hủy để thoát.
ApplicationsFound=Các ứng dụng sau đang sử dụng tệp cần được cập nhật. Bạn nên cho phép trình cài đặt tự động đóng các ứng dụng này.
ApplicationsFound2=Các ứng dụng sau đang sử dụng tệp cần được cập nhật. Trình cài đặt sẽ thử khởi động lại chúng sau khi hoàn tất.
CloseApplications=&Tự động đóng các ứng dụng
DontCloseApplications=&Không đóng các ứng dụng
ErrorCloseApplications=Không thể tự động đóng tất cả ứng dụng. Vui lòng tự đóng các ứng dụng đang sử dụng tệp cần cập nhật.

WizardInstalling=Đang cài đặt
InstallingLabel=Vui lòng chờ trong khi [name] được cài đặt trên máy tính.
FinishedHeadingLabel=Hoàn tất cài đặt [name]
FinishedLabelNoIcons=Đã cài đặt [name] trên máy tính.
FinishedLabel=Đã cài đặt [name] trên máy tính. Bạn có thể mở ứng dụng từ các lối tắt đã tạo.
ClickFinish=Bấm Hoàn tất để đóng trình cài đặt.
FinishedRestartLabel=Để hoàn tất cài đặt [name], bạn phải khởi động lại máy tính. Bạn có muốn khởi động lại ngay không?
FinishedRestartMessage=Để hoàn tất cài đặt [name], bạn phải khởi động lại máy tính.%n%nBạn có muốn khởi động lại ngay không?
RunEntryExec=Chạy %1

SetupAborted=Quá trình cài đặt chưa hoàn tất.%n%nVui lòng khắc phục sự cố rồi chạy lại bộ cài.
AbortRetryIgnoreSelectAction=Chọn hành động
AbortRetryIgnoreRetry=&Thử lại
AbortRetryIgnoreIgnore=&Bỏ qua lỗi và tiếp tục
AbortRetryIgnoreCancel=Hủy cài đặt
RetryCancelSelectAction=Chọn hành động
RetryCancelRetry=&Thử lại
RetryCancelCancel=Hủy
StatusClosingApplications=Đang đóng ứng dụng...
StatusCreateDirs=Đang tạo thư mục...
StatusExtractFiles=Đang giải nén tệp...
StatusCreateIcons=Đang tạo lối tắt...
StatusCreateIniEntries=Đang tạo thiết lập INI...
StatusCreateRegistryEntries=Đang cập nhật Registry...
StatusSavingUninstall=Đang lưu thông tin gỡ cài đặt...
StatusRunProgram=Đang hoàn tất cài đặt...
StatusRestartingApplications=Đang khởi động lại ứng dụng...
StatusRollback=Đang hoàn tác thay đổi...
ErrorExecutingProgram=Không thể chạy tệp:%n%1
ErrorCreatingTemp=Đã xảy ra lỗi khi tạo tệp trong thư mục đích:
ErrorReadingSource=Đã xảy ra lỗi khi đọc tệp nguồn:
ErrorCopying=Đã xảy ra lỗi khi sao chép tệp:
ErrorReplacingExistingFile=Đã xảy ra lỗi khi thay thế tệp hiện có:
ExistingFileReadOnly2=Không thể thay thế tệp hiện có vì tệp đang ở chế độ chỉ đọc.
ExistingFileReadOnlyRetry=&Bỏ thuộc tính chỉ đọc và thử lại
ExistingFileReadOnlyKeepExisting=&Giữ tệp hiện có
FileExistsSelectAction=Chọn hành động
FileExists2=Tệp đã tồn tại.
FileExistsOverwriteExisting=&Ghi đè tệp hiện có
FileExistsKeepExisting=&Giữ tệp hiện có
ExistingFileNewerSelectAction=Chọn hành động
ExistingFileNewer2=Tệp hiện có mới hơn tệp mà trình cài đặt đang sử dụng.
ExistingFileNewerOverwriteExisting=&Ghi đè tệp hiện có
ExistingFileNewerKeepExisting=&Giữ tệp hiện có (khuyến nghị)

UninstallDisplayNameMark64Bit=64-bit
UninstallDisplayNameMarkAllUsers=Mọi người dùng
UninstallDisplayNameMarkCurrentUser=Người dùng hiện tại
UninstallNotFound=Không tồn tại tệp "%1". Không thể gỡ cài đặt.
UninstallOpenError=Không thể mở tệp "%1". Không thể gỡ cài đặt
ConfirmUninstall=Bạn có chắc muốn gỡ hoàn toàn %1 và tất cả thành phần của ứng dụng không?
UninstallOnlyOnWin64=Chỉ có thể gỡ bản cài đặt này trên Windows 64-bit.
OnlyAdminCanUninstall=Chỉ người dùng có quyền quản trị viên mới có thể gỡ bản cài đặt này.
UninstallStatusLabel=Vui lòng chờ trong khi %1 được gỡ khỏi máy tính.
UninstalledAll=Đã gỡ %1 khỏi máy tính.
UninstalledMost=Đã hoàn tất gỡ %1.%n%nMột số thành phần chưa thể xóa và có thể được xóa thủ công.
UninstalledAndNeedsRestart=Để hoàn tất gỡ %1, bạn phải khởi động lại máy tính.%n%nBạn có muốn khởi động lại ngay không?
UninstallDataCorrupted=Tệp "%1" bị hỏng. Không thể gỡ cài đặt
WizardUninstalling=Trạng thái gỡ cài đặt
StatusUninstalling=Đang gỡ %1...
ShutdownBlockReasonInstallingApp=Đang cài đặt %1.
ShutdownBlockReasonUninstallingApp=Đang gỡ cài đặt %1.

[CustomMessages]
NameAndVersion=%1 phiên bản %2
AdditionalIcons=Lối tắt bổ sung:
CreateDesktopIcon=Tạo lối tắt trên &màn hình nền
UninstallProgram=Gỡ cài đặt %1
LaunchProgram=Mở %1
AutoStartProgramGroupDescription=Khởi động cùng Windows:
AutoStartProgram=Tự động khởi động %1
