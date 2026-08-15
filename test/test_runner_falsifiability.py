#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D7 falsifiability control for the canonical test runner.

The retired ``test/run-tests.py`` executed each test file AS A SCRIPT and read a
zero exit as a pass. A test file with no ``__main__`` block therefore imported,
ran zero test functions, exited 0, and was reported green — a runner that could
not fail. It was deleted (D1) in favour of the canonical build command, which
runs the suite through pytest.

This control proves the replacement is FALSIFIABLE: a file containing a
deliberately failing test MUST turn the canonical runner (pytest — the engine the
``module-tests`` build command drives) red. Without this control the D1 fix is
unfalsifiable, and an unfalsifiable fix for a false-green is the same defect
wearing a fix's clothes (D7).

The runner is exercised as ``python -m pytest`` rather than through ``./pw`` on
purpose: the red/green verdict lives entirely in pytest's exit-code semantics,
which ``python -m pytest`` exercises identically without the toolchain/network
weight of the full wrapper. The temp file is written OUTSIDE the repository (via
the ``outside_repo_dir`` fixture) so the subprocess pytest inherits none of this
suite's own config or conftest — it probes bare pytest's verdict mechanism.
"""

import subprocess
import sys
from pathlib import Path

# A test file with a failing test and NO ``__main__`` block — the exact shape the
# retired script-runner reported green.
_FAILING_TEST = (
    'def test_deliberately_fails():\n'
    '    assert False, "D7 control: this must redden the canonical runner"\n'
)
# The matched-pair positive: a passing file, so that a red result is a real
# verdict and not an unconditionally-red runner.
_PASSING_TEST = 'def test_deliberately_passes():\n    assert True\n'


def _run_pytest(target: Path) -> subprocess.CompletedProcess:
    """Run bare pytest against a single file, isolated from this suite's config."""
    return subprocess.run(
        [sys.executable, '-m', 'pytest', str(target), '-p', 'no:cacheprovider', '-q'],
        capture_output=True,
        text=True,
        cwd=str(target.parent),
        timeout=120,
    )


def test_failing_test_reddens_the_canonical_runner(outside_repo_dir):
    """A file whose test fails MUST make the canonical runner (pytest) exit
    non-zero. If it does not, the false-green defect is not closed."""
    target = Path(outside_repo_dir) / 'test_control_case.py'
    target.write_text(_FAILING_TEST)

    result = _run_pytest(target)

    assert result.returncode != 0, (
        'The canonical runner reported success on a deliberately failing test — '
        f'the false-green defect is NOT closed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    )
    assert '1 failed' in result.stdout


def test_passing_test_stays_green_under_the_canonical_runner(outside_repo_dir):
    """Matched control: a passing file exits 0, proving the red above is a real
    verdict and the runner is not unconditionally red."""
    target = Path(outside_repo_dir) / 'test_control_case.py'
    target.write_text(_PASSING_TEST)

    result = _run_pytest(target)

    assert result.returncode == 0, (
        'A passing test did not exit 0 under the canonical runner.\n'
        f'stdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    )


def test_failing_file_run_as_a_script_is_falsely_green(outside_repo_dir):
    """Documents the RETIRED defect. The deleted ``test/run-tests.py`` ran each
    file as a bare script and read exit 0 as a pass. The same failing file, with
    no ``__main__`` block, run as a script defines the failing function but never
    calls it, so the interpreter exits 0 — the exact false green that made a
    script-runner unable to fail, and the reason it was deleted. The canonical
    runner above does not share this blind spot."""
    target = Path(outside_repo_dir) / 'test_control_case.py'
    target.write_text(_FAILING_TEST)

    result = subprocess.run(
        [sys.executable, str(target)],
        capture_output=True,
        text=True,
        cwd=str(target.parent),
        timeout=60,
    )

    assert result.returncode == 0, (
        'A file with no __main__ block, run as a script, unexpectedly did not '
        f'exit 0.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    )
