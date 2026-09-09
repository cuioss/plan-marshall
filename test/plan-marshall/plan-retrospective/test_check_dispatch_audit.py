# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``check-dispatch-audit.py`` — the deterministic dispatch audit.

Each detector is exercised BOTH against a deliberately-divergent site (it must
produce a finding — a detector that has never failed is not evidence) AND against
a clean site (it must not fire). The divergent-site assertions are the
"the audit reports a deliberately-divergent step" guard the plan requires.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from toon_parser import serialize_toon

from conftest import MARKETPLACE_ROOT, run_script

SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-dispatch-audit.py'
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
    return f'[{_TS}] [INFO] [bbbbbb] [STEP] (plan-marshall:phase-6-finalize) Completed step: {step}{suffix}'


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
    (logs_dir / 'decision.log').write_text('\n'.join(decision_lines or []) + '\n', encoding='utf-8')

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
            {
                'step_id': 'finalize-step-simplify',
                'phase': '6-finalize',
                'outcome': 'done',
                'total_tokens': 5000,
                'tool_uses': 10,
            },
            {
                'step_id': 'finalize-step-security-audit',
                'phase': '6-finalize',
                'outcome': 'done',
                'total_tokens': 3000,
                'tool_uses': 6,
            },
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
            {'step_id': 'adr-propose', 'phase': '6-finalize', 'outcome': 'skipped', 'total_tokens': 0, 'tool_uses': 0},
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
            {
                'step_id': 'finalize-step-simplify',
                'phase': '6-finalize',
                'outcome': 'done',
                'total_tokens': 5000,
                'tool_uses': 10,
            },
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
            {
                'step_id': 'finalize-step-simplify',
                'phase': '6-finalize',
                'outcome': 'done',
                'total_tokens': 5000,
                'tool_uses': 10,
            },
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
            {
                'step_id': 'finalize-step-simplify',
                'phase': '6-finalize',
                'outcome': 'done',
                'total_tokens': 5000,
                'tool_uses': 10,
            },
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
            {
                'step_id': 'finalize-step-simplify',
                'phase': '6-finalize',
                'outcome': 'done',
                'total_tokens': 5000,
                'tool_uses': 10,
            },
            {
                'step_id': 'finalize-step-security-audit',
                'phase': '6-finalize',
                'outcome': 'done',
                'total_tokens': 3000,
                'tool_uses': 6,
            },
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
# D6-S03 — the RATIO arm of the ``low`` grade, and its strict-comparison edge
# ---------------------------------------------------------------------------
#
# ``low`` is reached by two independent branches, and every fixture above and in
# the measurement-contract sibling reaches it through the FIRST one (fewer
# dispatch lines than token-proven dispatched steps). The second — a
# dispatch/completion ratio under ``_SPARSE_RATIO`` — had no fixture at all, so
# deleting that branch, or flipping its comparison, changed no test.
#
# The two cases below are the sparse-but-NONZERO case (dispatch lines present, no
# shortfall against the proven dispatches, ratio under the threshold) and the
# strict-comparison boundary (ratio EXACTLY at the threshold, which the strict
# ``<`` must leave nominal). They are a matched pair over otherwise-identical
# fixtures differing by one completion line, so the grade flip is attributable to
# the ratio and to nothing else.
#
# The threshold is READ FROM THE SCRIPT rather than restated as ``0.5``: a
# literal here would keep passing after the production constant moved, grading
# the boundary against a threshold the script no longer uses.

#: The ``_SPARSE_RATIO`` declaration in the audit script. The value group is
#: unbounded so a threshold changed to any number is still read, rather than the
#: pattern silently failing to match and the tests below going vacuous.
_SPARSE_RATIO_DECL_RE = re.compile(r'^_SPARSE_RATIO\s*=\s*(?P<value>[0-9]*\.?[0-9]+)\s*$', re.MULTILINE)

#: The token-proven dispatched step shared by both ratio fixtures. One step, one
#: finalize [DISPATCH] line — so the shortfall branch cannot fire and the ratio
#: branch is the only one left that can grade ``low``.
_RATIO_STEP = 'default:finalize-step-simplify'
_RATIO_TOKEN_ROW = {
    'step_id': 'finalize-step-simplify',
    'phase': '6-finalize',
    'outcome': 'done',
    'total_tokens': 5000,
}


def _sparse_ratio_threshold() -> float:
    """The ``_SPARSE_RATIO`` value the script actually compares against."""
    match = _SPARSE_RATIO_DECL_RE.search(SCRIPT_PATH.read_text(encoding='utf-8'))
    assert match, (
        f'{SCRIPT_PATH} no longer declares a module-level `_SPARSE_RATIO` constant. '
        'The boundary tests below derive their fixtures from it, so a missing '
        'declaration must fail loudly here rather than let them assert against a '
        'threshold nothing uses.'
    )
    return float(match.group('value'))


def _ratio_channel(tmp_path, monkeypatch, plan_id: str, completion_steps: list[str]) -> dict:
    """One finalize dispatch line and one token-proven step over N completions."""
    written = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id=plan_id,
        work_lines=[_dispatch_line('default'), *(_step_completed_line(s) for s in completion_steps)],
        execution_log=[dict(_RATIO_TOKEN_ROW)],
        phase_steps={_RATIO_STEP: {'outcome': 'done'}},
    )
    return _run(written)['channel_completeness']


def test_sparse_but_nonzero_channel_grades_low_on_the_ratio_alone(tmp_path, monkeypatch):
    """A populated-but-thin channel downgrades even with no dispatch shortfall.

    Every other ``low`` fixture reaches the grade through the shortfall branch, so
    this is the first that exercises the ratio branch: the dispatch-line count
    MATCHES the token-proven dispatched-step count (asserted below, because that
    equality is what rules the shortfall branch out), and the only thing left that
    can downgrade the grade is the ratio.
    """
    channel = _ratio_channel(
        tmp_path,
        monkeypatch,
        'ratio-sparse-nonzero',
        ['default:finalize-step-simplify', 'default:push', 'default:create-pr'],
    )

    assert int(channel['dispatch_line_count']) == 1, 'the channel must be NONZERO, not the `none` grade'
    assert int(channel['dispatch_line_count']) == int(channel['dispatched_step_count']), (
        'the shortfall branch must be ruled out, or this fixture would grade low '
        'for the reason the sibling tests already cover'
    )
    assert float(channel['ratio']) < _sparse_ratio_threshold()
    assert channel['confidence'] == 'low', (
        'a nonzero but thin channel — one dispatch line against three completions — '
        f'must downgrade on the ratio; got {channel["confidence"]!r}'
    )


def test_ratio_exactly_at_the_threshold_stays_nominal(tmp_path, monkeypatch):
    """The comparison is strict: AT the threshold is not UNDER it.

    Paired with the test above over a fixture that differs by exactly one
    completion line. Flipping the production ``<`` to ``<=`` turns this green
    fixture red, which is what makes the strictness observable — the sparse case
    alone passes under either operator.
    """
    channel = _ratio_channel(
        tmp_path,
        monkeypatch,
        'ratio-at-threshold',
        ['default:finalize-step-simplify', 'default:push'],
    )

    assert float(channel['ratio']) == _sparse_ratio_threshold(), (
        'the fixture no longer sits exactly on the threshold, so it no longer tests '
        'the boundary; regenerate the completion count from the threshold'
    )
    assert int(channel['dispatch_line_count']) == int(channel['dispatched_step_count'])
    assert channel['confidence'] == 'nominal', (
        'a ratio equal to the sparse threshold is not under it — the comparison is '
        f'strict; got {channel["confidence"]!r}'
    )


def test_one_more_completion_is_what_flips_the_grade(tmp_path, monkeypatch):
    """The pair above, asserted as a pair — the delta is one completion line.

    Read separately, each test is consistent with a grader that ignores the ratio
    entirely and happens to return the expected constant. Asserting that the two
    otherwise-identical fixtures DISAGREE is the claim neither can make alone.
    """
    at_threshold = _ratio_channel(tmp_path, monkeypatch, 'flip-at-threshold', ['default:a', 'default:b'])
    below_threshold = _ratio_channel(
        tmp_path, monkeypatch, 'flip-below-threshold', ['default:a', 'default:b', 'default:c']
    )

    assert int(below_threshold['completion_count']) == int(at_threshold['completion_count']) + 1
    assert int(below_threshold['dispatch_line_count']) == int(at_threshold['dispatch_line_count'])
    assert int(below_threshold['dispatched_step_count']) == int(at_threshold['dispatched_step_count'])
    assert (at_threshold['confidence'], below_threshold['confidence']) == ('nominal', 'low')


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
        work_lines=[f'[{_TS}] [INFO] [aaaaaa] [STATUS] (plan-marshall:phase-5-execute) Task: general-purpose spawned'],
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


# ---------------------------------------------------------------------------
# Document contract: the metrics reconcile the efficiency aspect depends on
# ---------------------------------------------------------------------------
#
# ⛔ Scope of this section, stated so it is not read for more than it checks.
#
# Every test ABOVE drives ``check-dispatch-audit.py`` directly. The retrospective
# workflow's own prose is a separate artefact, and one of its steps — the
# ``manage-metrics generate`` reconcile that closes the open ``6-finalize``
# accumulator before the plan-efficiency aspect reads ``metrics.md`` — is shipped
# ONLY as prose. Nothing executes it in a test, so deleting the step from
# ``SKILL.md`` left this whole directory green: the deliverable could be reverted
# without a single failure.
#
# These tests close that hole and NOTHING else. They assert the invocation is
# still in the workflow, still positioned ahead of the aspect that consumes its
# output, and still carries its live-modes-only bound. They do NOT assert that a
# run performs the reconcile, that the reconcile produces correct numbers, or
# that the aspect reads the reconciled file — none of that is observable from the
# document, and a green here is not evidence of any of it.
#
# The anchors are the COMMAND STRING and the ORDER, never a heading and never the
# step number: both of those move under ordinary renumbering while the invocation
# and its position relative to its consumer do not.

_RETRO_SKILL_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'SKILL.md'

#: The reconcile invocation itself — the load-bearing literal of the prose step.
_METRICS_RECONCILE_COMMAND = 'plan-marshall:manage-metrics:manage-metrics generate'

#: The canonical registry key of the aspect that CONSUMES the reconciled file.
#: Backticked, so the row's ``references/plan-efficiency.md`` cell is not matched.
_CONSUMING_ASPECT_KEY = '`plan-efficiency`'

#: The archived-mode bound, as ONE normative prohibition on the WRITE whose TARGET
#: is the archived plan directory.
#:
#: ⛔ Deliberately not two independent substring checks. Testing ``'archived' in
#: conditions`` and ``'MUST NOT' in conditions`` separately is satisfied by a region
#: that PERMITS archived writes while forbidding some unrelated action — strictly
#: weaker than the property the failure message names ("the archived-mode exclusion
#: is no longer normative"). The tokens must belong to one statement: the
#: prohibition, the write, and the archived target inside a single sentence, which
#: is what ``[^.]`` enforces (a sentence boundary breaks the span).
#:
#: ⛔ Co-occurrence inside one sentence is still not the property, and that is the
#: same archetype recurring one level in. "Archived mode may write to the archived
#: plan directory, but the caller MUST NOT write the execution summary after
#: archived sync" chains ``MUST NOT`` → ``write`` → ``archived`` within a single
#: sentence while EXPRESSLY PERMITTING the archived write: the prohibition governs
#: the execution summary, and ``archived`` is merely a later co-occurring noun. The
#: destination preposition is therefore required between the verb and the target —
#: it is what makes the archived directory the thing being written TO rather than a
#: word that happens to follow ``write``.
#:
#: The word-order-agnostic alternative (``archived`` … ``MUST NOT`` … ``write``) was
#: REMOVED rather than kept alongside this one. The shipped wording puts the target
#: after the verb, so the reversed order bought no coverage for the real document
#: while admitting exactly the permissive shape above.
#:
#: ⛔ Removing that alternative is NOT on its own sufficient, and the measurement
#: says so: with the reversed alternative deleted and the preposition absent, the
#: permissive sentence still matches, because "MUST NOT write the execution summary
#: after archived sync" chains the three tokens in the accepted order. The
#: preposition is the part that actually closes the hole.
#:
#: ⛔ The preposition alone is STILL not the property — the same archetype, one noun
#: further in. Binding ``to|into`` to the bare token ``archived`` makes ANY
#: archived-named destination satisfy the prohibition, so this region matches while
#: expressly permitting the write the docstring above names:
#:
#:     "Archived mode may write the reconciled metrics back into the archived plan
#:      directory, but the caller MUST NOT write to the archived handshakes ledger"
#:
#: The prohibition there governs the handshakes ledger; the archived plan directory
#: is the thing being written to, permissively. The target NOUN is therefore matched,
#: not just the adjective: the property is a prohibition on the write whose target is
#: the archived plan directory, and nothing weaker.
_ARCHIVED_WRITE_PROHIBITION = re.compile(
    r'\bMUST NOT\b[^.]{0,160}?\bwrite\b[^.]{0,40}?\b(?:to|into)\b[^.]{0,40}?'
    r'\barchived plan director(?:y|ies)\b',
    re.IGNORECASE,
)

#: The pre-fix two-alternative pattern, kept ONLY as the fixture-sanity oracle for
#: the permissive-write arm below.
#:
#: That arm must be ADMITTED here and REJECTED by the shipped pattern above. Without
#: the admission half the arm could go green because the fixture drifted into some
#: unrelated shape the pattern was never going to match — which is precisely the
#: "passes for the wrong reason" defect this whole section exists to remove.
_PRE_FIX_ARCHIVED_WRITE_PROHIBITION = re.compile(
    r'\bMUST NOT\b[^.]{0,160}?\bwrite\b[^.]{0,160}?\barchived\b'
    r'|\barchived\b[^.]{0,160}?\bMUST NOT\b[^.]{0,160}?\bwrite\b',
    re.IGNORECASE,
)


def _reconcile_offset(text: str) -> int:
    """Character offset of the reconcile invocation, or ``-1`` when absent."""
    return text.find(_METRICS_RECONCILE_COMMAND)


def _consumer_offset(text: str) -> int:
    """Character offset of the consuming aspect's registry key, or ``-1``."""
    return text.find(_CONSUMING_ASPECT_KEY)


#: A next-step level-3 ATX heading — the reconcile region's TERMINATOR.
#:
#: ⛔ Deliberately not ``text.find('\n### ')``. That literal recognises only an
#: UNINDENTED marker followed by EXACTLY ONE SPACE, while CommonMark admits up to
#: three leading spaces on an ATX heading and admits a tab — or the end of the line
#: — after the marker. A next step written ``  ### Step 2.6: …`` was therefore not
#: seen as a terminator at all: the region ran past the end of the reconcile step,
#: and an archived-write prohibition belonging to some LATER step satisfied the
#: bound for a reconcile step that carries none. The extracted span was derived
#: from a narrower rule than the one this region's own docstring states, which is
#: this section's own archetype turned on the section itself.
#:
#: ⛔ ``re.MULTILINE`` is load-bearing, not decorative. Without it ``$`` anchors to
#: the end of the whole document, so a bare ``###`` heading in the middle of one
#: would terminate nothing and the end-of-line marker form would go unrecognised.
#:
#: A level-4 ``####`` heading is correctly NOT a terminator: it is a subsection of
#: the step the region is reading, and the character after the third ``#`` is
#: neither whitespace nor an end of line.
_NEXT_STEP_HEADING = re.compile(r'\n {0,3}###(?:[ \t]+|$)', re.MULTILINE)


def _reconcile_conditions(text: str) -> str:
    """The prose from the reconcile invocation to the next level-3 step heading.

    "Next level-3 heading" means every form CommonMark admits — see
    :data:`_NEXT_STEP_HEADING` for the accepted indents and marker terminators. The
    docstring names the same rule the pattern implements, deliberately: the defect
    this helper carried was a span derived from a NARROWER rule than the one stated
    here, so the two are kept in step rather than left to drift apart again.

    The heading is used as a TERMINATOR only — the region is entered at the
    command string, so a renamed or renumbered step heading does not move it.
    """
    start = _reconcile_offset(text)
    if start < 0:
        return ''
    next_step = _NEXT_STEP_HEADING.search(text, start)
    return text[start:] if next_step is None else text[start : next_step.start()]


def _pre_fix_reconcile_conditions(text: str) -> str:
    """The region as the PRE-FIX literal terminator bounded it.

    Kept ONLY as the fixture-sanity oracle for the widened-heading arms below. Each
    of those arms must be ADMITTED here — the region overrunning the indented or
    tab-marked heading and reaching the LATER step's prohibition — and terminated
    by the shipped pattern. Without the admission half an arm could go green
    because its fixture drifted into some shape carrying no prohibition anywhere,
    proving nothing about the indentation gap it names.
    """
    start = _reconcile_offset(text)
    if start < 0:
        return ''
    end = text.find('\n### ', start)
    return text[start:] if end < 0 else text[start:end]


def test_retrospective_workflow_still_carries_the_metrics_reconcile():
    text = _RETRO_SKILL_DOC.read_text(encoding='utf-8')

    assert _reconcile_offset(text) >= 0, (
        f'{_RETRO_SKILL_DOC} no longer invokes {_METRICS_RECONCILE_COMMAND!r}. The '
        'step is shipped as prose only, so its deletion is invisible to every other '
        'test in this directory — an unreconciled metrics.md renders the 6-finalize '
        'row as zero and the plan-efficiency aspect reads the largest finalize phase '
        'as if it did no work.'
    )


def test_metrics_reconcile_precedes_the_aspect_that_consumes_it():
    text = _RETRO_SKILL_DOC.read_text(encoding='utf-8')
    reconcile = _reconcile_offset(text)
    consumer = _consumer_offset(text)

    assert reconcile >= 0, 'the reconcile invocation is absent — see the sibling test'
    assert consumer >= 0, (
        f'the consuming aspect key {_CONSUMING_ASPECT_KEY} is absent from '
        f'{_RETRO_SKILL_DOC}, so the ordering assertion below would be vacuous'
    )
    assert reconcile < consumer, (
        'the metrics reconcile is positioned AFTER the plan-efficiency aspect that '
        'reads metrics.md. Order is the whole contract here: the reconcile exists to '
        'close the open 6-finalize accumulator before that aspect reads the file, so '
        'a reconcile that runs later leaves the aspect reading a zero row.'
    )


def _prohibits_the_archived_write(conditions: str) -> bool:
    """Whether the region carries ONE normative prohibition on the archived write."""
    return bool(_ARCHIVED_WRITE_PROHIBITION.search(conditions))


def test_metrics_reconcile_keeps_its_live_modes_only_bound():
    conditions = _reconcile_conditions(_RETRO_SKILL_DOC.read_text(encoding='utf-8'))

    assert conditions, 'the reconcile region is empty — the invocation is absent'
    assert _prohibits_the_archived_write(conditions), (
        'the archived-mode exclusion is no longer normative. Archived mode is a '
        'read-only historic audit whose plan directory must not be written, and this '
        'step is the one that would perform that write — so the region must forbid '
        'the archived write in one statement. A descriptive mention of archived mode '
        'beside an unrelated `MUST NOT` does not forbid anything, which is exactly '
        f'what this region now reads as: {conditions!r}'
    )


def _reconcile_step(heading: str, body: str) -> str:
    """A reconcile-step fixture: ``heading``, the invocation, then ``body`` prose.

    Every arm below differs only in its heading and its conditions prose, so the
    invocation block — the literal the region is ENTERED at — is built here once.
    An arm that hand-rolled the block could drift from the anchor and then pass by
    extracting an empty region rather than by the property it names.
    """
    return (
        f'{heading}\n\n'
        '```bash\n'
        f'python3 .plan/execute-script.py {_METRICS_RECONCILE_COMMAND} \\\n'
        '  --plan-id {plan_id}\n'
        '```\n\n'
        f'{body}\n\n'
    )


def test_document_contract_detects_the_pre_fix_and_reordered_shapes():
    """Mutation guard: the three assertions above must fire on the shapes they name.

    Without this, a typo in either literal would leave all three vacuously green
    against any document — which is the exact failure mode this section exists to
    remove, reproduced one level up.
    """
    step = _reconcile_step(
        '### Step 2.5: Reconcile the phase accumulators (live modes only)',
        '**Live modes only.** Archived mode is read-only and MUST NOT write to the archived plan directory.',
    )
    aspect_table = (
        f'### Step 3: Dispatch Aspects (in order)\n\n| 4 | Plan efficiency | {_CONSUMING_ASPECT_KEY} | (LLM) | ref |\n'
    )

    # Positive control — the shipped shape clears all three checks, so none of
    # them is unconditionally negative.
    shipped = step + aspect_table
    assert _reconcile_offset(shipped) >= 0
    assert _reconcile_offset(shipped) < _consumer_offset(shipped)
    conditions = _reconcile_conditions(shipped)
    assert _prohibits_the_archived_write(conditions)

    # Pre-fix shape — the step deleted entirely. This is the mutation that used to
    # leave the whole directory green.
    deleted = aspect_table
    assert _reconcile_offset(deleted) < 0, (
        'the presence check failed to notice a document with the reconcile step '
        'removed — the exact revert it exists to catch'
    )
    assert _reconcile_conditions(deleted) == ''

    # Reordered shape — the step survives but sinks below its consumer.
    reordered = aspect_table + step
    assert _reconcile_offset(reordered) >= 0
    assert _reconcile_offset(reordered) > _consumer_offset(reordered), (
        'the ordering check failed to notice a reconcile positioned after the aspect that consumes it'
    )

    # Condition stripped — the step and its order survive, the bound does not.
    unbounded = step.replace('MUST NOT write', 'may write') + aspect_table
    assert not _prohibits_the_archived_write(_reconcile_conditions(unbounded)), (
        'the condition check reads text outside the reconcile region — a normative '
        'token from a later step would satisfy it for the wrong document'
    )

    # PERMISSIVE-ARCHIVE shape — the arm that discriminates the bound conjunction
    # from two independent substring checks. The region names archived mode AND
    # carries a `MUST NOT`, but the prohibition governs an unrelated action while the
    # archived write is expressly PERMITTED. Two separate `in` checks pass here;
    # the property they claim to test ("the archived-mode exclusion is normative")
    # is false. Without this arm nothing proves the conjunction discriminates.
    permissive_archive = _reconcile_step(
        '### Step 2.5: Reconcile the phase accumulators',
        '**All modes.** Archived mode may write the reconciled `metrics.md` back '
        'into the archived plan directory.\n'
        'The caller MUST NOT re-run invariant capture.',
    )
    permissive_conditions = _reconcile_conditions(permissive_archive + aspect_table)

    # Fixture sanity — the arm must be exactly the shape the independent checks
    # passed, or it discriminates nothing.
    assert 'archived' in permissive_conditions.lower(), (
        'Fixture sanity: the permissive-archive arm must NAME archived mode'
    )
    assert 'MUST NOT' in permissive_conditions, (
        'Fixture sanity: the permissive-archive arm must carry a `MUST NOT`, or the '
        'two independent substring checks would already have rejected it and the arm '
        'would prove nothing'
    )

    assert not _prohibits_the_archived_write(permissive_conditions), (
        'the archived-write bound fired on a region that PERMITS the archived write '
        'and forbids something else entirely — the prohibition is not bound to the '
        'write, so the check is weaker than the property its failure message names'
    )

    # PERMISSIVE-WRITE shape — the same archetype one level in, and the arm that
    # discriminates "the archived directory is the write's TARGET" from "archived is
    # a noun that co-occurs with the write inside one sentence". This region chains
    # `MUST NOT` → `write` → `archived` in a single sentence — so the pre-fix pattern
    # admits it — while EXPRESSLY PERMITTING the archived write; the prohibition it
    # carries governs the execution summary instead.
    permissive_write = _reconcile_step(
        '### Step 2.5: Reconcile the phase accumulators',
        'Archived mode may write to the archived plan directory, but the caller '
        'MUST NOT write the execution summary after archived sync',
    )
    permissive_write_conditions = _reconcile_conditions(permissive_write + aspect_table)

    # Fixture sanity — the arm must be the shape the loosened pattern accepted, or
    # it discriminates nothing.
    assert 'archived' in permissive_write_conditions.lower(), (
        'Fixture sanity: the permissive-write arm must NAME archived mode'
    )
    assert 'MUST NOT' in permissive_write_conditions, 'Fixture sanity: the permissive-write arm must carry a `MUST NOT`'
    assert _PRE_FIX_ARCHIVED_WRITE_PROHIBITION.search(permissive_write_conditions), (
        'Fixture sanity: the permissive-write arm must be ADMITTED by the pre-fix '
        'pattern. This is the discriminator — without it the arm could go green '
        'because the fixture drifted into some shape the tightened pattern was never '
        'going to match, proving nothing about the loosening that was closed'
    )

    assert not _prohibits_the_archived_write(permissive_write_conditions), (
        'the archived-write bound fired on a region whose sentence chains MUST NOT, '
        'write and archived while EXPRESSLY PERMITTING the archived write — the '
        "archived directory is a co-occurring noun there, not the write's target, "
        'so the check is still weaker than the property its failure message names'
    )

    # PERMISSIVE-DESTINATION shape — the same archetype ONE NOUN further in, and the
    # arm that discriminates "the target is the archived plan DIRECTORY" from "the
    # target is any archived-named thing". This region satisfies the destination
    # preposition — `MUST NOT` → `write` → `to` → `archived` — but the thing forbidden
    # is the archived HANDSHAKES LEDGER, while the archived plan directory write the
    # bound exists to forbid is expressly PERMITTED in the same sentence.
    #
    # A preposition-only pattern admits this. Verified by probe before the fix, which
    # is how the hole was found rather than reasoned about.
    permissive_destination = _reconcile_step(
        '### Step 2.5: Reconcile the phase accumulators',
        'Archived mode may write the reconciled metrics back into the archived plan '
        'directory, but the caller MUST NOT write to the archived handshakes ledger',
    )
    permissive_destination_conditions = _reconcile_conditions(permissive_destination + aspect_table)

    # Fixture sanity — the arm must be the shape the preposition-only pattern
    # accepted. `_PRE_FIX_ARCHIVED_WRITE_PROHIBITION` is the TWO-ALTERNATIVE oracle
    # and is too weak to discriminate here, so the admission half is asserted against
    # the preposition-only form explicitly: without it this arm could go green because
    # the fixture drifted into a shape no pattern was ever going to match.
    _PREPOSITION_ONLY = re.compile(
        r'\bMUST NOT\b[^.]{0,160}?\bwrite\b[^.]{0,40}?\b(?:to|into)\b[^.]{0,40}?\barchived\b',
        re.IGNORECASE,
    )
    assert _PREPOSITION_ONLY.search(permissive_destination_conditions), (
        'Fixture sanity: the permissive-destination arm must be ADMITTED by the '
        'preposition-only pattern. That is the discriminator — it proves the arm '
        'exercises the target-noun gap rather than passing for an unrelated reason'
    )
    assert 'archived plan directory' in permissive_destination_conditions.lower(), (
        'Fixture sanity: the arm must NAME the archived plan directory, so its '
        'rejection is attributable to the write TARGET rather than to the phrase '
        'being absent altogether'
    )

    assert not _prohibits_the_archived_write(permissive_destination_conditions), (
        'the archived-write bound fired on a region that forbids writing to the '
        'archived handshakes ledger while EXPRESSLY PERMITTING the write to the '
        'archived plan directory — binding the preposition to the bare adjective '
        '`archived` makes any archived-named destination satisfy a prohibition that '
        'is supposed to govern the archived plan directory specifically'
    )

    # WIDENED NEXT-STEP HEADING shapes — the region must stop at any level-3 ATX
    # heading CommonMark admits, not only at an unindented marker followed by
    # exactly one space. In each arm the reconcile step carries NO prohibition and
    # a LATER step does; a terminator that fails to recognise the heading lets the
    # later step's prohibition satisfy the bound for a step that has none.
    #
    # The `condition stripped` arm above is silent on this dimension — its fixture's
    # heading is unindented — which is why these arms exist as a separate battery.
    reconcile_without_bound = _reconcile_step(
        '### Step 2.5: Reconcile the phase accumulators',
        'Reconcile the open phase accumulators before the aspect reads the file.',
    )
    later_step_body = (
        'Re-read `handshakes.toon` rather than re-capturing it.\n\n'
        '**Live modes only.** Archived mode is read-only and MUST NOT write to the '
        'archived plan directory.\n\n'
    )
    for label, heading in (
        ('two-space indent', '  ### Step 2.6: Summarize invariants'),
        ('three-space indent', '   ### Step 2.6: Summarize invariants'),
        ('tab after the marker', '###\tStep 2.6: Summarize invariants'),
        ('bare marker at end of line', '###'),
    ):
        widened = reconcile_without_bound + heading + '\n\n' + later_step_body + aspect_table

        # Fixture sanity (the discriminator) — under the PRE-FIX literal terminator
        # this same fixture overruns the heading and reaches the later step's
        # prohibition. Without this half, an arm could pass merely because its
        # fixture carries no prohibition anywhere and would prove nothing about the
        # heading form it names.
        assert _prohibits_the_archived_write(_pre_fix_reconcile_conditions(widened)), (
            f'Fixture sanity ({label}): the pre-fix literal terminator must OVERRUN '
            "this heading and reach the later step's prohibition, or the arm does "
            'not exercise the gap it claims to'
        )

        assert not _prohibits_the_archived_write(_reconcile_conditions(widened)), (
            f'the region ran past a level-3 heading with a {label} — an archived-write '
            'prohibition belonging to a LATER step satisfied the bound for a reconcile '
            'step that carries none, which is the region reading text it does not own'
        )

    # FOUR-SPACE INDENT — the arm that bounds the indent dimension from ABOVE. The
    # four arms above are all ADMIT arms, so they pin ` {0,3}` only from below:
    # widening it to ` {0,4}` or ` *` leaves every one of them green, leaves the
    # level-4 subsection arm green, and leaves the live-document assertion green
    # (the shipped SKILL.md carries no indented ATX heading, so the widening is
    # unobservable there). The docstring states the CommonMark rule the pattern
    # implements — up to three leading spaces — and without this arm the stated rule
    # and the enforced rule can diverge in silence.
    #
    # Four spaces is an indented code block in CommonMark, not a heading, so it must
    # NOT terminate the region: the reconcile step's own prohibition lies beneath it
    # and must still be reached. This is the same control the sibling fix for finding
    # 85a302 adopted in test_finalize_step_sync_baseline.py for the identical
    # archetype; this occurrence is the unclosed half of that class.
    code_block_marker = _reconcile_step(
        '### Step 2.5: Reconcile the phase accumulators',
        '    ### not a heading — four spaces makes this an indented code block\n\n'
        '**Live modes only.** Archived mode is read-only and MUST NOT write to the '
        'archived plan directory.',
    )
    assert _prohibits_the_archived_write(_reconcile_conditions(code_block_marker + aspect_table)), (
        "a four-space-indented `###` line terminated the region, so the step's OWN "
        'bound was cut out of it. Four spaces is an indented code block in CommonMark, '
        'not an ATX heading — a terminator that treats it as one has widened past the '
        'rule its own docstring states, and every ADMIT arm above stays green while it '
        'does so'
    )

    # A level-4 heading is NOT a terminator: it is a subsection of the step being
    # read, so the region must still reach the step's own prohibition beneath it.
    subsection = _reconcile_step(
        '### Step 2.5: Reconcile the phase accumulators',
        '#### Mode bound\n\n'
        '**Live modes only.** Archived mode is read-only and MUST NOT write to the '
        'archived plan directory.',
    )
    assert _prohibits_the_archived_write(_reconcile_conditions(subsection + aspect_table)), (
        "a `####` subsection heading terminated the region, so the step's OWN bound "
        'was cut out of it — the terminator widened past level-3 headings into the '
        'deeper ones that belong to the step being read'
    )
