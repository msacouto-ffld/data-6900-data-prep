"""Stage 7a — Jargon scan for Skill B.

Scans the transformation report and data dictionary for method-specific
terms from JARGON_TERMS. For each found term, checks whether a
plain-language explanation appears nearby. If undefined terms are found,
calls an optional LLM hook to add definitions.

Contract: contracts/scan-jargon.md (inferred from T020)
"""
from __future__ import annotations

import re
from typing import Callable, List, Optional, Tuple

from jargon_terms import JARGON_TERMS


# Explanation indicators — phrases that suggest a term has been defined
_EXPLANATION_PATTERNS = [
    r"which means",
    r"this means",
    r"in other words",
    r"that is",
    r"is a\b",
    r"refers to",
    r"also known as",
    r"\(",  # parenthetical definition like "one-hot encoding (creating binary columns)"
]


def _has_explanation(term: str, text: str) -> bool:
    """Check if the term has a nearby explanation in the text."""
    # Find all occurrences of the term (case-insensitive)
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    for match in pattern.finditer(text):
        # Look within ~300 characters after the match
        start = match.start()
        window = text[start:start + 300]
        for expl_pat in _EXPLANATION_PATTERNS:
            if re.search(expl_pat, window, re.IGNORECASE):
                return True
    return False


def scan_jargon(
    report_text: str,
    dictionary_text: str = "",
    llm_fix_hook: Optional[Callable[[str, str, List[str]], Tuple[str, str]]] = None,
) -> Tuple[str, str, List[str]]:
    """Scan report and dictionary for undefined jargon terms.

    Parameters
    ----------
    report_text : str
        The transformation report markdown.
    dictionary_text : str
        The data dictionary markdown.
    llm_fix_hook : callable, optional
        ``(report, dictionary, flagged_terms) -> (fixed_report, fixed_dict)``

    Returns
    -------
    (final_report, final_dictionary, flagged_terms)
    """
    print("🔍 Running jargon scan...")

    combined = report_text + "\n" + dictionary_text
    flagged: List[str] = []

    for term in JARGON_TERMS:
        # Check if the term appears at all
        if not re.search(re.escape(term), combined, re.IGNORECASE):
            continue
        # Check if it's explained
        if not _has_explanation(term, combined):
            flagged.append(term)

    if not flagged:
        print("✅ Jargon scan passed.")
        return report_text, dictionary_text, []

    print(f"   ⚠️ {len(flagged)} term(s) flagged: {', '.join(flagged)}")

    if llm_fix_hook:
        try:
            fixed_report, fixed_dict = llm_fix_hook(
                report_text, dictionary_text, flagged,
            )
            print(f"✅ Jargon scan passed — {len(flagged)} term(s) explained.")
            return fixed_report, fixed_dict, flagged
        except Exception as exc:
            print(f"   ⚠️ LLM fix failed ({exc}). Delivering with note.")

    # No hook or hook failed — add a note
    note = (
        "\n\n---\n\n> **Note**: the following terms may need additional "
        f"explanation: {', '.join(flagged)}."
    )
    return report_text + note, dictionary_text, flagged


if __name__ == "__main__":
    clean = "We applied one-hot encoding (creating binary columns for each category) to the region column."
    dirty = "We applied one-hot encoding and z-score normalization to the data."

    _, _, flagged = scan_jargon(clean)
    assert not flagged, f"Expected clean, got {flagged}"

    _, _, flagged = scan_jargon(dirty)
    print(f"Flagged: {flagged}")
    assert "z-score" in flagged or "normalization" in flagged
