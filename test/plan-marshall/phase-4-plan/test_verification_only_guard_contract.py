# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression test for the phase-4-plan Verification-Only Guard contract.

The guard must NOT collapse a deliverable's profile set to ``[verification]``
when the deliverable carries any write-intent affected file
(``write-new`` / ``write-replace`` / ``delete``). The per-file write-intent
set — sourced from ``affected_files[N].intent`` — is authoritative over a
``change_type == verification`` label: the override fires ONLY when the
deliverable is read-only (``affected_files`` empty OR every entry ``read``).
This test asserts the guard's documented contract by inspecting the workflow
doc (``SKILL.md``) where the guard logic lives.
"""

from pathlib import Path

import pytest

SKILL_PATH = (
    Path(__file__).resolve().parents[3]
    / "marketplace"
    / "bundles"
    / "plan-marshall"
    / "skills"
    / "phase-4-plan"
    / "SKILL.md"
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    """Load the phase-4-plan SKILL.md contents once per module."""
    assert SKILL_PATH.is_file(), f"phase-4-plan SKILL.md not found at {SKILL_PATH}"
    return SKILL_PATH.read_text(encoding="utf-8")


def _extract_guard_block(text: str) -> str:
    """Return the Verification-Only Guard pseudocode block.

    The block is the fenced ``` ... ``` block that contains the
    ``For each deliverable D:`` loop, located immediately after the
    Verification-Only Guard prose and warning ``bash`` block.
    """
    marker = "**Verification-Only Guard**"
    marker_index = text.find(marker)
    assert marker_index != -1, "Verification-Only Guard section not found in SKILL.md"

    # Find the first plain ``` fenced block after the marker that contains
    # the 'For each deliverable D:' loop. Skip the bash warning block.
    search_region = text[marker_index:]
    cursor = 0
    while True:
        open_idx = search_region.find("\n```", cursor)
        assert open_idx != -1, "Could not find pseudocode block after Verification-Only Guard"
        # Skip the language tag (e.g., ```bash) if present, by reading until newline
        block_start = open_idx + len("\n```")
        newline_after_open = search_region.find("\n", block_start)
        assert newline_after_open != -1
        close_idx = search_region.find("\n```", newline_after_open)
        assert close_idx != -1, "Unclosed fenced block after Verification-Only Guard"
        block_body = search_region[newline_after_open + 1 : close_idx]
        if "For each deliverable D" in block_body:
            return block_body
        cursor = close_idx + len("\n```")


def test_guard_documents_write_intent_predicate(skill_text: str) -> None:
    """The guard's pseudocode and prose must encode the write-intent predicate.

    Specifically:
    - The pseudocode keeps the existing verification override condition
      (``change_type == verification`` OR ``affected_files is empty``).
    - The pseudocode fires the override ONLY when the deliverable is read-only
      — ``affected_files`` empty OR every entry has ``intent == read``.
    - The deprecated ``"implementation" NOT IN D.profiles`` carve-out is GONE
      (it was the source of the lesson's bug: a write-bearing deliverable with
      a non-``implementation`` profile was silently collapsed to verification).
    - The surrounding prose explicitly states the per-file write-intent set is
      authoritative over ``change_type``.
    """
    block = _extract_guard_block(skill_text)

    # Legacy verification override condition must remain documented.
    assert "change_type == verification" in block, (
        "Guard pseudocode no longer mentions 'change_type == verification' — "
        "the legacy override condition must remain documented."
    )
    assert "affected_files is empty" in block, (
        "Guard pseudocode no longer mentions 'affected_files is empty' — "
        "the legacy override condition must remain documented."
    )

    # The write-intent predicate must gate the override: it fires only when the
    # deliverable is read-only (every affected_files entry has intent == read).
    assert "intent == read" in block, (
        "Guard pseudocode is missing the write-intent predicate. Expected the "
        "override to fire only when 'every affected_files entry has intent == read'."
    )

    # Regression guard: the deprecated implementation-profile carve-out — the
    # exact source of the lesson's bug — must NOT reappear in the pseudocode.
    assert '"implementation" NOT IN D.profiles' not in block, (
        "Guard pseudocode reintroduced the deprecated "
        "'\"implementation\" NOT IN D.profiles' carve-out — the write-intent "
        "predicate must be the sole override gate (lesson 2026-06-20-12-002)."
    )

    # Prose around the guard must state the per-file write-intent set is
    # authoritative over change_type. We assert key phrasing tokens rather than
    # a full sentence to keep the test robust to minor wording tweaks.
    marker_index = skill_text.find("**Verification-Only Guard**")
    prose_window = skill_text[marker_index : marker_index + 2000]
    assert "write-intent" in prose_window.lower(), (
        "Guard prose must reference the per-file write-intent set."
    )
    assert "authoritative" in prose_window.lower(), (
        "Guard prose must state the write-intent set is authoritative over change_type."
    )
    assert "intent" in prose_window.lower(), (
        "Guard prose must name the affected-file 'intent' enum as the override signal."
    )
