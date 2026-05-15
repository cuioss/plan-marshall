"""Regression test for the phase-4-plan Verification-Only Guard contract.

The guard must NOT collapse a deliverable's profile set to ``[verification]``
when the deliverable's explicit ``Profiles`` list already contains
``implementation``. The explicit profile declaration is authoritative over
``change_type``. This test asserts the guard's documented contract by
inspecting the workflow doc (``SKILL.md``) where the guard logic lives.
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


def test_guard_documents_implementation_profile_short_circuit(skill_text: str) -> None:
    """The guard's pseudocode and prose must encode the short-circuit.

    Specifically:
    - The pseudocode keeps the existing verification override condition
      (``change_type == verification`` OR ``affected_files is empty``).
    - The pseudocode adds a short-circuit so the override only fires when
      the deliverable's explicit ``Profiles`` list does NOT contain
      ``implementation``.
    - The surrounding prose explicitly states the explicit ``Profiles``
      list is authoritative over ``change_type`` when it names
      ``implementation``.
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

    # The new short-circuit must be present in the pseudocode. Accept the
    # canonical phrasing or a clearly-equivalent alternative.
    canonical = '"implementation" NOT IN D.profiles'
    equivalent = '"implementation" in D.profiles'
    assert canonical in block or equivalent in block, (
        "Guard pseudocode is missing the implementation-profile short-circuit. "
        f"Expected '{canonical}' (or equivalent referencing "
        f"'\"implementation\" in D.profiles') in the pseudocode block."
    )

    # Prose around the guard must explicitly state the explicit Profiles list
    # is authoritative over change_type. We assert key phrasing tokens rather
    # than a full sentence to keep the test robust to minor wording tweaks.
    marker_index = skill_text.find("**Verification-Only Guard**")
    prose_window = skill_text[marker_index : marker_index + 2000]
    assert "explicit" in prose_window.lower() and "profiles" in prose_window.lower(), (
        "Guard prose must reference the explicit Profiles list."
    )
    assert "authoritative" in prose_window.lower() or "wins" in prose_window.lower(), (
        "Guard prose must state the explicit Profiles list is authoritative "
        "over change_type (use 'authoritative' or 'wins')."
    )
    assert "implementation" in prose_window, (
        "Guard prose must name the 'implementation' profile as the trigger "
        "for the short-circuit."
    )
