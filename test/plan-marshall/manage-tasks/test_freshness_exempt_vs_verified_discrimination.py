#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression: the exempt route and the verified route stay apart.

THE DEFECT. ``cmd_pre_commit_verify_freshness`` once returned ``fresh`` from two
structurally different routes — a ledger-scanned, cross-check-corroborated build,
and a ``build-decision`` ``not_necessary`` short-circuit that returns before
``resolve_plan_context``, before ``compute_worktree_sha`` and before
``read_entries``, so it examines nothing at all. Every consumer branching on the
token alone therefore admitted an unexamined tree exactly as it admitted a
verified one. The exempt route now returns its own status member, ``exempt``.

WHAT THIS MODULE IS FOR. Each sibling module pins ONE site's behaviour. None of
them fails if the two routes are collapsed back into one token, because each
exercises only one route. This module is the cross-cutting proof, and every count
it asserts on is published together with the population it was measured over — an
assertion whose population is empty passes vacuously, which is the same
absence-read-as-coverage defect one level up.

FOUR PROOFS:

1. The two routes are distinguishable **from the return alone** — not merely on
   incidental keys, but on the field a consumer branches on.
2. Every member of the branching-consumer population reads the discriminator
   rather than the bare token. The population is DERIVED from the tree by
   conjunction (references the gate AND compares against a status literal), its
   size is published, and it is reconciled against deliverable 1's recorded
   ``branches`` count — a shortfall FAILS rather than passing silently.
3. ``_build_necessity_verdict`` still degrades to ``build`` on an unobtainable
   verdict, over both degradation inputs, with the input count published.
4. The ``stale`` and ``undecidable`` reason vocabularies are unchanged, ENUMERATED
   from the shipped source and from the shipped behaviour rather than restated as
   a hand-written literal list.

⛔ **This module is excluded from its own proof-2 population.** It is the prover,
not a consumer under test, and it necessarily contains the very shapes proof 2
forbids (it has to name them to forbid them). The exclusion is by explicit path,
declared below, so it can never silently widen to cover a real consumer. The
forbidden needles are additionally assembled from parts rather than written
verbatim, so this module would pass its own rules even without the exclusion.
"""

from __future__ import annotations

import re
from argparse import Namespace
from collections import Counter
from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (
    _CURRENT_SHA,
    _REAL_BUILD_NECESSITY_VERDICT,
    _RESOLVED_NOTATIONS,
    _build_entry,
    _build_is_necessary,
    _expected_notations_resolve,
    _freshness_mod,
    _stub_expected_notations,
    _stub_ledger_path,
    _stub_verdict,
    _stub_worktree_sha,
    _write_ledger,
    _write_status,
    cmd_pre_commit_verify_freshness,
)
from _resolve_project_dir_fixtures import (
    worktree_query_result,
)

from conftest import PROJECT_ROOT

# =============================================================================
# The status vocabulary under test
# =============================================================================

#: The two members that PERMIT, on structurally different bases. A consumer that
#: branches on the absence of a refusal admits both — and every future member —
#: which is the fail-open ADR-009 forbids, so consumers branch on the member.
_PERMITTING = ('exempt', 'fresh')

#: The two members that REFUSE.
_REFUSING = ('stale', 'undecidable')

_ALL_STATUSES = _PERMITTING + _REFUSING


@pytest.fixture(autouse=True)
def _stub_resolver_seam(monkeypatch):
    """Stub the ONE resolver seam so no case shells out to ``manage-status``.

    Mirrors the sibling modules: the gate resolves its worktree root through
    ``resolve_plan_context``, whose only external touch point is
    ``file_ops._query_worktree_path``.
    """
    monkeypatch.setattr(
        file_ops,
        '_query_worktree_path',
        lambda _plan_id: worktree_query_result(True, str(Path.cwd())),
    )


# =============================================================================
# PROOF 1 — the two routes are distinguishable from the return alone
# =============================================================================


def _exempt_return(plan_context, monkeypatch, tmp_path) -> dict:
    """Drive the ``not_necessary`` short-circuit and return its verdict."""
    plan_id = 'discrimination-exempt-route'
    _write_status(plan_context.plan_dir_for(plan_id))
    _stub_verdict(
        monkeypatch,
        {'decision': 'not_necessary', 'reason': 'plan footprint touches no build_map glob'},
    )
    # Boundary values that would force `undecidable` had the scan been reached —
    # proof that the short-circuit fires ahead of them.
    _stub_worktree_sha(monkeypatch, None)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')
    verdict: dict = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))
    return verdict


def _verified_return(plan_context, monkeypatch, tmp_path) -> dict:
    """Drive the ledger-scanned route to a citable row and return its verdict."""
    plan_id = 'discrimination-verified-route'
    _write_status(plan_context.plan_dir_for(plan_id))
    _stub_verdict(monkeypatch, {'decision': 'build'})
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    _stub_expected_notations(monkeypatch, _RESOLVED_NOTATIONS)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)]))
    verdict: dict = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))
    return verdict


def test_the_two_routes_differ_on_the_field_a_consumer_branches_on(plan_context, monkeypatch, tmp_path) -> None:
    """The discriminating field is ``status`` — the one every consumer reads.

    Asserting only that the two dicts are unequal would pass on an incidental key
    (a differing ``message`` string, a ``reason`` present on one side), which is
    exactly what the collapsed contract already had and what left every consumer
    unable to tell the routes apart. The assertion is therefore on ``status``.
    """
    exempt = _exempt_return(plan_context, monkeypatch, tmp_path)
    verified = _verified_return(plan_context, monkeypatch, tmp_path)

    assert exempt['status'] == 'exempt', exempt
    assert verified['status'] == 'fresh', verified


def test_both_permitting_members_are_reachable_and_are_the_only_ones(plan_context, monkeypatch, tmp_path) -> None:
    """Non-vacuity: both permitting members are REACHED, not merely declared.

    A proof that the two differ says nothing if one of them can never be produced.
    Driving each route and collecting what it returned establishes the permitting
    set by exercise; the set is then reconciled against the declared one, so a
    member that stopped being reachable fails here rather than quietly shrinking
    the vocabulary this module reasons about.
    """
    observed = {
        _exempt_return(plan_context, monkeypatch, tmp_path)['status'],
        _verified_return(plan_context, monkeypatch, tmp_path)['status'],
    }

    assert observed == set(_PERMITTING), (
        f'exercised {len(observed)} permitting status(es) {sorted(observed)} against a '
        f'declared permitting set of {len(_PERMITTING)} {sorted(_PERMITTING)}'
    )


def test_the_exempt_return_carries_no_evidence_it_never_gathered(plan_context, monkeypatch, tmp_path) -> None:
    """The exempt route omits every key the ledger scan would have produced.

    The absence is the record: it returns before the sha is computed and before a
    row is read, so publishing a ``worktree_sha`` or a ``matched_*`` field there
    would assert evidence that was never gathered. The verified return is the
    matched control — it MUST carry them, or this absence proves nothing about
    the route and only that the fields are unused.
    """
    exempt = _exempt_return(plan_context, monkeypatch, tmp_path)
    verified = _verified_return(plan_context, monkeypatch, tmp_path)

    evidence_keys = ('worktree_sha', 'matched_notation', 'matched_entry_index', 'ledger_path')
    absent = [key for key in evidence_keys if key not in exempt]
    present = [key for key in evidence_keys if key in verified]

    assert absent == list(evidence_keys), (
        f'the exempt return carried {len(evidence_keys) - len(absent)} of '
        f'{len(evidence_keys)} ledger-evidence keys it never gathered: '
        f'{[k for k in evidence_keys if k in exempt]}'
    )
    assert present == list(evidence_keys), (
        f'the verified return carried only {len(present)} of {len(evidence_keys)} '
        f'evidence keys, so the exempt absence above is not discriminating'
    )
    # The forwarded reason is the authority's own text, verbatim.
    assert exempt['reason'] == 'plan footprint touches no build_map glob', exempt


# =============================================================================
# PROOF 2 — every branching consumer reads the discriminator
# =============================================================================

#: Deliverable 1's recorded partition: `branches` = 10, `describes` = 23, summing
#: to the 33-member surveyed population. Only the branches count bears here.
_D1_PUBLISHED_BRANCHES_COUNT = 10

#: The two workflow documents in that class. A document "branches" by carrying a
#: normative instruction that selects behaviour on the status VALUE.
_DOC_BRANCHING_CONSUMERS = (
    'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md',
    'marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md',
)

#: The eight code members of the class, declared by the SLICE that owns each one
#: rather than by filename, so the DERIVED set below has something to be reconciled
#: against without this module pinning another slice's file names. The derivation is
#: what makes the check population-derived; this per-slice census is what makes a
#: drift legible — a consumer appearing in a new slice, or leaving one, moves a
#: count here, while a rename inside a slice moves nothing. A filename list would
#: instead red this module for a rename that has nothing to do with the gate.
_CODE_CONSUMER_SLICES = {
    'test/plan-marshall/manage-tasks': 6,
    'test/plan-marshall/manage-execution-manifest': 1,
    'test/plan-marshall/tools-script-executor': 1,
}

#: This module — the prover, excluded from its own population by explicit path.
_SELF = 'test/plan-marshall/manage-tasks/test_freshness_exempt_vs_verified_discrimination.py'

#: The trees the derivation walks. Both spellings of the gate identifier are
#: searched, because the dash form names the subcommand and the underscore form
#: names the module, and a consumer may reference either.
_DERIVATION_ROOTS = (
    'marketplace/bundles/plan-marshall',
    'test/plan-marshall',
)
_GATE_REFERENCES = ('pre-commit-verify-freshness', 'pre_commit_verify_freshness')

#: A comparison against a status literal. The conjunction with a gate reference is
#: what keeps unrelated ``fresh`` vocabularies out — the merge lock's holder
#: staleness, the executor's ``marshal_status``, the steward's cache freshness all
#: compare against ``'fresh'`` and none of them names this gate.
_STATUS_COMPARISON = re.compile(r"""(?:==|!=|\bin\b)\s*[\(\{\[]?\s*['"](?:exempt|fresh|stale|undecidable)['"]""")

#: Assembled from parts rather than written verbatim so this module satisfies the
#: rules it enforces, independently of the self-exclusion above.
_FORBIDDEN_BARE_REFUSAL = '!=' + " 'fresh'"
_FORBIDDEN_STALE_VOCABULARY = "('fresh', " + "'stale', " + "'undecidable')"

#: The POSITIVE form of the same comparison, which is what identifies the
#: verified-route control by its behaviour instead of by its file name.
_VERIFIED_ROUTE_PASS_PREDICATE = '==' + " 'fresh'"


def _read(rel_path: str) -> str:
    """Read a repository-relative file as text."""
    text: str = (PROJECT_ROOT / rel_path).read_text(encoding='utf-8')
    return text


def _derive_code_branching_population() -> list[str]:
    """Derive, from the tree, every code file that BRANCHES on the gate's status.

    The predicate is a conjunction — the file references the freshness gate AND
    compares against one of its status literals — because either half alone is
    wrong in a different direction: referencing the gate catches the many files
    that merely describe it, and comparing against ``'fresh'`` catches four
    unrelated vocabularies that use the same word.

    An unreadable file is NOT skipped silently: it is reported, because a file the
    derivation could not read is a file that might branch and was never examined,
    which is a coverage gap rather than an absence.
    """
    found: list[str] = []
    unreadable: list[str] = []
    for root in _DERIVATION_ROOTS:
        for path in sorted((PROJECT_ROOT / root).rglob('*.py')):
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            try:
                text = path.read_text(encoding='utf-8')
            except OSError as exc:  # a read that failed is not a read that found nothing
                unreadable.append(f'{rel}: {exc}')
                continue
            if not any(token in text for token in _GATE_REFERENCES):
                continue
            if _STATUS_COMPARISON.search(text):
                found.append(rel)
    assert not unreadable, (
        f'{len(unreadable)} file(s) could not be read, so the derived population is '
        f'incomplete and its size proves nothing: {unreadable}'
    )
    return found


#: The class's code members, DERIVED. Bound once at module level so every guard
#: below reasons over the same measured population instead of re-walking the tree,
#: and so none of them has to name a file another slice owns.
_CODE_BRANCHING_CONSUMERS: tuple[str, ...] = tuple(
    path for path in _derive_code_branching_population() if path != _SELF
)


def test_the_branching_population_is_derived_non_empty_and_reconciles() -> None:
    """The population is measured, published, and reconciled — never assumed.

    Three failures are kept apart. An EMPTY derived set would make every
    per-member assertion below vacuously true, so it fails first. A per-slice
    census that does not match the declared one means a branching consumer
    appeared or vanished without this class being updated — reconciled by owning
    slice rather than by filename, so a rename inside a slice is not reported as a
    drift it is not. And a total that does not equal deliverable 1's published
    ``branches`` count means the partition this module reasons over has moved —
    recorded as a failure rather than absorbed.
    """
    derived = _CODE_BRANCHING_CONSUMERS

    assert derived, (
        'the derived branching-consumer population is EMPTY, so every per-member '
        'assertion in this module would pass without examining anything'
    )
    by_slice = dict(Counter(path.rsplit('/', 1)[0] for path in derived))
    assert by_slice == _CODE_CONSUMER_SLICES, (
        f'the branching class is now distributed as {by_slice} against a declared '
        f'{_CODE_CONSUMER_SLICES}; the derived members are {sorted(derived)}'
    )

    total = len(derived) + len(_DOC_BRANCHING_CONSUMERS)
    assert total == _D1_PUBLISHED_BRANCHES_COUNT, (
        f'the branching class now measures {total} member(s) '
        f'({len(derived)} code + {len(_DOC_BRANCHING_CONSUMERS)} document) against '
        f"deliverable 1's published branches count of {_D1_PUBLISHED_BRANCHES_COUNT}"
    )


def test_no_code_consumer_refuses_against_the_bare_token() -> None:
    """A refusal written against ``fresh`` alone would admit the exempt route.

    This is the shape the split created and the one a reader is most likely to
    reintroduce: before the split, "not fresh" WAS "refused", and the phrase reads
    as correct long after it stopped being so. It is now satisfied by an
    ``exempt`` return, so a negative control written that way passes while the
    gate stands open.
    """
    population = _CODE_BRANCHING_CONSUMERS
    offenders = [path for path in population if _FORBIDDEN_BARE_REFUSAL in _read(path)]

    assert not offenders, (
        f'{len(offenders)} of {len(population)} code branching consumer(s) refuse '
        f'against the bare token: {offenders}. Write the refusal against both '
        f'permitting members {sorted(_PERMITTING)}.'
    )


def test_no_code_consumer_enumerates_a_vocabulary_missing_a_permitting_member() -> None:
    """A membership predicate over a stale vocabulary narrows what it accepts.

    A tuple naming the three pre-split members is not wrong in the way a bare
    refusal is — it does not admit anything it should not — but it silently
    encodes a closed set that is no longer closed, so the member it omits becomes
    a failure the moment that route is reached.
    """
    population = _CODE_BRANCHING_CONSUMERS
    offenders = [path for path in population if _FORBIDDEN_STALE_VOCABULARY in _read(path)]

    assert not offenders, (
        f'{len(offenders)} of {len(population)} code branching consumer(s) enumerate '
        f'the pre-split three-member vocabulary: {offenders}. The vocabulary has '
        f'{len(_ALL_STATUSES)} members: {sorted(_ALL_STATUSES)}.'
    )


def test_the_verified_route_positive_control_reads_its_evidence() -> None:
    """The one ``== 'fresh'`` pass predicate in the class reads what was examined.

    The subject is selected by BEHAVIOUR — the member of the derived class whose
    pass predicate compares positively against the token — not by file name, so a
    rename inside the slice that owns it does not red this module. Such a control
    bypasses the exempt short-circuit deliberately, so its token comparison would
    pass unchanged, which is exactly why the predicate had to move anyway. A
    positive control that can be satisfied without reading what the gate examined
    is the defect this plan removes, and leaving one inside the plan that removes
    it is not acceptable.
    """
    controls = [path for path in _CODE_BRANCHING_CONSUMERS if _VERIFIED_ROUTE_PASS_PREDICATE in _read(path)]

    assert len(controls) == 1, (
        f'expected exactly one verified-route positive control in the branching class of '
        f'{len(_CODE_BRANCHING_CONSUMERS)} code member(s); found {len(controls)}: {controls}. '
        f'With none there is no subject for this assertion; with several the class has '
        f'grown a second pass predicate that this guard was never written to cover.'
    )
    text = _read(controls[0])

    required = ('matched_notation', 'matched_entry_index', 'worktree_sha')
    missing = [key for key in required if key not in text]

    assert not missing, (
        f'the verified-route positive control reads {len(required) - len(missing)} of '
        f'{len(required)} evidence key(s); missing {missing}. Without them the control '
        f'passes on the bare token alone.'
    )


def test_both_document_consumers_name_the_second_permitting_member() -> None:
    """A branch table that names only ``fresh`` admits the exempt route silently.

    The two workflow documents are executed by an agent reading them, so their
    branch instruction IS their predicate. Each must name the second permitting
    member, and neither may keep the retired closure phrase that called every
    non-``fresh`` status a refusal — a phrase that was true before the split and
    is now false in the fail-open direction.
    """
    population = _DOC_BRANCHING_CONSUMERS
    retired_closure = 'non-' + '`fresh`'

    unnamed = [path for path in population if '`exempt`' not in _read(path)]
    stale_closure = [path for path in population if retired_closure in _read(path)]

    assert not unnamed, (
        f'{len(unnamed)} of {len(population)} document branching consumer(s) never name '
        f'the second permitting member: {unnamed}'
    )
    assert not stale_closure, (
        f'{len(stale_closure)} of {len(population)} document branching consumer(s) keep '
        f'the retired closure phrase, which now denotes a permitting member: {stale_closure}'
    )


# =============================================================================
# PROOF 3 — the fail-closed degradation is unchanged
# =============================================================================


def _degradation_inputs() -> tuple[tuple[str, object], ...]:
    """The ways an unobtainable build-necessity verdict can present.

    Both must degrade to ``build`` — the fall-through into the ledger scan, which
    is the fail-closed direction. Reading either as "no build was needed" would
    wave a plan through with no freshness proof at all.
    """
    inputs = (
        ('raises', RuntimeError('marshal.json unreadable')),
        ('non_dict', ['not', 'a', 'dict']),
    )
    # ⛔ Vacuity guard — an empty return collects zero cases at the parametrize that
    # binds this helper, reporting green while exercising neither degradation path.
    assert inputs, 'the degradation-input population is empty'
    return inputs


@pytest.mark.parametrize(('label', 'payload'), _degradation_inputs())
def test_an_unobtainable_verdict_degrades_to_build(monkeypatch, label, payload) -> None:
    """Each degradation input yields ``{'decision': 'build'}``, not an exemption."""
    import extension_base

    monkeypatch.setattr(_freshness_mod, '_build_necessity_verdict', _REAL_BUILD_NECESSITY_VERDICT)

    def _degrade(*_args, **_kwargs):
        if isinstance(payload, BaseException):
            raise payload
        return payload

    monkeypatch.setattr(extension_base, 'should_execute_build', _degrade)

    verdict = _freshness_mod._build_necessity_verdict('degradation-plan')

    assert verdict == {'decision': 'build'}, (
        f'degradation input {label!r} (1 of {len(_degradation_inputs())} exercised) '
        f'yielded {verdict!r} rather than the fail-closed fall-through'
    )
    assert verdict.get('decision') != 'not_necessary', (
        f'degradation input {label!r} produced the exemption verdict, which would '
        f'return the permitting member {_PERMITTING[0]!r} with nothing examined'
    )


def test_every_degradation_input_is_exercised() -> None:
    """Publish the degradation-input population the parametrization covers.

    The parametrized case above proves each input degrades; it cannot prove the
    input set is non-empty, because a parametrization over an empty sequence
    collects zero cases and reports green.
    """
    inputs = _degradation_inputs()
    assert len(inputs) == 2, (
        f'{len(inputs)} degradation input(s) declared; both the raising and the non-dict routes must be exercised'
    )


# =============================================================================
# PROOF 4 — the stale and undecidable vocabularies are unchanged
# =============================================================================


def _shipped_stale_reasons() -> set[str]:
    """Enumerate the ``stale`` reasons from the SHIPPED source, not from a list.

    Five come from the command module's own tables (the per-observed-status
    reasons plus the mutation reason) and four from the cross-check module's
    named constants. Reading them from the modules is what makes this a
    derivation: a reason renamed in the source moves here automatically, and a
    reason DELETED shrinks the count and fails the assertion below.
    """
    from_command = {reason for reason, _message in _freshness_mod._STALE_BY_STATUS.values()}
    from_command.add(_freshness_mod._STALE_MUTATED[0])
    from_crosscheck = {
        crosscheck.REASON_NOTATION_UNRELATED,
        crosscheck.REASON_NOTATION_ABSENT,
        crosscheck.REASON_SCOPE_NARROW,
        crosscheck.REASON_NO_ADMISSIBLE_ROW,
    }
    return from_command | from_crosscheck


def test_the_stale_reason_vocabulary_still_has_exactly_nine_members() -> None:
    """The nine ``stale`` reasons are untouched by the status-member split."""
    reasons = _shipped_stale_reasons()

    assert len(reasons) == 9, (
        f'the shipped stale vocabulary enumerates {len(reasons)} reason(s) against an '
        f'expectation of 9: {sorted(reasons)}'
    )
    assert 'exempt' not in reasons, (
        f'the new status member leaked into the stale reason vocabulary of {len(reasons)} member(s)'
    )


def _exercise_undecidable_reasons(plan_context, monkeypatch, tmp_path) -> set[str]:
    """Derive the ``undecidable`` reasons by DRIVING both of its routes.

    They are inline literals in the command handler rather than named constants,
    so there is no module attribute to read. Exercising the routes and collecting
    what the gate actually returned is the derivation that does not restate them.
    """
    observed: set[str] = set()

    plan_id = 'discrimination-undecidable-sha'
    _write_status(plan_context.plan_dir_for(plan_id))
    _stub_verdict(monkeypatch, {'decision': 'build'})
    _stub_worktree_sha(monkeypatch, None)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)]))
    verdict = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))
    assert verdict['status'] == 'undecidable', verdict
    observed.add(verdict['reason'])

    plan_id = 'discrimination-undecidable-ledger'
    _write_status(plan_context.plan_dir_for(plan_id))
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, []))
    verdict = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))
    assert verdict['status'] == 'undecidable', verdict
    observed.add(verdict['reason'])

    return observed


def test_the_undecidable_reason_vocabulary_still_has_exactly_two_members(plan_context, monkeypatch, tmp_path) -> None:
    """Both ``undecidable`` routes are reached, and they report distinct reasons."""
    reasons = _exercise_undecidable_reasons(plan_context, monkeypatch, tmp_path)

    assert len(reasons) == 2, (
        f'exercising both undecidable routes yielded {len(reasons)} distinct reason(s) '
        f'against an expectation of 2: {sorted(reasons)}'
    )
    assert reasons == {'no_registry', 'head_unresolvable'}, sorted(reasons)
