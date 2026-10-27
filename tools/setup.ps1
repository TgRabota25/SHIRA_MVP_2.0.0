$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$root=Split-Path -Parent $PSScriptRoot
$base=Join-Path $env:LOCALAPPDATA 'SHIRA_MVP'
New-Item -ItemType Directory -Path $base -Force | Out-Null
$log=Join-Path $base 'installation-v2.log'
Start-Transcript -Path $log -Append | Out-Null
try {
 if (![Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') { throw 'Windows x64 required; x86 and ARM64 not supported.' }
 if ([Environment]::OSVersion.Version.Major -lt 10) { throw 'Windows 10/11 x64 required.' }
 if ($root.StartsWith('\\')) { throw 'Extract ZIP to a local drive, not a network share.' }
 Write-Host 'SHIRA 2.0 offline setup. Keep the extracted folder after installation.'
 & (Join-Path $PSScriptRoot 'verify.ps1') -Root $root
 $drive=Get-PSDrive -Name ([IO.Path]::GetPathRoot($base).Substring(0,1)) -ErrorAction SilentlyContinue
 if ($drive -and $drive.Free -lt 2GB) { throw 'At least 2 GB free disk space required.' }
 $venv=Join-Path $base 'venv'
 $running=Get-Process python,pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$venv\*" }
 if ($running) { throw 'Close all SHIRA windows, diagnostics and batch processing before updating.' }
 $vcKey=Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' -ErrorAction SilentlyContinue
 if (!$vcKey -or $vcKey.Installed -ne 1 -or [int]$vcKey.Minor -lt 40) {
  Write-Host 'Installing Microsoft Visual C++ runtime. Windows may request administrator approval.'
  $p=Start-Process -FilePath (Join-Path $root 'vendor\vc_redist.x64.exe') -ArgumentList '/install /passive /norestart' -Verb RunAs -Wait -PassThru
  if ($p.ExitCode -notin @(0,3010,1638)) { throw "VC++ setup failed: $($p.ExitCode)" }
  if ($p.ExitCode -eq 3010) { Write-Warning 'Windows requests restart. Restart and rerun setup if diagnostics fail.' }
 }
 $runtime=Join-Path $env:LOCALAPPDATA 'SHIRA_Runtime\Python31316'
 $python=Join-Path $runtime 'python.exe'
 if (!(Test-Path -LiteralPath $python)) {
  $args=@('/quiet','InstallAllUsers=0',('TargetDir="'+$runtime+'"'),'Include_pip=1','Include_tcltk=1','Include_launcher=0','InstallLauncherAllUsers=0','Include_test=0','Include_doc=0','AssociateFiles=0','Shortcuts=0','PrependPath=0')
  $p=Start-Process -FilePath (Join-Path $root 'vendor\python-3.13.16-amd64.exe') -ArgumentList $args -Wait -PassThru
  if ($p.ExitCode -notin @(0,3010,1638)) { throw "Python setup failed: $($p.ExitCode)" }
 }
 if (!(Test-Path -LiteralPath $python)) {
  foreach ($key in @('HKCU:\Software\Python\PythonCore\3.13\InstallPath','HKLM:\Software\Python\PythonCore\3.13\InstallPath')) {
   if (Test-Path $key) {
    $candidate=Join-Path ((Get-Item $key).GetValue('')) 'python.exe'
    if (Test-Path -LiteralPath $candidate) { $python=$candidate; break }
   }
  }
 }
 if (!(Test-Path -LiteralPath $python)) { throw 'Python not found after installation.' }
 & $python -c "import struct,sys,tkinter;assert struct.calcsize('P')==8 and sys.version_info[:2]==(3,13) and sys.version_info[:3]>=(3,13,16), 'Python 3.13.16+ x64 with Tk required'"
 if ($LASTEXITCODE -ne 0) { throw 'Python/Tk/architecture check failed.' }
 if (!(Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe'))) {
  & $python -m venv $venv
  if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
 }
 $python=Join-Path $venv 'Scripts\python.exe'
 & $python -m pip install --disable-pip-version-check --no-index --only-binary=:all: --find-links (Join-Path $root 'wheels') --require-hashes -r (Join-Path $root 'requirements-windows-lock.txt')
 if ($LASTEXITCODE -ne 0) { throw 'Offline dependency install failed.' }
 & $python -m pip check
 if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
 & $python (Join-Path $root 'tools\doctor.py')
 if ($LASTEXITCODE -ne 0) { throw 'Local diagnostics failed. See diagnostics-v2.json in LOCALAPPDATA\SHIRA_MVP.' }
 $shell=New-Object -ComObject WScript.Shell
 $shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'SHIRA MVP.lnk'))
 $shortcut.TargetPath=Join-Path $venv 'Scripts\pythonw.exe'
 $shortcut.Arguments='"'+(Join-Path $root 'tools\launch.py')+'"'
 $shortcut.WorkingDirectory=$root
 $shortcut.IconLocation=Join-Path $root 'app\icon.ico'
 $shortcut.Save()
 Write-Host 'SUCCESS. Start SHIRA MVP desktop shortcut or 02_START.cmd.' -ForegroundColor Green
 Write-Host 'Old database is not deleted. New index is index-v2.sqlite3. Read README_RU.md.'
 Start-Process -FilePath (Join-Path $venv 'Scripts\pythonw.exe') -ArgumentList ('"'+(Join-Path $root 'tools\launch.py')+'"') -WorkingDirectory $root | Out-Null
 Stop-Transcript | Out-Null
 exit 0
} catch {
 Write-Host ('SETUP FAILED: '+$_.Exception.Message) -ForegroundColor Red
 Write-Host ('Log: '+$log)
 Stop-Transcript | Out-Null
 exit 1
}
