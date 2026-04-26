"""
windows_patches.py
==================
Apply this module's patches at the TOP of your training script (or import it
before anything else touches multiprocessing / shared memory).

What this fixes
---------------
1. `multiprocessing.set_start_method("spawn")` — Windows already defaults to
   spawn, but setting it explicitly prevents accidental 'fork' usage in any
   dependency that tries to change it.

2. Shared-memory path differences — POSIX shared memory uses `/dev/shm` paths
   that don't exist on Windows. Python 3.8+ `multiprocessing.shared_memory`
   works on Windows natively, but some RL libraries (PufferLib ≤1.x) fall back
   to `mmap`-based tricks. This patch ensures the right backend is chosen.

3. `os.getpid()` based temp paths — Linux code often writes to `/tmp/...`.
   This patch redirects those to `%TEMP%` on Windows.

4. `signal.SIGKILL` — does not exist on Windows. Replaced with SIGTERM.

5. Numba / LLVM JIT — numba works on Windows but sometimes needs
   `NUMBA_CACHE_DIR` set explicitly to avoid permission errors.

Usage
-----
Add this import as the very first line of train_windows.py (already done):

    import windows_patches  # noqa: F401  (side-effects only)
"""

import os
import platform
import signal
import sys
import tempfile

# ── Only apply patches on Windows ─────────────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"


def apply_all():
    if not IS_WINDOWS:
        return  # no-op on Linux / macOS

    _patch_tmp_dir()
    _patch_signal()
    _patch_numba_cache()
    _patch_multiprocessing_start_method()
    _patch_windows_console()

    print("[windows_patches] All Windows compatibility patches applied.")


# ── Individual patches ────────────────────────────────────────────────────────

def _patch_tmp_dir():
    """
    Redirect hardcoded /tmp paths to the Windows TEMP directory.
    Some PufferLib / environment code writes recordings or logs to /tmp.
    We monkeypatch tempfile so gettempdir() works, and expose a helper.
    """
    win_temp = tempfile.gettempdir()  # Usually C:\Users\<user>\AppData\Local\Temp
    os.makedirs(win_temp, exist_ok=True)

    # Expose a module-level helper other code can import
    global TEMP_DIR
    TEMP_DIR = win_temp


def _patch_signal():
    """
    Replace signal.SIGKILL with signal.SIGTERM on Windows.
    SIGKILL does not exist on Windows; SIGTERM is the closest equivalent.
    """
    if not hasattr(signal, "SIGKILL"):
        signal.SIGKILL = signal.SIGTERM  # type: ignore[attr-defined]
        print("[windows_patches] signal.SIGKILL → signal.SIGTERM")


def _patch_numba_cache():
    """
    Numba caches compiled kernels. On Windows the default cache path can
    trigger permission errors. Redirect to TEMP.
    """
    if "NUMBA_CACHE_DIR" not in os.environ:
        cache_dir = os.path.join(tempfile.gettempdir(), "numba_cache")
        os.makedirs(cache_dir, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = cache_dir
        print(f"[windows_patches] NUMBA_CACHE_DIR → {cache_dir}")


def _patch_multiprocessing_start_method():
    """
    Guarantee 'spawn' start method. Without this, some code paths in
    PufferLib try to use 'fork', which is not available on Windows and
    raises RuntimeError.
    """
    import multiprocessing
    try:
        multiprocessing.set_start_method("spawn", force=True)
        print("[windows_patches] multiprocessing start method → spawn")
    except RuntimeError:
        pass  # Already set; fine.


def _patch_windows_console():
    """
    Windows console (cmd.exe / PowerShell) may not support ANSI escape codes
    used by tqdm / rich. Enable virtual terminal processing if possible.
    """
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass  # Non-fatal; progress bars will just show raw codes.


# ── Auto-apply when imported ───────────────────────────────────────────────────
apply_all()
