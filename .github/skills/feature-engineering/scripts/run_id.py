"""Run ID generator for Skill B.

Produces IDs in the format ``feature-YYYYMMDD-HHMMSS-XXXX``
where XXXX is a 4-character random hex suffix.
"""
import datetime
import secrets


def generate_run_id(prefix: str = "feature") -> str:
    now = datetime.datetime.now()
    suffix = secrets.token_hex(2)
    return f"{prefix}-{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"


if __name__ == "__main__":
    for _ in range(3):
        print(generate_run_id())
