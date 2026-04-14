"""Stage 16 — Jargon scan (script + LLM hybrid).

Regex-based undefined-acronym detection. If violations found, calls
the injected LLM hook to fix them. If no violations, report passes
through unchanged.

Contract: ``contracts/scan-jargon.md``
"""
from __future__ import annotations

import re
from typing import Callable, List, Optional, Tuple


ACRONYM_WHITELIST = {
    # Common acronyms already explained elsewhere or universally known
    "CSV", "HTML", "JSON", "NaN", "PII", "ID", "LLM", "NL",
    "ASCII", "UTC", "ISO", "PDF", "API",
    # Report status vocabulary — these appear in the Verification
    # Summary section of every report and are not acronyms
    "PASS", "FAIL", "OK",
}

# An acronym is considered "defined on first use" if the report
# contains either:
#   TERM (Full Name)      e.g. "IQR (interquartile range)"
#   Full Name (TERM)      e.g. "interquartile range (IQR)"
_UPPERCASE_RE = re.compile(r"\b[A-Z]{2,}\b")


def _is_defined(term: str, text: str) -> bool:
    """True if ``term`` is defined on its first use in ``text``."""
    # Pattern A: TERM (something)
    pat_a = re.compile(
        rf"\b{re.escape(term)}\b\s*\([^)]+\)"
    )
    # Pattern B: something (TERM)
    pat_b = re.compile(
        rf"[A-Za-z][A-Za-z\s]+\s*\(\s*{re.escape(term)}\s*\)"
    )
    return bool(pat_a.search(text) or pat_b.search(text))


def _find_undefined_terms(text: str) -> List[str]:
    """Return the sorted list of undefined, non-whitelisted acronyms."""
    found = set(_UPPERCASE_RE.findall(text))
    undefined: List[str] = []
    for term in found:
        if term in ACRONYM_WHITELIST:
            continue
        if _is_defined(term, text):
            continue
        undefined.append(term)
    return sorted(set(undefined))


def scan_jargon(
    report_text: str,
    llm_fix_hook: Optional[Callable[[str, List[str]], str]] = None,
) -> Tuple[str, List[str]]:
    """Scan the report for jargon violations; fix via LLM if found.

    Parameters
    ----------
    report_text:
        The final transformation report after verification.
    llm_fix_hook:
        Optional callable ``(report, undefined_terms) -> fixed_report``.
        If None and violations are found, the report is returned
        unchanged with the flagged terms listed to the user.

    Returns
    -------
    (final_report_text, corrected_terms)
        ``corrected_terms`` is the list of terms that were addressed
        (either fixed or flagged). Empty if no violations.
    """
    print("🔎 Running jargon scan...")

    try:
        undefined = _find_undefined_terms(report_text)
    except Exception as exc:
        print(f"   ⚠️ Jargon scan could not be completed: {exc}")
        return report_text, []

    if not undefined:
        print("✅ Report complete — no jargon violations found.")
        return report_text, []

    print(
        f"⚠️ {len(undefined)} undefined term(s) found: "
        f"{', '.join(undefined)} — adding definitions."
    )

    if llm_fix_hook is None:
        # No LLM available — deliver with a soft warning
        note = (
            "\n\n---\n\n> ⚠️ **Note**: the following terms may need "
            "definition — "
            f"{', '.join(undefined)}. Please cross-check before sharing."
        )
        return report_text + note, undefined

    try:
        fixed_report = llm_fix_hook(report_text, undefined)
        print(f"✅ Report complete — {len(undefined)} term(s) corrected.")
        return fixed_report, undefined
    except Exception as exc:
        print(f"   ⚠️ LLM fix failed ({exc}). Delivering with warning.")
        note = (
            "\n\n---\n\n> ⚠️ **Note**: the following terms may need "
            "definition — "
            f"{', '.join(undefined)}. Please cross-check before sharing."
        )
        return report_text + note, undefined


if __name__ == "__main__":
    clean_report = """# Report
    This report uses CSV and JSON files and references PII findings.
    The mean (average) is 42 and the median (midpoint) is 40.
    """
    result, fixed = scan_jargon(clean_report)
    assert fixed == [], f"expected no violations, got {fixed}"
    print()

    dirty_report = """# Report
    We applied IQR-based outlier removal and used OLS regression
    to model the relationship. The MAPE was 12%.
    """
    result, fixed = scan_jargon(dirty_report)
    print(f"\nFlagged: {fixed}")
    assert "IQR" in fixed and "OLS" in fixed and "MAPE" in fixed

    # Test that defined terms are not flagged
    defined_report = """# Report
    We used IQR (interquartile range) to detect outliers. The
    mean absolute percentage error (MAPE) was acceptable.
    """
    result, fixed = scan_jargon(defined_report)
    print(f"\nFlagged (should be empty): {fixed}")
