# SPDX-License-Identifier: FSL-1.1-ALv2
"""``check-dispatch-audit`` publishes how much its own verdicts are worth.

Two qualifiers used to live only in ``standards/execution-context-dispatch-audit.md``
— which means they bound an LLM that had loaded that standard and reached no other
consumer of the fragment:

* ``dispatch_coverage.ran_inline`` is a CEILING on inline execution, because a
  dispatched step whose ``<usage>`` tag was captured as zero lands in the same
  bucket as a genuinely inline one.
* A clean ``shape_violation`` can be CANCELLED: a ``[DISPATCH]`` line written by a
  caller that resolved nothing for the role is counted on Surface A exactly like a
  seam-emitted one, so the role's delta reads ``0`` and the missing seam emission
  disappears into it.

Both are now derived from figures the script already computes and emitted beside
the verdict. Each is asserted as a MATCHED PAIR — the qualifier's weak value on a
fixture that produces the weakening condition, and its strong value on one that
does not — so neither assertion can pass against a field hardcoded to a constant.
The pairs are built so the two fixtures agree on every OTHER published figure
(``violations: 0`` on both shape pairs; the same single terminal step on both
coverage pairs), which is what makes the qualifier the only thing that moved.
"""

from __future__ import annotations

import json
from pathlib import Path

from toon_parser import serialize_toon

from conftest import MARKETPLACE_ROOT, run_script

SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-dispatch-audit.py'
)

_TS = '2026-04-17T11:00:00Z'
_FINALIZE_CALLER = 'plan-marshall:phase-6-finalize'
_SEAM_CALLER = 'plan-marshall:manage-config'


def _dispatch_line(role: str, *, caller: str = _FINALIZE_CALLER) -> str:
    return (
        f'[{_TS}] [INFO] [aaaaaa] [DISPATCH] ({caller}) '
        f'target=execution-context-level-3 level=level-3 role={role} '
        f'workflow=plan-marshall:demo/SKILL.md plan_id=demo'
    )


def _resolve_line(role: str, *, caller: str = _SEAM_CALLER) -> str:
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
) -> str:
    """Stage a live plan dir carrying only the surfaces the audit reads."""
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


def _rows(block: dict, key: str) -> list[dict]:
    """Return a TOON row list, tolerating the single-row dict collapse."""
    value = block.get(key) or []
    if isinstance(value, dict):
        return [value]
    return [row for row in value if isinstance(row, dict)]


# =============================================================================
# shape_violation — is a clean verdict corroborated, or merely cancelled?
# =============================================================================


def _shape_with_foreign_line(tmp_path, monkeypatch) -> dict:
    """One resolve, no seam line, one line from a caller that resolved nothing."""
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='claim-shape-foreign',
        work_lines=[_dispatch_line('automatic-review', caller='hand-written:by-agent')],
        decision_lines=[_resolve_line('automatic-review')],
    )
    return _run(plan_id)['shape_violation']


def _shape_seam_only(tmp_path, monkeypatch) -> dict:
    """The matched control: the SAME counts, emitted by the resolving caller."""
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='claim-shape-seam',
        work_lines=[_dispatch_line('automatic-review', caller=_SEAM_CALLER)],
        decision_lines=[_resolve_line('automatic-review')],
    )
    return _run(plan_id)['shape_violation']


def test_a_cancelled_clean_verdict_reports_uncorroborated(tmp_path, monkeypatch):
    """The hand-written line cancels the missing emission — and the payload says so.

    ``violations`` is ``0`` and the role's ``delta`` is ``0``, exactly as on the
    control below. Before the qualifier was emitted, that was the whole of what a
    consumer saw, and the two states were byte-identical unless it had loaded the
    standard and gone looking at ``by_role[].foreign_caller_lines`` itself.
    """
    shape = _shape_with_foreign_line(tmp_path, monkeypatch)

    assert shape['status'] == 'evaluated'
    assert int(shape['violations']) == 0, 'precondition: the verdict must read CLEAN'
    assert shape['corroboration'] == 'uncorroborated'
    assert int(shape['foreign_caller_line_total']) == 1


def test_a_seam_emitted_clean_verdict_reports_seam_corroborated(tmp_path, monkeypatch):
    """The matched control. Same counts, same clean verdict, opposite qualifier.

    Without this arm the assertion above would be equally satisfied by a field
    hardcoded to ``uncorroborated``, which asserts nothing about the derivation.
    """
    shape = _shape_seam_only(tmp_path, monkeypatch)

    assert shape['status'] == 'evaluated'
    assert int(shape['violations']) == 0
    assert shape['corroboration'] == 'seam_corroborated'
    assert int(shape['foreign_caller_line_total']) == 0


def test_the_two_shape_fixtures_differ_only_in_the_qualifier(tmp_path, monkeypatch):
    """⛔ The pair is discriminating: everything else a consumer reads agrees.

    Stated as its own assertion rather than left implicit across the two cases
    above, because it is the property that makes them a matched pair at all. If a
    later edit made the fixtures diverge on ``violations`` or on the per-role
    delta, each arm would still pass while the pair stopped proving that the
    qualifier is what moved.
    """
    cancelled = _shape_with_foreign_line(tmp_path, monkeypatch)
    corroborated = _shape_seam_only(tmp_path, monkeypatch)

    for block in (cancelled, corroborated):
        assert int(block['violations']) == 0
        assert int(block['evaluated_population']) == 1
        rows = {row['role']: row for row in _rows(block, 'by_role')}
        assert int(rows['automatic-review']['delta']) == 0

    assert cancelled['corroboration'] != corroborated['corroboration']


def test_foreign_caller_line_total_is_the_sum_of_the_per_role_figures(tmp_path, monkeypatch):
    """The block-level total is DERIVED from the rows, not counted a second way.

    Two roles each contribute a foreign line, so a total that mirrored a single
    row — or that recounted the dispatch lines from scratch — reads differently
    from the sum this asserts against.
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='claim-shape-total',
        work_lines=[
            _dispatch_line('automatic-review', caller='hand-written:by-agent'),
            _dispatch_line('ci-verify', caller='hand-written:by-agent'),
        ],
        decision_lines=[_resolve_line('automatic-review'), _resolve_line('ci-verify')],
    )
    shape = _run(plan_id)['shape_violation']

    rows = _rows(shape, 'by_role')
    assert rows, 'precondition: the per-role breakdown must be populated'
    assert int(shape['foreign_caller_line_total']) == sum(int(row['foreign_caller_lines']) for row in rows)
    assert int(shape['foreign_caller_line_total']) == 2
    assert shape['corroboration'] == 'uncorroborated'


def test_an_unevaluated_shape_block_omits_the_total_and_says_not_evaluated(tmp_path, monkeypatch):
    """⛔ Nothing was walked, so no total is published — not a total of zero.

    Surface B is empty, so the block evaluates no role and attributes no dispatch
    line to a caller. A ``foreign_caller_line_total: 0`` here would be the very
    defect this aspect exists to remove: a figure taken over nothing, wearing the
    same face as one taken over a clean population. The fixture carries a
    ``[DISPATCH]`` line precisely so a zero could not be read as "there were no
    lines to attribute".
    """
    plan_id = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id='claim-shape-unevaluated',
        work_lines=[_dispatch_line('automatic-review', caller='hand-written:by-agent')],
        decision_lines=[],
    )
    shape = _run(plan_id)['shape_violation']

    assert shape['status'] == 'not_evaluated'
    assert shape['corroboration'] == 'not_evaluated'
    assert 'foreign_caller_line_total' not in shape, (
        'a zero total over an unevaluated population is indistinguishable from a '
        'zero over a clean one — the key must be absent, not sent as 0'
    )


# =============================================================================
# dispatch_coverage — what is the ran_inline count worth?
# =============================================================================


def _coverage_for_token_record(tmp_path, monkeypatch, *, plan_id: str, total_tokens: int) -> dict:
    """One terminal finalize step whose token row carries ``total_tokens``."""
    resolved = _write_plan(
        tmp_path,
        monkeypatch,
        plan_id=plan_id,
        work_lines=[_dispatch_line('leaf')],
        execution_log=[
            {'step_id': 'push', 'phase': '6-finalize', 'outcome': 'done', 'total_tokens': total_tokens},
        ],
        phase_steps={'push': {'outcome': 'done'}},
    )
    return _run(resolved)['dispatch_coverage']


def test_a_populated_ran_inline_bucket_is_published_as_a_ceiling(tmp_path, monkeypatch):
    """A measured zero fills the bucket, and the payload states what it is worth.

    ``ceiling`` is the honest reading: the step may have run inline, or it may
    have dispatched with a ``<usage>`` tag captured as zero. The count alone
    cannot tell those apart, and a consumer reading it as "one step ran inline"
    over-claims by exactly the size of that second population.
    """
    coverage = _coverage_for_token_record(tmp_path, monkeypatch, plan_id='claim-inline-ceiling', total_tokens=0)

    assert int(coverage['ran_inline']) == 1, 'precondition: the bucket must be populated'
    assert coverage['ran_inline_claim_strength'] == 'ceiling'


def test_an_empty_ran_inline_bucket_claims_nothing(tmp_path, monkeypatch):
    """The matched control. Same single step, a dispatched token record instead.

    The bucket is empty, so there is no ceiling to quote — and a consumer reading
    ``ran_inline: 0`` as "nothing ran inline" would be over-claiming in the other
    direction, since an inline step whose caller measured nothing lands in
    ``no_evidence``. ``no_claim`` is what the count supports.

    Without this arm the assertion above would be equally satisfied by a field
    hardcoded to ``ceiling``.
    """
    coverage = _coverage_for_token_record(tmp_path, monkeypatch, plan_id='claim-inline-no-claim', total_tokens=7000)

    assert int(coverage['ran_inline']) == 0, 'precondition: the bucket must be empty'
    assert int(coverage['evaluated_population']) == 1, (
        'precondition: the population must match the ceiling fixture, so the '
        'qualifier is the only figure that moved between the two arms'
    )
    assert coverage['ran_inline_claim_strength'] == 'no_claim'


def test_the_two_coverage_fixtures_disagree_on_the_qualifier(tmp_path, monkeypatch):
    """⛔ The pair is discriminating: the qualifier tracks the bucket, not the plan."""
    ceiling = _coverage_for_token_record(tmp_path, monkeypatch, plan_id='claim-inline-pair-a', total_tokens=0)
    no_claim = _coverage_for_token_record(tmp_path, monkeypatch, plan_id='claim-inline-pair-b', total_tokens=7000)

    assert int(ceiling['evaluated_population']) == int(no_claim['evaluated_population'])
    assert ceiling['ran_inline_claim_strength'] != no_claim['ran_inline_claim_strength']
