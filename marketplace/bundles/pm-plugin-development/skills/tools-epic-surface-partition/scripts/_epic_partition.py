#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Join an epic's parsed claim model against the real ``test/`` tree.

Stage 2 of the epic-surface derivation. Stage 1
(``plan-marshall:script-shared``'s :mod:`epic_spec_parser`, the marketplace's
single reader of the ``## Expected Surface`` grammar) turns prose specs into a
typed claim model; this module maps every test module in the tree to the plan(s)
claiming it, and groups the test-module line-budget findings by owning plan.

The partition reports each verdict in :data:`VERDICT_ORDER` as a SEPARATE
population:

- ``claimed`` — exactly one SLICE plan's resolved entries cover the module.
- ``contested`` — two or more SLICE plans cover it. This is the residual
  genuinely-contested set: small enough to enumerate and act on.
- ``swept`` — no slice plan covers it, but one or more SWEEP plans do. The
  crossing is reported and no owner is manufactured.
- ``not_derivable`` — no plan's resolved entries cover it, but at least one
  spec names it in a span the parser could not resolve, or names it in a
  LEAD-shaped entry. This is coverage the derivation cannot see.
- ``unclaimed`` — no plan covers it and no spec names it.

A **sweep plan** is one whose spec DECLARES ITSELF to cross the whole partition
by construction, rather than claiming a slice of it. Such a plan pairs with
every other plan by design, so counting it as a competing owner would mark the
whole tree contested and destroy the partition's signal. A slice that shares a
module with any number of sweeps therefore OWNS that module, and the sweeps
crossing it are recorded beside the verdict as a separate fact
(:attr:`ModuleVerdict.sweeps`) rather than as competing ownership.

⛔ Sweep-ness is detected from the spec's own self-declaration by
:data:`_SWEEP_RE`, never from a hard-coded plan-id list — such a list here would
be the same defect the derivation exists to close, one level down.

⛔ A sweep plan is a property of the PLAN; a root span is a property of an
ENTRY. The two are independent and neither implies the other.

⛔ ``unclaimed``, ``swept`` and ``not_derivable`` are never merged. Merging them
would report a parser limitation or a deliberate crossing as a partition defect,
manufacturing a disagreement the corpus does not contain.

⛔ A LEAD-shaped entry contributes NO claim here. Stage 1 states each entry's
shape and demotes nothing, because its other consumer needs the surface whole;
this stage does the demotion, which is the projection half of that shared
reader's contract. A lead names a path without claiming it, so honouring it as
ownership is what collapses the attribution into one contested bucket.

Exclusions subtract from the claiming plan's own set only: a plan that claims a
recursive glob and excludes a sub-directory does not claim the modules under
that sub-directory, while another plan's claim over them is unaffected.

⛔ A **root span** — an entry covering the whole population root, such as bare
``test/`` or ``test/**`` — discriminates nothing: it names every module, so
honouring it as a claim would mark the entire tree ``contested`` and destroy the
partition's signal. Several specs carry such a span as passing prose rather than
as an ownership claim. Root spans are therefore excluded from claim matching and
reported in :attr:`Partition.root_claims`, so the fact is STATED rather than
silently dropped.

⛔ A spec whose class is ``derived`` owns nothing: it declares its surface the
union of OTHER plans' surfaces, so its entries restate their claims instead of
competing with them. Its coverage is reported as ``not_derivable`` when no slice
claims the module, never as an ownership contest.
"""

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

from epic_spec_parser import (
    CLASS_DERIVED,
    KIND_DIRECTORY,
    KIND_RECURSIVE_GLOB,
    SHAPE_LEAD,
    SpecClaim,
)

#: The partition verdicts.
VERDICT_CLAIMED = 'claimed'
VERDICT_UNCLAIMED = 'unclaimed'
VERDICT_CONTESTED = 'contested'
VERDICT_SWEPT = 'swept'
VERDICT_NOT_DERIVABLE = 'not_derivable'

#: Every verdict carries a row in the tally even at zero, so an empty
#: population reads as measured rather than as absent.
VERDICT_ORDER = (
    VERDICT_CLAIMED,
    VERDICT_UNCLAIMED,
    VERDICT_CONTESTED,
    VERDICT_SWEPT,
    VERDICT_NOT_DERIVABLE,
)

#: Attribution bucket keys for modules with no single owning plan. They keep the
#: ownerless populations distinct inside the attribution, mirroring the
#: partition's refusal to merge them.
OWNER_UNCLAIMED = '<unclaimed>'
OWNER_CONTESTED = '<contested>'
OWNER_SWEPT = '<swept>'
OWNER_NOT_DERIVABLE = '<not-derivable>'

#: A spec's self-declaration that it crosses the whole partition by construction
#: rather than claiming a slice of it, as a keyword-marker regex over the spec's
#: OWN prose — the same style as the parser's ``_DERIVED_RE``. Four settled
#: phrasings of the ONE declaration, each a sentence a spec writes about itself:
#:
#: - its surface is the test tree ENTIRE;
#: - it PAIRS WITH NO OTHER plan over that tree;
#: - it CROSSES the epic's reduction SLICES;
#: - its sites DO NOT RESPECT the slice boundaries, or the epic's partition.
#:
#: ⛔ The alternation is deliberately wider than the narrowest set reproducing
#: today's sweep list, and that width is the point. A marker matching only the
#: specs that share ONE boilerplate sentence is the hard-coded plan list this
#: module's docstring forbids, wearing a regex: it happens to name today's
#: sweeps and stops matching the moment a plan declares its crossing in its own
#: words instead of copying that sentence — which is exactly how a self-declared
#: sweep was read as a competing slice owner and contested every slice it
#: crossed. The crossing and partition-disregard alternatives are what make this
#: a reading of what a spec SAYS rather than a fingerprint of who wrote it.
#:
#: ⛔ The crossing alternative requires the plural ``slices`` — the epic's
#: reduction slices — and deliberately does NOT admit "crosses the whole
#: partition". A spec ANALYSING the corpus quotes that phrase when it cites
#: another spec's declaration, and a quotation is not a declaration: keying on
#: it would sweep the analysing plan and hand its own tests to a neighbour.
#:
#: ⛔ Corpus-independent by construction: it matches what a spec SAYS ABOUT
#: ITSELF, so a sweep added to the corpus is detected with no edit here, and no
#: plan identifier appears in the mechanism.
_SWEEP_RE = re.compile(
    r'\bpairs with no other\b'
    r'|\btree entire\b'
    r'|\bcrosses\b[^.]{0,60}\bslices\b'
    r'|\bdo(?:es)? not respect\b[^.]{0,60}\b(?:slice boundaries|partition)\b',
    re.IGNORECASE,
)

#: The test-module line budget the campaign's findings are derived against.
DEFAULT_LINE_BUDGET = 400

#: The filename glob a test module is recognised by.
TEST_MODULE_GLOB = 'test_*.py'

#: The population root. An entry spanning exactly this discriminates nothing.
ROOT_PREFIX = 'test'


@dataclass(frozen=True)
class ModuleVerdict:
    """One test module, its verdict, and the plans that verdict rests on.

    ``plans`` carries the SLICE plans the verdict rests on; ``sweeps`` carries
    the sweep plans that also cross the module. The two are separate fields
    because they are separate facts: a sweep crossing a slice's module is not a
    competing claim on it, and folding the two together is what produced a
    single undifferentiated contested bucket.
    """

    path: str
    verdict: str
    plans: tuple[str, ...]
    sweeps: tuple[str, ...] = ()


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


def is_root_span(entry_path: str, kind: str) -> bool:
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
    return not stem or stem == ROOT_PREFIX


def is_sweep_declaration(spec_text: str) -> bool:
    """Whether a spec DECLARES ITSELF a whole-partition sweep.

    The marker is matched over the spec's own prose, so the decision rests on
    what the plan says about itself rather than on any list held here. Tested in
    isolation from the rest of the partition, because a marker that silently
    stopped matching would quietly restore the single-bucket collapse.
    """
    return _SWEEP_RE.search(spec_text) is not None


def derive_sweep_plans(claims: list[SpecClaim], plans_dir: Path) -> frozenset[str]:
    """The plan ids whose specs declare themselves whole-partition sweeps.

    A spec that cannot be read contributes no sweep declaration: the partition
    then treats the plan as an ordinary slice, which is the conservative
    direction — it may report a contest that a readable spec would have resolved,
    and never invents an ownership it cannot substantiate.
    """
    sweeps = set()
    for claim in claims:
        try:
            text = (plans_dir / claim.spec).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        if is_sweep_declaration(text):
            sweeps.add(claim.plan_id)
    return frozenset(sweeps)


def _discriminating(claim: SpecClaim) -> list:
    """The spec's claimed entries that discriminate at all — root spans removed."""
    return [entry for entry in claim.claimed if not is_root_span(entry.path, entry.kind)]


def _owning_entries(claim: SpecClaim) -> list:
    """The entries that carry OWNERSHIP.

    ⛔ A spec whose surface is DERIVED owns nothing: it declares itself the union
    of OTHER plans' surfaces, so its entries restate those plans' claims rather
    than competing with them. Counting them as ownership makes the deriving spec
    a co-owner of every module its constituents cover, which contests the whole
    corpus at once. Stage 1 already publishes this verdict, and the reader's
    OTHER consumer already refuses to compare a derived spec's paths at its
    disjointness gate — this is the same refusal, applied to attribution.
    """
    if claim.spec_class == CLASS_DERIVED:
        return []
    return [entry for entry in _discriminating(claim) if entry.shape != SHAPE_LEAD]


def _naming_entries(claim: SpecClaim) -> list:
    """The entries that NAME a module without owning it.

    Together with :func:`_owning_entries` this partitions the spec's
    discriminating entries: every one of them either owns or merely names, never
    both and never neither. A named-but-unowned module is coverage the
    derivation cannot attribute, which is ``not_derivable`` — never
    ``unclaimed``.
    """
    if claim.spec_class == CLASS_DERIVED:
        return _discriminating(claim)
    return [entry for entry in _discriminating(claim) if entry.shape == SHAPE_LEAD]


def _claims_module(claim: SpecClaim, module: str) -> bool:
    """Whether a spec claims ``module`` after leads, root spans and exclusions subtract."""
    covered = any(entry_matches(entry.path, entry.kind, module) for entry in _owning_entries(claim))
    if not covered:
        return False
    return not any(entry_matches(entry.path, entry.kind, module) for entry in claim.excluded)


def _leads_module(claim: SpecClaim, module: str) -> bool:
    """Whether a spec NAMES ``module`` without claiming it.

    Root spans are excluded for the same reason they are excluded from claim
    matching: a span over the whole root discriminates nothing, and honouring it
    would mark the entire tree ``not_derivable``.
    """
    return any(entry_matches(entry.path, entry.kind, module) for entry in _naming_entries(claim))


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
    """Whether a spec names ``module`` in coverage the derivation cannot see.

    Two independent sources of such coverage: a span the parser could not
    resolve, and an entry stage 1 resolved but marked lead-shaped.
    """
    if any(_raw_mentions_module(raw, module) for raw in claim.unresolved):
        return True
    return _leads_module(claim, module)


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
    sweeps: frozenset[str] = frozenset(),
) -> Partition:
    """Assign every module exactly one verdict against the claim model.

    ``sweeps`` names the plans that declared themselves whole-partition sweeps
    (see :func:`derive_sweep_plans`). They are separated from the claiming set
    BEFORE the owner count is taken, which is what lets a single slice own a
    module that any number of sweeps also cross. Passing an empty set is the
    honest "no sweep declared" case, never a default that hides one.
    """
    root_claims = tuple(
        RootClaim(plan_id=claim.plan_id, path=entry.path)
        for claim in claims
        for entry in claim.claimed
        if is_root_span(entry.path, entry.kind)
    )
    verdicts: list[ModuleVerdict] = []
    for module in modules:
        claiming = tuple(claim.plan_id for claim in claims if _claims_module(claim, module))
        owners = tuple(plan_id for plan_id in claiming if plan_id not in sweeps)
        crossing = tuple(plan_id for plan_id in claiming if plan_id in sweeps)
        if len(owners) == 1:
            verdicts.append(ModuleVerdict(module, VERDICT_CLAIMED, owners, crossing))
            continue
        if len(owners) > 1:
            verdicts.append(ModuleVerdict(module, VERDICT_CONTESTED, owners, crossing))
            continue
        if crossing:
            verdicts.append(ModuleVerdict(module, VERDICT_SWEPT, (), crossing))
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
    """The attribution bucket key for one module's verdict.

    A ``claimed`` module is attributed to its owning slice REGARDLESS of how
    many sweeps also cross it — that is the whole point of separating the two
    populations, and it is what breaks the single-bucket collapse.
    """
    if module.verdict == VERDICT_CLAIMED:
        return module.plans[0]
    if module.verdict == VERDICT_CONTESTED:
        return OWNER_CONTESTED
    if module.verdict == VERDICT_SWEPT:
        return OWNER_SWEPT
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
