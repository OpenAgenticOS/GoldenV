; GoldenV Inno Setup 安装脚本

#define AppName "黄金镯子检测系统"
#define AppVersion "1.0.0"
#define AppPublisher "GoldenV"
#define AppExeName "GoldenV.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\GoldenV
DefaultGroupName={#AppName}
OutputDir=..\Output
OutputBaseFilename=GoldenV_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"

[Files]
Source: "..\dist\GoldenV\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "redist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist; Check: VCRedistNeeded

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "安装 Visual C++ 运行库..."; Check: VCRedistNeededAndExists; Flags: waituntilterminated

[Code]
function VCRedistNeeded: Boolean;
begin
  Result := not RegKeyExists(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64');
end;

function VCRedistNeededAndExists: Boolean;
begin
  Result := VCRedistNeeded and FileExists(ExpandConstant('{tmp}\vc_redist.x64.exe'));
end;

[Dirs]
Name: "{commonappdata}\GoldenV\configs"; Permissions: users-modify
Name: "{commonappdata}\GoldenV\logs"; Permissions: users-modify
Name: "{commonappdata}\GoldenV\data"; Permissions: users-modify
