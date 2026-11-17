param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "installer"
& $Python -m unittest discover -s tests -v
exit $LASTEXITCODE
