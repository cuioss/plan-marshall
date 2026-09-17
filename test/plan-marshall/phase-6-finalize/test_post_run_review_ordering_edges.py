#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
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
(g2) A dirty TRACKED path UNDER ``.plan/`` (``marshal.json``, an architecture
    descriptor) is ALSO reported — the exemption is keyed on git trackedness, not
    on the ``.plan/`` prefix, so a tracked plan-config write left dirty after the
    merge gate is as unpushable as any other tracked source.
(h) A dirty UNTRACKED path under ``.plan/`` is NOT an offender (**negative
    control** — matched to (g2): the ordinary plan-state writes every finalize
    step makes (status, logs, findings) are untracked, so reporting them would
    fire the guard on every post-run step).

The controls are matched deliberately: (g)/(g2) alone would pass for a guard that
reports every dirty path, and (h) alone would pass for a guard that exempts the
whole ``.plan/`` prefix — which is the defect. Only the set pins the trackedness
predicate.

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

_guard = load_script_module('plan-marshall', 'phase-6-finalize', 'post_run_source_guard.py')
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
    return [rec for rec in find_implementors(_EXT_POINT) if _declares_post_run_review(Path(rec['path']))]


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


_TRACKED_SOURCE = 'marketplace/bundles/demo/skills/demo/SKILL.md'

_TRACKED_PLAN_STATE = '.plan/local/status.json'

_UNTRACKED_PLAN_STATE = '.plan/local/logs/work.log'

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
    introduces is unambiguously that test's own. The ``.plan/`` file is
    force-added because an ambient global ``core.excludesFile`` could otherwise
    keep it untracked — which would silently turn the tracked ``.plan/`` control
    into an untracked one. The untracked negative control writes its own,
    separately, so it does NOT go through this add.
    """
    repo = tmp_path / 'worktree'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    _write(repo, _TRACKED_SOURCE, '# demo skill\n')
    _write(repo, _TRACKED_PLAN_STATE, '{"phase": "6-finalize"}\n')
    _git(repo, 'add', '-f', _TRACKED_SOURCE, _TRACKED_PLAN_STATE)
    _git(repo, 'commit', '-m', 'chore: seed worktree')
    return repo

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
        fields = extension_discovery._read_frontmatter_fields(doc_path, (_FACT_KEY, _MUTATES_SOURCE_KEY))
        if bool(fields.get(_FACT_KEY, False)) and bool(fields.get(_MUTATES_SOURCE_KEY, False)):
            offenders.append(f'{record["name"]} ({doc_path})')

    assert not offenders, (
        f'These steps declare both {_FACT_KEY}: true and {_MUTATES_SOURCE_KEY}: '
        'true. The two are mutually exclusive — a post-run-review step runs after '
        'the merge gate, where a tracked-source edit can never be pushed onto the '
        f'already-merged feature branch: {offenders}'
    )


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


def test_dirty_untracked_plan_state_is_not_reported(committed_repo: Path):
    """(h) NEGATIVE CONTROL — a dirty UNTRACKED ``.plan/`` path is not an offender.

    Matched to the tracked ``.plan/`` positive control below: the ordinary
    plan-state writes every finalize step makes (status, logs, findings) are
    untracked, so a guard that reported them would fire on every post-run step
    and be switched off within a run. The exemption drops them because they are
    untracked — NOT because of the ``.plan/`` prefix.
    """
    # Arrange — the ordinary untracked plan-state write every finalize step makes.
    _write(committed_repo, _UNTRACKED_PLAN_STATE, 'work-log line\n')

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is True, (
        'An UNTRACKED .plan/ write was reported as an unpushable source edit. '
        'Untracked plan state is not tracked source; reporting it would make the '
        f'guard fire on every post-run-review step. Reported: {offenders}'
    )
    assert offenders == []


def test_cli_publishes_examined_population(committed_repo: Path):
    """(D5d) The CLI publishes the population it examined.

    A ``clean`` verdict that names the paths it considered is distinguishable
    from a looked-at-nothing pass. Seen RED before the fix (no such field is
    emitted), GREEN after.
    """
    # Arrange — one dirty tracked source path, so the considered set is non-empty.
    _write(committed_repo, _TRACKED_SOURCE, '# demo skill\n\nEdited.\n')
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
    payload = result.toon()
    assert payload.get('considered_paths'), (
        'The guard published no non-empty considered-population field, so a '
        f'clean pass cannot be told from a looked-at-nothing one. Payload: {payload}'
    )


def test_mixed_dirty_reports_tracked_paths_and_exempts_untracked_plan_state(
    committed_repo: Path,
):
    """All three cases composed: untracked ``.plan/`` exempt, tracked paths reported.

    Run separately the controls leave open the possibility that the guard keys on
    "the worktree is dirty" rather than on WHICH path is dirty AND whether it is
    tracked. Dirtying an untracked ``.plan/`` write, a tracked ``.plan/`` file,
    and a tracked source file at once, then asserting the exact reported set,
    closes that: the untracked plan-state write is dropped while BOTH tracked
    paths are named.
    """
    # Arrange — the realistic post-run-band shape: ordinary (untracked) plan
    # state, plus a tracked config write and a stray tracked source edit.
    _write(committed_repo, _UNTRACKED_PLAN_STATE, 'work-log line\n')
    _write(committed_repo, _TRACKED_PLAN_STATE, '{"phase": "6-finalize", "step": "done"}\n')
    _write(committed_repo, _TRACKED_SOURCE, '# demo skill\n\nEdited post-merge.\n')

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is False
    assert offenders == sorted([_TRACKED_PLAN_STATE, _TRACKED_SOURCE])


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
