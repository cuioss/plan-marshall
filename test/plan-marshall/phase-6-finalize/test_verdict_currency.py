#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
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
  ``preserved``: a skip bought by a typo.
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

from conftest import get_scripts_dir, load_script_module  # noqa: E402
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


def test_disjoint_change_preserves_the_verdict():
    """A change touching nothing in the surface cannot alter the verdict."""
    verdict, reason, matched = _mod.classify_advance(
        _SURFACE, ['doc/plans/epic/plan/report-01.md', 'doc/lessons/L-12.md']
    )

    assert verdict == _PRESERVED
    assert reason == _mod.REASON_DISJOINT
    assert matched == []


def test_matched_change_invalidates_and_names_its_evidence():
    """A re-fire is substantiated by the paths that caused it, not asserted."""
    verdict, reason, matched = _mod.classify_advance(
        _SURFACE,
        ['doc/lessons/L-12.md', 'marketplace/bundles/plan-marshall/skills/x/SKILL.md'],
    )

    assert verdict == _INVALIDATED
    assert reason == _mod.REASON_MATCHED
    assert matched == ['marketplace/bundles/plan-marshall/skills/x/SKILL.md']


def test_empty_declaration_is_unknown_surface_not_empty_surface():
    """No declaration means "surface unknown", which must never buy a skip."""
    verdict, reason, matched = _mod.classify_advance([], ['doc/anything.md'])

    assert verdict == _INVALIDATED
    assert reason == _mod.REASON_UNDECLARED
    assert matched == []


def test_no_changed_paths_at_all_preserves_a_declared_surface():
    """An advance whose tree diff is empty changed nothing anywhere."""
    verdict, reason, _matched = _mod.classify_advance(_SURFACE, [])

    assert verdict == _PRESERVED
    assert reason == _mod.REASON_DISJOINT


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


def test_glob_outside_the_surface_does_not_match():
    """The surface is a real filter, not one that matches everything."""
    verdict, reason, _matched = _mod.classify_advance(['marketplace/*'], ['doc/x.md'])

    assert verdict == _PRESERVED
    assert reason == _mod.REASON_DISJOINT


# ---------------------------------------------------------------------------
# Fail-closed branches of classify_step — asserted one at a time
# ---------------------------------------------------------------------------


def _patch_declaration(monkeypatch, globs, head_dependent, unresolved):
    monkeypatch.setattr(
        _mod, 'resolve_verdict_inputs', lambda _step: (globs, head_dependent, unresolved)
    )


def test_absent_recorded_sha_invalidates(monkeypatch):
    """A record with no anchor has nothing to diff against."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)

    payload = _mod.classify_step('some-step', '/nowhere', '', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_NO_RECORDED_HEAD


def test_unresolvable_live_head_invalidates(monkeypatch):
    """A HEAD git cannot report is an uncertainty, not a match."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    monkeypatch.setattr(_mod, 'resolve_live_head', lambda _path: '')

    payload = _mod.classify_step('some-step', '/nowhere', 'cafe', '')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_DIFF_UNAVAILABLE


def test_unresolved_step_doc_invalidates(monkeypatch):
    """A step whose doc discovery cannot place has an unknown surface."""
    _patch_declaration(monkeypatch, [], False, _mod.REASON_STEP_UNRESOLVED)

    payload = _mod.classify_step('ghost-step', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_STEP_UNRESOLVED


def test_unavailable_discovery_invalidates(monkeypatch):
    """Broken machinery must not manufacture a skip."""
    _patch_declaration(monkeypatch, [], False, _mod.REASON_DISCOVERY_UNAVAILABLE)

    payload = _mod.classify_step('some-step', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_DISCOVERY_UNAVAILABLE


def test_non_head_dependent_step_invalidates(monkeypatch):
    """This classifier is not the re-entry authority for such a step."""
    _patch_declaration(monkeypatch, _SURFACE, False, None)

    payload = _mod.classify_step('push', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_NOT_HEAD_DEPENDENT


def test_undeclared_surface_keeps_the_unconditional_refire(monkeypatch):
    """Adoption is opt-in: a step declaring nothing behaves exactly as before."""
    _patch_declaration(monkeypatch, [], True, None)

    payload = _mod.classify_step('sonar-roundtrip', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_UNDECLARED


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


def test_equal_shas_preserve_for_an_unresolvable_step(monkeypatch):
    """The same property stated through the resolver's own failure mode."""
    _patch_declaration(monkeypatch, [], False, _mod.REASON_DISCOVERY_UNAVAILABLE)

    payload = _mod.classify_step('ghost-step', '/nowhere', 'cafe', 'cafe')

    assert payload['verdict'] == _PRESERVED
    assert payload['reason'] == _mod.REASON_HEAD_UNCHANGED


def test_uncomputable_tree_diff_invalidates(monkeypatch):
    """A git failure is an uncertainty; it must never read as "nothing changed"."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    monkeypatch.setattr(_mod, 'resolve_changed_paths', lambda *_a: ([], False))

    payload = _mod.classify_step('pre-push-quality-gate', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_DIFF_UNAVAILABLE


def test_equal_shas_short_circuit_without_a_diff(monkeypatch):
    """The steady-state row needs no git call at all."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)

    def _explode(*_args):
        raise AssertionError('resolve_changed_paths must not run on equal SHAs')

    monkeypatch.setattr(_mod, 'resolve_changed_paths', _explode)

    payload = _mod.classify_step('pre-push-quality-gate', '/nowhere', 'cafe', 'cafe')

    assert payload['verdict'] == _PRESERVED
    assert payload['reason'] == _mod.REASON_HEAD_UNCHANGED


def test_docs_only_advance_preserves_the_gate(monkeypatch):
    """The lever itself: a settle-band doc commit does not re-run the build gate."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    monkeypatch.setattr(
        _mod, 'resolve_changed_paths', lambda *_a: (['doc/lessons/L-3.md'], True)
    )

    payload = _mod.classify_step('pre-push-quality-gate', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _PRESERVED
    assert payload['recorded_head'] == 'cafe'
    assert payload['changed_paths'] == ['doc/lessons/L-3.md']


def test_source_advance_still_refires_the_gate(monkeypatch):
    """The safety half: a source commit must re-fire, exactly as before."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    monkeypatch.setattr(
        _mod, 'resolve_changed_paths', lambda *_a: (['marketplace/x/y.py'], True)
    )

    payload = _mod.classify_step('pre-push-quality-gate', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['matched_paths'] == ['marketplace/x/y.py']


def test_every_reason_token_carries_a_detail_phrasing():
    """The dispatcher logs ``detail``; a reason with no phrasing would log a token."""
    tokens = [
        value
        for name, value in vars(_mod).items()
        if name.startswith('REASON_') and isinstance(value, str)
    ]

    assert tokens
    for token in tokens:
        assert token in _mod._REASON_DETAIL, f'reason {token!r} has no detail phrasing'


# ---------------------------------------------------------------------------
# resolve_changed_paths against a real git repository
# ---------------------------------------------------------------------------


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


def test_resolve_changed_paths_reports_the_tree_difference(git_repo: Path):
    base = _commit(git_repo, 'src/app.py', 'x = 1\n')
    head = _commit(git_repo, 'doc/notes.md', 'notes\n')

    paths, ok = _mod.resolve_changed_paths(str(git_repo), base, head)

    assert ok is True
    assert paths == ['doc/notes.md']


def test_a_change_and_its_revert_cancel_out(git_repo: Path):
    """A tree diff is narrower than a commit walk — and correctly so."""
    base = _commit(git_repo, 'src/app.py', 'x = 1\n')
    _commit(git_repo, 'src/app.py', 'x = 2\n')
    head = _commit(git_repo, 'src/app.py', 'x = 1\n')

    paths, ok = _mod.resolve_changed_paths(str(git_repo), base, head)

    assert ok is True
    assert paths == []


def test_unresolvable_sha_reports_failure_not_an_empty_difference(git_repo: Path):
    """The distinction the fail-closed contract depends on."""
    head = _commit(git_repo, 'src/app.py', 'x = 1\n')

    paths, ok = _mod.resolve_changed_paths(str(git_repo), '0' * 40, head)

    assert ok is False
    assert paths == []


def test_resolve_live_head_matches_git(git_repo: Path):
    head = _commit(git_repo, 'src/app.py', 'x = 1\n')

    assert _mod.resolve_live_head(str(git_repo)) == head


def test_classify_step_end_to_end_over_a_real_repo(git_repo: Path, monkeypatch):
    """Declaration + real git, wired together on the one preserving path."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    base = _commit(git_repo, 'src/app.py', 'x = 1\n')
    _commit(git_repo, 'doc/notes.md', 'notes\n')

    payload = _mod.classify_step('pre-push-quality-gate', str(git_repo), base, '')

    assert payload['verdict'] == _PRESERVED
    assert payload['changed_paths'] == ['doc/notes.md']
    assert payload['recorded_head'] == base


# ---------------------------------------------------------------------------
# Declaration conformance over the derived implementor population
# ---------------------------------------------------------------------------


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


def test_at_least_one_step_declares_a_verdict_input_surface():
    """A conformance guard over an empty population is vacuously green."""
    assert _declared_surfaces(), 'no finalize step declares verdict_inputs'


def test_real_resolver_reads_a_declared_surface_off_the_live_population():
    """The resolution seam itself, unpatched — the riskiest part of the wiring.

    Every ``classify_step`` test above patches ``resolve_verdict_inputs``, so none
    of them exercises the discovery lookup or the ``canonicalize_step_key``
    matching that bridges discovery's name to the key the dispatcher holds. A
    rename or an alias change there would break the feature silently while every
    patched test stayed green.

    This test covers whichever prefix forms the live declaring population happens
    to carry; the sibling ``push`` test below covers the ``default:``-prefixed
    bridge unconditionally, since discovery names that step ``default:push`` while
    the dispatcher holds the bare key.
    """
    declared = _declared_surfaces()
    assert declared, 'no finalize step declares verdict_inputs'

    for discovery_name, (expected_globs, _head_dependent) in declared.items():
        # The dispatcher holds the CANONICAL key, not discovery's spelling.
        canonical = canonicalize_step_key(discovery_name)
        globs, is_head_dependent, unresolved = _mod.resolve_verdict_inputs(canonical)

        assert unresolved is None, f'{canonical} did not resolve: {unresolved}'
        assert is_head_dependent, f'{canonical} resolved as not head-dependent'
        assert globs == expected_globs, f'{canonical} resolved a different surface'


def test_real_resolver_reports_a_non_head_dependent_step_as_such():
    """``push`` is deliberately not head-dependent; the resolver must say so."""
    globs, is_head_dependent, unresolved = _mod.resolve_verdict_inputs('push')

    assert unresolved is None
    assert is_head_dependent is False
    assert globs == []


def test_real_resolver_reports_an_unknown_step_as_unresolved():
    """An unrecognised key must fail closed, not resolve to an empty surface."""
    _globs, _head_dependent, unresolved = _mod.resolve_verdict_inputs('no-such-finalize-step')

    assert unresolved == _mod.REASON_STEP_UNRESOLVED


def test_every_declared_surface_rides_a_head_dependent_step():
    """The fact is only meaningful alongside ``head_dependent: true``."""
    for step, (_globs, head_dependent) in _declared_surfaces().items():
        assert head_dependent, f'{step} declares verdict_inputs without head_dependent: true'


def test_every_declared_surface_is_non_empty_and_well_formed():
    """An empty or blank declaration would read as a surface while naming none."""
    for step, (globs, _head_dependent) in _declared_surfaces().items():
        assert globs, f'{step} declares an empty verdict_inputs list'
        for glob in globs:
            assert isinstance(glob, str) and glob.strip(), f'{step} declares a blank glob'


def test_no_declared_glob_uses_recursive_double_star():
    """The build.map convention: single ``*`` spans ``/``, so ``**`` is never needed."""
    for step, (globs, _head_dependent) in _declared_surfaces().items():
        for glob in globs:
            assert '**' not in glob, f'{step} declares a recursive glob {glob!r}'


#: The repository root — the base every declared glob is resolved against. Derived
#: from this module's own position in the tree (``test/{bundle}/{skill}/``), so it
#: is a property of the checkout layout rather than of the machine.
_REPO_ROOT = Path(__file__).parents[3]

#: The glob metacharacters whose presence means a declaration legitimately names a
#: FAMILY of paths rather than one path. A declaration carrying neither names a
#: single literal path, which can therefore be required to exist.
_GLOB_METACHARACTERS = ('*', '?')


def _is_wildcard_free(glob: str) -> bool:
    """True when a declared glob names one literal path rather than a family."""
    return not any(char in glob for char in _GLOB_METACHARACTERS)


def _tracked_paths() -> frozenset[str]:
    """Every git-tracked path in the repository, repo-relative and slash-separated."""
    result = subprocess.run(
        ['git', '-C', str(_REPO_ROOT), 'ls-files', '-z'],
        capture_output=True,
        text=True,
        check=True,
    )
    return frozenset(entry for entry in result.stdout.split('\0') if entry)


def test_wildcard_free_discriminator_separates_a_literal_from_a_family():
    """Guards the guard below: a family glob must be EXEMPT and a literal must not.

    Without this, a discriminator that classified everything as a family would make
    the existence check below vacuously green over the whole population.
    """
    assert _is_wildcard_free('marketplace/bundles/plan-marshall/skills/x/SKILL.md')
    assert not _is_wildcard_free('marketplace/*')
    assert not _is_wildcard_free('*.py')
    assert not _is_wildcard_free('scripts/audit?.py')


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
    """
    tracked = _tracked_paths()
    assert tracked, 'git ls-files returned nothing, so this guard would be vacuous'

    offenders = []
    for step, (globs, _head_dependent) in _declared_surfaces().items():
        for glob in globs:
            if not _is_wildcard_free(glob):
                continue
            if glob not in tracked:
                reason = 'not git-tracked' if (_REPO_ROOT / glob).exists() else 'does not exist'
                offenders.append(f'{step} declares {glob!r} — {reason}')

    assert not offenders, (
        'These steps declare a wildcard-free verdict_inputs glob that names no '
        'git-tracked path, so the glob matches nothing and the classifier would '
        f'return `preserved` on a surface that is not there: {offenders}'
    )


# ---------------------------------------------------------------------------
# The refusal table's rows are bound to their evidence
# ---------------------------------------------------------------------------

_VERDICT_CURRENCY_DOC = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'verdict-currency.md'
)

#: The heading each refusing step's own doc must carry.
_REFUSAL_HEADING = 'Verdict-input surface — deliberately undeclared'

#: The heading MATCH, anchored to an ATX heading line rather than searched as a
#: bare substring. Both tabled steps carry the phrase TWICE — once as their own
#: heading and once inside a cross-reference to the other step's section — so a
#: substring search over the whole doc stays green when the heading itself is
#: renamed and only the cross-reference survives. The captured group is the
#: heading level, reported in the assertion message.
_REFUSAL_HEADING_RE = re.compile(
    rf'^(#{{1,6}})\s+{re.escape(_REFUSAL_HEADING)}\s*$', re.MULTILINE
)


#: The ATX levels the refusal section legitimately appears at. A project-local
#: SKILL.md nests it under a section heading (``###``); a standards doc carries it
#: as a top-level section (``##``). Pinning the SET rather than a single value keeps
#: the assertion meaningful without forcing both docs into one shape.
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
        m.group(1)
        for m in re.finditer(r'^\|\s*`((?:default|project|plan-marshall):[^`]+)`\s*\|', text, re.MULTILINE)
    ]


def test_the_refusal_table_names_at_least_one_step():
    """A guard over an empty table would be vacuously green."""
    assert _tabled_refusals(), 'verdict-currency.md names no refusing step'


def test_every_tabled_refusal_carries_its_section():
    """Each row's cited evidence must actually exist in that step's own doc.

    The table is illustrative and cannot be derived — a refusal is a judgement
    about a step's body, not a frontmatter fact. What CAN be pinned is that every
    row still points at a real section, so a deleted or renamed refusal fails here
    rather than leaving the table asserting evidence that is gone.
    """
    records = {
        str(record.get('name', '')): Path(str(record.get('path', '')))
        for record in find_implementors(_EXT_POINT)
    }

    for step in _tabled_refusals():
        assert step in records, (
            f'verdict-currency.md tables a refusal for {step!r}, which is not a discovered '
            'finalize-step implementor — the row names a step that does not exist.'
        )
        body = records[step].read_text(encoding='utf-8')
        level = _refusal_heading_level(body)
        assert level is not None, (
            f'{step} is tabled as a recorded refusal but its own doc carries no '
            f'"{_REFUSAL_HEADING}" section. The table would then assert evidence that is not '
            'there — the exact un-propagated-restatement defect it is meant to survive. '
            'The match is anchored to an ATX heading line: a surviving cross-reference to '
            'the other step\'s section does not satisfy it.'
        )
        assert level in _REFUSAL_HEADING_LEVELS, (
            f'{step} carries the refusal section at heading level {level!r}, which is not one '
            f'of {sorted(_REFUSAL_HEADING_LEVELS)}. The two tabled docs differ legitimately — a '
            f'project SKILL.md nests it one deeper than a standards doc — but a level outside '
            f'that set means the section has been re-nested somewhere unexpected, and the '
            f'cross-references pointing at it are the thing to re-check.'
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
    xref_only = (
        'Some prose citing '
        f'[§ "{_REFUSAL_HEADING}"](../other/doc.md) and nothing else.\n'
    )

    assert _refusal_heading_level(heading_only) == '##'
    assert _refusal_heading_level(xref_only) is None, (
        'A cross-reference to the section satisfied the heading match, so renaming '
        'the real heading would leave the guard green — the bare-substring defect.'
    )
    assert _REFUSAL_HEADING in xref_only, (
        'The cross-reference fixture must contain the phrase, or it does not '
        'demonstrate anything about a substring search.'
    )


def test_no_tabled_refusal_also_declares_a_surface():
    """A step cannot both refuse and declare — the two are mutually exclusive."""
    declared = {canonicalize_step_key(name) for name in _declared_surfaces()}

    for step in _tabled_refusals():
        assert canonicalize_step_key(step) not in declared, (
            f'{step} is tabled as refusing to declare a verdict surface, yet it declares one.'
        )
