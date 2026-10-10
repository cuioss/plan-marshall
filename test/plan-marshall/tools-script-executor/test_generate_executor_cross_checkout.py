#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A generation whose scripts and output lie in different checkouts is refused.

``--marketplace-root`` pins where scripts are discovered; the executor is
written into the nearest ``.plan`` above the working directory. Nothing else
ties the two together, so a call that names one checkout's scripts while
standing in another would write the second checkout's executor from the first
checkout's scripts.

The cases build a throwaway main checkout with a worktree nested under its
``.plan/local/worktrees/`` - the layout in which the two roots share a path
prefix and only a comparison of resolved roots tells them apart. The generator
runs as a subprocess, because the output location is decided by the process
working directory and by environment the test session itself sets.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import get_scripts_dir, load_script_module

GENERATE_SCRIPT = get_scripts_dir('plan-marshall', 'tools-script-executor') / 'generate_executor.py'

_gen = load_script_module(
    'plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_executor_cross_checkout', register=False
)

#: Environment that would move the output path or the discovery root away from
#: what the working directory and the flags say.
_LOCATION_ENV = ('PLAN_BASE_DIR', 'PLAN_DIR_NAME', 'PM_MARKETPLACE_ROOT', 'PM_DIST_MANIFEST', 'PYTHONPATH')

#: What main's executor holds before the refused call. Any change to it shows.
_MAIN_EXECUTOR_BYTES = b'# the main checkout executor, as it was before the call\n'

_SCRIPT_BODY = (
    'import argparse\n\n'
    "parser = argparse.ArgumentParser(description='stand-in script', allow_abbrev=False)\n"
    'parser.parse_args()\n'
)


def _make_checkout(root: Path) -> Path:
    """Create a minimal checkout at ``root``: one bundle script and a ``.plan/local``."""
    scripts = root / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-logging' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'plan_logging.py').write_text(_SCRIPT_BODY, encoding='utf-8')
    (root / '.plan' / 'local').mkdir(parents=True)
    return root


@pytest.fixture
def checkouts(tmp_path: Path) -> tuple[Path, Path]:
    """A main checkout and a worktree nested under its ``.plan/local/worktrees/``."""
    main = _make_checkout((tmp_path / 'main').resolve())
    worktree = _make_checkout(main / '.plan' / 'local' / 'worktrees' / 'feature')
    (main / '.plan' / 'execute-script.py').write_bytes(_MAIN_EXECUTOR_BYTES)
    return main, worktree


def _generate(*, cwd: Path, marketplace_root: Path) -> subprocess.CompletedProcess[str]:
    """Run ``generate --marketplace --marketplace-root`` from ``cwd``."""
    env = {key: value for key, value in os.environ.items() if key not in _LOCATION_ENV}
    return subprocess.run(
        [
            sys.executable,
            str(GENERATE_SCRIPT),
            'generate',
            '--marketplace',
            '--marketplace-root',
            str(marketplace_root),
        ],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def _field(stdout: str, key: str) -> str:
    """Return the value of the TOON line ``key: value`` in ``stdout``, unquoted."""
    values = [line.split(':', 1)[1].strip().strip('"') for line in stdout.splitlines() if line.startswith(f'{key}:')]
    assert len(values) == 1, f'expected exactly one {key!r} line, found {len(values)} in:\n{stdout}'
    return values[0]


def test_generating_from_main_with_the_worktree_as_discovery_root_is_refused(checkouts) -> None:
    """The refusal names both checkout roots and leaves main's executor byte-identical."""
    main, worktree = checkouts

    result = _generate(cwd=main, marketplace_root=worktree)

    assert result.returncode == 0, result.stderr
    assert _field(result.stdout, 'status') == 'error'
    assert _field(result.stdout, 'error') == _gen.ERROR_CROSS_CHECKOUT_GENERATION
    assert _field(result.stdout, 'discovery_root') == str(worktree)
    assert _field(result.stdout, 'output_root') == str(main)
    assert (main / '.plan' / 'execute-script.py').read_bytes() == _MAIN_EXECUTOR_BYTES
    assert not (worktree / '.plan' / 'execute-script.py').exists()


def test_the_same_call_from_inside_the_worktree_generates_the_worktree_executor(checkouts) -> None:
    """Matched control: only the working directory differs, and the call succeeds.

    Every embedded path that lies under the main checkout lies under the
    worktree, and main's executor is still untouched.
    """
    main, worktree = checkouts

    result = _generate(cwd=worktree, marketplace_root=worktree)

    assert result.returncode == 0, result.stderr
    assert _field(result.stdout, 'status') == 'success', result.stdout
    generated = (worktree / '.plan' / 'execute-script.py').read_text(encoding='utf-8')
    script_path = worktree / 'marketplace/bundles/plan-marshall/skills/manage-logging/scripts/plan_logging.py'
    assert str(script_path) in generated
    # The worktree path starts with main's, so equal counts mean no embedded
    # path lies under main without lying under the worktree.
    assert generated.count(str(main)) == generated.count(str(worktree))
    assert (main / '.plan' / 'execute-script.py').read_bytes() == _MAIN_EXECUTOR_BYTES


def test_a_plugin_cache_discovery_root_is_not_a_checkout(tmp_path: Path) -> None:
    """Scripts discovered in a plugin cache are written into any checkout."""
    cache_base = tmp_path / 'home' / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
    cache_base.mkdir(parents=True)
    checkout = _make_checkout(tmp_path / 'checkout')

    refusal = _gen.cross_checkout_refusal(cache_base, checkout / '.plan' / 'execute-script.py')

    assert refusal is None


def test_an_output_directory_that_is_no_checkout_is_not_refused(tmp_path: Path) -> None:
    """A consumer project holds no marketplace tree, so there is no second checkout."""
    checkout = _make_checkout(tmp_path / 'checkout')
    consumer = tmp_path / 'consumer'
    (consumer / '.plan').mkdir(parents=True)

    refusal = _gen.cross_checkout_refusal(
        checkout / 'marketplace' / 'bundles', consumer / '.plan' / 'execute-script.py'
    )

    assert refusal is None


def test_two_sibling_checkouts_are_refused_and_one_checkout_is_not(tmp_path: Path) -> None:
    """The refusal follows from the two roots differing, not from their nesting."""
    first = _make_checkout((tmp_path / 'first').resolve())
    second = _make_checkout((tmp_path / 'second').resolve())
    base = first / 'marketplace' / 'bundles'

    same = _gen.cross_checkout_refusal(base, first / '.plan' / 'execute-script.py')
    different = _gen.cross_checkout_refusal(base, second / '.plan' / 'execute-script.py')

    assert same is None
    assert different is not None
    assert different['error'] == _gen.ERROR_CROSS_CHECKOUT_GENERATION
    assert (different['discovery_root'], different['output_root']) == (str(first), str(second))


def test_a_symlinked_spelling_of_one_checkout_is_the_same_checkout(tmp_path: Path) -> None:
    """Roots are compared resolved, so two spellings of one directory do not disagree."""
    checkout = _make_checkout((tmp_path / 'checkout').resolve())
    alias = tmp_path / 'alias'
    alias.symlink_to(checkout, target_is_directory=True)

    refusal = _gen.cross_checkout_refusal(alias / 'marketplace' / 'bundles', checkout / '.plan' / 'execute-script.py')

    assert refusal is None
