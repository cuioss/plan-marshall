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

A second sweep covers the host-interpreter spelling of a ``marketplace/targets/``
script. That form is not forbidden outright, because the stdlib-only harness sync
engine is prescribed that way on purpose: each such prescription is decided by
running the script it names where ``yaml`` is unimportable, so a script that
needs the project environment is still refused.

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

import textwrap
from pathlib import Path

from _documented_example_scan import (
    BARE_PYTHON_TARGETS_PREFIX,
    DEFECTIVE_GENERATOR_CALL,
    WRAPPER_GENERATOR_CALL,
)
from conftest import PROJECT_ROOT, run_clean_python_subprocess

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
    :data:`BARE_PYTHON_TARGETS_PREFIX`: a prescription is a line the reader
    copies and therefore begins with the command, while an explanatory mention is
    introduced by a backtick or by sentence text. Shared by the sweep and by its
    positive control so the two cannot diverge.
    """
    return [line for line in text.splitlines() if line.strip().startswith(BARE_PYTHON_TARGETS_PREFIX)]


def _prescribed_script(line: str) -> str:
    """The repository-relative script path a bare prescription line names."""
    return line.strip().split()[1]


#: Child program for :func:`_bare_run_failure`. It makes ``yaml`` unimportable —
#: reproducing a host interpreter with no project virtualenv — and then runs the
#: script named by ``sys.argv[1]`` as ``__main__`` with ``--help``. ``sys.path[0]``
#: is set to the script's directory, as the interpreter itself does for
#: ``python3 path/to/script.py``, so the child resolves imports exactly as the
#: prescribed command would and not through the working directory.
_BARE_HELP_PROBE = textwrap.dedent(
    """
    import os
    import runpy
    import sys


    class _Blocker:
        def find_spec(self, fullname, path=None, target=None):
            if fullname == 'yaml' or fullname.startswith('yaml.'):
                raise ModuleNotFoundError(f'No module named {fullname!r}', name=fullname)
            return None


    sys.meta_path.insert(0, _Blocker())
    script = sys.argv[1]
    sys.path[0] = os.path.dirname(script)
    sys.argv = [script, '--help']
    try:
        runpy.run_path(script, run_name='__main__')
    except SystemExit as exc:
        print('bare_exit=' + str(exc.code))
    """
)


def _bare_run_failure(script: Path) -> str | None:
    """Return why ``script --help`` fails on a bare interpreter, else ``None``.

    ``--help`` is enough to decide the question this guard asks: a script that
    cannot run on the host interpreter dies on a module-level import, before its
    argument parser is built.
    """
    if not script.is_file():
        return 'names no script file'
    result = run_clean_python_subprocess(['-c', _BARE_HELP_PROBE, script], text=True, timeout=60)
    if result.returncode == 0 and 'bare_exit=0' in result.stdout:
        return None
    stderr_lines = result.stderr.strip().splitlines()
    return stderr_lines[-1] if stderr_lines else f'exited {result.returncode} without --help succeeding'


def test_the_bare_python_detector_fires_on_a_constructed_prescription():
    """Positive control: the detector matches the form the sweep must examine.

    A tree in which every prescription happens to name a runnable script cannot
    show that the needle still matches anything, so the control is CONSTRUCTED
    from the shared constant. It is built by concatenation and never re-spelled,
    so this file stays outside its own sweep.
    """
    prescription = f'{BARE_PYTHON_TARGETS_PREFIX}claude/content_drift_cli.py'

    assert _lines_prescribing_bare_python_targets(prescription) == [prescription], (
        'the detector no longer matches a bare prescription line — the sweep below '
        'would pass over a tree that reintroduced the defect'
    )
    assert _lines_prescribing_bare_python_targets(f'  {prescription}') == [f'  {prescription}'], (
        'an indented prescription (inside a fenced block) must still match'
    )
    assert not _lines_prescribing_bare_python_targets(f'A bare `{prescription}` fails because …'), (
        'an explanatory prose mention must NOT match — examining it would make the '
        'repaired sites unable to say which form is broken'
    )
    assert _prescribed_script(f'  {prescription} --check') == 'marketplace/targets/claude/content_drift_cli.py'


def test_the_bare_run_probe_rejects_a_script_that_imports_the_targets_package():
    """Positive control for the probe: it refuses the script the defect shipped with.

    ``content_drift_cli.py`` imports ``marketplace.targets`` and so needs
    ``yaml``. If the probe accepted it, the sweep below would accept every
    prescription and guard nothing.
    """
    failure = _bare_run_failure(PROJECT_ROOT / 'marketplace' / 'targets' / 'claude' / 'content_drift_cli.py')

    assert failure is not None, 'the probe ran a yaml-dependent script on a bare interpreter'
    assert 'yaml' in failure


def test_every_bare_python_targets_prescription_names_a_script_that_runs_bare():
    """A targets script prescribed on the host interpreter actually runs there.

    A script that imports ``marketplace.targets`` dies on ``PyYAML`` under a host
    interpreter, so prescribing it bare hands the reader a command that fails;
    it belongs behind its ``./pw`` alias. A stdlib-only script does run bare, and
    the harness sync engine is prescribed that way on purpose. The sweep
    therefore decides each prescription by running the script it names where
    ``yaml`` is unimportable, rather than by forbidding the form.
    """
    files, labels = _walk_scanned_files()
    assert files, f'the walk over {labels} read no files at all'

    prescribers: dict[str, list[str]] = {}
    for path in files:
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for line in _lines_prescribing_bare_python_targets(text):
            prescribers.setdefault(_prescribed_script(line), []).append(path.relative_to(PROJECT_ROOT).as_posix())

    failures = {script: _bare_run_failure(PROJECT_ROOT / script) for script in sorted(prescribers)}
    offenders = [
        f'{script} ({failure}) — prescribed by {", ".join(sorted(set(prescribers[script])))}'
        for script, failure in failures.items()
        if failure is not None
    ]

    assert not offenders, (
        f'{len(offenders)} of {len(failures)} marketplace/targets script(s) prescribed on the host '
        f'interpreter across {len(files)} files in {labels} do not run there — use the ./pw wrapper '
        f'alias for a script that needs the project environment:\n  ' + '\n  '.join(offenders)
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
