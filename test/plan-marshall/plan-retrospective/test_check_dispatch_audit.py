# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``check-dispatch-audit.py`` — the deterministic dispatch audit.

Each detector is exercised BOTH against a deliberately-divergent site (it must
produce a finding — a detector that has never failed is not evidence) AND against
a clean site (it must not fire). The divergent-site assertions are the
"the audit reports a deliberately-divergent step" guard the plan requires.
"""

from __future__ import annotations

import json
from pathlib import Path

from toon_parser import serialize_toon

from conftest import MARKETPLACE_ROOT, run_script

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'check-dispatch-audit.py'
)

_TS = '2026-04-17T11:00:00Z'


def _dispatch_line(role: str, caller: str = 'plan-marshall:phase-6-finalize') -> str:
    return (
        f'[{_TS}] [INFO] [aaaaaa] [DISPATCH] ({caller}) '
        f'target=execution-context-level-3 level=level-3 role={role} '
        f'workflow=plan-marshall:demo/SKILL.md plan_id=demo'
    )


def _step_completed_line(step: str, outcome: str | None = 'done') -> str:
    """One completion line, in the WIDENED form the producer emits today.

    ``outcome=None`` renders the pre-widening form instead. That form is not
    legacy trivia for this consumer: a retrospective reads work logs written by
    earlier runs, so both shapes appear in the real corpus and both must count.
    """
    suffix = f' (outcome={outcome})' if outcome is not None else ''
    return (
        f'[{_TS}] [INFO] [bbbbbb] [STEP] (plan-marshall:phase-6-finalize) '
        f'Completed step: {step}{suffix}'
    )


def _resolve_line(role: str) -> str:
    return (
        f'[{_TS}] [INFO] [cccccc] (plan-marshall:manage-config) '
        f'effort resolve-target role={role} -> target=execution-context-level-3 level=level-3'
    )


def _write_plan(
    tmp_path: Path,
    monkeypatch,
    *,
    plan_id: str = 'dispatch-audit',
    work_lines: list[str] | None = None,
    decision_lines: list[str] | None = None,
    execution_log: list[dict] | None = None,
    phase_steps: dict | None = None,
) -> str:
    """Build a live plan dir with just the surfaces the dispatch audit reads."""
    base = tmp_path / 'base'
    plan_dir = base / 'plans' / plan_id
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True)

    (logs_dir / 'work.log').write_text('\n'.join(work_lines or []) + '\n', encoding='utf-8')
    (logs_dir / 'decision.log').write_text(
        '\n'.join(decision_lines or []) + '\n', encoding='utf-8'
    )

    if execution_log is not None:
        (plan_dir / 'execution.toon').write_text(
            serialize_toon({'execution_log': execution_log}) + '\n', encoding='utf-8'
        )
    status: dict = {'metadata': {}}
    if phase_steps is not None:
        status['metadata']['phase_steps'] = {'6-finalize': phase_steps}
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')

    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id


def _run(plan_id: str) -> dict:
    result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
    assert result.success, result.stderr
    return result.toon()


def _categories(data: dict) -> list[str]:
    findings = data.get('findings') or []
    if isinstance(findings, dict):
        findings = [findings]
    return [f.get('category') for f in findings if isinstance(f, dict)]


def _category(data: dict, name: str) -> dict:
    """Return one ``counts.by_category`` entry — a STRUCTURED value, not an int.

    Every entry carries ``count``, ``status`` and ``evaluated_population``. The
    predecessor published a bare integer, which made ``count: 0`` under a
    never-evaluated check and ``count: 0`` under an evaluated-clean one the same
    bytes; a consumer reading the summary alone could not tell the two apart.
    This accessor exists so every assertion below reads the count THROUGH the
    structure and cannot silently go back to comparing a bare number.
    """
    entry = data['counts']['by_category'][name]
    assert isinstance(entry, dict), (
        f'counts.by_category.{name} must be a structured value carrying its own '
        f'population and status, never a bare count; got {entry!r}'
    )
    return entry


# ---------------------------------------------------------------------------
# D1 — shape_violation: able to fail, population-derived, never a bare 0
# ---------------------------------------------------------------------------


def test_shape_violation_not_evaluated_when_surface_b_empty(tmp_path, monkeypatch):
    # Current finalize reality: [DISPATCH] lines exist, but NO effort
    # resolve-target record (Surface B empty). The check must report
    # not_evaluated with its population, NEVER a bare 0.
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[_dispatch_line('default')],
        decision_lines=['[ts] [INFO] [x] (plan-marshall:phase-4-plan) unrelated decision'],
    )
    data = _run(plan_id)

    shape = data['shape_violation']
    assert shape['status'] == 'not_evaluated'
    assert int(shape['evaluated_population']) == 0
    assert 'Surface B' in shape['reason']
    # The summary entry must carry the same not_evaluated verdict the block does.
    # A bare `0` here is the exact ambiguity the block above removed, reinstated
    # one level up where most readers stop.
    entry = _category(data, 'shape_violation')
    assert int(entry['count']) == 0
    assert entry['status'] == 'not_evaluated'
    assert int(entry['evaluated_population']) == 0


def test_shape_violation_fires_on_divergent_site(tmp_path, monkeypatch):
    # Deliberately-divergent site: a resolve for role=phase-2-refine with NO
    # matching [DISPATCH] emission. The corrected detector MUST produce a finding.
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[_dispatch_line('default')],  # different role — no phase-2-refine dispatch
        decision_lines=[_resolve_line('phase-2-refine')],
    )
    data = _run(plan_id)

    shape = data['shape_violation']
    assert shape['status'] == 'evaluated'
    assert int(shape['evaluated_population']) == 1
    assert int(shape['violations']) == 1
    entry = _category(data, 'shape_violation')
    assert int(entry['count']) == 1
    assert entry['status'] == 'evaluated'
    assert 'shape_violation' in _categories(data)


def test_shape_violation_clean_when_resolve_is_paired(tmp_path, monkeypatch):
    # A resolve WITH its matching dispatch line: evaluated, population 1, zero
    # violations — a legible clean-with-population, not a not_evaluated.
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[_dispatch_line('phase-2-refine')],
        decision_lines=[_resolve_line('phase-2-refine')],
    )
    data = _run(plan_id)

    shape = data['shape_violation']
    assert shape['status'] == 'evaluated'
    assert int(shape['evaluated_population']) == 1
    assert int(shape['violations']) == 0


# ---------------------------------------------------------------------------
# D2 — dispatch_coverage: three states, both mis-attributions corrected
# ---------------------------------------------------------------------------


def test_missing_dispatch_emission_on_dispatched_but_unlogged(tmp_path, monkeypatch):
    # Mis-attribution #1: two steps are token-PROVEN to have dispatched
    # (non-zero tokens) but no [DISPATCH] line was emitted. The detector must
    # report missing_dispatch_emission (an instrumentation finding on the
    # dispatcher), NOT "ran inline where dispatch was required".
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[_step_completed_line('default:finalize-step-simplify')],  # no [DISPATCH] line
        execution_log=[
            {'step_id': 'finalize-step-simplify', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 5000, 'tool_uses': 10},
            {'step_id': 'finalize-step-security-audit', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 3000, 'tool_uses': 6},
        ],
        phase_steps={
            'default:finalize-step-simplify': {'outcome': 'done'},
            'default:finalize-step-security-audit': {'outcome': 'done'},
        },
    )
    data = _run(plan_id)

    coverage = data['dispatch_coverage']
    assert int(coverage['evaluated_population']) == 2
    assert int(coverage['dispatched']) == 2
    assert int(coverage['missing_dispatch_emission']) == 2
    assert 'missing_dispatch_emission' in _categories(data)
    # It must NOT fabricate an inline/discipline finding.
    assert 'dispatch_coverage_violation' not in _categories(data)


def test_conditional_inline_step_not_flagged(tmp_path, monkeypatch):
    # Mis-attribution #2: a step that ran inline (measured-zero token record —
    # e.g. a conditionally-dispatching step that legitimately did not dispatch)
    # must be classified ran_inline and raise NO finding.
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[_step_completed_line('default:adr-propose')],
        execution_log=[
            {'step_id': 'adr-propose', 'phase': '6-finalize',
             'outcome': 'skipped', 'total_tokens': 0, 'tool_uses': 0},
        ],
        phase_steps={'default:adr-propose': {'outcome': 'skipped'}},
    )
    data = _run(plan_id)

    coverage = data['dispatch_coverage']
    assert int(coverage['ran_inline']) == 1
    assert int(coverage['dispatched']) == 0
    assert int(coverage['missing_dispatch_emission']) == 0
    assert _categories(data) == []


def test_no_evidence_when_terminal_step_has_no_token_record(tmp_path, monkeypatch):
    # A terminal step with NO execution_log row is honest no_evidence, never
    # "ran inline" — the second evidence source is absent, so no conclusion.
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[_step_completed_line('default:finalize-step-simplify')],
        execution_log=[],
        phase_steps={'default:finalize-step-simplify': {'outcome': 'done'}},
    )
    data = _run(plan_id)

    coverage = data['dispatch_coverage']
    assert int(coverage['no_evidence']) == 1
    assert int(coverage['dispatched']) == 0
    assert int(coverage['ran_inline']) == 0
    assert int(coverage['missing_dispatch_emission']) == 0
    assert _categories(data) == []


def test_dispatched_step_with_line_is_clean(tmp_path, monkeypatch):
    # A dispatched step (non-zero tokens) WITH its finalize [DISPATCH] line: no
    # missing_dispatch_emission.
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[
            _dispatch_line('default'),
            _step_completed_line('default:finalize-step-simplify'),
        ],
        execution_log=[
            {'step_id': 'finalize-step-simplify', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 5000, 'tool_uses': 10},
        ],
        phase_steps={'default:finalize-step-simplify': {'outcome': 'done'}},
    )
    data = _run(plan_id)

    coverage = data['dispatch_coverage']
    assert int(coverage['dispatched']) == 1
    assert int(coverage['missing_dispatch_emission']) == 0
    assert _categories(data) == []


# ---------------------------------------------------------------------------
# D3 — channel_completeness: a sparse channel downgrades confidence
# ---------------------------------------------------------------------------


def test_sparse_channel_lowers_confidence_to_none(tmp_path, monkeypatch):
    # Completions and a token-proven dispatch, but ZERO [DISPATCH] lines: the
    # audit saw no dispatch evidence at all, so confidence downgrades to 'none'.
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[
            _step_completed_line('default:finalize-step-simplify'),
            _step_completed_line('default:push'),
        ],
        execution_log=[
            {'step_id': 'finalize-step-simplify', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 5000, 'tool_uses': 10},
        ],
        phase_steps={'default:finalize-step-simplify': {'outcome': 'done'}},
    )
    data = _run(plan_id)

    channel = data['channel_completeness']
    assert channel['confidence'] == 'none'
    assert int(channel['dispatch_line_count']) == 0
    assert int(channel['completion_count']) == 2
    assert int(channel['dispatched_step_count']) == 1


def test_completion_count_is_unchanged_by_the_outcome_widening(tmp_path, monkeypatch):
    """The widened marker counts exactly as the pre-widening one did.

    ``completion_count`` is the D3 denominator: the dispatch/completion ratio and
    the confidence grade both divide by it. A read pattern that stopped matching
    one of the two shapes would not fail loudly — it would silently under-count,
    inflate the ratio, and grade a sparse channel as healthy (or, against a wholly
    historical corpus, divide by zero completions and report ``None``).

    Both shapes are therefore counted here over otherwise-identical logs, and the
    two counts are asserted EQUAL rather than each against a literal — the claim
    is parity, so parity is what is checked.
    """
    steps = ['default:finalize-step-simplify', 'default:push', 'default:create-pr']

    def _count(plan_id: str, work_lines: list[str]) -> int:
        # A distinct plan_id per call: the two logs are otherwise identical, and
        # reusing one id would collide on the plan directory.
        written = _write_plan(
            tmp_path,
            monkeypatch,
            plan_id=plan_id,
            work_lines=work_lines,
            execution_log=[],
            phase_steps={},
        )
        return int(_run(written)['channel_completeness']['completion_count'])

    widened = _count('widened-marker', [_step_completed_line(s) for s in steps])
    narrow = _count('narrow-marker', [_step_completed_line(s, outcome=None) for s in steps])

    assert widened == len(steps), (
        f'the widened completion line is not being counted: expected {len(steps)}, '
        f'got {widened}. The audit would under-report every current run.'
    )
    assert narrow == widened, (
        f'the pre-widening line counts differently ({narrow}) from the widened one '
        f'({widened}). A retrospective reads older work logs, so a pattern that '
        f'matches only one shape silently under-counts a whole corpus and grades '
        f'the dispatch/completion ratio against the wrong denominator.'
    )


def test_full_channel_is_nominal_confidence(tmp_path, monkeypatch):
    # Dispatch lines cover the token-proven dispatched steps and the ratio is
    # healthy: confidence is nominal.
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[
            _dispatch_line('default'),
            _step_completed_line('default:finalize-step-simplify'),
        ],
        execution_log=[
            {'step_id': 'finalize-step-simplify', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 5000, 'tool_uses': 10},
        ],
        phase_steps={'default:finalize-step-simplify': {'outcome': 'done'}},
    )
    data = _run(plan_id)

    channel = data['channel_completeness']
    assert channel['confidence'] == 'nominal'
    assert int(channel['dispatch_line_count']) == 1
    assert int(channel['dispatched_step_count']) == 1


def test_low_confidence_when_dispatch_lines_short_of_dispatched_steps(tmp_path, monkeypatch):
    # One [DISPATCH] line but TWO token-proven dispatched steps: a provable
    # shortfall in the channel -> confidence 'low'.
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[
            _dispatch_line('default'),
            _step_completed_line('default:finalize-step-simplify'),
            _step_completed_line('default:finalize-step-security-audit'),
        ],
        execution_log=[
            {'step_id': 'finalize-step-simplify', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 5000, 'tool_uses': 10},
            {'step_id': 'finalize-step-security-audit', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 3000, 'tool_uses': 6},
        ],
        phase_steps={
            'default:finalize-step-simplify': {'outcome': 'done'},
            'default:finalize-step-security-audit': {'outcome': 'done'},
        },
    )
    data = _run(plan_id)

    channel = data['channel_completeness']
    assert channel['confidence'] == 'low'
    assert int(channel['dispatch_line_count']) == 1
    assert int(channel['dispatched_step_count']) == 2


# ---------------------------------------------------------------------------
# Preserved deterministic checks: envelope + generic-subagent
# ---------------------------------------------------------------------------


def test_envelope_violation_on_non_execution_context_target(tmp_path, monkeypatch):
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[
            f'[{_TS}] [INFO] [aaaaaa] [DISPATCH] (plan-marshall:plan-marshall) '
            f'target=general-purpose level=inherit role=phase-3-outline '
            f'workflow=plan-marshall:phase-3-outline/SKILL.md plan_id=demo'
        ],
    )
    data = _run(plan_id)
    entry = _category(data, 'envelope_violation')
    assert int(entry['count']) == 1
    assert entry['status'] == 'evaluated'
    # The population is the [DISPATCH] spawn lines walked — published so a zero
    # from an empty work log is not the same bytes as a zero from a clean one.
    assert int(entry['evaluated_population']) == 1
    assert 'envelope_violation' in _categories(data)


def test_generic_subagent_violation_on_raw_task(tmp_path, monkeypatch):
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        work_lines=[
            f'[{_TS}] [INFO] [aaaaaa] [STATUS] (plan-marshall:phase-5-execute) '
            f'Task: general-purpose spawned'
        ],
    )
    data = _run(plan_id)
    entry = _category(data, 'generic_subagent_violation')
    assert int(entry['count']) == 1
    assert entry['status'] == 'evaluated'
    assert int(entry['evaluated_population']) == 1
    assert 'generic_subagent_violation' in _categories(data)


# ---------------------------------------------------------------------------
# Envelope: absent inputs degrade to not_evaluated / no_evidence, never a crash
# ---------------------------------------------------------------------------


def test_absent_inputs_degrade_cleanly(tmp_path, monkeypatch):
    """Every input empty ⇒ every block says so. NOTHING grades as healthy here.

    ⛔ The channel grade is ``not_evaluated``, NOT ``nominal``. A ``nominal``
    grade is the audit stating it evaluated the channel and found it sound, and
    over an all-empty input set there is nothing it could have evaluated. This
    assertion is the inversion of the one it replaces: the predecessor pinned
    ``nominal`` here, so the defect had a test defending it.
    """
    plan_id = _write_plan(tmp_path, monkeypatch, work_lines=[], decision_lines=[])
    data = _run(plan_id)

    assert data['status'] == 'success'
    assert data['shape_violation']['status'] == 'not_evaluated'
    assert int(data['dispatch_coverage']['evaluated_population']) == 0
    channel = data['channel_completeness']
    assert channel['confidence'] == 'not_evaluated'
    assert channel['reason']
    # The three checks whose own input surface is empty must say so in the summary.
    for name in ('shape_violation', 'envelope_violation', 'generic_subagent_violation'):
        entry = _category(data, name)
        assert int(entry['count']) == 0
        assert entry['status'] == 'not_evaluated', (
            f'{name} reported a count of 0 under status {entry["status"]!r} over an '
            'empty input surface — an evaluated-clean verdict over an empty evaluation'
        )
    # Coverage is DIFFERENT here, and the difference is the point: this fixture
    # writes a status.json carrying a real (empty) metadata mapping, so the
    # population WAS read and genuinely holds zero terminal finalize steps. That
    # is a measured zero, and it must not be reported as "could not look".
    coverage_entry = _category(data, 'missing_dispatch_emission')
    assert int(coverage_entry['count']) == 0
    assert coverage_entry['status'] == 'evaluated'
    assert int(coverage_entry['evaluated_population']) == 0
