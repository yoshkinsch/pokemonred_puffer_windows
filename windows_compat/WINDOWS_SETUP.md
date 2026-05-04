# Windows Setup Guide — pokemonred_puffer_windows

> **Goal:** Run the Pokémon Red RL agent on Windows 10/11 natively — no WSL2, no VM, no Linux required.
> **Status:** Verified working on Windows 11 with Python 3.11.1, RTX 5080 Laptop, CUDA 13.1 driver.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | **3.11.x only** | 3.12+ is NOT supported. 3.10 also works. |
| Git | Any recent | https://git-scm.com/download/win |
| Visual C++ Build Tools | 2019 or 2022 | Required for Cython/numba compilation |
| NVIDIA GPU Driver | Any recent | Optional but strongly recommended |
| ffmpeg | Any recent | Required only for video recording |

> ⚠️ **Python 3.12+ is NOT supported.** The `pyproject.toml` caps at `< 3.12`. Use Python **3.11.x**.

---

## Step 1 — Install Python 3.11

1. Download the **Windows installer (64-bit)** for Python 3.11.x from:  
   https://www.python.org/downloads/release/python-3119/
2. Run the installer.
3. **Do NOT check "Add to PATH"** if you already have another Python version installed system-wide — you will reference it by full path when creating the venv.

To find where it installed:
```powershell
C:\Users\<YourUsername>\AppData\Local\Programs\Python\Python311\python.exe --version
```
It should print `Python 3.11.x`.

---

## Step 2 — Install Visual C++ Build Tools

Some dependencies (numba, Cython extensions) require a C compiler on Windows.

1. Download **Build Tools for Visual Studio 2022** from:  
   https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Run the installer and select **"Desktop development with C++"**.
3. Reboot if prompted.

---

## Step 3 — Clone the Repository (should already be done)

Open **PowerShell** or the **VS Code integrated terminal**:

```powershell
git clone https://github.com/yoshkinsch/pokemonred_puffer_windows.git
cd pokemonred_puffer_windows
```

Open this folder in VS Code: **File → Open Folder → pokemonred_puffer_windows**

---

## Step 4 — Create a Virtual Environment with Python 3.11

Run this from inside the repo folder. Use the **full path** to Python 3.11 to ensure the correct version is used:

```powershell
C:\Users\<YourUsername>\AppData\Local\Programs\Python\Python311\python.exe -m venv .venv
```

If you hit an execution policy error, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Activate the virtual environment:
```powershell
.venv\Scripts\activate
```

You should see `(.venv)` at the start of your terminal prompt. Upgrade pip:
```powershell
python -m pip install --upgrade pip
```

---

## Step 5 — Install PyTorch

### Check Your CUDA Version First

```powershell
nvidia-smi
```

Look at the top-right corner for `CUDA Version: XX.X`.

### RTX 40-series or older (CUDA 12.x drivers)

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### RTX 50-series / Blackwell (CUDA 13.x drivers)

The RTX 5080 and other Blackwell cards require **PyTorch nightly with CUDA 12.8**:

```powershell
pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128
```

### CPU Only (no GPU)

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Verify PyTorch Installation

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Expected output (GPU example):
```
2.12.0.dev20260408+cu128
True
NVIDIA GeForce RTX 5080 Laptop GPU
```

---

## Step 6 — Install the Package

```powershell
pip install -e .
```

This will take several minutes — it compiles Cython extensions and pulls PufferLib from GitHub. You will see C compiler warnings during the build. **These are normal and harmless.**

If the install fails, try:
```powershell
pip install -e . --no-build-isolation
```

### What Gets Installed

- PyBoy (Game Boy emulator)
- PufferLib (RL environment vectorization)
- numba + llvmlite (JIT compilation for reward functions)
- gymnasium, gym (environment APIs)
- wandb (experiment tracking)
- scipy, scikit-image, opencv-python (scientific computing)
- mediapy (video recording, requires ffmpeg separately)

---

## Step 7 — Add Your ROM

Place your legally () obtained **Pokémon Red** ROM in the repo root directory. Rename it to:

```
red.gb
```

> The ROM is not included for legal reasons. The SHA1 of the correct ROM is:  
> `ea9bcae617fdf159b045185467ae58b2e4a48b9a`  
> Verify with: `certutil -hashfile red.gb SHA1`

---

## Step 8 — Configure wandb

Training uses Weights & Biases for logging. Either log in or run offline:

**Option A — Offline (no account needed, recommended for quick start):**
```powershell
$env:WANDB_MODE = "offline"
```

**Option B — Online (requires free wandb account):**
```powershell
wandb login
```

---

## Step 9 — Disable Video Recording (Required for First Run)

The debug config enables video recording by default, which requires ffmpeg. Open `config.yaml`, find the `debug:` section near the bottom, and ensure:

```yaml
debug:
  env:
    save_video: False
    fast_video: False
```

---

## Step 10 — Test the Environment (Debug Mode)

Run a single-environment debug session to verify everything works:

```powershell
python -m pokemonred_puffer.train debug
```

A PyBoy window will appear. You can control the character manually with arrow keys. This confirms the Game Boy environment is working correctly. Close with **Ctrl+C** in the terminal.

---

## Step 11 — Run Training

**Autotune** (find the optimal number of parallel environments for your machine):
```powershell
python -m pokemonred_puffer.train autotune
```

**Train** (default config):
```powershell
python -m pokemonred_puffer.train train
```

**Train with explicit reward and wrapper selection:**
```powershell
python -m pokemonred_puffer.train train -r baseline.CutWithObjectRewardRequiredEventsEnv -w stream_only
```

See all available options:
```powershell
python -m pokemonred_puffer.train train --help
python -m pokemonred_puffer.train debug --help
```

---

## Optional — Install ffmpeg (for Video Recording)

If you want to record videos of training episodes:

```powershell
winget install ffmpeg
```

Close and reopen your terminal after installation. Then re-enable video in `config.yaml`:
```yaml
debug:
  env:
    save_video: True
```

---

## Known Windows-Specific Issues & Fixes

### ❌ `sqlite3.OperationalError: unable to open database file`

**Cause:** The `NamedTemporaryFile` used for the SQLite swarm database holds an exclusive
file lock on Windows, preventing `sqlite3.connect()` from opening the same file.  
**Fix:** Disable the sqlite swarm wrapper in `config.yaml`:
```yaml
sqlite_wrapper: false
```
This disables the swarm mechanic (agents sharing best discovered save states) but does
not affect core PPO training or reward shaping.

---

### ❌ Training stops after ~400 wandb steps (~2 hours)

**Cause:** The `one_epoch` setting in `config.yaml` limits training to one full pass
through all environments before stopping, regardless of `total_timesteps`.  
**Fix:** Comment out the `one_epoch` block in `config.yaml`:
```yaml
# one_epoch:
#   - "EVENT_BEAT_CHAMPION_RIVAL"
```
With `one_epoch` disabled, training runs until `total_timesteps` is reached or you
stop it manually with **Ctrl+C**.

### ❌ `RuntimeError: An attempt has been made to start a new process before bootstrapping`

**Cause:** Windows uses `spawn` instead of `fork` for multiprocessing.  
**Fix:** Always launch training via `python -m pokemonred_puffer.train train`, never by importing and calling training functions directly from a script.

---

### ❌ `AttributeError: module 'signal' has no attribute 'SIGKILL'`

**Cause:** `SIGKILL` does not exist on Windows.  
**Fix:** This is handled in the `windows_compat/` patches. If it still occurs, run:
```powershell
python windows_compat\apply_windows_patches.py
```

---

### ❌ `RuntimeError: Program 'ffmpeg' is not found`

**Cause:** Video recording is enabled but ffmpeg is not installed.  
**Fix:** Either install ffmpeg (`winget install ffmpeg`) or set `save_video: False` in `config.yaml`.

---

### ❌ `OSError: [WinError 1314]` on symlink creation

**Cause:** Creating symlinks requires Administrator privileges on Windows.  
**Fix:** Either run VS Code/PowerShell as Administrator, or enable Developer Mode:  
Windows Settings → System → For Developers → Developer Mode → On.

---

### ❌ `numba` cache permission errors

**Fix:**
```powershell
$env:NUMBA_CACHE_DIR = "$env:TEMP\numba_cache"
```

---

### ❌ `BrokenPipeError` or workers dying silently

**Cause:** Windows multiprocessing (`spawn`) requires all objects passed to workers to be picklable. Lambda functions and certain closures are not picklable.  
**Fix:** Define any custom reward functions as named module-level functions, not lambdas.

---

### ❌ Execution policy error when activating venv

**Fix:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Performance Notes

- Training on Windows is typically **10–20% slower** than Linux due to `spawn` vs `fork` multiprocessing overhead.
- With an NVIDIA GPU, ensure you installed the CUDA version of PyTorch (Step 5).
- The `debug` subcommand runs a single environment sequentially — useful for testing reward logic without multiprocessing overhead.
- For serious training runs, `num_envs` in `config.yaml` should be tuned using `autotune` for your specific hardware.

---

## Verified Working Configuration

| Component | Version |
|-----------|---------|
| OS | Windows 11 |
| Python | 3.11.1 |
| PyTorch | 2.12.0.dev20260408+cu128 (nightly) |
| CUDA Driver | 13.1 (592.01) |
| GPU | NVIDIA GeForce RTX 5080 Laptop |
| numpy | 1.23.3 |
| pyboy | 2.7.0 |
| pufferlib | 1.0.1 |

---

## Directory Structure Reference

```
pokemonred_puffer_windows/
├── pokemonred_puffer/        ← Main source package
│   ├── environment.py        ← Core Game Boy RL environment
│   ├── train.py              ← CLI entry point
│   ├── cleanrl_puffer.py     ← PPO training loop
│   ├── rewards/              ← Reward function classes
│   ├── wrappers/             ← Gym wrapper classes
│   └── policies/             ← Neural network architectures
├── pyboy_states/             ← Game Boy save states (starting positions)
├── windows_compat/           ← Windows compatibility patches
├── config.yaml               ← Main configuration file
├── red.gb                    ← Your ROM (not included)
└── pyproject.toml            ← Package dependencies
```