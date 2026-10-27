param([string]$Root=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$textExt=@('.cmd','.ps1','.py','.md','.txt','.json','.csv','.toml','.cfg','.ini','.xml','.yml','.yaml','.gitattributes','.gitignore')
$Root=(Resolve-Path -LiteralPath $Root).Path.TrimEnd('\')
$sha=[Security.Cryptography.SHA256]::Create()
$lines=New-Object 'System.Collections.Generic.List[string]'
$files=Get-ChildItem -LiteralPath $Root -Recurse -File -Force | Where-Object {
 $rel=$_.FullName.Substring($Root.Length+1)
 $rel -ne 'SHA256SUMS.txt' -and $rel -notmatch '(^|\\)(\.git|__pycache__)(\\|$)' -and $_.Extension -ne '.pyc'
} | Sort-Object FullName
foreach ($f in $files) {
 $rel=$f.FullName.Substring($Root.Length+1).Replace('\','/')
 $bytes=[IO.File]::ReadAllBytes($f.FullName)
 if ($textExt -contains $f.Extension.ToLowerInvariant()) {
  $out=New-Object 'System.Collections.Generic.List[byte]' $bytes.Length
  for ($i=0;$i -lt $bytes.Length;$i++) { if ($bytes[$i] -eq 13 -and $i+1 -lt $bytes.Length -and $bytes[$i+1] -eq 10) { continue }; $out.Add($bytes[$i]) }
  $bytes=$out.ToArray()
 }
 $hash=(($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join '')
 $lines.Add($hash+'  '+$rel)
}
$sha.Dispose()
[IO.File]::WriteAllText((Join-Path $Root 'SHA256SUMS.txt'),(($lines -join "`n")+"`n"),(New-Object Text.UTF8Encoding $false))
Write-Host "SHA256SUMS.txt updated: $($lines.Count) files"
