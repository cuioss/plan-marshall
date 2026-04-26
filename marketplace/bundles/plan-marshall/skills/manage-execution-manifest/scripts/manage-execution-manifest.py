#!/usr/bin/env python3
"""
Manage the per-plan execution manifest (compose, read, validate).

The manifest is the single source of truth for which Phase 5 verification
steps and Phase 6 finalize steps fire for a given plan. Phases 5 and 6 read
the manifest and dispatch — they no longer carry per-doc skip logic.

Storage: TOON format at .plan/local/plans/{plan_id}/execution.toon
Output: TOON format for API responses

Usage:
    python3 manage-execution-manifest.py compose --plan-id my-plan \\
        --change-type bug_fix --track simple --scope-estimate surgical
    python3 manage-execution-manifest.py read --plan-id my-plan
    python3 manage-execution-manifest.py validate --plan-id my-plan
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from file_ops import (  # type: ignore[import-not-found]
    atomic_write_file,
    get_plan_dir,
    output_toon,
    output_toon_error,
    safe_main,
)
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    require_valid_plan_id,
)
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

# =============================================================================
# Constants
# =============================================================================

MANIFEST_FILENAME = 'execution.toon'
MANIFEST_VERSION = 1

VALID_CHANGE_TYPES = (
    'analysis',
    'feature',
    'enhancement',
    'bug_fix',
    'tech_debt',
    'verification',
)

VALID_SCOPE_ESTIMATES = (
    'none',
    'surgical',
    'single_module',
    'multi_module',
    'broad',
)

VALID_TRACKS = ('simple', 'complex')

# Default candidate step sets when callers don't pass --phase-5-steps / --phase-6-steps.
DEFAULT_PHASE_5_STEPS = ('quality-gate', 'module-tests')
DEFAULT_PHASE_6_STEPS = (
    'commit-push',
    'create-pr',
    'automated-review',
    'sonar-roundtrip',
    'knowledge-capture',
    'lessons-capture',
    'branch-cleanup',
    'archive-plan',
)


# =============================================================================
# File Operations
# =============================================================================


def get_manifest_path(plan_id: str) -> Path:
    """Return the absolute path to the execution manifest for ``plan_id``."""
    return get_plan_dir(plan_id) / MANIFEST_FILENAME


def write_manifest(plan_id: str, manifest: dict[str, Any]) -> None:
    """Atomically write the manifest as TOON to its plan path."""
    path = get_manifest_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_file(path, serialize_toon(manifest))


def read_manifest(plan_id: str) -> dict[str, Any] | None:
    """Read and parse the manifest, returning ``None`` if missing."""
    path = get_manifest_path(plan_id)
    if not path.exists():
        return None
    return parse_toon(path.read_text(encoding='utf-8'))


# =============================================================================
# Decision Engine (seven-row matrix from standards/decision-rules.md)
# =============================================================================


def _split_csv(value: str | None, default: tuple[str, ...]) -> list[str]:
    if value is None or value == '':
        return list(default)
    return [item.strip() for item in value.split(',') if item.strip()]


def _decide(
    change_type: str,
    track: str,
    scope_estimate: str,
    recipe_key: str | None,
    affected_files_count: int,
    phase_5_candidates: list[str],
    phase_6_candidates: list[str],
) -> tuple[dict[str, Any], str]:
    """Apply the seven-row decision matrix.

    Returns the manifest body (under ``phase_5`` / ``phase_6`` keys) plus the
    name of the rule that fired (one of the seven rule keys defined in
    standards/decision-rules.md).
    """

    # Rule 1: early_terminate — analysis without affected files. Phase 5 is
    # skipped entirely; Phase 6 still runs lessons/knowledge capture so the
    # analysis doesn't leak insights silently.
    if change_type == 'analysis' and affected_files_count == 0:
        body = {
            'phase_5': {
                'early_terminate': True,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': [
                    s for s in phase_6_candidates if s in {'knowledge-capture', 'lessons-capture', 'archive-plan'}
                ],
            },
        }
        return body, 'early_terminate_analysis'

    # Rule 2: recipe path — recipe-driven plans get a slim manifest. The
    # recipe-lesson-cleanup recipe (deliverable 7) sets scope_estimate=surgical
    # so the surgical-style cascades still apply downstream; here we only need
    # to drop heavy steps.
    if recipe_key:
        phase_6_steps = [
            s for s in phase_6_candidates
            if s not in {'automated-review', 'sonar-roundtrip', 'knowledge-capture'}
        ]
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [s for s in phase_5_candidates if s in {'quality-gate', 'module-tests'}],
            },
            'phase_6': {'steps': phase_6_steps},
        }
        return body, 'recipe'

    # Rule 3: docs-only — surgical scope plus no test/code expectations. Skip
    # build verification entirely; keep capture + commit + PR + branch cleanup.
    if scope_estimate in ('surgical', 'single_module') and change_type in ('tech_debt', 'enhancement') and affected_files_count > 0 and _looks_docs_only(phase_5_candidates):
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': [
                    s for s in phase_6_candidates
                    if s not in {'sonar-roundtrip', 'automated-review'}
                ],
            },
        }
        return body, 'docs_only'

    # Rule 4: tests-only — verification change_type with affected files. Run
    # the module-tests step but skip quality-gate; full Phase 6.
    if change_type == 'verification' and affected_files_count > 0:
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [s for s in phase_5_candidates if s == 'module-tests'],
            },
            'phase_6': {'steps': list(phase_6_candidates)},
        }
        return body, 'tests_only'

    # Rule 5: surgical + bug_fix / tech_debt — Q-Gate bypass already applies
    # at outline time (deliverable 4). Here we trim the manifest: no
    # automated-review, no sonar-roundtrip, no knowledge-capture (small,
    # focused changes). Keep lessons-capture + commit/PR/cleanup.
    if scope_estimate == 'surgical' and change_type in ('bug_fix', 'tech_debt'):
        phase_6_steps = [
            s for s in phase_6_candidates
            if s not in {'automated-review', 'sonar-roundtrip', 'knowledge-capture'}
        ]
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [s for s in phase_5_candidates if s in {'quality-gate', 'module-tests'}],
            },
            'phase_6': {'steps': phase_6_steps},
        }
        rule = f'surgical_{change_type}'
        return body, rule

    # Rule 6: verification change_type without affected files — same shape as
    # rule 1's Phase 6 minimum, but Phase 5 still runs whatever was passed.
    if change_type == 'verification' and affected_files_count == 0:
        body = {
            'phase_5': {
                'early_terminate': False,
                'verification_steps': list(phase_5_candidates),
            },
            'phase_6': {
                'steps': [
                    s for s in phase_6_candidates if s in {'knowledge-capture', 'lessons-capture', 'archive-plan'}
                ],
            },
        }
        return body, 'verification_no_files'

    # Rule 7 (default): code-shaped feature / enhancement / large change. Full
    # verification + full finalize. This is the safe baseline the request
    # called the "default code-shaped feature" row.
    body = {
        'phase_5': {
            'early_terminate': False,
            'verification_steps': list(phase_5_candidates),
        },
        'phase_6': {'steps': list(phase_6_candidates)},
    }
    return body, 'default'


def _looks_docs_only(phase_5_candidates: list[str]) -> bool:
    """Heuristic: docs-only plans don't request module-tests or coverage.

    The composer treats any candidate set that lacks ``module-tests`` AND
    ``coverage`` as a docs-only signal. Real code-shaped plans always include
    at least ``module-tests`` in their candidate set.
    """
    return 'module-tests' not in phase_5_candidates and 'coverage' not in phase_5_candidates


# =============================================================================
# Decision Logging
# =============================================================================


def _log_decision(plan_id: str, rule: str, body: dict[str, Any]) -> None:
    """Emit one ``decision.log`` entry for the rule that fired.

    The composer must produce one entry per applied rule per plan run, per the
    request example. We invoke ``manage-logging decision`` via the executor so
    the entry lands in the canonical decision log location.
    """
    phase_5 = body.get('phase_5', {})
    phase_6 = body.get('phase_6', {})
    p5_steps = phase_5.get('verification_steps', [])
    p6_steps = phase_6.get('steps', [])
    early = phase_5.get('early_terminate', False)
    message = (
        f'(plan-marshall:manage-execution-manifest:compose) Rule {rule} fired — '
        f'early_terminate={early}, phase_5.verification_steps={p5_steps}, '
        f'phase_6.steps={p6_steps}'
    )

    # Resolve the executor relative to the marketplace root. We walk up from
    # this script until we find the .plan/execute-script.py sibling, the same
    # bootstrap pattern file_ops.py uses.
    here = Path(__file__).resolve()
    executor: Path | None = None
    for ancestor in here.parents:
        candidate = ancestor / '.plan' / 'execute-script.py'
        if candidate.is_file():
            executor = candidate
            break

    if executor is None:
        # Decision logging is best-effort. If the executor isn't resolvable
        # (e.g., running under an exotic test fixture), fall back silently —
        # the manifest itself is the load-bearing artifact.
        return

    try:
        subprocess.run(
            [
                sys.executable,
                str(executor),
                'plan-marshall:manage-logging:manage-logging',
                'decision',
                '--plan-id',
                plan_id,
                '--level',
                'INFO',
                '--message',
                message,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        # Best-effort logging — never fail the compose call on a logging issue.
        return


# =============================================================================
# Command Handlers
# =============================================================================


def cmd_compose(args: argparse.Namespace) -> dict[str, Any] | None:
    """Compose and write the execution manifest."""
    plan_id = require_valid_plan_id(args)

    if args.change_type not in VALID_CHANGE_TYPES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_change_type',
            'message': f'Invalid change_type: {args.change_type!r}. Must be one of {list(VALID_CHANGE_TYPES)}',
        }
    if args.scope_estimate not in VALID_SCOPE_ESTIMATES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_scope_estimate',
            'message': f'Invalid scope_estimate: {args.scope_estimate!r}. Must be one of {list(VALID_SCOPE_ESTIMATES)}',
        }
    if args.track not in VALID_TRACKS:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_track',
            'message': f'Invalid track: {args.track!r}. Must be one of {list(VALID_TRACKS)}',
        }

    phase_5_candidates = _split_csv(args.phase_5_steps, DEFAULT_PHASE_5_STEPS)
    phase_6_candidates = _split_csv(args.phase_6_steps, DEFAULT_PHASE_6_STEPS)

    affected_files_count = max(0, int(args.affected_files_count or 0))
    recipe_key = args.recipe_key or None

    body, rule = _decide(
        change_type=args.change_type,
        track=args.track,
        scope_estimate=args.scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_candidates=phase_5_candidates,
        phase_6_candidates=phase_6_candidates,
    )

    manifest = {
        'manifest_version': MANIFEST_VERSION,
        'plan_id': plan_id,
        **body,
    }
    write_manifest(plan_id, manifest)
    _log_decision(plan_id, rule, body)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': MANIFEST_FILENAME,
        'created': True,
        'manifest_version': MANIFEST_VERSION,
        'phase_5': {
            'early_terminate': body['phase_5']['early_terminate'],
            'verification_steps_count': len(body['phase_5']['verification_steps']),
        },
        'phase_6': {
            'steps_count': len(body['phase_6']['steps']),
        },
        'rule_fired': rule,
    }


def cmd_read(args: argparse.Namespace) -> dict[str, Any] | None:
    """Read and return the manifest as TOON-friendly dict."""
    plan_id = require_valid_plan_id(args)

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    return {
        'status': 'success',
        'plan_id': plan_id,
        **manifest,
    }


def cmd_validate(args: argparse.Namespace) -> dict[str, Any] | None:
    """Validate manifest schema and (optionally) step IDs against candidate sets."""
    plan_id = require_valid_plan_id(args)

    manifest = read_manifest(plan_id)
    if manifest is None:
        output_toon_error(
            'file_not_found',
            f'execution.toon not found for plan {plan_id}',
            plan_id=plan_id,
        )
        return None

    errors: list[str] = []

    # Schema checks.
    if manifest.get('manifest_version') != MANIFEST_VERSION:
        errors.append(
            f'manifest_version mismatch: expected {MANIFEST_VERSION}, got {manifest.get("manifest_version")!r}'
        )
    if manifest.get('plan_id') != plan_id:
        errors.append(f'plan_id mismatch: expected {plan_id!r}, got {manifest.get("plan_id")!r}')

    phase_5 = manifest.get('phase_5')
    phase_6 = manifest.get('phase_6')
    if not isinstance(phase_5, dict):
        errors.append('phase_5 section missing or not a mapping')
        phase_5 = {}
    if not isinstance(phase_6, dict):
        errors.append('phase_6 section missing or not a mapping')
        phase_6 = {}

    if 'early_terminate' not in phase_5 or not isinstance(phase_5.get('early_terminate'), bool):
        errors.append('phase_5.early_terminate missing or not a bool')
    p5_steps = phase_5.get('verification_steps', [])
    if not isinstance(p5_steps, list):
        errors.append('phase_5.verification_steps must be a list')
        p5_steps = []
    p6_steps = phase_6.get('steps', [])
    if not isinstance(p6_steps, list):
        errors.append('phase_6.steps must be a list')
        p6_steps = []

    # Step-ID checks (only when caller passes candidate sets).
    p5_unknown: list[str] = []
    p6_unknown: list[str] = []
    if args.phase_5_steps is not None:
        allowed_5 = set(_split_csv(args.phase_5_steps, ()))
        p5_unknown = [s for s in p5_steps if s not in allowed_5]
        if p5_unknown:
            errors.append(f'phase_5.verification_steps contains unknown IDs: {p5_unknown}')
    if args.phase_6_steps is not None:
        allowed_6 = set(_split_csv(args.phase_6_steps, ()))
        p6_unknown = [s for s in p6_steps if s not in allowed_6]
        if p6_unknown:
            errors.append(f'phase_6.steps contains unknown IDs: {p6_unknown}')

    if errors:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_manifest',
            'message': '; '.join(errors),
            'phase_5_unknown_steps_count': len(p5_unknown),
            'phase_5_unknown_steps': p5_unknown,
            'phase_6_unknown_steps_count': len(p6_unknown),
            'phase_6_unknown_steps': p6_unknown,
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'valid': True,
        'phase_5_unknown_steps_count': 0,
        'phase_6_unknown_steps_count': 0,
    }


# =============================================================================
# CLI
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Manage the per-plan execution manifest', allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    compose_parser = subparsers.add_parser('compose', help='Compose and write execution.toon', allow_abbrev=False)
    add_plan_id_arg(compose_parser)
    compose_parser.add_argument('--change-type', required=True, help='Change type (one of VALID_CHANGE_TYPES)')
    compose_parser.add_argument('--track', required=True, help='Outline track: simple|complex')
    compose_parser.add_argument(
        '--scope-estimate', required=True, help='scope_estimate (none|surgical|single_module|multi_module|broad)'
    )
    compose_parser.add_argument('--recipe-key', default=None, help='Recipe key (e.g. lesson_cleanup) when applicable')
    compose_parser.add_argument(
        '--affected-files-count', type=int, default=0, help='Count of affected files from the outline'
    )
    compose_parser.add_argument('--phase-5-steps', default=None, help='Comma-separated candidate Phase 5 step IDs')
    compose_parser.add_argument('--phase-6-steps', default=None, help='Comma-separated candidate Phase 6 step IDs')

    read_parser = subparsers.add_parser('read', help='Read execution.toon as TOON', allow_abbrev=False)
    add_plan_id_arg(read_parser)

    validate_parser = subparsers.add_parser('validate', help='Validate execution.toon', allow_abbrev=False)
    add_plan_id_arg(validate_parser)
    validate_parser.add_argument('--phase-5-steps', default=None, help='Comma-separated allowed Phase 5 step IDs')
    validate_parser.add_argument('--phase-6-steps', default=None, help='Comma-separated allowed Phase 6 step IDs')

    return parser


@safe_main
def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    handlers = {
        'compose': cmd_compose,
        'read': cmd_read,
        'validate': cmd_validate,
    }
    handler = handlers[args.command]
    result = handler(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
