#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic halves of the two finalize reviews.

``default:functional-review`` and ``default:code-review`` keep the judgement —
reading the change, grading what they find. Everything that is a computation
rather than a judgement lives here, so the two step bodies call one script
instead of re-deriving it in prose:

* ``attribution`` — per outline deliverable, its declared write set plus the
  files the change ledger attributes to it (``attribution_source: ledger |
  declared_only``, with the fallback ``reason``); the realized-footprint files
  no deliverable owns (``unrequested_candidates``); and, with ``--delta-step``,
  only the deliverables a delta round covers (``_review_support_attribution``).
* ``domains`` — the plan's declared domains united with every configured skill
  domain whose ``file_globs`` match the realized footprint, each with its
  ``provenance`` (``declared`` / ``footprint`` / ``both``); ``status: error``
  with ``error: footprint_unresolved`` when the footprint could not be derived.
* ``validate`` — the author's verdict file checked against the schema below,
  with the grading, the loop-back target, the closure decision and the recorded
  fact set derived from it (grading lives in ``_review_support_validate``).
* ``author-verdict`` — seal a verdict with the authorship marker, so a verdict
  edited after the reviewer wrote it no longer matches the recorded output.
* ``open-criteria`` — the frozen Done-when criteria the plan has not yet graded
  ``met`` (the standing finalize triage source, and what the finalize completion
  gate reads).
* ``test-integrity`` — every changed test whose assertions the branch removed or
  filtered (a relaxed assertion that keeps its count stays the author's reading;
  a net-count evasion is still caught, by matching per test function).

The blocking line, the evidence forms, the citation forms and the loop-back
targets are stated once, in ``phase-6-finalize/standards/review-rubric.md``;
``validate`` applies them and restates none of the reasoning.

Every verb emits TOON and exits 0 on every outcome. An input that cannot be
read is ``status: error`` with a named ``error``; a verdict that breaks the
schema is ``status: success`` with ``valid: false``, because that is an answer
about the verdict, not a failure to look at it. A value that could not be
computed is OMITTED, never reported as an empty list or a zero:
``unrequested_candidates`` is absent when the realized footprint could not be
derived, and ``facts``, ``findings`` and ``loop_back_target`` are absent when
the verdict is invalid.

Verdict file schemas (JSON — the rows nest criteria and evidence lists)::

    functional:
      {"deliverables": [{"number": 1,
                         "verdict": "met|met_with_residuals|not_met|superseded",
                         "criteria": [{"criterion": str,
                                       "criterion_id": "C1 (optional; D1.C1 also accepted)",
                                       "status": "met|unevidenced|not_met",
                                       "evidence": [str, ...],
                                       "fix_kind": "implementation|correction"}],
                         "residuals": [{"description": str, "consequential": bool,
                                        "fix_kind": ...}],
                         "superseded_by": str,
                         "fix_kind": ...}],
       "unrequested_changes": [{"path": str, "consequential": bool,
                                "reason": str, "fix_kind": ...}],
       "self_reports": [{"source": str, "claim": str, "holds": bool,
                         "reader_acts_on": bool, "fix_kind": ...}],
       "files_read": [str, ...]}

    code:
      {"findings": [{"rule": {"form": "pack_rule|spine_category|convention|adr",
                              "ref": str},
                     "location": "path:line",
                     "failure_scenario": str,
                     "failure_class": "wrong_result|lost_data|fail_open|broken_contract|none",
                     "fix_kind": ..., "title": str}],
       "domains_reviewed": [str, ...],
       "files_read": [str, ...]}

    verifier:
      {"grading_supported": bool, "may_close": bool, "reason": str}

The verifier is ``accepted`` when it answers ``grading_supported: true`` — on
a round with a blocking finding its ``may_close: false`` is the expected answer,
not a refusal. It is ``declined`` when it answers ``grading_supported: false``,
or ``may_close: false`` on a round without a blocking finding.

``fix_kind`` is required on every item that grades ``blocking`` except a
``not_met`` deliverable and an ``unevidenced`` criterion, which default to
``implementation`` — the gap is missing work unless the author says otherwise.

Usage::

    review_support.py attribution --plan-id P [--delta-step STEP]
    review_support.py domains --plan-id P
    review_support.py validate --plan-id P --kind functional|code \\
        --verdict-file F [--verifier-file V]
    review_support.py author-verdict --plan-id P --kind functional|code --verdict-file F
    review_support.py open-criteria --plan-id P
    review_support.py test-integrity --plan-id P [--base-ref R]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import _review_support_attribution as _attr
from _criteria_snapshot import (
    FUNCTIONAL_VERDICT_FILE,
    criteria_drift,
    criterion_id_parts,
    open_criteria,
    plan_uses_worktree,
    read_snapshot,
    record_verdict_digest,
    snapshot_state,
)
from _review_support_attribution import (
    SOLUTION_FILE,
    compute_attribution,
    compute_domains,
    error_payload,
    load_outline_deliverables,
)
from _review_support_integrity import compute_test_integrity
from _review_support_validate import (
    FIX_KIND_CORRECTION,
    FIX_KIND_IMPLEMENTATION,
    KIND_CODE,
    KIND_FUNCTIONAL,
    SEVERITY_BLOCKING,
    VERIFIER_ACCEPTED,
    Grading,
    authorship_problem,
    deliverable_number,
    grade_frozen_criteria,
    read_json_object,
    report_unmatched_rows,
    seal_verdict,
    validate_code,
    validate_functional,
    verifier_status,
)
from file_ops import atomic_write_file, base_path, cwd_checkout_root
from input_validation import require_valid_plan_id
from toon_parser import serialize_toon

TARGET_EXECUTE = '5-execute'
TARGET_FINALIZE = '6-finalize'
TARGET_NONE = 'none'


def _main_checkout_root() -> Path | None:
    """The main checkout root, or ``None`` when it cannot be resolved."""
    try:
        root = Path(cwd_checkout_root())
    except Exception:
        return None
    return root if root.is_dir() else None


def _evidence_root(plan_id: str) -> Path | None:
    """Resolve the tree a verdict's evidence is checked against, or ``None``.

    A worktree-bound plan is graded against its worktree. A plan that runs WITHOUT
    a worktree (``use_worktree: false``) is graded against the MAIN CHECKOUT — the
    tree the finalize contract assigns it — so its citations are still checked
    rather than read as the not-run state (which is a blocking finding).

    A plan that DECLARED a materialized worktree which does not resolve now is
    different again: falling back to the main checkout would check citations
    against a tree other than the graded head. That case returns ``None``, so the
    not-run finding stands. ``None`` disables the existence check rather than
    reading the absence as a pass.
    """
    try:
        worktree = _attr.resolve_live_worktree(plan_id)
    except Exception:
        worktree = None
    if worktree is not None:
        root: Path | None = Path(worktree)
    elif plan_uses_worktree(plan_id):
        return None
    else:
        root = _main_checkout_root()
    if root is None:
        return None
    return root if root.is_dir() else None


def loop_back_target(findings: list[dict[str, Any]]) -> str:
    """Return the review-rubric.md § 6 target for a graded findings list.

    ``none`` without a blocking finding; ``5-execute`` when any blocking finding
    needs new implementation; ``6-finalize`` when every blocking finding is a
    correction to the diff in hand.
    """
    blocking = [finding for finding in findings if finding['severity'] == SEVERITY_BLOCKING]
    if not blocking:
        return TARGET_NONE
    if any(finding['fix_kind'] == FIX_KIND_IMPLEMENTATION for finding in blocking):
        return TARGET_EXECUTE
    return TARGET_FINALIZE


def _grade_test_integrity(grading: Grading, plan_id: str) -> None:
    """Consume the plan's ``test-integrity`` rows as blocking findings (rubric § 2).

    One finding per changed test whose assertions the branch removed or filtered.
    A failed computation is NOT read as an empty report: when the worktree resolves
    but the base diff cannot be read (``diff_unavailable``), the check did not run,
    so a blocking ``test_integrity_not_run`` finding blocks closure. A missing
    worktree is the same not-run state UNLESS the plan never declared one: a plan
    with ``use_worktree: false`` has no branch diff to grade, while a plan that
    declared a worktree which no longer resolves must not be graded against a tree
    it never used.
    """
    report = compute_test_integrity(plan_id)
    if not isinstance(report, dict):
        return
    if report.get('status') != 'success':
        error = str(report.get('error') or 'unknown')
        non_applicable = error == 'worktree_unresolved' and not plan_uses_worktree(plan_id)
        if not non_applicable:
            grading.add(
                'test_integrity_not_run',
                '-',
                f'the test-integrity check could not run: {error}',
                True,
                FIX_KIND_CORRECTION,
                'test-integrity',
            )
        return
    for row in report.get('findings') or []:
        if not isinstance(row, dict):
            continue
        path = str(row.get('path') or '-')
        detail = str(row.get('detail') or row.get('kind') or 'weakened test')
        grading.add('weakened_test', path, detail, True, FIX_KIND_CORRECTION, f'test-integrity {path}')


def run_validate(plan_id: str, kind: str, verdict_file: str, verifier_file: str | None) -> dict[str, Any]:
    """Validate one verdict file and derive grading, loop-back target, ``may_close`` and facts.

    ``may_close`` is true only for a valid verdict with no blocking finding AND
    an ``accepted`` verifier answer; every other outcome reports it false.

    When the plan carries a criteria snapshot (the criteria-integrity regime) the
    FUNCTIONAL verdict must also match the reviewer's recorded output — a verdict
    the review's own verb did not write, or one edited after it did, is refused —
    and every criterion the frozen snapshot holds that the current outline no
    longer carries verbatim is a blocking finding. The same regime checks that
    each ``met`` criterion's cited paths and test names exist at the graded head.
    The authorship check is functional-only: the code review's findings file is
    not covered by the freeze, and its own document writes and validates it. A
    plan without a snapshot is the legacy shape: there is nothing frozen to
    compare against, so only the verdict's own rules apply.
    """
    verdict, problem = read_json_object(verdict_file)
    if verdict is None:
        return error_payload(plan_id, 'verdict_file_unreadable', f'{verdict_file}: {problem}')
    grading = Grading()
    payload_evidence_check = 'not_run'
    state = snapshot_state(plan_id)
    if state in ('deleted', 'tampered'):
        return error_payload(
            plan_id,
            f'frozen_snapshot_{state}',
            f'the status record froze a criteria snapshot that is now {state}; '
            f'nothing can be graded against a record that is no longer there',
        )
    snapshot = read_snapshot(plan_id)
    if snapshot is not None and kind == KIND_FUNCTIONAL:
        authorship = authorship_problem(verdict, plan_id)
        if authorship:
            grading.errors.append(f'{verdict_file}: {authorship}')
    if kind == KIND_FUNCTIONAL:
        deliverables = load_outline_deliverables(plan_id)
        if deliverables is None:
            return error_payload(plan_id, 'outline_not_found', f'{SOLUTION_FILE} not found for plan {plan_id!r}')
        evidence_root = _evidence_root(plan_id) if snapshot is not None else None
        facts = validate_functional(verdict, deliverables, grading, plan_id, evidence_root)
        if snapshot is not None:
            grade_frozen_criteria(grading, criteria_drift(plan_id, deliverables))
            report_unmatched_rows(grading, verdict, snapshot, deliverables)
            # Prove the citation check ran, or say why it did not: an unrun check
            # that renders identically to a passed one is a green nothing produced.
            if evidence_root is None:
                payload_evidence_check = 'not_run'
                # Rubric § 4: a citation the reviewer cannot evaluate is never
                # silently accepted. The not-run state is a FINDING, not a quiet
                # field a reader may overlook — a verdict graded with no tree to
                # check its citations against cannot be closed on.
                grading.add(
                    'evidence_check_not_run',
                    '-',
                    'the citation-existence check could not run: no tree resolved for the graded head',
                    True,
                    FIX_KIND_IMPLEMENTATION,
                    'evidence check',
                )
            else:
                payload_evidence_check = 'run'
    else:
        facts = validate_code(verdict, grading)
        payload_evidence_check = 'not_run'

    # Consume the plan's own ``test-integrity`` rows: a weakened pre-existing test
    # is a blocking finding (rubric § 2), and before this the rows were produced by
    # a verb no validator read, so a removed assertion blocked nothing unless the
    # author remembered to copy it into prose. One finding per weakened test.
    _grade_test_integrity(grading, plan_id)

    blocking_count = sum(1 for finding in grading.findings if finding['severity'] == SEVERITY_BLOCKING)
    verifier = verifier_status(verifier_file, blocking_count > 0)
    payload: dict[str, Any] = {
        'status': 'success',
        'plan_id': plan_id,
        'kind': kind,
        'valid': grading.valid,
        'verifier': verifier,
        'may_close': False,
        'errors': grading.errors,
        'rewrites': grading.rewrites,
        'evidence_check': payload_evidence_check,
    }
    if kind == KIND_CODE:
        payload['rejected_findings'] = grading.rejected
    if not grading.valid:
        return payload

    facts['blocking_count'] = blocking_count
    facts['advisory_count'] = len(grading.findings) - blocking_count
    payload['may_close'] = blocking_count == 0 and verifier == VERIFIER_ACCEPTED
    payload['loop_back_target'] = loop_back_target(grading.findings)
    payload['findings'] = grading.findings
    payload['facts'] = facts
    return payload


def _unknown_criterion_ids(verdict: dict[str, Any], plan_id: str) -> list[str]:
    """Return every ``criterion_id`` that names no frozen criterion of its deliverable.

    A row may carry an id instead of quoting the criterion verbatim, which is what
    lets a reviewer paraphrase without orphaning the criterion. The id must name a
    criterion that actually exists: a malformed id, a position past the frozen
    list, a deliverable-qualified id naming another deliverable, or any id at all
    on a deliverable the freeze does not carry is refused. A plan with no snapshot
    is the legacy shape — there is no frozen set to name, so nothing is refused.
    """
    snapshot = read_snapshot(plan_id)
    if snapshot is None:
        return []
    frozen: dict[Any, int] = {}
    for row in snapshot.get('deliverables') or []:
        if isinstance(row, dict):
            frozen[deliverable_number(row.get('number'))] = len(row.get('criteria') or [])
    unknown: list[str] = []
    for row in verdict.get('deliverables') or []:
        if not isinstance(row, dict):
            continue
        number = deliverable_number(row.get('number'))
        for criterion in row.get('criteria') or []:
            if not isinstance(criterion, dict):
                continue
            raw = str(criterion.get('criterion_id') or '').strip()
            if not raw:
                continue
            named_deliverable, position = criterion_id_parts(raw)
            known_count = frozen.get(number)
            if (
                known_count is None
                or position is None
                or position < 1
                or position > known_count
                or (named_deliverable is not None and named_deliverable != number)
            ):
                unknown.append(raw)
    return unknown


def run_author_verdict(plan_id: str, kind: str, verdict_file: str) -> dict[str, Any]:
    """Seal a review verdict with the marker only the review's own verb can write.

    The author writes the verdict document, then seals it here. From that point
    the file's content is bound to the reviewer's recorded output: any later edit
    — the ``python3 -c`` rewrite that turned three OpenCode verdicts to "met" —
    no longer matches the recorded digest, and ``validate`` refuses it.

    A functional verdict's ``criterion_id`` values are checked against the frozen
    criteria BEFORE the seal is written. An id the freeze does not carry would
    otherwise seal a row that answers nothing, and the reviewer would have no way
    to tell a typo from a criterion that changed.
    """
    verdict, problem = read_json_object(verdict_file)
    if verdict is None:
        return error_payload(plan_id, 'verdict_file_unreadable', f'{verdict_file}: {problem}')
    if kind == KIND_FUNCTIONAL:
        unknown = _unknown_criterion_ids(verdict, plan_id)
        if unknown:
            return {
                'status': 'error',
                'plan_id': plan_id,
                'kind': kind,
                'verdict_file': verdict_file,
                'error': 'unknown_criterion_id',
                'message': (
                    'each criterion_id must name a frozen criterion of its own deliverable; '
                    f'these name none: {", ".join(unknown)}'
                ),
                'unknown_criterion_ids': unknown,
            }
    sealed = seal_verdict(verdict, kind)
    atomic_write_file(verdict_file, json.dumps(sealed, indent=2, sort_keys=True) + '\n')
    # Bind the seal OUTSIDE the file: the plan's status record holds the digest the
    # checks compare against, so recomputing the in-file digest after an edit does
    # not reproduce it. A plan with no status record keeps the legacy in-file check
    # (the digest is still written into the marker either way).
    record_verdict_digest(plan_id, kind, verdict_file)
    return {
        'status': 'success',
        'plan_id': plan_id,
        'kind': kind,
        'verdict_file': verdict_file,
        'digest': sealed['authored']['digest'],
    }


def run_open_criteria(plan_id: str) -> dict[str, Any]:
    """Return the frozen Done-when criteria the plan has not yet graded ``met``."""
    payload = open_criteria(plan_id, base_path('plans', plan_id, FUNCTIONAL_VERDICT_FILE))
    return {'status': 'success', 'plan_id': plan_id, **payload}


def cmd_attribution(args: argparse.Namespace) -> int:
    """CLI wrapper for ``compute_attribution`` — emits TOON, returns 0."""
    require_valid_plan_id(args)
    print(serialize_toon(compute_attribution(args.plan_id, args.delta_step)))
    return 0


def cmd_domains(args: argparse.Namespace) -> int:
    """CLI wrapper for ``compute_domains`` — emits TOON, returns 0."""
    require_valid_plan_id(args)
    print(serialize_toon(compute_domains(args.plan_id)))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """CLI wrapper for :func:`run_validate` — emits TOON, returns 0."""
    require_valid_plan_id(args)
    print(serialize_toon(run_validate(args.plan_id, args.kind, args.verdict_file, args.verifier_file)))
    return 0


def cmd_author_verdict(args: argparse.Namespace) -> int:
    """CLI wrapper for :func:`run_author_verdict` — emits TOON, returns 0."""
    require_valid_plan_id(args)
    print(serialize_toon(run_author_verdict(args.plan_id, args.kind, args.verdict_file)))
    return 0


def cmd_open_criteria(args: argparse.Namespace) -> int:
    """CLI wrapper for :func:`run_open_criteria` — emits TOON, returns 0."""
    require_valid_plan_id(args)
    print(serialize_toon(run_open_criteria(args.plan_id)))
    return 0


def cmd_test_integrity(args: argparse.Namespace) -> int:
    """CLI wrapper for :func:`compute_test_integrity` — emits TOON, returns 0."""
    require_valid_plan_id(args)
    print(serialize_toon(compute_test_integrity(args.plan_id, args.base_ref)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the parser with the ``attribution``, ``domains`` and ``validate`` verbs."""
    parser = argparse.ArgumentParser(
        description=(
            'Deterministic halves of the functional and code reviews: deliverable '
            'attribution, the reviewed domain set, and verdict validation with the '
            'grading, loop-back target and fact set derived from it.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    attribution = sub.add_parser(
        'attribution',
        help='Per-deliverable declared and ledger-attributed files, plus unrequested-change candidates',
        allow_abbrev=False,
    )
    attribution.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier.')
    attribution.add_argument(
        '--delta-step',
        default=None,
        dest='delta_step',
        help='Finalize step whose recorded completion anchors a delta round (e.g. functional-review).',
    )
    attribution.set_defaults(func=cmd_attribution)

    domains = sub.add_parser(
        'domains',
        help='Declared domains united with footprint-matched skill domains, with provenance',
        allow_abbrev=False,
    )
    domains.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier.')
    domains.set_defaults(func=cmd_domains)

    validate = sub.add_parser(
        'validate',
        help="Validate a review author's verdict file and derive grading, loop-back target and facts",
        allow_abbrev=False,
    )
    validate.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier.')
    validate.add_argument(
        '--kind',
        required=True,
        choices=(KIND_FUNCTIONAL, KIND_CODE),
        help='Which review authored the verdict.',
    )
    validate.add_argument(
        '--verdict-file',
        required=True,
        dest='verdict_file',
        help="Path to the author's JSON verdict file.",
    )
    validate.add_argument(
        '--verifier-file',
        default=None,
        dest='verifier_file',
        help="Path to the verifier's JSON answer; without it the round cannot close.",
    )
    validate.set_defaults(func=cmd_validate)

    author = sub.add_parser(
        'author-verdict',
        help='Seal a review verdict with the authorship marker only this verb writes',
        allow_abbrev=False,
    )
    author.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier.')
    author.add_argument(
        '--kind', required=True, choices=(KIND_FUNCTIONAL, KIND_CODE), help='Which review authored the verdict.'
    )
    author.add_argument(
        '--verdict-file', required=True, dest='verdict_file', help="Path to the author's JSON verdict file."
    )
    author.set_defaults(func=cmd_author_verdict)

    open_criteria_parser = sub.add_parser(
        'open-criteria',
        help='Frozen Done-when criteria the plan has not yet graded met (the standing triage source)',
        allow_abbrev=False,
    )
    open_criteria_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier.')
    open_criteria_parser.set_defaults(func=cmd_open_criteria)

    integrity = sub.add_parser(
        'test-integrity',
        help='Changed tests whose assertions the branch removed or filtered',
        allow_abbrev=False,
    )
    integrity.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier.')
    integrity.add_argument(
        '--base-ref', default=None, dest='base_ref', help='Base ref for the branch diff (default: resolved).'
    )
    integrity.set_defaults(func=cmd_test_integrity)
    return parser


def main() -> int:
    """Parse args and dispatch to the selected verb."""
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'TARGET_EXECUTE',
    'TARGET_FINALIZE',
    'TARGET_NONE',
    'build_parser',
    'loop_back_target',
    'run_author_verdict',
    'run_open_criteria',
    'run_validate',
]
