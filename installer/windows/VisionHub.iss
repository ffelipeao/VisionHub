#define MyAppName "VisionHub"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ffelipeao"
#define MyAppExeName "VisionHub.exe"

[Setup]
AppId={{8D40D6DF-8AB2-4BEC-95BC-B2BCA4E0A311}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#SourcePath}\..\output
OutputBaseFilename=VisionHub-Windows-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile={#SourcePath}\..\..\LICENSE
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "{#SourcePath}\..\..\dist\VisionHub\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent
