#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-check the per-plan execution manifest against the plan's realized footprint.

Reads ``execution.toon`` (produced by ``plan-marshall:manage-execution-manifest``)
plus the matching ``decision.log`` entries, then evaluates each manifest
assumption against the footprint resolved through the SHARED whole-chain resolver
(``_footprint_resolver.resolve_footprint``). Emits one finding per violated
assumption in the same fragment shape as ``check-artifact-consistency.py``.

⛔ **The footprint is NOT a private ``git diff {base}...HEAD`` taken here.** This
aspect runs at finalize ``order: 995``, after ``default:branch-cleanup`` has merged,
so that range spanned nothing on every real run: it succeeded, returned no path, and
rule M4 concluded "no implementation file changed" for plans that had shipped a real
footprint. Routing through the shared chain adopts the post-merge tiers the sibling
footprint consumers already use, which is also what makes this aspect a legitimate
member of ``retro_sections.FOOTPRINT_CONSUMING_ASPECTS``: when no tier resolves it
now publishes the ``inconclusive`` degradation verdict rather than a confident zero.

Two evidence sources feed the rules, and they are distinct: the footprint above, and
the ``affected_files_exact_match`` comparison ``check-artifact-consistency`` FORWARDS
to this aspect (``forwarded_to_manifest``). Rule M6 is that forward's receiver — the
flag previously had none, so the downgraded upstream finding was dropped rather than
re-routed. (M5 is the manifest-version rule; see ``standards/manifest-crosscheck.md``
for the numbering, which this script does not renumber.)

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
from _footprint_resolver import (
    RESOLVING_TIERS,
    coerce_pr_number,
    footprint_resolved,
    load_references_dict,
    read_captured_footprint,
    read_legacy_footprint,
    read_split_shard_shas,
    resolve_diff_file_path,
    resolve_footprint,
)
from _references_core import resolve_live_worktree
from _step_key_canonical import canonicalize_step_key
from file_ops import base_path, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
)
from toon_parser import ToonParseError, parse_toon

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


#: Evidence tiers whose footprint resolves POST-MERGE — the merge-commit and
#: PR-landing tiers of the shared footprint chain (``_footprint_resolver`` tiers
#: 3-4, consulted in that order). A diff taken over one of these bases names
#: the changes a landing commit introduced, not the live worktree delta the
#: plan's own ``base...HEAD`` range would have shown pre-merge, so verdicts
#: graded over it carry the tier caveat below rather than reading as live-diff
#: verdicts. The tier NAMES are the chain's own (:data:`RESOLVING_TIERS`
#: members), restated here as the post-merge subset the caveat applies to.
POST_MERGE_EVIDENCE_TIERS: tuple[str, ...] = ('merge_commit', 'pr_landing')


def footprint_evidence_caveat(tier: str | None, base_ref: str | None) -> str | None:
    """Return the evidence-tier caveat for a post-merge footprint, else ``None``.

    The caveat names the resolving tier and the base ref it diffed, so a
    verdict graded over post-merge evidence states its evidence tier instead
    of reading as a live-diff verdict. Live tiers (``live_diff``,
    ``realized_capture``, ``legacy_key``) and caller-supplied evidence
    (``diff_file``) need no caveat: the former are the plan's own delta, the
    latter's provenance the caller already states. Written for reuse by
    ``check-outline-vs-shipped`` verdicts, which resolve through the same
    chain and must state the same tier.
    """
    if tier not in POST_MERGE_EVIDENCE_TIERS:
        return None
    return (
        f'evidence tier: {tier} (post-merge footprint resolved over base-ref '
        f'{base_ref or "unknown"} — verdicts graded over landing-commit evidence, '
        f'not the live worktree delta)'
    )


def resolve_diff_evidence_tier(
    plan_dir: Path, diff_file: str | None, base_ref: str | None, plan_id: str | None
) -> tuple[str | None, str | None]:
    """Determine which tier of the shared chain supplied this run's footprint.

    The order below is :data:`_footprint_resolver.RESOLVING_TIERS` verbatim —
    ``live_diff`` FIRST, then capture, merge-commit, PR-landing, legacy key —
    because :func:`_footprint_resolver.resolve_footprint` is now what answers,
    and a tier label taken in a different order names a tier that did not
    supply the diff. The previous order put ``live_diff`` LAST, which was
    correct while this script ran its own ``git diff`` and consulted the
    recorded keys only as a fallback; under the shared chain it would report
    ``realized_capture`` for a footprint the live worktree actually produced.

    Each tier is probed through the RESOLVER'S OWN reader rather than a local
    re-read of the same key, so "did this tier answer?" is decided by the same
    predicate the chain applies. That distinction is load-bearing for a
    present-but-EMPTY key: ``realized_footprint: []`` is a resolved,
    genuinely-empty footprint that the chain accepts and stops at, while the
    previous truthiness test (``isinstance(v, list) and v``) skipped past it and
    attributed the answer to a lower tier.

    An explicit ``--diff-file`` is caller-supplied evidence outside the chain
    entirely and reports the ``diff_file`` tier. When no tier answers the tier
    is unknown (``None, None``) — the footprint-degradation state, never a
    guessed label.
    """
    if diff_file is not None:
        return 'diff_file', diff_file
    if resolve_live_worktree(plan_id) is not None:
        # Tier 1 answered — and it answers whether the diff succeeded or the
        # chain reported the sentinel, because a tier-1 failure does NOT fall
        # through to a lower tier (see _footprint_resolver's module docstring).
        return 'live_diff', base_ref or 'worktree'
    refs = load_references_dict(plan_dir)
    if read_captured_footprint(refs) is not None:
        return 'realized_capture', 'realized_footprint'
    shard_shas = read_split_shard_shas(refs)
    if shard_shas is not None:
        return 'merge_commit', f'merge_commit_shas[{len(shard_shas)}]'
    merge_sha = refs.get('merge_commit_sha')
    if isinstance(merge_sha, str) and merge_sha.strip():
        return 'merge_commit', merge_sha.strip()
    pr_number = coerce_pr_number(refs.get('pr_number'))
    if pr_number is not None:
        return 'pr_landing', str(pr_number)
    if read_legacy_footprint(refs) is not None:
        return 'legacy_key', 'modified_files'
    return None, None


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
    diff_file: str | None,
    plan_dir: Path,
    plan_id: str | None,
    evidence_tier: str | None,
    evidence_base_ref: str | None,
) -> tuple[list[str], str, bool]:
    """Return ``(file_paths, base_label, evidence_available)``.

    ``evidence_available`` says whether the rules received a footprint
    observation AT ALL, and it is threaded out of here rather than inferred
    downstream from an empty file list — because an empty list has two
    incompatible causes. A footprint that RESOLVED to no path is a measured
    result (the run really did change nothing, and a rule may pass on it); a
    footprint no tier could resolve is an ABSENCE OF EVIDENCE (no rule may pass
    on it). Inferring from ``len(files) == 0`` collapses the two, which is the
    could-not-look-versus-nothing-to-look-at conflation this script exists to
    report on and must not commit itself.

    When ``--diff-file`` is provided, read it directly. A RELATIVE argument is
    resolved against the plan directory first and the cwd second
    (:func:`resolve_diff_file_path`), so the plan-relative form the capture pattern
    documents resolves to the same file an absolute path names — and a
    supplied-but-unresolvable path raises rather than degrading to an empty diff.

    ⛔ **Without ``--diff-file`` the footprint comes from the SHARED whole-chain
    resolver (:func:`_footprint_resolver.resolve_footprint`), never from a private
    ``git diff {base}...HEAD`` here.** The module docstring owns why that private
    range was structurally empty on every real run.
    """
    if diff_file is not None:
        # `is not None`, never truthiness: `--diff-file ""` is SUPPLIED input and
        # must take the supplied path (where it raises) rather than the resolver path.
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

    footprint = resolve_footprint(plan_dir, plan_id)
    if not footprint_resolved(footprint):
        # Read through the named predicate, never by testing emptiness: the
        # sentinel and a resolved-empty set are different answers.
        return [], 'unresolved', False
    label = evidence_base_ref or evidence_tier or 'resolver'
    return sorted(footprint), label, True


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
    (a project-local skill root is routed exactly that way on some targets), and
    wherever it did, the filter discarded production
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
        # Seeded FAIL-CLOSED and overwritten by the caller, which owns the
        # loader's evidence signal. ``False`` is the only safe seed: this filter
        # never observes a diff, so it cannot know one was available, and a
        # ``True`` seed makes a caller that forgets the assignment publish
        # "evidence existed" on no evidence at all — the exact
        # could-not-look-versus-nothing-to-look-at conflation the surrounding
        # code exists to prevent. Seeded ``False``, a forgotten assignment
        # withholds every clean verdict instead of granting one.
        'diff_available': False,
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
    raw_files_total: int,
    evidence_available: bool,
) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Rule M4: branch-cleanup present in phase_6 → some implementation file changed.

    The rule reports ``inconclusive`` on ``evidence_available is False``, and
    is skipped only when branch-cleanup is absent from ``phase_6.steps``.
    ``evidence_available`` is the loader's own answer to "did a diff observation reach the
    rules AT ALL" (:func:`load_diff_files`), so the rule no longer re-derives an
    input condition it was handed. It must not be re-derived from
    ``raw_files_total == 0``, because an empty file list has two incompatible
    causes: a SUPPLIED diff naming nothing is a resolved empty footprint the rule
    can and must evaluate, while an absent or failed observation is an absence of
    evidence no rule may verdict on. Collapsing the two produced a skip message
    that was false about its own inputs — "no diff data available" emitted two
    lines from a ``diff_available: True`` field contradicting it.

    ``base_label`` is deliberately not a parameter: ``"unresolved"`` is precisely the
    label the loader pairs with ``evidence_available=False``, so testing it here
    would only restate the flag.

    ⛔ **The failing state is "no implementation file changed", and the message
    must name which of its two causes produced it.** This rule is the only
    diff-fed one that fails on the EMPTINESS of the filtered set rather than on a
    culprit present within it, and with evidence in hand that emptiness has two
    distinguishable origins, each with its own wording:

    - ``raw_files_total == 0`` — the observation itself named no path. The
      footprint is a RESOLVED empty one (a supplied diff file naming nothing, or a
      git diff that ran and returned nothing), so the message says the observed
      diff was empty. It may say so only here, where the loader's flag has already
      established that a diff really was observed.
    - ``raw_files_total > 0`` — every supplied entry was filtered away, so the
      filter is what produced the emptiness and the message names the reduction
      instead. Saying "the diff is empty" in this branch would state the opposite
      of what was observed.

    The verdict itself is substantiated in both branches — every drop category
    (``runtime_state`` / ``report`` / ``config``) is a POSITIVE classification, so
    an empty survivor set means every supplied path was positively identified as
    non-implementation.

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

    if not evidence_available:
        # The footprint-DEGRADATION branch. It is reported as
        # ``inconclusive`` rather than ``skip`` because the two say different
        # things: a skip means the rule did not apply, while this rule DID apply
        # and could not be evaluated for want of a resolvable footprint. It is
        # also the branch that must never fall through to the
        # ``raw_files_total == 0`` wording below — that wording asserts the
        # footprint resolved to no path, which is precisely what did not happen
        # here.
        message = (
            'rule M4 inconclusive — the plan footprint could not be resolved from any '
            f'tier of the shared chain ({", ".join(RESOLVING_TIERS)}), so whether an '
            'implementation file changed is UNMEASURABLE, not "no implementation file changed"'
        )
        return _make_check('branch_cleanup_changes', STATUS_INCONCLUSIVE, message), _make_finding(
            'warning', 'branch_cleanup_footprint_unresolved', message
        )

    if filtered_files:
        return _make_check(
            'branch_cleanup_changes', 'pass', f'branch-cleanup paired with {len(filtered_files)} changed file(s)'
        ), None

    if raw_files_total == 0:
        # A diff WAS observed and named no path — a resolved empty footprint, not
        # an absence of evidence. Only this branch may describe the diff itself as
        # empty; see the two-cause note in the docstring.
        message = (
            'phase_6.steps includes branch-cleanup but the observed diff is empty — '
            'the footprint resolved to no changed path at all, so no implementation '
            'file changed'
        )
    else:
        # A non-empty raw diff whose every entry the filter dropped, so this count
        # is always non-zero.
        dropped_total = raw_files_total - len(filtered_files)
        message = (
            'phase_6.steps includes branch-cleanup but no implementation file changed — '
            f'all {dropped_total} diff entries classified as bookkeeping '
            '(plan state, the plan report, or a build-config route)'
        )
    finding = _make_finding('info', 'branch_cleanup_without_changes', message)
    return _make_check('branch_cleanup_changes', 'fail', finding['message']), finding


def load_forwarded_set_comparison(plan_dir: Path) -> dict[str, Any] | None:
    """Return the upstream ``affected_files_exact_match`` block, or ``None``.

    ``None`` means the block could NOT be read — the fragment is absent, it did not
    parse, or it carries no such block. That is a could-not-look, and rule M6 reports
    it as one instead of grading two empty sets it never received. An empty
    ``outline_only`` / ``references_only`` inside a block that WAS read is the
    opposite answer: a measured agreement.
    """
    # The upstream ``artifact-consistency`` producer writes its fragment here, per
    # that aspect's Persistence contract.
    path = plan_dir / 'work' / 'fragment-artifact-consistency.toon'
    if not path.is_file():
        return None
    try:
        parsed = parse_toon(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, ToonParseError):
        return None
    if not isinstance(parsed, dict):
        return None
    block = parsed.get('affected_files_exact_match')
    return block if isinstance(block, dict) else None


def _as_path_list(value: Any) -> list[str]:
    """Coerce a fragment set field to a list of non-empty path strings."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(entry).strip() for entry in value if str(entry).strip()]


def evaluate_declared_vs_realized_set(
    comparison: dict[str, Any] | None,
) -> tuple[dict[str, str], dict[str, Any] | None]:
    """Rule M6: RECEIVE the set comparison ``check-artifact-consistency`` forwards.

    That producer downgrades its ``affected_files_exact_match`` ``warn`` to ``info``
    whenever an ``execution.toon`` is present, sets ``forwarded_to_manifest: true``,
    and tells the reader the drift is handled by this aspect. Nothing here read that
    flag, so the finding was not re-routed — it was DROPPED. A forward with no
    receiver is a finding lost on every manifest-bearing plan, which is worse than
    the duplicate reporting the downgrade was introduced to avoid.

    The two sets are graded at DIFFERENT severities because they mean different
    things. ``outline_only`` — declared with a modification intent, absent from the
    realized footprint — is a declaration the run did not honour, graded ``warning``.
    ``references_only`` — realized but never declared — is ordinary discovery on most
    plans, graded ``info``.

    ⛔ Both counts are published beside the verdict, and so is the size of the
    population they were taken over, because a zero from this rule is exactly the
    kind that needs attribution: ``0 outline_only`` from a comparison that ran and
    ``0 outline_only`` from a fragment that was never read are indistinguishable
    otherwise. An unread fragment therefore reports :data:`STATUS_INCONCLUSIVE` and
    no counts at all, rather than two zeros.
    """
    if comparison is None:
        return _make_check(
            'declared_vs_realized_set',
            STATUS_INCONCLUSIVE,
            'rule M6 inconclusive — the artifact-consistency fragment carrying '
            'affected_files_exact_match could not be read, so the declared-vs-realized '
            'comparison was never received; this is an unread input, not an agreeing pair of sets',
        ), None

    outline_only = _as_path_list(comparison.get('outline_only'))
    references_only = _as_path_list(comparison.get('references_only'))
    forwarded = comparison.get('forwarded_to_manifest') is True
    upstream_status = str(comparison.get('status') or 'unknown')
    population = (
        f'received from check-artifact-consistency (upstream status {upstream_status}, '
        f'forwarded_to_manifest={str(forwarded).lower()}); compared '
        f'{len(outline_only)} outline_only and {len(references_only)} references_only path(s)'
    )

    if not outline_only and not references_only:
        return _make_check(
            'declared_vs_realized_set',
            'pass',
            f'declared modification-intent set and realized footprint agree — {population}',
        ), None

    severity = 'warning' if outline_only else 'info'
    culprits = sorted(set(outline_only) | set(references_only))
    message = (
        f'declared-vs-realized set mismatch — {len(outline_only)} declared-but-unrealized '
        f'and {len(references_only)} realized-but-undeclared path(s); {population}'
    )
    finding = _make_finding(severity, 'declared_vs_realized_set_mismatch', message, culprits)
    return _make_check('declared_vs_realized_set', 'fail', message), finding


# =============================================================================
# Input-reduction reporting (D2)
# =============================================================================

#: The check status a diff-fed rule takes when it would otherwise emit a bare
#: clean pass over a majority-discarded footprint. Distinct from ``skip`` (the
#: rule did not apply) and from ``pass`` (the rule applied and was satisfied):
#: ``indeterminate`` says the rule applied but saw too little of the supplied
#: input for its verdict to mean anything.
STATUS_INDETERMINATE = 'indeterminate'

#: The check status a diff-fed rule takes when the plan footprint could not be
#: resolved from ANY tier of the shared chain — the footprint-DEGRADATION verdict.
#:
#: ⛔ It is deliberately NOT :data:`STATUS_INDETERMINATE`, and the two must not be
#: merged. ``inconclusive`` is this producer's honest-degradation TOKEN: it is a
#: member of :data:`retro_sections.FOOTPRINT_DEGRADED_TOKENS`, and
#: ``compile-report._declares_degraded`` matches it by EQUALITY against a verdict
#: field (``status`` / ``comparison``) — so emitting it under a check's ``status``
#: is what lets the plan-level footprint-derivation aggregate count this aspect as
#: degraded. ``indeterminate`` is not in that vocabulary and would read as
#: RESOLVED, leaving the aggregate one member short of firing on exactly the run
#: where every footprint consumer went unmeasurable together. The two statuses also
#: mean different things: ``indeterminate`` is "the footprint resolved and the
#: filter left too little of it", ``inconclusive`` is "no footprint resolved at
#: all".
STATUS_INCONCLUSIVE = 'inconclusive'

#: The aspect-level footprint-resolution states published beside the checks, so a
#: reader gets the degradation verdict without reassembling it from check rows.
FOOTPRINT_RESOLVED = 'resolved'

#: The ONE dispatch registry for the diff-fed rules: check name → evaluator.
#:
#: ⛔ The evaluation loop reads THIS map directly, so a rule added here is
#: automatically evaluated. The reduction report and the ``indeterminate``
#: downgrade read the derived :data:`_FOOTPRINT_FED_CHECKS` instead — the full
#: membership here minus ``declared_vs_realized_set`` (see that data's docstring
#: for why it is excluded) — so a rule added here is automatically subject to
#: those two EXCEPT for that one deliberate exclusion. A hardcoded name set
#: mirroring the dispatch table is the defect this whole change exists to remove
#: — a private list restating a set defined authoritatively elsewhere — and an
#: evaluator missing from that mirror would silently bypass D2's guarantee,
#: emitting a bare clean pass over a majority-discarded footprint. That is
#: precisely the failure the reduction report was written to prevent, so it must
#: not be reachable through the report's own membership test.
#:
#: ``evaluate_branch_cleanup`` and ``evaluate_declared_vs_realized_set`` are both
#: dispatched separately (see :data:`_SEPARATELY_DISPATCHED_CHECKS`) — the former
#: needs the diff-availability signal, the latter the forwarded upstream
#: comparison — which is why membership lives in this map rather than being
#: inferred from the evaluation loop alone.
#: ``manifest_version_recognized`` is deliberately absent: it reads the manifest
#: body alone, so no amount of diff filtering affects its verdict.
_DIFF_FED_RULES: dict[str, str] = {
    'docs_only_diff': 'evaluate_docs_only',
    'early_terminate_diff': 'evaluate_early_terminate',
    'tests_only_diff': 'evaluate_tests_only',
    'branch_cleanup_changes': 'evaluate_branch_cleanup',
    'declared_vs_realized_set': 'evaluate_declared_vs_realized_set',
}

#: Derived, never restated — see :data:`_DIFF_FED_RULES`.
_DIFF_FED_CHECKS = frozenset(_DIFF_FED_RULES)

#: The subset of :data:`_DIFF_FED_CHECKS` whose evidence channel is THIS script's
#: own footprint (the ``{base}...HEAD`` diff the shared resolving chain answers).
#: ``declared_vs_realized_set`` is excluded: its evidence is the forwarded upstream
#: ``affected_files_exact_match`` fragment (see :func:`load_forwarded_set_comparison`)
#: and it already owns its own could-not-look path (a ``None`` comparison degrades
#: to ``inconclusive`` on its own). Subjecting it to THIS script's footprint
#: degradation/reduction annotation conflates two unrelated evidence channels — a
#: received-and-agreeing verdict would read as withheld whenever this script's own
#: footprint (not the fragment) is unresolvable, which is exactly the post-merge
#: worktree-removed case the rule is most needed on. Used only by
#: :func:`_withhold_on_absent_evidence` and :func:`apply_input_reduction`;
#: :data:`_DIFF_FED_CHECKS` itself is unchanged and stays the full registry-derived
#: membership its own tests read.
_FOOTPRINT_FED_CHECKS: frozenset[str] = _DIFF_FED_CHECKS - {'declared_vs_realized_set'}

#: The diff-fed rules dispatched OUTSIDE the shared loop, because each takes an
#: input the shared ``(manifest, filtered_files)`` signature does not carry:
#: ``branch_cleanup_changes`` takes the footprint-availability signal, and
#: ``declared_vs_realized_set`` takes the forwarded upstream comparison. Naming them
#: here — and deriving the loop's evaluator tuple by SUBTRACTING this set from
#: :data:`_DIFF_FED_RULES` — is what keeps the registry the single membership source:
#: ``branch_cleanup_changes`` rides the reduction report and the downgrade
#: machinery via :data:`_FOOTPRINT_FED_CHECKS`; ``declared_vs_realized_set`` is
#: deliberately excluded from that machinery and owns its own could-not-look
#: path instead (see :data:`_FOOTPRINT_FED_CHECKS` for why).
_SEPARATELY_DISPATCHED_CHECKS: frozenset[str] = frozenset({'branch_cleanup_changes', 'declared_vs_realized_set'})


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
    STATUS_INCONCLUSIVE: 'inconclusive',
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
    """Degrade every footprint-fed clean ``pass`` when NO footprint tier resolved.

    "Footprint-fed" is :data:`_FOOTPRINT_FED_CHECKS`, not the full
    :data:`_DIFF_FED_CHECKS` registry: ``declared_vs_realized_set`` (Rule M6) is
    diff-fed for loop-derivation purposes but its evidence is the forwarded
    upstream fragment, not this script's footprint, so it is excluded here.

    Reached only when :func:`load_diff_files` reported the shared chain's
    unresolvable sentinel, so the rules ran against an empty footprint for want of
    any resolvable evidence rather than because the run changed nothing. A ``pass``
    there reads identically to a substantiated one downstream.

    The status is :data:`STATUS_INCONCLUSIVE`, this producer's footprint-DEGRADATION
    token, not :data:`STATUS_INDETERMINATE` — see that constant for why the
    distinction is load-bearing for the plan-level aggregate.

    A ``fail`` is untouched — a rule that found a violation without footprint
    evidence found it in the manifest body. A ``skip`` is untouched for the usual
    reason.
    """
    out: list[dict[str, str]] = []
    for check in checks:
        if check['name'] not in _FOOTPRINT_FED_CHECKS or check['status'] != 'pass':
            out.append(check)
            continue
        updated = dict(check)
        updated['status'] = STATUS_INCONCLUSIVE
        updated['message'] = (
            f'{check["message"]} — VERDICT WITHHELD: the plan footprint could not be '
            f'resolved from any tier of the shared chain ({", ".join(RESOLVING_TIERS)}), '
            'so the rule evaluated an empty footprint rather than an empty change'
        )
        out.append(updated)
    return out


def apply_input_reduction(checks: list[dict[str, str]], reduction: dict[str, Any]) -> list[dict[str, str]]:
    """Annotate — and where required downgrade — every footprint-fed check.

    "Footprint-fed" is :data:`_FOOTPRINT_FED_CHECKS`, not the full
    :data:`_DIFF_FED_CHECKS` registry — see :data:`_FOOTPRINT_FED_CHECKS` for why
    ``declared_vs_realized_set`` (Rule M6) is excluded.

    Three obligations, all discharged here so no rule evaluator can forget one:

    - **Every** footprint-fed check that ran against a reduced input set has the
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
      existed at all** takes :data:`STATUS_INCONCLUSIVE`. This is the
      zero-evidence sibling of the case above and the filtering logic cannot see
      it: nothing was discarded, so the reduction is empty, yet the rule evaluated
      an empty footprint and said ``all 0 entries are docs-shaped``. A verdict over
      no evidence is not a clean result; ``_withhold_on_absent_evidence`` already
      refuses it for ``evaluate_branch_cleanup`` (:data:`STATUS_INCONCLUSIVE`, never
      :data:`STATUS_INDETERMINATE` — the two must not be merged); this extends the
      same refusal to the rest.

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
        The checks, with footprint-fed entries annotated and possibly downgraded.
    """
    dropped = reduction['dropped']
    diff_available = reduction['diff_available']
    if not dropped and diff_available:
        return checks

    if not diff_available:
        return _withhold_on_absent_evidence(checks)

    note = f'{dropped} of {reduction["supplied"]} supplied paths were filtered as bookkeeping before evaluation'
    if not reduction['oracle_available']:
        note += (
            ' (build_map oracle unavailable — no path could be classified BY THE ORACLE; '
            'the categories decided without it still applied)'
        )

    annotated: list[dict[str, str]] = []
    for check in checks:
        if check['name'] not in _FOOTPRINT_FED_CHECKS or check['status'] == 'skip':
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
    # Evidence tier behind this run's footprint: post-merge tiers attach the caveat
    # naming the tier and base ref, so verdicts graded over landing-commit
    # evidence state their evidence tier rather than reading as live-diff
    # verdicts. Resolved in the shared chain's OWN tier order, so the label names
    # the tier that actually supplied the footprint.
    live_plan_id = args.plan_id if args.mode == 'live' else None
    evidence_tier, evidence_base_ref = resolve_diff_evidence_tier(plan_dir, args.diff_file, args.base_ref, live_plan_id)
    evidence_caveat = footprint_evidence_caveat(evidence_tier, evidence_base_ref)
    raw_files, base_label, evidence_available = load_diff_files(
        args.diff_file, plan_dir, live_plan_id, evidence_tier, evidence_base_ref
    )
    # The forwarded set comparison rule M6 receives. Loaded here so the payload can
    # publish whether it was readable at all beside the rule's own verdict.
    forwarded_comparison = load_forwarded_set_comparison(plan_dir)
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
    # entry except the members of _SEPARATELY_DISPATCHED_CHECKS, in registry order.
    diff_evaluators: tuple[
        Callable[[dict[str, Any], list[str]], tuple[dict[str, str], dict[str, Any] | None]],
        ...,
    ] = tuple(
        globals()[symbol] for name, symbol in _DIFF_FED_RULES.items() if name not in _SEPARATELY_DISPATCHED_CHECKS
    )
    for evaluator in diff_evaluators:
        check, finding = evaluator(manifest, kept_files)
        checks.append(check)
        if finding is not None:
            findings.append(finding)

    # evaluate_branch_cleanup takes the loader's evidence signal itself, so it can
    # report the footprint-degradation verdict (instead of false-positive failing)
    # when no tier resolved, and can still EVALUATE a resolved-empty footprint.
    cleanup_check, cleanup_finding = evaluate_branch_cleanup(manifest, kept_files, len(raw_files), evidence_available)
    checks.append(cleanup_check)
    if cleanup_finding is not None:
        findings.append(cleanup_finding)

    # Rule M6 takes the forwarded upstream comparison, which no other rule reads.
    set_check, set_finding = evaluate_declared_vs_realized_set(forwarded_comparison)
    checks.append(set_check)
    if set_finding is not None:
        findings.append(set_finding)

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
        # The aspect-level footprint verdict, published so a reader gets the
        # degradation state without reassembling it from check rows. ``status`` is
        # the DEGRADATION token on the unresolved path (see STATUS_INCONCLUSIVE) —
        # which is also what makes this aspect legible to the plan-level
        # footprint-derivation aggregate as a FOOTPRINT_CONSUMING_ASPECTS member.
        'footprint_resolution': {
            'status': FOOTPRINT_RESOLVED if evidence_available else STATUS_INCONCLUSIVE,
            'tier': evidence_tier or 'unresolved',
            'base': base_label,
            'chain': list(RESOLVING_TIERS),
            'caveat': evidence_caveat or '',
        },
        # The received half of the forward contract: whether the upstream comparison
        # was readable at all, and the sizes of the two sets it carried. Published
        # even on the unread path — as an explicit ``received: false`` with no
        # counts — so a zero here is never mistaken for a measured agreement.
        'declared_vs_realized': (
            {
                'received': True,
                'upstream_status': str(forwarded_comparison.get('status') or 'unknown'),
                'forwarded_to_manifest': forwarded_comparison.get('forwarded_to_manifest') is True,
                'outline_only_count': len(_as_path_list(forwarded_comparison.get('outline_only'))),
                'references_only_count': len(_as_path_list(forwarded_comparison.get('references_only'))),
            }
            if forwarded_comparison is not None
            else {
                'received': False,
                'reason': (
                    'the artifact-consistency fragment carrying affected_files_exact_match '
                    'could not be read, so no set sizes were measured'
                ),
            }
        ),
        'diff': {
            'base': base_label,
            'evidence_tier': evidence_tier or 'unresolved',
            'evidence_caveat': evidence_caveat or '',
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
        description="Cross-check execution manifest against the plan's realized footprint",
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
        help=(
            'Base ref LABEL reported beside a live-diff footprint (e.g. origin/main). It no '
            'longer selects the diff: without --diff-file the footprint comes from the shared '
            'whole-chain resolver, which derives its own base ref for the live-diff tier.'
        ),
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
