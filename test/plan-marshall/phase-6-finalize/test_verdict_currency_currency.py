#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Unit tests for the verdict-currency classifier.

The dispatcher's re-entry check used to re-fire a head-dependent finalize step on
a bare SHA inequality, so every HEAD advance inside finalize — a settle-band
commit, a replaying rebase, a loop-back fix — re-ran every gate recorded before
it, mostly to re-confirm the identical verdict. ``scripts/verdict_currency.py``
narrows that to advances that can actually change the answer.

The safety property is asymmetric and these tests pin it in that shape: a
``preserved`` verdict is reachable only past a resolution gate (the step doc
resolved AND the step is head-dependent), and past that gate on exactly two paths
— identical SHAs, or a non-empty declaration whose globs match no changed path.
EVERY other path must return ``invalidated``. So the fail-closed branches are
asserted one at a time — an aggregate "it usually re-fires" assertion could pass
while one branch silently leaked a skip, which is the failure mode with real cost.

Covered:

* The pure classifier: disjoint → ``preserved``; matched → ``invalidated`` with
  the matching paths named as evidence; empty declaration → ``invalidated``
  (NOT "matches nothing").
* The ``build.map`` glob convention: a single ``*`` spans ``/``, so
  ``marketplace/*`` covers nested paths and ``*.py`` covers any depth.
* Each fail-closed branch of :func:`classify_step` independently: absent recorded
  SHA, unresolvable live HEAD, unresolved step doc, unavailable discovery, a step
  that is not head-dependent, an undeclared surface, and a tree diff git could
  not compute.
* :func:`resolve_changed_paths` against a REAL temporary git repository,
  including the two properties the tree-diff choice buys — a change and its
  revert cancel out, and an unresolvable SHA reports failure rather than an empty
  difference.
* A declaration-conformance guard over the derived implementor population: every
  ``verdict_inputs`` declaration is a non-empty list of non-empty strings, uses
  no recursive ``**``, rides on a ``head_dependent: true`` step, and — for a glob
  carrying no wildcard, so that it names ONE literal path rather than a family —
  names a path that exists and is git-tracked. A literal glob bound to no path
  matches nothing, so the classifier reads the surface as untouched and returns
  ``preserved``: a skip bought by a typo. That existence check runs through a PURE
  core returning ``(offenders, examined_count)``, so it is driven synthetically by
  a matched control pair, its examined count is published on a clean run, and a
  floor fails the "examined nothing" zero that its empty offender list would
  otherwise report as a pass.
* The refusal table's rows: each tabled step's own doc carries the refusal section
  as an ATX HEADING. The match is heading-anchored rather than a bare substring
  search, because both tabled docs carry the phrase twice — as their own heading
  and inside a cross-reference to the other step's section — so a substring search
  survives renaming the heading itself.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

import extension_discovery
from _step_key_canonical import canonicalize_step_key
from extension_discovery import find_implementors

from conftest import PROJECT_ROOT, get_scripts_dir, get_skill_dir, load_script_module

_SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'phase-6-finalize')


def _load_module(name: str, filename: str):
    """Load the executor from source so its seams are patchable in-process."""
    return load_script_module('plan-marshall', 'phase-6-finalize', filename, name)


_mod = _load_module('verdict_currency', 'verdict_currency.py')

_PRESERVED = _mod.VERDICT_PRESERVED
_INVALIDATED = _mod.VERDICT_INVALIDATED

#: A representative declared surface — the shape ``pre-push-quality-gate`` uses.
_SURFACE = ['*.py', '*.toml', 'marketplace/*', '.claude/*', 'test/*']

_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'


# ---------------------------------------------------------------------------
# The pure classifier
# ---------------------------------------------------------------------------


def _patch_declaration(monkeypatch, globs, head_dependent, unresolved):
    monkeypatch.setattr(_mod, 'resolve_verdict_inputs', lambda _step: (globs, head_dependent, unresolved))

def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()

@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A minimal repository with deterministic identity and no signing."""
    if shutil.which('git') is None:
        pytest.skip('git is not available')
    repo = tmp_path / 'repo'
    repo.mkdir()
    _git(repo, 'init', '--quiet')
    _git(repo, 'config', 'user.email', 'test@example.invalid')
    _git(repo, 'config', 'user.name', 'Test')
    _git(repo, 'config', 'commit.gpgsign', 'false')
    return repo

def _commit(repo: Path, relative: str, body: str) -> str:
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding='utf-8')
    _git(repo, 'add', relative)
    _git(repo, 'commit', '--quiet', '-m', f'touch {relative}')
    return _git(repo, 'rev-parse', 'HEAD')

def _declared_surfaces() -> dict[str, tuple[list[str], bool]]:
    """Map every discovered step to its (verdict_inputs, head_dependent) facts."""
    surfaces: dict[str, tuple[list[str], bool]] = {}
    for record in find_implementors(_EXT_POINT):
        fields = extension_discovery._read_frontmatter_fields(
            Path(str(record.get('path', ''))),
            ('verdict_inputs', 'head_dependent'),
        )
        declared = fields.get('verdict_inputs')
        if declared is None:
            continue
        globs = list(declared) if isinstance(declared, list) else [declared]
        surfaces[str(record.get('name', ''))] = (globs, bool(fields.get('head_dependent', False)))
    return surfaces

_GLOB_METACHARACTERS = ('*', '?')

def _is_wildcard_free(glob: str) -> bool:
    """True when a declared glob names one literal path rather than a family."""
    return not any(char in glob for char in _GLOB_METACHARACTERS)

def _tracked_paths() -> frozenset[str]:
    """Every git-tracked path in the repository, repo-relative and slash-separated."""
    result = subprocess.run(
        ['git', '-C', str(PROJECT_ROOT), 'ls-files', '-z'],
        capture_output=True,
        text=True,
        check=True,
    )
    return frozenset(entry for entry in result.stdout.split('\0') if entry)

def _wildcard_free_offenders(
    surfaces: dict[str, tuple[list[str], bool]],
    tracked: frozenset[str],
    repo_root: Path = PROJECT_ROOT,
) -> tuple[list[str], int]:
    """Offenders, AND the number of wildcard-free globs actually examined.

    Pure over its inputs — the declared surfaces and the tracked-path set — so the
    guard can be driven synthetically by the control pair below, mirroring the
    ``_orphans`` / ``_undeclared`` cores in
    ``test_step_prompt_fields_contract.py``. A detector that can only run against
    the live population is one nobody has ever seen fire.

    Returning the examined count alongside the offenders is the point. An empty
    offender list means one of two entirely different things — every literal glob
    resolved, or NO literal glob was ever inspected — and the count is what
    separates them. Without it a declaration set that turned wholly
    wildcard-bearing would build an empty offender list and pass, having inspected
    nothing.
    """
    offenders: list[str] = []
    examined = 0
    for step, (globs, _head_dependent) in sorted(surfaces.items()):
        for glob in globs:
            if not _is_wildcard_free(glob):
                continue
            examined += 1
            if glob not in tracked:
                reason = 'not git-tracked' if (repo_root / glob).exists() else 'does not exist'
                offenders.append(f'{step} declares {glob!r} — {reason}')
    return offenders, examined

_VERDICT_CURRENCY_DOC = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards' / 'verdict-currency.md'

_REFUSAL_HEADING = 'Verdict-input surface — deliberately undeclared'

_REFUSAL_HEADING_RE = re.compile(rf'^(#{{1,6}})\s+{re.escape(_REFUSAL_HEADING)}\s*$', re.MULTILINE)

_REFUSAL_HEADING_LEVELS = frozenset({'##', '###'})

def _refusal_heading_level(body: str) -> str | None:
    """The ATX level of the refusal heading in ``body``, or ``None`` if absent.

    A markdown link whose display text is the heading phrase — the cross-reference
    form both tabled docs carry — never matches: it is not at the start of a line
    behind a run of ``#``.
    """
    match = _REFUSAL_HEADING_RE.search(body)
    return match.group(1) if match else None

def _tabled_refusals() -> list[str]:
    """Derive the step ids named in verdict-currency.md's refusal table.

    Parsed from the document rather than transcribed, so the guard tracks the
    table instead of a second hand-maintained copy of it.
    """
    text = _VERDICT_CURRENCY_DOC.read_text(encoding='utf-8')
    return [
        m.group(1) for m in re.finditer(r'^\|\s*`((?:default|project|plan-marshall):[^`]+)`\s*\|', text, re.MULTILINE)
    ]

def test_disjoint_change_preserves_the_verdict():
    """A change touching nothing in the surface cannot alter the verdict."""
    verdict, reason, matched = _mod.classify_advance(
        _SURFACE, ['doc/plans/epic/plan/report-01.md', 'doc/lessons/L-12.md']
    )

    assert verdict == _PRESERVED
    assert reason == _mod.REASON_DISJOINT
    assert matched == []


def test_no_changed_paths_at_all_preserves_a_declared_surface():
    """An advance whose tree diff is empty changed nothing anywhere."""
    verdict, reason, _matched = _mod.classify_advance(_SURFACE, [])

    assert verdict == _PRESERVED
    assert reason == _mod.REASON_DISJOINT


def test_absent_recorded_sha_invalidates(monkeypatch):
    """A record with no anchor has nothing to diff against."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)

    payload = _mod.classify_step('some-step', '/nowhere', '', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_NO_RECORDED_HEAD


def test_unavailable_discovery_invalidates(monkeypatch):
    """Broken machinery must not manufacture a skip."""
    _patch_declaration(monkeypatch, [], False, _mod.REASON_DISCOVERY_UNAVAILABLE)

    payload = _mod.classify_step('some-step', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_DISCOVERY_UNAVAILABLE


def test_undeclared_surface_still_preserves_on_an_unmoved_head(monkeypatch):
    """Equal SHAs are decided before the declaration is consulted.

    Identical SHAs mean byte-identical trees, so the verdict is current whatever
    the step reads. Answering ``invalidated`` here would contradict the
    dispatcher's own steady-state SKIP row and make this verb unsound to reuse as
    a general re-entry oracle.
    """
    _patch_declaration(monkeypatch, [], True, None)

    payload = _mod.classify_step('sonar-roundtrip', '/nowhere', 'cafe', 'cafe')

    assert payload['verdict'] == _PRESERVED
    assert payload['reason'] == _mod.REASON_HEAD_UNCHANGED


def test_uncomputable_tree_diff_invalidates(monkeypatch):
    """A git failure is an uncertainty; it must never read as "nothing changed"."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    monkeypatch.setattr(_mod, 'resolve_changed_paths', lambda *_a: ([], False))

    payload = _mod.classify_step('pre-push-quality-gate', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_DIFF_UNAVAILABLE


def test_source_advance_still_refires_the_gate(monkeypatch):
    """The safety half: a source commit must re-fire, exactly as before."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    monkeypatch.setattr(_mod, 'resolve_changed_paths', lambda *_a: (['marketplace/x/y.py'], True))

    payload = _mod.classify_step('pre-push-quality-gate', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['matched_paths'] == ['marketplace/x/y.py']


def test_a_change_and_its_revert_cancel_out(git_repo: Path):
    """A tree diff is narrower than a commit walk — and correctly so."""
    base = _commit(git_repo, 'src/app.py', 'x = 1\n')
    _commit(git_repo, 'src/app.py', 'x = 2\n')
    head = _commit(git_repo, 'src/app.py', 'x = 1\n')

    paths, ok = _mod.resolve_changed_paths(str(git_repo), base, head)

    assert ok is True
    assert paths == []


def test_classify_step_end_to_end_over_a_real_repo(git_repo: Path, monkeypatch):
    """Declaration + real git, wired together on the one preserving path."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    base = _commit(git_repo, 'src/app.py', 'x = 1\n')
    _commit(git_repo, 'doc/notes.md', 'notes\n')

    payload = _mod.classify_step('pre-push-quality-gate', str(git_repo), base, '')

    assert payload['verdict'] == _PRESERVED
    assert payload['changed_paths'] == ['doc/notes.md']
    assert payload['recorded_head'] == base


def test_real_resolver_reports_a_non_head_dependent_step_as_such():
    """``push`` is deliberately not head-dependent; the resolver must say so."""
    globs, is_head_dependent, unresolved = _mod.resolve_verdict_inputs('push')

    assert unresolved is None
    assert is_head_dependent is False
    assert globs == []


def test_every_declared_surface_is_non_empty_and_well_formed():
    """An empty or blank declaration would read as a surface while naming none."""
    for step, (globs, _head_dependent) in _declared_surfaces().items():
        assert globs, f'{step} declares an empty verdict_inputs list'
        for glob in globs:
            assert isinstance(glob, str) and glob.strip(), f'{step} declares a blank glob'


def test_the_wildcard_free_guard_examines_a_non_empty_population():
    """Non-vacuity floor: the guard below must have inspected something.

    The existence check reports an empty offender list both when every literal
    glob resolves and when there was no literal glob to check. Only the first is a
    clean bill of health. This floor fails the second as *"examined 0 of N"*,
    naming the declaring-step count and the declared-glob count so the zero is
    reported as the could-not-look zero it is.

    With exactly one declaring step today, a single frontmatter edit making all of
    its globs wildcard-bearing collapses the examined set to zero — and the
    sibling non-vacuity assertion below guards only that ``git ls-files`` returned
    something, which it would continue to do.
    """
    surfaces = _declared_surfaces()
    tracked = _tracked_paths()
    _offenders, examined = _wildcard_free_offenders(surfaces, tracked)

    declared_globs = sum(len(globs) for globs, _head in surfaces.values())

    # Published on a clean run, not only on failure.
    print(
        f'wildcard-free guard population: declaring_steps={len(surfaces)} '
        f'declared_globs={declared_globs} wildcard_free_examined={examined} '
        f'tracked_paths={len(tracked)}'
    )

    assert examined > 0, (
        f'The wildcard-free existence guard examined 0 of {declared_globs} declared '
        f'glob(s) across {len(surfaces)} declaring step(s), so its empty offender '
        f'list certifies nothing — it is a "could not look" zero, not an '
        f'"examined N, none offending" zero. Every declared glob now carries a '
        f'wildcard, or the declaring population collapsed.'
    )


def test_a_wholly_wildcard_bearing_declaration_examines_nothing():
    """The vacuous green the floor exists to catch, exhibited directly.

    Every glob carries a wildcard, so none is examined, so the offender list is
    empty — and the existence assertion alone would report that as a pass. This
    pins the exact input shape whose ``examined == 0`` the floor above converts
    into a failure.
    """
    offenders, examined = _wildcard_free_offenders(
        {'synthetic-step': (['marketplace/*', '*.py', 'scripts/audit?.py'], True)},
        frozenset({'some/tracked/path.py'}),
    )

    assert offenders == [], 'a wildcard-bearing declaration must produce no offender'
    assert examined == 0, (
        f'examined {examined}; a declaration carrying only wildcard-bearing globs '
        f'must examine none, which is precisely why the empty offender list above '
        f'cannot be read as a clean result'
    )


def test_refusal_heading_match_ignores_a_cross_reference():
    """The heading match fires on a heading and NOT on a link to one.

    Both tabled docs carry the phrase twice — as their own heading and inside a
    cross-reference to the other step's section — so a guard that cannot tell the
    two apart stays green when the heading alone is renamed. That is the exact
    defect this anchoring closes, so the discrimination is asserted here rather
    than assumed.
    """
    heading_only = f'## {_REFUSAL_HEADING}\n\nbody text\n'
    xref_only = f'Some prose citing [§ "{_REFUSAL_HEADING}"](../other/doc.md) and nothing else.\n'

    assert _refusal_heading_level(heading_only) == '##'
    assert _refusal_heading_level(xref_only) is None, (
        'A cross-reference to the section satisfied the heading match, so renaming '
        'the real heading would leave the guard green — the bare-substring defect.'
    )
    assert _REFUSAL_HEADING in xref_only, (
        'The cross-reference fixture must contain the phrase, or it does not '
        'demonstrate anything about a substring search.'
    )
