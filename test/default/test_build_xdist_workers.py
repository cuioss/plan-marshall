# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the bounded xdist worker count of ``module-tests``.

``-n auto`` starts one worker per CPU thread; on a many-thread host two
concurrent runs exhaust memory. The count is the CPU count bounded by
``PYTEST_XDIST_MAX_WORKERS``, unless the operator exported
``PYTEST_XDIST_AUTO_NUM_WORKERS``, which xdist reads itself.
"""

from pathlib import Path

import build
import pytest

REPO_ROOT = Path(build.__file__).resolve().parent


def _run_recorder(calls: list[list[str]]):
    def _stub(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        calls.append(cmd)
        return 0

    return _stub


@pytest.fixture(autouse=True)
def _no_operator_override(monkeypatch):
    monkeypatch.delenv('PYTEST_XDIST_AUTO_NUM_WORKERS', raising=False)


class TestWorkerArg:
    def test_many_cpus_are_bounded(self, monkeypatch):
        monkeypatch.setattr(build.os, 'cpu_count', lambda: 64)
        assert build._xdist_worker_arg() == str(build.PYTEST_XDIST_MAX_WORKERS)

    def test_few_cpus_stay_the_binding_bound(self, monkeypatch):
        monkeypatch.setattr(build.os, 'cpu_count', lambda: 2)
        assert build._xdist_worker_arg() == '2'

    def test_unknown_cpu_count_still_yields_a_worker(self, monkeypatch):
        monkeypatch.setattr(build.os, 'cpu_count', lambda: None)
        assert build._xdist_worker_arg() == '1'

    def test_operator_override_is_passed_through_to_xdist(self, monkeypatch):
        monkeypatch.setenv('PYTEST_XDIST_AUTO_NUM_WORKERS', '3')
        monkeypatch.setattr(build.os, 'cpu_count', lambda: 64)
        assert build._xdist_worker_arg() == 'auto'


class TestArgvCarriesBoundedCount:
    def test_parallel_argv_never_carries_a_bare_auto_by_default(self, monkeypatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(build, 'run', _run_recorder(calls))
        monkeypatch.setattr(build.os, 'cpu_count', lambda: 64)
        monkeypatch.chdir(REPO_ROOT)
        build.cmd_module_tests('plan-marshall', parallel=True)
        argv = calls[0]
        assert argv[argv.index('-n') + 1] == str(build.PYTEST_XDIST_MAX_WORKERS)
        assert '--dist=loadgroup' in argv

    def test_serial_run_carries_no_n_flag(self, monkeypatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(build, 'run', _run_recorder(calls))
        monkeypatch.chdir(REPO_ROOT)
        build.cmd_module_tests('plan-marshall', parallel=False)
        assert '-n' not in calls[0]
