param([string]$Root=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$count=0
foreach ($line in Get-Content -LiteralPath (Join-Path $Root 'SHA256SUMS.txt') -Encoding UTF8) {
 if (!$line.Trim()) { continue }
 if ($line -notmatch '^([a-f0-9]{64})  (.+)$') { throw "Invalid manifest: $line" }
 $expected=$Matches[1];$file=Join-Path $Root $Matches[2]
 if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw "File missing: $file" }
 if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw "Checksum mismatch: $file" }
 $count++
}
Write-Host "Integrity OK: $count files"
