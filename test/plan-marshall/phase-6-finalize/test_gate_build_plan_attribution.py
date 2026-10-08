#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A build a gate resolves and then runs is attributed to the gate's plan.

The gate documents resolve each build with ``architecture ... resolve`` and run
the returned ``executable`` verbatim. Two things must hold for that build to be
recorded under the plan rather than under the ``NO_PLAN`` sentinel:

* **The seam** — a resolve carrying the notation's top-level ``--plan-id``
  returns an ``executable`` whose own ``run`` parser reads that plan id, and the
  routing seam submits it to the build daemon.
* **The documents** — every fenced resolve call in the gate documents carries
  ``--plan-id`` between the notation and the ``resolve`` verb. A flag written
  after the verb is rejected by the parser and attributes nothing, so it does
  not satisfy the detector.

**The call population is DERIVED from the documents**, not listed here, and its
size is published on every run, so a derivation that silently collapsed is
visible on a green run. The detector is paired with mutation guards that run it
against synthetic calls, so a detector typo fails here instead of emptying the
sweep.
"""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path
from typing import Any

import _build_execute_factory as factory
import pytest
from _build_server_protocol import MARSHALLD_JOB_ENV

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module, parse_ns

_SKILLS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'

_PLAN = 'gate-plan'

_BUILD_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'

#: What the architecture resolves for a whole-tree gate build, before attribution.
_RESOLVED_EXECUTABLE = f'python3 .plan/execute-script.py {_BUILD_NOTATION} run --command-args "quality-gate"'


# ---------------------------------------------------------------------------
# The seam — resolve for a plan, run what it returned, submit for that plan
# ---------------------------------------------------------------------------


class _ReadyClient:
    """A build-server client whose daemon is ready and finishes the job green."""

    def __init__(self) -> None:
        self.submit_calls: list[argparse.Namespace] = []

    def run_preflight(self, args: argparse.Namespace) -> dict[str, Any]:
        return {'status': 'success', 'preflight': 'ready'}

    def run_submit(self, args: argparse.Namespace) -> dict[str, Any]:
        self.submit_calls.append(args)
        return {'status': 'success', 'job_id': 'JOB-1'}

    def run_wait(self, args: argparse.Namespace) -> dict[str, Any]:
        return {'status': 'success', 'job_status': 'success', 'duration_seconds': 1, 'log_file': 'absent.log'}


@pytest.fixture
def resolved_for_plan(monkeypatch) -> dict[str, Any]:
    """Resolve a gate build through ``architecture --plan-id {plan} resolve``.

    The architecture lookup is replaced through the handler's own globals, so the
    stand-in reaches the function under test whichever module copy is registered.
    """
    cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', register=False)
    monkeypatch.setitem(
        cmd_client.cmd_resolve.__globals__,
        'resolve_command',
        lambda command, module, project_dir: {
            'module': 'default',
            'command': command,
            'executable': _RESOLVED_EXECUTABLE,
            'resolution_level': 'module',
        },
    )
    args = parse_ns(
        'plan-marshall',
        'manage-architecture',
        'architecture.py',
        '--plan-id',
        _PLAN,
        'resolve',
        '--command',
        'quality-gate',
        register=False,
    )
    result: dict[str, Any] = cmd_client.cmd_resolve(args)
    return result


def _run_argv(executable: str) -> list[str]:
    """Return the argv the executor hands the build script for ``executable``."""
    tokens = shlex.split(executable)
    return tokens[tokens.index(_BUILD_NOTATION) + 1 :]


def test_resolved_executable_is_read_by_the_run_parser_as_the_plans_build(resolved_for_plan):
    run_args = parse_ns(
        'plan-marshall',
        'build-pyproject',
        'pyproject_build.py',
        *_run_argv(resolved_for_plan['executable']),
        register=False,
    )

    assert resolved_for_plan['status'] == 'success'
    assert run_args.plan_id == _PLAN
    assert run_args.command_args == 'quality-gate'


def test_routing_seam_submits_the_resolved_build_for_the_plan(resolved_for_plan, monkeypatch, tmp_path):
    """The plan id the daemon is handed is the one the resolve call named."""
    run_argv = _run_argv(resolved_for_plan['executable'])
    run_args = parse_ns('plan-marshall', 'build-pyproject', 'pyproject_build.py', *run_argv, register=False)
    pyproject_execute = load_script_module('plan-marshall', 'build-pyproject', '_pyproject_execute.py', register=False)
    client = _ReadyClient()
    monkeypatch.delenv(MARSHALLD_JOB_ENV, raising=False)
    monkeypatch.setattr(factory, '_load_build_server', lambda: client)
    monkeypatch.setattr(sys, 'argv', ['pyproject_build.py', *run_argv])

    routed, reason = factory._route_to_daemon(pyproject_execute._CONFIG, str(tmp_path), run_args.plan_id)

    assert reason == ''
    assert routed is not None
    assert [call.plan_id for call in client.submit_calls] == [_PLAN]


# ---------------------------------------------------------------------------
# The documents — every fenced resolve call names the plan before the verb
# ---------------------------------------------------------------------------

#: A resolve call on one folded line. ``top`` is everything between the notation
#: and the ``resolve`` verb — the only place the top-level flag is accepted.
_RESOLVE_CALL = re.compile(r'manage-architecture:architecture\s+(?P<top>(?:\S+\s+)*?)resolve\s+--command\s')

_TOP_LEVEL_PLAN_ID = re.compile(r'(?:^|\s)--plan-id(?:\s+|=)\S+')


def _gate_documents() -> list[Path]:
    """The documents whose resolve calls are run as gate builds."""
    phase_5 = _SKILLS / 'phase-5-execute'
    return [
        *sorted((_SKILLS / 'phase-6-finalize').rglob('*.md')),
        phase_5 / 'SKILL.md',
        phase_5 / 'standards' / 'canonical_verify.md',
    ]


def _fenced_lines(text: str) -> list[str]:
    """Return the lines inside fenced code blocks, backslash-continuations folded."""
    lines: list[str] = []
    in_fence = False
    block: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith('```'):
            if in_fence:
                lines.extend(re.sub(r'\\\n\s*', ' ', '\n'.join(block)).splitlines())
                block = []
            in_fence = not in_fence
            continue
        if in_fence:
            block.append(line)
    return lines


def _resolve_calls(text: str) -> list[tuple[str, bool]]:
    """Return ``(call, carries_top_level_plan_id)`` for every fenced resolve call."""
    calls: list[tuple[str, bool]] = []
    for line in _fenced_lines(text):
        match = _RESOLVE_CALL.search(line)
        if match:
            calls.append((line.strip(), bool(_TOP_LEVEL_PLAN_ID.search(match.group('top')))))
    return calls


def _derive_population() -> list[tuple[str, str, bool]]:
    """Return ``(document, call, carries_top_level_plan_id)`` across the gate documents."""
    population: list[tuple[str, str, bool]] = []
    for path in _gate_documents():
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        for call, attributed in _resolve_calls(path.read_text(encoding='utf-8')):
            population.append((relative, call, attributed))
    return population


_POPULATION = _derive_population()

#: Published on every run — passing included — by the root conftest's
#: ``pytest_report_header``, so a shrunken population is visible on a green run.
GUARD_POPULATION_LABEL = 'fenced architecture resolve calls in the gate documents'
GUARD_POPULATION_SIZE = len(_POPULATION)


def test_gate_documents_carry_resolve_calls_at_all():
    """An empty population would let the sweep below pass over nothing."""
    assert _POPULATION, (
        f'No fenced `architecture ... resolve --command` call was derived from '
        f'{[path.relative_to(PROJECT_ROOT).as_posix() for path in _gate_documents()]}'
    )


def test_every_fenced_resolve_call_names_the_plan_before_the_verb():
    unattributed = [(document, call) for document, call, attributed in _POPULATION if not attributed]

    assert not unattributed, (
        f'These fenced resolve calls carry no `--plan-id` between the notation and the '
        f'`resolve` verb, so the build they return records NO_PLAN: {unattributed} '
        f'(population: {len(_POPULATION)} call(s))'
    )


_NOTATION_PREFIX = 'python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture'

#: ``(tail after the notation, whether the detector must accept it)``.
_SYNTHETIC_CALLS = [
    ('resolve --command quality-gate --audit-plan-id {plan_id}', False),
    ('resolve --command quality-gate --plan-id {plan_id}', False),
    ('--plan-id {plan_id} resolve --command quality-gate --audit-plan-id {plan_id}', True),
]

_SYNTHETIC_IDS = ['no-flag', 'flag-after-the-verb', 'flag-before-the-verb']


@pytest.mark.parametrize(('tail', 'accepted'), _SYNTHETIC_CALLS, ids=_SYNTHETIC_IDS)
def test_detector_accepts_only_a_plan_id_written_before_the_verb(tail, accepted):
    document = f'```bash\n{_NOTATION_PREFIX} \\\n  {tail}\n```\n'

    calls = _resolve_calls(document)

    assert [attributed for _call, attributed in calls] == [accepted]
