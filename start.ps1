$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.venv\Scripts\python.exe')) {
    throw 'Provision .venv and dependencies first; startup never downloads packages. See README offline setup.'
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
