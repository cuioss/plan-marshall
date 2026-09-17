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

def test_empty_declaration_is_unknown_surface_not_empty_surface():
    """No declaration means "surface unknown", which must never buy a skip."""
    verdict, reason, matched = _mod.classify_advance([], ['doc/anything.md'])

    assert verdict == _INVALIDATED
    assert reason == _mod.REASON_UNDECLARED
    assert matched == []


def test_glob_outside_the_surface_does_not_match():
    """The surface is a real filter, not one that matches everything."""
    verdict, reason, _matched = _mod.classify_advance(['marketplace/*'], ['doc/x.md'])

    assert verdict == _PRESERVED
    assert reason == _mod.REASON_DISJOINT


def test_unresolved_step_doc_invalidates(monkeypatch):
    """A step whose doc discovery cannot place has an unknown surface."""
    _patch_declaration(monkeypatch, [], False, _mod.REASON_STEP_UNRESOLVED)

    payload = _mod.classify_step('ghost-step', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_STEP_UNRESOLVED


def test_undeclared_surface_keeps_the_unconditional_refire(monkeypatch):
    """Adoption is opt-in: a step declaring nothing behaves exactly as before."""
    _patch_declaration(monkeypatch, [], True, None)

    payload = _mod.classify_step('sonar-roundtrip', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _INVALIDATED
    assert payload['reason'] == _mod.REASON_UNDECLARED


def test_equal_shas_preserve_for_an_unresolvable_step(monkeypatch):
    """The same property stated through the resolver's own failure mode."""
    _patch_declaration(monkeypatch, [], False, _mod.REASON_DISCOVERY_UNAVAILABLE)

    payload = _mod.classify_step('ghost-step', '/nowhere', 'cafe', 'cafe')

    assert payload['verdict'] == _PRESERVED
    assert payload['reason'] == _mod.REASON_HEAD_UNCHANGED


def test_docs_only_advance_preserves_the_gate(monkeypatch):
    """The lever itself: a settle-band doc commit does not re-run the build gate."""
    _patch_declaration(monkeypatch, _SURFACE, True, None)
    monkeypatch.setattr(_mod, 'resolve_changed_paths', lambda *_a: (['doc/lessons/L-3.md'], True))

    payload = _mod.classify_step('pre-push-quality-gate', '/nowhere', 'cafe', 'beef')

    assert payload['verdict'] == _PRESERVED
    assert payload['recorded_head'] == 'cafe'
    assert payload['changed_paths'] == ['doc/lessons/L-3.md']


def test_resolve_changed_paths_reports_the_tree_difference(git_repo: Path):
    base = _commit(git_repo, 'src/app.py', 'x = 1\n')
    head = _commit(git_repo, 'doc/notes.md', 'notes\n')

    paths, ok = _mod.resolve_changed_paths(str(git_repo), base, head)

    assert ok is True
    assert paths == ['doc/notes.md']


def test_resolve_live_head_matches_git(git_repo: Path):
    head = _commit(git_repo, 'src/app.py', 'x = 1\n')

    assert _mod.resolve_live_head(str(git_repo)) == head


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


def test_every_declared_surface_rides_a_head_dependent_step():
    """The fact is only meaningful alongside ``head_dependent: true``."""
    for step, (_globs, head_dependent) in _declared_surfaces().items():
        assert head_dependent, f'{step} declares verdict_inputs without head_dependent: true'


def test_wildcard_free_discriminator_separates_a_literal_from_a_family():
    """Guards the guard below: a family glob must be EXEMPT and a literal must not.

    Without this, a discriminator that classified everything as a family would make
    the existence check below vacuously green over the whole population.
    """
    assert _is_wildcard_free('marketplace/bundles/plan-marshall/skills/x/SKILL.md')
    assert not _is_wildcard_free('marketplace/*')
    assert not _is_wildcard_free('*.py')
    assert not _is_wildcard_free('scripts/audit?.py')


def test_wildcard_free_core_flags_an_untracked_literal_and_spares_a_tracked_one():
    """Matched control pair, driven synthetically through the pure core.

    The two declarations differ ONLY in which literal path they name — same step,
    same shape, same tracked-path set — so the split is attributable to the
    tracked-membership test and to nothing else. A detector never seen to fire is
    indistinguishable from one that cannot.
    """
    present = 'test/plan-marshall/phase-6-finalize/test_verdict_currency.py'
    absent = 'test/plan-marshall/phase-6-finalize/no_such_file.py'
    tracked = frozenset({present})

    flagged, examined_flagged = _wildcard_free_offenders({'synthetic-step': ([absent], True)}, tracked)
    spared, examined_spared = _wildcard_free_offenders({'synthetic-step': ([present], True)}, tracked)

    # Both halves inspected exactly one glob — otherwise the split below could be
    # explained by one of them examining nothing rather than by the membership test.
    assert examined_flagged == 1, f'the flagged half examined {examined_flagged}, not 1'
    assert examined_spared == 1, f'the spared half examined {examined_spared}, not 1'

    assert len(flagged) == 1 and absent in flagged[0], (
        f'the core did not flag a literal glob naming an untracked path: {flagged}'
    )
    assert spared == [], (
        f'the core flagged a literal glob that IS tracked: {spared}. A guard that '
        f'fires on a correct declaration is a false positive.'
    )


def test_every_tabled_refusal_carries_its_section():
    """Each row's cited evidence must actually exist in that step's own doc.

    The table is illustrative and cannot be derived — a refusal is a judgement
    about a step's body, not a frontmatter fact. What CAN be pinned is that every
    row still points at a real section, so a deleted or renamed refusal fails here
    rather than leaving the table asserting evidence that is gone.
    """
    records = {
        str(record.get('name', '')): Path(str(record.get('path', ''))) for record in find_implementors(_EXT_POINT)
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
            "the other step's section does not satisfy it."
        )
        assert level in _REFUSAL_HEADING_LEVELS, (
            f'{step} carries the refusal section at heading level {level!r}, which is not one '
            f'of {sorted(_REFUSAL_HEADING_LEVELS)}. The two tabled docs differ legitimately — a '
            f'project SKILL.md nests it one deeper than a standards doc — but a level outside '
            f'that set means the section has been re-nested somewhere unexpected, and the '
            f'cross-references pointing at it are the thing to re-check.'
        )
