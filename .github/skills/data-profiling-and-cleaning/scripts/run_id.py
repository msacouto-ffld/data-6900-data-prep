"""Run ID generation for the Skill A pipeline.

Format: ``profile-YYYYMMDD-HHMMSS-XXXX``

Where ``XXXX`` is a 4-character hex suffix from ``secrets.token_hex(2)``.

Feature 2 (cleaning) uses the same generator with a ``transform-`` prefix;
that is handled by ``scripts/load_inputs.py`` for Feature 2.

FR-015 compliance: every profiling execution gets a unique ID.
"""
from __future__ import annotations

import datetime
import secrets


def generate_run_id(prefix: str = "profile") -> str:
    """Generate a unique run ID.

    Parameters
    ----------
    prefix:
        ``"profile"`` for Feature 1, ``"transform"`` for Feature 2.

    Returns
    -------
    str
        e.g. ``"profile-20260413-091533-b2f1"``.
    """
    now = datetime.datetime.now()
    suffix = secrets.token_hex(2)  # 4 hex characters
    return f"{prefix}-{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"


if __name__ == "__main__":
    # Quick smoke test
    for _ in range(3):
        print(generate_run_id())
