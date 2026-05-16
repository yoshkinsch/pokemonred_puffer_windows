<#
.SYNOPSIS
    One‑click Windows setup & training launcher for pokemonred_puffer_windows.
.DESCRIPTION
    This script assumes you have already installed:
      - Python 3.11.x (check path below)
      - Visual C++ Build Tools
      - A legally obtained Pokémon Red ROM renamed to "red.gb" in the repo folder.

    Run this script from the root of the cloned repository.
    It will:
      1. Create a Python 3.11 virtual environment (.venv)
      2. Install PyTorch (GPU auto‑detection)
      3. Install the pokemonred_puffer package in editable mode
      4. Apply Windows‑compatible config changes
      5. Launch training (by default, train with baseline reward)
.NOTES
    Author: Carson Kinsch
#>

#Requires -Version 5.1

# --- Configuration (adjust if needed) ------------------------------------
$Python311Path = ""   # Leave empty to auto‑detect. Otherwise set full path to python.exe

$TrainingMode = "train"          # "debug", "autotune", or "train"
$RewardWrapper = "baseline.CutWithObjectRewardRequiredEventsEnv"
$Wrapper = "stream_only"         # or "none" for no extra wrappers

# --------------------------------------------------------------------------

# Stop on errors
$ErrorActionPreference = "Stop"

# Helper: locate Python 3.11
function Find-Python311 {
    if ($Python311Path -and (Test-Path $Python311Path)) {
        return $Python311Path
    }

    # Common install locations
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "C:\Python311\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )

    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }

    # Try to find via where.exe
    $where = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if ($where -and (& $where --version 2>&1) -match "3\.11") {
        return $where
    }

    Write-Host "ERROR: Python 3.11 not found." -ForegroundColor Red
    Write-Host "Please install Python 3.11 from https://www.python.org/downloads/release/python-3119/" -ForegroundColor Yellow
    Write-Host "Then set `$Python311Path in this script or ensure it's in PATH." -ForegroundColor Yellow
    exit 1
}

$pythonExe = Find-Python311
Write-Host "Using Python: $pythonExe" -ForegroundColor Cyan

# --- Step 1: Create virtual environment -----------------------------------
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    & $pythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Venv creation failed. Try running: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Red
        exit 1
    }
}

# Activate the venv
$venvActivate = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
} else {
    Write-Host "Activate script not found. Exiting." -ForegroundColor Red
    exit 1
}

# Upgrade pip
python -m pip install --upgrade pip

# --- Step 2: Install PyTorch ----------------------------------------------
Write-Host "Detecting CUDA..." -ForegroundColor Cyan
$cudaVersion = $null
try {
    $nvcc = (Get-Command nvidia-smi -ErrorAction SilentlyContinue).Source
    if ($nvcc) {
        $cudaOutput = & nvidia-smi --query-gpu=driver_version --format=csv,noheader | Select-Object -First 1
        if ($cudaOutput -match "(\d+\.\d+)") {
            $cudaVersion = [double]$matches[1]
        }
    }
} catch {}

if ($cudaVersion) {
    Write-Host "CUDA driver version: $cudaVersion" -ForegroundColor Green
    if ($cudaVersion -ge 13.0) {
        Write-Host "Installing PyTorch nightly (CUDA 12.8) for Blackwell / RTX 50 series..." -ForegroundColor Cyan
        pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128
    } elseif ($cudaVersion -ge 12.0) {
        Write-Host "Installing PyTorch stable (CUDA 12.1)..." -ForegroundColor Cyan
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    } else {
        Write-Host "CUDA version older than 12.0. Installing CPU-only PyTorch." -ForegroundColor Yellow
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    }
} else {
    Write-Host "No CUDA GPU detected. Installing CPU-only PyTorch." -ForegroundColor Yellow
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
}

# --- Step 3: Install the package ------------------------------------------
Write-Host "Installing pokemonred_puffer package (editable)..." -ForegroundColor Cyan
pip install -e .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Regular install failed, trying with --no-build-isolation..." -ForegroundColor Yellow
    pip install -e . --no-build-isolation
}

# --- Step 4: Apply Windows config fixes -----------------------------------
Write-Host "Applying Windows configuration fixes..." -ForegroundColor Cyan

# Disable SQLite swarm wrapper (causes file lock on Windows)
$configFile = "config.yaml"
if (Test-Path $configFile) {
    $yaml = Get-Content $configFile -Raw
    # Set sqlite_wrapper to false
    $yaml = $yaml -replace 'sqlite_wrapper:\s*true', 'sqlite_wrapper: false'
    # Comment out one_epoch block (prevent early stopping)
    $yaml = $yaml -replace '(?ms)^one_epoch:.*?^(\S)', '# one_epoch block disabled for Windows training'
    # Ensure save_video is False
    $yaml = $yaml -replace 'save_video:\s*True', 'save_video: False'
    Set-Content -Path $configFile -Value $yaml
    Write-Host "Config updated." -ForegroundColor Green
} else {
    Write-Host "config.yaml not found. Ensure you are in the repository root." -ForegroundColor Red
    exit 1
}

# --- Step 5: Set wandb offline (if not already set) -----------------------
$env:WANDB_MODE = "offline"

# --- Step 6: Check for ROM ------------------------------------------------
if (-not (Test-Path "red.gb")) {
    Write-Host "ERROR: red.gb not found in the repository folder." -ForegroundColor Red
    Write-Host "Please place your Pokémon Red ROM (SHA1: ea9bcae617fdf159b045185467ae58b2e4a48b9a) as 'red.gb' and re-run this script." -ForegroundColor Yellow
    exit 1
}

# --- Step 7: Run training -------------------------------------------------
Write-Host "Starting training (mode: $TrainingMode)..." -ForegroundColor Cyan
$cmd = "python -m pokemonred_puffer.train $TrainingMode"
if ($TrainingMode -eq "train") {
    $cmd += " -r $RewardWrapper -w $Wrapper"
}

Invoke-Expression $cmd