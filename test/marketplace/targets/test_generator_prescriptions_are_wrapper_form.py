#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""No file in the tree prescribes the generator invocation that exits 127.

The generator was prescribed throughout the tree — bundle sources, developer
guides, READMEs, repository-root instruction files and project-local skills alike
— every occurrence naming a command that fails from a normal shell, because
``uv`` is installed only into the project-local ``.pyprojectx/`` tree. Repairing
the sites that happened to be discovered would leave the rest live, so this guard
makes the repair durable: reintroducing the broken form anywhere in the scanned
roots fails the suite.

**The repaired population is not enumerated here.** This guard derives its scope
by walking :data:`_SCAN_ROOTS`, and a list of sites copied into prose is a second,
unmaintained count that drifts from that walk the moment a site is added. What the
guard covers is what it publishes at runtime, below.

**The guard publishes the roots it walked and the number of files it read.** A
walk that resolves nothing reports no offenders, which is indistinguishable from
a clean tree unless the size is asserted on its own. Both numbers are checked
before the offender assertion, not merely mentioned in its message.

**Generated output under ``target/`` is out of the walk by construction**, and
that is a recorded decision rather than an accident of the root list: it is a
build artifact regenerated from the sources this guard already covers, so a stale
copy there is a signal to re-emit, not a prescription anyone reads. Parallel
worktrees under ``.claude/worktrees/`` are excluded for the same structural
reason ruff excludes them — they are isolated checkouts of other in-flight
branches and contribute nothing to this branch's tree.
"""

from __future__ import annotations

from pathlib import Path

from _documented_example_scan import (
    DEFECTIVE_BARE_PYTHON_TARGETS_PREFIX,
    DEFECTIVE_GENERATOR_CALL,
    WRAPPER_GENERATOR_CALL,
)
from conftest import PROJECT_ROOT

#: The tracked source roots the guard walks, as ``(label, relative path)``.
#: Repository-root documents are covered by :data:`_ROOT_FILE_SUFFIXES` below
#: rather than by a root entry, because walking the repository root itself would
#: descend into every gitignored build directory.
_SCAN_ROOTS: tuple[tuple[str, str], ...] = (
    ('marketplace', 'marketplace'),
    ('doc', 'doc'),
    ('test', 'test'),
    ('claude-local', '.claude'),
)

#: Suffixes read during the walk. A prescription is text a human copies, so
#: binaries and caches carry none.
_TEXT_SUFFIXES = frozenset({'.md', '.adoc', '.py', '.toml', '.txt', '.sh', '.json', '.yml', '.yaml'})

#: Suffixes of the repository-root documents, which are scanned individually.
#: ``.toml`` is included deliberately: the repository-root ``.pr_agent.toml`` is a
#: GENERATED but COMMITTED reviewer configuration whose header carries a
#: regenerate command, so it is a prescription site like any document.
_ROOT_FILE_SUFFIXES = frozenset({'.md', '.adoc', '.toml'})

#: Directory names never descended into. Matched against each path's segments
#: RELATIVE to its scan root, never against the absolute path: a checkout can
#: itself live under a directory carrying one of these names — a plan worktree
#: lives under ``.plan/local/worktrees/`` — and an absolute match would then skip
#: every file in the tree and report the resulting silence as a clean guard.
_SKIPPED_DIRS = frozenset({'__pycache__', '.git', 'node_modules', 'target', 'worktrees'})

#: EXCLUSION 1 — the pyprojectx alias table. The literal is the alias BODY here,
#: which is exactly where it belongs and is correct as written: ``./pw generate``
#: is the alias that runs it. Rewriting this file would break the wrapper the
#: whole repair depends on.
_ALIAS_DEFINITION = 'pyproject.toml'

#: EXCLUSION 2 — the shared module that DEFINES the forbidden literal. A guard
#: cannot forbid a string it must itself name; centralising the spelling in that
#: one module lets this sweep exempt the definition site instead of exempting
#: every guard module by name as guards are added.
_LITERAL_DEFINITION = 'test/_shared/_documented_example_scan.py'

#: Both exclusions, each a DEFINITION SITE rather than an unfixed defect. Stated
#: as one named set so widening it requires an explicit edit with a reason beside
#: it — a guard quietly widened is a guard turned vacuous.
_EXCLUDED_PATHS: tuple[str, ...] = (_ALIAS_DEFINITION, _LITERAL_DEFINITION)


def _walk_scanned_files() -> tuple[list[Path], list[str]]:
    """Return ``(files read, root labels walked)``.

    Both halves are the guard's published population: the label list says WHERE
    it looked, and the file list says how much it actually read. A root that
    resolves to nothing still contributes its label, so a mistyped root shows up
    as a label with no files rather than vanishing.
    """
    files: list[Path] = []
    labels: list[str] = []

    for label, relative in _SCAN_ROOTS:
        labels.append(label)
        root = PROJECT_ROOT / relative
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            if any(part in _SKIPPED_DIRS for part in path.relative_to(root).parts):
                continue
            if path.is_file() and not path.is_symlink() and path.suffix in _TEXT_SUFFIXES:
                files.append(path)

    labels.append('repository-root documents')
    for path in sorted(PROJECT_ROOT.glob('*')):
        if path.is_file() and not path.is_symlink() and path.suffix in _ROOT_FILE_SUFFIXES:
            files.append(path)

    excluded = {(PROJECT_ROOT / relative).resolve() for relative in _EXCLUDED_PATHS}
    return [path for path in files if path.resolve() not in excluded], labels


def test_guard_walks_a_non_empty_population_over_every_declared_root():
    """The walk resolves files, and it resolves them under every declared root.

    Asserted before the offender sweep and separately from it: a walk that
    reached nothing reports no offenders, and that is the one failure the sweep
    itself can never surface.
    """
    files, labels = _walk_scanned_files()

    assert labels == [label for label, _ in _SCAN_ROOTS] + ['repository-root documents'], (
        'the published root list must name every declared root'
    )
    assert len(files) > 0, f'the walk over {labels} read no files at all — the guard is vacuous'

    per_root = {
        label: sum(1 for path in files if str(path).startswith(str(PROJECT_ROOT / relative)))
        for label, relative in _SCAN_ROOTS
    }
    empty = sorted(label for label, count in per_root.items() if count == 0)
    assert not empty, (
        f'{len(empty)} declared root(s) contributed no files to the {len(files)}-file walk: '
        f'{", ".join(empty)} — a root that resolves to nothing guards nothing'
    )


def test_no_file_prescribes_the_bare_generator_invocation():
    """The repaired prescriptions stay repaired, everywhere the guard can see."""
    files, labels = _walk_scanned_files()
    assert files, f'the walk over {labels} read no files at all'

    offenders: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        if DEFECTIVE_GENERATOR_CALL in text:
            offenders.append(path.relative_to(PROJECT_ROOT).as_posix())

    assert not offenders, (
        f'{len(offenders)} file(s) of {len(files)} scanned across {labels} prescribe the bare '
        f'generator invocation, which exits 127 outside the wrapper — use '
        f'{WRAPPER_GENERATOR_CALL!r}:\n  ' + '\n  '.join(sorted(offenders))
    )


def _lines_prescribing_bare_python_targets(text: str) -> list[str]:
    """Lines that OPEN with the host-interpreter invocation of a targets script.

    Prefix-matched after stripping, per the discriminator documented beside
    :data:`DEFECTIVE_BARE_PYTHON_TARGETS_PREFIX`: a prescription is a line the
    reader copies and therefore begins with the command, while an explanatory
    mention is introduced by a backtick or by sentence text. Shared by the sweep
    and by its positive control so the two cannot diverge.
    """
    return [
        line
        for line in text.splitlines()
        if line.strip().startswith(DEFECTIVE_BARE_PYTHON_TARGETS_PREFIX)
    ]


def test_the_bare_python_detector_fires_on_a_constructed_prescription():
    """Positive control: the detector matches the form it is meant to forbid.

    The sweep below passes over a clean tree, and a clean tree cannot show that
    the needle still matches anything — the failure mode the sibling literal
    answers with ``pyproject.toml`` as a real matched site. This literal has no
    such site, because the one prescription that carried it was repaired rather
    than exempted, so the control is CONSTRUCTED from the shared constant. It is
    built by concatenation and never re-spelled, so this file stays outside its
    own sweep.
    """
    prescription = f'{DEFECTIVE_BARE_PYTHON_TARGETS_PREFIX}claude/content_drift_cli.py'

    assert _lines_prescribing_bare_python_targets(prescription) == [prescription], (
        'the detector no longer matches a bare prescription line — the sweep below '
        'would pass over a tree that reintroduced the defect'
    )
    assert _lines_prescribing_bare_python_targets(f'  {prescription}') == [f'  {prescription}'], (
        'an indented prescription (inside a fenced block) must still match'
    )
    assert not _lines_prescribing_bare_python_targets(f'A bare `{prescription}` fails because …'), (
        'an explanatory prose mention must NOT match — forbidding it would make the '
        'repaired sites unable to say which form is broken'
    )


def test_no_file_prescribes_the_bare_python_targets_invocation():
    """No document hands the reader a targets script on the host interpreter.

    The sibling sweep above forbids the ``uv run`` spelling; the shared constant's
    docstring already noted that dropping that prefix fails on ``PyYAML`` instead,
    but nothing enforced it — and the unenforced half is exactly the one that
    shipped in the steward upgrade flow. Same walk, same population, second
    literal.
    """
    files, labels = _walk_scanned_files()
    assert files, f'the walk over {labels} read no files at all'

    offenders: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        if _lines_prescribing_bare_python_targets(text):
            offenders.append(path.relative_to(PROJECT_ROOT).as_posix())

    assert not offenders, (
        f'{len(offenders)} file(s) of {len(files)} scanned across {labels} prescribe a '
        f'marketplace/targets script on the host interpreter, which dies on the project '
        f'PyYAML dependency before running — use the ./pw wrapper alias:\n  '
        + '\n  '.join(sorted(offenders))
    )


def test_the_alias_definition_still_carries_the_literal_and_is_excluded():
    """The matched negative control: the sweep would find the literal if it looked.

    ``pyproject.toml`` holds the alias BODY, so the literal is correct there and
    the file is excluded. Pinning that it still contains the literal is what
    proves the sweep above passes because the tree is clean, not because the
    needle stopped matching anything at all.
    """
    alias_table = (PROJECT_ROOT / _ALIAS_DEFINITION).read_text(encoding='utf-8')
    assert DEFECTIVE_GENERATOR_CALL in alias_table, (
        f'{_ALIAS_DEFINITION} no longer carries the alias body this guard excludes — either the '
        f'alias moved, or the literal this guard searches for is no longer the one in use'
    )

    files, _ = _walk_scanned_files()
    scanned = {path.relative_to(PROJECT_ROOT).as_posix() for path in files}
    for relative in _EXCLUDED_PATHS:
        assert relative not in scanned, f'{relative} is a declared exclusion but was scanned'


def test_every_declared_exclusion_exists():
    """A declared exclusion names a real file.

    An exclusion whose path went stale silently stops excluding anything, which
    would make the guard fail on the next unrelated rename rather than on a real
    defect — and would hide that one of its two named reasons no longer applies.
    """
    missing = [relative for relative in _EXCLUDED_PATHS if not (PROJECT_ROOT / relative).is_file()]
    assert not missing, f'declared exclusion(s) name no file: {", ".join(missing)}'
