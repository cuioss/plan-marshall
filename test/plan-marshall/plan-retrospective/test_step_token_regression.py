#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""End-to-end regression coverage pinning the plan-retrospective Step 6 token to
the manifest step_id.

The bug this guards against: ``plan-retrospective/SKILL.md`` Step 6
(finalize-step termination) emits ``manage-status mark-step-done --step
{token}``. That ``{token}`` is the key the dispatched retrospective step records
its terminal outcome under. The phase-6-finalize manifest declares the SAME step
under the canonical step_id ``plan-marshall:plan-retrospective`` (the member of
``OPTIONAL_BUNDLE_FINALIZE_STEPS`` in ``manage-config/_config_defaults.py`` that
``finalize_step_presets.FULL`` references). When the documented token drifts away
from the manifest step_id, the recording side keys ``phase_steps`` under the
wrong name: the ``phase_steps_complete`` handshake invariant then reports the
canonical step as missing (``PhaseStepsIncomplete``) or the renderer emits
``<missing display_detail>`` — the exact mis-keying class hardened by
``assert-step-recorded``'s near-miss detection (``step_record_mismatched_key``).

These tests pin the drift-prevention contract:

1. The token documented in SKILL.md Step 6 (parsed from the ``mark-step-done
   --step ...`` invocation) is EXACTLY the canonical manifest step_id
   ``plan-marshall:plan-retrospective``.
2. The canonical step_id is a member of the authoritative finalize-step registry
   (``OPTIONAL_BUNDLE_FINALIZE_STEPS``) — so the manifest side and the
   documented side share a single source of truth, not two literals that can
   diverge silently.

Drifting the SKILL.md ``--step`` token (e.g. back to the bare
``plan-retrospective``) re-introduces the manifest-ID-vs-phase_steps-key
divergence and fails test 1.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from conftest import MARKETPLACE_ROOT, get_scripts_dir  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Source anchors
# ---------------------------------------------------------------------------

# The retrospective skill body whose Step 6 emits the mark-step-done token.
_RETROSPECTIVE_SKILL = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'SKILL.md'
)

# The canonical manifest step_id this regression pins the documented token to.
_CANONICAL_STEP_ID = 'plan-marshall:plan-retrospective'

# ``_config_defaults`` imports the sibling ``constants`` module by bare name
# (PYTHONPATH is normally set by the executor); add the scripts dir to the
# import path before loading so the bare ``from constants import ...`` resolves.
_CONFIG_SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'manage-config')
if str(_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_CONFIG_SCRIPTS_DIR))

import _config_defaults as config_defaults  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _documented_step_token(skill_md: Path) -> str:
    """Parse the ``--step {token}`` argument from the retrospective SKILL.md
    Step 6 ``mark-step-done`` invocation.

    Step 6 emits exactly one ``manage-status mark-step-done`` call carrying a
    ``--phase 6-finalize`` argument and a ``--step {token}`` argument. Return
    the ``{token}`` so the test asserts against the live documented value
    rather than a hard-coded copy.
    """
    content = skill_md.read_text(encoding='utf-8')
    # Match the --step argument on a mark-step-done invocation that also names
    # the 6-finalize phase, tolerant of line breaks / backslash continuations.
    match = re.search(
        r'mark-step-done\b[\s\S]*?--phase\s+6-finalize\b[\s\S]*?--step\s+(\S+)',
        content,
    )
    if match is None:
        raise AssertionError(
            f'No `mark-step-done ... --phase 6-finalize ... --step <token>` '
            f'invocation found in {skill_md}; Step 6 termination contract changed.'
        )
    return match.group(1)


# ---------------------------------------------------------------------------
# Test 1: documented token matches the canonical manifest step_id exactly
# ---------------------------------------------------------------------------


def test_documented_step_token_matches_manifest_step_id() -> None:
    """The token documented in SKILL.md Step 6 is EXACTLY the canonical manifest
    step_id ``plan-marshall:plan-retrospective``.

    This is the drift guard: if a maintainer edits the Step 6 ``--step``
    argument away from the manifest step_id (e.g. to the bare
    ``plan-retrospective``), the recording side keys ``phase_steps`` under the
    wrong name and the ``phase_steps_complete`` handshake reports the canonical
    step missing. Pinning the documented token to the manifest step_id catches
    the divergence at test time.
    """
    assert _RETROSPECTIVE_SKILL.is_file(), (
        f'expected retrospective skill body not found: {_RETROSPECTIVE_SKILL}'
    )

    documented = _documented_step_token(_RETROSPECTIVE_SKILL)

    assert documented == _CANONICAL_STEP_ID, (
        f'plan-retrospective SKILL.md Step 6 documents `--step {documented}`, '
        f'but the canonical manifest step_id is `{_CANONICAL_STEP_ID}`. The '
        f'documented mark-step-done token MUST match the manifest step_id '
        f'exactly, or the recorded phase_steps key drifts and the '
        f'phase_steps_complete handshake reports the step missing.'
    )


# ---------------------------------------------------------------------------
# Test 2: the canonical step_id is the authoritative registry member
# ---------------------------------------------------------------------------


def test_canonical_step_id_is_authoritative_registry_member() -> None:
    """The canonical step_id the documented token is pinned to is itself a member
    of the authoritative finalize-step registry ``OPTIONAL_BUNDLE_FINALIZE_STEPS``.

    Anchoring test 1's expected value in the registry (rather than a second
    bare literal) guarantees the documented side and the manifest side share a
    single source of truth: if the registry ever renames the step, this test
    fails alongside test 1 and forces both sides to move together.
    """
    optional_steps = config_defaults.OPTIONAL_BUNDLE_FINALIZE_STEPS

    assert _CANONICAL_STEP_ID in optional_steps, (
        f'`{_CANONICAL_STEP_ID}` is not a member of '
        f'OPTIONAL_BUNDLE_FINALIZE_STEPS ({optional_steps}); the manifest '
        f'step_id this regression pins the documented token to no longer '
        f'matches the authoritative finalize-step registry.'
    )
