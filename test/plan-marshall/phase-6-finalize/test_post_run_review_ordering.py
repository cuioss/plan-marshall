#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Derivation guard for the finalize-step ``post_run_review`` membership set.

A post-run-review step looks back over the finished run and reports on it. Three
such steps — ``project:finalize-step-review-retrospective``,
``default:lessons-capture`` and ``default:finalize-step-preference-emitter`` —
were ordered ahead of the merge gate ``default:branch-cleanup``, which hosts the
pre-merge review barrier, the bot re-review wait, triage and loop-back. Each
therefore emitted a confident verdict over evidence the gate had not yet
produced. The role was never a declared fact — it existed only as an effort role
sub-key picking a dispatch model level — so nothing constrained where such a step
could be ordered.

Membership is now a **derived frontmatter fact**: each step doc declares
``post_run_review: true`` in its own frontmatter, and the set is obtained by
reading that fact off every doc ``find_implementors()`` discovers. The governing
discriminator is two predicates, both of which must hold — **P1** the step's
output is a record/assessment about the just-finished run, and **P2** at least
one input it reads is only determined at or after the merge gate. These tests pin
that derivation:

(a) The derived set is **non-empty**. A derivation that silently returned nothing
    would make every other assertion here vacuous, so this is checked first and
    on its own.
(b) It contains every known member — the three that needed moving plus
    ``plan-marshall:plan-retrospective`` (already correctly placed),
    ``default:record-metrics`` and
    ``default:finalize-step-print-phase-breakdown`` (already post-gate,
    declaration-only). The two already-correct members are required too: a guard
    whose required set covered only the movers would re-create the
    population-not-derived defect it exists to remove.
(c) The merge gate is **discoverable**, so the ordering assertion below cannot
    pass merely because no threshold was found.
(d) No member is ordered before the merge gate, whose order is **dynamically
    resolved** from the discovered ``default:branch-cleanup`` record rather than
    the literal ``70`` — a future move of the gate must move the threshold with
    it instead of silently vacating this guard.
(e) No step declares both ``post_run_review: true`` and ``mutates_source: true``.
    The exclusion is a consequence of P2, not an independent axiom: a step that
    reads post-merge-determined evidence runs once the feature branch is already
    gone, so it cannot produce a pushable source edit.
(f) Every member declares a ``mutates_source`` key **explicitly** — present, not
    merely falsy-by-absence. This is the in-module counterpart to the
    ``mutates_source_declaration_missing`` quality-gate-time (plugin-doctor)
    rule; its external
    backstop is
    ``test/pm-plugin-development/plugin-doctor/test_analyze_mutates_source_order.py``
    ``::test_real_marketplace_has_zero_findings``.

Plus the per-member mutation guard: (b) is verified to fail for **each** required
member independently, so a guard that passes on one omission while missing
another cannot read as green.

Checks (a)-(f) all read DECLARATIONS. That is the limit of what a frontmatter
guard can prove, and it is exactly why the runtime arm below exists: a step whose
branch writes tracked source in violation of its own ``mutates_source: false``
declaration is invisible to every assertion above. The second half of this
module therefore drives ``phase-6-finalize/scripts/post_run_source_guard.py`` —
the seam item 5f of ``phase-6-finalize/SKILL.md`` calls once per post-run-band
step return — against **real worktree state** in a real throwaway git repository:

(g) A dirty TRACKED path outside ``.plan/`` is reported as an offender
    (**positive control** — the check can fail, and fails for the right reason).
(h) A dirty path under ``.plan/`` alone is NOT an offender (**negative control**
    — matched to (g), since every finalize step writes plan state under
    ``.plan/`` and a bare porcelain non-empty test would fire on all of them).

The two controls are matched deliberately: (g) alone would pass for a guard that
simply reports every dirty path, and (h) alone would pass for a guard that
reports nothing at all. Only the pair pins the predicate.

**The population is derived from discovery, never hardcoded**, so a step added
later is covered automatically. This module deliberately asserts **no cardinality
literal**: a hardcoded count is precisely the drift shape this plan removes. The
named-member assertions are lower bounds on a derived set, not a pinned
enumeration of it.

The derivation reuses the registry's OWN path — ``find_implementors()`` for the
population and ``extension_discovery._read_frontmatter_fields`` for the fact — so
no second parser exists to drift from the one the registry uses. This mirrors
``test_head_dependence_derivation.py``, the sibling guard for ``head_dependent``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import extension_discovery
from conftest import get_script_path, load_script_module, run_script
from extension_discovery import find_implementors

_guard = load_script_module(
    'plan-marshall', 'phase-6-finalize', 'post_run_source_guard.py'
)
check_tracked_source = _guard.check_tracked_source

#: The canonical ext-point value whose implementors carry the fact.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The frontmatter key that IS the membership declaration.
_FACT_KEY = 'post_run_review'

#: The reciprocal fact. Mutually exclusive with _FACT_KEY, and required to be
#: declared explicitly on every member.
_MUTATES_SOURCE_KEY = 'mutates_source'

#: The merge gate. Its order is the ordering threshold, read off discovery.
_MERGE_GATE = 'default:branch-cleanup'

#: Members this plan MOVED from ahead of the merge gate to behind it.
_MOVED_MEMBERS = (
    'project:finalize-step-review-retrospective',
    'default:lessons-capture',
    'default:finalize-step-preference-emitter',
)

#: Members that were ALREADY correctly placed and needed only the declaration.
#: Required here for the same reason the movers are: a required set covering only
#: the movers would assert a hand-picked subset rather than the derived role.
_ALREADY_PLACED_MEMBERS = (
    'plan-marshall:plan-retrospective',
    'default:record-metrics',
    'default:finalize-step-print-phase-breakdown',
)

#: The lower bound the derived set must cover. NOT an enumeration of the set —
#: the set is derived and may legitimately be larger.
_REQUIRED_MEMBERS = _MOVED_MEMBERS + _ALREADY_PLACED_MEMBERS


def _declares_post_run_review(doc_path: Path) -> bool:
    """Read the ``post_run_review`` fact off one discovered step doc.

    Reuses ``_read_frontmatter_fields`` — the same extraction primitive
    ``_build_implementor_record`` uses for every other implementor field — rather
    than re-implementing a frontmatter parser. The coerced value is narrowed with
    ``bool()`` exactly the way the registry narrows ``default_on``, so every
    conditional boolean is read identically.
    """
    fields = extension_discovery._read_frontmatter_fields(doc_path, (_FACT_KEY,))
    return bool(fields.get(_FACT_KEY, False))


def _post_run_review_records() -> list[dict]:
    """Derive the post-run-review implementor records from discovery."""
    return [
        rec
        for rec in find_implementors(_EXT_POINT)
        if _declares_post_run_review(Path(rec['path']))
    ]


def _post_run_review_names() -> set[str]:
    """Derive the post-run-review step-id set from discovery."""
    return {rec['name'] for rec in _post_run_review_records()}


def _missing_required(derived: set[str]) -> list[str]:
    """The membership predicate under test: which required members are absent.

    Factored out so the mutation guard can drive the SAME predicate the
    assertions use. A guard that re-implemented the check would prove nothing
    about the check that actually runs.
    """
    return [member for member in _REQUIRED_MEMBERS if member not in derived]


def _merge_gate_order() -> int | None:
    """Resolve the merge gate's order from discovery, never from a literal.

    Returns ``None`` when the gate is not discoverable — the vacuity case test
    (c) pins away, so the ordering assertion can never pass merely because no
    threshold was found.
    """
    for record in find_implementors(_EXT_POINT):
        if record.get('name') == _MERGE_GATE:
            return record.get('order')
    return None


def test_derived_set_is_non_empty():
    """(a) The derivation resolves something — every later assertion depends on it."""
    derived = _post_run_review_names()

    assert derived, (
        'The post-run-review derivation returned an EMPTY set. Every membership '
        'assertion in this module would pass vacuously against an empty '
        'derivation, so this is checked first and separately. Either no step doc '
        f'declares {_FACT_KEY}: true, or find_implementors({_EXT_POINT!r}) '
        'discovered no step docs at all.'
    )


@pytest.mark.parametrize('member', _REQUIRED_MEMBERS)
def test_derived_set_contains_required_member(member):
    """(b) Every known post-run-review step is derived.

    Parametrized per member rather than asserted as one set-containment, so a
    regression that drops exactly one fails as one identifiable test instead of
    hiding inside a combined assertion.
    """
    derived = _post_run_review_names()

    assert member in derived, (
        f'{member} looks back over the finished run and reads evidence the merge '
        f'gate produces, so its step doc must declare {_FACT_KEY}: true in '
        f'frontmatter. Derived set: {sorted(derived)}'
    )


@pytest.mark.parametrize('omitted', _REQUIRED_MEMBERS)
def test_each_required_member_is_independently_load_bearing(omitted):
    """Mutation guard: dropping any ONE required member is detected on its own.

    Removing a single member from the derived set must make the membership
    predicate report exactly that member — no more, no fewer. This proves the
    check is sensitive to each member independently, so a derivation that
    silently omitted one while satisfying the others could never read as green.
    A single set-containment assertion cannot make that claim about itself.
    """
    derived = _post_run_review_names()
    assert omitted in derived, (
        f'Mutation guard precondition failed: {omitted} is not in the derived set, '
        'so removing it proves nothing. Fix the derivation first.'
    )

    mutated = derived - {omitted}

    assert _missing_required(mutated) == [omitted], (
        f'The membership predicate did not isolate {omitted} when it alone was '
        'removed from the derived set. A predicate that cannot detect each '
        'member independently can pass while silently missing one — which is '
        'exactly how a member goes unnoticed. '
        f'Reported missing: {_missing_required(mutated)}'
    )


def test_merge_gate_is_discoverable():
    """(c) The ordering assertion below is non-vacuous.

    The ordering check compares each member's order against the gate's. If the
    gate were undiscoverable there would be no threshold to compare against and
    the check would have nothing to fail on, so the gate's discoverability is
    asserted separately rather than folded into the ordering test.
    """
    merge_gate_order = _merge_gate_order()

    assert merge_gate_order is not None, (
        f'{_MERGE_GATE} was not found among the discovered {_EXT_POINT} '
        'implementors, so the merge-gate ordering threshold cannot be resolved '
        'and the ordering guard below would have nothing to compare against.'
    )


def test_no_member_is_ordered_before_the_merge_gate():
    """(d) Every derived member runs after the merge gate.

    The threshold is READ from the discovered gate record, never hardcoded, so
    moving the gate moves the obligation with it. The comparison is strict:
    a step sharing the gate's order has no guaranteed ordering against it, so it
    cannot be relied on to run after the gate.

    The population is the DERIVED set, so a member added later is covered with no
    edit here.
    """
    merge_gate_order = _merge_gate_order()
    assert merge_gate_order is not None, (
        'Precondition failed — see test_merge_gate_is_discoverable.'
    )

    offenders = [
        f"{rec['name']} (order {rec.get('order')})"
        for rec in _post_run_review_records()
        if not isinstance(rec.get('order'), int) or rec['order'] <= merge_gate_order
    ]

    assert not offenders, (
        f'These {_FACT_KEY} steps are ordered at or before the merge gate '
        f'{_MERGE_GATE} (order {merge_gate_order}). A post-run-review step reads '
        'evidence that is only determined at or after that gate, so ordered ahead '
        'of it the step reports a confident verdict about evidence that does not '
        f'exist yet: {offenders}'
    )


def test_no_step_declares_both_post_run_review_and_mutates_source():
    """(e) The two facts are mutually exclusive across every discovered step.

    Scanned over ALL implementors, not just the derived members, so a step that
    acquires both facts is caught wherever it sits. The exclusion follows from
    P2: a step reading post-merge-determined evidence runs once the feature
    branch is gone, so a source edit it wrote could never ride the plan's PR.
    """
    offenders = []
    for record in find_implementors(_EXT_POINT):
        doc_path = Path(record['path'])
        fields = extension_discovery._read_frontmatter_fields(
            doc_path, (_FACT_KEY, _MUTATES_SOURCE_KEY)
        )
        if bool(fields.get(_FACT_KEY, False)) and bool(
            fields.get(_MUTATES_SOURCE_KEY, False)
        ):
            offenders.append(f"{record['name']} ({doc_path})")

    assert not offenders, (
        f'These steps declare both {_FACT_KEY}: true and {_MUTATES_SOURCE_KEY}: '
        'true. The two are mutually exclusive — a post-run-review step runs after '
        'the merge gate, where a tracked-source edit can never be pushed onto the '
        f'already-merged feature branch: {offenders}'
    )


def test_every_member_declares_mutates_source_explicitly():
    """(f) Every derived member settles the source-mutation claim explicitly.

    Being ordered after the merge gate, each member falls in the band where an
    ABSENT ``mutates_source`` key is itself a quality-gate-time (plugin-doctor)
    error — a silent
    omission is exactly how a source-mutating step slips past the ordering check
    without ever making the claim. Presence is asserted, not merely falsiness,
    because an absent key is falsy and would pass a truthiness check.

    The population is the DERIVED set, so a member added later is covered with no
    edit here.
    """
    offenders = []
    for record in _post_run_review_records():
        doc_path = Path(record['path'])
        fields = extension_discovery._read_frontmatter_fields(
            doc_path, (_MUTATES_SOURCE_KEY,)
        )
        if _MUTATES_SOURCE_KEY not in fields:
            offenders.append(f"{record['name']} ({doc_path})")

    assert not offenders, (
        f'These {_FACT_KEY} steps declare no {_MUTATES_SOURCE_KEY} key at all. '
        'A step ordered at or after the merge gate MUST settle the pushability '
        'claim explicitly — an omission reads as no-claim and evades the '
        f'ordering rule that governs source edits: {offenders}'
    )


# ---------------------------------------------------------------------------
# Runtime arm — real worktree state, not a declaration
#
# Everything above reads frontmatter. These tests observe an actual git
# worktree, because the defect the declaration cannot detect is a branch that
# violates it.
# ---------------------------------------------------------------------------

#: A tracked path that IS source — the shape whose post-merge write is
#: unpushable and therefore the thing the guard exists to name.
_TRACKED_SOURCE = 'marketplace/bundles/demo/skills/demo/SKILL.md'

#: A tracked path under ``.plan/`` — the shape every finalize step legitimately
#: writes, and therefore the thing the guard must NOT name.
_PLAN_STATE = '.plan/local/status.json'


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Run one git command against ``repo`` with a pinned, hermetic identity.

    Commit identity and signing are supplied per-invocation rather than read
    from the ambient environment so the fixture behaves identically on a
    developer machine with a global gitconfig and on a bare CI runner with
    none.
    """
    return subprocess.run(
        [
            'git',
            '-C',
            str(repo),
            '-c',
            'user.name=Test',
            '-c',
            'user.email=test@example.invalid',
            '-c',
            'commit.gpgsign=false',
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


def _write(repo: Path, rel_path: str, content: str) -> Path:
    """Write ``content`` to ``repo/rel_path``, creating parents as needed."""
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    return target


@pytest.fixture
def committed_repo(tmp_path: Path) -> Path:
    """A real git repository with one tracked source file and one tracked ``.plan/`` file.

    Both files are committed, so the worktree starts clean and any dirt a test
    introduces is unambiguously that test's own. ``.plan/`` is force-added
    because an ambient global ``core.excludesFile`` could otherwise keep it
    untracked, which would silently turn the negative control into a
    tracked-vs-untracked test instead of the ``.plan/``-exclusion test it is
    meant to be.
    """
    repo = tmp_path / 'worktree'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    _write(repo, _TRACKED_SOURCE, '# demo skill\n')
    _write(repo, _PLAN_STATE, '{"phase": "6-finalize"}\n')
    _git(repo, 'add', '-f', _TRACKED_SOURCE, _PLAN_STATE)
    _git(repo, 'commit', '-m', 'chore: seed worktree')
    return repo


def test_clean_worktree_reports_clean(committed_repo: Path):
    """Baseline: an untouched worktree yields no offenders.

    Without this, both controls below could be satisfied by a guard that is
    simply reading a worktree that was never clean to begin with.
    """
    # Arrange — the fixture committed everything; nothing has been touched.

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is True
    assert offenders == []


def test_dirty_tracked_source_is_reported(committed_repo: Path):
    """(g) POSITIVE CONTROL — a dirty tracked source path is named as an offender.

    This is the branch the ``mutates_source: false`` declaration claims cannot
    happen. A guard that could not fail here would make the negative control
    below vacuous.
    """
    # Arrange — a post-run-band step writes tracked source after the merge gate.
    _write(committed_repo, _TRACKED_SOURCE, '# demo skill\n\nEdited post-merge.\n')

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is False, (
        'A dirty TRACKED source path outside .plan/ went unreported. That edit '
        'was made after the merge gate and has no push path, which is precisely '
        'the condition this guard exists to surface.'
    )
    assert offenders == [_TRACKED_SOURCE]


def test_dirty_plan_state_alone_is_not_reported(committed_repo: Path):
    """(h) NEGATIVE CONTROL — a dirty ``.plan/`` path alone is not an offender.

    Matched to the positive control above: every finalize step writes plan
    state, so a guard that reported this would fire on every post-run step and
    be switched off within a run.
    """
    # Arrange — the ordinary plan-state write every finalize step makes.
    _write(committed_repo, _PLAN_STATE, '{"phase": "6-finalize", "step": "done"}\n')

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is True, (
        'A .plan/ write was reported as an unpushable source edit. .plan/ is '
        'plan state, not source; reporting it would make the guard fire on '
        f'every post-run-review step. Reported: {offenders}'
    )
    assert offenders == []


def test_untracked_source_file_is_not_reported(committed_repo: Path):
    """A brand-new untracked file is not an offender — the predicate is TRACKED.

    The predicate is "dirty AND tracked AND outside .plan/". This pins the
    tracked conjunct independently of the ``.plan/`` conjunct that (h) pins.
    """
    # Arrange — a new file that was never added to the index.
    _write(committed_repo, 'marketplace/bundles/demo/scratch.md', 'scratch\n')

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is True
    assert offenders == []


def test_both_dirty_reports_only_the_tracked_source_path(committed_repo: Path):
    """The two controls composed: the ``.plan/`` write is filtered, the source write is not.

    Run separately, (g) and (h) each leave open the possibility that the guard
    keys on "the worktree is dirty" rather than on WHICH path is dirty. Dirtying
    both at once and asserting the exact reported set closes that.
    """
    # Arrange — the realistic post-run-band shape: plan state plus a stray edit.
    _write(committed_repo, _PLAN_STATE, '{"phase": "6-finalize", "step": "done"}\n')
    _write(committed_repo, _TRACKED_SOURCE, '# demo skill\n\nEdited post-merge.\n')

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is False
    assert offenders == [_TRACKED_SOURCE]


def test_renamed_tracked_source_reports_both_sides(committed_repo: Path):
    """A staged rename of tracked source names both the old and the new path.

    Porcelain reports a rename as one record carrying two paths; decoding only
    the first would drop the destination, and decoding only the record would
    misalign every later record in the ``-z`` stream.
    """
    # Arrange — stage a rename so git emits an R record with both paths.
    renamed = 'marketplace/bundles/demo/skills/demo/RENAMED.md'
    _git(committed_repo, 'mv', _TRACKED_SOURCE, renamed)

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is False
    assert offenders == sorted([_TRACKED_SOURCE, renamed])


def test_non_repository_directory_reports_error_without_inventing_offenders(
    outside_repo_dir: Path,
):
    """An unusable observation degrades to ``clean`` plus an error, never to an offender.

    The guard is advisory. Reporting a phantom offender because git could not
    answer would put a WARNING and a finding on a run that did nothing wrong.

    The directory comes from ``outside_repo_dir`` rather than ``tmp_path``:
    ``build.py`` gives pytest a repo-local ``--basetemp``, so a ``tmp_path``
    subdirectory still sits INSIDE this repository's worktree and
    ``git -C`` there resolves the enclosing repo instead of failing — the test
    would then silently assert against plan-marshall's own working tree.
    """
    # Arrange — a directory with no git repository anywhere above it.
    plain_dir = outside_repo_dir / 'not-a-repo'
    plain_dir.mkdir()

    # Act
    clean, offenders, error = check_tracked_source(plain_dir)

    # Assert
    assert error is not None
    assert clean is True
    assert offenders == []


def test_cli_reports_offender_and_still_exits_zero(committed_repo: Path):
    """The non-blocking contract holds at the CLI boundary, not just in-process.

    Item 5f treats ``clean: false`` as a WARNING plus a finding and then
    proceeds. A non-zero exit here would make the advisory band blocking, which
    contradicts the band's documented placement after the merge gate.
    """
    # Arrange — the offending condition.
    _write(committed_repo, _TRACKED_SOURCE, '# demo skill\n\nEdited post-merge.\n')
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'post_run_source_guard.py')

    # Act
    result = run_script(
        script,
        'check',
        '--step-id',
        'default:lessons-capture',
        '--project-dir',
        str(committed_repo),
    )

    # Assert
    assert result.returncode == 0, (
        'The guard exited non-zero on a detected offender. The post-run band is '
        'advisory and never blocking, so the verdict rides the payload and the '
        f'exit code stays 0. stderr: {result.stderr}'
    )
    payload = result.toon()
    assert payload['status'] == 'success'
    assert payload['step_id'] == 'default:lessons-capture'
    assert payload['clean'] is False
    assert _TRACKED_SOURCE in str(payload['offending_paths'])
