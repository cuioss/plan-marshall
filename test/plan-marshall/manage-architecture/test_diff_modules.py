#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``diff-modules`` reader verb in ``_cmd_client.py``.

Pins the four-bucket classification contract (added/removed/changed/unchanged)
of ``cmd_diff_modules``, its ``snapshot_not_found`` / ``invalid_ref`` error
contract, the ``--pre-ref`` baseline read (parity with ``--pre`` and the archive
member refusals), and the argparse wiring on ``architecture.py``.

Under the on-demand crawl model the snapshot side still reads
``derived.json`` files from disk (snapshots remain file-based) while the
current side hashes the canonical JSON of a fresh ``crawl_module_derived``
call.
For test fixtures, ``save_module_derived`` is used to seed the on-disk
fallback that ``crawl_all_modules`` consults when the extension discovery
pipeline returns no modules (typical for tmp project trees with no real
build files). The fixtures intentionally write under the project tree so
both the snapshot copy and the current-side fallback see the same
payload before any mutation.

The comparison surface is intentionally narrow — only derived shas
matter; differences in ``enriched.json`` never produce a ``changed``
classification.
"""

import argparse
import copy
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import pytest

from conftest import load_script_module, parse_ns

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')
_architecture = load_script_module('plan-marshall', 'manage-architecture', 'architecture.py', 'architecture')
_handlers = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_handlers.py', '_cmd_client_handlers'
)

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
save_module_enriched = _architecture_core.save_module_enriched
get_data_dir = _architecture_core.get_data_dir
cmd_diff_modules = _cmd_client.cmd_diff_modules

#: The architecture script's address, as module-level string constants so the
#: ``parse_ns`` call below stays statically resolvable.
_ARCH_BUNDLE = 'plan-marshall'
_ARCH_SKILL = 'manage-architecture'
_ARCH_SCRIPT = 'architecture.py'


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from the hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because a namespace's values
    are the parser's own scalars, and the base must stay unmutated for the other
    callers sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: The ``diff-modules`` namespace, built by ``architecture.py``'s OWN parser so
#: it carries every default the production CLI applies — the ``command``
#: discriminator and the ``plan_id`` half of the ``--plan-id``/``--project-dir``
#: pair among them, neither of which the hand-built namespaces carried. Hoisted
#: to module scope because ``parse_ns`` re-executes the script module on every
#: call, and ``register=False`` so it cannot displace the ``architecture``
#: registration this module performs above.
_DIFF_MODULES_ARGS = parse_ns(
    _ARCH_BUNDLE,
    _ARCH_SKILL,
    _ARCH_SCRIPT,
    '--project-dir',
    '.',
    'diff-modules',
    '--pre',
    '.',
    register=False,
)


# =============================================================================
# Fixture helpers
# =============================================================================


def _seed_project(project_dir: str, modules: dict[str, dict]) -> None:
    """Write ``_project.json`` plus per-module ``derived.json`` files."""
    save_project_meta(
        {
            'name': 'diff-modules-test',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        project_dir,
    )
    for name, derived in modules.items():
        save_module_derived(name, derived, project_dir)


def _snapshot_data_dir(project_dir: str, snapshot_root: str) -> Path:
    """Copy the live ``project-architecture/`` tree into ``snapshot_root``.

    Returns the snapshot directory containing ``_project.json`` directly.
    """
    src = get_data_dir(project_dir)
    dst = Path(snapshot_root) / 'project-architecture'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def _make_module(name: str) -> dict:
    return {
        'name': name,
        'build_systems': ['python'],
        'paths': {'module': name},
        'commands': {},
    }


# =============================================================================
# Bucket classification
# =============================================================================


def test_unchanged_tree_classifies_every_module_as_unchanged():
    """When snapshot equals current, all modules land in ``unchanged``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a'), 'mod-b': _make_module('mod-b')})

        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        result = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['added'] == []
        assert result['removed'] == []
        assert result['changed'] == []
        assert result['unchanged'] == ['mod-a', 'mod-b']


def test_byte_modified_derived_classifies_as_changed():
    """A single module's ``derived.json`` byte-modified between snapshot and current → ``changed``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a'), 'mod-b': _make_module('mod-b')})
        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        # Mutate mod-b's derived.json in the live tree (simulating a re-discover).
        save_module_derived('mod-b', {**_make_module('mod-b'), 'note': 'mutated'}, str(project))

        result = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['added'] == []
        assert result['removed'] == []
        assert result['changed'] == ['mod-b']
        assert result['unchanged'] == ['mod-a']


def test_added_module_classifies_as_added():
    """A module present in current but not in snapshot → ``added``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})
        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        # Add mod-new to the live tree, re-write _project.json index.
        _seed_project(
            str(project),
            {'mod-a': _make_module('mod-a'), 'mod-new': _make_module('mod-new')},
        )

        result = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['added'] == ['mod-new']
        assert result['removed'] == []
        assert result['changed'] == []
        assert result['unchanged'] == ['mod-a']


def test_removed_module_classifies_as_removed():
    """A module present in snapshot but not in current → ``removed``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(
            str(project),
            {'mod-a': _make_module('mod-a'), 'mod-gone': _make_module('mod-gone')},
        )
        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        # Remove mod-gone from the live tree by re-writing only mod-a.
        shutil.rmtree(get_data_dir(str(project)))
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})

        result = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['added'] == []
        assert result['removed'] == ['mod-gone']
        assert result['changed'] == []
        assert result['unchanged'] == ['mod-a']


# =============================================================================
# Error contract
# =============================================================================


def test_missing_snapshot_directory_returns_snapshot_not_found():
    """A non-existent ``--pre`` path returns ``error: snapshot_not_found``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})

        missing = Path(tmp) / 'no-such-snapshot'

        result = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=str(missing)))

        assert result['status'] == 'error'
        assert result['error'] == 'snapshot_not_found'
        assert result['path'] == str(missing)


def test_snapshot_dir_present_but_project_meta_missing_returns_error():
    """An existing directory without ``_project.json`` is also ``snapshot_not_found``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})

        # Create the snapshot directory but do not populate it with _project.json.
        empty_snapshot = Path(tmp) / 'empty-snapshot'
        empty_snapshot.mkdir()

        result = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=str(empty_snapshot)))

        assert result['status'] == 'error'
        assert result['error'] == 'snapshot_not_found'
        assert result['path'] == str(empty_snapshot)


# =============================================================================
# Comparison surface — derived-only
# =============================================================================


def test_enriched_only_diff_does_not_produce_changed():
    """A diff confined to ``enriched.json`` does NOT classify the module as changed."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})
        # Seed an initial enriched.json on both sides.
        save_module_enriched('mod-a', {'responsibility': 'before'}, str(project))
        snapshot_dir = _snapshot_data_dir(str(project), tmp)

        # Mutate ONLY enriched.json on the current side.
        save_module_enriched('mod-a', {'responsibility': 'after'}, str(project))

        result = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=str(snapshot_dir)))

        assert result['status'] == 'success'
        assert result['changed'] == []
        assert result['unchanged'] == ['mod-a']


# =============================================================================
# --pre-ref baselines
# =============================================================================


def _git(repo: Path, *argv: str) -> str:
    completed = subprocess.run(
        [
            'git',
            '-c',
            'user.name=test',
            '-c',
            'user.email=test@example.com',
            '-c',
            'commit.gpgsign=false',
            '-C',
            str(repo),
            *argv,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def _commit_tree(project: Path) -> None:
    _git(project, 'init', '-q')
    # ``-f``: a machine-level ignore rule for ``.plan/`` must not empty the baseline.
    _git(project, 'add', '-f', '-A')
    _git(project, 'commit', '-q', '-m', 'baseline')


def test_pre_ref_matches_pre_on_the_same_baseline():
    """The committed tree read by ref classifies exactly as the same tree read from disk."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a'), 'mod-b': _make_module('mod-b')})
        snapshot_dir = _snapshot_data_dir(str(project), tmp)
        _commit_tree(project)
        save_module_derived('mod-b', {**_make_module('mod-b'), 'note': 'mutated'}, str(project))

        by_path = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=str(snapshot_dir)))
        by_ref = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=None, pre_ref='HEAD'))

        assert by_path['changed'] == ['mod-b'], 'the fixture no longer produces a non-trivial diff'
        assert by_ref == by_path


def test_pre_ref_lacking_the_tree_is_snapshot_not_found():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        (project / 'README.md').write_text('no descriptor tree committed\n', encoding='utf-8')
        _commit_tree(project)
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})

        result = cmd_diff_modules(_variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=None, pre_ref='HEAD'))

        assert result['status'] == 'error'
        assert result['error'] == 'snapshot_not_found'
        assert result['ref'] == 'HEAD'
        assert 'path' not in result


def test_dash_prefixed_ref_is_refused_as_invalid_ref():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed_project(str(project), {'mod-a': _make_module('mod-a')})

        result = cmd_diff_modules(
            _variant(_DIFF_MODULES_ARGS, project_dir=str(project), pre=None, pre_ref='-o/tmp/evil')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_ref'
        assert result['ref'] == '-o/tmp/evil'


def _tar_bytes(*members: tuple[tarfile.TarInfo, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as tar:
        for info, content in members:
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content) if info.isfile() else None)
    return buffer.getvalue()


def _file(name: str) -> tuple[tarfile.TarInfo, bytes]:
    return tarfile.TarInfo(name), b'{}'


def _symlink(name: str, target: str) -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name)
    info.type = tarfile.SYMTYPE
    info.linkname = target
    return info, b''


def test_archive_extraction_writes_regular_members():
    """Positive control for the refusals below: a clean archive extracts."""
    with tempfile.TemporaryDirectory() as tmp:
        _handlers._extract_archive(_tar_bytes(_file('.plan/project-architecture/_project.json')), Path(tmp))

        assert (Path(tmp) / '.plan' / 'project-architecture' / '_project.json').read_bytes() == b'{}'


@pytest.mark.parametrize(
    'member',
    [
        _file('../escaped.json'),
        _file('/absolute.json'),
        _symlink('.plan/project-architecture/_project.json', '/etc/passwd'),
    ],
    ids=['parent-component', 'absolute', 'symlink'],
)
def test_archive_extraction_refuses_unsafe_members(member):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'root'
        root.mkdir()

        with pytest.raises(_handlers._UnsafeArchiveMemberError):
            _handlers._extract_archive(_tar_bytes(member), root)

        assert list(root.rglob('*')) == []
        assert not (Path(tmp) / 'escaped.json').exists()


# =============================================================================
# Argparse wiring
# =============================================================================


def test_argparse_registers_diff_modules_subcommand():
    """``architecture diff-modules --pre <path>`` is a registered subcommand.

    Drives ``architecture.main()`` in-process with a patched ``sys.argv`` of
    ``['architecture.py', 'diff-modules', '--help']`` under captured stdout so
    the assertion exercises the real argparse wiring (no interpreter
    cold-start). The top-level ``--help`` presence of ``diff-modules`` is
    asserted authoritatively in
    ``test_cmd_client.py::test_architecture_help_registers_all_subcommands`` —
    this test owns only the subcommand-level ``--pre`` / ``--pre-ref`` flag check.
    """
    import contextlib
    import io

    buf = io.StringIO()
    saved_argv = sys.argv
    sys.argv = ['architecture.py', 'diff-modules', '--help']
    try:
        with contextlib.redirect_stdout(buf):
            _architecture.main()
    except SystemExit as exc:
        assert exc.code in (0, None), f'diff-modules --help exited non-zero: {exc.code}'
    finally:
        sys.argv = saved_argv

    assert '--pre' in buf.getvalue()
    assert '--pre-ref' in buf.getvalue()


def test_pre_and_pre_ref_are_mutually_exclusive_and_one_is_required():
    base = (_ARCH_BUNDLE, _ARCH_SKILL, _ARCH_SCRIPT, 'diff-modules')
    assert parse_ns(*base, '--pre-ref', 'origin/main', register=False).pre_ref == 'origin/main'
    with pytest.raises(SystemExit):
        parse_ns(*base, '--pre', '.', '--pre-ref', 'HEAD', register=False)
    with pytest.raises(SystemExit):
        parse_ns(*base, register=False)
