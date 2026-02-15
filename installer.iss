[Setup]
AppName=HR Docs
AppVersion=1.0
DefaultDirName={autopf}\HR Docs
DefaultGroupName=HR Docs
OutputDir=Output
OutputBaseFilename=HRDocs_Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\HRDocs\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\HR Docs"; Filename: "{app}\HRDocs.exe"
Name: "{commondesktop}\HR Docs"; Filename: "{app}\HRDocs.exe"

[Run]
Filename: "{app}\HRDocs.exe"; Description: "Launch HR Docs"; Flags: nowait postinstall skipifsilent