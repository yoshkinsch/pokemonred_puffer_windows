"""
Windows-compatible entrypoint for pokemonred_puffer training.

On Windows, Python's multiprocessing uses 'spawn' instead of 'fork',
which requires all training code to be inside `if __name__ == "__main__":`.
This wrapper ensures that requirement is met.

Usage (replace your normal train command with this):
    python train_windows.py autotune
    python train_windows.py train
"""

import multiprocessing
import sys
import os

# ── Critical for Windows multiprocessing ──────────────────────────────────────
# Must be called BEFORE any other multiprocessing usage and at the TOP of the
# main script. This is a no-op on Linux/Mac but required on Windows.
if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Add the repo root to path so imports resolve correctly
    repo_root = os.path.dirname(os.path.abspath(__file__))
    # If this file is inside windows_compat/, go up one level to repo root
    if os.path.basename(repo_root) == "windows_compat":
        repo_root = os.path.dirname(repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Force 'spawn' start method explicitly (Windows default, but be explicit)
    multiprocessing.set_start_method("spawn", force=True)

    # Now import and run the real training module
    from pokemonred_puffer.train import main
    main()
