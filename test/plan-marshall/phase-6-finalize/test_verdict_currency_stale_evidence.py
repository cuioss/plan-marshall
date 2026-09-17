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

def test_matched_change_invalidates_and_names_its_evidence():
    """A re-fire is substantiated by the paths that caused it, not asserted."""
    verdict, reason, matched = _mod.classify_advance(
        _SURFACE,
        ['doc/lessons/L-12.md', 'marketplace/bundles/plan-marshall/skills/x/SKILL.md'],
    )

    assert verdict == _INVALIDATED
    assert reason == _mod.REASON_MATCHED
    assert matched == ['marketplace/bundles/plan-marshall/skills/x/SKILL.md']


@pytest.mark.parametrize(
    ('glob', 'path'),
    [
        ('marketplace/*', 'marketplace/bundles/plan-marshall/skills/x/scripts/y.py'),
        ('*.py', 'marketplace/bundles/a/b/c/deep.py'),
        ('*.py', 'top_level.py'),
        ('.claude/*', '.claude/skills/finalize-step-plugin-doctor/SKILL.md'),
        ('test/*', 'test/plan-marshall/phase-6-finalize/fixture.json'),
    ],
)
def test_single_star_glob_spans_path_separators(glob: str, path: str):
    """The build.map convention: one ``*`` crosses ``/``, so no ``**`` is needed."""
    verdict, _reason, matched = _mod.classify_advance([glob], [path])

    assert verdict == _INVALIDATED
    assert matched == [path]


def test_unresolvable_live_head_invalidates(monkeypatch):
    """A HEAD git cannot report is an uncertainty, not a match."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    monkeypatch.setattr(_mod, 'resolve_live_head', lambda _path: '')

    payload = _mod.classify_step('some-step', '/nowhere', 'cafe', '')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_DIFF_UNAVAILABLE


def test_non_head_dependent_step_invalidates(monkeypatch):
    """This classifier is not the re-entry authority for such a step."""
    _patch_declaration(monkeypatch, _SURFACE, False, None)

    payload = _mod.classify_step('push', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_NOT_HEAD_DEPENDENT


def test_equal_shas_preserve_even_when_resolution_is_impossible(monkeypatch):
    """The equal-SHA path consults NOTHING — the module docstring's promise.

    Placed after the resolution gate, this case would answer ``invalidated``
    whenever discovery hiccuped on an unmoved HEAD: a re-fire manufactured by a
    broken lookup rather than by any change to the tree. Identical SHAs are
    identical trees, so no verdict about that tree can be stale against it, and
    the answer must hold with the declaration unresolvable.
    """

    def _explode(_step):
        raise AssertionError('resolve_verdict_inputs must not run on equal SHAs')

    monkeypatch.setattr(_mod, 'resolve_verdict_inputs', _explode)

    payload = _mod.classify_step('any-step', '/nowhere', 'cafe', 'cafe')

    assert payload['verdict'] == _PRESERVED
    assert payload['reason'] == _mod.REASON_HEAD_UNCHANGED
    assert payload['verdict_inputs'] == []


def test_equal_shas_short_circuit_without_a_diff(monkeypatch):
    """The steady-state row needs no git call at all."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)

    def _explode(*_args):
        raise AssertionError('resolve_changed_paths must not run on equal SHAs')

    monkeypatch.setattr(_mod, 'resolve_changed_paths', _explode)

    payload = _mod.classify_step('pre-push-quality-gate', '/nowhere', 'cafe', 'cafe')

    assert payload['verdict'] == _PRESERVED
    assert payload['reason'] == _mod.REASON_HEAD_UNCHANGED


def test_every_reason_token_carries_a_detail_phrasing():
    """The dispatcher logs ``detail``; a reason with no phrasing would log a token."""
    tokens = [value for name, value in vars(_mod).items() if name.startswith('REASON_') and isinstance(value, str)]

    assert tokens
    for token in tokens:
        assert token in _mod._REASON_DETAIL, f'reason {token!r} has no detail phrasing'


def test_unresolvable_sha_reports_failure_not_an_empty_difference(git_repo: Path):
    """The distinction the fail-closed contract depends on."""
    head = _commit(git_repo, 'src/app.py', 'x = 1\n')

    paths, ok = _mod.resolve_changed_paths(str(git_repo), '0' * 40, head)

    assert ok is False
    assert paths == []


def test_at_least_one_step_declares_a_verdict_input_surface():
    """A conformance guard over an empty population is vacuously green."""
    assert _declared_surfaces(), 'no finalize step declares verdict_inputs'


def test_real_resolver_reports_an_unknown_step_as_unresolved():
    """An unrecognised key must fail closed, not resolve to an empty surface."""
    _globs, _head_dependent, unresolved = _mod.resolve_verdict_inputs('no-such-finalize-step')

    assert unresolved == _mod.REASON_STEP_UNRESOLVED


def test_no_declared_glob_uses_recursive_double_star():
    """The build.map convention: single ``*`` spans ``/``, so ``**`` is never needed."""
    for step, (globs, _head_dependent) in _declared_surfaces().items():
        for glob in globs:
            assert '**' not in glob, f'{step} declares a recursive glob {glob!r}'


def test_every_wildcard_free_declared_glob_names_a_tracked_path():
    """A literal ``verdict_inputs`` glob must name a path that exists and is tracked.

    The sibling conformance guards pin non-emptiness, well-formedness,
    ``head_dependent`` companionship and the no-``**`` rule — none of which notices
    a glob bound to no path at all. A wildcard-free declaration that names a moved
    or deleted file silently matches nothing, so the classifier reads "the tree
    difference touches none of my surface" and returns ``preserved``: the step's
    stale verdict is kept on the strength of a surface that does not exist. That is
    a skip bought by a typo.

    Wildcard-bearing globs are exempt because they legitimately name a family that
    may be empty right now; only a declaration claiming ONE literal path is held to
    that path existing.

    The examined count is published with the verdict, and its floor is asserted
    separately above, so a green here always states how much it looked at.
    """
    tracked = _tracked_paths()
    assert tracked, 'git ls-files returned nothing, so this guard would be vacuous'

    offenders, examined = _wildcard_free_offenders(_declared_surfaces(), tracked)

    assert not offenders, (
        f'These steps declare a wildcard-free verdict_inputs glob that names no '
        f'git-tracked path, so the glob matches nothing and the classifier would '
        f'return `preserved` on a surface that is not there (examined {examined} '
        f'wildcard-free glob(s) against {len(tracked)} tracked paths): {offenders}'
    )


def test_the_refusal_table_names_at_least_one_step():
    """A guard over an empty table would be vacuously green."""
    assert _tabled_refusals(), 'verdict-currency.md names no refusing step'


def test_no_tabled_refusal_also_declares_a_surface():
    """A step cannot both refuse and declare — the two are mutually exclusive."""
    declared = {canonicalize_step_key(name) for name in _declared_surfaces()}

    for step in _tabled_refusals():
        assert canonicalize_step_key(step) not in declared, (
            f'{step} is tabled as refusing to declare a verdict surface, yet it declares one.'
        )
