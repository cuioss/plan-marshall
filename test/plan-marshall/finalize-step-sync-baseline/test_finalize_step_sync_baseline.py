# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the default:finalize-step-sync-baseline finalize-step contract.

The sync-baseline finalize step is a ``standards/*.md`` executor doc (not a
Python script), so this module parses the doc's YAML frontmatter as a pure
function and asserts the declared contract plus the ordering invariant
(``order(sync-baseline) < order(pre-push-quality-gate)``). It does NOT exercise
runtime git behaviour — the rebase mechanics are covered by the existing
``worktree-rebase-to`` / ``baseline-reconcile`` script tests, which this step
reuses unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path

# Repo root resolved from this test file:
# test/plan-marshall/finalize-step-sync-baseline/test_*.py -> repo root is 4 parents up (index 3).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PHASE6_STANDARDS = (
    _REPO_ROOT
    / 'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards'
)
_SYNC_BASELINE_DOC = _PHASE6_STANDARDS / 'finalize-step-sync-baseline.md'
_PRE_PUSH_QUALITY_GATE_DOC = _PHASE6_STANDARDS / 'pre-push-quality-gate.md'

# The step's canonical order — order 3 places it before pre-push-quality-gate
# (order 5) so the early rebase happens before any downstream local quality gate.
_EXPECTED_ORDER = 3
_FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'


def _frontmatter_block(doc: Path) -> str:
    """Return the raw text of the YAML frontmatter block of a standards doc."""
    content = doc.read_text(encoding='utf-8')
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    assert fm_match, f'No YAML frontmatter found in {doc}'
    return fm_match.group(1)


def _read_frontmatter_order(doc: Path) -> int:
    """Parse the integer ``order:`` field from a standards-doc frontmatter block."""
    block = _frontmatter_block(doc)
    order_match = re.search(r'^order:\s*(\d+)\s*$', block, re.MULTILINE)
    assert order_match, f'No `order:` field in {doc} frontmatter'
    return int(order_match.group(1))


def _read_frontmatter_scalar(doc: Path, key: str) -> str:
    """Parse a top-level scalar ``key: value`` field from the frontmatter block."""
    block = _frontmatter_block(doc)
    match = re.search(rf'^{re.escape(key)}:\s*(.+?)\s*$', block, re.MULTILINE)
    assert match, f'No `{key}:` field in {doc} frontmatter'
    return match.group(1)


def _doc_body(doc: Path) -> str:
    """Return the markdown body (everything after the closing frontmatter fence)."""
    content = doc.read_text(encoding='utf-8')
    parts = content.split('\n---', 1)
    assert len(parts) == 2, f'No frontmatter fence to split on in {doc}'
    # Drop everything up to and including the closing fence line.
    after = parts[1].split('\n', 1)
    return after[1] if len(after) == 2 else ''


# ---------------------------------------------------------------------------
# Frontmatter contract
# ---------------------------------------------------------------------------


class TestSyncBaselineFrontmatterContract:
    """The standards doc declares the full finalize-step frontmatter contract."""

    def test_doc_exists(self):
        assert _SYNC_BASELINE_DOC.is_file(), (
            f'sync-baseline standards doc missing at {_SYNC_BASELINE_DOC}'
        )

    def test_name_is_default_finalize_step_sync_baseline(self):
        name = _read_frontmatter_scalar(_SYNC_BASELINE_DOC, 'name')
        assert name == 'default:finalize-step-sync-baseline', (
            f'expected name=default:finalize-step-sync-baseline, got {name!r}'
        )

    def test_order_is_3(self):
        assert _read_frontmatter_order(_SYNC_BASELINE_DOC) == _EXPECTED_ORDER

    def test_mutates_source_is_true(self):
        value = _read_frontmatter_scalar(_SYNC_BASELINE_DOC, 'mutates_source')
        assert value == 'true', (
            f'sync-baseline rebases the worktree HEAD, so mutates_source must be '
            f'true, got {value!r}'
        )

    def test_default_on_is_true(self):
        value = _read_frontmatter_scalar(_SYNC_BASELINE_DOC, 'default_on')
        assert value == 'true', f'expected default_on=true, got {value!r}'

    def test_implements_includes_finalize_step_ext_point(self):
        block = _frontmatter_block(_SYNC_BASELINE_DOC)
        assert _FINALIZE_STEP_EXT_POINT in block, (
            'frontmatter must declare implements: '
            f'{_FINALIZE_STEP_EXT_POINT} for finalize-step discovery'
        )

    def test_presets_member_of_full(self):
        block = _frontmatter_block(_SYNC_BASELINE_DOC)
        presets_match = re.search(r'^presets:\s*\n((?:\s*-\s*\w+\s*\n?)+)', block, re.MULTILINE)
        assert presets_match, 'frontmatter must declare a presets: block'
        members = re.findall(r'-\s*(\w+)', presets_match.group(1))
        assert 'full' in members, (
            f'sync-baseline is a quality-narrowing gate; presets must include '
            f'full, got {members}'
        )

    def test_configurable_declares_auto_rebase_threshold_default_no_overlap_only(self):
        block = _frontmatter_block(_SYNC_BASELINE_DOC)
        assert 'auto_rebase_threshold' in block, (
            'frontmatter must declare a configurable auto_rebase_threshold knob'
        )
        # The key/default pair appears in the configurable: list as
        #   - key: auto_rebase_threshold
        #     default: no_overlap_only
        pair_match = re.search(
            r'key:\s*auto_rebase_threshold\s*\n\s*default:\s*(\S+)',
            block,
        )
        assert pair_match, (
            'auto_rebase_threshold must declare an explicit default in the '
            'configurable: block'
        )
        assert pair_match.group(1) == 'no_overlap_only', (
            f'auto_rebase_threshold default must be no_overlap_only, got '
            f'{pair_match.group(1)!r}'
        )


# ---------------------------------------------------------------------------
# Ordering invariant
# ---------------------------------------------------------------------------


class TestSyncBaselineOrderingInvariant:
    """sync-baseline (order 3) must precede pre-push-quality-gate (order 5)."""

    def test_order_strictly_precedes_pre_push_quality_gate(self):
        sync_order = _read_frontmatter_order(_SYNC_BASELINE_DOC)
        gate_order = _read_frontmatter_order(_PRE_PUSH_QUALITY_GATE_DOC)
        assert sync_order < gate_order, (
            f'sync-baseline order={sync_order} must be < pre-push-quality-gate '
            f'order={gate_order} so the early rebase runs before the downstream '
            f'local quality gates validate the rebased tree'
        )


# ---------------------------------------------------------------------------
# Body contract — reuses existing verbs, no force-push / no ci wait at order 3
# ---------------------------------------------------------------------------


class TestSyncBaselineBodyContract:
    """The body orchestrates only existing verbs and forbids force-push / ci wait."""

    def test_body_cites_baseline_reconcile(self):
        body = _doc_body(_SYNC_BASELINE_DOC)
        assert 'baseline-reconcile' in body, (
            'sync-baseline must classify the rebase via the existing '
            'baseline-reconcile verb'
        )

    def test_body_cites_worktree_rebase_to(self):
        body = _doc_body(_SYNC_BASELINE_DOC)
        assert 'worktree-rebase-to' in body, (
            'sync-baseline must perform the rebase via the existing '
            'worktree-rebase-to verb'
        )

    def test_body_invokes_no_force_push_command(self):
        # Guard against an executable force-push INVOCATION, not the prose word
        # (the body legitimately documents the ABSENCE of force-push). A command
        # invocation is the verb dispatched via the git-workflow executor.
        body = _doc_body(_SYNC_BASELINE_DOC)
        invocation_lines = [
            line for line in body.splitlines()
            if 'force-push-with-lease' in line and 'git-workflow' in line
        ]
        assert not invocation_lines, (
            'at order 3 the branch is not yet pushed — sync-baseline must NOT '
            f'invoke force-push-with-lease, found: {invocation_lines}'
        )

    def test_body_invokes_no_ci_wait_command(self):
        # Guard against an executable `ci ... checks wait` INVOCATION, not the
        # prose word (the body legitimately documents the ABSENCE of a CI wait).
        body = _doc_body(_SYNC_BASELINE_DOC)
        invocation_lines = [
            line for line in body.splitlines()
            if 'checks wait' in line and ':ci ' in line
        ]
        assert not invocation_lines, (
            'at order 3 no PR exists — sync-baseline must NOT invoke a CI wait, '
            f'found: {invocation_lines}'
        )
