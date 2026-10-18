#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef BundleDir
  #error BundleDir is required
#endif
#ifndef OutputPath
  #error OutputPath is required
#endif

[Setup]
AppId={{2474B373-802E-44B6-B098-DAE132586581}
AppName=Izlek
AppVersion={#AppVersion}
AppPublisher=Izlek contributors
AppPublisherURL=https://github.com/Teknoloji-Filozoflari/Izlek
DefaultDirName={localappdata}\Programs\Izlek
DefaultGroupName=Izlek
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\..\LICENSE
OutputDir={#OutputPath}
OutputBaseFilename=Izlek-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\izlek.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Izlek"; Filename: "{app}\izlek.exe"

[Run]
Filename: "{app}\izlek.exe"; Description: "Izlek"; Flags: nowait postinstall skipifsilent
