#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""The ``sync-harnesses`` command is one engine behind three harness-local entry points.

Each harness reads its commands from its own project-local location, so the
command exists as three files: a Claude skill, an OpenCode command and an
Antigravity skill. All three are thin pointers at one engine,
``marketplace/targets/sync.py``, and pass their arguments through to it
unchanged.

Three copies of one command drift unless something holds them together. These
tests pin the parts that must stay identical — the command name, the engine
invocation and the prescribed command sequence — and that no entry point named
after a retired single-harness command sits beside them.

The entry points live under ``.claude/``, ``.opencode/`` and ``.agents/``, which
lie outside the architecture inventory, so they are read by explicit path.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _documented_example_scan import BARE_PYTHON_TARGETS_PREFIX, iter_fenced_blocks
from conftest import PROJECT_ROOT
from marketplace.targets.sync import SYNC_TARGETS

_COMMAND_NAME = 'sync-harnesses'

#: The repository-relative entry point of each harness, keyed by harness name.
#: The mapping is explicit because each harness reads commands from its own
#: location; which harnesses must HAVE an entry point is derived below.
_ENTRY_POINT_PATHS: dict[str, str] = {
    'claude': '.claude/skills/sync-harnesses/SKILL.md',
    'opencode': '.opencode/commands/sync-harnesses.md',
    'antigravity': '.agents/skills/sync-harnesses/SKILL.md',
}

#: ``(harness, repository-relative entry point)`` for every harness the engine
#: syncs, derived from the engine's own ``SYNC_TARGETS`` so a harness added there
#: without an entry point fails here instead of falling outside every check.
_ENTRY_POINTS: tuple[tuple[str, str], ...] = tuple(
    (harness, _ENTRY_POINT_PATHS.get(harness, f'<no entry point declared for {harness}>')) for harness in SYNC_TARGETS
)

#: A ``./pw`` invocation at any shell command boundary: line start, or after a
#: command separator. A prefix test alone would pass ``cd repo && ./pw …``.
_DIRECT_WRAPPER_CALL = re.compile(r'(?:^|[;&|(]\s*)\./pw(?:\s|$)')

#: The entry points that are skills. A skill declares its name in frontmatter; an
#: OpenCode command is named by its file alone.
_SKILL_ENTRY_POINTS: tuple[tuple[str, str], ...] = (
    ('claude', '.claude/skills/sync-harnesses/SKILL.md'),
    ('antigravity', '.agents/skills/sync-harnesses/SKILL.md'),
)

#: The one engine invocation every entry point prescribes. Built from the shared
#: prefix constant so this module never opens a line with the invocation itself.
_ENGINE_INVOCATION = f'{BARE_PYTHON_TARGETS_PREFIX}sync.py $ARGUMENTS'

#: The directories each harness reads its project-local commands from.
_HARNESS_LOCAL_ROOTS: tuple[str, ...] = ('.claude/skills', '.opencode/commands', '.agents/skills')

#: Names of the single-harness commands ``sync-harnesses`` replaces. Matched as
#: whole entry names: the ``finalize-step-sync-plugin-cache`` step keeps its id
#: and is not a retired command.
_RETIRED_NAMES: tuple[str, ...] = ('sync-plugin-cache', 'sync-opencode', 'sync-antigravity')


def _read(relative: str) -> str:
    return (PROJECT_ROOT / relative).read_text(encoding='utf-8')


def _frontmatter(text: str) -> dict[str, str]:
    """The ``key: value`` pairs of the document's leading ``---`` block."""
    lines = text.splitlines()
    closing = lines.index('---', 1)
    pairs = (line.partition(':') for line in lines[1:closing])
    return {key.strip(): value.strip() for key, _, value in pairs}


def _prescribed_commands(text: str) -> list[str]:
    """The command lines of every ``bash`` fence, in document order.

    Only ``bash`` fences are read: a ``text`` fence carries a usage example or a
    diagram, which is not a command the entry point runs.
    """
    return [
        line.strip()
        for block in iter_fenced_blocks(text)
        if block.language == 'bash'
        for line in block.body.splitlines()
        if line.strip()
    ]


def _entry_names(root: Path) -> list[str]:
    """The name of every entry directly under ``root``, extension dropped."""
    return sorted(entry.stem for entry in root.iterdir())


def _retired_entries(root: Path) -> list[str]:
    """The entries directly under ``root`` named exactly after a retired command."""
    return sorted(set(_entry_names(root)) & set(_RETIRED_NAMES))


@pytest.mark.parametrize(('harness', 'relative'), _ENTRY_POINTS, ids=[harness for harness, _ in _ENTRY_POINTS])
def test_entry_point_exists_under_the_command_name(harness: str, relative: str):
    """Every harness carries an entry point whose location names ``sync-harnesses``."""
    named_location = relative.removesuffix('/SKILL.md').removesuffix('.md')

    assert (PROJECT_ROOT / relative).is_file(), f'the {harness} entry point {relative} should exist'
    assert named_location.endswith(f'/{_COMMAND_NAME}'), (
        f'the {harness} entry point {relative} should be named {_COMMAND_NAME}'
    )


@pytest.mark.parametrize(
    ('harness', 'relative'), _SKILL_ENTRY_POINTS, ids=[harness for harness, _ in _SKILL_ENTRY_POINTS]
)
def test_skill_entry_point_declares_the_command_name(harness: str, relative: str):
    """A skill entry point declares ``sync-harnesses`` as its frontmatter name."""
    frontmatter = _frontmatter(_read(relative))

    assert frontmatter['name'] == _COMMAND_NAME, f'the {harness} skill {relative} should declare name {_COMMAND_NAME}'


@pytest.mark.parametrize(('harness', 'relative'), _ENTRY_POINTS, ids=[harness for harness, _ in _ENTRY_POINTS])
def test_entry_point_description_is_harness_neutral(harness: str, relative: str):
    """The description names no single harness's install location.

    The command syncs every harness, so a description worded around the Claude
    plugin cache would misstate what running it does.
    """
    description = _frontmatter(_read(relative))['description']

    assert description, f'the {harness} entry point {relative} should carry a description'
    assert 'plugin cache' not in description.casefold(), (
        f'the {harness} entry point description should be harness-neutral, got: {description}'
    )


@pytest.mark.parametrize(('harness', 'relative'), _ENTRY_POINTS, ids=[harness for harness, _ in _ENTRY_POINTS])
def test_entry_point_invokes_the_engine_with_arguments_passed_through(harness: str, relative: str):
    """The only sync script an entry point runs is the engine, with ``$ARGUMENTS`` passed through.

    Matching every prescribed line that names a ``sync.py`` — rather than only
    looking for the engine line — is what catches a second, harness-specific
    sync script or a hard-coded ``--target`` appearing beside the engine call.
    """
    sync_calls = [command for command in _prescribed_commands(_read(relative)) if 'sync.py' in command]

    assert sync_calls == [_ENGINE_INVOCATION], (
        f'the {harness} entry point {relative} should prescribe exactly one sync call, the engine '
        f'with arguments passed through, got: {sync_calls}'
    )


@pytest.mark.parametrize(('harness', 'relative'), _ENTRY_POINTS, ids=[harness for harness, _ in _ENTRY_POINTS])
def test_entry_point_prescribes_no_direct_wrapper_call(harness: str, relative: str):
    """No prescribed command runs ``./pw`` directly.

    The enforcement hook denies a direct ``./pw`` call inside a plan context, so
    the regeneration step goes through the build executor instead. The command
    must stay runnable from a plan worktree as well as from the main checkout.
    """
    prescribed = _prescribed_commands(_read(relative))
    assert prescribed, f'no prescribed command resolved from the {harness} entry point {relative}'

    direct = [command for command in prescribed if _DIRECT_WRAPPER_CALL.search(command)]

    assert direct == [], f'the {harness} entry point {relative} prescribes a direct ./pw call: {direct}'


def test_entry_point_map_covers_exactly_the_synced_harnesses():
    """Every harness the engine syncs has an entry point, and no entry point names another."""
    assert set(_ENTRY_POINT_PATHS) == set(SYNC_TARGETS), (
        f'entry points {sorted(_ENTRY_POINT_PATHS)} should match the engine targets {sorted(SYNC_TARGETS)}'
    )


def test_direct_wrapper_detector_matches_at_command_boundaries_only():
    """Matched control for the ``./pw`` check: chained calls count, mentions inside a word do not."""
    assert _DIRECT_WRAPPER_CALL.search('./pw generate-claude')
    assert _DIRECT_WRAPPER_CALL.search('cd repo && ./pw generate-claude')
    assert _DIRECT_WRAPPER_CALL.search('true; ./pw verify')
    assert not _DIRECT_WRAPPER_CALL.search(
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
        '--command-args "generate-claude"'
    )
    assert not _DIRECT_WRAPPER_CALL.search('echo x/./pwd')


def test_every_entry_point_prescribes_the_same_commands():
    """The three entry points prescribe one command sequence, in one order."""
    prescribed = {harness: _prescribed_commands(_read(relative)) for harness, relative in _ENTRY_POINTS}

    assert prescribed['claude'], 'no prescribed command resolved from the claude entry point'
    assert prescribed['opencode'] == prescribed['claude'], (
        'the opencode entry point should prescribe the same commands as the claude one'
    )
    assert prescribed['antigravity'] == prescribed['claude'], (
        'the antigravity entry point should prescribe the same commands as the claude one'
    )


@pytest.mark.parametrize('relative_root', _HARNESS_LOCAL_ROOTS)
def test_no_harness_local_entry_is_named_after_a_retired_command(relative_root: str):
    """No harness-local directory carries an entry named after a retired sync command."""
    root = PROJECT_ROOT / relative_root

    assert _entry_names(root), f'{relative_root} should hold at least one entry — nothing was examined'
    assert _retired_entries(root) == [], (
        f'{relative_root} should carry no entry named after a retired command, found: {_retired_entries(root)}'
    )


def test_retired_name_detector_reports_exact_matches_only(tmp_path: Path):
    """The detector reports a retired file or directory name and nothing that merely contains one.

    The matched control for the sweep above: a detector that stopped matching
    would report a clean tree whatever it held, and one that matched substrings
    would report the kept ``finalize-step-sync-plugin-cache`` step.
    """
    (tmp_path / 'sync-opencode.md').write_text('', encoding='utf-8')
    (tmp_path / 'sync-plugin-cache').mkdir()
    (tmp_path / 'finalize-step-sync-plugin-cache').mkdir()
    (tmp_path / _COMMAND_NAME).mkdir()

    assert _retired_entries(tmp_path) == ['sync-opencode', 'sync-plugin-cache']
