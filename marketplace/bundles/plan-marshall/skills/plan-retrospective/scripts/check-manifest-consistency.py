#!/usr/bin/env python3
"""Cross-check the per-plan execution manifest against the actual end-of-execute diff.

Reads ``execution.toon`` (produced by ``plan-marshall:manage-execution-manifest``)
plus the matching ``decision.log`` entries, then evaluates each manifest
assumption against ``git diff {base}...HEAD --name-only``. Emits one finding
per violated assumption in the same fragment shape as
``check-artifact-consistency.py``.

Sibling to ``check-artifact-consistency.py`` — both scripts produce
deterministic TOON fragments that the retrospective orchestrator pipes into
``collect-fragments add`` and finally ``compile-report``.

Cross-check matrix is documented in ``standards/manifest-crosscheck.md``.

Usage:
    python3 check-manifest-consistency.py run --plan-id my-plan --mode live
    python3 check-manifest-consistency.py run --archived-plan-path /abs --mode archived
    python3 check-manifest-consistency.py run --plan-id my-plan --mode live \\
        --diff-file /abs/path/to/diff.txt   # for tests / offline runs
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from file_ops import base_path, output_toon, safe_main  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]

# Manifest schema version known to this script. Bump in lock-step with
# ``manage-execution-manifest`` whenever the manifest body changes shape.
KNOWN_MANIFEST_VERSION = 1

MANIFEST_FILENAME = 'execution.toon'
DECISION_LOG_RELPATH = ('logs', 'decision.log')

# Paths whose changes are bookkeeping side-effects of phase-6-finalize, not
# implementation work. Filtered before evaluating any rule.
_BOOKKEEPING_PREFIXES = ('.plan/', '.claude/')
_REPORT_NAME_RE = re.compile(r'(^|/)quality-verification-report(-audit-[^/]+)?\.md$')

# Docs-only path classifier (Rule M1).
_DOCS_SUFFIXES = ('.md', '.adoc')
_DOCS_DIR_TOKENS = ('/references/', '/templates/')

# Test-file classifier (Rule M3).
_TEST_DIR_TOKENS = ('/test/', '/tests/')
_TEST_NAME_RE = re.compile(
    r'(^|/)(test_[^/]+\.py|[^/]+_test\.py|[^/]+Test\.java|[^/]+Spec\.java|[^/]+\.test\.js|[^/]+\.spec\.js)$'
)

# Decision-log caller tag we surface to the report.
_DECISION_TAG = '(plan-marshall:manage-execution-manifest:compose)'

# Maximum culprit list length included in a finding's user-visible message.
_CULPRITS_PREVIEW = 5


# =============================================================================
# Resolution helpers
# =============================================================================


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f"Unknown mode: {mode!r}")


# =============================================================================
# Loaders
# =============================================================================


def load_manifest(plan_dir: Path) -> dict[str, Any] | None:
    """Return the parsed manifest dict, or ``None`` when ``execution.toon`` is absent.

    A missing manifest is the legacy-plan signal — the caller treats it as a
    skip rather than a failure. Parse failures bubble up as ValueError because
    a corrupt manifest is a real problem worth surfacing.
    """
    manifest_path = plan_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    parsed = parse_toon(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(parsed, dict):
        raise ValueError(f'{MANIFEST_FILENAME} must parse to a top-level dict')
    return parsed


def load_decision_log_entries(plan_dir: Path) -> list[str]:
    """Return raw decision-log lines whose caller tag is the manifest composer.

    The script intentionally returns full log lines (including timestamp and
    severity prefix) so the report renderer can show the entry verbatim.
    """
    log_path = plan_dir
    for segment in DECISION_LOG_RELPATH:
        log_path = log_path / segment
    if not log_path.exists():
        return []
    matches: list[str] = []
    for line in log_path.read_text(encoding='utf-8').splitlines():
        if _DECISION_TAG in line:
            matches.append(line)
    return matches


def load_diff_files(diff_file: str | None, base_ref: str | None) -> tuple[list[str], str]:
    """Return ``(file_paths, base_label)`` from either a pre-saved diff file or git.

    When ``--diff-file`` is provided (typical in tests), read it directly. Otherwise
    invoke ``git diff {base}...HEAD --name-only`` and treat any failure as
    "no diff available" rather than aborting — the manifest cross-check is a
    best-effort retrospective signal, not a build-blocking gate.
    """
    if diff_file:
        path = Path(diff_file)
        if not path.exists():
            raise ValueError(f'Diff file does not exist: {diff_file}')
        return _split_diff_lines(path.read_text(encoding='utf-8')), f'file:{path.name}'

    if not base_ref:
        return [], 'unknown'

    try:
        result = subprocess.run(
            ['git', 'diff', f'{base_ref}...HEAD', '--name-only'],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return [], base_ref
    if result.returncode != 0:
        return [], base_ref
    return _split_diff_lines(result.stdout), base_ref


def _split_diff_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


# =============================================================================
# Filtering
# =============================================================================


def filter_bookkeeping(files: list[str]) -> tuple[list[str], list[str]]:
    """Return ``(kept, dropped)`` lists.

    A path is dropped when:
    - it begins with a bookkeeping prefix (``.plan/``, ``.claude/``), OR
    - its filename matches the ``quality-verification-report`` pattern.
    """
    kept: list[str] = []
    dropped: list[str] = []
    for path in files:
        if any(path.startswith(prefix) for prefix in _BOOKKEEPING_PREFIXES):
            dropped.append(path)
            continue
        if _REPORT_NAME_RE.search(path):
            dropped.append(path)
            continue
        kept.append(path)
    return kept, dropped


# =============================================================================
# Path classifiers
# =============================================================================


def is_docs_path(path: str) -> bool:
    """A path counts as docs when it ends with .md/.adoc OR sits under references/ / templates/."""
    if path.endswith(_DOCS_SUFFIXES):
        return True
    return any(token in f'/{path}' for token in _DOCS_DIR_TOKENS)


def is_test_path(path: str) -> bool:
    """A path counts as a test file via either dir token or filename pattern."""
    normalized = f'/{path}'
    if any(token in normalized for token in _TEST_DIR_TOKENS):
        return True
    return bool(_TEST_NAME_RE.search(path))


# =============================================================================
# Rule evaluators
# =============================================================================


def _make_check(name: str, status: str, message: str) -> dict[str, str]:
    return {'name': name, 'status': status, 'message': message}


def _make_finding(
    severity: str,
    code: str,
    message: str,
    culprits: list[str] | None = None,
) -> dict[str, Any]:
    finding: dict[str, Any] = {'severity': severity, 'code': code, 'message': message}
    if culprits:
        finding['culprits'] = culprits
    return finding


def evaluate_manifest_version(manifest: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any] | None]:
    actual = manifest.get('manifest_version')
    if actual == KNOWN_MANIFEST_VERSION:
        return _make_check(
            'manifest_version_recognized', 'pass', f'manifest_version={actual} recognized'
        ), None
    finding = _make_finding(
        'error',
        'manifest_version_unknown',
        f'manifest_version={actual!r} not recognized by check-manifest-consistency '
        f'(expected {KNOWN_MANIFEST_VERSION})',
    )
    return _make_check(
        'manifest_version_recognized', 'fail', finding['message']
    ), finding


def evaluate_docs_only(
    manifest: dict[str, Any], filtered_files: list[str]
) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Rule M1: empty verification_steps + non-early-terminate → docs-only diff."""
    phase_5 = manifest.get('phase_5', {}) if isinstance(manifest.get('phase_5'), dict) else {}
    steps = phase_5.get('verification_steps', [])
    early = bool(phase_5.get('early_terminate', False))
    if not isinstance(steps, list) or steps or early:
        return _make_check(
            'docs_only_diff', 'skip',
            'rule M1 not applicable — verification_steps non-empty or early_terminate=true'
        ), None

    culprits = sorted(p for p in filtered_files if not is_docs_path(p))
    if not culprits:
        return _make_check(
            'docs_only_diff', 'pass',
            f'all {len(filtered_files)} non-bookkeeping diff entries are docs-shaped'
        ), None

    preview = culprits[:_CULPRITS_PREVIEW]
    finding = _make_finding(
        'warning',
        'docs_only_diff_violation',
        f'phase_5.verification_steps is empty but diff includes non-docs files: {preview}',
        culprits,
    )
    return _make_check('docs_only_diff', 'fail', finding['message']), finding


def evaluate_early_terminate(
    manifest: dict[str, Any], filtered_files: list[str]
) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Rule M2: early_terminate=true → empty implementation diff."""
    phase_5 = manifest.get('phase_5', {}) if isinstance(manifest.get('phase_5'), dict) else {}
    early = bool(phase_5.get('early_terminate', False))
    if not early:
        return _make_check(
            'early_terminate_diff', 'skip', 'rule M2 not applicable — early_terminate=false'
        ), None

    if not filtered_files:
        return _make_check(
            'early_terminate_diff', 'pass', 'early_terminate=true and diff is empty'
        ), None

    culprits = sorted(filtered_files)
    preview = culprits[:_CULPRITS_PREVIEW]
    finding = _make_finding(
        'warning',
        'early_terminate_diff_nonempty',
        f'phase_5.early_terminate=true but diff includes implementation files: {preview}',
        culprits,
    )
    return _make_check('early_terminate_diff', 'fail', finding['message']), finding


def evaluate_tests_only(
    manifest: dict[str, Any], filtered_files: list[str]
) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Rule M3: verification_steps == ['module-tests'] → tests-only diff (or docs)."""
    phase_5 = manifest.get('phase_5', {}) if isinstance(manifest.get('phase_5'), dict) else {}
    steps = phase_5.get('verification_steps', [])
    if not isinstance(steps, list) or steps != ['module-tests']:
        return _make_check(
            'tests_only_diff', 'skip',
            'rule M3 not applicable — verification_steps != ["module-tests"]'
        ), None

    culprits = sorted(
        p for p in filtered_files if not is_test_path(p) and not is_docs_path(p)
    )
    if not culprits:
        return _make_check(
            'tests_only_diff', 'pass',
            f'all {len(filtered_files)} non-bookkeeping diff entries are tests or docs'
        ), None

    preview = culprits[:_CULPRITS_PREVIEW]
    finding = _make_finding(
        'warning',
        'tests_only_diff_violation',
        f'phase_5 manifest is tests-only but diff includes non-test source files: {preview}',
        culprits,
    )
    return _make_check('tests_only_diff', 'fail', finding['message']), finding


def evaluate_branch_cleanup(
    manifest: dict[str, Any], filtered_files: list[str]
) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Rule M4: branch-cleanup present in phase_6 → diff should not be empty."""
    phase_6 = manifest.get('phase_6', {}) if isinstance(manifest.get('phase_6'), dict) else {}
    steps = phase_6.get('steps', [])
    if not isinstance(steps, list) or 'branch-cleanup' not in steps:
        return _make_check(
            'branch_cleanup_changes', 'skip',
            'rule M4 not applicable — branch-cleanup not in phase_6.steps'
        ), None

    if filtered_files:
        return _make_check(
            'branch_cleanup_changes', 'pass',
            f'branch-cleanup paired with {len(filtered_files)} changed file(s)'
        ), None

    finding = _make_finding(
        'info',
        'branch_cleanup_without_changes',
        'phase_6.steps includes branch-cleanup but diff is empty — nothing to push/clean',
    )
    return _make_check('branch_cleanup_changes', 'fail', finding['message']), finding


# =============================================================================
# Orchestration
# =============================================================================


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    plan_id = args.plan_id or plan_dir.name

    manifest = load_manifest(plan_dir)
    if manifest is None:
        # Legacy plans pre-dating the manifest deliverable: emit a skipped
        # fragment so the orchestrator can cleanly drop the section.
        return {
            'status': 'skipped',
            'aspect': 'manifest-decisions',
            'plan_id': plan_id,
            'plan_dir': str(plan_dir),
            'manifest_present': False,
            'reason': f'{MANIFEST_FILENAME} not found',
            'checks': [],
            'findings': [],
            'summary': {'passed': 0, 'failed': 0, 'skipped': 0, 'findings': 0},
        }

    decision_entries = load_decision_log_entries(plan_dir)
    raw_files, base_label = load_diff_files(args.diff_file, args.base_ref)
    kept_files, dropped_files = filter_bookkeeping(raw_files)

    checks: list[dict[str, str]] = []
    findings: list[dict[str, Any]] = []

    # evaluate_manifest_version has a different signature (manifest only) and is
    # called once outside the dispatch loop. The remaining evaluators share the
    # (manifest, filtered_files) signature, which lets mypy infer a homogeneous
    # callable type without per-call type-ignores.
    version_check, version_finding = evaluate_manifest_version(manifest)
    checks.append(version_check)
    if version_finding is not None:
        findings.append(version_finding)

    diff_evaluators: tuple[
        Callable[[dict[str, Any], list[str]], tuple[dict[str, str], dict[str, Any] | None]],
        ...,
    ] = (
        evaluate_docs_only,
        evaluate_early_terminate,
        evaluate_tests_only,
        evaluate_branch_cleanup,
    )
    for evaluator in diff_evaluators:
        check, finding = evaluator(manifest, kept_files)
        checks.append(check)
        if finding is not None:
            findings.append(finding)

    summary = {
        'passed': sum(1 for c in checks if c['status'] == 'pass'),
        'failed': sum(1 for c in checks if c['status'] == 'fail'),
        'skipped': sum(1 for c in checks if c['status'] == 'skip'),
        'findings': len(findings),
    }

    return {
        'status': 'success',
        'aspect': 'manifest-decisions',
        'plan_id': plan_id,
        'plan_dir': str(plan_dir),
        'manifest_present': True,
        'manifest': {
            'manifest_version': manifest.get('manifest_version'),
            'phase_5': manifest.get('phase_5', {}),
            'phase_6': manifest.get('phase_6', {}),
        },
        'decision_log_entries': decision_entries,
        'diff': {
            'base': base_label,
            'files_total': len(raw_files),
            'files_filtered': len(dropped_files),
            'files_kept': len(kept_files),
        },
        'checks': checks,
        'findings': findings,
        'summary': summary,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Cross-check execution manifest against actual end-of-execute diff',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Run all manifest cross-checks', allow_abbrev=False)
    run_parser.add_argument('--plan-id', help='Plan identifier (live mode)')
    run_parser.add_argument(
        '--archived-plan-path',
        help='Absolute path to archived plan directory (archived mode)',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.add_argument(
        '--diff-file',
        default=None,
        help='Pre-saved diff (one path per line). Bypasses the git invocation. Used in tests.',
    )
    run_parser.add_argument(
        '--base-ref',
        default=None,
        help='Git base ref for the diff (e.g. origin/main). Required when --diff-file is absent.',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
