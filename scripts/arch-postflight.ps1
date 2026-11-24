$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (Get-Command graphify -ErrorAction SilentlyContinue) {
        graphify update .
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Warning "Graphify is unavailable. The code graph was not rebuilt."
    }

    if (Test-Path ".sentrux/baseline.json") {
        if (-not (Get-Command sentrux -ErrorAction SilentlyContinue)) {
            throw "Sentrux is required to compare with the existing baseline."
        }
        if (Test-Path ".sentrux/rules.toml") {
            sentrux check .
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
        sentrux gate .
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Warning "No Sentrux baseline found. Run arch-preflight.ps1 before editing."
    }
} finally {
    Pop-Location
}
