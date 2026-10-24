#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end tests for the executor's direct-path recovery entry (D3).

A fixture consumer project holds a REAL generated executor whose bootstrap
import fails (a bootstrap module was removed). The executor's own failure output
must name the exact recovery command; running that command must regenerate the
executor and make it startable again. A cache that is itself missing the module
must produce ``regenerate_failed``, never ``regenerated``.

The fixture cache is a nested, versioned copy of the real ``plan-marshall``
bundle, discovered through ``OPENCODE_CONFIG_DIR`` exactly as a deployed OpenCode
install is. The consumer project has no ``marketplace/bundles`` tree, so the
recovery generation resolves from the cache — the consumer case the defect names.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT

CACHE_VERSION = '0.1.9999'
BROKEN_MODULE = Path('skills') / 'manage-change-ledger' / 'scripts' / '_ledger_core.py'


def _clean_env(home: Path, plan_base: Path) -> dict[str, str]:
    """A fresh-shell environment: no PYTHONPATH, no ambient marketplace anchor.

    ``PLAN_BASE_DIR`` pins the generated executor's output to the fixture
    project's own ``.plan`` — otherwise the generator walks up to the enclosing
    checkout's ``.plan`` and writes the executor there.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in (
            'PYTHONPATH',
            'PM_MARKETPLACE_ROOT',
            'OPENCODE',
            'OPENCODE_CONFIG_DIR',
            'PLAN_BASE_DIR',
            'PM_SURFACE_BUDGET_SECONDS',
        )
    }
    env.update(
        {
            'CLAUDE_CODE_SESSION_ID': 'fixture-session',
            'HOME': str(home),
            'XDG_CONFIG_HOME': str(home / '.config'),
            'PLAN_BASE_DIR': str(plan_base),
        }
    )
    return env


@pytest.fixture()
def recovery_fixture():
    """A consumer project with a generated executor and a nested fixture cache.

    The fixture lives in a SYSTEM temp directory, outside the enclosing checkout:
    a directory under the worktree's ``.plan/temp`` would let the generator's
    tree-first resolution find the worktree's own ``marketplace/bundles`` and pin
    the executor to it, hiding the cache-only consumer case this test exists for.
    """
    root = Path(tempfile.mkdtemp(prefix='pm-recovery-'))
    try:
        home = root / 'home'
        home.mkdir()
        cache_root = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
        cache_root.mkdir(parents=True)
        # Each bundle deploys as {cache_root}/{bundle}/{version}/ in the Claude cache.
        for source_bundle in sorted(MARKETPLACE_ROOT.iterdir()):
            if source_bundle.is_dir():
                shutil.copytree(source_bundle, cache_root / source_bundle.name / CACHE_VERSION)
        version_dir = cache_root / 'plan-marshall' / CACHE_VERSION
        (cache_root / 'dist-manifest.json').write_text(json.dumps({'version': CACHE_VERSION}), encoding='utf-8')

        consumer = root / 'consumer'
        (consumer / '.plan').mkdir(parents=True)
        env = _clean_env(home, consumer / '.plan')

        generator = version_dir / 'skills' / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
        generated = subprocess.run(
            [sys.executable, str(generator), 'generate', '--target', 'claude'],
            cwd=consumer,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert generated.returncode == 0, generated.stdout + generated.stderr
        executor = consumer / '.plan' / 'execute-script.py'
        assert executor.is_file(), generated.stdout + generated.stderr

        broken = version_dir / BROKEN_MODULE
        assert broken.is_file(), broken
        yield {
            'consumer': consumer,
            'executor': executor,
            'broken': broken,
            'env': env,
            'cache_root': cache_root,
            'version_dir': version_dir,
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _run_executor(fixture: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(fixture['executor']), '--list'],
        cwd=fixture['consumer'],
        env=fixture['env'],
        capture_output=True,
        text=True,
        timeout=120,
    )


def _recovery_command(stderr: str) -> str:
    """Extract the recovery command line the executor printed."""
    for line in stderr.splitlines():
        candidate = line.strip()
        if candidate.startswith('python3 ') and 'generate_executor.py' in candidate and ' recover' in candidate:
            return candidate
    raise AssertionError(f'no recovery command line in stderr:\n{stderr}')


def test_broken_executor_prints_an_exact_recovery_command(recovery_fixture: dict) -> None:
    recovery_fixture['broken'].unlink()

    result = _run_executor(recovery_fixture)

    assert result.returncode != 0
    command = _recovery_command(result.stderr)
    assert str(recovery_fixture['cache_root']) in command
    assert '--target claude' in command


def test_the_printed_command_recovers_the_executor(recovery_fixture: dict) -> None:
    broken = recovery_fixture['broken']
    original = broken.read_bytes()
    broken.unlink()

    failing = _run_executor(recovery_fixture)
    command = _recovery_command(failing.stderr)

    # The failure was the on-disk executor's; the cache is intact again.
    broken.write_bytes(original)
    recovered = subprocess.run(
        shlex.split(command),
        cwd=recovery_fixture['consumer'],
        env=recovery_fixture['env'],
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert 'action: regenerated' in recovered.stdout, recovered.stdout + recovered.stderr
    assert _run_executor(recovery_fixture).returncode == 0


def test_a_cache_missing_the_module_reports_regenerate_failed(recovery_fixture: dict) -> None:
    recovery_fixture['broken'].unlink()

    failing = _run_executor(recovery_fixture)
    command = _recovery_command(failing.stderr)

    recovered = subprocess.run(
        shlex.split(command),
        cwd=recovery_fixture['consumer'],
        env=recovery_fixture['env'],
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert 'action: regenerate_failed' in recovered.stdout, recovered.stdout + recovered.stderr
    assert '_ledger_core' in recovered.stdout or 'ModuleNotFoundError' in recovered.stdout
    assert 'action: regenerated' not in recovered.stdout
