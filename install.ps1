$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment setup failed.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PSScriptRoot '.browsers'
& '.\.venv\Scripts\python.exe' -m playwright install chromium --only-shell
if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed.' }
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
Write-Output 'Installed. Start with .venv/Scripts/python.exe run.py'
