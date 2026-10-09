param([switch]$Debug, [switch]$Examples, [string]$Image)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host 'Run setup.ps1 first to create the local virtual environment.'
    exit 1
}
$appArguments = @('-m', 'microscale')
if ($Debug) { $appArguments += '--debug' }
if ($Examples) { $appArguments += '--examples' }
if ($Image) { $appArguments += $Image }
& $pythonExe @appArguments
exit $LASTEXITCODE
