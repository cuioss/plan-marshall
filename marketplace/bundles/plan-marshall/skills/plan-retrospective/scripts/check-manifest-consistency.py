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
    is_test_path,
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

# Canonical-verify step-id prefix (Rule M3). On the marshal.json compose path —
# the one every real plan takes — the composer emits each built-in verify step as
# ``default:verify:{canonical}`` and boundary-normalizes it to the bare
# ``verify:{canonical}`` form; ``DEFAULT_PHASE_5_STEPS`` is itself
# ``('verify:quality-gate', 'verify:module-tests')``. Comparing verification_steps
# against an unprefixed name is what made M3 unreachable there.
#
# The bare ``{canonical}`` form is NOT impossible, so this is a normalization and
# not a rewrite: the ``--phase-5-steps`` CSV fallback (callers without a
# marshal.json, notably tests) passes its argument through verbatim, and archived
# manifests predating the canonical-verify step id carry bare names too. Both forms
# are accepted; see :func:`normalize_verification_step`.
_CANONICAL_VERIFY_PREFIX = 'verify:'

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


def load_diff_files(
    diff_file: str | None, base_ref: str | None, plan_dir: Path
) -> tuple[list[str], str, bool]:
    """Return ``(file_paths, base_label, evidence_available)``.

    ``evidence_available`` says whether the rules received a diff observation AT
    ALL, and it is threaded out of here rather than inferred downstream from an
    empty file list — because an empty list has two incompatible causes. A supplied
    diff file naming nothing is a RESOLVED empty footprint (the run really did
    change nothing, and a rule may pass on it); no diff input, or a git invocation
    that failed, is an ABSENCE OF EVIDENCE (no rule may pass on it). Inferring from
    `len(files) == 0` collapses the two, which is the same
    could-not-look-versus-nothing-to-look-at conflation this script is being fixed
    for.

    When ``--diff-file`` is provided, read it directly. A RELATIVE argument is
    resolved against the plan directory first and the cwd second
    (:func:`resolve_diff_file_path`), so the plan-relative form the capture pattern
    documents resolves to the same file an absolute path names — and a
    supplied-but-unresolvable path raises rather than degrading to an empty diff.

    Without ``--diff-file``, invoke ``git diff {base}...HEAD --name-only`` and treat
    any failure as "no diff available" rather than aborting — the manifest
    cross-check is a best-effort retrospective signal, not a build-blocking gate.
    """
    if diff_file is not None:
        # `is not None`, never truthiness: `--diff-file ""` is SUPPLIED input and
        # must take the supplied path (where it raises) rather than the git path.
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
        return _split_diff_lines(raw), f'file:{path.name}', True

    if not base_ref:
        return [], 'unknown', False

    try:
        result = subprocess.run(
            ['git', 'diff', f'{base_ref}...HEAD', '--name-only'],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return [], base_ref, False
    if result.returncode != 0:
        return [], base_ref, False
    return _split_diff_lines(result.stdout), base_ref, True


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

    This replaces a private prefix tuple that declared a project-local dotfile tree
    to be bookkeeping. A build extension may route such a tree as ``production``
    (on the Claude target the project-local skill root ``.claude/skills/*.py`` is
    routed exactly that way), and wherever it did, the filter discarded production
    source as bookkeeping and every downstream rule evaluated the remainder.

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
        # Filled in by the caller, which owns the base-label signal.
        'diff_available': True,
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

    The marshal.json compose path emits the ``verify:``-prefixed form, so a rule
    comparing against an unprefixed name without this normalization cannot fire on
    a manifest composed that way. The bare form is still accepted: the
    ``--phase-5-steps`` CSV fallback forwards its argument verbatim, and archived
    manifests carry bare names.
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
    (:func:`normalize_verification_step`), because the marshal.json compose path
    emits every built-in verify step as ``verify:{canonical}``. Comparing the raw
    list against a bare ``['module-tests']`` made this rule unreachable on every
    manifest composed that way.
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
    """Rule M4: branch-cleanup present in phase_6 → some implementation file changed.

    The rule is skipped when no diff data is available — ``base_label`` is
    ``"unknown"`` or the raw diff is empty (``raw_files_total == 0``). In those
    cases the absence of changes is an artefact of missing diff input, not a
    real defect, so emitting a fail would be a false positive. This mirrors the
    skip-on-missing-data behaviour of the other diff evaluators
    (``evaluate_docs_only``, ``evaluate_early_terminate``, etc.).

    ⛔ **The failing state is "no implementation file changed", NOT "the diff is
    empty", and the two are different.** This rule is the only diff-fed one that
    fails on the EMPTINESS of the filtered set rather than on a culprit present
    within it, so the filter is what produces that emptiness: reaching the fail
    branch requires a non-empty raw diff (guarded above) whose every entry the
    filter dropped. Saying "the diff is empty" there states something the
    ``raw_files_total`` guard has already ruled out. The verdict itself is
    substantiated — every drop category (``runtime_state`` / ``report`` /
    ``config``) is a POSITIVE classification, so an empty survivor set means every
    supplied path was positively identified as non-implementation — but the message
    must name the reduction that produced it.

    ⚠ It must not go further and infer that there was nothing to push. Every drop
    category can contain tracked files that really did change on the branch — a
    ``report`` or ``config`` entry plainly, and ``runtime_state`` too, since
    ``.plan/`` is only partly git-ignored (``marshal.json`` and the
    ``project-architecture/**`` descriptors are tracked). The finding says what it
    knows — no IMPLEMENTATION file changed — and names the categories, rather than
    concluding anything about the push.
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

    # Reachable only with raw_files_total > 0 and an empty survivor set, so the
    # whole raw diff was filtered and this count is always non-zero.
    dropped_total = raw_files_total - len(filtered_files)
    finding = _make_finding(
        'info',
        'branch_cleanup_without_changes',
        'phase_6.steps includes branch-cleanup but no implementation file changed — '
        f'all {dropped_total} diff entries classified as bookkeeping '
        '(plan state, the plan report, or a build-config route)',
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

#: The ONE dispatch registry for the diff-fed rules: check name → evaluator.
#:
#: ⛔ Both the evaluation loop and the reduction report read THIS map, so a rule
#: added here is automatically evaluated AND automatically subject to the reduction
#: report and the ``indeterminate`` downgrade. A hardcoded name set mirroring the
#: dispatch table is the defect this whole change exists to remove — a private list
#: restating a set defined authoritatively elsewhere — and an evaluator missing from
#: that mirror would silently bypass D2's guarantee, emitting a bare clean pass over
#: a majority-discarded footprint. That is precisely the failure the reduction
#: report was written to prevent, so it must not be reachable through the report's
#: own membership test.
#:
#: ``evaluate_branch_cleanup`` is dispatched separately (it needs the
#: diff-availability signal the others do not take), which is why membership lives
#: in this map rather than being inferred from the evaluation loop alone.
#: ``manifest_version_recognized`` is deliberately absent: it reads the manifest
#: body alone, so no amount of diff filtering affects its verdict.
_DIFF_FED_RULES: dict[str, str] = {
    'docs_only_diff': 'evaluate_docs_only',
    'early_terminate_diff': 'evaluate_early_terminate',
    'tests_only_diff': 'evaluate_tests_only',
    'branch_cleanup_changes': 'evaluate_branch_cleanup',
}

#: Derived, never restated — see :data:`_DIFF_FED_RULES`.
_DIFF_FED_CHECKS = frozenset(_DIFF_FED_RULES)

#: The one diff-fed rule dispatched outside the shared loop, because it takes the
#: diff-availability signal the others do not. Named once so both the loop's
#: exclusion and any reader can refer to the same string.
_BRANCH_CLEANUP_CHECK = 'branch_cleanup_changes'


#: Emitted check status → its ``summary`` bucket name. EVERY status this script
#: emits has a row, including :data:`STATUS_INDETERMINATE`, whose bucket name is the
#: status itself — the map is total over the emitted set rather than a table of
#: exceptions, which is what lets :func:`summarize_checks` report an explicit zero
#: for each so an absent key is never mistaken for a measured zero. A status with no
#: row is still counted, under its own name (see that function).
_STATUS_BUCKETS: dict[str, str] = {
    'pass': 'passed',
    'fail': 'failed',
    'skip': 'skipped',
    STATUS_INDETERMINATE: 'indeterminate',
}


def summarize_checks(checks: list[dict[str, str]]) -> dict[str, int]:
    """Return the per-status counts for ``checks``, total over what was emitted.

    Every known status gets an explicit zero, and an UNKNOWN status is counted under
    its own name rather than dropped, so ``sum(result.values()) == len(checks)``
    holds unconditionally.

    That second half is the point, and it is the sibling
    ``check-artifact-consistency.summarize_checks``'s rule rather than a variation
    on it: a summary that counts only the statuses it knows lets every other verdict
    land in no bucket at all, which reads to a summary consumer as a check that does
    not exist. Silently dropping an unrecognised verdict is exactly the
    absent-reads-as-nothing defect this aspect exists to surface, so it must not be
    reproduced in the aspect's own summary.
    """
    summary = dict.fromkeys(_STATUS_BUCKETS.values(), 0)
    for check in checks:
        bucket = _STATUS_BUCKETS.get(check['status'], check['status'])
        summary[bucket] = summary.get(bucket, 0) + 1
    return summary


def _withhold_on_absent_evidence(checks: list[dict[str, str]]) -> list[dict[str, str]]:
    """Downgrade every diff-fed clean ``pass`` when no diff evidence existed at all.

    ``base_label == 'unknown'`` (no ``--diff-file`` and no ``--base-ref``) or a git
    diff that returned nothing means the rules ran against an empty footprint for
    want of input rather than because the run changed nothing. A ``pass`` there
    reads identically to a substantiated one downstream.

    A ``fail`` is untouched — a rule that found a violation without diff evidence
    found it in the manifest body. A ``skip`` is untouched for the usual reason.
    """
    out: list[dict[str, str]] = []
    for check in checks:
        if check['name'] not in _DIFF_FED_CHECKS or check['status'] != 'pass':
            out.append(check)
            continue
        updated = dict(check)
        updated['status'] = STATUS_INDETERMINATE
        updated['message'] = (
            f'{check["message"]} — VERDICT WITHHELD: no diff evidence was available '
            '(no --diff-file supplied and no usable --base-ref diff), so the rule '
            'evaluated an empty footprint rather than an empty change'
        )
        out.append(updated)
    return out


def apply_input_reduction(checks: list[dict[str, str]], reduction: dict[str, Any]) -> list[dict[str, str]]:
    """Annotate — and where required downgrade — every diff-fed check.

    Three obligations, all discharged here so no rule evaluator can forget one:

    - **Every** diff-fed check that ran against a reduced input set has the
      reduction appended to its message, so the count the rule actually saw is
      visible beside its verdict rather than buried in the ``diff`` block.
    - A check that would otherwise emit a bare clean ``pass`` while the MAJORITY of
      the supplied footprint was discarded becomes
      :data:`STATUS_INDETERMINATE` instead. A clean pass over a small fraction of
      the real input is an unsubstantiated verdict, and it reads in every
      downstream summary exactly like a substantiated one — so a run whose filter
      discarded all but one path could report every rule green while none of them
      had seen the change the plan was about.
    - A check that would emit a bare clean ``pass`` while **no diff evidence
      existed at all** takes :data:`STATUS_INDETERMINATE` too. This is the
      zero-evidence sibling of the case above and the filtering logic cannot see
      it: nothing was discarded, so the reduction is empty, yet the rule evaluated
      an empty footprint and said ``all 0 entries are docs-shaped``. A verdict over
      no evidence is not a clean result, and ``evaluate_branch_cleanup`` already
      refuses it for its own rule (the ``base=unknown or empty diff`` skip); this
      extends the same refusal to the rest.

    A ``fail`` is never downgraded, but the reason differs by rule shape and is
    worth stating precisely, because the obvious blanket rationale — "a reduced
    input can only have hidden more violations" — is true of only one of the two
    shapes:

    - **Rules that fail on a culprit PRESENT in the survivors** (M1 / M2 / M3) draw
      their culprits from the filtered set, so a smaller input yields fewer of
      them: a culprit that survived is real, and filtering can only have concealed
      others.
    - **The rule that fails on the survivors being EMPTY** (M4) is the case that
      rationale does not cover, since the filter is what empties the set. Its
      verdict is substantiated by a different argument — every drop category is a
      positive classification, so an empty survivor set means every supplied path
      was positively identified as non-implementation — and
      :func:`evaluate_branch_cleanup` states that in its own message rather than
      claiming the diff was empty.

    A ``skip`` is never downgraded either — the rule did not apply, which the
    filtering did not decide.

    Args:
        checks: The evaluated checks, mutated copies of which are returned.
        reduction: The block :func:`filter_bookkeeping` produced.

    Returns:
        The checks, with diff-fed entries annotated and possibly downgraded.
    """
    dropped = reduction['dropped']
    diff_available = reduction['diff_available']
    if not dropped and diff_available:
        return checks

    if not diff_available:
        return _withhold_on_absent_evidence(checks)

    note = (
        f'{dropped} of {reduction["supplied"]} supplied paths were filtered as '
        f'bookkeeping before evaluation'
    )
    if not reduction['oracle_available']:
        note += (
            ' (build_map oracle unavailable — no path could be classified BY THE ORACLE; '
            'the categories decided without it still applied)'
        )

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
            'summary': {**summarize_checks([]), 'findings': 0},
        }

    decision_entries = load_decision_log_entries(plan_dir)
    raw_files, base_label, evidence_available = load_diff_files(args.diff_file, args.base_ref, plan_dir)
    kept_files, dropped_files, reduction = filter_bookkeeping(raw_files)
    # Whether a diff observation reached the rules at all. Taken from the loader,
    # never inferred from an empty file list: a SUPPLIED file naming nothing is a
    # resolved empty footprint a rule may pass on, while an absent or failed
    # observation is not.
    reduction['diff_available'] = evidence_available

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

    # Derived from the ONE registry rather than restated: every _DIFF_FED_RULES
    # entry except the separately-dispatched branch-cleanup rule, in registry order.
    diff_evaluators: tuple[
        Callable[[dict[str, Any], list[str]], tuple[dict[str, str], dict[str, Any] | None]],
        ...,
    ] = tuple(
        globals()[symbol]
        for name, symbol in _DIFF_FED_RULES.items()
        if name != _BRANCH_CLEANUP_CHECK
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

    summary = {**summarize_checks(checks), 'findings': len(findings)}

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
            'diff_available': reduction['diff_available'],
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
