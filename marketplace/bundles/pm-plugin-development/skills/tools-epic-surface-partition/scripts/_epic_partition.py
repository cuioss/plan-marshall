#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Join an epic's parsed claim model against the real ``test/`` tree.

Stage 2 of the epic-surface derivation. Stage 1 (:mod:`_epic_spec_parser`) turns
prose specs into a typed claim model; this module maps every test module in the
tree to the plan(s) claiming it, and groups the test-module line-budget findings
by owning plan.

The partition reports four verdicts as SEPARATE populations:

- ``claimed`` — exactly one plan's resolved entries cover the module.
- ``multiply_claimed`` — more than one plan covers it.
- ``not_derivable`` — no plan's RESOLVED entries cover it, but at least one
  spec names it in a span the parser could not resolve to a path. This is
  coverage the derivation cannot see.
- ``unclaimed`` — no plan covers it and no spec names it.

⛔ ``unclaimed`` and ``not_derivable`` are never merged. Merging them would
report a parser limitation as a partition defect, manufacturing a disagreement
the corpus does not contain.

Exclusions subtract from the claiming plan's own set only: a plan that claims a
recursive glob and excludes a sub-directory does not claim the modules under
that sub-directory, while another plan's claim over them is unaffected.

⛔ A **root span** — an entry covering the whole population root, such as bare
``test/`` or ``test/**`` — discriminates nothing: it names every module, so
honouring it as a claim would mark the entire tree ``multiply_claimed`` and
destroy the partition's signal. Several specs carry such a span as passing
prose rather than as an ownership claim. Root spans are therefore excluded from
claim matching and reported in :attr:`Partition.root_claims`, so the fact is
STATED rather than silently dropped.
"""

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from _epic_spec_parser import (
    KIND_DIRECTORY,
    KIND_RECURSIVE_GLOB,
    SpecClaim,
)

#: The four partition verdicts.
VERDICT_CLAIMED = 'claimed'
VERDICT_UNCLAIMED = 'unclaimed'
VERDICT_MULTIPLY_CLAIMED = 'multiply_claimed'
VERDICT_NOT_DERIVABLE = 'not_derivable'

#: Every verdict carries a row in the tally even at zero, so an empty
#: population reads as measured rather than as absent.
VERDICT_ORDER = (
    VERDICT_CLAIMED,
    VERDICT_UNCLAIMED,
    VERDICT_MULTIPLY_CLAIMED,
    VERDICT_NOT_DERIVABLE,
)

#: Attribution bucket keys for modules with no single owning plan. They keep the
#: three ownerless populations distinct inside the attribution, mirroring the
#: partition's refusal to merge them.
OWNER_UNCLAIMED = '<unclaimed>'
OWNER_MULTIPLY_CLAIMED = '<multiply-claimed>'
OWNER_NOT_DERIVABLE = '<not-derivable>'

#: The test-module line budget the campaign's findings are derived against.
DEFAULT_LINE_BUDGET = 400

#: The filename glob a test module is recognised by.
TEST_MODULE_GLOB = 'test_*.py'

#: The population root. An entry spanning exactly this discriminates nothing.
DEFAULT_ROOT_PREFIX = 'test'


@dataclass(frozen=True)
class ModuleVerdict:
    """One test module, its verdict, and the plans that verdict rests on."""

    path: str
    verdict: str
    plans: tuple[str, ...]


@dataclass(frozen=True)
class RootClaim:
    """One span set aside because it covers the whole population root."""

    plan_id: str
    path: str


@dataclass(frozen=True)
class Partition:
    """Every test module in the tree, each with exactly one verdict."""

    modules: tuple[ModuleVerdict, ...]
    root_claims: tuple[RootClaim, ...] = ()

    def with_verdict(self, verdict: str) -> tuple[ModuleVerdict, ...]:
        """Every module carrying ``verdict``, in tree order."""
        return tuple(module for module in self.modules if module.verdict == verdict)

    def tally(self) -> dict[str, int]:
        """Population size per verdict, with every verdict present."""
        counts = dict.fromkeys(VERDICT_ORDER, 0)
        for module in self.modules:
            counts[module.verdict] += 1
        return counts


@dataclass(frozen=True)
class BudgetFinding:
    """One test module over the line budget, as re-derived from the tree."""

    path: str
    line_count: int


@dataclass(frozen=True)
class AttributionBucket:
    """The over-budget modules attributed to one owner."""

    owner: str
    findings: tuple[BudgetFinding, ...]


@dataclass(frozen=True)
class Attribution:
    """Budget findings grouped by owning plan, each file appearing once."""

    budget: int
    buckets: tuple[AttributionBucket, ...]

    def total_findings(self) -> int:
        return sum(len(bucket.findings) for bucket in self.buckets)


def _segments(path: str) -> list[str]:
    return [segment for segment in path.strip('/').split('/') if segment]


def _match_segments(pattern: list[str], target: list[str]) -> bool:
    """Segment-wise glob match, so a ``*`` never spans a path separator."""
    if len(pattern) != len(target):
        return False
    return all(
        fnmatch.fnmatchcase(part, glob) for glob, part in zip(pattern, target, strict=True)
    )


def entry_matches(entry_path: str, kind: str, module: str) -> bool:
    """Whether one resolved claim entry covers ``module``.

    A recursive glob and a directory both cover everything beneath them; every
    other shape matches segment-wise, so ``a/test_*.py`` covers ``a/test_x.py``
    but not ``a/nested/test_x.py``.
    """
    if kind == KIND_RECURSIVE_GLOB:
        prefix = entry_path[:-2]
        return module.startswith(prefix) if prefix else True
    if kind == KIND_DIRECTORY:
        return module.startswith(entry_path)
    return _match_segments(_segments(entry_path), _segments(module))


def is_root_span(entry_path: str, kind: str, root_prefix: str) -> bool:
    """Whether an entry covers the whole population root, discriminating nothing.

    Only a directory or a recursive glob can span the root; a named file and a
    filename glob always name something narrower.
    """
    if kind == KIND_RECURSIVE_GLOB:
        prefix = entry_path[:-2]
    elif kind == KIND_DIRECTORY:
        prefix = entry_path
    else:
        return False
    stem = prefix.strip('/')
    return not stem or stem == root_prefix.strip('/')


def _discriminating(entries: tuple, root_prefix: str) -> list:
    return [entry for entry in entries if not is_root_span(entry.path, entry.kind, root_prefix)]


def _claims_module(claim: SpecClaim, module: str, root_prefix: str) -> bool:
    """Whether a spec claims ``module`` after root spans and exclusions subtract."""
    claimed = _discriminating(claim.claimed, root_prefix)
    covered = any(entry_matches(entry.path, entry.kind, module) for entry in claimed)
    if not covered:
        return False
    return not any(entry_matches(entry.path, entry.kind, module) for entry in claim.excluded)


def _is_container_span(cleaned: str) -> bool:
    """Whether an unresolved span names a DIRECTORY rather than a file."""
    return cleaned.endswith('/') or cleaned.endswith('**')


def _raw_mentions_module(raw: str, module: str) -> bool:
    """Whether an UNRESOLVED span names ``module``.

    A file-shaped span names the module by its TRAILING segments, the filename
    included: ``test_x.py`` and ``a/test_x.py`` both name ``test/a/test_x.py``.

    A CONTAINER-shaped span — written with a trailing ``/`` or a trailing
    ``**`` — names a directory, so it names every module beneath that
    directory at any depth. Its segments are therefore matched against the
    module's ancestor directories rather than against the filename: the
    filename can never equal a directory name, so anchoring a container span on
    the trailing segment would make it name NOTHING.

    ⛔ A container span naming nothing is not a harmless miss. Every module it
    covers would fall through to ``unclaimed`` instead of ``not_derivable`` —
    the one merge :mod:`_epic_partition` exists to prevent, manufacturing
    partition defects out of the parser's own limits.

    The container match is deliberately unanchored at the front: an unresolved
    span is by definition one the parser could not anchor to the repo root, so
    the only honest reading is "some directory with these segments". Erring
    towards ``not_derivable`` reports coverage the derivation cannot see, which
    is the safe direction; erring the other way invents a defect.
    """
    cleaned = raw[2:] if raw.startswith('./') else raw
    cleaned = cleaned[4:] if cleaned.startswith('.../') else cleaned
    container = _is_container_span(cleaned)
    pattern = _segments(cleaned)
    if container and pattern and pattern[-1] == '**':
        pattern = pattern[:-1]
    target = _segments(module)
    if not pattern:
        return False
    if not container:
        if len(pattern) > len(target):
            return False
        return _match_segments(pattern, target[-len(pattern) :])
    parents = target[:-1]
    width = len(pattern)
    return any(
        _match_segments(pattern, parents[start : start + width])
        for start in range(len(parents) - width + 1)
    )


def _mentions_module(claim: SpecClaim, module: str) -> bool:
    return any(_raw_mentions_module(raw, module) for raw in claim.unresolved)


def iter_test_modules(test_root: Path, repo_root: Path) -> tuple[str, ...]:
    """Every test module under ``test_root``, as sorted repo-relative paths."""
    if not test_root.is_dir():
        return ()
    found = [
        path.relative_to(repo_root).as_posix()
        for path in test_root.rglob(TEST_MODULE_GLOB)
        if path.is_file()
    ]
    return tuple(sorted(found))


def derive_partition(
    claims: list[SpecClaim],
    modules: tuple[str, ...],
    root_prefix: str = DEFAULT_ROOT_PREFIX,
) -> Partition:
    """Assign every module exactly one verdict against the claim model."""
    root_claims = tuple(
        RootClaim(plan_id=claim.plan_id, path=entry.path)
        for claim in claims
        for entry in claim.claimed
        if is_root_span(entry.path, entry.kind, root_prefix)
    )
    verdicts: list[ModuleVerdict] = []
    for module in modules:
        owners = tuple(
            claim.plan_id for claim in claims if _claims_module(claim, module, root_prefix)
        )
        if len(owners) == 1:
            verdicts.append(ModuleVerdict(module, VERDICT_CLAIMED, owners))
            continue
        if len(owners) > 1:
            verdicts.append(ModuleVerdict(module, VERDICT_MULTIPLY_CLAIMED, owners))
            continue
        mentioned = tuple(claim.plan_id for claim in claims if _mentions_module(claim, module))
        if mentioned:
            verdicts.append(ModuleVerdict(module, VERDICT_NOT_DERIVABLE, mentioned))
        else:
            verdicts.append(ModuleVerdict(module, VERDICT_UNCLAIMED, ()))
    return Partition(modules=tuple(verdicts), root_claims=root_claims)


def derive_budget_findings(
    modules: tuple[str, ...],
    repo_root: Path,
    budget: int = DEFAULT_LINE_BUDGET,
) -> tuple[BudgetFinding, ...]:
    """Re-derive the over-budget modules from the CURRENT tree.

    The campaign's published baseline is never adopted as input — it is only
    ever a post-hoc comparison against what this returns.
    """
    findings = [
        BudgetFinding(path=module, line_count=count)
        for module, count in ((m, _line_count(repo_root / m)) for m in modules)
        if count > budget
    ]
    return tuple(findings)


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding='utf-8').splitlines())


def owner_of(module: ModuleVerdict) -> str:
    """The attribution bucket key for one module's verdict."""
    if module.verdict == VERDICT_CLAIMED:
        return module.plans[0]
    if module.verdict == VERDICT_MULTIPLY_CLAIMED:
        return OWNER_MULTIPLY_CLAIMED
    if module.verdict == VERDICT_NOT_DERIVABLE:
        return OWNER_NOT_DERIVABLE
    return OWNER_UNCLAIMED


def derive_attribution(
    partition: Partition,
    findings: tuple[BudgetFinding, ...],
    budget: int = DEFAULT_LINE_BUDGET,
) -> Attribution:
    """Group budget findings by owning plan; each file lands in exactly one bucket."""
    owners = {module.path: owner_of(module) for module in partition.modules}
    grouped: dict[str, list[BudgetFinding]] = {}
    for finding in findings:
        grouped.setdefault(owners.get(finding.path, OWNER_UNCLAIMED), []).append(finding)
    buckets = tuple(
        AttributionBucket(owner=owner, findings=tuple(grouped[owner])) for owner in sorted(grouped)
    )
    return Attribution(budget=budget, buckets=buckets)
