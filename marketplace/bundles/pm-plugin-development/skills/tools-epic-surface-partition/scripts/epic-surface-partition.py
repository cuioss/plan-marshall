#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Derive an epic's test-tree surface partition from its staged spec corpus.

Registered entry point of the ``tools-epic-surface-partition`` skill. Read-only
throughout: it reads the orchestrator store and the repository tree and writes
nothing.

Subcommands:

- ``classify --epic {slug}`` — parse every spec's ``## Expected Surface`` and
  ``## Out of Scope``, resolve the paths each claims and excludes, and assign
  every spec exactly one of ``declarative`` / ``derived`` / ``prose`` with the
  evidence for that verdict. A spec whose class cannot be determined halts the
  run with the spec named, rather than defaulting to a class.

- ``partition --epic {slug}`` — join that claim model against the real ``test/``
  tree and assign every test module exactly one of ``claimed`` / ``unclaimed`` /
  ``multiply_claimed`` / ``not_derivable``. The last two populations are
  reported per instance, and ``unclaimed`` is never merged with
  ``not_derivable``.

- ``attribution --epic {slug}`` — group the test-module line-budget findings,
  re-derived from the current tree, by owning plan. Modules with no single
  owning plan land in the three explicit ownerless buckets rather than being
  folded into a plan's total.

The derivation is a report, never a build gate: the specs live under a
git-ignored path and are absent from a fresh clone, so no CI check can read
them.
"""

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from _epic_partition import (
    DEFAULT_LINE_BUDGET,
    VERDICT_ORDER,
    derive_attribution,
    derive_budget_findings,
    derive_partition,
    iter_test_modules,
)
from _epic_spec_parser import (
    CLASS_DECLARATIVE,
    CLASS_DERIVED,
    CLASS_PROSE,
    UnclassifiableSpecError,
    classify_corpus,
)
from file_ops import cwd_checkout_root, get_store_dir, output_toon, safe_main

#: The classes reported in the tally, in the order the model states them. Every
#: class carries a row even at zero, so an empty class reads as measured rather
#: than as absent.
_TALLY_ORDER = (CLASS_DECLARATIVE, CLASS_DERIVED, CLASS_PROSE)


class _CorpusError(Exception):
    """A corpus the derivation cannot load; carries the caller's error payload."""

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload.get('error', 'corpus_error'))
        self.payload = payload


def _load_corpus(epic: str) -> tuple[list[Any], Path, Path]:
    """Resolve the epic's spec corpus and classify it.

    Raises:
        _CorpusError: when the slug is invalid, the corpus is absent, or a spec
            cannot be classified — each carrying the caller's error payload.
    """
    try:
        epic_dir = get_store_dir('orchestrator', epic, allow_archived=True)
    except ValueError as error:
        raise _CorpusError(
            {'status': 'error', 'error': 'invalid_epic_slug', 'epic': epic, 'reason': str(error)}
        ) from error

    plans_dir = epic_dir / 'plans'
    if not plans_dir.is_dir():
        raise _CorpusError(
            {
                'status': 'error',
                'error': 'epic_corpus_not_found',
                'epic': epic,
                'plans_dir': str(plans_dir),
            }
        )

    repo_root = Path(cwd_checkout_root())
    try:
        claims = classify_corpus(plans_dir, repo_root)
    except UnclassifiableSpecError as error:
        raise _CorpusError(
            {
                'status': 'error',
                'error': 'unclassifiable_spec',
                'epic': epic,
                'spec': error.spec,
                'reason': error.reason,
            }
        ) from error

    return claims, plans_dir, repo_root


def cmd_classify(args: argparse.Namespace) -> dict[str, Any]:
    """Handle ``classify --epic EPIC``."""
    try:
        claims, plans_dir, repo_root = _load_corpus(args.epic)
    except _CorpusError as error:
        return error.payload

    tally = Counter(claim.spec_class for claim in claims)
    return {
        'status': 'success',
        'epic': args.epic,
        'plans_dir': str(plans_dir),
        'repo_root': str(repo_root),
        'specs_total': len(claims),
        'class_tally': [{'spec_class': name, 'count': tally.get(name, 0)} for name in _TALLY_ORDER],
        'specs': [
            {
                'plan_id': claim.plan_id,
                'spec': claim.spec,
                'spec_class': claim.spec_class,
                'claimed_count': len(claim.claimed),
                'excluded_count': len(claim.excluded),
                'unresolved_count': len(claim.unresolved),
                'evidence': claim.evidence,
            }
            for claim in claims
        ],
        'claimed': [
            {'plan_id': claim.plan_id, 'path': entry.path, 'kind': entry.kind}
            for claim in claims
            for entry in claim.claimed
        ],
        'excluded': [
            {'plan_id': claim.plan_id, 'path': entry.path, 'kind': entry.kind}
            for claim in claims
            for entry in claim.excluded
        ],
        'unresolved': [
            {'plan_id': claim.plan_id, 'raw': raw} for claim in claims for raw in claim.unresolved
        ],
    }


def cmd_partition(args: argparse.Namespace) -> dict[str, Any]:
    """Handle ``partition --epic EPIC``."""
    try:
        claims, plans_dir, repo_root = _load_corpus(args.epic)
    except _CorpusError as error:
        return error.payload

    test_root = repo_root / 'test'
    modules = iter_test_modules(test_root, repo_root)
    partition = derive_partition(claims, modules)
    tally = partition.tally()

    return {
        'status': 'success',
        'epic': args.epic,
        'plans_dir': str(plans_dir),
        'test_root': str(test_root),
        'modules_total': len(modules),
        'verdict_tally': [
            {'verdict': verdict, 'count': tally[verdict]} for verdict in VERDICT_ORDER
        ],
        'root_claims': [
            {'plan_id': root.plan_id, 'path': root.path} for root in partition.root_claims
        ],
        'modules': [
            {
                'path': module.path,
                'verdict': module.verdict,
                'plans': ','.join(module.plans),
            }
            for module in partition.modules
        ],
    }


def cmd_attribution(args: argparse.Namespace) -> dict[str, Any]:
    """Handle ``attribution --epic EPIC``."""
    try:
        claims, plans_dir, repo_root = _load_corpus(args.epic)
    except _CorpusError as error:
        return error.payload

    test_root = repo_root / 'test'
    modules = iter_test_modules(test_root, repo_root)
    partition = derive_partition(claims, modules)
    findings = derive_budget_findings(modules, repo_root, args.budget)
    attribution = derive_attribution(partition, findings, args.budget)

    return {
        'status': 'success',
        'epic': args.epic,
        'plans_dir': str(plans_dir),
        'test_root': str(test_root),
        'budget': attribution.budget,
        'modules_total': len(modules),
        'findings_total': attribution.total_findings(),
        'buckets': [
            {'owner': bucket.owner, 'count': len(bucket.findings)}
            for bucket in attribution.buckets
        ],
        'findings': [
            {'owner': bucket.owner, 'path': finding.path, 'line_count': finding.line_count}
            for bucket in attribution.buckets
            for finding in bucket.findings
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser (the seam ``parse_ns`` resolves against)."""
    parser = argparse.ArgumentParser(
        description="Derive an epic's test-tree surface partition from its staged spec corpus",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    classify = subparsers.add_parser(
        'classify',
        help="Classify every spec's Expected Surface",
        allow_abbrev=False,
    )
    classify.add_argument('--epic', required=True, help='Epic slug naming the orchestrator store entry')
    classify.set_defaults(handler=cmd_classify)

    partition = subparsers.add_parser(
        'partition',
        help='Map every test module to the plan(s) claiming it',
        allow_abbrev=False,
    )
    partition.add_argument(
        '--epic', required=True, help='Epic slug naming the orchestrator store entry'
    )
    partition.set_defaults(handler=cmd_partition)

    attribution = subparsers.add_parser(
        'attribution',
        help='Group test-module line-budget findings by owning plan',
        allow_abbrev=False,
    )
    attribution.add_argument(
        '--epic', required=True, help='Epic slug naming the orchestrator store entry'
    )
    attribution.add_argument(
        '--budget',
        type=int,
        default=DEFAULT_LINE_BUDGET,
        help=f'Test-module line budget (default: {DEFAULT_LINE_BUDGET})',
    )
    attribution.set_defaults(handler=cmd_attribution)

    return parser


@safe_main
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    output_toon(args.handler(args))
    return 0


if __name__ == '__main__':
    main()
