param([string]$Root=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$count=0
$textExt=@('.cmd','.bat','.ps1','.py','.txt','.md','.json')

function Get-Sha([byte[]]$bytes) {
 $sha=[Security.Cryptography.SHA256]::Create()
 try { return ([BitConverter]::ToString($sha.ComputeHash($bytes)) -replace '-','').ToLowerInvariant() } finally { $sha.Dispose() }
}

function Get-Candidates([string]$file) {
 $bytes=[IO.File]::ReadAllBytes($file)
 $set=@(Get-Sha $bytes)
 if ($textExt -contains [IO.Path]::GetExtension($file).ToLowerInvariant()) {
  $s=[Text.Encoding]::UTF8.GetString($bytes)
  $lf=$s -replace "`r`n","`n"
  $crlf=$lf -replace "`n","`r`n"
  $set+=Get-Sha ([Text.Encoding]::UTF8.GetBytes($lf))
  $set+=Get-Sha ([Text.Encoding]::UTF8.GetBytes($crlf))
 }
 return $set
}

foreach ($line in Get-Content -LiteralPath (Join-Path $Root 'SHA256SUMS.txt') -Encoding UTF8) {
 $line=$line.TrimStart([char]0xFEFF)
 if (!$line.Trim()) { continue }
 if ($line -notmatch '^([a-f0-9]{64})  (.+)$') { throw "Invalid manifest: $line" }
 $expected=$Matches[1];$file=Join-Path $Root $Matches[2]
 if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw "File missing: $file" }
 if ((Get-Candidates $file) -notcontains $expected) { throw "Checksum mismatch: $file. If you edited files yourself, run: powershell -ExecutionPolicy Bypass -File tools\make_manifest.ps1" }
 $count++
}
Write-Host "Integrity OK: $count files"
