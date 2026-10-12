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
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _review_support_attribution import (
    SOLUTION_FILE,
    compute_attribution,
    compute_domains,
    error_payload,
    load_outline_deliverables,
)
from _review_support_validate import (
    FIX_KIND_IMPLEMENTATION,
    KIND_CODE,
    KIND_FUNCTIONAL,
    SEVERITY_BLOCKING,
    VERIFIER_ACCEPTED,
    Grading,
    read_json_object,
    validate_code,
    validate_functional,
    verifier_status,
)
from input_validation import require_valid_plan_id
from toon_parser import serialize_toon

TARGET_EXECUTE = '5-execute'
TARGET_FINALIZE = '6-finalize'
TARGET_NONE = 'none'


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


def run_validate(plan_id: str, kind: str, verdict_file: str, verifier_file: str | None) -> dict[str, Any]:
    """Validate one verdict file and derive grading, loop-back target, ``may_close`` and facts.

    ``may_close`` is true only for a valid verdict with no blocking finding AND
    an ``accepted`` verifier answer; every other outcome reports it false.
    """
    verdict, problem = read_json_object(verdict_file)
    if verdict is None:
        return error_payload(plan_id, 'verdict_file_unreadable', f'{verdict_file}: {problem}')
    grading = Grading()
    if kind == KIND_FUNCTIONAL:
        deliverables = load_outline_deliverables(plan_id)
        if deliverables is None:
            return error_payload(plan_id, 'outline_not_found', f'{SOLUTION_FILE} not found for plan {plan_id!r}')
        facts = validate_functional(verdict, deliverables, grading)
    else:
        facts = validate_code(verdict, grading)

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
    'run_validate',
]
