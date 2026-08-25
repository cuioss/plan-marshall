# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``build.py`` ``cmd_verify`` orchestration and the mypy scope guards.

The second half of this module covers the exclude-aware emptiness guard that
keeps scoped ``compile`` / ``test-compile`` truthful for "thin" modules whose
every Python file is removed by the ``[tool.mypy] exclude`` patterns. Those
tests derive the affected module set from the real tree on each run rather than
pinning a hand-listed sample.

The third section covers the executor-substrate bootstrap the whole-tree
quality-gate runs before the marketplace-wide plugin-doctor sweep: the cluster's
accept-set comes from a git-ignored file a fresh clone does not carry, so
without it CI reports that it could not look instead of looking.

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
    """Return a stub that records its label and yields the given return code.

    The stub accepts ``boundary`` because the refactored ``cmd_verify`` threads a
    :class:`CoverageBoundary` into ``cmd_quality_gate`` / ``cmd_test_compile`` (and
    ``parallel`` into ``cmd_module_tests``); a stub that rejected the kwarg would
    fail with a spurious ``TypeError`` rather than exercising the orchestration.
    """

    def _stub(module, parallel: bool = True, boundary=None) -> int:
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
        ['uv', 'run', 'mypy', '--no-incremental', f'marketplace/bundles/{name}'] for name in collectable
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
    assert calls == [['uv', 'run', 'mypy', '--no-incremental', 'marketplace/bundles']], (
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
    assert calls == [['uv', 'run', 'mypy', '--no-incremental', 'marketplace/bundles', str(claude)]]


# ---------------------------------------------------------------------------
# Freshness (D4) and coverage boundary (D5)
#
# The gate must be a truthful proxy for a cold CI run: it runs mypy with the
# incremental cache disabled (so a stale cache can no longer produce a clean
# verdict), backstops that with a duration sanity check (an implausibly fast
# success over a substantial file set is treated as suspect, not reassurance),
# and its own output names its coverage boundary (a partially-checked footprint
# is distinguishable from one that genuinely passed).
# ---------------------------------------------------------------------------


def _ticks(*values: float):
    """Return a build.time.monotonic replacement yielding the given values in order."""
    seq = iter(values)
    return lambda: next(seq)


def test_compile_runs_mypy_cold_with_no_incremental(repo_root_cwd, monkeypatch):
    """Every mypy invocation carries --no-incremental — the gate runs cold like CI.

    This is the deterministic close of the stale-cache hole (D4): a warm
    incremental cache cannot answer a gate that never consults it.
    """
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls))

    build.cmd_compile(None)

    assert calls, 'mypy must have been invoked'
    assert '--no-incremental' in calls[0], (
        f'the gate must run mypy cold (--no-incremental) to match CI; got {calls[0]!r}'
    )


def test_quality_gate_fails_closed_when_whole_tree_mypy_reports_implausibly_fast(
    repo_root_cwd, monkeypatch, capsys
):
    """A whole-tree mypy 'success' in zero wall-time is not trusted — the gate fails closed (D4).

    Models the stale-cache no-op: mypy exits 0 having analysed nothing. Over the
    substantial whole-tree file set that is impossibly fast, so the freshness
    backstop converts the clean verdict into a non-clean one rather than reading
    it as reassurance.
    """
    monkeypatch.setattr(build, 'run', _run_recorder([], rc=0))
    monkeypatch.setattr(build, 'check_spdx_headers', lambda paths: [])
    monkeypatch.setattr(build, 'ensure_executor_substrate', lambda: 0)
    # start == end → zero elapsed → infinite throughput over the whole tree.
    monkeypatch.setattr(build.time, 'monotonic', _ticks(100.0, 100.0))

    rc = build.cmd_quality_gate(None)

    assert rc != 0, 'an implausibly fast whole-tree type-check must not report a clean pass'
    captured = capsys.readouterr()
    assert 'FRESHNESS SUSPECT' in captured.err
    assert 'PARTIAL' in captured.out, 'the coverage verdict must be PARTIAL, not silent'


def test_quality_gate_does_not_flag_a_plausibly_timed_whole_tree_run(repo_root_cwd, monkeypatch, capsys):
    """A whole-tree mypy success that took real time is NOT flagged (D4, negative direction).

    A check that cried wolf on every run would be disabled within a week, so the
    negative direction is load-bearing: a legitimately-timed cold run passes clean.
    """
    monkeypatch.setattr(build, 'run', _run_recorder([], rc=0))
    monkeypatch.setattr(build, 'check_spdx_headers', lambda paths: [])
    monkeypatch.setattr(build, 'ensure_executor_substrate', lambda: 0)
    # 30 s over the whole tree — a plausible cold analysis.
    monkeypatch.setattr(build.time, 'monotonic', _ticks(100.0, 130.0))

    rc = build.cmd_quality_gate(None)

    assert rc == 0
    out = capsys.readouterr().out
    assert 'FRESHNESS SUSPECT' not in out
    assert 'coverage: COMPLETE' in out


def test_verify_prints_complete_coverage_summary_on_success(monkeypatch, capsys):
    """A fully-checked verify names its coverage as COMPLETE (D5)."""
    calls: list[str] = []
    monkeypatch.setattr(build, 'cmd_quality_gate', _record(calls, 'quality-gate', 0))
    monkeypatch.setattr(build, 'cmd_test_compile', _record(calls, 'test-compile', 0))
    monkeypatch.setattr(build, 'cmd_module_tests', _record(calls, 'module-tests', 0))

    rc = build.cmd_verify(None)

    assert rc == 0
    assert 'coverage: COMPLETE' in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Executor-substrate bootstrap (whole-tree quality-gate only)
#
# The marketplace-wide plugin-doctor gate derives the argument-naming cluster's
# whole accept-set from `.plan/execute-script.py`, which is git-ignored — so the
# fresh clone CI runs on carries none, and the cluster reports
# ARGUMENT_NAMING_SUBSTRATE_ABSENT rather than judging the corpus. These tests
# pin the bootstrap that makes the population reachable in CI, and — the half
# that matters — that it FAILS CLOSED: a gate that proceeds without the
# substrate reinstates the false-clean the rule exists to remove.
# ---------------------------------------------------------------------------

_EXPECTED_GENERATOR_ARGV = [
    'python3',
    str(
        build.BUNDLES_DIR / 'plan-marshall' / 'skills' / 'tools-script-executor'
        / 'scripts' / 'generate_executor.py'
    ),
    'generate',
    '--marketplace',
    '--marketplace-root',
    '.',
]


def _executor_writing_run(calls: list[list[str]], target: Path, rc: int = 0):
    """A ``build.run`` stub that records argv and materializes ``target`` on success."""

    def _stub(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        calls.append(cmd)
        if rc == 0:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('SCRIPTS = {\n}\n', encoding='utf-8')
        return rc

    return _stub


def test_executor_bootstrap_is_a_noop_when_the_substrate_already_exists(monkeypatch, tmp_path):
    """A developer machine's own executor is never regenerated by the gate.

    The bootstrap exists for the fresh checkout. Overwriting an executor that is
    already there would let the gate replace a local (possibly newer) one as a
    side effect of linting.
    """
    monkeypatch.chdir(tmp_path)
    executor = tmp_path / '.plan' / 'execute-script.py'
    executor.parent.mkdir(parents=True)
    executor.write_text('SCRIPTS = {\n}\n', encoding='utf-8')
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls))

    assert build.ensure_executor_substrate() == 0
    assert calls == [], f'an existing executor must not be regenerated; got {calls!r}'


def test_executor_bootstrap_generates_by_direct_path_when_absent(monkeypatch, tmp_path):
    """An absent executor is generated, and the generator is invoked BY PATH.

    The argv is asserted whole rather than probed for a substring: the file this
    step creates cannot be the thing that dispatches its own creation, so routing
    the call through `.plan/execute-script.py` would be circular and is the one
    spelling that must never appear here.
    """
    monkeypatch.chdir(tmp_path)
    executor = tmp_path / '.plan' / 'execute-script.py'
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _executor_writing_run(calls, executor))

    assert build.ensure_executor_substrate() == 0
    assert calls == [_EXPECTED_GENERATOR_ARGV], f'unexpected bootstrap argv: {calls!r}'
    assert executor.is_file()


def test_executor_bootstrap_propagates_a_generator_failure(monkeypatch, tmp_path, capsys):
    """A failed generation halts rather than handing plugin-doctor an empty registry.

    Running the cluster anyway would produce a substrate-absent finding whose real
    cause is this step, sending a reader to triage the corpus instead of the
    bootstrap.
    """
    monkeypatch.chdir(tmp_path)
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls, rc=2))

    rc = build.ensure_executor_substrate()

    assert rc == 2, 'the generator exit code must be propagated, not remapped'
    assert 'no notation registry' in capsys.readouterr().err


def test_executor_bootstrap_rejects_a_zero_exit_that_produced_no_file(monkeypatch, tmp_path, capsys):
    """A clean exit code is not evidence the file landed — the effect is verified.

    Same contract the manage-* scripts carry: an operation failure exits zero and
    reports itself in its payload. Trusting the exit code alone would let the gate
    proceed into exactly the absent-substrate state this step exists to remove.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build, 'run', _run_recorder([], rc=0))

    rc = build.ensure_executor_substrate()

    assert rc != 0, 'a zero exit with no executor on disk must not read as success'
    assert 'does not exist' in capsys.readouterr().err


def test_whole_tree_quality_gate_halts_before_plugin_doctor_when_the_bootstrap_fails(
    repo_root_cwd, monkeypatch
):
    """The gate is composed so the bootstrap gates plugin-doctor, not merely precedes it.

    Asserted through the real ``cmd_quality_gate`` rather than by reading the two
    functions: the failure this pins is an ordering that runs plugin-doctor anyway,
    which no unit test of either half can see.
    """
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls))
    monkeypatch.setattr(build, 'check_spdx_headers', lambda paths: [])
    monkeypatch.setattr(build.time, 'monotonic', _ticks(100.0, 130.0))
    monkeypatch.setattr(build, 'ensure_executor_substrate', lambda: 7)

    rc = build.cmd_quality_gate(None)

    assert rc == 7
    assert not any('doctor-marketplace.py' in ' '.join(cmd) for cmd in calls), (
        f'plugin-doctor must not run without its substrate; got {calls!r}'
    )


def test_whole_tree_quality_gate_reaches_plugin_doctor_once_the_bootstrap_clears(
    repo_root_cwd, monkeypatch
):
    """Matched positive control: a cleared bootstrap does reach the marketplace sweep.

    Without it the halt test above is satisfied by a gate that never runs
    plugin-doctor at all.
    """
    calls: list[list[str]] = []
    monkeypatch.setattr(build, 'run', _run_recorder(calls))
    monkeypatch.setattr(build, 'check_spdx_headers', lambda paths: [])
    monkeypatch.setattr(build.time, 'monotonic', _ticks(100.0, 130.0))
    monkeypatch.setattr(build, 'ensure_executor_substrate', lambda: 0)

    rc = build.cmd_quality_gate(None)

    assert rc == 0
    assert any('doctor-marketplace.py' in ' '.join(cmd) for cmd in calls), (
        f'the marketplace-wide sweep must run when the substrate is present; got {calls!r}'
    )


def test_verify_prints_partial_coverage_when_a_step_is_freshness_suspect(monkeypatch, capsys):
    """A freshness-suspect step makes verify's verdict PARTIAL and names the un-certified dimension (D4+D5).

    The cold-read property: shown this verdict for a partially-checked footprint
    and asked 'is it safe to push?', a reader must read NO — mypy(test) was not
    certified — never a clean pass.
    """
    def _fresh_suspect_test_compile(module, boundary=None):
        boundary.record_degraded('mypy(test)', 'freshness suspect — reported success implausibly fast')
        return build._FRESHNESS_SUSPECT_RC

    monkeypatch.setattr(build, 'cmd_quality_gate', _record([], 'quality-gate', 0))
    monkeypatch.setattr(build, 'cmd_test_compile', _fresh_suspect_test_compile)
    monkeypatch.setattr(build, 'cmd_module_tests', _record([], 'module-tests', 0))

    rc = build.cmd_verify(None)

    assert rc == build._FRESHNESS_SUSPECT_RC
    out = capsys.readouterr().out
    assert 'PARTIAL' in out
    assert 'mypy(test)' in out
    assert 'NOT a full pass' in out
