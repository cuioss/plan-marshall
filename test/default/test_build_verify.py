# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``build.py`` ``cmd_verify`` orchestration and the mypy scope guards.

The second half of this module covers the exclude-aware emptiness guard that
keeps scoped ``compile`` / ``test-compile`` truthful for "thin" modules whose
every Python file is removed by the ``[tool.mypy] exclude`` patterns. Those
tests derive the affected module set from the real tree on each run rather than
pinning a hand-listed sample.

``cmd_verify`` wires ``cmd_test_compile`` in between the
quality-gate and module-tests steps. These tests pin that ordering and the
short-circuit contract by monkeypatching ``cmd_verify``'s three direct
collaborators (``cmd_quality_gate`` / ``cmd_test_compile`` / ``cmd_module_tests``)
so the orchestration is exercised in isolation — no real mypy/ruff/pytest run
and no coupling to the tree's live SPDX/type state. The repo root is on the
pytest path (``[tool.pytest.ini_options]``), so the root ``build`` module imports
by bare name.
"""

from pathlib import Path

import build
import pytest

# build.py resolves every path relative to the repo root, so the real-tree tests
# below pin cwd there instead of trusting whatever directory pytest was started
# from. The root is derived from the imported module, never hard-coded.
REPO_ROOT = Path(build.__file__).resolve().parent
BUNDLES_ROOT = REPO_ROOT / 'marketplace' / 'bundles'
TESTS_ROOT = REPO_ROOT / 'test'


@pytest.fixture
def repo_root_cwd(monkeypatch):
    """Pin cwd to the repo root and stub the (slow, irrelevant) MYPYPATH walk."""
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setattr(build, '_compute_mypypath', lambda: '')
    return REPO_ROOT


def _run_recorder(calls: list[list[str]], rc: int = 0):
    """Return a ``build.run`` stub that records argv and yields ``rc``."""

    def _stub(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        calls.append(cmd)
        return rc

    return _stub


def _child_dirs(root: Path) -> list[str]:
    """Return the names of ``root``'s immediate subdirectories, sorted."""
    return sorted(child.name for child in root.iterdir() if child.is_dir())


def _naive_has_py(directory: Path) -> bool:
    """The exclude-BLIND predicate: does any ``.py`` file exist under ``directory``?

    This is the shape of predicate the guard must NOT use — it is reproduced here
    only so the tests can prove the exclude-aware predicate diverges from it on
    the real tree.
    """
    return any(directory.rglob('*.py'))


def _fully_excluded(names: list[str], root: Path) -> list[str]:
    """Return the subdirectories of ``root`` that contain .py files mypy excludes wholly."""
    return [
        name for name in names
        if _naive_has_py(root / name) and not build._mypy_collects_any(str(root.relative_to(REPO_ROOT) / name))
    ]


def _collectable(names: list[str], root: Path) -> list[str]:
    """Return the subdirectories of ``root`` where at least one file survives mypy's excludes."""
    return [
        name for name in names
        if build._mypy_collects_any(str(root.relative_to(REPO_ROOT) / name))
    ]


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


# ---------------------------------------------------------------------------
# Exclude-aware emptiness guard (scoped compile / test-compile)
#
# The affected bundle set is DERIVED from the real tree on every run, never
# hand-listed: a hand-listed pair is a sample, and a sample stops covering the
# class the moment a new thin bundle lands.
# ---------------------------------------------------------------------------


def test_exclude_aware_predicate_diverges_from_naive_py_count_on_the_real_tree(repo_root_cwd):
    """At least one real bundle has .py files yet nothing mypy would collect.

    This is the anchor for every skip assertion below: if the derived population
    were empty, those tests would pass vacuously while proving nothing. It is
    also the regression statement for the predicate itself — the exclude-blind
    ``any(*.py)`` check says "there is something to check" for exactly these
    bundles, which is why it cannot be used as the emptiness guard.
    """
    bundles = _child_dirs(BUNDLES_ROOT)
    fully_excluded = _fully_excluded(bundles, BUNDLES_ROOT)

    assert fully_excluded, (
        'expected at least one bundle whose .py files are all mypy-excluded; '
        f'scanned {len(bundles)} bundles: {bundles!r}'
    )
    for name in fully_excluded:
        assert _naive_has_py(BUNDLES_ROOT / name), (
            f'{name} must contain a .py file, else it does not demonstrate the divergence'
        )


def test_scoped_compile_skips_mypy_for_every_fully_excluded_bundle(repo_root_cwd, monkeypatch, capsys):
    """compile {bundle} returns 0 without invoking mypy when nothing survives the excludes."""
    fully_excluded = _fully_excluded(_child_dirs(BUNDLES_ROOT), BUNDLES_ROOT)
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls))

    results = {name: build.cmd_compile(name) for name in fully_excluded}

    assert results == dict.fromkeys(fully_excluded, 0), f'expected a clean skip for each of {fully_excluded!r}'
    assert calls == [], f'mypy must not be invoked for a fully-excluded bundle; got {calls!r}'
    out = capsys.readouterr().out
    for name in fully_excluded:
        assert f'skipping mypy for marketplace/bundles/{name}' in out, (
            f'the skip for {name} must be reported on stdout; got {out!r}'
        )
        assert 'exclude patterns' in out, f'the skip must state WHY it skipped; got {out!r}'


def test_scoped_compile_invokes_mypy_for_every_bundle_with_surviving_files(repo_root_cwd, monkeypatch):
    """The guard suppresses nothing for bundles mypy can actually collect from."""
    collectable = _collectable(_child_dirs(BUNDLES_ROOT), BUNDLES_ROOT)
    assert collectable, 'expected at least one bundle with type-checkable sources'
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls))

    for name in collectable:
        build.cmd_compile(name)

    assert calls == [
        ['uv', 'run', 'mypy', f'marketplace/bundles/{name}'] for name in collectable
    ], f'every collectable bundle must reach mypy; got {calls!r}'


def test_scoped_compile_propagates_mypy_failure_when_files_survive(repo_root_cwd, monkeypatch):
    """A real mypy failure stays red — the guard never blanket-maps a non-zero exit to success."""
    collectable = _collectable(_child_dirs(BUNDLES_ROOT), BUNDLES_ROOT)
    assert collectable, 'expected at least one bundle with type-checkable sources'
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls, rc=2))

    rc = build.cmd_compile(collectable[0])

    assert rc == 2
    assert len(calls) == 1


def test_scoped_test_compile_skips_mypy_for_every_fully_excluded_test_dir(repo_root_cwd, monkeypatch):
    """test-compile {module} carries the same guard — verify {bundle} is unsatisfiable without it."""
    fully_excluded = _fully_excluded(_child_dirs(TESTS_ROOT), TESTS_ROOT)
    assert fully_excluded, (
        'expected at least one test directory whose .py files are all mypy-excluded; '
        f'scanned {_child_dirs(TESTS_ROOT)!r}'
    )
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls))

    results = {name: build.cmd_test_compile(name) for name in fully_excluded}

    assert results == dict.fromkeys(fully_excluded, 0)
    assert calls == [], f'mypy must not be invoked for a fully-excluded test dir; got {calls!r}'


def test_scoped_test_compile_propagates_mypy_failure_when_files_survive(repo_root_cwd, monkeypatch):
    """A real mypy failure stays red under test-compile — the guard's second arm.

    ``cmd_compile`` and ``cmd_test_compile`` apply the identical
    guard-then-run pattern, so pinning the propagation on the ``compile`` arm
    alone leaves the symmetric half free to map a genuine mypy failure to
    success. This is the ``test-compile`` mirror of
    ``test_scoped_compile_propagates_mypy_failure_when_files_survive``.
    """
    collectable = _collectable(_child_dirs(TESTS_ROOT), TESTS_ROOT)
    assert collectable, 'expected at least one test directory with type-checkable sources'
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls, rc=2))

    rc = build.cmd_test_compile(collectable[0])

    assert rc == 2
    assert len(calls) == 1, f'mypy must be invoked exactly once; got {calls!r}'


def test_collects_any_distinguishes_surviving_from_excluded_files(repo_root_cwd, tmp_path):
    """The predicate flips on exclude membership, not on the presence of a .py file."""
    excluded_only = tmp_path / 'thin' / 'skills' / 'plan-marshall-plugin'
    excluded_only.mkdir(parents=True)
    (excluded_only / 'extension.py').write_text('x = 1\n', encoding='utf-8')

    assert _naive_has_py(tmp_path / 'thin'), 'fixture must contain a .py file for the divergence to be meaningful'
    assert build._mypy_collects_any(str(tmp_path / 'thin')) is False

    (tmp_path / 'thin' / 'skills' / 'other.py').write_text('y = 1\n', encoding='utf-8')

    assert build._mypy_collects_any(str(tmp_path / 'thin')) is True


def test_collects_any_is_false_for_a_missing_or_non_python_path(repo_root_cwd, tmp_path):
    """A path with nothing to collect is empty, whether it is absent or carries no Python."""
    (tmp_path / 'notes.md').write_text('# notes\n', encoding='utf-8')

    assert build._mypy_collects_any(str(tmp_path / 'absent')) is False
    assert build._mypy_collects_any(str(tmp_path / 'notes.md')) is False
    assert build._mypy_collects_any(str(tmp_path)) is False


def test_exclude_patterns_fail_open_when_pyproject_is_unreadable(monkeypatch, tmp_path):
    """An unreadable config yields no exclusions, so mypy runs rather than being skipped."""
    monkeypatch.chdir(tmp_path)
    package = tmp_path / 'pkg'
    package.mkdir()
    (package / 'mod.py').write_text('z = 1\n', encoding='utf-8')

    assert build._mypy_exclude_patterns() == []
    assert build._mypy_collects_any('pkg') is True


@pytest.mark.parametrize(
    ('exclude_literal', 'type_name'),
    [('true', 'bool'), ('42', 'int'), ('{ dir = "x" }', 'dict')],
)
def test_exclude_patterns_fail_open_when_exclude_is_neither_string_nor_list(
    monkeypatch, tmp_path, capsys, exclude_literal, type_name
):
    """A malformed ``[tool.mypy] exclude`` fails OPEN, as the docstring promises.

    ``pyproject.toml`` is externally-sourced config: a typo such as
    ``exclude = true`` slips past the ``isinstance(raw, str)`` branch and reaches
    ``for entry in raw``, raising an unhandled ``TypeError`` out through
    ``_mypy_collects_any`` into BOTH ``cmd_compile`` and ``cmd_test_compile``.
    The helper documents the opposite contract, so the regression statement is
    "no raise, zero exclusions, mypy still runs, and a diagnostic that names the
    offending type". The parametrisation spans three non-list types so the guard
    is type-general rather than special-cased to the reported ``bool``.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'pyproject.toml').write_text(
        f'[tool.mypy]\nexclude = {exclude_literal}\n', encoding='utf-8'
    )
    package = tmp_path / 'pkg'
    package.mkdir()
    (package / 'mod.py').write_text('z = 1\n', encoding='utf-8')

    patterns = build._mypy_exclude_patterns('compile')

    assert patterns == [], f'a malformed exclude must yield no exclusions; got {patterns!r}'
    assert build._mypy_collects_any('pkg') is True, 'failing open must leave mypy something to check'
    err = capsys.readouterr().err
    assert err.startswith('compile: '), f'the diagnostic must name the calling command; got {err!r}'
    assert type_name in err, f'the diagnostic must name the offending type; got {err!r}'


def test_exclude_patterns_diagnostic_names_the_calling_command(monkeypatch, tmp_path, capsys):
    """The unreadable-config diagnostic is attributed to the command that hit it.

    ``_mypy_exclude_patterns`` is reachable from BOTH ``compile`` and
    ``test-compile``. A hardcoded ``compile:`` prefix would send an operator
    running ``test-compile`` to the wrong command, so the label is threaded from
    the caller. The whole point is that the two commands produce DIFFERENT
    prefixes — asserting one in isolation would pass against a hardcoded literal.
    """
    monkeypatch.chdir(tmp_path)

    build._mypy_exclude_patterns('test-compile')
    test_compile_err = capsys.readouterr().err
    build._mypy_exclude_patterns('compile')
    compile_err = capsys.readouterr().err

    assert test_compile_err.startswith('test-compile: '), (
        f'the diagnostic must name the calling command; got {test_compile_err!r}'
    )
    assert compile_err.startswith('compile: '), (
        f'the diagnostic must name the calling command; got {compile_err!r}'
    )


def test_whole_tree_compile_omits_claude_dir_when_all_its_py_files_are_excluded(
    repo_root_cwd, monkeypatch, tmp_path
):
    """The .claude/ guard is exclude-aware: an excluded-only .claude/ is not passed to mypy.

    The exclude-blind ``any(CLAUDE_DIR.rglob('*.py'))`` predicate this replaces
    passes here — the directory plainly holds a .py file — and mypy would then
    collect nothing from it and exit 2.
    """
    claude = tmp_path / '.claude'
    (claude / 'worktrees' / 'other-branch').mkdir(parents=True)
    (claude / 'worktrees' / 'other-branch' / 'script.py').write_text('a = 1\n', encoding='utf-8')
    monkeypatch.setattr(build, 'CLAUDE_DIR', claude)
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls))

    rc = build.cmd_compile(None)

    assert rc == 0
    assert _naive_has_py(claude), 'fixture must satisfy the exclude-blind predicate to pin the regression'
    assert calls == [['uv', 'run', 'mypy', 'marketplace/bundles']], (
        f'.claude/ must be omitted when nothing there survives the excludes; got {calls!r}'
    )


def test_whole_tree_compile_includes_claude_dir_when_a_file_survives(repo_root_cwd, monkeypatch, tmp_path):
    """A .claude/ with collectable sources is still type-checked."""
    claude = tmp_path / '.claude'
    (claude / 'skills').mkdir(parents=True)
    (claude / 'skills' / 'helper.py').write_text('b = 1\n', encoding='utf-8')
    monkeypatch.setattr(build, 'CLAUDE_DIR', claude)
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls))

    rc = build.cmd_compile(None)

    assert rc == 0
    assert calls == [['uv', 'run', 'mypy', 'marketplace/bundles', str(claude)]]
