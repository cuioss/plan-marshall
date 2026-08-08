#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic candidate surfacing for the pre-submission-self-review finalize step.

Reads the worktree's diff against the base branch, scans added lines in modified
files, and emits one candidate list per entry of the ``CANDIDATE_LISTS`` registry
in ``_self_review_patterns`` as TOON for the LLM cognitive review pass to consume.
That registry is the single code-side source of truth for the emitted key set,
the ``counts.total`` formula, and the ``surface`` help prose — this docstring
deliberately does not mirror the vocabulary. The contract prose lives in
``plan-marshall:extension-api/standards/ext-point-self-review-surfacing.md``.

The sibling ``scan-worked-examples`` verb runs the worked-example-vs-clause
adjudication (candidate list ``worked_example_pairs``) over a SUPPLIED file
population instead of the diff, and reports the population size the verdict was
drawn against — so a zero-contradiction result is distinguishable from a
zero-population one.

``surface`` accepts an optional ``--since-ref``, which narrows the surfaced file
set to the footprint intersected with the paths changed since a previous round's
recorded HEAD. Only the file set narrows — hunks are still computed against the
base branch, so a surviving file is always reviewed against its full plan diff.

Storage: stateless — reads the worktree diff and derives the plan footprint
live from the worktree (``compute-footprint``: ``{base}...HEAD`` ∪ porcelain).
Output: TOON to stdout.

Usage:
    python3 self_review.py surface --plan-id EXAMPLE-PLAN --project-dir /path/to/worktree
    python3 self_review.py surface --plan-id EXAMPLE-PLAN --since-ref abc1234
    python3 self_review.py scan-worked-examples --plan-id EXAMPLE-PLAN \\
        --paths-glob 'marketplace/bundles/*/skills/*/standards/*.md'
"""

import argparse
import subprocess
import textwrap
from pathlib import Path
from typing import Any

from _references_core import (
    compute_plan_branch_diff,
)
from _self_review_detectors import (
    _detect_advertised_form_help_strings,
    _detect_contract_sources,
    _detect_count_prose,
    _detect_description_vs_body,
    _detect_discard_without_report,
    _detect_duplicate_claimable_keys,
    _detect_flag_guard_pairs,
    _detect_keep_markers,
    _detect_markdown_sections,
    _detect_ordinal_references,
    _detect_producer_consumer,
    _detect_regexes,
    _detect_same_document_consistency,
    _detect_scan_derived_keys,
    _detect_source_of_truth,
    _detect_symmetric_pairs,
    _detect_touched_claims,
    _detect_unguarded_boundaries,
    _detect_user_facing_strings,
    _detect_worked_example_pairs,
    _find_skill_dir,  # noqa: F401 - re-exported for stable import surface
    _load_test_tree_blob,  # noqa: F401 - re-exported for stable import surface
    _name_in_test_blob,  # noqa: F401 - re-exported for stable import surface
    _symmetric_pair_has_test,  # noqa: F401 - re-exported for stable import surface
    _worked_example_pairs,
)
from _self_review_diff import (
    _diff_hunks,
    _iter_added_lines,
    _iter_changed_line_pairs,
    _resolve_footprint,
    _run_git,
    _truncate,  # noqa: F401 - re-exported for stable import surface
    _verify_base_branch,
)
from _self_review_patterns import (
    CANDIDATE_FAMILIES,
    CANDIDATE_LISTS,
    candidate_list_prose,
)
from file_ops import (
    output_toon,
    output_toon_error,
    safe_main,
)
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
    require_valid_plan_id,
)
from resolve_project_dir import (
    WorktreeResolutionError,
    emit_worktree_error,
    resolve_project_dir,
)

# =============================================================================
# Subcommand: surface
# =============================================================================


def _compose_candidate_output(detected: dict[str, list]) -> dict[str, Any]:
    """Derive the counts block and the candidate payload from ``CANDIDATE_LISTS``.

    ``detected`` maps every registry key to that list's detector output. Both the
    per-list counts, the ``total`` sum (over the registry's ``in_total`` entries),
    and the emitted payload key set are derived here, so a candidate list cannot
    reach the output without also appearing in the derived count.

    The two key sets MUST match exactly. A registry entry with no detector result
    would emit a key with no payload; a detector result with no registry entry
    would be silently dropped from BOTH the payload and the count — the same
    mirror-drift this registry exists to remove. Either direction raises.

    Which lists feed ``total`` is the registry's ``in_total`` field; the rationale
    is owned by
    ``plan-marshall:extension-api/standards/ext-point-self-review-surfacing.md``
    § Output Schema.

    ``counts.by_family`` partitions that SAME ``in_total`` population by each
    entry's registry ``family``, so the per-family figures sum exactly to
    ``total`` and the mix cannot drift from the total it decomposes.
    """
    registered = {spec.key for spec in CANDIDATE_LISTS}
    if detected.keys() != registered:
        raise ValueError(
            'candidate-list registry drift — detected but not registered: '
            f'{sorted(detected.keys() - registered)}; registered but not '
            f'detected: {sorted(registered - detected.keys())}'
        )

    counts: dict[str, Any] = {
        spec.key: len(detected[spec.key]) for spec in CANDIDATE_LISTS
    }
    counts['total'] = sum(
        len(detected[spec.key]) for spec in CANDIDATE_LISTS if spec.in_total
    )

    # ``by_family`` is derived from the SAME registry and the SAME ``in_total``
    # population as ``total``, so the family counts sum EXACTLY to ``total``.
    # Deriving both from one traversal is what keeps the mix from drifting from
    # the total for the same structural reason the total cannot drift from the
    # emitted key set. Every declared family is seeded to zero first, so a round
    # in which one family surfaced nothing REPORTS a zero rather than omitting
    # the key — an all-prose round must be legible as a detector-mix signal, and
    # a missing key would read as "not measured" instead of "none found".
    by_family: dict[str, int] = dict.fromkeys(CANDIDATE_FAMILIES, 0)
    for spec in CANDIDATE_LISTS:
        if spec.in_total:
            by_family[spec.family] += len(detected[spec.key])
    counts['by_family'] = by_family

    payload: dict[str, Any] = {'counts': counts}
    payload.update({spec.key: detected[spec.key] for spec in CANDIDATE_LISTS})
    return payload


def _resolve_since_delta(project_dir: Path, since_ref: str) -> set[str] | None:
    """Return the repo-relative paths changed since ``since_ref``, or ``None``.

    ``since_ref`` is the previous review round's recorded ``head_at_completion``.
    The delta is the union of the name-only diff between that ref and ``HEAD``
    (what landed in commits after the previous round closed) and the porcelain
    working-tree state (what this round's loop-back fixes changed but have not
    committed yet — the same reason ``_diff_hunks`` targets the working tree).

    The union is computed by ``compute_plan_branch_diff``, the declared single
    source of truth for "diff name set ∪ porcelain state", which this module
    reuses rather than re-implementing. Its diff leg is the three-dot
    ``{since_ref}...HEAD`` form, which is EQUIVALENT to the two-dot form here:
    ``since_ref`` is a previously recorded ``HEAD`` of this same branch and is
    therefore always an ancestor of the current ``HEAD``, so the merge-base the
    three-dot form anchors on IS ``since_ref``. An absorb merge from the base
    branch does not disturb that — it only adds descendants — so the two forms
    cannot diverge for any ref this argument accepts.

    Returns ``None`` when ``since_ref`` does not resolve to a commit inside the
    worktree, or when git fails while computing the delta. The caller MUST treat
    ``None`` as a diagnosable error and refuse: silently falling through to the
    full sweep would turn an unresolvable anchor into an unrecorded full round,
    which is exactly the ambiguity the anchor exists to remove.
    """
    rc, _, _ = _run_git(project_dir, 'rev-parse', '--verify', f'{since_ref}^{{commit}}')
    if rc != 0:
        return None
    try:
        return compute_plan_branch_diff(project_dir, since_ref)
    except subprocess.CalledProcessError:
        return None


def _cmd_surface(args: argparse.Namespace) -> int:
    plan_id = require_valid_plan_id(args)

    # Routing: when --project-dir is supplied, use it verbatim (escape hatch).
    # When omitted, auto-resolve through the single plan-context resolver
    # (resolve_project_dir delegates to file_ops.resolve_plan_context, which
    # owns the manage-status get-worktree-path channel). Both paths are funneled
    # through resolve_project_dir so the two-state
    # contract is enforced consistently — note that self_review legitimately
    # needs --plan-id for modified-files lookup as well, so an explicit
    # --project-dir alongside is allowed here only as a tie-break (the
    # helper would normally reject the pair via MutuallyExclusiveArgsError;
    # we resolve manually instead).
    if args.project_dir is not None:
        project_dir = Path(args.project_dir).resolve()
    else:
        try:
            resolved = resolve_project_dir(plan_id, None, default=None)
        except WorktreeResolutionError as exc:
            output_toon(emit_worktree_error(plan_id, exc))
            return 2
        project_dir = Path(resolved).resolve()
    base_branch = args.base_branch or 'main'

    if not project_dir.is_dir():
        output_toon_error(
            'project_dir_invalid',
            f'project-dir does not exist or is not a directory: {project_dir}',
        )
        return 1

    rc_check, _, stderr_check = _run_git(project_dir, 'rev-parse', '--git-dir')
    if rc_check != 0:
        output_toon_error(
            'git_unavailable',
            f'git -C {project_dir} rev-parse failed: {stderr_check.strip()}',
        )
        return 1

    if not _verify_base_branch(project_dir, base_branch):
        output_toon_error(
            'base_branch_not_found',
            f'base branch {base_branch!r} does not resolve inside {project_dir}',
        )
        return 1

    modified_files = _resolve_footprint(project_dir, base_branch)

    # The allow-set is tri-state on purpose. ``None`` means "do not filter" (the
    # footprint was unresolvable), while an EMPTY set means "filter to nothing" —
    # a delta round whose intersection is empty has genuinely nothing to review
    # and MUST surface nothing. Collapsing the two into a truthiness test would
    # make an empty delta surface the entire diff, inverting the scoping.
    allow_set: set[str] | None = set(modified_files) if modified_files else None

    since_ref = args.since_ref
    if since_ref is not None:
        delta = _resolve_since_delta(project_dir, since_ref)
        if delta is None:
            output_toon_error(
                'since_ref_unresolvable',
                f'--since-ref {since_ref!r} does not resolve to a commit inside '
                f'{project_dir}, so the delta surface cannot be computed. The '
                'round is refused rather than silently widened to a full sweep.',
            )
            return 1
        allow_set = delta if allow_set is None else (allow_set & delta)
        modified_files = sorted(allow_set)

    diff_text = _diff_hunks(project_dir, base_branch)
    added = _iter_added_lines(diff_text)

    if allow_set is not None:
        added = [(p, ln, c) for (p, ln, c) in added if p in allow_set]

    regexes = _detect_regexes(added)
    user_facing = _detect_user_facing_strings(added)
    md_sections = _detect_markdown_sections(added, project_dir)
    sym_pairs = _detect_symmetric_pairs(added, project_dir)
    flag_guard_pairs = _detect_flag_guard_pairs(added)
    contract_sources, schema_bearing = _detect_contract_sources(
        modified_files, project_dir, args.contract_radius, added
    )
    keep_markers, protected_identifiers = _detect_keep_markers(added, project_dir)
    producer_consumer = _detect_producer_consumer(added)
    source_of_truth = _detect_source_of_truth(added)
    same_document = _detect_same_document_consistency(added)
    description_vs_body = _detect_description_vs_body(added, project_dir)
    unguarded_boundaries = _detect_unguarded_boundaries(added, project_dir)
    count_prose = _detect_count_prose(modified_files, project_dir)
    changed_pairs = _iter_changed_line_pairs(diff_text)
    if allow_set is not None:
        changed_pairs = [pr for pr in changed_pairs if pr[0] in allow_set]
    touched_claims = _detect_touched_claims(changed_pairs)
    advertised_form_help_strings = _detect_advertised_form_help_strings(
        added, project_dir
    )
    ordinal_references = _detect_ordinal_references(added, project_dir)
    scan_derived_keys = _detect_scan_derived_keys(added, project_dir)
    worked_example_pairs = _detect_worked_example_pairs(added, project_dir)
    duplicate_claimable_keys = _detect_duplicate_claimable_keys(added, project_dir)
    discard_without_report = _detect_discard_without_report(added, project_dir)

    detected: dict[str, list] = {
        'regexes': regexes,
        'user_facing_strings': user_facing,
        'markdown_sections': md_sections,
        'symmetric_pairs': sym_pairs,
        'flag_guard_pairs': flag_guard_pairs,
        'contract_sources': contract_sources,
        'schema_bearing_files': schema_bearing,
        'keep_markers': keep_markers,
        'protected_identifiers': protected_identifiers,
        'producer_consumer': producer_consumer,
        'source_of_truth': source_of_truth,
        'same_document_consistency': same_document,
        'description_vs_body': description_vs_body,
        'unguarded_boundaries': unguarded_boundaries,
        'count_prose': count_prose,
        'touched_claims': touched_claims,
        'advertised_form_help_strings': advertised_form_help_strings,
        'ordinal_references': ordinal_references,
        'scan_derived_keys': scan_derived_keys,
        'worked_example_pairs': worked_example_pairs,
        'duplicate_claimable_keys': duplicate_claimable_keys,
        'discard_without_report': discard_without_report,
    }

    output = {
        'status': 'success',
        'plan_id': plan_id,
        'project_dir': str(project_dir),
        'base_branch': base_branch,
        'since_ref': since_ref or '',
        'surface_scope': 'delta' if since_ref is not None else 'full',
        'files_in_scope': len(modified_files),
        **_compose_candidate_output(detected),
    }
    output_toon(output)
    return 0


# =============================================================================
# Subcommand: scan-worked-examples
# =============================================================================


def _resolve_scan_project_dir(plan_id: str, project_dir_arg: str | None) -> Path | None:
    """Resolve the working tree for a population scan, or emit the error TOON.

    Mirrors ``_cmd_surface``'s two-state routing: an explicit ``--project-dir``
    is used verbatim (escape hatch), otherwise the path is auto-resolved from
    ``--plan-id`` through the single plan-context resolver. Returns ``None`` when
    the resolution failed and the caller must exit non-zero — the error TOON has
    already been emitted.
    """
    if project_dir_arg is not None:
        return Path(project_dir_arg).resolve()
    try:
        resolved = resolve_project_dir(plan_id, None, default=None)
    except WorktreeResolutionError as exc:
        output_toon(emit_worktree_error(plan_id, exc))
        return None
    return Path(resolved).resolve()


def _collect_glob_population(project_dir: Path, paths_glob: str) -> list[Path]:
    """Return the deduplicated, sorted file set matching ``paths_glob``.

    The glob is resolved relative to ``project_dir``; every match is required to
    stay inside it, so a pattern that escapes the working tree contributes
    nothing. Deduplication is on the RESOLVED path, which is what makes the
    reported denominator a count of distinct files rather than of match rows.
    """
    seen: set[Path] = set()
    for match in project_dir.glob(paths_glob):
        if not match.is_file():
            continue
        resolved = match.resolve()
        try:
            resolved.relative_to(project_dir)
        except ValueError:
            continue
        seen.add(resolved)
    return sorted(seen)


def _cmd_scan_worked_examples(args: argparse.Namespace) -> int:
    plan_id = require_valid_plan_id(args)

    project_dir = _resolve_scan_project_dir(plan_id, args.project_dir)
    if project_dir is None:
        return 2
    if not project_dir.is_dir():
        output_toon_error(
            'project_dir_invalid',
            f'project-dir does not exist or is not a directory: {project_dir}',
        )
        return 1

    paths_glob = args.paths_glob
    if paths_glob.startswith('/') or '..' in Path(paths_glob).parts:
        output_toon_error(
            'paths_glob_invalid',
            'paths-glob must be a relative pattern with no parent-directory '
            f'segments: {paths_glob!r}',
        )
        return 1

    population = _collect_glob_population(project_dir, paths_glob)

    records: list[dict[str, Any]] = []
    pair_bearing_files = 0
    unreadable = 0
    for path in population:
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            unreadable += 1
            continue
        rel = str(path.relative_to(project_dir))
        found = _worked_example_pairs(rel, text.splitlines(), None)
        if found:
            pair_bearing_files += 1
            records.extend(found)

    contradicting = [r for r in records if r['agrees'] is False]
    agreeing = [r for r in records if r['agrees'] is True]
    unadjudicated = [r for r in records if r['agrees'] is None]

    output: dict[str, Any] = {
        'status': 'success',
        'plan_id': plan_id,
        'project_dir': str(project_dir),
        'paths_glob': paths_glob,
        'boundary': (
            f'files matching {paths_glob} under {project_dir}, deduplicated by '
            'resolved path, filtered to those carrying a GOOD/BAD worked-example pair'
        ),
        'population': {
            'distinct_paths': len(population),
            'unreadable_paths': unreadable,
            'pair_bearing_files': pair_bearing_files,
            'pairs_total': len(records),
            'pairs_agreeing': len(agreeing),
            'pairs_unadjudicated': len(unadjudicated),
            'pairs_contradicting': len(contradicting),
        },
        'worked_example_pairs': contradicting,
    }
    if args.include_unadjudicated:
        output['unadjudicated_pairs'] = unadjudicated
    output_toon(output)
    return 0


# =============================================================================
# CLI
# =============================================================================


class _TermPreservingHelpFormatter(argparse.HelpFormatter):
    """Wrap help text without splitting a term across a line break.

    The candidate-list labels the ``surface`` help enumerates are hyphenated
    terms of art derived from ``CANDIDATE_LISTS`` (``same-document normative
    directives``, ``near-identical-hunk touched claims``). ``textwrap``'s
    defaults break on hyphens and inside over-long words, which renders a label
    that no reader — and no derivation check — can match verbatim against the
    registry. Both break modes are disabled so a label always reaches the
    rendered help intact; an over-long term simply overflows its column.
    """

    def _split_lines(self, text: str, width: int) -> list[str]:
        collapsed = self._whitespace_matcher.sub(' ', text).strip()
        return textwrap.wrap(
            collapsed, width, break_on_hyphens=False, break_long_words=False
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Surface candidate lists for pre-submission self-review.',
        allow_abbrev=False,
        formatter_class=_TermPreservingHelpFormatter,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_surface = sub.add_parser(
        'surface',
        help=(
            f'Emit {len(CANDIDATE_LISTS)} candidate lists '
            f'({candidate_list_prose()}) from the worktree diff as TOON.'
        ),
        allow_abbrev=False,
        formatter_class=_TermPreservingHelpFormatter,
    )
    add_plan_id_arg(p_surface)
    p_surface.add_argument(
        '--project-dir',
        required=False,
        default=None,
        help=(
            'Absolute path to the active git worktree (Bucket B). Optional — '
            'when omitted, the worktree path is auto-resolved from --plan-id '
            'via manage-status get-worktree-path. Supplying both is allowed '
            'here because --plan-id also drives modified-files lookup; the '
            'mutual-exclusivity check applies only to routing.'
        ),
    )
    p_surface.add_argument(
        '--base-branch',
        default='main',
        help='Base branch for diff computation (default: main).',
    )
    p_surface.add_argument(
        '--since-ref',
        required=False,
        default=None,
        help=(
            "Previous review round's recorded head_at_completion SHA. When "
            'supplied, the surfaced file set is narrowed to the footprint '
            'intersected with the paths changed since that ref, so a follow-up '
            'round re-examines only what the preceding loop-back actually '
            'changed. Hunks are still computed against --base-branch, so every '
            'surviving file is reviewed against its FULL plan diff — this '
            'narrows which files are reviewed, never how deeply one is. Omit it '
            'for round 1 and for the closing full-surface confirmation sweep. A '
            'ref that does not resolve is refused, never widened to a full sweep.'
        ),
    )
    p_surface.add_argument(
        '--contract-radius',
        type=int,
        default=3,
        help='Directory levels to walk up when collecting schema-bearing markdown files (default: 3).',
    )
    p_surface.set_defaults(func=_cmd_surface)

    p_scan = sub.add_parser(
        'scan-worked-examples',
        help=(
            'Adjudicate every GOOD/BAD worked-example pair in a supplied file '
            'population (not the diff) and report the contradicting ones '
            'alongside the population size they were drawn from.'
        ),
        allow_abbrev=False,
        formatter_class=_TermPreservingHelpFormatter,
    )
    add_plan_id_arg(p_scan)
    p_scan.add_argument(
        '--project-dir',
        required=False,
        default=None,
        help=(
            'Absolute path to the active git worktree (Bucket B). Optional — '
            'when omitted, the worktree path is auto-resolved from --plan-id '
            'via manage-status get-worktree-path.'
        ),
    )
    p_scan.add_argument(
        '--paths-glob',
        required=True,
        help=(
            'Relative glob selecting the file population, resolved against the '
            'working tree (e.g. marketplace/bundles/*/skills/*/standards/*.md). '
            'Echoed back as the boundary the reported counts were drawn against.'
        ),
    )
    p_scan.add_argument(
        '--include-unadjudicated',
        action='store_true',
        help=(
            'Also emit the unadjudicated_pairs list (pairs whose clause names no '
            'normative predicate, or whose GOOD example branches on nothing '
            'recoverable). Off by default: the population block always reports '
            'their count.'
        ),
    )
    p_scan.set_defaults(func=_cmd_scan_worked_examples)
    return parser


@safe_main
def main() -> int:
    parser = _build_parser()
    args = parse_args_with_toon_errors(parser)
    return int(args.func(args))


if __name__ == '__main__':
    main()
