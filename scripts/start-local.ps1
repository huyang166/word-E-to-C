$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host "[START] $Message"
}

function Test-PortListening {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Test-EnvValue {
    param(
        [string]$Path,
        [string]$Name
    )
    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match "^\s*$Name\s*=" } | Select-Object -First 1
    if (-not $line) {
        return $false
    }
    $value = ($line -split "=", 2)[1].Trim()
    return -not [string]::IsNullOrWhiteSpace($value)
}

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$Command
    )
    $escapedRoot = $ProjectRoot.Replace("'", "''")
    $windowCommand = @"
`$Host.UI.RawUI.WindowTitle = '$Title'
Set-Location -LiteralPath '$escapedRoot'
$Command
"@
    $encodedCommand = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($windowCommand))
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        $encodedCommand
    )
}

Write-Host "=========================================="
Write-Host "Word E-to-C Local Prototype"
Write-Host "=========================================="
Write-Host ""

if (-not (Test-Path -LiteralPath "backend/app/main.py")) {
    throw "Please run this script from the project root."
}

if (-not (Test-Path -LiteralPath ".env")) {
    Write-Host "[SETUP] .env was not found. Creating it from .env.example."
    Copy-Item -LiteralPath ".env.example" -Destination ".env" -Force
    Write-Host "Please fill OPENAI_API_KEY and OPENAI_MODEL in the opened Notepad window."
    Write-Host "Save the file, close Notepad, then double-click start-local.bat again."
    Start-Process -FilePath "notepad.exe" -ArgumentList (Join-Path $ProjectRoot ".env")
    exit 1
}

if (-not (Test-EnvValue -Path ".env" -Name "OPENAI_API_KEY")) {
    Write-Host "[WARN] OPENAI_API_KEY is empty. AI suggestions will be unavailable."
}
if (-not (Test-EnvValue -Path ".env" -Name "OPENAI_MODEL")) {
    Write-Host "[WARN] OPENAI_MODEL is empty. AI suggestions will be unavailable."
}

if (-not (Test-Path -LiteralPath ".venv/Scripts/python.exe")) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python was not found. Please install Python first."
    }
    Write-Step "Creating Python virtual environment..."
    python -m venv .venv
}

Write-Step "Checking backend dependencies..."
& ".\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"

if (-not (Test-Path -LiteralPath "frontend/node_modules/vite")) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm was not found. Please install Node.js first."
    }
    Write-Step "Installing frontend dependencies..."
    npm --prefix frontend install
}

if (Test-PortListening -Port 8000) {
    Write-Host "[SKIP] Port 8000 is already listening."
} else {
    Write-Step "Backend: http://127.0.0.1:8000"
    Start-ServiceWindow -Title "Word Sync Backend" -Command "& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000"
}

if (Test-PortListening -Port 5173) {
    Write-Host "[SKIP] Port 5173 is already listening."
} else {
    Write-Step "Frontend: http://127.0.0.1:5173"
    Start-ServiceWindow -Title "Word Sync Frontend" -Command "npm --prefix frontend run dev -- --port 5173"
}

Write-Host ""
Write-Host "[OPEN] http://127.0.0.1:5173"
Start-Sleep -Seconds 6
Start-Process "http://127.0.0.1:5173/"

Write-Host ""
Write-Host "Started. Close the Backend and Frontend command windows to stop the app."
