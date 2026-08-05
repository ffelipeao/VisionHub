#define MyAppName "VisionHub"
#ifndef MyAppVersion
  #define MyAppVersion "1.1.0-beta.1"
#endif
#ifndef MyOutputBaseFilename
  #define MyOutputBaseFilename "VisionHub-1.1.0-beta.1-Windows-Setup"
#endif
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
OutputBaseFilename={#MyOutputBaseFilename}
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
