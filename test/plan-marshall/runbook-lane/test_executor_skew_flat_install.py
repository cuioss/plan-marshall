#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The executor-skew check answers on a flat install.

A flat install (OpenCode, Antigravity) deploys ``{root}/skills/{bundle}-{skill}/``
and carries no ``{bundle}/{version}/`` directory, so the only version witness it
holds is the sync stamp (``dist-manifest.json``) at the deploy root. Without that
leg the lane-text version is unmakeable on every flat harness, the check answers
``could_not_check`` there, and a genuinely stale executor passes unnoticed.

The in-process cases drive the helper; the end-to-end cases drive the verb through
a generated executor under the OpenCode runtime signal, naming the flat fixture's
lane skill explicitly (``--lane-dir``) because a developer checkout's own tree
outranks every deployed copy by design.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import target_context
from _flat_install_fixtures import build_flat_install, write_dist_manifest

from conftest import MARKETPLACE_ROOT, load_script_module

_SKILL_NAME = 'runbook-lane'
_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / _SKILL_NAME
_FLAT_LANE_DIR_NAME = f'plan-marshall-{_SKILL_NAME}'

#: Every platform env signal the runtime detector reads, taken from the detector's
#: own declaration so a new signal cannot stay active in the subprocess paths.
_SIGNALS = tuple(signal for signal, _target in target_context.TARGET_ENV_SIGNALS)

#: The reason a read-but-version-less executor produces. Pinned because the
#: operator's remedy depends on WHICH side of the comparison could not be read.
_EXECUTOR_REASON = 'executor version missing or empty'

ge = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py', register=False)


# -----------------------------------------------------------------------------
# Fixtures and helpers
# -----------------------------------------------------------------------------


def _lane_module():
    """Load the lane script fresh, publishing nothing."""
    return load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)


def _executor(tmp_path: Path, version: str | None) -> Path:
    """Write a minimal executor carrying ``version`` (``None``: no assignment)."""
    path = tmp_path / 'execute-script.py'
    path.write_text('' if version is None else f"MARSHALL_VERSION = '{version}'\n", encoding='utf-8')
    return path


def _flat_install(tmp_path: Path, stamp_version: str | None) -> tuple[Path, Path]:
    """Build a flat install and return ``(deploy_root, lane_skill_dir)``."""
    root = build_flat_install(tmp_path / 'opencode', stamp_version=stamp_version)
    return root, root / 'skills' / _FLAT_LANE_DIR_NAME


def _versioned_lane(tmp_path: Path, version: str) -> Path:
    """Lay out one versioned plugin-cache entry carrying the lane skill."""
    version_dir = tmp_path / 'cache' / 'plan-marshall' / version
    (version_dir / '.claude-plugin').mkdir(parents=True, exist_ok=True)
    (version_dir / '.claude-plugin' / 'plugin.json').write_text('{}\n', encoding='utf-8')
    lane = version_dir / 'skills' / _SKILL_NAME
    lane.mkdir(parents=True, exist_ok=True)
    (lane / 'SKILL.md').write_text(f'---\nname: {_SKILL_NAME}\n---\n\n# Runbook Lane\n', encoding='utf-8')
    return lane


def _skew_result(executor: Path, lane_dir: Path) -> dict[str, object]:
    """Run the verb in-process against ``lane_dir`` and return its payload."""
    module = _lane_module()
    payload: dict[str, object] = module.cmd_executor_skew(
        argparse.Namespace(executor=str(executor), lane_dir=str(lane_dir))
    )
    return payload


def _flat_reason(deploy_root: Path) -> str:
    """The reason a flat install without a usable stamp reports."""
    return f'lane text version unknown: no usable version in the install stamp {deploy_root / "dist-manifest.json"}'


# -----------------------------------------------------------------------------
# The lane-text version comes from the install's own stamp
# -----------------------------------------------------------------------------


def test_flat_install_stamp_matches_the_current_executor(tmp_path: Path) -> None:
    _root, lane = _flat_install(tmp_path, '0.1.2021')

    assert _lane_module()._executor_skew(_executor(tmp_path, '0.1.2021'), lane) == 'match'


def test_flat_install_stamp_reports_skew_with_the_remedy(tmp_path: Path) -> None:
    _root, lane = _flat_install(tmp_path, '0.1.2017')

    data = _skew_result(_executor(tmp_path, '0.1.2010'), lane)

    assert data['verdict'] == 'skew'
    assert data['executor_version'] == '0.1.2010'
    assert data['lane_version'] == '0.1.2017'
    assert data['remedy'] == 'regenerate the executor'


def test_flat_install_stamp_matches_a_newer_executor(tmp_path: Path) -> None:
    """A newer executor is never skew: only an OLDER one cannot run the text."""
    _root, lane = _flat_install(tmp_path, '0.1.2017')

    assert _lane_module()._executor_skew(_executor(tmp_path, '0.1.2021'), lane) == 'match'


def test_flat_install_without_a_stamp_cannot_check(tmp_path: Path) -> None:
    root, lane = _flat_install(tmp_path, None)

    data = _skew_result(_executor(tmp_path, '0.1.2021'), lane)

    assert data['verdict'] == 'could_not_check'
    assert data['reason'] == _flat_reason(root)


def test_flat_install_with_an_unreadable_stamp_cannot_check(tmp_path: Path) -> None:
    root, lane = _flat_install(tmp_path, None)
    write_dist_manifest(root, raw='{"version": ')

    data = _skew_result(_executor(tmp_path, '0.1.2021'), lane)

    assert data['verdict'] == 'could_not_check'
    assert data['reason'] == _flat_reason(root)


def test_flat_install_with_a_versionless_stamp_cannot_check(tmp_path: Path) -> None:
    root, lane = _flat_install(tmp_path, None)
    write_dist_manifest(root, version=None)

    data = _skew_result(_executor(tmp_path, '0.1.2021'), lane)

    assert data['verdict'] == 'could_not_check'
    assert data['reason'] == _flat_reason(root)


def test_flat_install_with_an_incomparable_stamp_cannot_check(tmp_path: Path) -> None:
    """A stamp version with no digit cannot be compared, so it is never agreement.

    The comparison parses versions by their digit runs, so a word would compare
    as the empty tuple and read as ``match`` against any executor — the exact
    fail-open direction the check exists to close.
    """
    root, lane = _flat_install(tmp_path, 'unknown')

    data = _skew_result(_executor(tmp_path, '0.1.2010'), lane)

    assert data['verdict'] == 'could_not_check'
    assert data['reason'] == _flat_reason(root)


def test_versioned_cache_still_reads_the_installed_version_directory(tmp_path: Path) -> None:
    """The versioned leg keeps answering from the live install, unchanged."""
    module = _lane_module()
    _versioned_lane(tmp_path, '0.1.1961')
    lane = _versioned_lane(tmp_path, '0.1.1977')

    assert module._executor_skew(_executor(tmp_path, '0.1.1977'), lane) == 'match'
    assert module._executor_skew(_executor(tmp_path, '0.1.1950'), lane) == 'skew'


# The source-checkout case lives in ``test_executor_skew_source_checkout.py``: it is
# no longer a ``could_not_check``, and the verdict it answers now is that module's subject.


# -----------------------------------------------------------------------------
# The reason names the thing that could not be read
# -----------------------------------------------------------------------------


def test_reason_names_a_read_but_versionless_executor(tmp_path: Path) -> None:
    _root, lane = _flat_install(tmp_path, '0.1.2021')

    data = _skew_result(_executor(tmp_path, None), lane)

    assert data['verdict'] == 'could_not_check'
    assert data['reason'] == _EXECUTOR_REASON


def test_reason_names_an_unreadable_executor(tmp_path: Path) -> None:
    _root, lane = _flat_install(tmp_path, '0.1.2021')

    data = _skew_result(tmp_path / 'absent-execute-script.py', lane)

    assert data['verdict'] == 'could_not_check'
    assert data['reason'] == 'executor version unreadable'


def test_an_unparseable_executor_version_cannot_check(tmp_path: Path) -> None:
    """A version with no version key is a failed read, not the older side.

    ``skew`` claims the executor is OLDER; a name the comparison cannot parse
    would compare as the empty tuple and make that claim without a comparison.
    The failure is the executor's, so the reason must not blame the lane text.
    """
    _root, lane = _flat_install(tmp_path, '0.1.2021')

    data = _skew_result(_executor(tmp_path, 'dev'), lane)

    assert data['verdict'] == 'could_not_check'
    assert data['reason'] == 'executor version names no version key'


def test_an_unparseable_version_directory_cannot_check(tmp_path: Path) -> None:
    """A live version dir whose name carries no version key cannot be compared."""
    module = _lane_module()
    lane = _versioned_lane(tmp_path, 'dev')

    data = _skew_result(_executor(tmp_path, '0.1.2021'), lane)

    assert data['verdict'] == 'could_not_check'
    assert data['reason'] == f'lane text version unknown: the version directory {lane.parents[1]} names no version key'
    assert module._executor_skew(_executor(tmp_path, '0.1.2021'), lane) == 'could_not_check'


def test_skill_states_where_each_layout_takes_the_lane_text_version() -> None:
    text = (_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
    section = _skill_section(text, '### executor-skew')

    assert 'dist-manifest.json' in section, 'the executor-skew section names no flat-install witness'
    assert 'version directory' in section, 'the executor-skew section names no versioned witness'
    assert 'source checkout' in section, 'the executor-skew section does not say which layout stays unmakeable'
    assert 'never read as' in section, 'an unmakeable comparison is not distinguished from no skew'
    assert text.count('dist-manifest.json') == 1, 'the flat-install witness is stated more than once'


def _skill_section(text: str, heading: str) -> str:
    """Return one heading's prose, whitespace-normalised, up to the next ``##``/``###``."""
    start = text.index(heading)
    rest = text[start + len(heading) :]
    following = re.search(r'\n#{2,3} ', rest)
    end = following.start() if following else -1
    return ' '.join((heading + (rest if end == -1 else rest[:end])).split())


# -----------------------------------------------------------------------------
# The verdict on the path a lane takes: through the executor
# -----------------------------------------------------------------------------


def _generate_executor(
    monkeypatch: pytest.MonkeyPatch,
    plan_dir: Path,
    roots: tuple[tuple[str, str], ...],
    versions: tuple[tuple[str, str], ...],
) -> Path:
    """Generate a real executor whose OpenCode install is ``roots`` at ``versions``."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    for signal in _SIGNALS:
        monkeypatch.delenv(signal, raising=False)
    monkeypatch.setattr(ge, 'installed_harness_roots', lambda: list(roots))
    monkeypatch.setattr(ge, 'installed_harness_versions', lambda _roots=None: list(versions))
    result = ge.generate_executor({}, MARKETPLACE_ROOT, dry_run=False, target='opencode')
    assert result['status'] == 'success', result
    executor = plan_dir / 'execute-script.py'
    assert executor.is_file()
    return executor


def _run_skew(executor: Path, project_dir: Path, lane_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run the verb through ``executor`` as an OpenCode call against ``lane_dir``.

    ``--lane-dir`` names the flat fixture's lane skill: a developer checkout puts
    its own ``marketplace/bundles`` tree ahead of every deployed copy by design,
    so the fixture is named explicitly rather than left to the install walk.
    """
    env = {key: value for key, value in os.environ.items() if key not in _SIGNALS}
    env.pop('PYTHONPATH', None)
    env['OPENCODE'] = '1'
    env['PLAN_MARSHALL_HOME'] = str(project_dir / '.machine-home')
    return subprocess.run(
        [
            sys.executable,
            str(executor),
            'plan-marshall:runbook-lane:runbook_lane',
            'executor-skew',
            '--lane-dir',
            str(lane_dir),
        ],
        cwd=project_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_executor_skew_matches_through_the_executor_on_a_flat_install(tmp_path, monkeypatch) -> None:
    root = build_flat_install(tmp_path / 'opencode', stamp_version='0.1.2021')
    executor = _generate_executor(
        monkeypatch,
        tmp_path / 'project' / '.plan',
        roots=(('opencode', str(root / 'skills')),),
        versions=(('opencode', '0.1.2021'),),
    )

    result = _run_skew(executor, tmp_path / 'project', root / 'skills' / _FLAT_LANE_DIR_NAME)

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'verdict: match' in result.stdout, result.stdout + result.stderr
    assert 'executor_version: 0.1.2021' in result.stdout
    assert 'lane_version: 0.1.2021' in result.stdout


def test_executor_skew_reports_the_stale_executor_through_the_executor(tmp_path, monkeypatch) -> None:
    """An executor generated before the install's last sync ends the run as skew."""
    root = build_flat_install(tmp_path / 'opencode', stamp_version='0.1.2017')
    executor = _generate_executor(
        monkeypatch,
        tmp_path / 'project' / '.plan',
        roots=(('opencode', str(root / 'skills')),),
        versions=(('opencode', '0.1.2010'),),
    )

    result = _run_skew(executor, tmp_path / 'project', root / 'skills' / _FLAT_LANE_DIR_NAME)

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'verdict: skew' in result.stdout, result.stdout + result.stderr
    assert 'executor_version: 0.1.2010' in result.stdout
    assert 'lane_version: 0.1.2017' in result.stdout
    assert 'regenerate the executor' in result.stdout


def test_executor_skew_cannot_check_through_the_executor_without_a_stamp(tmp_path, monkeypatch) -> None:
    root = build_flat_install(tmp_path / 'opencode')
    executor = _generate_executor(
        monkeypatch,
        tmp_path / 'project' / '.plan',
        roots=(('opencode', str(root / 'skills')),),
        versions=(('opencode', '0.1.2021'),),
    )

    result = _run_skew(executor, tmp_path / 'project', root / 'skills' / _FLAT_LANE_DIR_NAME)

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'verdict: could_not_check' in result.stdout, result.stdout + result.stderr
    assert 'no usable version in the install stamp' in result.stdout
    assert 'dist-manifest.json' in result.stdout
