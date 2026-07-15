#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the inline-phase (omit-`<usage>`) recording mode.

A phase that runs *inline* in the main orchestrator context — rather than as a
dispatched `execution-context` leaf — produces no agent `<usage>` envelope, so
its `phase-boundary` / `end-phase` close OMITS `--total-tokens` /
`--duration-ms` / `--tool-uses`. This is the sanctioned inline recording mode,
NOT an incomplete call: the closing phase's `end_time` is stamped
unconditionally and `generate`'s partiality verdict keys a phase's *recorded*
status solely off that `end_time` marker.

The omission is at the boundary *write* only — it is NOT a permanent token gap.
The finalize-phase `manage-metrics enrich` pass attributes the parent-window
`message.usage` four-field data to each inline window and derives `total_tokens`
from input + output + cache_creation ONLY (cache_read EXCLUDED, so the inline
row matches the dispatched-phase `<usage>` total definition), so an inline phase
DOES count toward the breakdown Tokens column and the report reads `n=6/6` (not
`n=5/6`). These tests drive the REAL
enrich production path (with a fixture that mirrors the runtime's
post-normalization per-phase bucket shape, per lesson `2026-07-09-14-001`) and
lock that contract:
  - the inline **1-init** window and the recipe-inline **2-refine** / **3-outline**
    windows, closed usage-free, carry a real `total_tokens` after enrich;
  - a dispatched phase's `<usage>`-sourced `total_tokens` is never overwritten
    (explicit-wins);
  - a fully-recorded six-phase plan reports `partial: false` with every phase
    carrying token data (`n=6/6`).
The negative control (an unclosed phase still flips `partial`) keeps the verdict
non-vacuous.
"""

import importlib.util
from argparse import Namespace

import pytest

from conftest import get_script_path

# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location(
    'manage_metrics', get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')
)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)
cmd_phase_boundary = manage_metrics.cmd_phase_boundary
cmd_start_phase = manage_metrics.cmd_start_phase
cmd_end_phase = manage_metrics.cmd_end_phase
cmd_generate = manage_metrics.cmd_generate
cmd_enrich = manage_metrics.cmd_enrich

# Production-shaped per-phase enrich buckets — the exact shape the runtime's
# ``metrics normalized-tokens`` op returns for the three inline phases (the
# canonical ``message.usage`` four-field keys plus the billing-weighted total),
# NOT a synthetic pre-normalization transcript shape (lesson 2026-07-09-14-001).
_INLINE_ENRICH_BUCKETS = {
    # cache_read DOMINATES 1-init (11M) — two orders above the comparable
    # input+output+cache_creation (60K). enrich's inline total_tokens EXCLUDES
    # cache_read, so it must surface ~60K, not the ~11M four-field sum.
    '1-init': {
        'input_tokens': 40000,
        'output_tokens': 15000,
        'cache_read_input_tokens': 11000000,
        'cache_creation_input_tokens': 5000,
        'billing_weighted_total': 12000,
    },
    '2-refine': {
        'input_tokens': 6000,
        'output_tokens': 1500,
        'cache_read_input_tokens': 30000,
        'cache_creation_input_tokens': 0,
        'billing_weighted_total': 9000,
    },
    '3-outline': {
        'input_tokens': 5000,
        'output_tokens': 1200,
        'cache_read_input_tokens': 20000,
        'cache_creation_input_tokens': 0,
        'billing_weighted_total': 7000,
    },
}
# The three-field sum enrich derives into total_tokens for the inline 1-init row
# (input + output + cache_creation — cache_read EXCLUDED). ~60K, not ~11M.
_INIT_INLINE_TOTAL = 40000 + 15000 + 5000
# The cache_read magnitude the derived total must NOT reach.
_INIT_CACHE_READ = 11000000


def _run_inline_enrich(plan_id: str, monkeypatch, buckets: dict | None = None) -> dict:
    """Drive the real cmd_enrich with the runtime op stubbed to inline buckets.

    ``cmd_enrich`` hands the phase windows to the platform-runtime transcript
    engine over a subprocess boundary; the unit test replaces that one seam with
    a production-shaped return so the rest of enrich (four-field raw write + the
    three-field inline total_tokens derivation) runs for real.
    """
    resolved = _INLINE_ENRICH_BUCKETS if buckets is None else buckets

    def _fake_op(session_id, windows):
        counters = {'message_count': 42, 'four_field_phases_attributed': len(resolved)}
        return dict(resolved), counters, 'success'

    monkeypatch.setattr(manage_metrics, '_run_normalized_tokens_op', _fake_op)
    result: dict = cmd_enrich(Namespace(plan_id=plan_id, session_id='sess-inline'))
    return result


# =============================================================================
# require_plan_exists guard fixture (mirrors test_manage_metrics_phase_boundary)
# =============================================================================
#
# Every plan-scoped writer in manage-metrics.py carries a require_plan_exists
# guard that returns ``error: plan_not_found`` unless the plan dir holds a
# ``status.json`` sentinel. The ``plan_context`` fixture creates plan dirs
# without that sentinel, so the positive tests below would otherwise trip the
# guard. This autouse fixture patches the guard chokepoint to auto-materialise
# the sentinel for any plan whose dir exists.


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        plan_dir = real_get_plan_dir(plan_id)
        plan_dir.mkdir(parents=True, exist_ok=True)
        sentinel = plan_dir / 'status.json'
        if not sentinel.is_file():
            sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


# =============================================================================
# Namespace helpers
# =============================================================================


def _ns_start_phase(plan_id, phase):
    return Namespace(plan_id=plan_id, phase=phase, command='start-phase', func=cmd_start_phase)


def _ns_boundary(
    plan_id,
    prev_phase,
    next_phase,
    total_tokens=None,
    duration_ms=None,
    tool_uses=None,
    retrospective_tokens=None,
):
    return Namespace(
        plan_id=plan_id,
        prev_phase=prev_phase,
        next_phase=next_phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
        retrospective_tokens=retrospective_tokens,
        command='phase-boundary',
        func=cmd_phase_boundary,
    )


def _ns_end_phase(
    plan_id,
    phase,
    total_tokens=None,
    duration_ms=None,
    tool_uses=None,
    retrospective_tokens=None,
):
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
        retrospective_tokens=retrospective_tokens,
        command='end-phase',
        func=cmd_end_phase,
    )


def _ns_generate(plan_id):
    return Namespace(plan_id=plan_id, command='generate', func=cmd_generate)


def _phase_block(content: str, phase: str) -> str:
    """Return the metrics.toon text block for a single [phase] section."""
    start = content.index(f'[{phase}]')
    rest = content[start + len(f'[{phase}]'):]
    nxt = rest.find('\n[')
    return rest if nxt == -1 else rest[:nxt]


def _field(block: str, key: str) -> str | None:
    for line in block.splitlines():
        s = line.strip()
        if s.startswith(f'{key}:'):
            return s.split(':', 1)[1].strip()
    return None


def _drive_full_six_phase_plan(plan_id: str) -> None:
    """Record a complete six-phase plan with the inline phases closed usage-free.

    Models the shipped topology: phase-1-init and the recipe-inline refine /
    outline phases run inline (no agent `<usage>`), so their closing
    `phase-boundary` calls OMIT the token/duration/tool-uses flags. The
    dispatched phases (4-plan, 5-execute, 6-finalize) close with usage data.
    Every phase ends up with an `end_time`, so the plan is fully recorded.
    """
    # 1-init opens via the phase-1-init Step 3a self-record, then closes inline.
    cmd_start_phase(_ns_start_phase(plan_id, '1-init'))
    # Inline boundaries — usage flags OMITTED (no agent <usage> envelope).
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='1-init', next_phase='2-refine'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='2-refine', next_phase='3-outline'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='3-outline', next_phase='4-plan'))
    # Dispatched boundaries — usage data present.
    cmd_phase_boundary(
        _ns_boundary(plan_id, prev_phase='4-plan', next_phase='5-execute', total_tokens=42000, tool_uses=15)
    )
    cmd_phase_boundary(
        _ns_boundary(plan_id, prev_phase='5-execute', next_phase='6-finalize', total_tokens=88000, tool_uses=30)
    )
    cmd_end_phase(_ns_end_phase(plan_id, phase='6-finalize', total_tokens=31000, tool_uses=12))


# =============================================================================
# Inline-phase recording: fully-recorded plan is NOT partial
# =============================================================================


def test_inline_init_refine_boundary_records_not_partial(plan_context):
    """A fully-recorded six-phase plan whose init→refine boundary closed inline
    (usage flags omitted) reports partial: false with no unrecorded phases."""
    _drive_full_six_phase_plan('inline-full')

    result = cmd_generate(_ns_generate('inline-full'))

    assert result['status'] == 'success'
    # The inline close of 1-init must NOT make the report partial.
    assert result['partial'] is False
    assert result['unrecorded_phases'] == []


def test_inline_init_phase_carries_total_tokens_after_enrich(plan_context, monkeypatch):
    """After enrich, the inline-closed 1-init row carries a real derived total_tokens.

    The boundary close omitted --total-tokens (no inline `<usage>`), so before
    enrich the row has no total_tokens. The finalize enrich attributes the
    parent-window `message.usage` data to the window and derives total_tokens
    from input + output + cache_creation ONLY — cache_read is EXCLUDED so the
    inline row matches the dispatched-phase `<usage>` total definition. Under
    the cache-read-dominated fixture (cache_read ~11M) the surfaced total must
    be ~60K, NOT ~11M.
    """
    _drive_full_six_phase_plan('inline-init-row')
    enrich_result = _run_inline_enrich('inline-init-row', monkeypatch)
    assert enrich_result['enriched'] is True
    cmd_generate(_ns_generate('inline-init-row'))

    content = (plan_context.plan_dir_for('inline-init-row') / 'work' / 'metrics.toon').read_text()
    init_block = _phase_block(content, '1-init')

    # Recorded: end_time stamped by the inline boundary.
    assert _field(init_block, 'end_time') is not None
    # The four raw usage fields all land on the row (kept for billing analysis) ...
    assert _field(init_block, 'input_tokens') == '40000'
    assert _field(init_block, 'output_tokens') == '15000'
    assert _field(init_block, 'cache_read_input_tokens') == str(_INIT_CACHE_READ)
    # ... but total_tokens is the three-field sum (cache_read EXCLUDED): ~60K.
    total = _field(init_block, 'total_tokens')
    assert total is not None
    assert int(total) == _INIT_INLINE_TOTAL
    # The cache-read magnitude must NOT leak into the derived total.
    assert int(total) < _INIT_CACHE_READ


def test_inline_init_phase_absent_from_unrecorded_list(plan_context):
    """1-init never appears under unrecorded_phases despite carrying no usage data."""
    _drive_full_six_phase_plan('inline-not-unrecorded')
    result = cmd_generate(_ns_generate('inline-not-unrecorded'))

    assert '1-init' not in result['unrecorded_phases']
    # The persisted top-level marker agrees with the returned verdict.
    content = (plan_context.plan_dir_for('inline-not-unrecorded') / 'work' / 'metrics.toon').read_text()
    assert 'partial: false' in content
    assert 'unrecorded_phases:' in content


def test_recipe_inline_refine_outline_carry_total_tokens_after_enrich(plan_context, monkeypatch):
    """The recipe-inline 2-refine / 3-outline phases carry a derived total_tokens after enrich."""
    _drive_full_six_phase_plan('inline-recipe')
    _run_inline_enrich('inline-recipe', monkeypatch)
    result = cmd_generate(_ns_generate('inline-recipe'))

    assert result['partial'] is False
    for phase in ('2-refine', '3-outline'):
        assert phase not in result['unrecorded_phases']

    content = (plan_context.plan_dir_for('inline-recipe') / 'work' / 'metrics.toon').read_text()
    for phase in ('2-refine', '3-outline'):
        block = _phase_block(content, phase)
        assert _field(block, 'end_time') is not None
        # After enrich the recipe-inline close carries a real derived total_tokens.
        total = _field(block, 'total_tokens')
        assert total is not None
        assert int(total) > 0


def test_report_is_n_six_of_six_after_inline_enrich(plan_context, monkeypatch):
    """Every one of the six phases carries token data after inline enrich (n=6/6)."""
    _drive_full_six_phase_plan('inline-n6')
    _run_inline_enrich('inline-n6', monkeypatch)
    result = cmd_generate(_ns_generate('inline-n6'))

    assert result['partial'] is False
    content = (plan_context.plan_dir_for('inline-n6') / 'work' / 'metrics.toon').read_text()
    # All six canonical phases now carry a truthy total_tokens — the tokens
    # column completeness is 6/6, so the breakdown Total is a plain sum with no
    # (n=k/6) shortfall marker on the tokens column.
    for phase in manage_metrics.PHASE_NAMES:
        block = _phase_block(content, phase)
        total = _field(block, 'total_tokens')
        assert total is not None and int(total) > 0, f'{phase} is missing total_tokens'


def test_enrich_does_not_overwrite_dispatched_phase_total(plan_context, monkeypatch):
    """Explicit-wins: a dispatched phase's <usage> total_tokens is never clobbered by enrich.

    Even when enrich attributes four-field data to a phase that already carries a
    dispatched `<usage>` total, the derivation only fills an ABSENT total_tokens,
    so the dispatched value is preserved byte-for-byte.
    """
    _drive_full_six_phase_plan('inline-explicit-wins')
    # 4-plan closed with total_tokens=42000 (dispatched). Feed enrich a tiny
    # four-field bucket for it; the derivation must NOT overwrite the real total.
    buckets = {'4-plan': {'input_tokens': 1, 'output_tokens': 1, 'billing_weighted_total': 2}}
    _run_inline_enrich('inline-explicit-wins', monkeypatch, buckets=buckets)
    cmd_generate(_ns_generate('inline-explicit-wins'))

    content = (plan_context.plan_dir_for('inline-explicit-wins') / 'work' / 'metrics.toon').read_text()
    plan_block = _phase_block(content, '4-plan')
    assert int(_field(plan_block, 'total_tokens')) == 42000


# =============================================================================
# Negative control: an un-closed phase DOES flip partial (verdict is real)
# =============================================================================


def test_unclosed_phase_still_flips_partial(plan_context):
    """A phase with no end_time is unrecorded — proving the verdict isn't always false.

    This guards against a regression that would treat every phase as recorded
    (which would make the positive tests pass vacuously). The 6-finalize phase
    is started but never closed, so it must surface as unrecorded / partial.
    """
    plan_id = 'inline-partial-neg'
    cmd_start_phase(_ns_start_phase(plan_id, '1-init'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='1-init', next_phase='2-refine'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='2-refine', next_phase='3-outline'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='3-outline', next_phase='4-plan'))
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='4-plan', next_phase='5-execute'))
    # 5-execute → 6-finalize opens 6-finalize but it is never closed (no end_time).
    cmd_phase_boundary(_ns_boundary(plan_id, prev_phase='5-execute', next_phase='6-finalize'))

    result = cmd_generate(_ns_generate(plan_id))

    assert result['partial'] is True
    assert result['unrecorded_phases'] == ['6-finalize']
    # The inline-closed early phases are still recorded — only 6-finalize is missing.
    assert '1-init' not in result['unrecorded_phases']
    assert '2-refine' not in result['unrecorded_phases']
