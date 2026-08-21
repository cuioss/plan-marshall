#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared fixtures for the ``audit-archived-plan-retrospectives`` test modules.

Loads ``scripts/audit.py`` once and exposes it as :data:`audit`. The script is
project-local (under ``.claude/skills/``) rather than a marketplace-bundle
script, so ``conftest.load_script_module`` does not resolve it and the module is
loaded here by path instead.

Loading it in ONE place is what keeps the per-check test modules independent: a
loader copied into each of them would have every module re-execute ``audit.py``
and re-register the same ``sys.modules`` name, so the module object a test held
would depend on collection order.

The staging helpers below are the ones more than one test module needs. A helper
used by a single module stays in that module.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

from conftest import PROJECT_ROOT

_AUDIT_SCRIPT = (
    PROJECT_ROOT
    / '.claude'
    / 'skills'
    / 'audit-archived-plan-retrospectives'
    / 'scripts'
    / 'audit.py'
)


def _load_audit():
    spec = importlib.util.spec_from_file_location('audit_under_test', _AUDIT_SCRIPT)
    assert spec is not None, f'Failed to load module spec for {_AUDIT_SCRIPT}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register before exec_module so @dataclass can resolve the module via
    # sys.modules[cls.__module__] (required under Python 3.14's dataclasses
    # with `from __future__ import annotations`).
    sys.modules['audit_under_test'] = mod
    spec.loader.exec_module(mod)
    return mod


audit = _load_audit()

#: The audit skill's ``scripts/`` directory. Derived from the loaded script's own
#: path so the two cannot drift.
AUDIT_SCRIPTS_DIR = _AUDIT_SCRIPT.parent

#: The globbed ``script-execution-*.log`` name the probe fixtures write to.
#: ``cross_global_log_analysis`` only picks up files matching that glob, so the
#: name is part of the fixture contract rather than an arbitrary label.
PROBE_LOG_NAME = "script-execution-2026-06-29.log"

def _inputs(phase_5: list[str]) -> Any:
    """Build a minimal PlanInputs carrying only the phase_5 manifest list."""
    return audit.PlanInputs(
        plan_id='test-plan',
        plan_dir=PROJECT_ROOT / '.plan' / 'temp' / 'nonexistent-plan',
        manifest_present=True,
        manifest_phase_5=list(phase_5),
    )

def _phase(
    name: str,
    *,
    total_tokens: int = 0,
    duration_seconds: float = 0.0,
    retrospective_tokens: int = 0,
    agent_duration_seconds: float = 0.0,
    idle_duration_ms: float = 0.0,
) -> Any:
    return audit.PhaseMetrics(
        phase=name,
        total_tokens=total_tokens,
        duration_seconds=duration_seconds,
        retrospective_tokens=retrospective_tokens,
        agent_duration_seconds=agent_duration_seconds,
        idle_duration_ms=idle_duration_ms,
    )

def _write_metrics_toon(plan_dir: Path, blocks: dict[str, dict[str, Any]]) -> None:
    """Write an INI-shaped `work/metrics.toon` the audit parser reads."""
    lines = ['plan_id: fixture', '']
    for phase, fields in blocks.items():
        lines.append(f'[{phase}]')
        for key, value in fields.items():
            lines.append(f'  {key}: {value}')
        lines.append('')
    work = plan_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    (work / 'metrics.toon').write_text('\n'.join(lines) + '\n', encoding='utf-8')

def _plan_with_counters(repo_root: Path, name: str, phases: dict[str, dict[str, int]]) -> Any:
    """Stage an archived plan whose metrics.toon carries per-phase counters.

    ``phases`` maps a phase name to the counter fields to write under its
    ``[phase]`` section. A phase mapped to an EMPTY dict writes the section with a
    non-counter field only — the absent-counter shape.
    """
    plan_dir = repo_root / '.plan' / 'local' / 'archived-plans' / name
    (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text(
        '{"scope_estimate": "surgical"}', encoding='utf-8'
    )
    (plan_dir / 'status.json').write_text(
        '{"metadata": {"change_type": "feature"}}', encoding='utf-8'
    )
    lines: list[str] = []
    for phase, fields in phases.items():
        lines.append(f'[{phase}]')
        lines.append('  total_tokens: 100')
        for key, value in fields.items():
            lines.append(f'  {key}: {value}')
        lines.append('')
    (plan_dir / 'work' / 'metrics.toon').write_text('\n'.join(lines), encoding='utf-8')
    return audit.collect_inputs(plan_dir)

def _counters(exploration: int, work: int, execute: int = 0, **extra: int) -> dict[str, int]:
    """Build a counter dict for one measure pair, defaulting the rest to a measured 0."""
    fields = {
        'exploration_tool_calls': exploration,
        'work_tool_calls': work,
        'execute_tool_calls': execute,
        'orchestration_tool_calls': 0,
        'unclassified_tool_calls': 0,
    }
    fields.update(extra)
    return fields

def _shares_plan(
    repo_root: Path,
    name: str,
    *,
    exploration_calls: int,
    other_calls: int,
    exploration_bytes: int,
    other_bytes: int,
    orchestration_calls: int = 0,
    orchestration_bytes: int = 0,
    unclassified_calls: int = 0,
    unclassified_bytes: int = 0,
) -> Any:
    """Stage a one-phase plan with the exact call/byte split a share test needs."""
    return _plan_with_counters(
        repo_root,
        name,
        {
            '5-execute': {
                'exploration_tool_calls': exploration_calls,
                'work_tool_calls': other_calls,
                'execute_tool_calls': 0,
                'orchestration_tool_calls': orchestration_calls,
                'unclassified_tool_calls': unclassified_calls,
                'exploration_result_bytes': exploration_bytes,
                'work_result_bytes': other_bytes,
                'execute_result_bytes': 0,
                'orchestration_result_bytes': orchestration_bytes,
                'unclassified_result_bytes': unclassified_bytes,
            }
        },
    )

def _write_log(repo_root: Path, name: str, lines: list[str]) -> None:
    """Write a global log file under ``{repo_root}/.plan/local/logs/{name}``.

    ``name`` MUST match one of the three globbed patterns
    (``script-execution-*.log`` / ``work-*.log`` / ``decision-*.log``) for
    ``cross_global_log_analysis`` to pick it up. Each entry in ``lines`` is one
    raw log line written verbatim.
    """
    logs_dir = repo_root / '.plan' / 'local' / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / name).write_text('\n'.join(lines) + '\n', encoding='utf-8')

def _write_metrics_window(
    repo_root: Path,
    plan_id: str,
    start: str,
    end: str,
    *,
    archived: bool = True,
) -> None:
    """Seed an archived (or active) plan's ``work/metrics.toon`` window.

    Writes a single-phase ``metrics.toon`` carrying ``start_time`` / ``end_time``
    lines so ``plan_execution_windows`` derives a ``(start, end)`` window for the
    plan. ``start`` / ``end`` are ``YYYY-MM-DDTHH:MM:SSZ`` strings (trailing ``Z``
    is stripped by the parser).
    """
    sub = 'archived-plans' if archived else 'plans'
    work = repo_root / '.plan' / 'local' / sub / plan_id / 'work'
    work.mkdir(parents=True, exist_ok=True)
    body = (
        'report: metrics\n'
        'phases:\n'
        '  - phase: 5-execute\n'
        f'    start_time: {start}\n'
        f'    end_time: {end}\n'
    )
    (work / 'metrics.toon').write_text(body, encoding='utf-8')

def _line(ts: str, level: str, rest: str, *, hash_: str = '3befe7') -> str:
    """Build a single log line in the shared ``_LOG_LINE_RE`` grammar."""
    return f'[{ts}] [{level}] [{hash_}] {rest}'

def _write_token_plan(
    repo_root: Path,
    plan_id: str,
    *,
    change_type: str = 'feature',
    scope_estimate: str = 'surgical',
    files: int = 5,
    task_count: int = 3,
    phase_tokens: dict[str, int] | None = None,
    session_message_count: int | None = None,
) -> Any:
    """Materialise one synthetic plan and return its parsed ``PlanInputs``.

    Builds a self-contained plan directory under ``{repo_root}/.plan/temp`` —
    never the live ``.plan/local`` tree — carrying the four artefacts the
    token-economics collector reads:

    - ``references.json`` — supplies ``scope_estimate`` and the
      ``modified_files`` list whose length becomes the per-plan file count.
    - ``status.json`` — supplies ``metadata.change_type``.
    - ``work/metrics.toon`` — INI-shaped ``[phase]`` blocks with ``total_tokens``
      lines plus the top-level ``session_message_count`` scalar.
    - ``tasks/TASK-*.json`` — ``task_count`` empty files counted by glob.

    The plan is then parsed through the real ``collect_inputs`` so the
    change_type / scope / file-count wiring is exercised end-to-end rather than
    hand-stuffed onto a ``PlanInputs`` instance.
    """
    if phase_tokens is None:
        phase_tokens = {'5-execute': 10_000}
    plan_dir = repo_root / '.plan' / 'temp' / 'token-corpus' / plan_id
    (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'tasks').mkdir(parents=True, exist_ok=True)

    import json as _json

    (plan_dir / 'references.json').write_text(
        _json.dumps(
            {
                'scope_estimate': scope_estimate,
                'modified_files': [f'src/file_{i}.py' for i in range(files)],
            }
        ),
        encoding='utf-8',
    )
    (plan_dir / 'status.json').write_text(
        _json.dumps({'metadata': {'change_type': change_type}}),
        encoding='utf-8',
    )

    metrics_lines: list[str] = []
    if session_message_count is not None:
        metrics_lines.append(f'session_message_count: {session_message_count}')
    for phase, tokens in phase_tokens.items():
        metrics_lines.append(f'[{phase}]')
        metrics_lines.append(f'  total_tokens: {tokens}')
    (plan_dir / 'work' / 'metrics.toon').write_text(
        '\n'.join(metrics_lines) + '\n', encoding='utf-8'
    )

    for n in range(1, task_count + 1):
        (plan_dir / 'tasks' / f'TASK-{n:03d}.json').write_text('{}', encoding='utf-8')

    return audit.collect_inputs(plan_dir)

def _sbm_call(ts: str, notation: str, sub: str, dur: float | None = None) -> str:
    """Build one ``script-execution.log`` call line in the ``_SBM_CALL_RE`` grammar.

    Format: ``[<ts>Z] [INFO] [<hash>] <notation> <sub>[ (<dur>s)]``. ``ts`` is a
    bare ``YYYY-MM-DDTHH:MM:SS`` stamp (no trailing ``Z`` — this helper adds it).
    A ``dur`` of ``None`` omits the trailing duration clause, which the parser
    reads as a 0.0-second (``unknown``-band) call.
    """
    head = f'[{ts}Z] [INFO] [3befe7] {notation} {sub}'
    return head if dur is None else f'{head} ({dur:.1f}s)'

def _sbm_dispatch(ts: str, role: str) -> str:
    """Build one ``work.log`` ``[DISPATCH] ... role=phase-N...`` marker line.

    The phase-bucketing timeline in ``_sequence_build_minimality_plan`` only reads
    work.log lines that start with a ``[<ts>Z]`` stamp AND match ``_SBM_DISPATCH_RE``;
    ``role`` is a ``phase-N-name`` token (e.g. ``phase-5-execute``).
    """
    return f'[{ts}Z] [INFO] [3befe7] [DISPATCH] (orchestrator) role={role} dispatched'

# Build notation for a staged kind=build ledger row. The re-base derives build
# time from the change-ledger, which records `command` per build system.
_LEDGER_NOTATION_PYPROJECT = 'plan-marshall:build-pyproject:pyproject_build'

def _sbm_ledger_row(
    plan_id: str,
    *,
    dur: float | None,
    status: str = 'success',
    ts: str = '2026-06-01T10:00:00Z',
    notation: str = _LEDGER_NOTATION_PYPROJECT,
    command: str = './pw verify',
) -> dict[str, Any]:
    """One kind=build change-ledger row — the build-time oracle's unit.

    ``dur=None`` (or 0) is a SUSPECT duration; ``status`` is one of
    success/error/timeout/killed/unknown; ``notation``/``command`` name the build
    system so a non-pyproject build is attributable.
    """
    return {
        'kind': 'build',
        'plan_id': plan_id,
        'notation': notation,
        'command': command,
        'duration_seconds': dur,
        'status': status,
        'timestamp_iso': ts,
    }

def _write_change_ledger(repo_root: Path, rows: list[dict[str, Any]]) -> None:
    """Append kind=build rows to ``<repo_root>/.plan/work/change-ledger.jsonl``."""
    import json as _json

    work = repo_root / '.plan' / 'work'
    work.mkdir(parents=True, exist_ok=True)
    with (work / 'change-ledger.jsonl').open('a', encoding='utf-8') as fh:
        for row in rows:
            fh.write(_json.dumps(row) + '\n')

def _sbm_index(repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    """The ledger build-index the check consumes, loaded from the staged ledger."""
    return audit._load_build_ledger_index(repo_root)

def _write_sbm_plan(
    repo_root: Path,
    plan_id: str,
    *,
    sel_lines: list[str] | None = None,
    work_lines: list[str] | None = None,
    modified_files: list[str] | None = None,
    change_type: str | None = None,
    ci_runs: int = 0,
    ledger_builds: list[dict[str, Any]] | None = None,
    metrics_phases: dict[str, float] | None = None,
) -> Any:
    """Materialise a synthetic plan dir for the sequence-and-build-minimality check.

    Writes ``logs/script-execution.log`` (the ordered call timeline),
    ``logs/work.log`` (dispatch markers + build-verb mentions),
    ``references.json`` (the ``modified_files`` footprint), ``status.json``
    (``metadata.change_type``), and ``ci_runs`` empty ``artifacts/ci-runs/run-N/``
    directories. When ``ledger_builds`` is given, each entry (a ``_sbm_ledger_row``
    kwargs dict) is appended to the shared ``.plan/work/change-ledger.jsonl`` under
    this ``plan_id`` — that ledger is the build-time oracle the check derives from.
    ``metrics_phases`` (``{phase: duration_seconds}``) writes a ``work/metrics.toon``
    supplying the wall-clock denominator. The plan is then parsed through the real
    ``collect_inputs``. Lives under ``.plan/temp/`` — never the real
    ``.plan/local/``.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'sbm-corpus' / plan_id
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'script-execution.log').write_text(
        '\n'.join(sel_lines or []) + '\n', encoding='utf-8'
    )
    (logs_dir / 'work.log').write_text(
        '\n'.join(work_lines or []) + '\n', encoding='utf-8'
    )
    (plan_dir / 'references.json').write_text(
        _json.dumps({'modified_files': modified_files or []}), encoding='utf-8'
    )
    (plan_dir / 'status.json').write_text(
        _json.dumps({'metadata': {'change_type': change_type} if change_type else {}}),
        encoding='utf-8',
    )
    for i in range(ci_runs):
        (plan_dir / 'artifacts' / 'ci-runs' / f'run-{i}').mkdir(
            parents=True, exist_ok=True
        )
    if ledger_builds:
        _write_change_ledger(
            repo_root, [_sbm_ledger_row(plan_id, **b) for b in ledger_builds]
        )
    if metrics_phases:
        _write_metrics_toon(
            plan_dir,
            {phase: {'duration_seconds': dur} for phase, dur in metrics_phases.items()},
        )
    return audit.collect_inputs(plan_dir)

_BUILD = 'pm:build-pyproject:pyproject_build'

_ARCH = 'pm:manage-architecture:architecture'

def _write_ii_plan(
    repo_root: Path,
    plan_id: str,
    *,
    has_execution: bool = True,
    has_metrics: bool = True,
    has_references: bool = True,
    has_tasks: bool = True,
    has_findings: bool = True,
    has_script_log: bool = True,
    phase_tokens: dict[str, int] | None = None,
    dispatch_marker: bool = True,
    marker_schema: str = 'current',
    phases_missing_end_time: str = '',
) -> Any:
    """Materialise a synthetic plan dir for the input-integrity meta-check.

    Builds, under ``{repo_root}/.plan/temp/ii-corpus/{plan_id}`` (never the live
    ``.plan/local`` tree), exactly the canonical input set
    ``check_input_integrity`` probes — each artefact toggled by its
    ``has_*`` flag so a test can omit any single input:

    - ``execution.toon`` — the composed manifest presence sentinel.
    - ``work/metrics.toon`` — INI-shaped ``[phase]`` blocks with ``total_tokens``
      lines; ``phase_tokens`` controls which phases are recorded and with how
      many tokens (a zero-token ``5-execute`` is the load-bearing ``blind`` case).
    - ``references.json`` — scope/footprint sentinel.
    - ``tasks/TASK-*.json`` — one non-empty task file (glob-counted).
    - ``artifacts/findings/*.jsonl`` — one non-empty findings file.
    - ``logs/script-execution.log`` — non-empty plan-scoped script log.
    - ``logs/work.log`` — carries a ``[DISPATCH] role=phase-N`` marker iff
      ``dispatch_marker`` is True.

    ``marker_schema`` selects which of the three #812 end_time-presence marker
    states the written ``metrics.toon`` is in, because the state is load-bearing
    for the ``data_confidence`` bucket:

    - ``'current'`` (default) — the new ``any_phase_missing_end_time`` /
      ``phases_missing_end_time`` keys, with the list taken from
      ``phases_missing_end_time``. This is the only state that can reach
      ``fully-recorded``.
    - ``'old-schema'`` — the RETIRED ``partial`` / ``unrecorded_phases`` keys, as
      an archived record written before the rename still carries them.
    - ``'pre-#812'`` — neither pair, the legitimate historical degrade.

    Returns a ``PlanInputs`` bound to the materialised ``plan_dir``;
    ``check_input_integrity`` reads only ``plan_dir`` / ``plan_id`` from disk, so
    the instance is constructed directly rather than parsed.
    """
    import json as _json

    if phase_tokens is None:
        phase_tokens = {'5-execute': 10_000, '6-finalize': 5_000}
    plan_dir = repo_root / '.plan' / 'temp' / 'ii-corpus' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)

    if has_execution:
        (plan_dir / 'execution.toon').write_text('phase_5:\n', encoding='utf-8')
    if has_metrics:
        (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
        metrics_lines: list[str] = []
        # Top-level marker keys come FIRST — `parse_toon_scalar` reads them as
        # plan-level scalars, and `parse_metrics_toon` starts collecting only at
        # the first `[phase]` header.
        if marker_schema == 'current':
            any_missing = 'true' if phases_missing_end_time else 'false'
            metrics_lines.append(f'any_phase_missing_end_time: {any_missing}')
            metrics_lines.append(f'phases_missing_end_time: {phases_missing_end_time}')
        elif marker_schema == 'old-schema':
            any_missing = 'true' if phases_missing_end_time else 'false'
            metrics_lines.append(f'partial: {any_missing}')
            metrics_lines.append(f'unrecorded_phases: {phases_missing_end_time}')
        elif marker_schema != 'pre-#812':
            # The selector is TOTAL. Without this branch any unrecognised value
            # writes neither key pair — which is exactly a `pre-#812` record — so
            # a typo at a call site would silently produce a valid-looking
            # pre-#812 fixture and the three-state tests would keep passing. The
            # fixture must be able to tell "the test asked for pre-#812" from
            # "the test asked for a value this helper does not know".
            raise ValueError(f'unknown marker_schema: {marker_schema!r}')
        for phase, tokens in phase_tokens.items():
            metrics_lines.append(f'[{phase}]')
            metrics_lines.append(f'  total_tokens: {tokens}')
        (plan_dir / 'work' / 'metrics.toon').write_text(
            '\n'.join(metrics_lines) + '\n', encoding='utf-8'
        )
    if has_references:
        (plan_dir / 'references.json').write_text(
            _json.dumps({'modified_files': []}), encoding='utf-8'
        )
    if has_tasks:
        (plan_dir / 'tasks').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'tasks' / 'TASK-001.json').write_text('{}', encoding='utf-8')
    if has_findings:
        (plan_dir / 'artifacts' / 'findings').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'artifacts' / 'findings' / 'f.jsonl').write_text(
            '{"id": 1}\n', encoding='utf-8'
        )
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    if has_script_log:
        (logs_dir / 'script-execution.log').write_text(
            '[2026-06-01T10:00:00Z] [INFO] call\n', encoding='utf-8'
        )
    work_lines = ['[2026-06-01T10:00:00Z] [INFO] [3befe7] work line']
    if dispatch_marker:
        work_lines.append(
            '[2026-06-01T10:00:01Z] [INFO] [3befe7] '
            '[DISPATCH] (orchestrator) role=phase-5-execute dispatched'
        )
    (logs_dir / 'work.log').write_text(
        '\n'.join(work_lines) + '\n', encoding='utf-8'
    )

    return audit.PlanInputs(plan_id=plan_id, plan_dir=plan_dir)

def _flag_result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap per-plan ``{plan_id, flags}`` rows in the cross-plan result shape."""
    return {'rows': rows}

def _coupling_row(result: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the single coupling row matching ``name`` from a synthesis result."""
    return next(r for r in result['rows'] if r['coupling'] == name)

def _write_preference_plan(
    repo_root: Path,
    plan_id: str,
    findings: list[dict[str, Any]],
) -> Any:
    """Materialise a plan whose ``artifacts/findings/findings.jsonl`` carries the
    supplied finding dicts verbatim (each carrying ``title``/``type``,
    ``resolution``, and optionally ``module``)."""
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'pref-corpus' / plan_id
    findings_dir = plan_dir / 'artifacts' / 'findings'
    findings_dir.mkdir(parents=True, exist_ok=True)
    lines = '\n'.join(_json.dumps(f) for f in findings) + '\n'
    (findings_dir / 'findings.jsonl').write_text(lines, encoding='utf-8')
    return audit.collect_inputs(plan_dir)

def _write_shipping_plan(
    repo_root: Path,
    plan_id: str,
    *,
    pr_number: str | None = None,
    modified_files: list[str] | None = None,
    archived_reason: str | None = None,
) -> Any:
    """Materialise a plan carrying the two shipping-evidence inputs (or neither).

    ``pr_number`` writes ``artifacts/ci-runs/run-1/manifest.toon`` with that
    scalar (the PR-record arm); ``modified_files`` seeds
    ``references.json::modified_files`` (the footprint arm); ``archived_reason``
    seeds ``status.json::metadata.archived_reason`` (the exclusion LABEL, never
    the predicate). Parsed through the real ``collect_inputs`` so the field
    wiring is exercised end-to-end.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'ship-corpus' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text(
        _json.dumps(
            {'scope_estimate': 'surgical', 'modified_files': modified_files or []}
        ),
        encoding='utf-8',
    )
    metadata: dict[str, Any] = {'change_type': 'bug_fix'}
    if archived_reason is not None:
        metadata['archived_reason'] = archived_reason
    (plan_dir / 'status.json').write_text(
        _json.dumps({'metadata': metadata}), encoding='utf-8'
    )
    if pr_number is not None:
        run_dir = plan_dir / 'artifacts' / 'ci-runs' / 'run-1'
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / 'manifest.toon').write_text(
            f'pr_number: {pr_number}\nfetched_at: 2026-05-30T10:00:00Z\n',
            encoding='utf-8',
        )
    return audit.collect_inputs(plan_dir)

_EXECUTE_PHASE = '5-execute'

def _phase_block(phase: str, **fields: int) -> str:
    """Render one `[phase]` section of a `metrics.toon`."""
    body = ''.join(f'  {key}: {value}\n' for key, value in fields.items())
    return f'[{phase}]\n{body}'

def _clean_metrics_body(**execute_fields: int) -> str:
    """A fully-recorded six-phase `metrics.toon` carrying *execute_fields*.

    Every canonical phase carries a non-zero ``total_tokens`` so
    ``check_input_integrity`` reports no ``metrics_blind`` phase and every
    canonical row is present, AND the body carries the CURRENT #812
    ``end_time``-presence keys reporting nothing missing — an unreadable marker
    record floors a plan on its own, so a baseline without them would be floored
    for a reason unrelated to whatever the test is measuring. The fixture is
    deliberately NOT floored and NOT omitting a row, so when a test asserts
    `label == 'measured'` that is a real verdict rather than fixture noise — and
    the floor/omitted tests below each introduce exactly one defect against this
    clean baseline.
    """
    blocks = [
        'any_phase_missing_end_time: false\n',
        'phases_missing_end_time: \n',
    ]
    for phase in audit._TE_PHASES:
        fields: dict[str, int] = {'total_tokens': 100}
        if phase == _EXECUTE_PHASE:
            fields.update(execute_fields)
        blocks.append(_phase_block(phase, **fields))
    return ''.join(blocks)

def _write_billing_plan(
    repo_root: Path,
    plan_id: str,
    metrics_body: str,
    *,
    ledgers: dict[str, str] | None = None,
) -> Any:
    """Materialise a SHIPPING plan carrying a metrics.toon and optional ledgers.

    ``references.json::modified_files`` is seeded non-empty so the plan clears the
    shipping predicate — ``billing-composition`` is a delivery-cost check, so a
    fixture without delivery evidence would be partitioned out before the check
    saw it. Parsed through the real ``collect_inputs`` so the field wiring is
    exercised end-to-end.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'billing-corpus' / plan_id
    (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text(
        _json.dumps({'scope_estimate': 'surgical', 'modified_files': ['src/a.py']}),
        encoding='utf-8',
    )
    (plan_dir / 'status.json').write_text(
        _json.dumps({'metadata': {'change_type': 'bug_fix'}}), encoding='utf-8'
    )
    (plan_dir / 'work' / 'metrics.toon').write_text(metrics_body, encoding='utf-8')
    for phase, body in (ledgers or {}).items():
        (plan_dir / 'work' / f'metrics-dispatch-boundaries-{phase}.toon').write_text(
            body, encoding='utf-8'
        )
    return audit.collect_inputs(plan_dir)

def _billing_row(result: dict[str, Any], plan_id: str) -> dict[str, Any]:
    return next(r for r in result['rows'] if r['plan_id'] == plan_id)


def minimal_corpus(repo_root: Path) -> list:
    """Build a one-plan archived corpus and return its collected inputs."""
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "sample-plan"
    plan_dir.mkdir(parents=True)
    (plan_dir / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    return [audit.collect_inputs(plan_dir)]


_LEDGER_HEADER = (
    'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
    'input_tokens,output_tokens,cache_read_input_tokens,'
    'cache_creation_input_tokens}:'
)
