#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the inline-phase (omit-`<usage>`) recording mode.

A phase that runs *inline* in the main orchestrator context — rather than as a
dispatched `execution-context` leaf — produces no agent `<usage>` envelope, so
its `phase-boundary` / `end-phase` close OMITS `--total-tokens` /
`--duration-ms` / `--tool-uses`. This is the sanctioned inline recording mode,
NOT an incomplete call: the closing phase's `end_time` is stamped
unconditionally and `generate`'s `end_time`-presence check
(`any_phase_missing_end_time` / `phases_missing_end_time`) reads solely that
marker.

The omission is at the boundary *write* only — it is NOT a permanent token gap.
The finalize-phase `manage-metrics enrich` pass attributes the parent-window
`message.usage` four-field data to each inline window and derives `total_tokens`
from input + output + cache_creation ONLY (cache_read EXCLUDED, so the inline
row matches the dispatched-phase `<usage>` total definition), so an inline phase
DOES count toward the breakdown Tokens column and the report reads `n=6/6` (not
`n=5/6`). These tests drive the REAL
enrich production path (with a fixture that mirrors the runtime's
post-normalization per-phase bucket shape) and lock that contract:
  - the inline **1-init** window and the recipe-inline **2-refine** / **3-outline**
    windows, closed usage-free, carry a real `total_tokens` after enrich;
  - a dispatched phase's `<usage>`-sourced `total_tokens` is never overwritten
    (explicit-wins);
  - a six-phase plan whose rows all carry `end_time` reports
    `any_phase_missing_end_time: false` with every phase carrying token data
    (`n=6/6`).
The negative control (an unclosed phase still flips
`any_phase_missing_end_time`) keeps the check non-vacuous.
"""


import pytest
from _manage_metrics_fixtures import (
    ns_generate,
    ns_phase_boundary,
    ns_start_phase,
)
from _phase_boundary_inline_fixtures import (
    _INIT_CACHE_READ,
    _INIT_INLINE_TOTAL,
    _drive_full_six_phase_plan,
    _field,
    _phase_block,
    _run_inline_enrich,
    cmd_generate,
    cmd_phase_boundary,
    cmd_start_phase,
    manage_metrics,
)

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
# Inline-phase recording: an inline close still carries its end_time marker
# =============================================================================


def test_inline_init_refine_boundary_carries_end_time_marker(plan_context):
    """A six-phase plan whose init→refine boundary closed inline (usage flags
    omitted) reports every row as carrying its end_time marker."""
    _drive_full_six_phase_plan('inline-full')

    result = cmd_generate(ns_generate('inline-full'))

    assert result['status'] == 'success'
    # The inline close of 1-init stamps end_time like any other close.
    assert result['any_phase_missing_end_time'] is False
    assert result['phases_missing_end_time'] == []


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
    cmd_generate(ns_generate('inline-init-row'))

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


def test_inline_init_phase_absent_from_missing_end_time_list(plan_context):
    """1-init never appears under phases_missing_end_time despite carrying no usage data."""
    _drive_full_six_phase_plan('inline-not-unrecorded')
    result = cmd_generate(ns_generate('inline-not-unrecorded'))

    assert '1-init' not in result['phases_missing_end_time']
    # The persisted top-level keys agree with the returned values, and the
    # retired pair is absent from the file entirely (breaking rename, no shim).
    content = (plan_context.plan_dir_for('inline-not-unrecorded') / 'work' / 'metrics.toon').read_text()
    assert 'any_phase_missing_end_time: false' in content
    assert 'phases_missing_end_time:' in content
    assert 'partial: false' not in content
    assert 'unrecorded_phases:' not in content


# =============================================================================
# Inline main-context attribution on a MIXED phase (D2): a 6-finalize phase that
# ran BOTH dispatched steps (total_tokens present) AND inline steps (four-field
# usage present) surfaces the inline contribution as a distinct field.
# =============================================================================


def test_inline_main_context_surfaced_on_mixed_finalize_phase(plan_context, monkeypatch):
    """A 6-finalize phase carrying BOTH a dispatched total_tokens AND four-field usage
    surfaces inline_main_context_tokens (input+output+cache_creation, cache_read
    EXCLUDED), keeps total_tokens byte-identical, and keeps its end_time marker
    (#812).
    """
    _drive_full_six_phase_plan('inline-mixed-finalize')
    # 6-finalize closed with dispatched total_tokens=31000. Feed enrich a
    # four-field bucket for it — the inline finalize-step contribution. The
    # enrich else-branch must surface inline_main_context_tokens without
    # overwriting the dispatched total.
    buckets = {
        '6-finalize': {
            'input_tokens': 20000,
            'output_tokens': 8000,
            'cache_read_input_tokens': 500000,
            'cache_creation_input_tokens': 2000,
            'billing_weighted_total': 40000,
        },
    }
    _run_inline_enrich('inline-mixed-finalize', monkeypatch, buckets=buckets)
    result = cmd_generate(ns_generate('inline-mixed-finalize'))

    # #812: the timestamps-closed row keeps its end_time marker — attribution
    # never touches it.
    assert result['any_phase_missing_end_time'] is False

    content = (plan_context.plan_dir_for('inline-mixed-finalize') / 'work' / 'metrics.toon').read_text()
    fin_block = _phase_block(content, '6-finalize')
    # Explicit-wins: the dispatched total_tokens is byte-identical.
    assert int(_field(fin_block, 'total_tokens')) == 31000
    # inline_main_context_tokens = 20000 + 8000 + 2000 = 30000 (cache_read EXCLUDED).
    inline_field = _field(fin_block, 'inline_main_context_tokens')
    assert inline_field is not None
    assert int(inline_field) == 30000
    # The cache_read magnitude must NOT leak into the surfaced inline figure.
    assert int(inline_field) < 500000

    # generate renders the inline reconciliation line under the phase total.
    md = (plan_context.plan_dir_for('inline-mixed-finalize') / 'metrics.md').read_text()
    assert 'Inline main-context tokens' in md


# =============================================================================
# Inline-phase recording: an inline close still carries its end_time marker
# =============================================================================

def test_recipe_inline_refine_outline_carry_total_tokens_after_enrich(plan_context, monkeypatch):
    """The recipe-inline 2-refine / 3-outline phases carry a derived total_tokens after enrich."""
    _drive_full_six_phase_plan('inline-recipe')
    _run_inline_enrich('inline-recipe', monkeypatch)
    result = cmd_generate(ns_generate('inline-recipe'))

    assert result['any_phase_missing_end_time'] is False
    for phase in ('2-refine', '3-outline'):
        assert phase not in result['phases_missing_end_time']

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
    result = cmd_generate(ns_generate('inline-n6'))

    assert result['any_phase_missing_end_time'] is False
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
    cmd_generate(ns_generate('inline-explicit-wins'))

    content = (plan_context.plan_dir_for('inline-explicit-wins') / 'work' / 'metrics.toon').read_text()
    plan_block = _phase_block(content, '4-plan')
    assert int(_field(plan_block, 'total_tokens')) == 42000


# =============================================================================
# Negative control: an un-closed phase DOES flip the check (it is not vacuous)
# =============================================================================


def test_unclosed_phase_still_flips_missing_end_time(plan_context):
    """A phase with no end_time is listed — proving the check isn't always false.

    This guards against a regression that would treat every row as carrying the
    marker (which would make the positive tests pass vacuously). The 6-finalize
    phase is started but never closed, so it must surface in
    phases_missing_end_time.
    """
    plan_id = 'inline-partial-neg'
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase='1-init', next_phase='2-refine'))
    cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase='2-refine', next_phase='3-outline'))
    cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase='3-outline', next_phase='4-plan'))
    cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase='4-plan', next_phase='5-execute'))
    # 5-execute → 6-finalize opens 6-finalize but it is never closed (no end_time).
    cmd_phase_boundary(ns_phase_boundary(plan_id, prev_phase='5-execute', next_phase='6-finalize'))

    result = cmd_generate(ns_generate(plan_id))

    assert result['any_phase_missing_end_time'] is True
    assert result['phases_missing_end_time'] == ['6-finalize']
    # The inline-closed early phases still carry their marker — only 6-finalize
    # is missing one.
    assert '1-init' not in result['phases_missing_end_time']
    assert '2-refine' not in result['phases_missing_end_time']


# =============================================================================
# Inline main-context attribution on a MIXED phase (D2): a 6-finalize phase that
# ran BOTH dispatched steps (total_tokens present) AND inline steps (four-field
# usage present) surfaces the inline contribution as a distinct field.
# =============================================================================

def test_dispatched_phase_without_four_field_usage_is_marked_unmeasured(plan_context, monkeypatch):
    """A dispatched phase enrich never attributed carries the unmeasured marker.

    `enrich` writes no inline figure for such a phase, and `generate` must not
    leave the field absent: absence conflated "enrich measured no inline spend"
    with "enrich never looked at this phase". The discriminator is the row's own
    `total_tokens_population` stamp, which enrich writes on every row it visits —
    this phase carries none, so the honest value is the marker, not a `0`.
    """
    _drive_full_six_phase_plan('inline-no-fourfield')
    # Feed enrich buckets ONLY for the inline early phases; 5-execute (dispatched
    # total_tokens=88000) receives no four-field usage.
    _run_inline_enrich('inline-no-fourfield', monkeypatch)
    cmd_generate(ns_generate('inline-no-fourfield'))

    content = (plan_context.plan_dir_for('inline-no-fourfield') / 'work' / 'metrics.toon').read_text()
    exec_block = _phase_block(content, '5-execute')
    assert int(_field(exec_block, 'total_tokens')) == 88000
    assert _field(exec_block, 'inline_main_context_tokens') == 'unmeasured'
    assert _field(exec_block, 'total_tokens_population') is None
