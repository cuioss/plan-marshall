#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PYTHONPATH follows the resolved script's own cached version (PLAN-LB-95).

A deployed plugin cache holds many versions of every bundle, so a helper module
exists once per cached version. The dispatch ``PYTHONPATH`` must carry the
version the script was resolved FROM, and no other: a helper imported from an
older version either lacks a symbol the script needs (``ImportError``) or
silently runs older code. Each case renders the real executor template into a
project whose executor sits outside any marketplace tree, so resolution has to
come from the fixture cache; the generating checkout's own script dirs ride
along last, which is why every fixture module and skill name here is
fixture-only — nothing in the real tree can satisfy these imports by accident.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

ge = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_executor_own_version')

#: Every platform env signal the runtime detector reads.
_SIGNALS = ('CLAUDE_CODE_SESSION_ID', 'OPENCODE', 'ANTIGRAVITY_AGENT')

#: Every env variable that declares an install root at call time. Cleared out of
#: the child's environment so a fixture owns the ONLY root the dispatch can see.
_ROOT_DECLARATIONS = ('OPENCODE_CONFIG_DIR', 'XDG_CONFIG_HOME', 'GEMINI_CONFIG_DIR')

#: The newest cached version in every fixture, and the version the probe runs from.
_NEWEST = '0.1.2010'

#: The cached helper's file and the symbol only the newest version defines. Both
#: are fixture-only names, so no real install can satisfy the import by accident.
_HELPER = 'cached_helper'
_MARKER = 'CACHED_VERSION_MARKER'

_IMPORT_PROBE = (
    f'from {_HELPER} import {_MARKER}\n'
    'import os\n'
    f'print("{_MARKER}=" + {_MARKER})\n'
    'print("PYTHONPATH=" + os.environ.get("PYTHONPATH", ""))\n'
)

_SHOW_PROBE = 'import os\nprint("PYTHONPATH=" + os.environ.get("PYTHONPATH", ""))\n'


def _cached(root: Path, bundle: str, version: str, skill: str, script: str, body: str) -> Path:
    """Write ``{root}/{bundle}/{version}/skills/{skill}/scripts/{script}.py``."""
    path = root / bundle / version / 'skills' / skill / 'scripts' / f'{script}.py'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


def _helper_body(version: str) -> str:
    """The helper as it ships at ``version``: only the newest defines the marker."""
    marker = f"{_MARKER} = '{version}'\n" if version == _NEWEST else ''
    return f"VERSION = '{version}'\n{marker}"


def _generate(monkeypatch: pytest.MonkeyPatch, plan_dir: Path, cache: Path) -> Path:
    """Generate a real executor whose only known install root is ``cache``."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    for signal in _SIGNALS:
        monkeypatch.delenv(signal, raising=False)
    monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', '1')
    monkeypatch.setattr(ge, 'installed_harness_roots', lambda: [('claude', str(cache))])
    monkeypatch.setattr(ge, 'installed_harness_versions', lambda _roots=None: [('claude', _NEWEST)])
    result = ge.generate_executor({}, MARKETPLACE_ROOT, dry_run=False, target='claude')
    assert result['status'] == 'success', result
    executor = plan_dir / 'execute-script.py'
    assert executor.is_file()
    return executor


def _run(executor: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ``executor`` as the claude harness with a hermetic environment."""
    env = {key: value for key, value in os.environ.items() if key not in _SIGNALS + _ROOT_DECLARATIONS}
    env.pop('PYTHONPATH', None)
    env['CLAUDE_CODE_SESSION_ID'] = '1'
    return subprocess.run(
        [sys.executable, str(executor), *args],
        cwd=executor.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _pythonpath(result: subprocess.CompletedProcess[str]) -> list[str]:
    """Return the dispatch ``PYTHONPATH`` entries the probe printed."""
    for line in result.stdout.splitlines():
        if line.startswith('PYTHONPATH='):
            return [entry for entry in line.removeprefix('PYTHONPATH=').split(':') if entry]
    raise AssertionError(f'the probe printed no PYTHONPATH: {result.stdout}{result.stderr}')


def _consumer_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, versions: tuple[str, ...]) -> Path:
    """A cache holding ``versions`` of ``plan-marshall`` plus the probe script."""
    cache = tmp_path / 'cache'
    for version in versions:
        _cached(cache, 'plan-marshall', version, 'platform-runtime', _HELPER, _helper_body(version))
    _cached(cache, 'plan-marshall', _NEWEST, 'probe', 'tool', _IMPORT_PROBE)
    return _generate(monkeypatch, tmp_path / 'project' / '.plan', cache)


def _assert_own_version_helper_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, versions: tuple[str, ...]
) -> None:
    """D1's check: the newest script imports the newest helper, over ``versions``."""
    executor = _consumer_fixture(tmp_path, monkeypatch, versions)

    result = _run(executor, ['plan-marshall:probe:tool'])

    assert result.returncode == 0, f'ImportError naming {_MARKER}: {result.stdout}{result.stderr}'
    pythonpath = ':'.join(_pythonpath(result))
    assert f'{_MARKER}={_NEWEST}' in result.stdout, result.stdout
    assert '0.1.1916' not in pythonpath, pythonpath


# =============================================================================
# D1 — the same-root walk returns only the resolved script's own version
# =============================================================================


def test_d1_a_cached_script_imports_its_own_versions_helper(tmp_path, monkeypatch):
    """A newest-version script imports the newest helper while an older one is cached."""
    _assert_own_version_helper_import(tmp_path, monkeypatch, ('0.1.1916', _NEWEST))


# =============================================================================
# D2 — a sibling bundle without the script's version falls back to its newest
# =============================================================================


def test_d2_a_sibling_bundle_without_the_script_version_uses_its_newest(tmp_path, monkeypatch):
    """A sibling bundle contributes one version: its newest, never both."""
    cache = tmp_path / 'cache'
    for version in ('0.1.1916', '0.1.2004'):
        _cached(cache, 'pm-dev-python', version, 'python-core', 'shared', f"VERSION = '{version}'\n")
    _cached(cache, 'plan-marshall', _NEWEST, 'probe', 'tool', _SHOW_PROBE)
    executor = _generate(monkeypatch, tmp_path / 'project' / '.plan', cache)

    result = _run(executor, ['plan-marshall:probe:tool'])

    assert result.returncode == 0, result.stdout + result.stderr
    pythonpath = ':'.join(_pythonpath(result))
    assert str((cache / 'pm-dev-python' / '0.1.2004').resolve()) in pythonpath, pythonpath
    assert '0.1.1916' not in pythonpath, pythonpath


def test_d2_the_fallback_orders_versions_by_numeric_tuple(tmp_path, monkeypatch):
    """The fallback leads with 0.1.1000 over 0.1.999 — numeric, never a string sort."""
    cache = tmp_path / 'cache'
    for version in ('0.1.999', '0.1.1000'):
        _cached(cache, 'pm-dev-python', version, 'python-core', 'shared', f"VERSION = '{version}'\n")
    _cached(cache, 'plan-marshall', _NEWEST, 'probe', 'tool', _SHOW_PROBE)
    executor = _generate(monkeypatch, tmp_path / 'project' / '.plan', cache)

    result = _run(executor, ['plan-marshall:probe:tool'])

    assert result.returncode == 0, result.stdout + result.stderr
    pythonpath = _pythonpath(result)
    leading = [entry for entry in pythonpath if '/pm-dev-python/' in entry]
    assert leading, pythonpath
    # A string max()/sorted() picks 0.1.999 here; the numeric tuple picks 0.1.1000.
    expected = cache / 'pm-dev-python' / '0.1.1000' / 'skills' / 'python-core' / 'scripts'
    assert leading[0] == str(expected.resolve()), pythonpath


# =============================================================================
# D3 — every shape the walk served keeps working, and one version per skill leads
# =============================================================================


def _cached_direct(root: Path, version: str, skill: str, script: str, body: str) -> Path:
    """Write ``{root}/{version}/skills/{skill}/scripts/{script}.py``."""
    path = root / version / 'skills' / skill / 'scripts' / f'{script}.py'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


def _versions_of(pythonpath: list[str], cache: Path, skill: str) -> list[tuple[int, str]]:
    """Return ``(index, version)`` for every cached ``skill`` dir on ``pythonpath``."""
    found: list[tuple[int, str]] = []
    for index, entry in enumerate(pythonpath):
        try:
            parts = Path(entry).relative_to(cache.resolve()).parts
        except ValueError:
            continue
        if len(parts) >= 4 and parts[2] == 'skills' and parts[3] == skill:
            found.append((index, parts[1]))
    return found


def test_d3_no_skill_gets_an_older_copy_ahead_of_a_newer_one(tmp_path, monkeypatch):
    """In a multi-version cache no skill is on PYTHONPATH twice, older or newer."""
    executor = _consumer_fixture(tmp_path, monkeypatch, ('0.1.1916', '0.1.1969', '0.1.1996', '0.1.2004', _NEWEST))

    result = _run(executor, ['plan-marshall:probe:tool'])

    assert result.returncode == 0, result.stdout + result.stderr
    pythonpath = _pythonpath(result)
    for skill in ('platform-runtime', 'probe'):
        found = _versions_of(pythonpath, tmp_path / 'cache', skill)
        assert len(found) == 1, f"{skill} carries {found} — it must appear once, on the script's version"


def test_d3_the_version_direct_nested_shape_uses_the_scripts_version(tmp_path, monkeypatch):
    """``{root}/{version}/skills/...`` keeps working and stays on one version."""
    cache = tmp_path / 'cache'
    for version in ('0.1.1916', _NEWEST):
        _cached_direct(cache, version, 'platform-runtime', _HELPER, _helper_body(version))
    _cached_direct(cache, _NEWEST, 'probe', 'tool', _IMPORT_PROBE)
    executor = _generate(monkeypatch, tmp_path / 'project' / '.plan', cache)

    result = _run(executor, ['plan-marshall:probe:tool'])

    assert result.returncode == 0, result.stdout + result.stderr
    pythonpath = ':'.join(_pythonpath(result))
    assert str((cache / _NEWEST).resolve()) in pythonpath, pythonpath
    assert '0.1.1916' not in pythonpath, pythonpath


# =============================================================================
# D4 — the regression is reproduced against the reported shape
# =============================================================================


def test_d4_eight_cached_versions_still_import_the_newest_helper(tmp_path, monkeypatch):
    """D1's check on the reported shape: eight cached versions, the helper gaining a symbol."""
    _assert_own_version_helper_import(
        tmp_path,
        monkeypatch,
        ('0.1.1916', '0.1.1965', '0.1.1969', '0.1.1989', '0.1.1996', '0.1.2004', '0.1.2007', _NEWEST),
    )
