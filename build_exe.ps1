param([switch]$InstallBuildTools, [string]$IndexUrl = 'https://pypi.org/simple')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run setup.ps1 -OCR first.' }
if ($InstallBuildTools) {
    & $taskPython -m pip install --index-url $IndexUrl -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Build tool installation failed.' }
}
& $taskPython -c 'import PyInstaller, rapidocr_onnxruntime, onnxruntime, PySide6, imagecodecs; assert imagecodecs.LZW.available'
if ($LASTEXITCODE -ne 0) { throw 'Install requirements-build.txt and requirements-ocr.txt first.' }
$appVersion = & $taskPython -c 'from microscale import __version__; print(__version__)'
& $taskPython -m PyInstaller --noconfirm --distpath "dist\v$appVersion" MicroScaleEditor.spec
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed; inspect build\MicroScaleEditor\warn-MicroScaleEditor.txt.' }
Write-Host "Built dist\v$appVersion\MicroScaleEditor.exe. Run the standalone self-test before distributing it."
