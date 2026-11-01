$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Chua co moi truong .venv. Xem README.md de cai dat Python va thu vien.'
}
Write-Host 'EPU Energy: http://127.0.0.1:5000 (Ctrl+C de dung)'
& $taskPython app.py
