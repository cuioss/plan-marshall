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
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'pre-push-quality-gate.md'
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
_WHOLE_TREE_QUALITY_GATE = re.compile(
    r'whole-tree[\s`*_]{0,4}quality-gate', re.IGNORECASE
)

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
_RUNS_RESOLVED_EXECUTABLE = re.compile(
    r'run\s+the\s+captured\s+`?executable`?', re.IGNORECASE
)

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


@pytest.mark.parametrize(
    'footprint',
    [
        pytest.param(_DIVERGENT_FOOTPRINT, id='shared_build_infra'),
        pytest.param(_MULTI_MODULE_FOOTPRINT, id='multi_module'),
    ],
)
def test_scoped_green_whole_tree_red_is_caught(footprint):
    """A divergent footprint routes to whole-tree and CATCHES the regression."""
    # Arrange: the scoped target(s) are green, the whole-tree run is red. The
    # gate routes a divergent footprint to the whole-tree (``None``) run only, so
    # the injected runner scripts just that key red; the scoped-green side is the
    # ``scoped_outcome`` literal below. (``recommended_target`` is ``None`` for a
    # divergent footprint, so keying it here would collide with the whole-tree
    # ``None`` key and mask the red outcome.)
    resolution = resolve_test_scope(footprint, _GLOBS, _REGISTERED_MODULES)
    runner = _InjectedRunner({None: 'error'})

    # Act: the gate routes on divergence risk, then the seam classifies the pair.
    route, target = _gate_route(resolution, whole_tree_available=True)
    scoped_outcome = 'success'  # what a scoped run would have reported
    whole_tree_outcome = runner.run(target)
    verdict = classify_divergence(scoped_outcome, whole_tree_outcome)

    # Assert: routed to whole-tree (no module arg) and the divergence is caught.
    assert resolution.divergence_possible is True
    assert route == 'whole_tree'
    assert target is None
    assert runner.calls == [None]
    assert verdict.divergent is True
    assert verdict.caught is True


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


def test_whole_tree_unavailable_routes_to_warn():
    """When no pytest module set is discoverable the gate degrades to a WARNING."""
    # Arrange: a divergent footprint, but whole-tree module-tests is unavailable.
    resolution = resolve_test_scope(_DIVERGENT_FOOTPRINT, _GLOBS, _REGISTERED_MODULES)

    # Act
    route, target = _gate_route(resolution, whole_tree_available=False)

    # Assert: honest degradation — warn, never a silent whole-tree skip masquerading as green.
    assert resolution.divergence_possible is True
    assert route == 'warn'
    assert target is None


def test_empty_footprint_skips_pytest_instead_of_interpolating_a_null_target():
    """Zero scoped modules routes to ``skip`` — never to a scoped run with a null target.

    The empty footprint is the one legitimate benign verdict from the seam
    (``divergence_possible: false`` with ``recommended_target: None``), so it
    shares that verdict with the single-module case while carrying NO target.
    Branch-ordering is what keeps them apart; without it the scoped branch
    renders ``module-tests None``, which the wrapper exits 0 on and the gate
    reads as a pass.
    """
    # Arrange
    resolution = resolve_test_scope([], _GLOBS, _REGISTERED_MODULES)
    runner = _InjectedRunner({})

    # Act
    route, target = _gate_route(resolution, whole_tree_available=True)

    # Assert
    assert resolution.divergence_possible is False
    assert resolution.scoped_modules == ()
    assert resolution.recommended_target is None
    assert route == 'skip'
    assert target is None
    assert runner.calls == [], 'the skip branch must invoke no pytest run at all'


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


# ---------------------------------------------------------------------------
# Guard 1's whole-tree arm: reachability, honest degradation, lock-step
# ---------------------------------------------------------------------------
#
# Three quality-gate dimensions exist ONLY at whole-tree scope IN THIS
# repository (the marketplace-wide plugin-doctor pass, the `.claude/` ruff
# coverage, and the `marketplace/targets` SPDX coverage). A purely bundle-scoped
# guard 1 can never reach them, so they surface first at remote CI. These tests
# pin that guard 1 carries a whole-tree arm, that any skip path degrades
# honestly, and that the lock-step sites describing the guard set cannot drift
# apart one site at a time.
#
# The degradation obligation is split across two assertions because the set is
# the PROJECT's, not this repository's: the EMITTED message must interpolate the
# derived set (so a consumer names its own dimensions), while the labelled
# WORKED EXAMPLE — this repository's rendering of that template — must name all
# three. Asserting all three of the emitted message would re-pin the literal;
# asserting nothing of the example would let the template ship with no instance.


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
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == heading), None
    )
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
    return [
        line
        for line in lines
        if _QG_RESOLVE.search(line) and not _MODULE_ARG.search(line)
    ]


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


def test_whole_tree_quality_gate_pass_is_reachable_from_the_gate_document():
    """Guard 1's whole-tree arm must resolve its own invocation and then run it.

    Reachability is asserted STRUCTURALLY — a default-scope (no ``--module``)
    ``quality-gate`` resolve inside the arm, plus the instruction to run what
    that resolve returned. Asserting a literal build-tool invocation instead
    would pin the very hardcoding this sweep exists to remove: the arm obtains
    its executable from the resolver, so a literal assertion can only pass on a
    gate document that hardcodes one project's build tool.
    """
    arm = _section(_WHOLE_TREE_ARM_HEADING)

    assert arm, (
        f'The gate document carries no "{_WHOLE_TREE_ARM_HEADING}" section, so '
        f'the three whole-tree-only dimensions are unreachable from the pre-push gate'
    )
    assert _default_scope_quality_gate_resolves(arm), (
        'The whole-tree arm must resolve quality-gate at DEFAULT scope (no '
        '--module argument) — a module-scoped resolve reaches only the '
        'per-bundle dimensions, never the three whole-tree-only ones'
    )
    assert any(_RUNS_RESOLVED_EXECUTABLE.search(line) for line in arm), (
        'The whole-tree arm resolves an executable but never says to run it — '
        'a resolved-then-discarded invocation gates nothing'
    )


def test_gate_document_names_all_three_whole_tree_only_dimensions():
    text = _gate_text()

    missing = [d for d in _WHOLE_TREE_ONLY_DIMENSIONS if d not in text]

    assert not missing, (
        f'The gate document must name every whole-tree-only quality-gate '
        f'dimension so a reader knows what the arm exists to reach. '
        f'Missing: {missing}'
    )


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


def test_gate_document_parses_and_discloses_unresolved_paths():
    """``unresolved_paths`` must be parsed AND surfaced as a WARNING by the gate.

    The ADR-014 disclosure only reaches a human if the gate both reads the field
    and emits it. Asserting the parse alone would pass on a gate that read the
    field and dropped it silently.
    """
    text = _gate_text()

    assert '`unresolved_paths`' in text, (
        'The gate document must parse unresolved_paths from the resolve-test-scope TOON'
    )
    disclosure = [
        line
        for line in text.splitlines()
        if '[WARNING]' in line and 'unresolved_paths' in line
    ]
    assert disclosure, (
        'The gate document must emit a [WARNING] naming the unresolved paths — '
        'a parsed-but-undisclosed field is a silent drop (ADR-014)'
    )


def _worked_example_block() -> list[str]:
    """Return the fenced block rendering the degradation template for this repo.

    Located by the worked-example label rather than by ordinal, so the sweep
    survives prose edits around it. An absent label — or a label with no fenced
    block under it — yields ``[]``, which the caller asserts against, so a
    deleted example fails loudly instead of emptying the assertion.
    """
    lines = _gate_text().splitlines()
    start = next(
        (i for i, line in enumerate(lines) if _WORKED_EXAMPLE_LABEL in line), None
    )
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


def test_degradation_warning_interpolates_the_derived_dimension_set():
    """The EMITTED WARNING carries the derived set, never one project's literal.

    The surrounding prose has always said the dimensions to name are "the
    project's own", but prose is not the artifact a downstream agent copies —
    the message literal is. A hardcoded literal therefore asserts THIS
    repository's three dimensions of a project whose whole-tree-only set is
    different, which is the shipped-guard-assumes-our-layout defect in the one
    place it does the most damage: a WARNING that is supposed to state a
    coverage boundary honestly.
    """
    warnings = _degradation_warning_lines()

    assert warnings, (
        'The gate document must carry an honest-degradation WARNING for the '
        'whole-tree quality-gate skip path — a silent skip is prohibited'
    )
    for warning in warnings:
        assert _DIMENSION_PLACEHOLDER in warning, (
            f'A whole-tree quality-gate degradation WARNING must interpolate '
            f'the derived dimension set via {_DIMENSION_PLACEHOLDER!r}, so a '
            f'consumer emits ITS OWN whole-tree-only dimensions. Offending '
            f'line: {warning!r}'
        )
        pinned = [d for d in _WHOLE_TREE_ONLY_DIMENSIONS if d in warning]
        assert not pinned, (
            f'The emitted WARNING pins this repository\'s dimension names '
            f'{pinned} instead of interpolating the derived set — the literal '
            f'is what a downstream agent copies. Offending line: {warning!r}'
        )


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
    start = next(
        (i for i, line in enumerate(lines) if _DIMENSION_SOURCE_LABEL in line), None
    )
    if start is None:
        return []
    items: list[str] = []
    for line in lines[start + 1 :]:
        if _SAME_OR_HIGHER_HEADING.match(line) or line.startswith(
            _DIMENSION_SOURCE_TERMINATOR
        ):
            break
        if _ENUMERATED_ITEM.match(line):
            items.append(line)
    return items


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


def test_whole_tree_only_dimension_population_is_derived_not_asserted():
    """The expected dimension set must reconcile with the document's enumeration.

    ``_WHOLE_TREE_ONLY_DIMENSIONS`` is what every dimension sweep above keys on,
    so its own completeness is load-bearing. Left as a hand-written triple that
    nothing reconciles against the authoritative section, it is an ASSERTED
    population — and an asserted population cannot notice a fourth dimension
    being added: the worked example could omit the new one and stay green.
    Reconciled in BOTH directions, so neither an enumerated item without a token
    nor a token without an enumerated item can pass.
    """
    items = _enumerated_dimension_items()

    assert items, (
        f'The gate document carries no enumerated dimension list under '
        f'{_DIMENSION_SOURCE_LABEL!r}, so the authoritative source for '
        f'{_WHOLE_TREE_ONLY_DIMENSIONS} is gone and every sweep keyed on that '
        f'tuple now pins an unsourced literal'
    )
    assert len(items) == len(_WHOLE_TREE_ONLY_DIMENSIONS), (
        f'The gate document enumerates {len(items)} whole-tree-only dimension(s) '
        f'but the expected set carries {len(_WHOLE_TREE_ONLY_DIMENSIONS)}: '
        f'{_WHOLE_TREE_ONLY_DIMENSIONS}. Enumerated: {items}'
    )

    enumerated = '\n'.join(items)
    unsourced = [d for d in _WHOLE_TREE_ONLY_DIMENSIONS if d not in enumerated]
    assert not unsourced, (
        f'These expected dimensions appear in no enumerated item, so the tuple '
        f'has drifted from the section that defines it: {unsourced}'
    )

    uncovered = [
        item
        for item in items
        if not any(d in item for d in _WHOLE_TREE_ONLY_DIMENSIONS)
    ]
    assert not uncovered, (
        f'These enumerated dimensions are matched by no token in '
        f'{_WHOLE_TREE_ONLY_DIMENSIONS}, so the worked example could omit them '
        f'while every sweep stayed green: {uncovered}'
    )


def test_degradation_warning_worked_example_names_all_three_dimensions():
    """The template's worked example must render this repository's full set.

    A template with no instance is the opposite failure from a pinned literal:
    the reader gets a placeholder and no evidence of what a correct rendering
    looks like. The example is therefore mandatory, and — being this
    repository's own rendering — it carries the same all-three obligation the
    emitted literal used to.
    """
    block = _worked_example_block()

    assert block, (
        f'The gate document carries no fenced worked example under '
        f'{_WORKED_EXAMPLE_LABEL!r}, so the degradation template ships with no '
        f'concrete rendering to be read against'
    )
    rendered = '\n'.join(block)
    assert _names_all_three_dimensions(rendered), (
        f'The worked example renders the degradation template for THIS '
        f'repository, so it must name ALL THREE un-gated dimensions '
        f'{_WHOLE_TREE_ONLY_DIMENSIONS} — never a singular "the whole-tree '
        f'dimension". Rendered: {rendered!r}'
    )


def test_lock_step_sites_all_name_the_whole_tree_quality_gate_arm():
    sites = _lock_step_sites()

    # Every named site must have been located; a missing site would silently
    # shrink the sweep and let that site drift unchecked.
    expected_sites = {
        'frontmatter-description',
        'body-guard-enumeration',
        'folds-into-summary',
        'mark-step-complete-preamble',
        'branch-a-condition',
        'branch-b-condition',
        'branch-a-display-detail',
        'branch-b-display-detail',
    }
    missing_sites = expected_sites - set(sites)
    assert not missing_sites, (
        f'Lock-step sites not found in pre-push-quality-gate.md: '
        f'{sorted(missing_sites)} — the sweep would silently skip them'
    )

    stale = [
        name
        for name, body in sites.items()
        if not _WHOLE_TREE_QUALITY_GATE.search(body)
    ]

    assert not stale, (
        f'Lock-step drift: these sites describe the guard set without naming '
        f"guard 1's whole-tree arm, so one site was updated and another left "
        f'stale: {sorted(stale)}'
    )


def test_lock_step_sites_all_name_every_guard():
    # The guard set itself must stay consistent across the describing sites —
    # the branch conditions and display_detail strings are where a guard is
    # most often added in one place and forgotten in the other.
    sites = _lock_step_sites()

    drift = {
        name: [g for g in _GUARD_TOKENS if g not in body]
        for name, body in sites.items()
        if name
        in {
            'body-guard-enumeration',
            'folds-into-summary',
            'mark-step-complete-preamble',
            'branch-a-condition',
            'branch-b-condition',
        }
    }
    incomplete = {name: missing for name, missing in drift.items() if missing}

    assert not incomplete, (
        f'Lock-step drift: these sites omit guards from the guard set '
        f'{_GUARD_TOKENS}: {incomplete}'
    )


# ---------------------------------------------------------------------------
# Mutation guards — the sweeps above must fail on the pre-fix shapes
# ---------------------------------------------------------------------------


def test_three_dimension_detector_rejects_a_single_dimension_warning():
    # A WARNING naming only one dimension is the partial-truth shape this
    # deliverable forbids; the detector must reject it.
    single = (
        '[WARNING] (plan-marshall:pre-push-quality-gate) Whole-tree '
        'quality-gate unavailable — the plugin-doctor pass is UN-GATED.'
    )
    assert not _names_all_three_dimensions(single), (
        'Three-dimension detector accepted a WARNING naming only one '
        'dimension — the assertion would be vacuous'
    )

    two = single.replace('UN-GATED.', 'UN-GATED, and .claude/ ruff coverage.')
    assert not _names_all_three_dimensions(two), (
        'Three-dimension detector accepted a two-dimension WARNING'
    )

    complete = two.replace(
        'ruff coverage.', 'ruff coverage, and marketplace/targets SPDX coverage.'
    )
    assert _names_all_three_dimensions(complete), (
        'Three-dimension detector rejected a complete three-dimension WARNING'
    )


def test_reachability_detector_rejects_a_module_scoped_resolve_and_an_empty_arm():
    # Mutation guard for the reachability sweep. The per-bundle loop resolves
    # the SAME canonical, so a detector that only looked for `--command
    # quality-gate` would be satisfied by a gate document that dropped the
    # whole-tree arm entirely — vacuously green on exactly the regression the
    # sweep exists to catch. The `--module` argument is the discriminator.
    per_bundle = '  resolve --command quality-gate --module {bundle} --audit-plan-id {plan_id}'
    assert not _default_scope_quality_gate_resolves([per_bundle]), (
        'Reachability detector accepted the per-bundle module-scoped resolve as '
        'a whole-tree one — the sweep would pass with no whole-tree arm at all'
    )

    assert not _default_scope_quality_gate_resolves([]), (
        'Reachability detector reported a resolve over an EMPTY section — an '
        'absent arm must never read as a present one'
    )

    # Positive control — the whole-tree, default-scope resolve IS accepted.
    whole_tree = '  resolve --command quality-gate --audit-plan-id {plan_id}'
    assert _default_scope_quality_gate_resolves([whole_tree])


def test_degradation_warning_detector_separates_an_emitted_warning_from_prose():
    # Mutation guard for the dimension-naming sweep. A sibling arm's prose may
    # name this arm while describing its own single-dimension warning; holding
    # that sentence to this arm's dimension-naming rule would demand a false
    # claim of it. Only a warning the gate EMITS carries the obligation.
    sibling_prose = (
        'this project exposes no `test-compile` target at any scope: emit one '
        '`[WARNING]` naming the test-tree type-checking dimension as un-gated '
        "for this push, exactly as the whole-tree `quality-gate` arm's "
        'honest-degradation branch does for its own dimension set.'
    )
    assert _WHOLE_TREE_QUALITY_GATE.search(sibling_prose), (
        'Fixture drift: the sibling-arm prose no longer names the whole-tree '
        'quality-gate arm, so it no longer exercises the discrimination'
    )
    assert not _is_emitted_warning(sibling_prose), (
        'Emitted-warning detector accepted prose that merely mentions a '
        'WARNING — a cross-reference is not an emitted warning'
    )

    # Positive control — the arm's own emitted warning IS selected.
    emitted = (
        '  --message "[WARNING] (plan-marshall:pre-push-quality-gate) Whole-tree '
        'quality-gate unavailable — three whole-tree-only dimensions are UN-GATED."'
    )
    assert _is_emitted_warning(emitted)
    assert _WHOLE_TREE_QUALITY_GATE.search(emitted)


def test_whole_tree_arm_detector_fires_on_the_pre_fix_bundle_only_prose():
    # Mutation guard for the lock-step sweep: the pre-fix sites described guard
    # 1 as bundle-scoped only, with no whole-tree arm.
    pre_fix_sites = [
        'description: Run quality-gate per affected bundle, then whole-tree '
        'test-compile, then gate whole-tree module-tests on scoped-vs-whole-tree '
        'divergence risk, as the last gate before push',
        '**Branch A — all bundles green AND test-compile green AND module-tests '
        'gate green**:',
        '  --display-detail "quality-gate green for {N} bundle(s), test-compile '
        'green, module-tests gate green" \\',
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
            f'Whole-tree-arm detector failed to reject a known pre-fix '
            f'bundle-only site: {site!r}'
        )

    # Positive control — the post-fix Branch A condition IS accepted.
    post_fix = (
        '**Branch A — all bundles green AND whole-tree quality-gate green AND '
        'test-compile green AND module-tests gate green**:'
    )
    assert _WHOLE_TREE_QUALITY_GATE.search(post_fix)
