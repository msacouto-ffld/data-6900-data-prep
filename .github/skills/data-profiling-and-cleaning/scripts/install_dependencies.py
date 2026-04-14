"""Stage 1 — Install dependencies.

Runs ``pip install ydata-profiling -q`` and verifies the import before any
other pipeline code runs. This must complete first because ydata-profiling's
install mutates pre-installed package versions.

Contract: ``contracts/install-dependencies.md``
"""
from __future__ import annotations

import subprocess
import sys


FAIL_MESSAGE = (
    "❌ Dependency error: ydata-profiling could not be installed.\n"
    "   Please try again in a new Claude.ai session."
)


def install_dependencies() -> bool:
    """Install ydata-profiling and verify the import.

    Returns
    -------
    bool
        ``True`` on success. Prints the failure message and returns
        ``False`` on any failure — callers should halt the pipeline.
    """
    print("📦 Installing profiling dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "ydata-profiling", "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError:
        print(FAIL_MESSAGE)
        return False

    try:
        import ydata_profiling  # noqa: F401
    except ImportError:
        print(FAIL_MESSAGE)
        return False

    print("✅ ydata-profiling installed successfully.")
    return True


if __name__ == "__main__":
    ok = install_dependencies()
    sys.exit(0 if ok else 1)
