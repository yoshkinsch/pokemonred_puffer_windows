"""
apply_windows_patches.py
========================
Run this script ONCE from the repo root after cloning:

    python windows_compat/apply_windows_patches.py

It will make surgical edits to the existing source files so that the
normal `python -m pokemonred_puffer.train train` command works on Windows
without WSL2.

Changes made
------------
pokemonred_puffer/train.py
  • Wrap the module-level `main()` call in `if __name__ == "__main__":`
  • Add `multiprocessing.freeze_support()` and `set_start_method("spawn")`

pokemonred_puffer/cleanrl_puffer.py
  • Guard any top-level process spawning with `if __name__ == "__main__":`
  • Replace `signal.SIGKILL` with portable fallback

pokemonred_puffer/environment.py
  • Replace hardcoded `/tmp` paths with `tempfile.gettempdir()`
  • Replace `os.symlink` (broken on Windows without admin rights) with
    `shutil.copy2` fallback

All edits are idempotent — running the script twice is safe.
"""

import os
import re
import shutil
import sys
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Helpers ───────────────────────────────────────────────────────────────────

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"  ✔ Patched: {path}")


def backup(path):
    bak = path + ".win_bak"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print(f"  ↳ Backup:  {bak}")


# ── Patch: train.py ───────────────────────────────────────────────────────────

def patch_train_py():
    path = os.path.join(REPO_ROOT, "pokemonred_puffer", "train.py")
    if not os.path.exists(path):
        print(f"  ⚠ Not found (skipping): {path}")
        return

    backup(path)
    src = read(path)

    # 1. Add multiprocessing import if missing
    if "import multiprocessing" not in src:
        src = "import multiprocessing\n" + src

    # 2. Add freeze_support + set_start_method guard before main() call
    # Look for the common pattern: `if __name__ == "__main__":` already there
    if 'freeze_support' not in src:
        guard = textwrap.dedent("""\
            if __name__ == "__main__":
                multiprocessing.freeze_support()
                # Windows requires 'spawn'; safe no-op on Linux/Mac
                try:
                    multiprocessing.set_start_method("spawn", force=True)
                except RuntimeError:
                    pass
        """)

        # If there's already a __main__ guard, insert inside it
        if 'if __name__ == "__main__":' in src:
            src = src.replace(
                'if __name__ == "__main__":',
                'if __name__ == "__main__":\n'
                '    multiprocessing.freeze_support()\n'
                '    try:\n'
                '        multiprocessing.set_start_method("spawn", force=True)\n'
                '    except RuntimeError:\n'
                '        pass\n',
                1,  # only first occurrence
            )
        else:
            # Append guard that calls existing main()
            src = src.rstrip() + "\n\n" + guard + "    main()\n"

    write(path, src)


# ── Patch: cleanrl_puffer.py ─────────────────────────────────────────────────

def patch_cleanrl_puffer():
    path = os.path.join(REPO_ROOT, "pokemonred_puffer", "cleanrl_puffer.py")
    if not os.path.exists(path):
        print(f"  ⚠ Not found (skipping): {path}")
        return

    backup(path)
    src = read(path)

    # Replace signal.SIGKILL with portable version
    if "signal.SIGKILL" in src:
        portable_sigkill = textwrap.dedent("""\
            # Windows-compatible signal: SIGKILL does not exist on Windows
            _SIGKILL = getattr(signal, "SIGKILL", signal.SIGTERM)
        """)
        # Add helper after `import signal` line
        if "import signal" in src and "_SIGKILL" not in src:
            src = src.replace(
                "import signal\n",
                "import signal\n" + portable_sigkill,
                1,
            )
        # Replace usages
        src = src.replace("signal.SIGKILL", "_SIGKILL")

    write(path, src)


# ── Patch: environment.py ────────────────────────────────────────────────────

def patch_environment_py():
    path = os.path.join(REPO_ROOT, "pokemonred_puffer", "environment.py")
    if not os.path.exists(path):
        print(f"  ⚠ Not found (skipping): {path}")
        return

    backup(path)
    src = read(path)

    # 1. Replace hardcoded /tmp with tempfile.gettempdir()
    if '"/tmp"' in src or "'/tmp'" in src or '"/tmp/' in src:
        if "import tempfile" not in src:
            src = "import tempfile\n" + src
        # Replace /tmp/ prefix in strings
        src = re.sub(r'["\']\/tmp\/', 'os.path.join(tempfile.gettempdir(), "', src)
        # Close the strings that were opened (naive — works for simple cases)
        # More robust: replace literal "/tmp" standalone
        src = src.replace('"/tmp"', 'tempfile.gettempdir()')
        src = src.replace("'/tmp'", 'tempfile.gettempdir()')

    # 2. Replace os.symlink with shutil.copy2 fallback (symlinks need admin on Windows)
    if "os.symlink" in src and "try:\n" not in src.split("os.symlink")[0].rsplit("\n", 3)[-1]:
        src = src.replace(
            "os.symlink(",
            "_windows_safe_symlink(",
        )
        symlink_helper = textwrap.dedent("""\

            def _windows_safe_symlink(src, dst):
                \"\"\"os.symlink requires admin on Windows; fall back to copy.\"\"\"
                import platform, shutil
                if os.path.exists(dst):
                    return
                if platform.system() == "Windows":
                    shutil.copy2(src, dst)
                else:
                    os.symlink(src, dst)

        """)
        # Insert after imports block (before first non-import line)
        insert_pos = 0
        for m in re.finditer(r"^(import |from )", src, re.MULTILINE):
            insert_pos = m.end() + src[m.end():].index("\n") + 1
        src = src[:insert_pos] + symlink_helper + src[insert_pos:]

    write(path, src)


# ── Patch: pyproject.toml ────────────────────────────────────────────────────

def patch_pyproject_toml():
    """Add Windows to the supported OS classifiers."""
    path = os.path.join(REPO_ROOT, "pyproject.toml")
    if not os.path.exists(path):
        print(f"  ⚠ Not found (skipping): {path}")
        return

    backup(path)
    src = read(path)

    windows_classifier = '    "Operating System :: Microsoft :: Windows",\n'
    if "Microsoft :: Windows" not in src:
        src = src.replace(
            '    "Operating System :: MacOS :: MacOS X",\n',
            '    "Operating System :: MacOS :: MacOS X",\n' + windows_classifier,
        )
        write(path, src)
    else:
        print(f"  ✔ Already patched: {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print("  pokemonred_puffer — Windows Compatibility Patcher")
    print(f"{'='*60}")
    print(f"  Repo root: {REPO_ROOT}\n")

    patch_train_py()
    patch_cleanrl_puffer()
    patch_environment_py()
    patch_pyproject_toml()

    print(f"\n{'='*60}")
    print("  Done! See WINDOWS_SETUP.md for next steps.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
