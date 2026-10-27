param([string]$Root=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$textExt=@('.cmd','.ps1','.py','.md','.txt','.json','.csv','.toml','.cfg','.ini','.xml','.yml','.yaml','.gitattributes','.gitignore')
function Get-Sha([byte[]]$bytes){
 $sha=[Security.Cryptography.SHA256]::Create()
 try { return (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join '') } finally { $sha.Dispose() }
}
function Normalize-Lf([byte[]]$bytes){
 $out=New-Object 'System.Collections.Generic.List[byte]' $bytes.Length
 for ($i=0;$i -lt $bytes.Length;$i++) {
  if ($bytes[$i] -eq 13 -and $i+1 -lt $bytes.Length -and $bytes[$i+1] -eq 10) { continue }
  $out.Add($bytes[$i])
 }
 return ,$out.ToArray()
}
function Expand-Crlf([byte[]]$lf){
 $out=New-Object 'System.Collections.Generic.List[byte]' ($lf.Length+256)
 foreach ($b in $lf) { if ($b -eq 10) { $out.Add(13) }; $out.Add($b) }
 return ,$out.ToArray()
}
$count=0
foreach ($line in Get-Content -LiteralPath (Join-Path $Root 'SHA256SUMS.txt') -Encoding UTF8) {
 if (!$line.Trim()) { continue }
 if ($line -notmatch '^([a-f0-9]{64})  (.+)$') { throw "Invalid manifest: $line" }
 $expected=$Matches[1];$file=Join-Path $Root $Matches[2]
 if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw "File missing: $file" }
 $bytes=[IO.File]::ReadAllBytes($file)
 $ok=((Get-Sha $bytes) -eq $expected)
 if (!$ok -and ($textExt -contains [IO.Path]::GetExtension($file).ToLowerInvariant())) {
  $lf=Normalize-Lf $bytes
  $ok=((Get-Sha $lf) -eq $expected) -or ((Get-Sha (Expand-Crlf $lf)) -eq $expected)
 }
 if (!$ok) { throw "Checksum mismatch: $file (if you edited files, run tools\make_checksums.ps1)" }
 $count++
}
Write-Host "Integrity OK: $count files"
