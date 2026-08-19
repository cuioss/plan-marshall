#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Covers: start-phase, end-phase, generate, enrich, accumulate-agent-usage subcommands.

Tier 2 (direct import) tests for cmd_* functions, with 2 subprocess
tests retained for CLI plumbing verification.
"""


import pytest
from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_end_phase,
    ns_enrich,
    ns_generate,
    ns_phase_boundary,
    ns_record_dispatch_boundary,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _register_unseeded,
    _unseeded_plan_dir,
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_enrich,
    cmd_generate,
    cmd_record_dispatch_boundary,
    cmd_start_phase,
    manage_metrics,
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


class TestRecordDispatchBoundaryContextLoadColumns:
    """The four per-dispatch context-load columns are appended after the legacy five.

    record-dispatch-boundary records four context-load columns —
    ``input_tokens``, ``output_tokens``, ``cache_read_input_tokens``,
    ``cache_creation_input_tokens`` — appended at the END of each row, and the
    legacy five columns (``timestamp``, ``termination_cause``, ``total_tokens``,
    ``tool_uses``, ``duration_ms``) stay positionally unchanged.

    The four have **no numeric default**: an omitted flag writes the literal
    ``unmeasured`` and omits the key from the result TOON, so "the caller passed
    no measurement" stays distinguishable from "the dispatch loaded zero
    context". A measured zero is still written and returned as ``0``. The
    canonical column order / count / unmeasured representation are owned by
    manage-metrics ``standards/data-format.md`` (Per-Dispatch Context-Load
    Attribution section).
    """

    def test_context_load_columns_recorded_when_supplied(self, plan_context):
        """All four context-load flags land in the result dict and the data row."""
        plan_id = 'rdb-ctx-supplied'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='clean_exit_queue_empty',
                total_tokens=84211,
                tool_uses=38,
                duration_ms=412390,
                input_tokens=38000,
                output_tokens=4000,
                cache_read_input_tokens=210000,
                cache_creation_input_tokens=12000,
            )
        )

        assert result['status'] == 'success', result
        assert result['input_tokens'] == 38000
        assert result['output_tokens'] == 4000
        assert result['cache_read_input_tokens'] == 210000
        assert result['cache_creation_input_tokens'] == 12000
        # Nothing was left unmeasured on this row, and the result says so
        # explicitly rather than by the absence of a complaint.
        assert result['unmeasured_context_load_columns'] == ''

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        # Full nine-column data row: legacy five then the four context-load columns.
        assert ',clean_exit_queue_empty,84211,38,412390,38000,4000,210000,12000' in content

    def test_omitted_context_load_flags_record_unmeasured_not_zero(self, plan_context):
        """Omitting the four flags writes `unmeasured`, NOT 0, and omits the keys.

        The load-bearing assertion is the DISTINCTION: this row and the
        measured-zero row in the companion test below must not be byte-identical
        on columns 6-9, which they were while an omitted flag defaulted to 0.
        """
        plan_id = 'rdb-ctx-default-zero'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='clean_exit_queue_empty',
                total_tokens=1000,
                tool_uses=5,
                duration_ms=2000,
            )
        )

        assert result['status'] == 'success', result
        # ABSENT, not 0 — returning 0 would re-assert in the caller's own reply
        # the measurement the row deliberately declines to claim.
        for column in (
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ):
            assert column not in result, column
        assert result['unmeasured_context_load_columns'] == (
            'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens'
        )

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        # Legacy five carry the supplied values; the four context columns carry
        # the token. The `0,0,0,0` tail the old default produced is GONE.
        assert (
            ',clean_exit_queue_empty,1000,5,2000,unmeasured,unmeasured,unmeasured,unmeasured'
            in content
        )
        assert ',clean_exit_queue_empty,1000,5,2000,0,0,0,0' not in content

    def test_measured_zero_context_load_is_written_as_zero(self, plan_context):
        """An explicitly-passed 0 is a MEASUREMENT and stays 0 on the row.

        The other half of the distinction: the unmeasured token must not swallow
        a real zero. Read together with the companion test above, the two rows
        differ on exactly the four context-load cells.
        """
        plan_id = 'rdb-ctx-measured-zero'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='clean_exit_queue_empty',
                total_tokens=1000,
                tool_uses=5,
                duration_ms=2000,
                input_tokens=0,
                output_tokens=0,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            )
        )

        assert result['status'] == 'success', result
        assert result['input_tokens'] == 0
        assert result['output_tokens'] == 0
        assert result['cache_read_input_tokens'] == 0
        assert result['cache_creation_input_tokens'] == 0
        assert result['unmeasured_context_load_columns'] == ''

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        assert ',clean_exit_queue_empty,1000,5,2000,0,0,0,0' in content
        assert 'unmeasured' not in content

    def test_header_declares_nine_column_order(self, plan_context):
        """The artifact header lists the legacy five then the four context-load columns."""
        plan_id = 'rdb-ctx-header'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(
                plan_id, '5-execute', termination_cause='clean_exit_queue_empty'
            )
        )

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        assert (
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
            'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:'
        ) in content

    def test_legacy_five_columns_positionally_unchanged(self, plan_context):
        """The first five comma-fields are the legacy columns in order, with the
        four context-load columns following at positions 5-8."""
        plan_id = 'rdb-ctx-positional'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='budget_yield',
                total_tokens=1234,
                tool_uses=5,
                duration_ms=6789,
                input_tokens=11,
                output_tokens=22,
                cache_read_input_tokens=33,
                cache_creation_input_tokens=44,
            )
        )

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        data_lines = [
            line for line in artifact.read_text(encoding='utf-8').splitlines()
            if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
        ]
        assert len(data_lines) == 1
        parts = data_lines[0].split(',')
        # Nine columns total: legacy five at positions 0-4, context-load at 5-8.
        assert len(parts) == 9
        # parts[0] is the timestamp (non-empty); legacy positions 1-4 unchanged.
        assert parts[0]
        assert parts[1] == 'budget_yield'
        assert parts[2] == '1234'
        assert parts[3] == '5'
        assert parts[4] == '6789'
        # The four appended context-load columns follow in canonical order.
        assert parts[5:] == ['11', '22', '33', '44']

    def test_per_column_measured_and_unmeasured_mix_on_one_row(self, plan_context):
        """Supplying only input_tokens leaves the other three UNMEASURED, not 0.

        The distinction is per COLUMN, not per row: one measured cell on a row
        does not make its neighbours measured. The legacy five keep their `0`
        default, so this row also pins that the two rules coexist.
        """
        plan_id = 'rdb-ctx-partial'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='clean_exit_queue_empty',
                input_tokens=500,
            )
        )

        assert result['input_tokens'] == 500
        assert 'output_tokens' not in result
        assert 'cache_read_input_tokens' not in result
        assert 'cache_creation_input_tokens' not in result
        assert result['unmeasured_context_load_columns'] == (
            'output_tokens,cache_read_input_tokens,cache_creation_input_tokens'
        )

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        # total/tool/duration omitted → 0 (legacy default, unchanged); input=500
        # measured; the remaining three context columns carry the token.
        assert (
            ',clean_exit_queue_empty,0,0,0,500,unmeasured,unmeasured,unmeasured' in content
        )


# =============================================================================
# Test: require_plan_exists guard on plan-scoped writers (orphan-plan-dir guard)
# =============================================================================


class TestPlanDirGuardOnWriters:
    """Each plan-scoped writer returns ``plan_not_found`` for an uninitialised plan dir.

    TASK-1 routed every plan-scoped writer through ``_guard_plan_exists``, which
    calls ``require_plan_exists`` and converts ``PlanNotFoundError`` into a
    structured ``error: plan_not_found`` envelope instead of silently creating an
    orphan plan tree. These tests assert the guard fires — and the envelope shape
    is uniform — for each guarded command when the plan dir exists but carries no
    ``status.json`` sentinel (the canonical orphan-plan-dir shape).

    The writers all run their argument validation (phase-name / cause checks)
    BEFORE the guard, so each invocation below uses valid phase names to reach the
    guard branch.
    """

    # (label, callable building the result from an unseeded plan_id) for every
    # writer routed through _guard_plan_exists in manage-metrics.py.
    _GUARDED_WRITERS = [
        ('start-phase', lambda pid: cmd_start_phase(ns_start_phase(pid, '1-init'))),
        ('end-phase', lambda pid: cmd_end_phase(ns_end_phase(pid, '1-init'))),
        ('generate', lambda pid: cmd_generate(ns_generate(pid))),
        (
            'phase-boundary',
            lambda pid: manage_metrics.cmd_phase_boundary(
                ns_phase_boundary(pid, '4-plan', '5-execute')
            ),
        ),
        (
            'accumulate-agent-usage',
            lambda pid: cmd_accumulate_agent_usage(
                ns_accumulate(pid, '5-execute', total_tokens=10)
            ),
        ),
        ('enrich', lambda pid: cmd_enrich(ns_enrich(pid, 'any-session'))),
    ]

    @pytest.mark.parametrize(
        'label,invoke',
        _GUARDED_WRITERS,
        ids=[label for label, _ in _GUARDED_WRITERS],
    )
    def test_writer_returns_plan_not_found_for_orphan_plan_dir(
        self, plan_context, label, invoke
    ):
        """An orphan plan dir (exists, no status.json) yields error: plan_not_found."""
        plan_id = _register_unseeded(f'guard-orphan-{label}')
        plan_dir = _unseeded_plan_dir(plan_context, plan_id)

        result = invoke(plan_id)

        assert result['status'] == 'error', result
        assert result['error'] == 'plan_not_found', result
        assert result['plan_id'] == plan_id
        # The envelope surfaces the resolved plan dir and a human-readable message.
        assert str(plan_dir) == result['plan_dir']
        assert 'status.json' in str(result['message'])

        # The guard must NOT have created any metrics artifact for the orphan plan.
        assert not (plan_dir / 'work' / 'metrics.toon').exists()

    @pytest.mark.parametrize(
        'label,invoke',
        _GUARDED_WRITERS,
        ids=[label for label, _ in _GUARDED_WRITERS],
    )
    def test_writer_returns_plan_not_found_when_plan_dir_absent(
        self, plan_context, label, invoke
    ):
        """A plan_id whose dir was never created also trips the guard."""
        plan_id = _register_unseeded(f'guard-absent-{label}')
        # Deliberately do NOT create the directory — the guard must reject it.

        result = invoke(plan_id)

        assert result['status'] == 'error', result
        assert result['error'] == 'plan_not_found', result
        assert result['plan_id'] == plan_id

    def test_writer_succeeds_once_status_json_is_seeded(self, plan_context):
        """Control case: seeding the sentinel flips the same writer back to success.

        Guards the negative tests against a false positive — the failure must come
        from the missing sentinel, not from an unrelated error in the writer path.
        """
        plan_id = 'guard-positive-control'
        # Seeded via the autouse fixture (plan_id is not registered as unseeded).
        result = cmd_start_phase(ns_start_phase(plan_id, '1-init'))
        assert result['status'] == 'success', result
        assert result['phase'] == '1-init'
