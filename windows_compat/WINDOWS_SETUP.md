# Windows Setup Guide — pokemonred_puffer

> **Goal:** Run the Pokémon Blue RL agent on Windows 10/11 with no WSL2, no VM, and no Linux required.

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10 or 3.11 (NOT 3.12+) | https://www.python.org/downloads/ |
| Git | Any recent | https://git-scm.com/download/win |
| PyTorch (CUDA optional) | ≥ 2.4 | See Step 3 |
| Visual C++ Build Tools | 2019 or 2022 | See Step 2 |

> ⚠️ **Python 3.12 is NOT supported** by the repo's dependencies (`pyproject.toml` caps at `< 3.12`). Use **Python 3.10 or 3.11**.

---

## Step 1 — Clone the Repo

Open **PowerShell** or **Command Prompt** (not WSL):

```powershell
git clone https://github.com/drubinstein/pokemonred_puffer.git
cd pokemonred_puffer
```

---

## Step 2 — Install Visual C++ Build Tools

Some dependencies (e.g. `numba`, Cython extensions) need a C compiler on Windows.

1. Download **Build Tools for Visual Studio 2022** from:  
   https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Run the installer and select **"Desktop development with C++"**.
3. Reboot if prompted.

---

## Step 3 — Create a Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

---

## Step 4 — Install PyTorch (CPU or CUDA)

**CPU only** (simpler, slower training):
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

**CUDA 12.x** (if you have an NVIDIA GPU):
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

---

## Step 5 — Apply Windows Compatibility Patches

Copy the `windows_compat/` folder from this repository into the repo root, then run:

```powershell
python windows_compat\apply_windows_patches.py
```

This makes three surgical edits to the source:

| File | What changes |
|------|-------------|
| `pokemonred_puffer/train.py` | Adds `freeze_support()` + `set_start_method("spawn")` inside `__main__` guard |
| `pokemonred_puffer/cleanrl_puffer.py` | Replaces `signal.SIGKILL` (not on Windows) with portable fallback |
| `pokemonred_puffer/environment.py` | Replaces hardcoded `/tmp` paths with `tempfile.gettempdir()`, and wraps `os.symlink` in a copy fallback |

Each original file is backed up as `filename.py.win_bak` before editing.

---

## Step 6 — Install the Package

```powershell
pip install -e .
```

If you hit a build error on `pufferlib`, try:
```powershell
pip install -e . --no-build-isolation
```

---

## Step 7 — Add Your ROM

Place your **Pokémon Blue** (or Red) ROM in the repo root. It must be named:
```
pokemon_blue.gb    (or as expected by config.yaml — check the rom_path setting)
```

> The ROM is not included in the repo for legal reasons. You must obtain your own copy.

---

## Step 8 — Run Training

**Autotune** (find the right number of parallel environments for your machine):
```powershell
python -m pokemonred_puffer.train autotune
```

**Train** (default config):
```powershell
python -m pokemonred_puffer.train train
```

**Debug mode** (single environment, no multiprocessing):
```powershell
python -m pokemonred_puffer.train train --debug
```

> 💡 **Tip:** If you hit multiprocessing errors, use `--debug` first to confirm the environment runs correctly, then switch to full training.

---

## Known Windows-Specific Issues & Fixes

### ❌ `RuntimeError: An attempt has been made to start a new process before the current process has finished its bootstrapping phase`

**Cause:** Training code called at module level instead of inside `if __name__ == "__main__":`.  
**Fix:** The patch in Step 5 handles this. If it still occurs, run via `train_windows.py` instead:
```powershell
python windows_compat\train_windows.py train
```

---

### ❌ `AttributeError: module 'signal' has no attribute 'SIGKILL'`

**Cause:** `SIGKILL` doesn't exist on Windows.  
**Fix:** Handled automatically by `apply_windows_patches.py` (replaced with `SIGTERM`).

---

### ❌ `FileNotFoundError: [WinError 2] The system cannot find the file specified` on `/tmp/...`

**Cause:** Hardcoded Linux `/tmp` paths.  
**Fix:** Handled by the patch — redirected to `%TEMP%` via `tempfile.gettempdir()`.

---

### ❌ `OSError: [WinError 1314] A required privilege is not held by the client` on `os.symlink`

**Cause:** Creating symlinks on Windows requires administrator privileges.  
**Fix:** Handled by the patch — symlinks are replaced with `shutil.copy2`.  
**Alternative:** Run PowerShell as Administrator, or enable Developer Mode in Windows Settings → System → For Developers.

---

### ❌ `numba` JIT compilation errors / cache permission errors

**Fix:** The patch sets `NUMBA_CACHE_DIR` to your temp folder. Alternatively:
```powershell
set NUMBA_CACHE_DIR=%TEMP%\numba_cache
```

---

### ❌ `BrokenPipeError` or workers dying silently

**Cause:** Windows multiprocessing uses `spawn` (not `fork`), so all objects passed to worker processes must be **picklable**. Lambda functions and certain closures are not.  
**Fix:** If you add custom reward functions, define them as named functions (not lambdas) at the module level.

---

### ❌ PyBoy rendering issues (black screen or SDL error)

**Cause:** PyBoy's display backend may need SDL2 on Windows.  
**Fix:** Headless mode is already used for training (PyBoy runs without displaying). If you need the display:
```powershell
pip install pygame
```

---

## Performance Notes

- Training on Windows is typically **10–20% slower** than Linux due to multiprocessing overhead with the `spawn` start method (Linux uses `fork` which is faster).
- If you have an NVIDIA GPU, make sure you installed the CUDA version of PyTorch in Step 4.
- The `--debug` flag runs a single environment sequentially and is useful for testing reward logic without multiprocessing overhead.

---

## Reverting the Patches

Each patched file has a `.win_bak` backup. To revert:

```powershell
copy pokemonred_puffer\train.py.win_bak pokemonred_puffer\train.py
copy pokemonred_puffer\cleanrl_puffer.py.win_bak pokemonred_puffer\cleanrl_puffer.py
copy pokemonred_puffer\environment.py.win_bak pokemonred_puffer\environment.py
```

---

## File Summary

```
windows_compat/
├── WINDOWS_SETUP.md          ← This file
├── apply_windows_patches.py  ← Run once to patch the repo
├── train_windows.py          ← Alternative entrypoint (backup option)
└── windows_patches.py        ← Runtime patches (auto-imported by train_windows.py)
```
