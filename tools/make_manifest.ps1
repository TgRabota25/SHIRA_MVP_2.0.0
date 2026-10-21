param([string]$Root=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$manifest=Join-Path $Root 'SHA256SUMS.txt'
$paths=@()
foreach ($line in Get-Content -LiteralPath $manifest -Encoding UTF8) {
 $line=$line.TrimStart([char]0xFEFF)
 if (!$line.Trim()) { continue }
 if ($line -notmatch '^([a-f0-9]{64})  (.+)$') { throw "Invalid manifest: $line" }
 $paths+=$Matches[2]
}
$out=New-Object System.Collections.Generic.List[string]
foreach ($rel in $paths) {
 $file=Join-Path $Root $rel
 if (!(Test-Path -LiteralPath $file -PathType Leaf)) { Write-Warning "Skipped (missing): $rel"; continue }
 $hash=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
 $out.Add("$hash  $rel")
}
$enc=New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($manifest,(($out -join "`n")+"`n"),$enc)
Write-Host "SHA256SUMS.txt updated: $($out.Count) files"
