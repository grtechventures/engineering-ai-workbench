$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.venv\Scripts\python.exe')) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 first.' }
    & .venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
if (Test-Path 'data\worker-image.txt') {
    if (!$env:EWB_WORKER_IMAGE) { $env:EWB_WORKER_IMAGE = (Get-Content 'data\worker-image.txt' -Raw).Trim() }
}
if (Test-Path 'data\local-model.json') {
    $modelConfig = Get-Content 'data\local-model.json' -Raw | ConvertFrom-Json
    if (!$env:EWB_LOCAL_MODEL_URL) { $env:EWB_LOCAL_MODEL_URL = $modelConfig.url }
    if (!$env:EWB_LOCAL_MODEL) { $env:EWB_LOCAL_MODEL = $modelConfig.model }
}
& .venv\Scripts\python.exe scripts/setup.py
if ($LASTEXITCODE -ne 0) { throw 'C++ build failed. Use a Visual Studio Developer PowerShell or install clang++.' }
& .venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
