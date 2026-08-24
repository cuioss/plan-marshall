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

The derivation is a report, never a build gate: the specs live under a
git-ignored path and are absent from a fresh clone, so no CI check can read
them.
"""

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

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


def cmd_classify(args: argparse.Namespace) -> dict[str, Any]:
    """Handle ``classify --epic EPIC``."""
    try:
        epic_dir = get_store_dir('orchestrator', args.epic, allow_archived=True)
    except ValueError as error:
        return {
            'status': 'error',
            'error': 'invalid_epic_slug',
            'epic': args.epic,
            'reason': str(error),
        }

    plans_dir = epic_dir / 'plans'
    if not plans_dir.is_dir():
        return {
            'status': 'error',
            'error': 'epic_corpus_not_found',
            'epic': args.epic,
            'plans_dir': str(plans_dir),
        }

    repo_root = Path(cwd_checkout_root())
    try:
        claims = classify_corpus(plans_dir, repo_root)
    except UnclassifiableSpecError as error:
        return {
            'status': 'error',
            'error': 'unclassifiable_spec',
            'epic': args.epic,
            'spec': error.spec,
            'reason': error.reason,
        }

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

    return parser


@safe_main
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    output_toon(args.handler(args))
    return 0


if __name__ == '__main__':
    main()
