#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the project-level finalize-step-sync-plugin-cache SKILL contract.

Deliverable 5 relocates on-main executor regeneration OUT of ``integrate_into_main``
and INTO this project-level finalize step: after a successful cache sync, the step
regenerates ``.plan/execute-script.py`` against the freshly-synced cache, in BOTH
worktree and no-worktree finalize flows (closing the no-worktree staleness gap).

The step body is a markdown workflow (no executable Python body), so these tests
assert the documented contract — the regen invocation ordering, its
non-fatal / unconditional-after-success semantics, the both-flows guarantee, and
the relocation of regen ownership away from ``integrate_into_main`` — guarding
against silent regression of the wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_MD = _REPO_ROOT / '.claude' / 'skills' / 'finalize-step-sync-plugin-cache' / 'SKILL.md'


@pytest.fixture(scope='module')
def skill_text() -> str:
    assert _SKILL_MD.is_file(), f'cache-sync step SKILL.md not found at {_SKILL_MD}'
    # Collapse all whitespace (including markdown line wraps) to single spaces so
    # multi-word phrase assertions are robust to where the prose happens to wrap.
    return ' '.join(_SKILL_MD.read_text(encoding='utf-8').split())


class TestCacheSyncStepRegenContract:
    def test_regenerates_executor_after_sync(self, skill_text: str) -> None:
        """The step invokes ``generate_executor generate`` (the on-main regen) AFTER
        the sync-engine invocation."""
        sync_idx = skill_text.find('sync-plugin-cache/scripts/sync.py')
        regen_idx = skill_text.find('tools-script-executor:generate_executor generate')
        assert sync_idx != -1, 'sync.py invocation missing from the step body'
        assert regen_idx != -1, 'generate_executor generate invocation missing from the step body'
        # Regen is documented AFTER the sync invocation.
        assert regen_idx > sync_idx

    def test_regen_is_non_fatal(self, skill_text: str) -> None:
        """Regen failure is non-fatal — the step still records its sync outcome and
        logs a WARN."""
        lowered = skill_text.lower()
        assert 'non-fatal' in lowered
        assert 'regeneration failed' in lowered

    def test_regen_unconditional_after_successful_sync(self, skill_text: str) -> None:
        """Regen is unconditional after a successful sync (no gating heuristic)."""
        assert 'unconditional-after-successful-sync' in skill_text.lower()

    def test_regen_runs_in_both_worktree_and_no_worktree_flows(self, skill_text: str) -> None:
        """The step runs the regen in BOTH worktree and no-worktree finalize flows,
        closing the no-worktree staleness gap."""
        lowered = skill_text.lower()
        assert 'both worktree and no-worktree' in lowered
        assert 'staleness gap' in lowered

    def test_integrate_no_longer_owns_regen(self, skill_text: str) -> None:
        """The Ordering section names THIS step as the on-main regen owner and states
        ``integrate_into_main`` does NOT regenerate the executor."""
        assert 'does NOT regenerate the executor' in skill_text
        assert 'project-level owner' in skill_text.lower()
