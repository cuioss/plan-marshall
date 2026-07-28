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

Storage: stateless — reads the worktree diff and derives the plan footprint
live from the worktree (``compute-footprint``: ``{base}...HEAD`` ∪ porcelain).
Output: TOON to stdout.

Usage:
    python3 self_review.py surface --plan-id EXAMPLE-PLAN --project-dir /path/to/worktree
"""

import argparse
from pathlib import Path
from typing import Any

from _self_review_detectors import (
    _detect_advertised_form_help_strings,
    _detect_contract_sources,
    _detect_count_prose,
    _detect_description_vs_body,
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
    _find_skill_dir,  # noqa: F401 - re-exported for stable import surface
    _load_test_tree_blob,  # noqa: F401 - re-exported for stable import surface
    _name_in_test_blob,  # noqa: F401 - re-exported for stable import surface
    _symmetric_pair_has_test,  # noqa: F401 - re-exported for stable import surface
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
    """
    registered = {spec.key for spec in CANDIDATE_LISTS}
    if detected.keys() != registered:
        raise ValueError(
            'candidate-list registry drift — detected but not registered: '
            f'{sorted(detected.keys() - registered)}; registered but not '
            f'detected: {sorted(registered - detected.keys())}'
        )

    counts: dict[str, int] = {
        spec.key: len(detected[spec.key]) for spec in CANDIDATE_LISTS
    }
    counts['total'] = sum(
        len(detected[spec.key]) for spec in CANDIDATE_LISTS if spec.in_total
    )

    payload: dict[str, Any] = {'counts': counts}
    payload.update({spec.key: detected[spec.key] for spec in CANDIDATE_LISTS})
    return payload


def _cmd_surface(args: argparse.Namespace) -> int:
    plan_id = require_valid_plan_id(args)

    # Routing: when --project-dir is supplied, use it verbatim (escape hatch).
    # When omitted, auto-resolve via manage-status get-worktree-path. Both
    # paths are funneled through resolve_project_dir so the two-state
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

    diff_text = _diff_hunks(project_dir, base_branch)
    added = _iter_added_lines(diff_text)

    if modified_files:
        allowed = set(modified_files)
        added = [(p, ln, c) for (p, ln, c) in added if p in allowed]

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
    if modified_files:
        allowed = set(modified_files)
        changed_pairs = [pr for pr in changed_pairs if pr[0] in allowed]
    touched_claims = _detect_touched_claims(changed_pairs)
    advertised_form_help_strings = _detect_advertised_form_help_strings(
        added, project_dir
    )
    ordinal_references = _detect_ordinal_references(added, project_dir)
    scan_derived_keys = _detect_scan_derived_keys(added, project_dir)

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
    }

    output = {
        'status': 'success',
        'plan_id': plan_id,
        'project_dir': str(project_dir),
        'base_branch': base_branch,
        **_compose_candidate_output(detected),
    }
    output_toon(output)
    return 0


# =============================================================================
# CLI
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Surface candidate lists for pre-submission self-review.',
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_surface = sub.add_parser(
        'surface',
        help=(
            f'Emit {len(CANDIDATE_LISTS)} candidate lists '
            f'({candidate_list_prose()}) from the worktree diff as TOON.'
        ),
        allow_abbrev=False,
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
        '--contract-radius',
        type=int,
        default=3,
        help='Directory levels to walk up when collecting schema-bearing markdown files (default: 3).',
    )
    p_surface.set_defaults(func=_cmd_surface)
    return parser


@safe_main
def main() -> int:
    parser = _build_parser()
    args = parse_args_with_toon_errors(parser)
    return int(args.func(args))


if __name__ == '__main__':
    main()
