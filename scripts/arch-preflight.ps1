$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (Test-Path "graphify-out/GRAPH_REPORT.md") {
        Get-Content "graphify-out/GRAPH_REPORT.md" -TotalCount 80
    }

    if (Get-Command sentrux -ErrorAction SilentlyContinue) {
        sentrux gate --save .
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        if (Test-Path ".sentrux/rules.toml") {
            sentrux check .
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
    } else {
        Write-Warning "Sentrux is unavailable. No baseline was saved."
    }
} finally {
    Pop-Location
}
