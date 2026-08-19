# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``plan retrospective manifest`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import sys
from pathlib import Path

from _plan_retrospective_fixtures import build_happy_plan_dir  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))


MANIFEST_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-manifest-consistency.py'
)


ARTIFACT_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-artifact-consistency.py'
)


ROUTING_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-routing-decisions.py'
)


# =============================================================================
# Fixture helpers
# =============================================================================


def _write_manifest(plan_dir: Path, body: str) -> None:
    """Write a TOON manifest into the plan directory."""
    (plan_dir / 'execution.toon').write_text(body, encoding='utf-8')


def _write_diff(tmp_path: Path, files: list[str]) -> Path:
    """Write a one-path-per-line diff file and return its path."""
    diff_path = tmp_path / 'diff.txt'
    diff_path.write_text('\n'.join(files) + ('\n' if files else ''), encoding='utf-8')
    return diff_path


def _write_decision_log(plan_dir: Path, lines: list[str]) -> None:
    """Write decision-log lines including the composer caller tag where requested."""
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'decision.log').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _setup_plan_with_manifest(
    tmp_path: Path,
    monkeypatch,
    manifest_body: str,
    *,
    plan_id: str = 'manifest-plan',
    decision_lines: list[str] | None = None,
) -> tuple[str, Path]:
    """Build a happy-path plan and overlay an execution.toon manifest."""
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)
    _write_manifest(plan_dir, manifest_body)
    if decision_lines is not None:
        _write_decision_log(plan_dir, decision_lines)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


# Manifest body templates. We round-trip through ``serialize_toon`` so the
# fixtures always match the on-disk shape produced by ``manage-execution-manifest``
# (``key[N]:`` header followed by ``  - value`` lines for simple arrays).
def _serialize_manifest(body: dict) -> str:
    from toon_parser import serialize_toon  # local import — script-test PYTHONPATH

    return serialize_toon(body) + '\n'


def _manifest_default() -> str:
    return _serialize_manifest(
        {
            'manifest_version': 1,
            'plan_id': 'manifest-plan',
            'phase_5': {
                'early_terminate': False,
                # The composer's real shape: every built-in verify step is a
                # canonical-verify id, boundary-normalized to ``verify:{canonical}``.
                'verification_steps': ['verify:quality-gate', 'verify:module-tests'],
            },
            'phase_6': {
                'steps': ['push', 'create-pr', 'branch-cleanup'],
            },
        }
    )


def _manifest_docs_only() -> str:
    return _serialize_manifest(
        {
            'manifest_version': 1,
            'plan_id': 'manifest-plan',
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': ['push', 'create-pr'],
            },
        }
    )


def _manifest_early_terminate() -> str:
    return _serialize_manifest(
        {
            'manifest_version': 1,
            'plan_id': 'manifest-plan',
            'phase_5': {
                'early_terminate': True,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': ['lessons-capture', 'archive-plan'],
            },
        }
    )


def _manifest_tests_only() -> str:
    return _serialize_manifest(
        {
            'manifest_version': 1,
            'plan_id': 'manifest-plan',
            'phase_5': {
                'early_terminate': False,
                # ``verify:``-prefixed, as the composer emits it — a fixture carrying
                # the bare form drives rule M3 with a shape production never sees.
                'verification_steps': ['verify:module-tests'],
            },
            'phase_6': {
                'steps': ['push', 'create-pr'],
            },
        }
    )


def _check_by_name(checks: list, name: str) -> dict | None:
    for entry in checks:
        if entry.get('name') == name:
            return entry
    return None


def _finding_by_code(findings: list, code: str) -> dict | None:
    for entry in findings:
        if entry.get('code') == code:
            return entry
    return None


# =============================================================================
# Routing-decision aspect (deliverable 10)
# =============================================================================
#
# check-routing-decisions re-evaluates the lane prune predicates against the
# realized footprint and emits deterministic facts. The OVER/UNDER posture
# counterfactual is reserved for LLM cognition — the script NEVER computes a
# posture verdict and marks the boundary with llm_judgement_required.


def _write_status_metadata(plan_dir: Path, metadata: dict) -> None:
    """Overwrite the plan's status.json with the given metadata block."""
    import json  # local import — script-test PYTHONPATH

    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'metadata': metadata}, indent=2),
        encoding='utf-8',
    )


def _manifest_with_steps_and_log(steps: list[str], log_rows: list[dict]) -> str:
    return _serialize_manifest(
        {
            'manifest_version': 1,
            'plan_id': 'manifest-plan',
            'phase_5': {'early_terminate': False, 'verification_steps': []},
            'phase_6': {'steps': steps},
            'execution_log': log_rows,
        }
    )


def _run_routing(plan_id: str, *extra: str):
    return run_script(ROUTING_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live', *extra)


def _mis_prune(checks: list, step: str) -> dict | None:
    for entry in checks:
        if entry.get('check') == f'mis_prune:{step}':
            return entry
    return None
