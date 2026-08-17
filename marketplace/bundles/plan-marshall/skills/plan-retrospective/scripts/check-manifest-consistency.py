#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
    python3 check-manifest-consistency.py run --plan-id EXAMPLE-PLAN --mode live
    python3 check-manifest-consistency.py run --archived-plan-path /abs --mode archived
    python3 check-manifest-consistency.py run --plan-id EXAMPLE-PLAN --mode live \\
        --diff-file work/footprint.txt      # plan-relative, or an absolute path
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _footprint_classification import (
    CATEGORY_CONFIG,
    CATEGORY_REPORT,
    CATEGORY_RUNTIME_STATE,
    classify_footprint,
    is_docs_path,
    load_oracle_routes,
    oracle_available,
)
from _footprint_resolver import resolve_diff_file_path
from _step_key_canonical import canonicalize_step_key
from file_ops import base_path, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
)
from toon_parser import parse_toon

# Manifest schema version known to this script. Bump in lock-step with
# ``manage-execution-manifest`` whenever the manifest body changes shape.
KNOWN_MANIFEST_VERSION = 1

MANIFEST_FILENAME = 'execution.toon'
DECISION_LOG_RELPATH = ('logs', 'decision.log')

# The categories :func:`filter_bookkeeping` drops before any rule is evaluated —
# bookkeeping side-effects of phase-6-finalize rather than implementation work.
# The membership decision itself is the ORACLE'S (``build.map`` in marshal.json),
# routed through ``_footprint_classification``; this tuple only says which of the
# oracle's answers this consumer treats as droppable.
#
# ``unclassified`` is deliberately ABSENT. A path no declared route covers is one
# the oracle has no opinion about, and dropping it would put a private guess back
# in charge of exactly the question this filter was getting wrong — silently, and
# with the oracle's authority borrowed for it. An unrouted path is therefore
# RETAINED and counted, which can only widen what a rule examines.
_DROPPED_CATEGORIES = (CATEGORY_RUNTIME_STATE, CATEGORY_REPORT, CATEGORY_CONFIG)

# Canonical-verify step-id prefix (Rule M3). The composer emits every built-in
# verify step as ``default:verify:{canonical}``, boundary-normalized to the bare
# ``verify:{canonical}`` form — never as a bare ``{canonical}``. Comparing a
# manifest's verification_steps against an unprefixed name is what made M3
# unreachable on every composer-produced manifest.
_CANONICAL_VERIFY_PREFIX = 'verify:'

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
    raise ValueError(f'Unknown mode: {mode!r}')


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
    try:
        raw = manifest_path.read_text(encoding='utf-8')
    except OSError:
        # Fail closed on an I/O-boundary read failure: a manifest that passed
        # .exists() but raises on read (permission denied, the path resolves to
        # a directory, a mid-read deletion race) degrades to the same skip
        # sentinel as a missing manifest rather than crashing the verdict path.
        # The deliberate "corrupt manifest bubbles as ValueError" parse-failure
        # contract below is preserved — only the OSError is caught here, so a
        # parse_toon ValueError still bubbles.
        return None
    parsed = parse_toon(raw)
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
    try:
        raw = log_path.read_text(encoding='utf-8')
    except OSError:
        # Fail closed: a decision log that passed .exists() but raises on read
        # degrades to the empty-matches sentinel (the same value returned when
        # the log is absent) rather than crashing the verdict path.
        return []
    matches: list[str] = []
    for line in raw.splitlines():
        if _DECISION_TAG in line:
            matches.append(line)
    return matches


def load_diff_files(diff_file: str | None, base_ref: str | None, plan_dir: Path) -> tuple[list[str], str]:
    """Return ``(file_paths, base_label)`` from either a pre-saved diff file or git.

    When ``--diff-file`` is provided, read it directly. A RELATIVE argument is
    resolved against the plan directory first and the cwd second
    (:func:`resolve_diff_file_path`), so the plan-relative form the capture pattern
    documents resolves to the same file an absolute path names — and a
    supplied-but-unresolvable path raises rather than degrading to an empty diff.

    Without ``--diff-file``, invoke ``git diff {base}...HEAD --name-only`` and treat
    any failure as "no diff available" rather than aborting — the manifest
    cross-check is a best-effort retrospective signal, not a build-blocking gate.
    """
    if diff_file:
        path = resolve_diff_file_path(diff_file, plan_dir)
        try:
            raw = path.read_text(encoding='utf-8')
        except OSError as e:
            # Fail closed on the explicit --diff-file path: a diff file that
            # passed .exists() but raises on read converts to a ValueError
            # carrying the OSError context, consistent with the
            # "Diff file does not exist" ValueError above — an explicitly
            # supplied diff that cannot be read is a caller error, not a
            # silently-empty diff.
            raise ValueError(f'Diff file could not be read: {diff_file}: {e}') from e
        return _split_diff_lines(raw), f'file:{path.name}'

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


def filter_bookkeeping(files: list[str]) -> tuple[list[str], list[str], dict[str, Any]]:
    """Return ``(kept, dropped, reduction)`` — the footprint partitioned by the oracle.

    A path is dropped when its ``_footprint_classification`` category is one of
    :data:`_DROPPED_CATEGORIES`: the genuinely-runtime ``.plan/`` state directory,
    the plan's own quality-verification report, or a path the ORACLE routes with
    role ``config``. Everything else is kept — production and test (the oracle's
    implementation roles), documentation, and any path no declared route covers.

    This replaces a private ``('.plan/', '.claude/')`` prefix tuple that
    contradicted the project's own ``build.map``, which routes the project-local
    skill tree as ``production``. The filter was discarding production source as
    bookkeeping and every downstream rule then evaluated the remainder.

    Args:
        files: The supplied footprint, one repo-relative path per entry.

    Returns:
        ``(kept, dropped, reduction)``. ``reduction`` carries the per-category
        counts, whether the oracle answered at all, and the ``majority_discarded``
        flag :func:`apply_input_reduction` uses to refuse a bare clean pass.
    """
    routes = load_oracle_routes()
    buckets = classify_footprint(files, routes)

    kept: list[str] = []
    dropped: list[str] = []
    for path in files:
        target = dropped if _category_of(path, buckets) in _DROPPED_CATEGORIES else kept
        target.append(path)

    reduction = {
        'oracle_available': oracle_available(routes),
        'supplied': len(files),
        'kept': len(kept),
        'dropped': len(dropped),
        # Every category key is present even at zero, so a reader cannot mistake
        # an absent key for a measured zero.
        'by_category': {category: len(paths) for category, paths in buckets.items()},
        'majority_discarded': len(dropped) > len(kept),
    }
    return kept, dropped, reduction


def _category_of(path: str, buckets: dict[str, list[str]]) -> str:
    """Return the category bucket ``path`` was filed under."""
    for category, paths in buckets.items():
        if path in paths:
            return category
    raise ValueError(f'path not classified: {path!r}')


# =============================================================================
# Path classifiers
# =============================================================================


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
        return _make_check('manifest_version_recognized', 'pass', f'manifest_version={actual} recognized'), None
    finding = _make_finding(
        'error',
        'manifest_version_unknown',
        f'manifest_version={actual!r} not recognized by check-manifest-consistency (expected {KNOWN_MANIFEST_VERSION})',
    )
    return _make_check('manifest_version_recognized', 'fail', finding['message']), finding


def evaluate_docs_only(
    manifest: dict[str, Any], filtered_files: list[str]
) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Rule M1: empty verification_steps + non-early-terminate → docs-only diff."""
    phase_5 = manifest.get('phase_5', {}) if isinstance(manifest.get('phase_5'), dict) else {}
    steps = phase_5.get('verification_steps', [])
    early = bool(phase_5.get('early_terminate', False))
    if not isinstance(steps, list) or steps or early:
        return _make_check(
            'docs_only_diff', 'skip', 'rule M1 not applicable — verification_steps non-empty or early_terminate=true'
        ), None

    culprits = sorted(p for p in filtered_files if not is_docs_path(p))
    if not culprits:
        return _make_check(
            'docs_only_diff', 'pass', f'all {len(filtered_files)} non-bookkeeping diff entries are docs-shaped'
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
        return _make_check('early_terminate_diff', 'skip', 'rule M2 not applicable — early_terminate=false'), None

    if not filtered_files:
        return _make_check('early_terminate_diff', 'pass', 'early_terminate=true and diff is empty'), None

    culprits = sorted(filtered_files)
    preview = culprits[:_CULPRITS_PREVIEW]
    finding = _make_finding(
        'warning',
        'early_terminate_diff_nonempty',
        f'phase_5.early_terminate=true but diff includes implementation files: {preview}',
        culprits,
    )
    return _make_check('early_terminate_diff', 'fail', finding['message']), finding


def normalize_verification_step(step: str) -> str:
    """Return the bare canonical name a ``verification_steps`` entry denotes.

    Strips the optional ``default:`` prefix (via the shared
    :func:`canonicalize_step_key`) and then the canonical-verify ``verify:``
    prefix, so ``default:verify:module-tests``, ``verify:module-tests`` and a bare
    ``module-tests`` all resolve to ``module-tests``.

    The composer emits the ``verify:``-prefixed form and never the bare one, so a
    rule that compares against an unprefixed name without this normalization can
    never fire on a composer-produced manifest. The bare form is still accepted
    because archived manifests and hand-built fixtures carry it.
    """
    bare = canonicalize_step_key(step)
    if bare.startswith(_CANONICAL_VERIFY_PREFIX):
        return bare[len(_CANONICAL_VERIFY_PREFIX) :]
    return bare


def evaluate_tests_only(
    manifest: dict[str, Any], filtered_files: list[str]
) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Rule M3: verification_steps denotes module-tests only → tests-only diff (or docs).

    The manifest signal is compared on the NORMALIZED step names
    (:func:`normalize_verification_step`), because the composer emits every
    built-in verify step as ``verify:{canonical}``. Comparing the raw list against
    a bare ``['module-tests']`` made this rule unreachable on every manifest the
    composer produces.
    """
    phase_5 = manifest.get('phase_5', {}) if isinstance(manifest.get('phase_5'), dict) else {}
    steps = phase_5.get('verification_steps', [])
    if not isinstance(steps, list) or [normalize_verification_step(str(s)) for s in steps] != ['module-tests']:
        return _make_check(
            'tests_only_diff',
            'skip',
            'rule M3 not applicable — verification_steps does not denote module-tests only',
        ), None

    culprits = sorted(p for p in filtered_files if not is_test_path(p) and not is_docs_path(p))
    if not culprits:
        return _make_check(
            'tests_only_diff', 'pass', f'all {len(filtered_files)} non-bookkeeping diff entries are tests or docs'
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
    manifest: dict[str, Any],
    filtered_files: list[str],
    base_label: str,
    raw_files_total: int,
) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Rule M4: branch-cleanup present in phase_6 → diff should not be empty.

    The rule is skipped when no diff data is available — ``base_label`` is
    ``"unknown"`` or the raw diff is empty (``raw_files_total == 0``). In those
    cases the absence of changes is an artefact of missing diff input, not a
    real defect, so emitting a fail would be a false positive. This mirrors the
    skip-on-missing-data behaviour of the other diff evaluators
    (``evaluate_docs_only``, ``evaluate_early_terminate``, etc.).
    """
    phase_6 = manifest.get('phase_6', {}) if isinstance(manifest.get('phase_6'), dict) else {}
    steps = phase_6.get('steps', [])
    if not isinstance(steps, list) or 'branch-cleanup' not in steps:
        return _make_check(
            'branch_cleanup_changes', 'skip', 'rule M4 not applicable — branch-cleanup not in phase_6.steps'
        ), None

    if base_label == 'unknown' or raw_files_total == 0:
        return _make_check(
            'branch_cleanup_changes',
            'skip',
            'rule M4 skipped — no diff data available (base=unknown or empty diff)',
        ), None

    if filtered_files:
        return _make_check(
            'branch_cleanup_changes', 'pass', f'branch-cleanup paired with {len(filtered_files)} changed file(s)'
        ), None

    finding = _make_finding(
        'info',
        'branch_cleanup_without_changes',
        'phase_6.steps includes branch-cleanup but diff is empty — nothing to push/clean',
    )
    return _make_check('branch_cleanup_changes', 'fail', finding['message']), finding


# =============================================================================
# Input-reduction reporting (D2)
# =============================================================================

#: The check status a diff-fed rule takes when it would otherwise emit a bare
#: clean pass over a majority-discarded footprint. Distinct from ``skip`` (the
#: rule did not apply) and from ``pass`` (the rule applied and was satisfied):
#: ``indeterminate`` says the rule applied but saw too little of the supplied
#: input for its verdict to mean anything.
STATUS_INDETERMINATE = 'indeterminate'

#: The checks evaluated against the FILTERED footprint. Only these are subject to
#: the reduction report — ``manifest_version_recognized`` reads the manifest body
#: alone, so no amount of diff filtering affects its verdict.
_DIFF_FED_CHECKS = frozenset(
    {'docs_only_diff', 'early_terminate_diff', 'tests_only_diff', 'branch_cleanup_changes'}
)


def apply_input_reduction(checks: list[dict[str, str]], reduction: dict[str, Any]) -> list[dict[str, str]]:
    """Annotate — and where required downgrade — every diff-fed check.

    Two obligations, both discharged here so no rule evaluator can forget one:

    - **Every** diff-fed check that ran against a reduced input set has the
      reduction appended to its message, so the count the rule actually saw is
      visible beside its verdict rather than buried in the ``diff`` block.
    - A check that would otherwise emit a bare clean ``pass`` while the MAJORITY of
      the supplied footprint was discarded becomes
      :data:`STATUS_INDETERMINATE` instead. A clean pass over a small fraction of
      the real input is an unsubstantiated verdict, and it reads in every
      downstream summary exactly like a substantiated one — which is how a real
      run reported ``passed: 2, failed: 0, findings: 0`` over a phantom one-file
      footprint whose discarded remainder was the whole subject of the plan.

    A ``fail`` is never downgraded: a violation found in the surviving fraction is
    still a violation, and a reduced input can only have hidden more of them. A
    ``skip`` is never downgraded either — the rule did not apply, which the
    filtering did not decide.

    Args:
        checks: The evaluated checks, mutated copies of which are returned.
        reduction: The block :func:`filter_bookkeeping` produced.

    Returns:
        The checks, with diff-fed entries annotated and possibly downgraded.
    """
    dropped = reduction['dropped']
    if not dropped:
        return checks

    note = (
        f'{dropped} of {reduction["supplied"]} supplied paths were filtered as '
        f'bookkeeping before evaluation'
    )
    if not reduction['oracle_available']:
        note += ' (build_map oracle unavailable — only runtime-state paths were classifiable)'

    annotated: list[dict[str, str]] = []
    for check in checks:
        if check['name'] not in _DIFF_FED_CHECKS or check['status'] == 'skip':
            annotated.append(check)
            continue
        updated = dict(check)
        if check['status'] == 'pass' and reduction['majority_discarded']:
            updated['status'] = STATUS_INDETERMINATE
            updated['message'] = f'{check["message"]} — VERDICT WITHHELD: {note}'
        else:
            updated['message'] = f'{check["message"]} ({note})'
        annotated.append(updated)
    return annotated


# =============================================================================
# Orchestration
# =============================================================================


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    plan_id = args.plan_id or plan_dir.name

    manifest = load_manifest(plan_dir)
    # SHIM(B): archived plans predating the execution-manifest deliverable (no execution.toon was written).
    # shim-owner: plan-retrospective
    # shim-floor: the introduction of the execution-manifest deliverable (execution.toon; MANIFEST_FILENAME) as a phase output; predates this shallow clone's root (dcd3c00 / #1105), so not PR-pinnable here.
    # shim-remove-when: no archived plan predating the execution-manifest deliverable is retained.
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
            'summary': {'passed': 0, 'failed': 0, 'skipped': 0, 'indeterminate': 0, 'findings': 0},
        }

    decision_entries = load_decision_log_entries(plan_dir)
    raw_files, base_label = load_diff_files(args.diff_file, args.base_ref, plan_dir)
    kept_files, dropped_files, reduction = filter_bookkeeping(raw_files)

    checks: list[dict[str, str]] = []
    findings: list[dict[str, Any]] = []

    # evaluate_manifest_version (manifest only) has a distinct signature and is
    # called once outside the dispatch loop. The remaining evaluators share
    # the (manifest, filtered_files) signature, which lets mypy infer a
    # homogeneous callable type without per-call type-ignores.
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
    )
    for evaluator in diff_evaluators:
        check, finding = evaluator(manifest, kept_files)
        checks.append(check)
        if finding is not None:
            findings.append(finding)

    # evaluate_branch_cleanup needs the diff-availability signal so it can skip
    # (instead of false-positive failing) when no diff data was resolved.
    cleanup_check, cleanup_finding = evaluate_branch_cleanup(
        manifest, kept_files, base_label, len(raw_files)
    )
    checks.append(cleanup_check)
    if cleanup_finding is not None:
        findings.append(cleanup_finding)

    # Applied AFTER every evaluator so no rule can emit a bare clean pass over a
    # majority-discarded footprint, and so the reduction is reported exactly once.
    checks = apply_input_reduction(checks, reduction)

    summary = {
        'passed': sum(1 for c in checks if c['status'] == 'pass'),
        'failed': sum(1 for c in checks if c['status'] == 'fail'),
        'skipped': sum(1 for c in checks if c['status'] == 'skip'),
        'indeterminate': sum(1 for c in checks if c['status'] == STATUS_INDETERMINATE),
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
            # The reduction the rules were subject to, published beside the counts
            # so a reader can see WHICH categories were discarded and whether the
            # oracle answered at all — never only that some number was dropped.
            'filtered_by_category': reduction['by_category'],
            'oracle_available': reduction['oracle_available'],
            'majority_discarded': reduction['majority_discarded'],
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
    add_plan_id_arg(run_parser, required=False)
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
        help=(
            'Pre-saved diff (one path per line). Bypasses the git invocation. A relative '
            'path is resolved against the plan directory first and the cwd second; a '
            'supplied path that resolves to nothing is an error, never an empty diff.'
        ),
    )
    run_parser.add_argument(
        '--base-ref',
        default=None,
        help='Git base ref for the diff (e.g. origin/main). Required when --diff-file is absent.',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
