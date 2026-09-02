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
  tree and assign every test module exactly one verdict. A module claimed by one
  SLICE plan is owned by it however many self-declared SWEEP plans also cross
  it; the crossings are reported beside the verdict as a separate fact. Two or
  more slice plans make the module ``contested`` — the residual, enumerable
  disagreement — and ``unclaimed``, ``swept`` and ``not_derivable`` are each
  reported per instance and never merged.

- ``attribution --epic {slug}`` — group the test-module line-budget findings,
  re-derived from the current tree, by owning plan. Modules with no single
  owning slice land in the explicit ownerless buckets rather than being folded
  into a plan's total.

- ``report --epic {slug}`` — render every section of the derivation: the
  partition, the attribution, the entries awaiting a decision, the contested
  set, the sweep crossings, every spec whose spans the parser could not resolve,
  the injected-failure demonstrations, the declared-test count before and after,
  the baseline drift, and provenance. Each section carries the command that
  produced it, and the rendered set is exactly ``_SECTION_ORDER``.

The derivation is a report, never a build gate: the specs live under a
git-ignored path and are absent from a fresh clone, so no CI check can read
them. ``report`` therefore exits 0 on disagreement — a rendered disagreement is
the product, not a failure.
"""

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from _epic_partition import (
    DEFAULT_LINE_BUDGET,
    VERDICT_CONTESTED,
    VERDICT_NOT_DERIVABLE,
    VERDICT_ORDER,
    VERDICT_UNCLAIMED,
    derive_attribution,
    derive_budget_findings,
    derive_partition,
    derive_sweep_plans,
    iter_test_modules,
)
from epic_spec_parser import (
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
    sweeps = derive_sweep_plans(claims, plans_dir)
    return {
        'status': 'success',
        'epic': args.epic,
        'plans_dir': str(plans_dir),
        'repo_root': str(repo_root),
        'specs_total': len(claims),
        'class_tally': [{'spec_class': name, 'count': tally.get(name, 0)} for name in _TALLY_ORDER],
        'sweep_plans': sorted(sweeps),
        'specs': [
            {
                'plan_id': claim.plan_id,
                'spec': claim.spec,
                'spec_class': claim.spec_class,
                'is_sweep': claim.plan_id in sweeps,
                'claimed_count': len(claim.claimed),
                'excluded_count': len(claim.excluded),
                'unresolved_count': len(claim.unresolved),
                'evidence': claim.evidence,
            }
            for claim in claims
        ],
        'claimed': [
            {
                'plan_id': claim.plan_id,
                'path': entry.path,
                'kind': entry.kind,
                'shape': entry.shape,
            }
            for claim in claims
            for entry in claim.claimed
        ],
        'excluded': [
            {
                'plan_id': claim.plan_id,
                'path': entry.path,
                'kind': entry.kind,
                'shape': entry.shape,
            }
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
    sweeps = derive_sweep_plans(claims, plans_dir)
    partition = derive_partition(claims, modules, sweeps)
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
        'sweep_plans': sorted(sweeps),
        'root_claims': [
            {'plan_id': root.plan_id, 'path': root.path} for root in partition.root_claims
        ],
        'contested': [
            {'path': module.path, 'plans': ','.join(module.plans)}
            for module in partition.with_verdict(VERDICT_CONTESTED)
        ],
        'sweep_crossings': [
            {'path': module.path, 'verdict': module.verdict, 'sweeps': ','.join(module.sweeps)}
            for module in partition.modules
            if module.sweeps
        ],
        'modules': [
            {
                'path': module.path,
                'verdict': module.verdict,
                'plans': ','.join(module.plans),
                'sweeps': ','.join(module.sweeps),
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
    sweeps = derive_sweep_plans(claims, plans_dir)
    partition = derive_partition(claims, modules, sweeps)
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
        'sweep_plans': sorted(sweeps),
        'contested': [
            {'path': module.path, 'plans': ','.join(module.plans)}
            for module in partition.with_verdict(VERDICT_CONTESTED)
        ],
        'sweep_crossings': [
            {'path': module.path, 'verdict': module.verdict, 'sweeps': ','.join(module.sweeps)}
            for module in partition.modules
            if module.sweeps
        ],
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


#: The executor notation every rendered section cites as its producing command.
_NOTATION = 'pm-plugin-development:tools-epic-surface-partition:epic-surface-partition'

#: The module-tests command that produces the injected-failure demonstrations.
#: It does NOT produce the test count: pytest collection counts parametrized
#: instances over one bundle, while the count section is a static declaration
#: count over the whole enumerated tree.
_TESTS_COMMAND = (
    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
    'run --command-args "module-tests pm-plugin-development"'
)

#: The placement the script-architecture standard gave, with its citation. The
#: provenance section renders these so the decision survives as output rather
#: than only as outline prose.
_PLACEMENT_CLAIMS = (
    (
        'test_mirror_location',
        'test/{bundle}/{skill}/',
        'plugin-script-architecture/standards/testing-standards.md',
    ),
    (
        'script_directory_location',
        'marketplace/bundles/{bundle}/skills/{skill}/scripts/',
        'plugin-script-architecture/standards/cross-skill-integration.md; python-implementation.md',
    ),
)

#: The prefix whose claimed entries make the bundle-tree overlap LIVE.
_OVERLAP_PREFIX = 'marketplace/bundles/'

#: The injected-failure demonstrations shipped with the partition, each naming
#: the control that demonstrates it. A checker never observed failing is not a
#: checker, so these are rendered as a first-class report section.
#:
#: The set is COMPLETE — every control group shipped in the demonstrations module
#: appears here. Both directions are pinned in
#: ``test_epic_report_reproducibility.py``: one guard walks this tuple to the
#: tests, the other walks the shipped groups back to this tuple, so neither a
#: removal here nor an addition there can drift the claim unnoticed.
_INJECTED_CONTROLS = (
    (
        'injected_unclaimed_directory',
        'a fixture directory no spec claims is reported by name as unclaimed',
        'test_epic_partition_injected_failures.py::'
        'test_injected_unclaimed_directory_is_reported_by_name',
    ),
    (
        'injected_double_claim',
        'a path added to two slice specs is reported by name as contested',
        'test_epic_partition_injected_failures.py::test_injected_double_claim_is_reported_by_name',
    ),
    (
        'clean_corpus_control',
        'the clean fixture corpus reports neither unclaimed nor contested',
        'test_epic_partition_injected_failures.py::test_clean_corpus_reports_nothing_unclaimed',
    ),
    (
        'injected_root_span',
        'a root span does not mask a module no plan claims',
        'test_epic_partition_injected_failures.py::'
        'test_injected_root_span_does_not_hide_an_unclaimed_module',
    ),
    (
        'injected_container_span',
        'a directory-shaped unresolved span reports not_derivable, never unclaimed',
        'test_epic_partition_injected_failures.py::'
        'test_container_span_marks_the_module_beneath_it_not_derivable',
    ),
)

#: The line prefix that makes a declaration a test. Named once so the counter,
#: the rendered ``method`` field, and the ``--tests-before`` help cannot drift
#: into describing a measurement the counter does not perform.
_TEST_DEF_PREFIX = 'def test_'

#: The one method BOTH test-count figures are measured by. ``--tests-before`` is
#: this same count taken before the campaign, so before and after are comparable.
_TEST_COUNT_METHOD = f'static "{_TEST_DEF_PREFIX}" count over the enumerated test modules'

#: The sections the report renders, in order. This tuple is the SOLE authority
#: for that set: every count claim about it is derived from it at render time, or
#: written count-free, so adding a section here cannot leave a stale number
#: behind. ``disagreements`` is the actionable list — everything awaiting a
#: decision — while ``contested`` and ``swept`` isolate the two populations
#: inside it that are read for different reasons.
_SECTION_ORDER = (
    'partition',
    'attribution',
    'disagreements',
    'contested',
    'swept',
    'not_derivable',
    'injected_controls',
    'test_count',
    'baseline_drift',
    'provenance',
)


def _verb_command(verb: str, epic: str) -> str:
    return f'python3 .plan/execute-script.py {_NOTATION} {verb} --epic {epic}'


def _read_baseline(path: str | None) -> tuple[bool, frozenset[str]]:
    """The recorded baseline finding set, and whether one was supplied at all.

    ⛔ The baseline is a POST-HOC comparison, never an input to the derivation:
    the findings are re-derived from the current tree either way, and the
    baseline only decides what the drift section reports. An absent baseline is
    reported as unsupplied rather than as an empty one, so "no baseline given"
    can never be read as "nothing drifted".
    """
    if path is None:
        return False, frozenset()
    text = Path(path).read_text(encoding='utf-8')
    return True, frozenset(line.strip() for line in text.splitlines() if line.strip())


def _static_test_count(modules: tuple[str, ...], repo_root: Path) -> int:
    """Count declared test functions across the enumerated modules."""
    total = 0
    for module in modules:
        text = (repo_root / module).read_text(encoding='utf-8')
        total += sum(1 for line in text.splitlines() if line.lstrip().startswith(_TEST_DEF_PREFIX))
    return total


def cmd_report(args: argparse.Namespace) -> dict[str, Any]:
    """Handle ``report --epic EPIC`` — render every section in ``_SECTION_ORDER``.

    Report-only by contract: a disagreement is rendered, never raised, and the
    subcommand exits 0 regardless — baseline drift included, which is a
    comparison result and not a failure. The specs are git-ignored and absent
    from a fresh clone, so no CI check could read them and this must never gate
    a build.
    """
    try:
        claims, plans_dir, repo_root = _load_corpus(args.epic)
    except _CorpusError as error:
        return error.payload

    test_root = repo_root / 'test'
    modules = iter_test_modules(test_root, repo_root)
    sweeps = derive_sweep_plans(claims, plans_dir)
    partition = derive_partition(claims, modules, sweeps)
    findings = derive_budget_findings(modules, repo_root, args.budget)
    attribution = derive_attribution(partition, findings, args.budget)
    tally = partition.tally()

    disagreements = [
        module
        for module in partition.modules
        if module.verdict in (VERDICT_UNCLAIMED, VERDICT_CONTESTED)
    ]
    contested = partition.with_verdict(VERDICT_CONTESTED)
    crossings = [module for module in partition.modules if module.sweeps]
    not_derivable = partition.with_verdict(VERDICT_NOT_DERIVABLE)

    baseline_supplied, baseline = _read_baseline(args.baseline_findings)
    observed = frozenset(finding.path for finding in findings)
    drift_added = sorted(observed - baseline) if baseline_supplied else []
    drift_removed = sorted(baseline - observed) if baseline_supplied else []
    unresolvable_specs = [claim for claim in claims if claim.unresolved]
    overlaps = [
        {'plan_id': claim.plan_id, 'path': entry.path}
        for claim in claims
        for entry in claim.claimed
        if entry.path.startswith(_OVERLAP_PREFIX)
    ]

    summaries = {
        'partition': f'{len(modules)} modules across {len(VERDICT_ORDER)} verdicts',
        'attribution': f'{attribution.total_findings()} findings over budget {attribution.budget}',
        'disagreements': f'{len(disagreements)} entries listed per instance',
        'contested': f'{len(contested)} modules claimed by more than one slice plan',
        'swept': (
            f'{len(crossings)} modules crossed by {len(sweeps)} self-declared sweep plan(s)'
        ),
        'not_derivable': f'{len(not_derivable)} modules, {len(unresolvable_specs)} specs',
        'injected_controls': f'{len(_INJECTED_CONTROLS)} demonstrations',
        'test_count': f'before and after, both as a {_TEST_COUNT_METHOD}',
        'baseline_drift': (
            f'{len(drift_added)} added, {len(drift_removed)} removed against a supplied baseline'
            if baseline_supplied
            else 'no baseline supplied; nothing compared'
        ),
        'provenance': (
            f'{len(_PLACEMENT_CLAIMS)} placement claims, {len(overlaps)} overlapping entries'
        ),
    }
    commands = {
        'partition': _verb_command('partition', args.epic),
        'attribution': _verb_command('attribution', args.epic),
        'disagreements': _verb_command('partition', args.epic),
        'contested': _verb_command('partition', args.epic),
        'swept': _verb_command('partition', args.epic),
        # The drift comparison needs BOTH the re-derived findings and the
        # supplied baseline, and ``report`` is the only verb that takes a
        # baseline at all — ``attribution`` re-derives the findings but has
        # nothing to compare them against.
        'baseline_drift': _verb_command('report', args.epic),
        # Both halves, or neither: the modules half comes from ``derive_partition``
        # and the specs half from ``classify_corpus``, and ``report`` is the only
        # verb whose payload carries both. ``classify`` emits no module verdict at
        # all, so it cannot reproduce the "N modules" figure this section renders.
        'not_derivable': _verb_command('report', args.epic),
        'injected_controls': _TESTS_COMMAND,
        # ``report`` is the producer of the static count: no other verb computes
        # ``_static_test_count``, and the module-tests command counts by a
        # different method over a different population.
        'test_count': _verb_command('report', args.epic),
        'provenance': _verb_command('report', args.epic),
    }

    return {
        'status': 'success',
        'epic': args.epic,
        'plans_dir': str(plans_dir),
        'test_root': str(test_root),
        'report_only': True,
        'gates_build': False,
        'sections': [
            {'section': name, 'command': commands[name], 'summary': summaries[name]}
            for name in _SECTION_ORDER
        ],
        'partition_tally': [
            {'verdict': verdict, 'count': tally[verdict]} for verdict in VERDICT_ORDER
        ],
        'attribution_buckets': [
            {'owner': bucket.owner, 'count': len(bucket.findings)}
            for bucket in attribution.buckets
        ],
        'disagreements': [
            {'path': module.path, 'verdict': module.verdict, 'plans': ','.join(module.plans)}
            for module in disagreements
        ],
        'sweep_plans': sorted(sweeps),
        'contested': [
            {'path': module.path, 'plans': ','.join(module.plans)} for module in contested
        ],
        'sweep_crossings': [
            {'path': module.path, 'verdict': module.verdict, 'sweeps': ','.join(module.sweeps)}
            for module in crossings
        ],
        'baseline_drift': {
            'baseline_supplied': baseline_supplied,
            'baseline_count': len(baseline),
            'observed_count': len(observed),
            'added_count': len(drift_added),
            'removed_count': len(drift_removed),
        },
        'baseline_drift_instances': (
            [{'path': path, 'drift': 'added'} for path in drift_added]
            + [{'path': path, 'drift': 'removed'} for path in drift_removed]
        ),
        'not_derivable_modules': [
            {'path': module.path, 'plans': ','.join(module.plans)} for module in not_derivable
        ],
        'not_derivable_specs': [
            {
                'plan_id': claim.plan_id,
                'spec': claim.spec,
                'spec_class': claim.spec_class,
                'unresolved_count': len(claim.unresolved),
            }
            for claim in unresolvable_specs
        ],
        'injected_controls': [
            {'control': name, 'expectation': expectation, 'demonstrated_by': demonstrated}
            for name, expectation, demonstrated in _INJECTED_CONTROLS
        ],
        'test_count': {
            'before': args.tests_before if args.tests_before is not None else 'not_supplied',
            'after': _static_test_count(modules, repo_root),
            'method': _TEST_COUNT_METHOD,
        },
        'provenance': {
            'overlap_live': bool(overlaps),
            'overlap_count': len(overlaps),
        },
        'provenance_placement': [
            {'claim': name, 'value': value, 'citation': citation}
            for name, value, citation in _PLACEMENT_CLAIMS
        ],
        'provenance_overlaps': overlaps,
        'root_claims': [
            {'plan_id': root.plan_id, 'path': root.path} for root in partition.root_claims
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

    report = subparsers.add_parser(
        'report',
        help='Render the full derivation report, every section carrying its producing command',
        allow_abbrev=False,
    )
    report.add_argument(
        '--epic', required=True, help='Epic slug naming the orchestrator store entry'
    )
    report.add_argument(
        '--budget',
        type=int,
        default=DEFAULT_LINE_BUDGET,
        help=f'Test-module line budget (default: {DEFAULT_LINE_BUDGET})',
    )
    report.add_argument(
        '--tests-before',
        type=int,
        default=None,
        help=(
            'Declared-test count before the campaign, for the before/after section. '
            'Measured by the same method as the emitted after figure — the static '
            f'"{_TEST_DEF_PREFIX}" count this report renders — so the two are comparable'
        ),
    )
    report.add_argument(
        '--baseline-findings',
        default=None,
        help=(
            'Path to a file listing the over-budget modules recorded at the baseline, one '
            'per line. Compared POST-HOC against the findings re-derived from the current '
            'tree: drift is reported per instance and never changes the exit status. '
            'Omit it and the drift section reports that nothing was compared'
        ),
    )
    report.set_defaults(handler=cmd_report)

    return parser


@safe_main
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    output_toon(args.handler(args))
    return 0


if __name__ == '__main__':
    main()
