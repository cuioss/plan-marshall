#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population-derived regression tests for the build-class ledger-stamp discriminator.

The executor dispatch boundary stamps a ``kind=build`` change-ledger row only for
a dispatch that ACTUALLY runs a build. Build-class-ness is the CONJUNCTION of two
conditions -- a notation under a ``build-*`` skill AND a build-executing
subcommand -- and this module pins both halves plus their interaction.

Why the conjunction is load-bearing: ``pre-commit-verify-freshness`` accepts a
``kind=build`` row carrying ``status: success`` at the current ``worktree_sha``
as proof that the working tree was built. A pure query verb under a build wrapper
-- and a bare ``--help``, which carries no subcommand at all -- exits 0 without
building anything, so a row stamped for it satisfies that gate with no build
having run. That is a confident green derived from an undetermined signal.

The subcommand population is DERIVED, never declared: ``build_class_roster()``
introspects each wrapper's real argparse parser, so a subcommand added to any
wrapper later joins these assertions with no edit here. The notation population
comes from the separately-sourced ``build_class_prefixes()`` read of the
template's own ``_BUILD_CLASS_PREFIXES``. The two derivations share no input.

**Ledger isolation.** This module renders and dispatches a real executor, which
writes to the change-ledger resolved by ``file_ops.get_tracked_config_dir()``. A
row written into the PRODUCTION ledger by the test suite would satisfy the
production freshness gate -- the suite would be manufacturing the very false
signal these tests exist to prevent. The module-scoped :func:`_isolated_ledger`
fixture therefore redirects that resolution to a temporary directory for the
whole module, and :func:`test_ledger_path_is_redirected_away_from_production`
asserts the redirect is actually in force rather than assuming it.

**Template render helper.** :func:`_render_executor` substitutes the
``execute-script.py.template`` placeholders and writes the result. It is one of
the test-local render helpers a template-contract change must sweep: per-task
quality-gate and test-compile validate the template in isolation, so a desynced
renderer is caught only by a whole-tree module-tests run.
"""

from __future__ import annotations

import json
import os
import subprocess
import types
from pathlib import Path

import pytest
from _build_class_roster import build_class_domain, build_class_prefixes, build_class_roster

from conftest import _MARKETPLACE_SCRIPT_DIRS, PROJECT_ROOT

_SKILL_DIR = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'tools-script-executor'
_TEMPLATE_PATH = _SKILL_DIR / 'templates' / 'execute-script.py.template'
_LOGGING_DIR = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-logging' / 'scripts'
_PRODUCTION_LEDGER = PROJECT_ROOT / '.plan' / 'work' / 'change-ledger.jsonl'


# =============================================================================
# Ledger isolation for the whole module
# =============================================================================


@pytest.fixture(scope='module', autouse=True)
def _isolated_ledger(tmp_path_factory):
    """Redirect the change-ledger away from the production tree for this module.

    Both resolution rungs ``get_tracked_config_dir()`` consults are pinned: the
    ``set_base_dir`` override (rung 1) and the ``PLAN_BASE_DIR`` environment
    variable (rung 3, which the dispatched subprocesses inherit). Pinning only
    one of the two would leave the other free to resolve back to the repo.
    """
    import file_ops

    root = tmp_path_factory.mktemp('discriminator-ledger-root')
    patch = pytest.MonkeyPatch()
    patch.setenv('PLAN_BASE_DIR', str(root))
    patch.setattr(file_ops, '_BASE_DIR_OVERRIDE', root, raising=False)
    yield root
    patch.undo()


def _subprocess_env() -> dict[str, str]:
    """Build the subprocess environment with the marketplace script dirs on PYTHONPATH."""
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    return env


def _render_code(mappings: dict[str, Path]) -> str:
    """Substitute every ``execute-script.py.template`` placeholder and return the source."""
    code: str = _TEMPLATE_PATH.read_text(encoding='utf-8')
    rendered = ''.join(f'    "{notation}": "{path}",\n' for notation, path in mappings.items())
    code = code.replace('{{SCRIPT_MAPPINGS}}', rendered)
    code = code.replace('{{SUBCOMMAND_MAPPINGS}}', '')
    code = code.replace('{{LOGGING_DIR}}', str(_LOGGING_DIR))
    code = code.replace('{{SHARED_MODULE_DIRS}}', '# (none in test)')
    code = code.replace('{{EXTRA_SCRIPT_DIRS}}', '')
    code = code.replace('{{PLAN_DIR_NAME}}', '.plan')
    code = code.replace('{{EXECUTOR_TARGET}}', 'claude')
    code = code.replace('{{GENERATED_VERSION}}', '0.0.0-test')
    code = code.replace('{{MAPPINGS_FINGERPRINT}}', 'test-fingerprint')
    return code.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None\n',
    )


def _render_executor(target_path: Path, mappings: dict[str, Path]) -> None:
    """Write the rendered template to ``target_path`` with ``mappings`` registered."""
    target_path.write_text(_render_code(mappings), encoding='utf-8')


def _load_executor_module() -> types.ModuleType:
    """Exec the rendered template in-process so its predicate can be called directly.

    Rendered in memory: writing a probe file next to the template would pollute
    the marketplace source tree the suite is asserting against.
    """
    module = types.ModuleType('execute_script_discriminator')
    module.__dict__['__file__'] = str(_TEMPLATE_PATH)
    exec(_render_code({}), module.__dict__)
    return module


def _build_class_notations() -> dict[str, dict[str, bool]]:
    """Return the roster entries whose notation the executor treats as build-class.

    Intersecting the two independently-derived populations is what makes the
    universality assertion below a real check: the subcommands come from each
    wrapper's own argparse parser, the notation filter from the executor
    template's own prefix declaration.
    """
    prefixes = tuple(build_class_prefixes())
    return {
        notation: subcommands
        for notation, subcommands in build_class_roster().items()
        if notation.startswith(prefixes)
    }


# =============================================================================
# The discriminator predicate
# =============================================================================


def test_build_executing_subcommands_is_the_single_run_verb():
    """The allow-list holds exactly the one verb that runs a build.

    Pinned as a literal so WIDENING the allow-list is a deliberate, reviewed
    edit. An allow-list is the fail-closed shape here: a query verb added to a
    wrapper later is excluded by default, whereas a deny-list of known query
    verbs would silently admit it and re-open the false-fresh hole.
    """
    executor = _load_executor_module()

    assert executor._BUILD_EXECUTING_SUBCOMMANDS == frozenset({'run'}), (
        f'the build-executing allow-list is {set(executor._BUILD_EXECUTING_SUBCOMMANDS)!r}; '
        'widening it lets another verb stamp a kind=build row that the freshness '
        'gate will accept as proof of a build.'
    )


def test_predicate_sweep_covers_the_whole_build_class_domain_not_just_the_roster():
    """The sweep population must equal the predicate's domain, not a subset of it.

    ``build_class_roster()`` discovers scripts that route through
    ``_build_cli.build_main``; ``_is_build_class_notation`` accepts ANY notation
    under ``_BUILD_CLASS_PREFIXES``. Those two sets are not the same, and where
    the roster is the smaller one the universality sweep below silently asserts
    less than its name claims — the population-derived-detector failure mode this
    suite exists to prevent, pointed at the suite itself.

    This test pins the containment direction that actually bites (domain not
    covered by the roster) and sweeps the predicate over the FULL domain, so a
    build-class script that never enters the roster still has every subcommand
    checked.
    """
    executor = _load_executor_module()
    executing = executor._BUILD_EXECUTING_SUBCOMMANDS
    domain = build_class_domain()
    roster = _build_class_notations()

    assert domain, (
        'no script matched the executor build-class prefixes -- the domain '
        'derivation is vacuous and this sweep covers nothing.'
    )
    assert set(roster) <= set(domain), (
        f'roster notations {sorted(set(roster) - set(domain))!r} are absent from the '
        'derived build-class domain -- the two derivations disagree about which '
        'notations are build-class.'
    )

    swept_true = 0
    swept_false = 0
    for notation, subcommands in domain.items():
        # A zero-subcommand entry is legitimate, not vacuous: the ``extension``
        # modules sit under a build-class prefix and register no CLI at all, so
        # they contribute no dispatchable subcommand to partition. The
        # anti-vacuity anchor below is therefore domain-level, not per-script.
        for subcommand in subcommands:
            expected = subcommand in executing
            actual = executor._is_build_class_notation(notation, subcommand)
            assert actual is expected, (
                f'_is_build_class_notation({notation!r}, {subcommand!r}) returned {actual!r}, '
                f'expected {expected!r}: a build-class row is stamped for the '
                f'build-executing verb only, across the whole domain.'
            )
            if expected:
                swept_true += 1
            else:
                swept_false += 1

    assert swept_true and swept_false, (
        f'the domain sweep observed {swept_true} build-executing and {swept_false} query '
        'subcommands -- it must see BOTH partitions or it pins only one side of the '
        'discriminator.'
    )
    assert set(domain) - set(roster), (
        'the derived domain adds no notation beyond the roster, so this sweep is a '
        'restatement of the roster sweep rather than the wider check it claims to be. '
        'If every build-class script now routes through build_main, delete this test '
        'rather than letting it stand as a vacuous duplicate.'
    )


def test_predicate_is_true_exactly_for_the_build_executing_verb_across_the_roster():
    """Population-derived universality: True iff the subcommand is build-executing.

    Sweeps EVERY registered subcommand of EVERY build-class wrapper, so a
    subcommand added to any wrapper joins this assertion with no edit here. The
    two coverage counters below are the anti-vacuity anchor: without them a
    roster that degraded to an empty (or all-query, or all-run) population would
    let this test pass while asserting nothing.
    """
    executor = _load_executor_module()
    executing = executor._BUILD_EXECUTING_SUBCOMMANDS
    roster = _build_class_notations()

    assert roster, (
        'no roster notation matched the executor build-class prefixes -- the two '
        'populations have drifted apart and this sweep covers nothing.'
    )

    expected_true = 0
    expected_false = 0
    for notation, subcommands in roster.items():
        for subcommand in subcommands:
            expected = subcommand in executing
            actual = executor._is_build_class_notation(notation, subcommand)
            assert actual is expected, (
                f'_is_build_class_notation({notation!r}, {subcommand!r}) returned {actual!r}, '
                f'expected {expected!r}: a build-class row is stamped for the build-executing '
                f'verb only.'
            )
            if expected:
                expected_true += 1
            else:
                expected_false += 1

    assert expected_true, 'no build-executing subcommand was covered -- the sweep is vacuous.'
    assert expected_false, 'no query subcommand was covered -- the sweep proves no narrowing.'


def test_predicate_is_false_for_the_empty_subcommand():
    """A bare ``--help``-style dispatch carries no subcommand and stamps nothing.

    This is the shape that originally wrote false rows: ``--help`` probes exit 0
    under a build-* notation, and the prefix-only predicate stamped every one of
    them ``kind=build / status=success``.
    """
    executor = _load_executor_module()

    for notation in _build_class_notations():
        assert executor._is_build_class_notation(notation, '') is False, (
            f'{notation!r} dispatched with no subcommand was treated as build-class; '
            'a bare --help probe must stamp no ledger row.'
        )


def test_predicate_is_false_for_a_non_build_class_notation_with_the_run_verb():
    """Negative control on the OTHER conjunct -- the subcommand alone is not enough.

    Without this, a predicate that had collapsed to "subcommand == run" would
    satisfy every assertion above while stamping build rows for unrelated skills.
    """
    executor = _load_executor_module()

    assert executor._is_build_class_notation('plan-marshall:manage-files:manage-files', 'run') is False, (
        'a non-build-class notation was treated as build-class on the strength of '
        'its subcommand alone -- the prefix conjunct is not being evaluated.'
    )


# =============================================================================
# Ledger isolation
# =============================================================================


def test_ledger_path_is_redirected_away_from_production(_isolated_ledger):
    """The module's ledger writes land in the temp root, never in the repo ledger.

    Asserted rather than assumed: a redirect that silently failed would make the
    dispatch tests below append rows to the production ledger, where the real
    ``pre-commit-verify-freshness`` gate would accept them.
    """
    from _ledger_core import resolve_ledger_path

    resolved = resolve_ledger_path()

    assert resolved.is_relative_to(_isolated_ledger), (
        f'the change-ledger resolved to {resolved} -- outside the isolated root '
        f'{_isolated_ledger}. This module must never write into a shared ledger.'
    )
    assert resolved != _PRODUCTION_LEDGER, (
        f'the change-ledger resolved to the production path {resolved}.'
    )


# =============================================================================
# Dispatch boundary: query writes no row, run does
# =============================================================================


def _dispatch(tmp_path: Path, notation: str, argv: list[str]) -> list[dict]:
    """Dispatch a stubbed build wrapper through a rendered executor; return the ledger rows.

    The stub prints a ``status: success`` payload and exits 0 -- exactly what a
    pure query verb does -- so the ONLY thing distinguishing the two cases below
    is the dispatched subcommand.
    """
    stub_script = tmp_path / 'stub_build.py'
    stub_script.write_text(
        '#!/usr/bin/env python3\nimport sys\nsys.stdout.write("status: success")\nsys.exit(0)\n',
        encoding='utf-8',
    )

    executor_path = tmp_path / 'execute-script.py'
    _render_executor(executor_path, {notation: stub_script})

    ledger_root = tmp_path / 'plan-base'
    ledger_root.mkdir()

    env = _subprocess_env()
    env['PLAN_BASE_DIR'] = str(ledger_root)
    result = subprocess.run(
        ['python3', str(executor_path), notation, *argv],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f'the executor must propagate the stub exit code 0, got {result.returncode} '
        f'(stderr: {result.stderr!r})'
    )

    ledger = ledger_root / 'work' / 'change-ledger.jsonl'
    if not ledger.is_file():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines() if line.strip()]


def _a_query_subcommand() -> tuple[str, str]:
    """Return a ``(notation, query_subcommand)`` pair derived from the live roster."""
    executor = _load_executor_module()
    executing = executor._BUILD_EXECUTING_SUBCOMMANDS
    for notation, subcommands in sorted(_build_class_notations().items()):
        for subcommand in sorted(subcommands):
            if subcommand not in executing:
                return notation, subcommand
    raise AssertionError(
        'no query subcommand exists on any build wrapper -- the roster derivation '
        'has degraded and the narrowing below cannot be exercised.'
    )


def _a_build_executing_subcommand() -> tuple[str, str]:
    """Return a ``(notation, build_executing_subcommand)`` pair derived from the live roster."""
    executor = _load_executor_module()
    executing = executor._BUILD_EXECUTING_SUBCOMMANDS
    for notation, subcommands in sorted(_build_class_notations().items()):
        for subcommand in sorted(subcommands):
            if subcommand in executing:
                return notation, subcommand
    raise AssertionError(
        'no build-executing subcommand exists on any build wrapper -- the roster '
        'derivation has degraded and the positive control cannot be exercised.'
    )


def test_query_dispatch_appends_no_build_row(tmp_path):
    """A query verb under a build wrapper writes NO ``kind=build`` row."""
    notation, subcommand = _a_query_subcommand()

    entries = _dispatch(tmp_path, notation, [subcommand])

    build_rows = [entry for entry in entries if entry.get('kind') == 'build']
    assert not build_rows, (
        f'{notation} {subcommand} wrote {len(build_rows)} kind=build row(s) despite running '
        f'no build: {build_rows!r}. The freshness gate accepts such a row as proof the '
        f'working tree was built.'
    )


def test_run_dispatch_still_appends_the_build_row(tmp_path):
    """Matched positive control: the build-executing verb still stamps its row.

    Without this the narrowing could have disabled the stamp entirely and the
    negative test above would still pass -- for the wrong reason.
    """
    notation, subcommand = _a_build_executing_subcommand()

    entries = _dispatch(tmp_path, notation, [subcommand])

    build_rows = [entry for entry in entries if entry.get('kind') == 'build']
    assert len(build_rows) == 1, (
        f'{notation} {subcommand} wrote {len(build_rows)} kind=build row(s); a build-executing '
        f'dispatch must still stamp exactly one.'
    )
    assert build_rows[0]['status'] == 'success', (
        f'the build-executing row carries status={build_rows[0]["status"]!r}; the truthful '
        'derivation is unchanged by the narrowing.'
    )


# =============================================================================
# Freshness-gate regression
# =============================================================================


def _freshness_verdict(monkeypatch, plan_id: str) -> dict:
    """Run the real ``pre-commit-verify-freshness`` handler against the isolated ledger.

    ``_build_necessity_verdict`` is pinned to ``build`` on purpose: the
    build-necessity short-circuit is a separate concern that would return
    ``fresh`` without ever reaching the ledger scan, and the ledger scan is
    exactly what this regression is about.
    """
    import _cmd_pre_commit_verify_freshness as gate

    monkeypatch.setattr(gate, '_build_necessity_verdict', lambda _plan_id: {'decision': 'build'})
    args = types.SimpleNamespace(plan_id=plan_id)
    return gate.cmd_pre_commit_verify_freshness(args)


def test_freshness_gate_cannot_report_fresh_after_a_query_dispatch(tmp_path, monkeypatch):
    """The gate has nothing to match after a query dispatch, so it cannot pass.

    Fail-first against the prefix-only predicate: that boundary stamped the query
    ``kind=build / status=success`` at the current working-tree sha, which is
    precisely the row this gate accepts as proof of a build.
    """
    notation, subcommand = _a_query_subcommand()
    ledger_root = tmp_path / 'gate-base'
    ledger_root.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(ledger_root))

    import file_ops

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', ledger_root, raising=False)
    monkeypatch.chdir(PROJECT_ROOT)

    _dispatch_into(ledger_root, tmp_path, notation, [subcommand])

    verdict = _freshness_verdict(monkeypatch, 'discriminator-regression-plan')

    assert verdict['status'] != 'fresh', (
        f'the freshness gate reported {verdict["status"]!r} on the strength of a '
        f'{notation} {subcommand} dispatch that ran no build.'
    )


def test_freshness_gate_reports_fresh_after_a_build_executing_dispatch(tmp_path, monkeypatch):
    """Matched positive control: the gate DOES pass on a real build-executing row.

    This is what proves the negative above fails for the right reason -- the
    dispatch boundary, the ledger and the gate are genuinely wired together
    against the same working-tree sha, so the absence of a row is what withheld
    the ``fresh`` verdict, not a broken fixture.
    """
    notation, subcommand = _a_build_executing_subcommand()
    ledger_root = tmp_path / 'gate-base'
    ledger_root.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(ledger_root))

    import file_ops

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', ledger_root, raising=False)
    monkeypatch.chdir(PROJECT_ROOT)

    _dispatch_into(ledger_root, tmp_path, notation, [subcommand])

    verdict = _freshness_verdict(monkeypatch, 'discriminator-regression-plan')

    assert verdict['status'] == 'fresh', (
        f'the freshness gate reported {verdict["status"]!r} after a real build-executing '
        'dispatch; the negative case above would then pass for the wrong reason.'
    )


def _dispatch_into(ledger_root: Path, tmp_path: Path, notation: str, argv: list[str]) -> None:
    """Dispatch a stubbed build wrapper with the ledger pinned to ``ledger_root``.

    Shares the stub and render shape with :func:`_dispatch` but writes into a
    CALLER-supplied ledger root, so the freshness gate below reads the same file
    the dispatch wrote. ``cwd`` is the repo root in both directions, so the
    dispatch-time and gate-time ``worktree_sha`` are computed over the same tree.
    """
    stub_script = tmp_path / 'gate_stub_build.py'
    stub_script.write_text(
        '#!/usr/bin/env python3\nimport sys\nsys.stdout.write("status: success")\nsys.exit(0)\n',
        encoding='utf-8',
    )

    executor_path = tmp_path / 'gate-execute-script.py'
    _render_executor(executor_path, {notation: stub_script})

    env = _subprocess_env()
    env['PLAN_BASE_DIR'] = str(ledger_root)
    result = subprocess.run(
        ['python3', str(executor_path), notation, *argv],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f'the executor must propagate the stub exit code 0, got {result.returncode} '
        f'(stderr: {result.stderr!r})'
    )
