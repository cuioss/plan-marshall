#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Behavioral fixture — the scoped-green / whole-tree-red divergence is CAUGHT.

Drives the D1 seam (``_test_scope_divergence.resolve_test_scope`` +
``classify_divergence``) through a model of the phase-6-finalize
whole-tree module-tests divergence gate (``pre-push-quality-gate.md``), with an
INJECTED build runner rather than a real build. Proves the load-bearing PLAN-14
acceptance: a change that a scoped run would pass but a whole-tree run fails is
routed to the whole-tree target and classified ``caught=True``.

The gate's routing prose (D2) is modelled once by ``_gate_route`` below; the
decision logic itself lives in the pure D1 seam, so this test exercises the real
seam behavior end-to-end without spawning pytest. The D1 seam lives on the
``script-shared/scripts/build/`` PYTHONPATH entry the root conftest sets up
for every test, so it is exercised via a plain import.
"""

import re

import pytest

# Cross-skill import — PYTHONPATH is configured by the root conftest.
from _test_scope_divergence import classify_divergence, resolve_test_scope
from conftest import MARKETPLACE_ROOT

_GATE_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'pre-push-quality-gate.md'
)

#: The three guards the gate runs, in `build.py:cmd_verify` order.
_GUARD_TOKENS = ('quality-gate', 'test-compile', 'module-tests')

#: The three quality-gate dimensions ONLY whole-tree scope reaches IN THIS
#: repository. They are this project's derived set, not a portable list, so they
#: are asserted of the gate document's labelled WORKED EXAMPLE — the rendering
#: of the degradation template for this repository — rather than of the emitted
#: message itself. A worked example naming fewer than all three is the
#: partial-truth signal.
#:
#: This tuple MIRRORS the gate document's own enumeration and is reconciled
#: against it below, in both directions, rather than standing as an independent
#: assertion of the population. A mirror nothing checks drifts silently: were
#: the source section to gain a fourth dimension, the worked example could omit
#: it and every sweep keyed on this tuple would still pass.
_WHOLE_TREE_ONLY_DIMENSIONS = ('plugin-doctor', '.claude/', 'marketplace/targets')

#: The label of the section that AUTHORITATIVELY enumerates those dimensions.
#: The tuple above is derived from it, so the label is the anchor that keeps the
#: population sourced rather than asserted.
_DIMENSION_SOURCE_LABEL = '**Why guard 1 carries a whole-tree arm.**'

#: The paragraph that closes the enumeration — the governing rule stated after
#: the numbered items. Bounding the sweep here keeps the surrounding prose's
#: bullet lists out of the item count.
_DIMENSION_SOURCE_TERMINATOR = '**The general rule'

#: A numbered enumeration item, as the source section renders one.
_ENUMERATED_ITEM = re.compile(r'^\d+\.\s')

#: The placeholder the emitted degradation WARNING interpolates. The dimension
#: set is the PROJECT's — whatever its own ``quality-gate`` widens to beyond
#: module scope — so the emitted message must carry the placeholder rather than
#: one project's dimension names. The literal is what a downstream agent copies,
#: and a copied literal asserts THIS repository's dimensions of a project whose
#: set is different: prose saying "the project's own" does not undo a pinned
#: artifact.
_DIMENSION_PLACEHOLDER = '{dimension_clause}'

#: The label anchoring the worked example that renders the placeholder for this
#: repository. Anchored on the label rather than a line number, so ordinary
#: prose edits around it do not silently empty the sweep — an absent label
#: yields an empty block, which the assertion below rejects.
_WORKED_EXAMPLE_LABEL = "**Worked example — this repository's instance.**"

#: The two clauses the UNENUMERABLE rendering must state. A template with no
#: legal value on the derivation-failed path is how an author ends up filling
#: the placeholder with an empty list — rendering "no dimensions are un-gated",
#: which is the confident-empty signal this gate exists to refuse.
_UNENUMERABLE_RENDERING_CLAUSES = (
    'could not be enumerated',
    'UNKNOWN set of dimensions',
)

#: The label anchoring the block that DECLARES the template's renderings. The
#: clauses above are asserted of that block rather than of the whole document:
#: searched document-wide they also occur in the surrounding explanatory prose,
#: so the assertion would stay green after the rendering it names is removed or
#: broken — passing without verifying its own mechanism.
_TEMPLATE_RENDERINGS_LABEL = '`{dimension_clause}` has exactly two renderings'

#: Guard 1's whole-tree arm, as the ADJACENT phrase "whole-tree quality-gate"
#: (tolerating only markdown emphasis/backtick noise between the two words).
#: Adjacency is load-bearing: a mere-proximity match would be satisfied by the
#: pre-fix prose, where "whole-tree" belongs to test-compile or module-tests and
#: never to quality-gate — which is exactly the drift this sweep must catch. So
#: every lock-step site spells the arm as one adjacent phrase.
_WHOLE_TREE_QUALITY_GATE = re.compile(r'whole-tree[\s`*_]{0,4}quality-gate', re.IGNORECASE)

#: The heading of the section that owns guard 1's whole-tree arm, and the
#: heading levels that terminate it (``####`` and deeper stay inside).
_WHOLE_TREE_ARM_HEADING = '### Whole-tree quality-gate arm'
_SAME_OR_HIGHER_HEADING = re.compile(r'#{1,3} ')

#: A ``quality-gate`` resolve, and the module argument that scopes one. The arm
#: is reachable when it resolves the canonical at DEFAULT scope — no
#: ``--module`` — and runs what came back. Deliberately structural: the arm
#: derives its invocation from the resolver, so which executable a project gets
#: is that project's business. Pinning a build-tool literal here could only ever
#: pass over a hardcoded gate document, which is the defect this sweep removes.
_QG_RESOLVE = re.compile(r'resolve\s+--command\s+quality-gate')
_MODULE_ARG = re.compile(r'--module\b')

#: The arm must RUN what it resolved — a resolved-then-discarded executable
#: gates nothing, so presence of the resolve alone would be a half-assertion.
_RUNS_RESOLVED_EXECUTABLE = re.compile(r'run\s+the\s+captured\s+`?executable`?', re.IGNORECASE)

#: A WARNING the gate actually EMITS, as opposed to prose that mentions one. An
#: emitted warning is the payload of a ``manage-logging`` invocation, so it
#: always rides on a ``--message "[WARNING]`` line. Prose in a *different* arm
#: that cross-references this arm's warning is not itself a warning and carries
#: no obligation to name this arm's dimensions.
_EMITTED_WARNING = '--message "[WARNING]'

# The real Python build_map globs (single-``*`` fnmatch spans ``/``).
_GLOBS = ['marketplace/bundles/*.py', 'test/*.py', 'pyproject.toml']

#: The caller-enumerated registered module names ``resolve_test_scope`` takes as
#: its third argument. The seam is pure by contract, so the set is supplied here
#: rather than read from an inventory inside it. A derived name absent from this
#: set resolves to NO module and lands in ``unresolved_paths``.
_REGISTERED_MODULES = frozenset({'plan-marshall', 'pm-dev-python'})

# A footprint the D1 seam classifies divergence_possible=True: it touches the
# shared build layer, exactly the PLAN-08 cross-module regression class.
_DIVERGENT_FOOTPRINT = [
    'marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_x.py',
]
# A footprint spanning two distinct modules — also divergence_possible=True.
_MULTI_MODULE_FOOTPRINT = [
    'marketplace/bundles/plan-marshall/skills/foo/scripts/a.py',
    'marketplace/bundles/pm-dev-python/skills/bar/scripts/b.py',
]
# A single isolated module, no shared infra — divergence_possible=False.
_ISOLATED_FOOTPRINT = [
    'marketplace/bundles/pm-dev-python/skills/bar/scripts/b.py',
]


def _gate_route(resolution, whole_tree_available: bool):
    """Model the D2 divergence-gate routing over a D1 resolution.

    Returns ``(route, target)`` where ``route`` is one of ``'whole_tree'`` /
    ``'scoped'`` / ``'skip'`` / ``'warn'`` and ``target`` is the module arg a
    scoped run would carry (``None`` for the whole-tree, no-module-arg route and
    for the skip route). Mirrors the branch ORDER in
    ``pre-push-quality-gate.md`` § "Whole-tree module-tests divergence gate" -
    and the order is load-bearing, not incidental.

    The zero-scoped-modules branch MUST be evaluated before the
    ``divergence_possible == false`` branch: that verdict holds for ZERO scoped
    modules as well as for exactly one, and ``recommended_target`` is populated
    only in the one-module case. Collapsing the two lets the scoped branch
    interpolate a null target and invoke ``module-tests None``, which the build
    wrapper exits 0 on and the gate then reads as a pass.
    """
    if not whole_tree_available:
        return 'warn', None
    if resolution.divergence_possible:
        return 'whole_tree', None
    if not resolution.scoped_modules:
        return 'skip', None
    return 'scoped', resolution.recommended_target


class _InjectedRunner:
    """A build runner returning scripted outcomes per target — no real build.

    ``None`` keys the whole-tree (no-module-arg) run; a module name keys a
    scoped run.
    """

    def __init__(self, outcomes: dict[str | None, str]):
        self._outcomes = outcomes
        self.calls: list[str | None] = []

    def run(self, target: str | None) -> str:
        self.calls.append(target)
        return self._outcomes[target]


def _gate_text() -> str:
    text: str = _GATE_DOC.read_text(encoding='utf-8')
    return text


def _lock_step_sites() -> dict[str, str]:
    """Return the named sites that must all describe the same guard set.

    Each site is located by a stable anchor rather than a line number, so
    ordinary prose edits around it do not silently drop a site from the sweep.
    """
    lines = _gate_text().splitlines()
    sites: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('description:'):
            sites.setdefault('frontmatter-description', stripped)
        elif stripped.startswith('Pure executor for the `pre-push-quality-gate`'):
            sites.setdefault('body-guard-enumeration', stripped)
        elif stripped.startswith('The module-tests outcome folds into'):
            sites.setdefault('folds-into-summary', stripped)
        elif stripped.startswith('Record the outcome on the live plan'):
            sites.setdefault('mark-step-complete-preamble', stripped)
        elif stripped.startswith('**Branch A —'):
            sites.setdefault('branch-a-condition', stripped)
        elif stripped.startswith('**Branch B —'):
            sites.setdefault('branch-b-condition', stripped)
        elif '--display-detail "{N} bundles' in stripped:
            sites.setdefault('branch-a-display-detail', stripped)
        elif '--display-detail "{quality-gate failed for' in stripped:
            sites.setdefault('branch-b-display-detail', stripped)
    return sites


def _section(heading: str) -> list[str]:
    """Return the body lines under ``heading``, up to the next heading.

    Anchored on the heading text rather than a line number so ordinary prose
    edits around the section do not silently empty the sweep — an absent
    heading returns ``[]``, which every caller asserts against.
    """
    lines = _gate_text().splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return []
    body: list[str] = []
    for line in lines[start + 1 :]:
        if _SAME_OR_HIGHER_HEADING.match(line):
            break
        body.append(line)
    return body


def _default_scope_quality_gate_resolves(lines: list[str]) -> list[str]:
    """Return the ``quality-gate`` resolves carrying NO ``--module`` argument."""
    return [line for line in lines if _QG_RESOLVE.search(line) and not _MODULE_ARG.search(line)]


def _names_all_three_dimensions(text: str) -> bool:
    return all(dimension in text for dimension in _WHOLE_TREE_ONLY_DIMENSIONS)


def _is_emitted_warning(line: str) -> bool:
    return _EMITTED_WARNING in line


def _degradation_warning_lines() -> list[str]:
    """Return the WARNINGs the gate EMITS on the whole-tree quality-gate skip path.

    Scoped to *emitted* warnings on purpose. A sibling arm's prose may
    cross-reference this arm ("exactly as the whole-tree `quality-gate` arm's
    honest-degradation branch does for its own dimension set") while describing
    its OWN, single-dimension warning; that sentence is documentation of another
    guard, not a warning this arm emits, and holding it to this arm's
    dimension-naming rule would demand a false claim of it.
    """
    return [
        line
        for line in _gate_text().splitlines()
        if _is_emitted_warning(line) and _WHOLE_TREE_QUALITY_GATE.search(line)
    ]


def _worked_example_block() -> list[str]:
    """Return the fenced block rendering the degradation template for this repo.

    Located by the worked-example label rather than by ordinal, so the sweep
    survives prose edits around it. An absent label — or a label with no fenced
    block under it — yields ``[]``, which the caller asserts against, so a
    deleted example fails loudly instead of emptying the assertion.
    """
    lines = _gate_text().splitlines()
    start = next((i for i, line in enumerate(lines) if _WORKED_EXAMPLE_LABEL in line), None)
    if start is None:
        return []
    block: list[str] = []
    in_fence = False
    for line in lines[start + 1 :]:
        if line.lstrip().startswith('```'):
            if in_fence:
                break
            in_fence = True
            continue
        if in_fence:
            block.append(line)
    return block


def _degradation_template_block() -> list[str]:
    """Return the lines declaring the two renderings of the degradation template.

    Located by the renderings label rather than by ordinal, so the sweep
    survives prose edits around it. An absent label — or a label with no body
    beneath it — yields ``[]``, which the caller asserts against, so a deleted
    or relocated declaration fails loudly instead of silently emptying the
    sweep. Bounded by the worked-example label that follows it, since that block
    is this repository's RENDERING of the template and is swept separately.
    """
    lines = _gate_text().splitlines()
    start = next(
        (i for i, line in enumerate(lines) if _TEMPLATE_RENDERINGS_LABEL in line),
        None,
    )
    if start is None:
        return []
    block: list[str] = []
    for line in lines[start + 1 :]:
        if _SAME_OR_HIGHER_HEADING.match(line) or _WORKED_EXAMPLE_LABEL in line:
            break
        block.append(line)
    return block


def _enumerated_dimension_items() -> list[str]:
    """Return the numbered items of the gate document's own dimension enumeration.

    The authoritative source for ``_WHOLE_TREE_ONLY_DIMENSIONS``. Anchored on
    the section label rather than an ordinal; an absent label yields ``[]``,
    which the caller asserts against.
    """
    lines = _gate_text().splitlines()
    start = next((i for i, line in enumerate(lines) if _DIMENSION_SOURCE_LABEL in line), None)
    if start is None:
        return []
    items: list[str] = []
    for line in lines[start + 1 :]:
        if _SAME_OR_HIGHER_HEADING.match(line) or line.startswith(_DIMENSION_SOURCE_TERMINATOR):
            break
        if _ENUMERATED_ITEM.match(line):
            items.append(line)
    return items


_NON_RUN_LIST_LABEL = '**Branch A does not mean every arm ran.**'

_NON_RUN_LIST_TERMINATOR = '**A non-finish is not on that list'

_NUMBERED_ITEM = re.compile(r'^\d+\.\s')

_BRANCH_ZERO_TOKEN = 'branch-0'

_DEGRADED_VARIANT_MARKER = 'module-tests DEGRADED'

_DISPLAY_DETAIL_PAYLOAD = re.compile(r'--display-detail\s+"([^"]*)"')

_MODULE_TESTS_DEGRADATION_TOKENS = ('module-tests DEGRADED', 'module-tests UN-GATED', 'module-tests skipped')

_MODULE_TESTS_DETAIL_VARIANT_HEADING = re.compile(r'\*\*Detail variant — module-tests ')

_FORBIDDEN_GREEN_CLAIM = 'module-tests green'


def _non_run_list_items() -> list[str]:
    """Return the numbered items of Branch A's derived non-run path list.

    An absent label yields ``[]``, which every caller asserts against, so a
    relocated or reworded list fails loudly rather than emptying the sweep.
    """
    lines = _gate_text().splitlines()
    start = next((i for i, line in enumerate(lines) if _NON_RUN_LIST_LABEL in line), None)
    if start is None:
        return []
    items: list[str] = []
    for line in lines[start + 1 :]:
        if _SAME_OR_HIGHER_HEADING.match(line) or line.startswith(_NON_RUN_LIST_TERMINATOR):
            break
        if _NUMBERED_ITEM.match(line):
            items.append(line)
    return items


def _module_tests_degradation_payloads() -> list[str]:
    """Return every documented `display_detail` payload reporting a non-run module-tests arm."""
    return [
        payload
        for payload in _DISPLAY_DETAIL_PAYLOAD.findall(_gate_text())
        if any(token in payload for token in _MODULE_TESTS_DEGRADATION_TOKENS)
    ]


def test_isolated_module_stays_scoped_and_both_green_not_divergent():
    """A single isolated module runs scoped (no whole-tree cost) and is not divergent."""
    # Arrange
    resolution = resolve_test_scope(_ISOLATED_FOOTPRINT, _GLOBS, _REGISTERED_MODULES)
    runner = _InjectedRunner({'pm-dev-python': 'success'})

    # Act
    route, target = _gate_route(resolution, whole_tree_available=True)
    scoped_outcome = runner.run(target)
    verdict = classify_divergence(scoped_outcome, whole_tree_outcome='success')

    # Assert: scoped route to the single module, no whole-tree run, not divergent.
    assert resolution.divergence_possible is False
    assert route == 'scoped'
    assert target == 'pm-dev-python'
    assert runner.calls == ['pm-dev-python']
    assert verdict.divergent is False
    assert verdict.caught is False


def test_unmapped_footprint_fails_closed_to_the_whole_tree_route():
    """A non-empty footprint that maps to no registered module routes whole-tree.

    The counterpart to the skip branch above, and what keeps that branch narrow:
    "nothing to run" (empty footprint) and "cannot determine what to run"
    (unmapped paths) must NOT collapse into one verdict.
    """
    # Arrange — neither path is module-owning under the registered set.
    footprint = ['doc/developer/build.adoc', '.github/workflows/python-verify.yml']

    # Act
    resolution = resolve_test_scope(footprint, _GLOBS, _REGISTERED_MODULES)
    route, target = _gate_route(resolution, whole_tree_available=True)

    # Assert
    assert resolution.divergence_possible is True
    assert resolution.unresolved_paths == tuple(footprint)
    assert route == 'whole_tree'
    assert target is None


def test_gate_document_orders_the_zero_scoped_modules_branch_first():
    """The zero-scoped-modules branch must precede the ``divergence_possible == false`` one.

    Order, not mere presence, is the whole point: the resolver returns
    ``divergence_possible: false`` for ZERO scoped modules as well as for exactly
    one, and only the one-module case populates ``recommended_target``. A gate
    document that reaches the scoped branch first interpolates a null target and
    renders ``module-tests None`` — which the build wrapper exits 0 on, so the
    gate reads it as a pass. Anchored on the branch text rather than its ordinal,
    so renumbering the list does not silently drop the assertion.
    """
    lines = _gate_text().splitlines()

    zero_idx = next(
        (i for i, line in enumerate(lines) if '`scoped_modules` is empty' in line),
        None,
    )
    one_idx = next(
        (i for i, line in enumerate(lines) if 'exactly one scoped module' in line),
        None,
    )

    assert zero_idx is not None, (
        'The gate document carries no zero-scoped-modules branch, so an empty '
        'footprint falls through to the scoped branch and renders module-tests None'
    )
    assert one_idx is not None, (
        "The scoped branch no longer states its 'exactly one scoped module' "
        'precondition, leaving the zero/one collapse implicit again'
    )
    assert zero_idx < one_idx, (
        f'The zero-scoped-modules branch (line {zero_idx + 1}) must be evaluated '
        f'BEFORE the single-module scoped branch (line {one_idx + 1}); as ordered '
        f'it can never be reached.'
    )


def test_degradation_warning_declares_an_unenumerable_rendering():
    """The template must have a legal value when the derivation yields no set.

    Without one, the only rendering an author can reach for on that path is the
    empty list — which prints "no dimensions are un-gated" and turns an
    unestablished set into a confident all-clear.

    Scoped to the declaring block, for the same reason its two siblings are
    scoped (``_degradation_warning_lines``, ``_worked_example_block``): searched
    document-wide, both clauses also occur in the surrounding explanatory prose,
    so the assertion would survive the removal of the very rendering it names —
    green without verifying its own mechanism.
    """
    block = _degradation_template_block()

    assert block, (
        f'The gate document declares no degradation-template block under '
        f'{_TEMPLATE_RENDERINGS_LABEL!r}, so the unenumerable rendering has no '
        f'declared home and this sweep would pass on prose alone'
    )
    declared = '\n'.join(block)

    missing = [c for c in _UNENUMERABLE_RENDERING_CLAUSES if c not in declared]

    assert not missing, (
        f'The degradation template declares no unenumerable rendering '
        f'(missing: {missing}), so a project that cannot derive its '
        f'whole-tree-only dimension set has no honest value for '
        f'{_DIMENSION_PLACEHOLDER!r} and an empty list becomes the default'
    )


def test_every_branch_zero_path_names_the_degraded_detail_variant():
    """Both branch-0 paths must say WHICH variant they emit, not defer to a rule.

    Deferring to "compose under the governing rule" is what left these two paths
    with no named detail at all: an author following the gate document reached
    Branch A, found no variant covering the path, and the nearest one to hand ends
    `test-compile + module-tests green` — asserting an arm that never ran. The
    population is READ from the list by the document's own `branch-0` token, so
    renumbering the list cannot silently drop an item from this sweep.
    """
    items = _non_run_list_items()

    assert items, (
        f'The gate document carries no numbered non-run list under '
        f'{_NON_RUN_LIST_LABEL!r}, so Branch A no longer enumerates the paths that '
        f'reach it without an arm having run, and this sweep would pass over nothing'
    )

    branch_zero_items = [item for item in items if _BRANCH_ZERO_TOKEN in item]

    assert branch_zero_items, (
        f'None of the {len(items)} non-run item(s) names a {_BRANCH_ZERO_TOKEN!r} '
        f'path, so either the list dropped both branch-0 degradations or it renamed '
        f'them — in both cases the paths this deliverable covers are unswept. '
        f'Items: {items}'
    )

    unnamed = [item for item in branch_zero_items if _DEGRADED_VARIANT_MARKER not in item]

    assert not unnamed, (
        f'These branch-0 non-run path(s) name no {_DEGRADED_VARIANT_MARKER!r} detail '
        f'variant, so an author reaching Branch A from them has no documented string '
        f'to emit and the nearest one claims module-tests is green: {unnamed}'
    )


def test_the_green_claim_detector_fires_on_branch_as_default_string():
    """Mutation guard: the predicate must reject the string it exists to keep out.

    Branch A's default detail is precisely the payload a degradation path must not
    emit, so it is the exact shape the detector has to catch. Without this, a typo
    in :data:`_FORBIDDEN_GREEN_CLAIM` would leave the sweep above vacuously green
    over every payload.
    """
    branch_a_default = '{N} bundles + whole-tree quality-gate green, test-compile + module-tests green'

    assert _FORBIDDEN_GREEN_CLAIM in branch_a_default, (
        'The green-claim detector does not fire on Branch A default string, which '
        'is the one payload a degradation path must never emit — so the sweep above '
        'would pass over it'
    )

    # Negative control — a payload that reports the arms that DID run as green while
    # naming module-tests as not run is CONFORMANT, so the detector must not fire on
    # it. A detector that did would have to be suppressed to keep the document green.
    conformant = '{N} bundles + whole-tree gates green, module-tests DEGRADED'
    assert _FORBIDDEN_GREEN_CLAIM not in conformant, (
        'The green-claim detector fires on a conformant degradation payload that '
        'reports only the arms that ran as green — banning the word outright would '
        'strip the passing arms out of the step record'
    )


def test_three_dimension_detector_rejects_a_single_dimension_warning():
    # A WARNING naming only one dimension is the partial-truth shape this
    # deliverable forbids; the detector must reject it.
    single = (
        '[WARNING] (plan-marshall:pre-push-quality-gate) Whole-tree '
        'quality-gate unavailable — the plugin-doctor pass is UN-GATED.'
    )
    assert not _names_all_three_dimensions(single), (
        'Three-dimension detector accepted a WARNING naming only one dimension — the assertion would be vacuous'
    )

    two = single.replace('UN-GATED.', 'UN-GATED, and .claude/ ruff coverage.')
    assert not _names_all_three_dimensions(two), 'Three-dimension detector accepted a two-dimension WARNING'

    complete = two.replace('ruff coverage.', 'ruff coverage, and marketplace/targets SPDX coverage.')
    assert _names_all_three_dimensions(complete), 'Three-dimension detector rejected a complete three-dimension WARNING'


def test_whole_tree_arm_detector_fires_on_the_pre_fix_bundle_only_prose():
    # Mutation guard for the lock-step sweep: the pre-fix sites described guard
    # 1 as bundle-scoped only, with no whole-tree arm.
    pre_fix_sites = [
        'description: Run quality-gate per affected bundle, then whole-tree '
        'test-compile, then gate whole-tree module-tests on scoped-vs-whole-tree '
        'divergence risk, as the last gate before push',
        '**Branch A — all bundles green AND test-compile green AND module-tests gate green**:',
        '  --display-detail "quality-gate green for {N} bundle(s), test-compile green, module-tests gate green" \\',
    ]

    # The frontmatter line is the subtle one: it DOES contain "whole-tree", but
    # only attached to test-compile / module-tests, never to quality-gate. The
    # adjacency-bounded detector must not be fooled by that.
    assert not _WHOLE_TREE_QUALITY_GATE.search(pre_fix_sites[0]), (
        'Whole-tree-arm detector was fooled by a "whole-tree" that belongs to a '
        'different guard — the lock-step sweep would be vacuously green'
    )
    for site in pre_fix_sites[1:]:
        assert not _WHOLE_TREE_QUALITY_GATE.search(site), (
            f'Whole-tree-arm detector failed to reject a known pre-fix bundle-only site: {site!r}'
        )

    # Positive control — the post-fix Branch A condition IS accepted.
    post_fix = (
        '**Branch A — all bundles green AND whole-tree quality-gate green AND '
        'test-compile green AND module-tests gate green**:'
    )
    assert _WHOLE_TREE_QUALITY_GATE.search(post_fix)
