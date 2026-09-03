#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the notation cross-check on ``pre-commit-verify-freshness``."""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest
from _freshness_notation_crosscheck_fixtures import (
    _CURRENT_SHA,
    _NPM,
    _OTHER_SHA,
    _PYPROJECT,
    _args_for,
    _build_entry,
    _build_is_necessary,
    _FakeQueryModule,
    _freshness_mod,
    _outcome_for,
    _required,
    _run,
    _stub_expected,
    _stub_required,
    _write_ledger,
    _write_status,
    cmd_pre_commit_verify_freshness,
)

from conftest import PROJECT_ROOT


@pytest.fixture(autouse=True)
def _stub_resolver_seam(monkeypatch):
    """Keep worktree-root resolution hermetic (no ``manage-status`` subprocess)."""
    monkeypatch.setattr(
        file_ops, '_query_worktree_path', lambda _plan_id: (True, str(Path.cwd()))
    )


# =============================================================================
# The record names its evidence
# =============================================================================


def test_fresh_record_names_the_matched_row(plan_context, monkeypatch, tmp_path) -> None:
    """Every field a reader needs to find the satisfying row is in the record."""
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [
            _build_entry(worktree_sha=_OTHER_SHA),
            _build_entry(status='error'),
            _build_entry(notation=_PYPROJECT, plan_id='some-other-plan', timestamp_iso='2026-06-11T13:00:00Z'),
        ],
        'crosscheck-audit',
    )

    assert result['status'] == 'fresh', result
    assert result['matched_notation'] == _PYPROJECT
    assert result['matched_entry_index'] == 2
    assert result['matched_plan_id'] == 'some-other-plan'
    assert result['timestamp_iso'] == '2026-06-11T13:00:00Z'
    assert result['expected_notations'] == [_PYPROJECT]


def test_matched_index_addresses_the_parsed_row_not_the_file_line(
    plan_context, monkeypatch, tmp_path
) -> None:
    """``matched_entry_index`` indexes PARSED entries, which malformed lines shift.

    ``read_entries`` skips unparseable lines, so the parsed index and the
    physical line number diverge on a corrupted ledger. The parsed index is the
    one that addresses the row the gate actually read.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    plan_dir = plan_context.plan_dir_for('crosscheck-malformed')
    _write_status(plan_dir)
    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', lambda _root: _CURRENT_SHA)
    ledger_path = tmp_path / 'change-ledger.jsonl'
    ledger_path.write_text(
        'not json at all\n' + json.dumps(_build_entry(), sort_keys=True) + '\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='crosscheck-malformed'))

    assert result['status'] == 'fresh', result
    # Physical line 2, parsed entry 0 — the malformed line is not an entry.
    assert result['matched_entry_index'] == 0


# =============================================================================
# The structural-stale case must remain stale
# =============================================================================


def test_mutated_worktree_stays_stale_with_its_own_reason(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A tree mutated after its build is still ``worktree_mutated``, not a notation refusal.

    This verdict is structural and CORRECT: the chain verifies and stamps, a
    later commit changes the tree, the gate compares and reports stale. The
    cross-check must not reach it at all — there is no candidate to check — and
    must not relabel it, or the next reader silences a true positive along with
    the false ones.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(worktree_sha=_OTHER_SHA)],
        'crosscheck-mutated',
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_mutated'
    assert 'notation_cross_check' not in result


def test_failed_build_for_current_sha_keeps_its_build_status_reason(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A red build against the current tree still reports ``build_error``.

    The cross-check runs only on rows that already passed ``status == 'success'``,
    so a failing build's own remedy sentence is never displaced by a notation
    message.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(status='error')],
        'crosscheck-error',
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == 'build_error'
    assert 'notation_cross_check' not in result


# =============================================================================
# resolve_expected_notations — the three outcomes, directly
# =============================================================================


def test_resolver_reports_a_non_empty_set_with_no_reason(monkeypatch) -> None:
    """A resolver that finds notations returns them with ``reason is None``."""
    monkeypatch.setitem(
        __import__('sys').modules,
        '_cmd_client_query',
        _FakeQueryModule(frozenset({_PYPROJECT})),
    )
    notations, reason = crosscheck.resolve_expected_notations('.')

    assert notations == frozenset({_PYPROJECT})
    assert reason is None


def test_resolver_reports_an_unimportable_resolver_apart_from_a_failing_one(monkeypatch) -> None:
    """An unimportable resolver gets its OWN reason, not the running-failure one.

    Both pass the gate — neither is a refutation — so the distinction buys
    nothing at the gate and everything to a reader asking why the cross-check
    never corroborates anything. An unimportable resolver means THIS CHECK IS
    BROKEN and will report ``unverified`` on every row forever; an un-crawled
    project is a legitimate quiet pass.
    """
    import builtins

    real_import = builtins.__import__

    def _refuse_query_module(name, *args, **kwargs):
        if name == '_cmd_client_query':
            raise ImportError('no module named _cmd_client_query')
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(__import__('sys').modules, '_cmd_client_query', raising=False)
    monkeypatch.setattr(builtins, '__import__', _refuse_query_module)

    notations, reason = crosscheck.resolve_expected_notations('.')

    assert notations == frozenset()
    assert reason == crosscheck.REASON_RESOLVER_UNIMPORTABLE
    assert reason != crosscheck.REASON_RESOLUTION_FAILED


def test_resolver_reports_an_empty_set_as_an_inability(monkeypatch) -> None:
    """An empty resolution is 'I do not know', carrying its own reason.

    It is NOT returned as a refutation-grade answer: an un-crawled project
    resolves nothing, and treating that as 'this project builds with nothing'
    would refuse every real build row it holds.
    """
    monkeypatch.setitem(
        __import__('sys').modules, '_cmd_client_query', _FakeQueryModule(frozenset())
    )
    notations, reason = crosscheck.resolve_expected_notations('.')

    assert notations == frozenset()
    assert reason == crosscheck.REASON_NO_NOTATIONS_RESOLVED


def test_resolver_reports_a_raising_crawl_as_an_inability(monkeypatch) -> None:
    """A resolver that raises is an inability, never a refutation."""
    monkeypatch.setitem(
        __import__('sys').modules, '_cmd_client_query', _FakeQueryModule(RuntimeError('crawl blew up'))
    )
    notations, reason = crosscheck.resolve_expected_notations('.')

    assert notations == frozenset()
    assert reason == crosscheck.REASON_RESOLUTION_FAILED


# =============================================================================
# cross_check_candidates preconditions
# =============================================================================


def test_an_empty_candidate_list_is_a_precondition_violation() -> None:
    """Zero candidates has no honest verdict, so it fails fast rather than guessing.

    Both answers the code could otherwise reach are wrong: ``refuted`` would
    assert "no row carries a notation" about zero rows, and ``unverified`` would
    hand the caller a ``chosen`` position addressing nothing. The caller routes
    the no-candidate case to ``stale`` before reaching here, so arriving with an
    empty list is a programming error and is reported as one.
    """
    with pytest.raises(ValueError, match='at least one candidate'):
        crosscheck.cross_check_candidates([], '.')


def test_the_chosen_position_indexes_the_list_it_was_given(monkeypatch) -> None:
    """``chosen`` is a position, not the row object — the caller maps it back itself.

    Returning the dict instead would force the caller to recover the row's ledger
    index by ``id()``, which is sound only while this function returns one of the
    very objects it was handed — not a property its signature promises.

    The resolver is pinned so a failure here is attributable to the position
    contract and not to the live architecture; the real path has its own case.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    outcome = crosscheck.cross_check_candidates(
        [_build_entry(notation=_NPM), _build_entry(notation=_PYPROJECT)],
        '/nonexistent-project-dir',
    )
    assert outcome['chosen'] == 1
    assert 'entry' not in outcome


# =============================================================================
# Positive control: the WHOLE real path, no seam stubbed
# =============================================================================


def test_the_real_resolution_path_refuses_and_corroborates_against_this_repository(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Anti-vacuity for every case above: the unstubbed check still discriminates.

    Every other gate case here pins ``resolve_expected_notations``. If the real
    resolver could not be imported at runtime, or resolved nothing against a real
    tree, the cross-check would collapse to a permanent ``unverified`` pass — and
    all of those cases would stay green, because none of them uses it. This one
    drives the gate with NO seam stubbed but the ledger and the sha, so an import
    path or a crawl that stopped working is a test failure rather than a silent
    no-op.

    Both directions are asserted in one case on purpose: a refusal alone would
    also be produced by a resolver that resolves the empty set and (wrongly)
    treated it as a refutation, so the corroboration is what proves the set was
    really populated.
    """
    monkeypatch.setattr(
        file_ops, '_query_worktree_path', lambda _plan_id: (True, str(PROJECT_ROOT))
    )
    plan_dir = plan_context.plan_dir_for('crosscheck-live')
    _write_status(plan_dir)
    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', lambda _root: _CURRENT_SHA)

    unrelated = _write_ledger(tmp_path, [_build_entry(notation=_NPM)])
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: unrelated)
    refused = cmd_pre_commit_verify_freshness(Namespace(plan_id='crosscheck-live'))

    related = tmp_path / 'related.jsonl'
    related.write_text(
        json.dumps(_build_entry(notation=_PYPROJECT), sort_keys=True) + '\n', encoding='utf-8'
    )
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: related)
    permitted = cmd_pre_commit_verify_freshness(Namespace(plan_id='crosscheck-live'))

    assert refused['status'] == 'stale', refused
    assert refused['reason'] == crosscheck.REASON_NOTATION_UNRELATED
    assert permitted['status'] == 'fresh', permitted
    assert permitted['notation_cross_check'] == crosscheck.CORROBORATED
    assert _PYPROJECT in permitted['expected_notations']


# =============================================================================
# The scope cross-check — the observed 858061bc false-green, and its control
# =============================================================================
#
# Every case in this section is a PAIR or is half of one, deliberately. The
# notation cross-check above was shipped one-directional once already, and this
# epic has repeatedly turned a false green into a false red; a scope check that
# refuses everything is exactly as wrong as one that accepts everything. So each
# refusal below is stated against a matched row that must still pass.


def test_the_observed_three_row_ledger_no_longer_certifies_a_whole_tree_change(
    plan_context, monkeypatch, tmp_path
) -> None:
    """The 858061bc state: three rows for one tree, and the narrowest one passed.

    Reproduces the observed ledger exactly — a whole-tree ``module-tests`` that
    TIMED OUT, a module-scoped ``module-tests`` that FAILED, and a
    single-directory 573-test run that SUCCEEDED. Only the third clears the
    primary predicate, and before the scope dimension the gate cited it as
    ``corroborated`` evidence for a whole-tree change: every ``pyproject_build``
    invocation carries the identical notation, so the attribution dimension
    cannot tell 573 tests in one directory from a whole-tree ``verify``.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    _stub_required(monkeypatch, _required())
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [
            _build_entry(status='timeout', args=_args_for('module-tests')),
            _build_entry(status='error', args=_args_for('module-tests plan-marshall')),
            _build_entry(
                args=_args_for('module-tests plan-marshall/manage-findings'),
                outcome=_outcome_for(573),
            ),
        ],
        'scope-observed-state',
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_SCOPE_NARROW
    assert result['scope_cross_check'] == crosscheck.NARROW
    # The refusal names WHAT the row ran, not merely that something was narrow.
    assert result['row_scopes'] == ['module-tests plan-marshall/manage-findings: '
                                    + crosscheck.ROW_CANONICAL_TOO_WEAK]


def test_a_whole_tree_verify_row_still_certifies_the_same_change(
    plan_context, monkeypatch, tmp_path
) -> None:
    """MATCHED POSITIVE CONTROL for the case above — load-bearing, not optional.

    Same sha, same requirement, same ledger shape; only the surviving row's
    canonical and scope differ. Without this the refusal above is satisfied by a
    gate that refuses every row, which is the inverse defect.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    _stub_required(monkeypatch, _required())
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [
            _build_entry(status='timeout', args=_args_for('module-tests')),
            _build_entry(status='error', args=_args_for('module-tests plan-marshall')),
            _build_entry(args=_args_for('verify'), outcome=_outcome_for(19007)),
        ],
        'scope-adequate-control',
    )

    assert result['status'] == 'fresh', result
    assert result['scope_cross_check'] == crosscheck.COVERED
    assert result['notation_cross_check'] == crosscheck.CORROBORATED
    assert result['matched_entry_index'] == 2
    # A pass on evidence audited on BOTH dimensions carries neither reason field.
    assert 'scope_cross_check_reason' not in result
    assert 'notation_cross_check_reason' not in result


def test_a_module_scoped_verify_covers_its_own_module_but_not_a_tree_wide_change(
    monkeypatch,
) -> None:
    """The scope half, as a matched pair over ONE row and two requirements.

    Holding the row fixed and varying only what the change needs is what isolates
    the scope dimension from the canonical one: the same ``verify plan-marshall``
    row is adequate for a change confined to ``plan-marshall`` and inadequate for
    one whose blast radius is the whole tree.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    row = _build_entry(args=_args_for('verify plan-marshall'), outcome=_outcome_for(19007))

    confined = crosscheck.cross_check_candidates(
        [row], '/nonexistent-project-dir', _required(whole_tree=False, modules={'plan-marshall'})
    )
    tree_wide = crosscheck.cross_check_candidates(
        [row], '/nonexistent-project-dir', _required(whole_tree=True)
    )

    assert confined['scope_verdict'] == crosscheck.COVERED, confined
    assert confined['chosen'] == 0
    assert tree_wide['scope_verdict'] == crosscheck.NARROW, tree_wide
    assert tree_wide['chosen'] is None
    assert tree_wide['row_scopes'] == ['verify plan-marshall: ' + crosscheck.ROW_SCOPE_TOO_NARROW]


def test_a_module_scoped_row_does_not_cover_a_different_module(monkeypatch) -> None:
    """Scope adequacy is set containment, not "was scoped at all".

    A row scoped to some module is not evidence for a change in another one, and
    a check that only asked "does this row name a module?" would accept it.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    outcome = crosscheck.cross_check_candidates(
        [_build_entry(args=_args_for('verify pm-dev-java'), outcome=_outcome_for(400))],
        '/nonexistent-project-dir',
        _required(whole_tree=False, modules={'plan-marshall'}),
    )

    assert outcome['scope_verdict'] == crosscheck.NARROW, outcome
    assert outcome['chosen'] is None


def test_a_zero_test_compile_row_does_not_certify_a_tree_that_needs_tests(
    monkeypatch,
) -> None:
    """The canonical half: a green ``compile`` says nothing about the test dimension.

    ``compile`` performs only the translation analysis, so it cannot reach a
    change the test suite can break — and a zero-test row satisfying the gate
    exactly as a full ``verify`` would is the second half of the observed defect.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    outcome = crosscheck.cross_check_candidates(
        [_build_entry(args=_args_for('compile'), outcome=_outcome_for(0))],
        '/nonexistent-project-dir',
        _required(),
    )

    assert outcome['scope_verdict'] == crosscheck.NARROW, outcome
    assert outcome['row_scopes'] == ['compile: ' + crosscheck.ROW_CANONICAL_TOO_WEAK]


def test_a_measured_zero_test_run_is_refused_but_an_unmeasured_one_is_not(
    monkeypatch,
) -> None:
    """A MEASURED zero refutes; an unknown count does not — the pair proves it.

    Both rows are whole-tree ``verify`` and differ only in their wrapper payload.
    Reading an absent or unparseable test summary as zero would refuse a
    legitimate run for having an unreadable payload, which is the false-red this
    asymmetry exists to avoid.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    measured_zero = crosscheck.cross_check_candidates(
        [_build_entry(args=_args_for('verify'), outcome=_outcome_for(0))],
        '/nonexistent-project-dir',
        _required(),
    )
    unmeasured = crosscheck.cross_check_candidates(
        [_build_entry(args=_args_for('verify'), outcome=_outcome_for(None, population='unknown'))],
        '/nonexistent-project-dir',
        _required(),
    )

    assert measured_zero['scope_verdict'] == crosscheck.NARROW, measured_zero
    assert measured_zero['row_scopes'] == ['verify: ' + crosscheck.ROW_TESTS_EXECUTED_ZERO]
    assert unmeasured['scope_verdict'] == crosscheck.COVERED, unmeasured


def test_selection_is_joint_so_an_attributable_narrow_row_is_never_cited(
    monkeypatch,
) -> None:
    """Neither dimension refuses, yet nothing is citable — the disjoint case.

    Per-dimension selection is the actual mechanism behind the observed
    false-green: the narrow row was attributable, and nothing asked whether it
    covered the change. Here the attributable row is narrow and the covering row
    is unattributable, so both dimensions find SOMETHING acceptable while no
    single row is acceptable to both. That state carries its own reason rather
    than borrowing either dimension's.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    outcome = crosscheck.cross_check_candidates(
        [
            _build_entry(notation=_PYPROJECT, args=_args_for('compile')),
            _build_entry(notation=_NPM, args=_args_for('verify'), outcome=_outcome_for(500)),
        ],
        '/nonexistent-project-dir',
        _required(),
    )

    assert outcome['verdict'] == crosscheck.CORROBORATED, outcome
    assert outcome['scope_verdict'] == crosscheck.COVERED, outcome
    assert outcome['chosen'] is None
    assert outcome['joint_reason'] == crosscheck.REASON_NO_ADMISSIBLE_ROW


def test_the_notation_property_survives_the_scope_widening(monkeypatch) -> None:
    """The pre-existing guarantee still holds after the second dimension lands.

    A row naming a build this project never runs cannot prove freshness, no
    matter how adequate its recorded canonical and scope are. Widening a gate is
    the classic moment for an older guarantee to be lost, so it is re-asserted
    here against a row that is deliberately perfect on the NEW dimension.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    outcome = crosscheck.cross_check_candidates(
        [_build_entry(notation=_NPM, args=_args_for('verify'), outcome=_outcome_for(19007))],
        '/nonexistent-project-dir',
        _required(),
    )

    assert outcome['verdict'] == crosscheck.REFUTED, outcome
    assert outcome['scope_verdict'] == crosscheck.COVERED
    assert outcome['chosen'] is None
    assert outcome['joint_reason'] == crosscheck.REASON_NOTATION_UNRELATED


# =============================================================================
# Every scope inability passes, and says which one it was
# =============================================================================


def test_an_unreadable_row_scope_passes_and_names_the_inability(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A row whose ``args`` carries no ``--command-args`` is undetermined, not narrow.

    ⛔ The fail direction here is the whole point: an unreadable row must NOT be
    read as whole-tree (which would manufacture the false-green) and must NOT be
    read as narrow (which would refuse every pre-existing ledger row). It is an
    absence of knowledge, so it passes with the inability recorded.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    _stub_required(monkeypatch, _required())
    result = _run(
        plan_context, monkeypatch, tmp_path, [_build_entry(args='run')], 'scope-unreadable'
    )

    assert result['status'] == 'fresh', result
    assert result['scope_cross_check'] == crosscheck.UNDETERMINED
    assert result['scope_cross_check_reason'] == crosscheck.REASON_SCOPE_UNREADABLE


def test_an_underivable_requirement_passes_and_names_the_inability(
    plan_context, monkeypatch, tmp_path
) -> None:
    """An unresolvable footprint is an inability, never an empty requirement.

    Rendering it as "the change requires nothing" would make every row cover it
    — re-opening the exact false-green this dimension closes — so the consumer
    returns ``None`` and the check reports ``undetermined`` instead.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    _stub_required(monkeypatch, None, reason=crosscheck.REASON_REQUIRED_COVERAGE_UNKNOWN)
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(args=_args_for('compile'))],
        'scope-underivable',
    )

    assert result['status'] == 'fresh', result
    assert result['scope_cross_check'] == crosscheck.UNDETERMINED
    assert result['scope_cross_check_reason'] == crosscheck.REASON_REQUIRED_COVERAGE_UNKNOWN


def test_a_canonical_outside_the_vocabulary_is_undetermined_not_refuted(
    monkeypatch,
) -> None:
    """``CANONICAL_ANALYSES`` is PARTIAL by design, so a miss means unknown.

    ``clean`` and friends are deliberately unmapped because no analysis set
    honestly describes them. Treating an unmapped canonical as "performs nothing"
    would convert that documented partiality into a refusal.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    outcome = crosscheck.cross_check_candidates(
        [_build_entry(args=_args_for('clean'))], '/nonexistent-project-dir', _required()
    )

    assert outcome['scope_verdict'] == crosscheck.UNDETERMINED, outcome
    assert outcome['scope_reason'] == crosscheck.REASON_SCOPE_UNREADABLE
    assert outcome['chosen'] == 0


# =============================================================================
# The two pure derivations the dimension rests on
# =============================================================================


@pytest.mark.parametrize(
    ('args', 'expected'),
    [
        ('run', None),
        ('run --plan-id p', None),
        ('run --command-args', None),
        ('run --command-args --timeout 900', None),
        ('run --command-args verify', ('verify', ())),
        ('run --command-args verify --timeout 900', ('verify', ())),
        ('run --command-args=verify', ('verify', ())),
        ('run --command-args verify plan-marshall', ('verify', ('plan-marshall',))),
        ('run --command-args=verify plan-marshall', ('verify', ('plan-marshall',))),
    ],
)
def test_parse_row_scope_never_reads_an_unreadable_row_as_whole_tree(args, expected) -> None:
    """``None`` and an empty scope tuple are different answers, never interchangeable.

    An empty ``scope_tokens`` ASSERTS whole-tree — the widest coverage claim
    available — so every shape that carries no readable ``--command-args`` must
    return ``None`` instead. Both argparse spellings are accepted because the
    ledger stamps whichever the caller used.
    """
    parsed = crosscheck.parse_row_scope(_build_entry(args=args))

    if expected is None:
        assert parsed is None
    else:
        assert parsed is not None
        assert (parsed.canonical, parsed.scope_tokens) == expected


def test_parse_row_scope_rejects_a_row_whose_args_is_not_a_string() -> None:
    """An absent or non-string ``args`` is unreadable, not an empty command line."""
    assert crosscheck.parse_row_scope({'kind': 'build'}) is None
    assert crosscheck.parse_row_scope({'kind': 'build', 'args': None}) is None
    assert crosscheck.parse_row_scope({'kind': 'build', 'args': ['run']}) is None


def test_required_coverage_is_derived_from_the_footprint_not_fixed() -> None:
    """What the change needs varies with the change — the non-inverting property.

    A gate that demanded a whole-tree ``verify`` of every footprint would be the
    mirror-image false signal, so the requirement is derived: the test dimension
    for any non-empty footprint (bundle markdown is a build input here), the
    type-check dimensions only for a source-bearing one, and nothing at all for
    an empty footprint.
    """
    vocabulary, reason = crosscheck.load_analysis_vocabulary()
    assert vocabulary is not None, reason

    empty = crosscheck.required_coverage([], (), False, vocabulary)
    docs_only = crosscheck.required_coverage(
        ['marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'],
        ('plan-marshall',),
        False,
        vocabulary,
    )
    with_source = crosscheck.required_coverage(
        ['marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/x.py'],
        ('plan-marshall',),
        True,
        vocabulary,
    )

    assert empty.analyses == frozenset()
    assert empty.whole_tree is False
    assert docs_only.analyses == frozenset({vocabulary.test})
    assert docs_only.whole_tree is False
    assert docs_only.modules == frozenset({'plan-marshall'})
    assert with_source.analyses == frozenset(
        {vocabulary.compile, vocabulary.lint, vocabulary.test}
    )
    # ``divergence_possible`` is taken verbatim — this dimension does not re-derive it.
    assert with_source.whole_tree is True
