#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the phase-4-plan mechanical Q-Gate's CLOSURE checks.

Scope: how the closure check discloses what it could not measure and bounds what it
reports — a truncated enumeration or scanned-path list disclosed rather than silent,
and a hit list that names its remainder.
"""


from __future__ import annotations

import json
from argparse import Namespace

import pytest
from _qgate_closure_fixtures import (
    _MULTI_HIT_GLOB,
    _REAL_A,
    _REAL_B,
    _closure,
    _deliverable,
    _independent_expansion,
    _task,
    _write_outline,
    _write_task_file,
    check_declared_scope_reconciliation,
    check_declared_set_closure,
    cmd_qgate_mechanical,
    compute_projection_gaps,
    compute_referrer_gaps,
    declared_paths,
    expand_declared_glob,
    extract_deliverables,
    is_glob,
    normalize_declared_path,
    parse_document_sections,
)

from conftest import PROJECT_ROOT


def test_a_directory_only_scope_is_unmeasured_not_a_clean_zero():
    """``marketplace/bundles/*/`` matches only directories, which is/was dropped.

    Every match falling to the ``is_file()`` filter left an empty file list and
    a ``population_complete: True`` — a measured-looking verdict over a scope
    that was never reconciled.
    """
    expansion = expand_declared_glob('marketplace/bundles/*/', PROJECT_ROOT)
    assert expansion.matches == []
    assert expansion.directories_matched > 0, 'precondition: the pattern must match directories'

    gaps, population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=['marketplace/bundles/*/'])], PROJECT_ROOT
    )

    assert [g['kind'] for g in gaps] == ['unexpandable_glob']
    assert population['directories_matched'] > 0
    assert population['population_complete'] is False


def test_a_declaration_normalizing_to_nothing_is_dropped():
    """``./`` is a non-empty string that normalizes to ``''``.

    Guarding the raw string let the empty path into the comparison, where it was
    reported as a gap named ``''``.
    """
    assert normalize_declared_path('./') == ''
    deliverable = _deliverable(1, survey=['./'], mutate=[_REAL_A])

    assert declared_paths(deliverable) == {_REAL_A}
    assert compute_referrer_gaps(_task(1, 1, ['./']), declared_paths(deliverable)) == []


def test_truncated_enumeration_is_disclosed_and_bounds_the_hit_list(monkeypatch):
    """A capped expansion is a LOWER BOUND, and says so.

    The match ceiling and the hit-naming cap are both lowered here rather than
    building a fixture large enough to reach the shipped values — the property
    under test is the disclosure, not the constants. The glob is asserted to
    match MORE than the lowered ceiling, so the cap is genuinely reached.
    """
    monkeypatch.setattr(_closure, '_MAX_GLOB_MATCHES', 1)
    all_hits = _independent_expansion(_MULTI_HIT_GLOB)
    assert len(all_hits) > 1, 'precondition: the glob must exceed the lowered ceiling'

    expansion = expand_declared_glob(_MULTI_HIT_GLOB, PROJECT_ROOT)
    assert expansion.truncated is True
    assert len(expansion.matches) == 1

    gaps, population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=[_MULTI_HIT_GLOB])], PROJECT_ROOT
    )
    assert population['enumeration_truncated'] is True
    assert population['population_complete'] is False
    assert 'LOWER BOUND' in gaps[0]['detail']


def test_the_hit_list_names_a_bounded_set_and_discloses_the_remainder(monkeypatch):
    """Above the naming cap the finding still states the TOTAL.

    A silent truncation would read as "these are the hits"; the ``+N more``
    summary and the unenumerated count keep the finding honest about its own
    elision.
    """
    monkeypatch.setattr(_closure, '_MAX_HITS_NAMED', 1)
    hits = _independent_expansion(_MULTI_HIT_GLOB)
    assert len(hits) > 1, 'precondition: the glob must exceed the lowered naming cap'

    gaps, _population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=[_MULTI_HIT_GLOB])], PROJECT_ROOT
    )

    assert len(gaps) == 1
    detail, title = gaps[0]['detail'], gaps[0]['title']
    assert f'+{len(hits) - 1} more' in detail
    assert f'{len(hits)} of them appear in no declared list' in detail
    # ⛔ The TITLE must state the same TOTAL, not the count it managed to name.
    # This is the only place the two diverge — below the cap they are equal, so
    # a fixture there cannot tell a total from a named count, and a mutant
    # substituting one for the other survives it.
    assert f'{len(hits)} fewer file(s)' in title
    assert f'{len(hits) - 1} fewer file(s)' not in title


def test_the_finding_names_every_hit_and_states_the_true_total():
    """The hit list and the title are pinned against a REAL multi-hit glob.

    Both other claim-vs-index tests are blind to this: one uses a glob that
    expands to a single file (a population of one cannot see a slicing bug), and
    the other lowers ``_MAX_HITS_NAMED`` by monkeypatch (which cannot see a
    hard-coded slice). Two mutants survived the whole suite because of it —
    ``unenumerated[:1]`` for the named list, and a title reporting the NAMED
    count where it claims the total.

    The title's number is the disclosure-integrity claim D2 makes about its own
    finding text, so it is asserted against an independently derived total
    rather than against the length of whatever the finding chose to name.
    """
    hits = _independent_expansion(_MULTI_HIT_GLOB)
    assert len(hits) > 2, 'precondition: more hits than a slice-of-1 mutant would name'
    assert len(hits) <= _closure._MAX_HITS_NAMED, (
        'precondition: below the naming cap, so every hit must appear un-elided'
    )

    gaps, _population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=[_MULTI_HIT_GLOB])], PROJECT_ROOT
    )

    assert len(gaps) == 1
    detail, title = gaps[0]['detail'], gaps[0]['title']
    for hit in hits:
        assert hit in detail, hit
    assert 'more, not named here' not in detail, 'below the cap nothing is elided'
    # The TOTAL, not the named count — the two coincide only below the cap, and
    # a mutant substituting one for the other is what this pins.
    assert f'{len(hits)} fewer file(s)' in title
    assert f'{len(hits)} of them appear in no declared list' in detail


def test_scanned_paths_truncation_is_disclosed_not_silent(monkeypatch):
    """The published-member cap says when it bit. (B1)

    ``scanned_paths`` is D3's own discharge mechanism: it carries the member
    identities a positive-population assertion needs. A cap applied silently
    would present a PARTIAL population as a complete one — the plan's own defect
    class, reached inside the field that exists to prevent it.

    The cap is lowered rather than building a 200-path fixture; the property
    under test is the disclosure, not the constant. The unlowered case is
    asserted alongside it, so a mutant hard-coding either verdict is caught.
    """
    deliverable = _deliverable(1, affected=[_REAL_A, _REAL_B])
    tasks = [_task(1, 1, [_REAL_A, _REAL_B])]

    _gaps, full = check_declared_set_closure(tasks, [deliverable])
    assert full['scanned_paths_truncated'] is False
    assert len(full['scanned_paths']) == 2

    monkeypatch.setattr(_closure, '_MAX_SCANNED_PATHS_PUBLISHED', 1)
    _gaps, capped = check_declared_set_closure(tasks, [deliverable])

    assert capped['scanned_paths_truncated'] is True
    assert len(capped['scanned_paths']) == 1
    # The COUNT is unaffected by the publication cap — a reader can still tell
    # how large the population was, which is what makes the cap a disclosure
    # rather than a shrunken population.
    assert capped['declared_paths_scanned'] == 2


def test_a_bracket_pattern_is_not_treated_as_a_declared_glob():
    """``[`` is deliberately outside the metacharacter set. (B5)

    A character class is legal glob syntax but vanishingly rare in a declared
    scope and common in prose, so reading a prose bracket as a pattern would
    manufacture findings. The decision is documented at
    ``_GLOB_METACHARACTERS``; this pins it, so a future widening has to change a
    test rather than only a comment.
    """
    assert is_glob('src/a[0-9].py') is False
    assert is_glob('src/*.py') is True
    assert is_glob('src/a?.py') is True

    # A bracketed path is therefore a LITERAL declaration: it takes part in the
    # projection closure (which skips patterns) rather than the reconciliation.
    deliverable = _deliverable(1, mutate=['src/a[0-9].py'])
    assert compute_projection_gaps(deliverable, [_task(1, 1, [])]) == ['src/a[0-9].py']


def test_a_holistic_task_is_exempt_and_not_counted_as_scanned():
    """``deliverable == 0`` is EXEMPT — neither unmapped nor scanned.

    ``_check_coverage`` already whitelists the sentinel ("do not flag as
    orphan"), and the closure pass must agree: a holistic task belongs to no
    deliverable, so no declared set exists to check it against, and counting it
    as unmapped would flip ``ambiguous`` on a correctly-shaped plan.

    ⛔ But exemption must not INFLATE the scanned population. An earlier version
    of this carve-out skipped the closure after the accounting had already
    counted the task's targets, so the population claimed three targets scanned
    while one entered the check — a ``population_complete: True`` over a surface
    the closure never examined, which is the defect this module reports on
    outlines. The three counts are asserted together for exactly that reason: a
    regression that re-inflates them changes numbers this test reads.
    """
    deliverables = [_deliverable(1, affected=[_REAL_A])]
    mapped = _task(1, 1, [_REAL_A])
    holistic = _task(2, 0, ['src/undeclared-a.py', 'src/undeclared-b.py'])

    gaps, population = check_declared_set_closure([mapped, holistic], deliverables)

    assert gaps == [], 'the holistic task owes no referrer closure'
    assert population['holistic_tasks'] == [2], 'the exemption is published, not silent'
    assert population['unmapped_tasks'] == []
    # Only the mapped task and its single target entered the closure.
    assert population['tasks_scanned'] == 1
    assert population['step_targets_scanned'] == 1
    assert population['population_complete'] is True


def test_ambiguous_flips_when_the_closure_population_is_incomplete(plan_context):
    """The mechanism q-gate-validation.md §2.9a names as discharging D3.

    ``population_complete: False`` MUST reach the caller as ``ambiguous``, or the
    normative line `detector_population ⊇ fix_set_population` is documentation
    with nothing behind it: the orchestrator would read a clean mechanical pass
    over a population the check could not fully scan.
    """
    plan_dir = plan_context.plan_dir_for('closure-ambiguous')
    _write_outline(
        plan_dir,
        f'### 1. One deliverable\n\n**Affected files:**\n- `{_REAL_A}` (read)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))
    # TASK-002 names deliverable 99, which the outline does not contain.
    _write_task_file(plan_dir / 'tasks', _task(2, 99, [_REAL_A]))

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-ambiguous', no_emit=True))

    assert result['population']['declared_set_closure']['population_complete'] is False
    assert result['population_complete'] is False
    assert result['ambiguous'] is True


def test_closure_check_runs_under_the_surgical_scope_bypass_shape(plan_context):
    """ADVERSARIAL: a plan shaped exactly like the Step 8b bypass is still checked.

    phase-4-plan's B2 predicate — ``scope_estimate == surgical`` AND at most two
    declared affected files — suppresses the DISPATCHED q-gate-validation. This
    fixture satisfies BOTH conjuncts, and asserts the closure check still runs
    and still fires, because it lives in Step 8, which has no bypass. A closure
    claim is a hint; it may never be a licence to skip the check that would test
    it.

    Both conjuncts are asserted as PRECONDITIONS, re-derived from the artifacts
    the fixture just wrote — the persisted ``scope_estimate`` and the declared
    cardinality the predicate actually reads. Without that, the fixture could
    drift out of the bypass shape and the test would keep passing while
    verifying nothing about the bypass at all.
    """
    plan_dir = plan_context.plan_dir_for('closure-bypass')
    (plan_dir / 'references.json').write_text(
        json.dumps({'scope_estimate': 'surgical'}), encoding='utf-8'
    )
    _write_outline(
        plan_dir,
        f'### 1. Surgical fix\n\n'
        f'**Metadata:**\n- change_type: bug_fix\n\n'
        f'**Affected files:**\n- `{_REAL_A}` (read)\n- `{_REAL_B}` (write-replace)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))

    # Precondition 1 — the persisted scope_estimate the B2 predicate reads.
    references = json.loads((plan_dir / 'references.json').read_text(encoding='utf-8'))
    assert references['scope_estimate'] == 'surgical'

    # Precondition 2 — the deduplicated declared cardinality, re-derived through
    # the SAME parser phase-4-plan uses, never by counting bullet lines.
    #
    # This fixture declares only `Affected files:`, so the flat count and the
    # widened declared-surface count B2 actually reads coincide here. They do
    # NOT coincide for a survey-scope deliverable, which is why the surface is
    # summed explicitly rather than reading `affected_files` alone: a fixture
    # that later grew a survey pair would otherwise keep asserting a number the
    # predicate no longer uses.
    outline = (plan_dir / 'solution_outline.md').read_text(encoding='utf-8')
    deliverables = extract_deliverables(parse_document_sections(outline)['deliverables'])
    affected_files_count = len(
        {
            entry['path']
            for d in deliverables
            for field in ('affected_files', 'survey_scope', 'mutation_scope')
            for entry in d[field]
        }
    )
    assert affected_files_count <= 2, 'precondition: the fixture must satisfy the bypass predicate'

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-bypass', no_emit=True))

    assert result['checks']['declared_set_closure']['failed'] == 1


@pytest.mark.parametrize(
    'bad_number',
    [
        pytest.param(None, id='none'),
        pytest.param('', id='empty-string'),
        pytest.param('holistic', id='non-numeric'),
    ],
)
def test_a_malformed_task_number_still_emits_the_referrer_finding(bad_number):
    """A task whose ``number`` is unusable must not take the whole Q-Gate down.

    The referrer finding is built from ``task['number']``, and that access sits on
    the path that REPORTS a closure gap. A raw ``int(task['number'])`` there raises
    ``KeyError`` / ``TypeError`` / ``ValueError`` on exactly the input the check
    exists to flag — so the gate would crash whenever it had a finding to emit and
    pass whenever it had none. That is a fail-open in the checks written to prevent
    fail-open, and it is why the number is read through ``_as_int`` here, as the
    holistic and unmapped accounting in the same function already does.

    Asserted positively — one referrer gap, naming the target — rather than merely
    "did not raise": a regression that swallowed the gap entirely would satisfy a
    bare no-raise assertion while losing the finding.
    """
    deliverable = _deliverable(1, affected=[_REAL_A])
    task = _task(1, 1, [_REAL_B])
    task['number'] = bad_number

    gaps, population = check_declared_set_closure([task], [deliverable])

    referrer = [g for g in gaps if g['kind'] == 'referrer']
    assert len(referrer) == 1, 'the undeclared step target is still reported'
    assert referrer[0]['file_path'] == _REAL_B
    assert 'TASK-000' in referrer[0]['title'], 'an unusable number renders as 000, not a crash'
    assert population['population_complete'] is True


def test_a_missing_task_number_key_is_tolerated_on_the_finding_path():
    """The same guard covers an ABSENT key, not only a present-but-unusable value.

    ``task.get('number')`` and ``task['number']`` fail differently — the second
    raises ``KeyError`` before any conversion happens — so the absent-key case is
    pinned separately rather than assumed to ride along with the parametrized one.
    """
    deliverable = _deliverable(1, affected=[_REAL_A])
    task = _task(1, 1, [_REAL_B])
    del task['number']

    gaps, _ = check_declared_set_closure([task], [deliverable])

    assert [g['file_path'] for g in gaps if g['kind'] == 'referrer'] == [_REAL_B]
