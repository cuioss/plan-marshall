#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests pinning the interpreter-launch-abort path as fail-closed.

A dispatched process that dies by signal before producing any stdout is the
executor's worst-case signal: there is no TOON, no ``status`` field, and no
Python-level traceback to read. The live example is a virtual environment whose
``pyvenv.cfg`` names an interpreter that no longer resolves, which aborts the
launch at ``dyld`` level. The abort is structurally uncatchable from inside the
process that failed to launch, so there is no code layer to add -- these tests
PIN the two fail-closed properties that already hold at the boundary:

1. The ``kind=build`` ledger row stamps ``status: killed``. That value is
   reachable ONLY from the negative-returncode branch of the status derivation;
   no stdout claim can produce it, and an empty stdout can never become
   ``success``.
2. The dispatch-failure work.log emission classifies the case
   ``script_internal_failure`` and carries the stderr text as its ``detail``,
   rather than an empty diagnostic.

**Stub binary only.** Every dispatch here targets a throwaway stub script under
``tmp_path``. No live worktree, no real build wrapper, and no real build is ever
invoked.

**Order-independence w.r.t. the build-class discriminator.** The stub is
dispatched under a build-class notation carrying the build-executing ``run``
subcommand. That argv satisfies BOTH the historical prefix-only predicate and
the narrowed prefix-AND-subcommand predicate, so the ``status: killed``
assertion holds regardless of which one is installed. The subcommand is asserted
explicitly in the test body (see :func:`test_dispatch_uses_the_build_executing_subcommand`)
rather than left implicit in a fixture, so a later edit cannot silently drop it
back to a query verb and quietly stop stamping a row at all.

**Ledger isolation.** This module deliberately drives the ``kind=build`` stamp.
A row written into the PRODUCTION change-ledger by the test suite would satisfy
the production ``pre-commit-verify-freshness`` gate -- the suite would be
manufacturing a false signal. The module-scoped :func:`_isolated_ledger` fixture
redirects that resolution to a temporary directory for the whole module, and
:func:`test_ledger_path_is_redirected_away_from_production` asserts the redirect
is actually in force rather than assuming it.

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

from conftest import _MARKETPLACE_SCRIPT_DIRS, PROJECT_ROOT

_SKILL_DIR = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'tools-script-executor'
_TEMPLATE_PATH = _SKILL_DIR / 'templates' / 'execute-script.py.template'
_LOGGING_DIR = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-logging' / 'scripts'
_PRODUCTION_LEDGER = PROJECT_ROOT / '.plan' / 'work' / 'change-ledger.jsonl'

#: A build-class notation. Paired with :data:`_BUILD_EXECUTING_SUBCOMMAND` below
#: it is what makes the dispatch stamp a ``kind=build`` row under BOTH the
#: prefix-only and the prefix-AND-subcommand predicate.
_BUILD_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'

#: The build-executing verb. Named as a module constant so the explicit
#: assertion below and the dispatch itself read the SAME value.
_BUILD_EXECUTING_SUBCOMMAND = 'run'

#: Plan id the dispatch carries, so the boundary's work.log emission has a plan
#: directory to write into. Scoped to the isolated ``PLAN_BASE_DIR`` root.
_PLAN_ID = 'launch-abort-fail-closed-plan'

#: Marker the stub writes to stderr immediately before aborting. Its presence in
#: the work.log ``detail=`` field is what proves the diagnostic is not empty.
_STDERR_MARKER = 'dyld: Library not loaded (stub launch abort)'

#: Source of the stub "binary". It writes the stderr marker, flushes it, and then
#: terminates by signal -- reproducing "died by signal, produced no stdout" at the
#: same subprocess boundary a real interpreter-launch abort hits.
#:
#: SIGKILL rather than SIGABRT on purpose. The property under test is the NEGATIVE
#: RETURNCODE branch of the status derivation, which any terminating signal
#: reaches identically; SIGKILL additionally leaves no core dump and triggers no
#: OS crash reporter, so a suite that runs this on every commit stays quiet. The
#: stderr write is flushed BEFORE the kill so the text is already in the pipe when
#: the process dies.
_ABORTING_STUB_SOURCE = (
    '#!/usr/bin/env python3\n'
    'import os\n'
    'import signal\n'
    'import sys\n'
    f'sys.stderr.write({_STDERR_MARKER!r})\n'
    'sys.stderr.flush()\n'
    'os.kill(os.getpid(), signal.SIGKILL)\n'
)


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

    root = tmp_path_factory.mktemp('launch-abort-ledger-root')
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
    code = code.replace('{{SCRIPT_SURFACES}}', '').replace('{{SUBCOMMAND_MAPPINGS}}', '')
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
    """Exec the rendered template in-process so its predicates can be read directly.

    Rendered in memory: writing a probe file next to the template would pollute
    the marketplace source tree the suite is asserting against.
    """
    module = types.ModuleType('execute_script_launch_abort')
    module.__dict__['__file__'] = str(_TEMPLATE_PATH)
    exec(_render_code({}), module.__dict__)
    return module


class _AbortDispatch:
    """The observable result of dispatching the aborting stub through the executor.

    Attributes:
        argv: The full executor argv, so a test can assert what was dispatched.
        ledger_rows: Every change-ledger row the dispatch appended.
        work_log: The concatenated work.log text written under the isolated root.
    """

    def __init__(self, argv: list[str], ledger_rows: list[dict], work_log: str):
        self.argv = argv
        self.ledger_rows = ledger_rows
        self.work_log = work_log


@pytest.fixture
def abort_dispatch(tmp_path) -> _AbortDispatch:
    """Dispatch the aborting stub once and collect the ledger rows plus work.log.

    The stub is registered under :data:`_BUILD_NOTATION` and dispatched with
    :data:`_BUILD_EXECUTING_SUBCOMMAND`, so the build-class boundary fires. The
    ledger root is a fresh per-test directory, so the rows collected below belong
    to this dispatch alone.
    """
    stub_script = tmp_path / 'aborting_stub.py'
    stub_script.write_text(_ABORTING_STUB_SOURCE, encoding='utf-8')

    executor_path = tmp_path / 'execute-script.py'
    _render_executor(executor_path, {_BUILD_NOTATION: stub_script})

    ledger_root = tmp_path / 'plan-base'
    ledger_root.mkdir()

    argv = [_BUILD_NOTATION, _BUILD_EXECUTING_SUBCOMMAND, '--plan-id', _PLAN_ID]
    env = _subprocess_env()
    env['PLAN_BASE_DIR'] = str(ledger_root)
    subprocess.run(
        ['python3', str(executor_path), *argv],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
    )

    ledger = ledger_root / 'work' / 'change-ledger.jsonl'
    rows = (
        [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines() if line.strip()]
        if ledger.is_file()
        else []
    )
    # ``work*.log`` rather than ``work.log``: the boundary's emission lands in the
    # plan-scoped ``logs/work.log`` only when the plan dir carries a status.json
    # sentinel, and otherwise in the date-suffixed global ``logs/work-{date}.log``.
    # This module scaffolds no plan dir, so it collects both spellings rather than
    # depending on which fallback fired.
    work_log = '\n'.join(path.read_text(encoding='utf-8') for path in sorted(ledger_root.rglob('work*.log')))
    return _AbortDispatch(argv=argv, ledger_rows=rows, work_log=work_log)


# =============================================================================
# Ledger isolation
# =============================================================================


def test_ledger_path_is_redirected_away_from_production(_isolated_ledger):
    """The module's ledger writes land in the temp root, never in the repo ledger.

    Asserted rather than assumed: a redirect that silently failed would make the
    dispatch below append a ``kind=build`` row to the production ledger, where
    the real ``pre-commit-verify-freshness`` gate would accept it.
    """
    from _ledger_core import resolve_ledger_path

    resolved = resolve_ledger_path()

    assert resolved.is_relative_to(_isolated_ledger), (
        f'the change-ledger resolved to {resolved} -- outside the isolated root '
        f'{_isolated_ledger}. This module must never write into a shared ledger.'
    )
    assert resolved != _PRODUCTION_LEDGER, f'the change-ledger resolved to the production path {resolved}.'


# =============================================================================
# The dispatched argv
# =============================================================================


def test_dispatch_uses_the_build_executing_subcommand(abort_dispatch):
    """The stub is dispatched under a build-class notation WITH the build-executing verb.

    Explicit rather than implicit. If a later edit dropped the subcommand (or
    swapped it for a query verb), the narrowed discriminator would stamp no
    ``kind=build`` row at all and the ``status: killed`` assertion below would
    silently stop testing anything. Asserting the argv here makes that a red.
    """
    executor = _load_executor_module()

    assert abort_dispatch.argv[0] == _BUILD_NOTATION
    assert abort_dispatch.argv[1] == _BUILD_EXECUTING_SUBCOMMAND
    assert _BUILD_EXECUTING_SUBCOMMAND in executor._BUILD_EXECUTING_SUBCOMMANDS, (
        f'{_BUILD_EXECUTING_SUBCOMMAND!r} is no longer a build-executing verb, so this '
        'module dispatches a subcommand that stamps no ledger row.'
    )


# =============================================================================
# Property 1: the ledger row stamps status: killed, never success
# =============================================================================


def test_signal_terminated_dispatch_stamps_status_killed(abort_dispatch):
    """A signal-terminated dispatch producing no stdout stamps ``killed``.

    ``killed`` is reachable only from the negative-returncode branch of the
    status derivation. An empty stdout carries no ``status`` field to fall back
    on, so the derivation has nothing that could launder the abort into
    ``success`` -- which is exactly the fail-closed property being pinned.
    """
    build_rows = [row for row in abort_dispatch.ledger_rows if row.get('kind') == 'build']

    assert len(build_rows) == 1, (
        f'expected exactly one kind=build row from the aborting dispatch, got '
        f'{len(build_rows)}: {abort_dispatch.ledger_rows!r}'
    )
    row = build_rows[0]
    assert row['status'] == 'killed', (
        f'the aborting dispatch stamped status={row["status"]!r}. A launch abort that '
        'produced no stdout must never be recorded as a completed build.'
    )
    assert row['status'] != 'success'
    assert row['exit_code'] < 0, (
        f'expected a negative returncode (terminated by signal), got {row["exit_code"]!r}; '
        'without it the killed branch is not the one under test.'
    )


def test_aborting_dispatch_records_no_outcome_payload(abort_dispatch):
    """The row carries no stdout-derived outcome, so the verdict rests on the returncode.

    The anti-vacuity anchor for the case above: it proves the ``killed`` verdict
    was NOT read out of a stdout payload (there is none), but derived from the
    signal death alone.
    """
    row = next(row for row in abort_dispatch.ledger_rows if row.get('kind') == 'build')

    assert not row.get('outcome'), (
        f'the aborting dispatch recorded an outcome payload {row.get("outcome")!r}; the stub '
        'writes no stdout, so a payload here means the fixture is not reproducing the abort.'
    )


# =============================================================================
# Property 2: the work.log diagnostic is classified and non-empty
# =============================================================================


def test_work_log_classifies_the_abort_as_script_internal_failure(abort_dispatch):
    """The boundary emits a classified ``[ERROR]`` line for the aborting dispatch."""
    assert 'failure_kind=script_internal_failure' in abort_dispatch.work_log, (
        f'no script_internal_failure classification found in the work.log:\n{abort_dispatch.work_log}'
    )
    assert f'notation={_BUILD_NOTATION}' in abort_dispatch.work_log


def test_work_log_detail_carries_the_stderr_text(abort_dispatch):
    """The ``detail=`` field carries the loader's stderr text, not an empty diagnostic.

    The stub writes to stderr and nothing to stdout, so the detail derivation
    falls through to its stderr last resort. An empty detail here would leave the
    only human-readable record of the abort undiagnosable.
    """
    assert _STDERR_MARKER in abort_dispatch.work_log, (
        f'the stderr marker {_STDERR_MARKER!r} is absent from the work.log entry, so the '
        f'dispatch-failure detail is empty or dropped:\n{abort_dispatch.work_log}'
    )
    assert 'detail=' in abort_dispatch.work_log
