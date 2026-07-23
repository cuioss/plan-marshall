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


def test_module_tests_emits_per_session_basetemp_flag(monkeypatch):
    """cmd_module_tests's pytest cmd carries a per-session --basetemp under the root.

    Guards the per-session basetemp contract: each invocation must pass an
    explicit ``--basetemp`` pointing under ``.plan/temp/pytest-basetemp/`` so
    concurrent worktrees and killed-then-restarted sessions never share the
    default ``pytest-of-{user}`` root whose keep-last-3 cleanup races.
    """
    captured: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        captured['cmd'] = cmd
        return 0

    monkeypatch.setattr(build, 'run', fake_run)
    monkeypatch.setattr(build, '_prune_basetemp_roots', lambda *a, **k: None)
    monkeypatch.setattr(build.Path, 'mkdir', lambda *a, **k: None)
    monkeypatch.setattr(build, 'get_test_path', lambda module: 'test')

    rc = build.cmd_module_tests(None)

    assert rc == 0
    cmd = captured['cmd']
    matches = [a for a in cmd if a.startswith('--basetemp=')]
    assert len(matches) == 1, f'expected exactly one --basetemp flag; got {matches!r} in {cmd!r}'
    basetemp = matches[0][len('--basetemp='):]
    assert basetemp.startswith('.plan/temp/pytest-basetemp/'), (
        f'cmd_module_tests --basetemp must point under .plan/temp/pytest-basetemp/; got {basetemp!r}'
    )


def test_module_tests_distinct_invocations_do_not_collide(monkeypatch):
    """Two cmd_module_tests invocations yield distinct per-session --basetemp paths."""
    seen: list[str] = []

    def fake_run(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        seen.append(next(a[len('--basetemp='):] for a in cmd if a.startswith('--basetemp=')))
        return 0

    monkeypatch.setattr(build, 'run', fake_run)
    monkeypatch.setattr(build, '_prune_basetemp_roots', lambda *a, **k: None)
    monkeypatch.setattr(build.Path, 'mkdir', lambda *a, **k: None)
    monkeypatch.setattr(build, 'get_test_path', lambda module: 'test')

    build.cmd_module_tests(None)
    build.cmd_module_tests(None)

    assert len(seen) == 2
    assert seen[0] != seen[1], f'invocations must not collide; got {seen[0]!r} twice'
