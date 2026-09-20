# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``module-tests --filter`` fast-signal passthrough.

Deliverable 3 of PLAN-03 (process-compliance): the sanctioned alternative to
a direct ``.venv/bin/pytest -k`` invocation. The filter expression is
forwarded verbatim as pytest's ``-k`` argv (list form, no shell), keeping the
per-session basetemp isolation, the xdist grouping, and the change-ledger
build attribution the direct path bypasses.

Each detector carries a matched pair: the passthrough reaching the pytest
argv, and the refusal that fires instead of a silent ignore (an empty
``--filter`` is rejected; an unfiltered run carries no ``-k`` at all).
"""

from pathlib import Path

import build
import pytest

REPO_ROOT = Path(build.__file__).resolve().parent


def _run_recorder(calls: list[list[str]], rc: int = 0):
    def _stub(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        calls.append(cmd)
        return rc

    return _stub


@pytest.fixture
def repo_root_cwd(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    return REPO_ROOT


class TestFilterPassthrough:
    def test_filter_reaches_pytest_argv_verbatim(self, monkeypatch, repo_root_cwd):
        calls: list[list[str]] = []
        monkeypatch.setattr(build, 'run', _run_recorder(calls))
        rc = build.cmd_module_tests('plan-marshall', parallel=False, filter_expr='test_foo')
        assert rc == 0
        assert calls, 'cmd_module_tests must invoke the runner'
        argv = calls[0]
        assert '-k' in argv
        assert argv[argv.index('-k') + 1] == 'test_foo'

    def test_filter_combines_with_parallel_grouping(self, monkeypatch, repo_root_cwd):
        calls: list[list[str]] = []
        monkeypatch.setattr(build, 'run', _run_recorder(calls))
        build.cmd_module_tests('plan-marshall', parallel=True, filter_expr='test_foo')
        argv = calls[0]
        assert '-k' in argv
        assert '-n' in argv
        assert '--dist=loadgroup' in argv

    def test_unfiltered_run_carries_no_k_flag(self, monkeypatch, repo_root_cwd):
        calls: list[list[str]] = []
        monkeypatch.setattr(build, 'run', _run_recorder(calls))
        build.cmd_module_tests('plan-marshall', parallel=False)
        assert '-k' not in calls[0]


class TestFilterRefusals:
    @pytest.mark.parametrize('empty', ['', '   '])
    def test_empty_filter_refused_not_silently_ignored(self, empty):
        """The CLI layer rejects an empty ``--filter`` (exit 1); it never runs
        an unfiltered suite while reporting a filtered one."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, 'build.py', 'module-tests', 'plan-marshall', '--filter', empty],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 1
        assert '--filter requires a non-empty' in result.stderr

    def test_filter_flag_reaches_parser(self):
        """The ``--filter`` flag exists on the ``module-tests`` parser (no
        argparse rejection for the sanctioned form)."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, 'build.py', 'module-tests', '--help'],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert '--filter' in result.stdout
