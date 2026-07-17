# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``build.py`` ``cmd_verify`` orchestration.

Deliverable 4 wires ``cmd_test_compile`` into ``cmd_verify`` between the
quality-gate and module-tests steps. These tests pin that ordering and the
short-circuit contract by monkeypatching ``cmd_verify``'s three direct
collaborators (``cmd_quality_gate`` / ``cmd_test_compile`` / ``cmd_module_tests``)
so the orchestration is exercised in isolation — no real mypy/ruff/pytest run
and no coupling to the tree's live SPDX/type state. The repo root is on the
pytest path (``[tool.pytest.ini_options]``), so the root ``build`` module imports
by bare name.
"""

import build


def _record(calls: list[str], label: str, rc: int):
    """Return a stub that records its label and yields the given return code."""

    def _stub(module, parallel: bool = True) -> int:
        calls.append(label)
        return rc

    return _stub


def test_verify_runs_test_compile_between_quality_gate_and_module_tests(monkeypatch):
    """cmd_verify runs quality-gate -> test-compile -> module-tests in that order."""
    calls: list[str] = []
    monkeypatch.setattr(build, 'cmd_quality_gate', _record(calls, 'quality-gate', 0))
    monkeypatch.setattr(build, 'cmd_test_compile', _record(calls, 'test-compile', 0))
    monkeypatch.setattr(build, 'cmd_module_tests', _record(calls, 'module-tests', 0))

    rc = build.cmd_verify(None)

    assert rc == 0
    assert calls == ['quality-gate', 'test-compile', 'module-tests']


def test_verify_short_circuits_before_module_tests_on_test_compile_failure(monkeypatch):
    """A non-zero test-compile return aborts cmd_verify before module-tests."""
    calls: list[str] = []
    monkeypatch.setattr(build, 'cmd_quality_gate', _record(calls, 'quality-gate', 0))
    monkeypatch.setattr(build, 'cmd_test_compile', _record(calls, 'test-compile', 1))
    monkeypatch.setattr(build, 'cmd_module_tests', _record(calls, 'module-tests', 0))

    rc = build.cmd_verify(None)

    assert rc == 1
    assert 'module-tests' not in calls
    assert calls == ['quality-gate', 'test-compile']


def test_verify_short_circuits_before_test_compile_on_quality_gate_failure(monkeypatch):
    """A non-zero quality-gate return aborts cmd_verify before test-compile."""
    calls: list[str] = []
    monkeypatch.setattr(build, 'cmd_quality_gate', _record(calls, 'quality-gate', 1))
    monkeypatch.setattr(build, 'cmd_test_compile', _record(calls, 'test-compile', 0))
    monkeypatch.setattr(build, 'cmd_module_tests', _record(calls, 'module-tests', 0))

    rc = build.cmd_verify(None)

    assert rc == 1
    assert calls == ['quality-gate']
