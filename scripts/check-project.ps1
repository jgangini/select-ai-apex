param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
& $Python -m unittest discover -s tests -v
exit $LASTEXITCODE
