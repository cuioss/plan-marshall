#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""End-to-end regression coverage pinning the plan-retrospective Step 6 token to
the manifest step_id.

The bug this guards against: ``plan-retrospective/SKILL.md`` Step 6
(finalize-step termination) emits ``manage-status mark-step-done --step
{token}``. That ``{token}`` is the key the dispatched retrospective step records
its terminal outcome under. The phase-6-finalize manifest declares the SAME step
under the canonical step_id ``plan-marshall:plan-retrospective`` (the
bundle-optional finalize-step implementor surfaced by
``extension_discovery.find_implementors`` that the ``full`` preset references).
When the documented token drifts away
from the manifest step_id, the recording side keys ``phase_steps`` under the
wrong name: the ``phase_steps_complete`` handshake invariant then reports the
canonical step as missing (``PhaseStepsIncomplete``) or the renderer emits
``<missing display_detail>`` — the exact mis-keying class hardened by
``assert-step-recorded``'s near-miss detection (``step_record_mismatched_key``).

These tests pin the drift-prevention contract:

1. The token documented in SKILL.md Step 6 (parsed from the ``mark-step-done
   --step ...`` invocation) is EXACTLY the canonical manifest step_id
   ``plan-marshall:plan-retrospective``.
2. The canonical step_id is a discovered bundle-optional finalize-step
   implementor (via ``extension_discovery.find_implementors``) — so the manifest
   side and the documented side share a single source of truth, not two literals
   that can diverge silently.

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

    The parsing is order-independent: ``--phase`` and ``--step`` may appear in
    either order within the ``mark-step-done`` command block, and both
    space-separated (``--flag value``) and equals-separated (``--flag=value``)
    forms are handled.
    """
    content = skill_md.read_text(encoding='utf-8')
    # Extract every mark-step-done command block (up to the next blank line,
    # closing code fence, or end of string), then search within each block for
    # one that contains both --phase 6-finalize and --step, regardless of order.
    _phase_pat = re.compile(r'--phase(?:\s+|=)6-finalize\b')
    _step_pat = re.compile(r'--step(?:\s+|=)(\S+)')
    for block in re.findall(r'mark-step-done\b[\s\S]*?(?=\n\s*\n|```|$)', content):
        if not _phase_pat.search(block):
            continue
        step_match = _step_pat.search(block)
        if step_match:
            return step_match.group(1)
    raise AssertionError(
        f'No `mark-step-done ... --phase 6-finalize ... --step <token>` '
        f'invocation found in {skill_md}; Step 6 termination contract changed.'
    )


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
    """The canonical step_id the documented token is pinned to is itself a
    discovered bundle-optional finalize-step implementor.

    Anchoring test 1's expected value in the discovery query (rather than a
    second bare literal) guarantees the documented side and the manifest side
    share a single source of truth: if the step doc ever renames the step, this
    test fails alongside test 1 and forces both sides to move together. The
    bundle-optional set is derived from ``extension_discovery.find_implementors``
    (the SOLE finalize-step discovery path; ``OPTIONAL_BUNDLE_FINALIZE_STEPS``
    was removed).
    """
    from extension_discovery import find_implementors  # type: ignore[import-not-found]

    optional_steps = [
        rec['name']
        for rec in find_implementors(config_defaults.FINALIZE_STEP_EXT_POINT)
        if rec.get('source') == 'bundle-optional' and rec.get('name')
    ]

    assert _CANONICAL_STEP_ID in optional_steps, (
        f'`{_CANONICAL_STEP_ID}` is not a discovered bundle-optional finalize '
        f'step ({optional_steps}); the manifest step_id this regression pins the '
        f'documented token to no longer matches the discovered finalize-step '
        f'universe.'
    )
