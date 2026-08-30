# SPDX-License-Identifier: FSL-1.1-ALv2
"""The measurement contract of ``check-dispatch-audit`` — a zero must name its population.

Every guard here pins a state the predecessor rendered as the SAME bytes as a
healthy one. The shared shape of the defects: a value that was never measured
was coerced into a measured one, and the coercion happened where the reader
stops — the classification bucket, the summary count, the confidence grade.

Scope split from ``test_check_dispatch_audit.py``: that module exercises each
detector against a divergent and a clean site (can it fire at all?). This one
asks the narrower question the detectors were corrected for — *when it reports a
zero, does the output say what the zero was measured over?* — and covers the
axes no fixture there reaches: the token-record three-state boundary, all four
confidence grades, the finalize-vs-all-caller scope divergence, the signed
per-role delta, and the ``(role, workflow)`` dispatch dedup.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from toon_parser import serialize_toon  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'check-dispatch-audit.py'
)

_TS = '2026-04-17T11:00:00Z'

_FINALIZE_CALLER = 'plan-marshall:phase-6-finalize'

# Every ``confidence = '<name>'`` assignment in the script, matched with an
# UNBOUNDED name group. The group is deliberately not an alternation over the
# grades below: a pattern that can only match names already known cannot report
# a grade that is not among them, which is the whole failure this guard exists
# to catch.
_CONFIDENCE_ASSIGNMENT_RE = re.compile(r"confidence = '([a-z_]+)'")

# The grades THIS module stages a fixture for. A literal is correct here because
# the literal IS the assertion — this is the module's own coverage claim, and
# deriving it from the script would make the comparison below `script == script`.
_COVERED_GRADES = {'not_evaluated', 'none', 'low', 'nominal'}


def _dispatch_line(
    role: str,
    *,
    caller: str = _FINALIZE_CALLER,
    workflow: str = 'plan-marshall:demo/SKILL.md',
) -> str:
    return (
        f'[{_TS}] [INFO] [aaaaaa] [DISPATCH] ({caller}) '
        f'target=execution-context-level-3 level=level-3 role={role} '
        f'workflow={workflow} plan_id=demo'
    )


def _step_completed_line(step: str) -> str:
    return (
        f'[{_TS}] [INFO] [bbbbbb] [STEP] (plan-marshall:phase-6-finalize) '
        f'Completed step: {step} (outcome=done)'
    )


def _resolve_line(role: str, *, caller: str = 'plan-marshall:manage-config') -> str:
    return (
        f'[{_TS}] [INFO] [cccccc] ({caller}) '
        f'effort resolve-target role={role} -> target=execution-context-level-3 level=level-3'
    )


def _write_plan(
    tmp_path: Path,
    monkeypatch,
    *,
    plan_id: str,
    work_lines: list[str] | None = None,
    decision_lines: list[str] | None = None,
    execution_log: list[dict] | None = None,
    phase_steps: dict | None = None,
    status_json: str | None = None,
    write_status: bool = True,
) -> str:
    """Stage a live plan dir carrying only the surfaces the audit reads.

    ``write_status=False`` omits ``status.json`` entirely and ``status_json``
    writes a raw body — both needed because the coverage block's population
    status now distinguishes *absent*, *unreadable* and *read-but-empty*, and a
    helper that could only produce a well-formed file could not reach two of the
    three.
    """
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

    if write_status:
        if status_json is not None:
            (plan_dir / 'status.json').write_text(status_json, encoding='utf-8')
        else:
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


def _rows(block: dict, key: str) -> list[dict]:
    """Return a TOON row list, tolerating the single-row dict collapse."""
    value = block.get(key) or []
    if isinstance(value, dict):
        return [value]
    return [row for row in value if isinstance(row, dict)]


# =============================================================================
# The token record: three states, and an absence is never a measured zero
# =============================================================================


def test_row_without_a_total_tokens_column_is_no_evidence_not_ran_inline(
    tmp_path, monkeypatch
):
    """A row carrying no ``total_tokens`` column at all classifies ``no_evidence``.

    This is the load-bearing half of the token-record fix. The predecessor
    coerced an absent column to ``0`` BEFORE the classifier saw it, so the step
    landed in ``ran_inline`` — the bucket the module docstring and the shipped
    standard both present as evidence the step ran inline. An absent column is
    the absence of a measurement, and it must be reported as one.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='token-absent-column',
        execution_log=[
            {'step_id': 'push', 'phase': '6-finalize', 'outcome': 'done'},
            {'step_id': 'create-pr', 'phase': '6-finalize', 'outcome': 'done'},
        ],
        phase_steps={'push': {'outcome': 'done'}, 'create-pr': {'outcome': 'done'}},
    )
    coverage = _run(plan_id)['dispatch_coverage']

    assert int(coverage['no_evidence']) == 2, (
        'a finalize row with no total_tokens column carries no measurement, so it '
        f'must classify no_evidence; got no_evidence={coverage["no_evidence"]!r} '
        f'ran_inline={coverage["ran_inline"]!r}'
    )
    assert int(coverage['ran_inline']) == 0
    assert sorted(coverage['no_evidence_steps']) == ['create-pr', 'push']


def test_explicit_zero_total_tokens_still_classifies_ran_inline(tmp_path, monkeypatch):
    """The matched negative control — an EXPLICIT ``0`` is still a measurement.

    Without this the fix above would be indistinguishable from "route every zero
    to no_evidence", which would re-classify every currently-clean plan and start
    reporting ``missing_dispatch_emission`` against runs that are fine. The rule
    is bounded to rows that genuinely carry no reading.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='token-explicit-zero',
        execution_log=[
            {'step_id': 'push', 'phase': '6-finalize', 'outcome': 'done',
             'total_tokens': 0},
        ],
        phase_steps={'push': {'outcome': 'done'}},
    )
    coverage = _run(plan_id)['dispatch_coverage']

    assert int(coverage['ran_inline']) == 1
    assert int(coverage['no_evidence']) == 0


def test_unreadable_total_tokens_value_is_no_evidence(tmp_path, monkeypatch):
    """A present-but-unreadable value is an absence too, not a zero.

    ``'n/a'`` is recorded and cannot be read as a token count. The predecessor's
    ``else: value = 0`` swallowed it into the same bucket as a real inline step.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='token-unreadable',
        execution_log=[
            {'step_id': 'push', 'phase': '6-finalize', 'outcome': 'done',
             'total_tokens': 'n/a'},
        ],
        phase_steps={'push': {'outcome': 'done'}},
    )
    coverage = _run(plan_id)['dispatch_coverage']

    assert int(coverage['no_evidence']) == 1
    assert int(coverage['ran_inline']) == 0


def test_a_recorded_measurement_outranks_its_absence_on_a_refire(tmp_path, monkeypatch):
    """Two rows for one step: the RECORDED value wins over the unreadable one.

    A re-fire appends a second row, and the second is not automatically the
    better record. Reducing on ``max`` alone cannot express this once the value
    may be ``None``, so the reduction is explicit — and a step proven to have
    dispatched must not be demoted to ``no_evidence`` by a later blank row.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='token-refire',
        execution_log=[
            {'step_id': 'push', 'phase': '6-finalize', 'outcome': 'done',
             'total_tokens': 8000},
            {'step_id': 'push', 'phase': '6-finalize', 'outcome': 'done'},
        ],
        phase_steps={'push': {'outcome': 'done'}},
    )
    coverage = _run(plan_id)['dispatch_coverage']

    assert int(coverage['dispatched']) == 1
    assert int(coverage['no_evidence']) == 0
    assert list(coverage['dispatched_steps']) == ['push']


# =============================================================================
# The coverage population: absent / unreadable status.json is not an empty phase
# =============================================================================


def test_absent_status_json_reports_not_evaluated_with_a_reason(tmp_path, monkeypatch):
    plan_id = _write_plan(
        tmp_path, monkeypatch, plan_id='status-absent', write_status=False
    )
    coverage = _run(plan_id)['dispatch_coverage']

    assert coverage['status'] == 'not_evaluated'
    assert 'status.json' in coverage['reason']


def test_unparseable_status_json_reports_not_evaluated_with_a_reason(
    tmp_path, monkeypatch
):
    plan_id = _write_plan(
        tmp_path, monkeypatch, plan_id='status-broken', status_json='{not json'
    )
    coverage = _run(plan_id)['dispatch_coverage']

    assert coverage['status'] == 'not_evaluated'
    assert 'status.json' in coverage['reason']


def test_valid_status_json_with_empty_finalize_map_is_a_measured_zero(
    tmp_path, monkeypatch
):
    """The discriminator: an EMPTY finalize map was read, so its zero is measured.

    ⛔ This is the control that makes the two assertions above mean something. An
    absent status.json and a valid one carrying an empty ``6-finalize`` map both
    produced ``evaluated_population: 0`` and were byte-identical in the output;
    they are opposite statements about whether anything was read.
    """
    plan_id = _write_plan(
        tmp_path, monkeypatch, plan_id='status-empty-finalize', phase_steps={}
    )
    coverage = _run(plan_id)['dispatch_coverage']

    assert coverage['status'] == 'evaluated'
    assert int(coverage['evaluated_population']) == 0
    assert 'reason' not in coverage


# =============================================================================
# All four confidence grades — the population the grade was taken over
# =============================================================================


def test_confidence_not_evaluated_when_every_input_is_empty(tmp_path, monkeypatch):
    """The fourth grade. A log-less plan graded ``nominal`` before it existed."""
    plan_id = _write_plan(
        tmp_path, monkeypatch, plan_id='grade-not-evaluated', write_status=False
    )
    channel = _run(plan_id)['channel_completeness']

    assert channel['confidence'] == 'not_evaluated'
    assert channel['reason']
    # Pins the fixture as the ALL-ZERO one, so the guard below — same three
    # finalize inputs, non-zero all-caller total — is a genuinely different state
    # and not a restatement of this one.
    assert int(channel['all_caller_dispatch_line_count']) == 0


def test_phase_5_dispatch_lines_do_not_rescue_an_empty_finalize_evaluation(
    tmp_path, monkeypatch
):
    """⛔ The killing fixture: all-caller > 0 with every FINALIZE input at zero.

    This is the state the fourth grade exists for, and the state a fourth
    predicate term — ``and all_caller_dispatch_line_count == 0`` — silently
    excluded from it. ``all_caller`` is taken over a SUPERSET of the population
    the other three are taken over, so ANDing it on could only ever narrow the
    guard, never widen it.

    Walk the fall-through the extra term opened: the guard misses because
    all-caller is 2; ``none`` needs a completion or a proven dispatch and has
    neither; both ``low`` branches need a proven dispatch or a ratio, and
    ``dispatched_step_count`` is 0 with ``ratio`` ``None``. Execution reaches the
    ``else`` and grades ``nominal`` — an evaluated-clean verdict over an entirely
    empty finalize evaluation.

    The matched negative control is
    ``test_confidence_none_when_finalize_lines_absent_despite_a_proven_dispatch``:
    same non-zero all-caller total, but ONE token-proven finalize dispatch, and
    the grade must move off ``not_evaluated``. Without it this guard would be
    equally satisfied by a predicate that graded ``not_evaluated`` unconditionally.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='grade-not-evaluated-despite-phase-5-lines',
        work_lines=[
            _dispatch_line('phase-5-execute', caller='plan-marshall:phase-5-execute'),
            _dispatch_line(
                'verification-feedback', caller='plan-marshall:phase-5-execute'
            ),
        ],
        phase_steps={},
    )
    channel = _run(plan_id)['channel_completeness']

    # The divergence that makes this fixture the one the defect needed.
    assert int(channel['all_caller_dispatch_line_count']) == 2
    assert int(channel['dispatch_line_count']) == 0
    assert int(channel['completion_count']) == 0
    assert int(channel['dispatched_step_count']) == 0
    # ``ratio`` is None by construction here (no completions to divide by), which
    # is why neither ``low`` branch can fire — asserted through its input rather
    # than through the serialized null it renders as.

    assert channel['confidence'] == 'not_evaluated', (
        'every finalize-scoped input is zero, so nothing about the finalize '
        'channel was evaluated; a non-zero all-caller total is a REPORTED figure '
        'over a superset population and must not be a term in the guard — with it '
        f'this fixture falls through to `nominal`. Got {channel["confidence"]!r}'
    )
    assert channel['reason']


def test_confidence_none_when_finalize_lines_absent_despite_a_proven_dispatch(
    tmp_path, monkeypatch
):
    """Zero FINALIZE dispatch lines beside a token-proven dispatched step ⇒ ``none``.

    ⛔ The fixture's phase-5 lines are what make this a real test of the SCOPE
    fix: the all-caller total is 3, so a grade computed from it reads the channel
    as populated and lands on ``nominal``. The finalize-scoped count is 0, which
    is the figure the other two members of this block are taken over. A
    single-phase fixture cannot distinguish the two and would pass either way.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='grade-none-scope-divergent',
        work_lines=[
            _dispatch_line('phase-5-execute', caller='plan-marshall:phase-5-execute'),
            _dispatch_line(
                'phase-5-execute',
                caller='plan-marshall:phase-5-execute',
                workflow='plan-marshall:other/SKILL.md',
            ),
            _dispatch_line(
                'verification-feedback', caller='plan-marshall:phase-5-execute'
            ),
        ],
        execution_log=[
            {'step_id': 'automatic-review', 'phase': '6-finalize', 'outcome': 'done',
             'total_tokens': 84000},
        ],
        phase_steps={'automatic-review': {'outcome': 'done'}},
    )
    data = _run(plan_id)
    channel = data['channel_completeness']

    assert int(channel['all_caller_dispatch_line_count']) == 3
    assert int(channel['dispatch_line_count']) == 0
    # The two figures genuinely differ on this fixture, which is what makes the
    # next assertion a test of WHICH one the grade follows.
    assert channel['dispatch_line_count'] != channel['all_caller_dispatch_line_count']
    assert channel['confidence'] == 'none', (
        'the grade must follow the finalize-scoped count (0), not the all-caller '
        f'total (3); got {channel["confidence"]!r}'
    )
    assert int(data['dispatch_coverage']['missing_dispatch_emission']) == 1


def test_confidence_low_when_lines_fall_short_of_proven_dispatches(
    tmp_path, monkeypatch
):
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='grade-low',
        work_lines=[
            _dispatch_line('finalize-step-simplify'),
            _step_completed_line('finalize-step-simplify'),
            _step_completed_line('finalize-step-security-audit'),
        ],
        execution_log=[
            {'step_id': 'finalize-step-simplify', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 5000},
            {'step_id': 'finalize-step-security-audit', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 3000},
        ],
        phase_steps={
            'finalize-step-simplify': {'outcome': 'done'},
            'finalize-step-security-audit': {'outcome': 'done'},
        },
    )
    channel = _run(plan_id)['channel_completeness']

    assert channel['confidence'] == 'low'
    assert int(channel['dispatch_line_count']) == 1
    assert int(channel['dispatched_step_count']) == 2


def test_confidence_nominal_when_the_channel_is_covered(tmp_path, monkeypatch):
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='grade-nominal',
        work_lines=[
            _dispatch_line('finalize-step-simplify'),
            _step_completed_line('finalize-step-simplify'),
        ],
        execution_log=[
            {'step_id': 'finalize-step-simplify', 'phase': '6-finalize',
             'outcome': 'done', 'total_tokens': 5000},
        ],
        phase_steps={'finalize-step-simplify': {'outcome': 'done'}},
    )
    channel = _run(plan_id)['channel_completeness']

    assert channel['confidence'] == 'nominal'
    assert 'reason' not in channel


def test_the_confidence_grades_the_script_emits_are_the_ones_declared_covered():
    """Population guard: the grades the script ASSIGNS equal the declared covered set.

    The emitted side is DERIVED — an unbounded scan of the script for every
    ``confidence = '<name>'`` assignment. The predecessor built it as a
    comprehension over the literal covered set, which made it a subset of that
    set by construction: a fifth grade in the script was invisible to it, and a
    renamed grade read as a plain deletion. Scanning for whatever the script
    actually assigns is what makes BOTH a new grade and a renamed one fail here.

    What this proves is the vocabulary agreement only. It does NOT read the
    fixtures above and so does not establish that each declared grade is
    actually exercised by one; ``_COVERED_GRADES`` is a maintained declaration,
    not a measurement of this module.
    """
    source = SCRIPT_PATH.read_text(encoding='utf-8')
    emitted = set(_CONFIDENCE_ASSIGNMENT_RE.findall(source))

    assert emitted, (
        'no `confidence = ...` assignment matched in check-dispatch-audit.py, so '
        'the population this guard compares against is EMPTY and the comparison '
        'below would prove nothing — the scan, not the script, is what broke'
    )
    assert emitted == _COVERED_GRADES, (
        'check-dispatch-audit no longer emits exactly the grades this module '
        f'declares it covers; emitted={sorted(emitted)}, '
        f'covered={sorted(_COVERED_GRADES)}'
    )


# =============================================================================
# The signed per-role breakdown, and the caller-blindness it makes legible
# =============================================================================


def test_per_role_breakdown_publishes_a_signed_delta(tmp_path, monkeypatch):
    """A SURPLUS of dispatch lines is a fact with a negative delta, not a finding.

    The predecessor discarded every non-positive difference, so a role with more
    ``[DISPATCH]`` lines than resolves contributed nothing at all to the output.
    Reporting it as a violation would fail plans for a legitimate hand-written
    emission; discarding it hid the only signal that the two surfaces disagree.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='role-signed-delta',
        work_lines=[
            _dispatch_line('automatic-review'),
            _dispatch_line('automatic-review', workflow='plan-marshall:second/SKILL.md'),
        ],
        decision_lines=[_resolve_line('automatic-review')],
    )
    shape = _run(plan_id)['shape_violation']

    rows = {row['role']: row for row in _rows(shape, 'by_role')}
    assert 'automatic-review' in rows
    row = rows['automatic-review']
    assert int(row['resolves']) == 1
    assert int(row['dispatch_lines']) == 2
    assert int(row['delta']) == -1, 'the delta must be SIGNED, not clamped at zero'
    # A surplus is reported, never raised.
    assert int(shape['violations']) == 0


def test_a_hand_written_dispatch_line_reports_a_non_zero_signal(tmp_path, monkeypatch):
    """One resolve, no seam line, one FOREIGN-caller line ⇒ the cancellation is visible.

    ⛔ This is the caller-blindness case. The pairing compares counts, so the
    hand-written line cancels the missing seam emission exactly: ``delta`` is
    ``0`` and ``violations`` is ``0``, and the output looked like a corroborated
    clean verdict. ``foreign_caller_lines`` is the discriminator — a line for a
    role whose caller resolved nothing for it.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='role-foreign-caller',
        work_lines=[_dispatch_line('automatic-review', caller='hand-written:by-agent')],
        decision_lines=[_resolve_line('automatic-review')],
    )
    shape = _run(plan_id)['shape_violation']

    rows = {row['role']: row for row in _rows(shape, 'by_role')}
    row = rows['automatic-review']
    assert int(row['delta']) == 0
    assert int(shape['violations']) == 0
    assert int(row['foreign_caller_lines']) == 1, (
        'a [DISPATCH] line whose caller resolved nothing for the role must surface '
        'as a non-zero signal; without it a cancelled pairing reads as clean'
    )


def test_a_dispatch_only_role_is_published_in_the_by_role_breakdown(tmp_path, monkeypatch):
    """A role on the DISPATCH side alone must still get a ``by_role`` row.

    ⛔ This is the surplus direction of the role union, and it is load-bearing
    rather than cosmetic. ``standards/execution-context-dispatch-audit.md``
    instructs the reader to consult ``by_role[].foreign_caller_lines`` before
    calling a ``violations: 0`` result clean — and for a role that appears ONLY on
    the dispatch side there is no row at all to consult, so the documented reading
    is unusable for exactly the case the union was added to expose.

    The fixture is that case, not an approximation of it: ``violations`` is ``0``
    (the one resolved role is matched by its own seam-emitted line), so the summary
    reads clean, and the ONLY signal that a hand-written ``[DISPATCH]`` line was
    emitted for a role the resolve seam never resolved is this row. Restricting the
    walk to the resolve side deletes the row and the report becomes clean with
    nothing left to disagree with it.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='role-dispatch-only',
        work_lines=[
            _dispatch_line('automatic-review', caller='plan-marshall:manage-config'),
            _dispatch_line('hand-rolled-role', caller='hand-written:by-agent'),
        ],
        decision_lines=[_resolve_line('automatic-review')],
    )
    shape = _run(plan_id)['shape_violation']

    assert shape['status'] == 'evaluated', 'precondition: Surface B must be non-empty'
    assert int(shape['violations']) == 0, (
        'precondition: the summary must read CLEAN, so the by_role row is the only '
        'thing standing between the reader and an uncorroborated clean verdict'
    )

    rows = {row['role']: row for row in _rows(shape, 'by_role')}
    assert 'hand-rolled-role' in rows, (
        'a role carrying a [DISPATCH] line and no resolve record must still appear '
        'in by_role; without the row the documented interpretation rule — consult '
        'foreign_caller_lines before calling violations:0 clean — has nothing to read'
    )
    row = rows['hand-rolled-role']
    assert int(row['resolves']) == 0
    assert int(row['dispatch_lines']) == 1
    assert int(row['delta']) == -1
    assert int(row['foreign_caller_lines']) == 1


def test_the_dispatch_only_row_appears_only_because_its_line_does(tmp_path, monkeypatch):
    """The matched negative control for the guard above.

    The SAME ``decision.log`` and the SAME seam-emitted pair, with the one
    hand-written ``[DISPATCH]`` line removed — and no row for that role appears.
    Without this control the assertion above would be equally satisfied by a
    breakdown that manufactured a row for every name it ever saw, and the reader's
    check would be reading noise rather than evidence.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='role-dispatch-only-control',
        work_lines=[
            _dispatch_line('automatic-review', caller='plan-marshall:manage-config'),
        ],
        decision_lines=[_resolve_line('automatic-review')],
    )
    shape = _run(plan_id)['shape_violation']

    rows = {row['role']: row for row in _rows(shape, 'by_role')}
    assert 'hand-rolled-role' not in rows
    assert 'automatic-review' in rows, 'the resolve side is published either way'
    assert int(shape['violations']) == 0
    assert int(rows['automatic-review']['foreign_caller_lines']) == 0


def test_a_seam_emitted_pair_reports_no_foreign_caller_line(tmp_path, monkeypatch):
    """The matched negative control for the guard above.

    Same counts, same delta of ``0``, same ``violations: 0`` — and
    ``foreign_caller_lines: 0``, because the line came from the caller that
    resolved the role. Without this control the new field would fire on every
    healthy pairing and prove nothing.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='role-seam-pair',
        work_lines=[_dispatch_line('automatic-review', caller='plan-marshall:manage-config')],
        decision_lines=[_resolve_line('automatic-review')],
    )
    shape = _run(plan_id)['shape_violation']

    rows = {row['role']: row for row in _rows(shape, 'by_role')}
    row = rows['automatic-review']
    assert int(row['delta']) == 0
    assert int(row['foreign_caller_lines']) == 0


# =============================================================================
# Finalize dispatch dedup by (role, workflow)
# =============================================================================


def test_refired_dispatch_lines_dedup_by_role_and_workflow(tmp_path, monkeypatch):
    """A re-fire of ONE step must not inflate the dispatch-line side.

    Two identical finalize ``[DISPATCH]`` lines are one step's dispatch emitted
    twice. Counting them as two lines masks a genuine
    ``missing_dispatch_emission`` — the comparison is *steps proven dispatched*
    against *emissions for them*.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='dedup-refire',
        work_lines=[
            _dispatch_line('automatic-review'),
            _dispatch_line('automatic-review'),
        ],
        execution_log=[
            {'step_id': 'automatic-review', 'phase': '6-finalize', 'outcome': 'done',
             'total_tokens': 84000},
            {'step_id': 'create-pr', 'phase': '6-finalize', 'outcome': 'done',
             'total_tokens': 12000},
        ],
        phase_steps={
            'automatic-review': {'outcome': 'done'},
            'create-pr': {'outcome': 'done'},
        },
    )
    data = _run(plan_id)

    assert int(data['channel_completeness']['dispatch_line_count']) == 1, (
        'two identical (role, workflow) finalize lines are one distinct emission'
    )
    assert int(data['channel_completeness']['all_caller_dispatch_line_count']) == 2
    assert int(data['dispatch_coverage']['missing_dispatch_emission']) == 1, (
        'with 2 steps proven dispatched and 1 distinct emission, exactly 1 is missing'
    )


def test_two_steps_sharing_a_role_are_two_distinct_emissions(tmp_path, monkeypatch):
    """⛔ The over-correction control: dedup on the PAIR, never on the role alone.

    Two different finalize steps can resolve the same role. Collapsing by role
    would fold their two real emissions into one and manufacture a
    ``missing_dispatch_emission`` that is not there — the opposite error from the
    one the dedup exists to prevent, and equally silent.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='dedup-shared-role',
        work_lines=[
            _dispatch_line('leaf', workflow='plan-marshall:automatic-review/SKILL.md'),
            _dispatch_line('leaf', workflow='plan-marshall:create-pr/SKILL.md'),
        ],
        execution_log=[
            {'step_id': 'automatic-review', 'phase': '6-finalize', 'outcome': 'done',
             'total_tokens': 84000},
            {'step_id': 'create-pr', 'phase': '6-finalize', 'outcome': 'done',
             'total_tokens': 12000},
        ],
        phase_steps={
            'automatic-review': {'outcome': 'done'},
            'create-pr': {'outcome': 'done'},
        },
    )
    data = _run(plan_id)

    assert int(data['channel_completeness']['dispatch_line_count']) == 2
    assert int(data['dispatch_coverage']['missing_dispatch_emission']) == 0


# =============================================================================
# The list-returning checks publish their population
# =============================================================================


def test_list_checks_distinguish_an_empty_log_from_a_populated_clean_one(
    tmp_path, monkeypatch
):
    """A run over no work log and a run over a clean one must differ visibly.

    Both report zero violations — correctly. The predecessor surfaced ONLY that
    zero, so the two were byte-identical and a reader could not tell "nothing was
    scanned" from "everything scanned was fine".
    """
    empty_id = _write_plan(tmp_path, monkeypatch, plan_id='lists-empty', work_lines=[])
    empty = _run(empty_id)

    clean_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='lists-clean',
        work_lines=[
            _dispatch_line('automatic-review'),
            _step_completed_line('automatic-review'),
        ],
    )
    clean = _run(clean_id)

    for name in ('envelope_violation', 'generic_subagent_violation'):
        assert int(empty[name]['violations']) == 0
        assert int(clean[name]['violations']) == 0
        assert empty[name]['status'] == 'not_evaluated'
        assert clean[name]['status'] == 'evaluated'
        assert int(empty[name]['evaluated_population']) == 0
        assert int(clean[name]['evaluated_population']) > 0, (
            f'{name} must publish the population it scanned, or its zero is '
            'indistinguishable from a zero over nothing'
        )
