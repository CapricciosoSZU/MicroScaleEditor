param([string]$Python = 'python', [switch]$OCR, [string]$IndexUrl = 'https://pypi.org/simple')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
& '.\.venv\Scripts\python.exe' -m pip install --index-url $IndexUrl -r requirements.txt 'pytest>=8,<10'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your network or use -IndexUrl with a trusted mirror.' }
if ($OCR) {
    & '.\.venv\Scripts\python.exe' -m pip install --index-url $IndexUrl -r requirements-ocr.txt
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Optional OCR installation failed. Manual editing is still available.' }
}
Write-Host 'Ready: .\launch.ps1 -Examples'
