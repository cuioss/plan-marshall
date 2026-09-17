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


def test_gate_document_names_all_three_whole_tree_only_dimensions():
    text = _gate_text()

    missing = [d for d in _WHOLE_TREE_ONLY_DIMENSIONS if d not in text]

    assert not missing, (
        f'The gate document must name every whole-tree-only quality-gate '
        f'dimension so a reader knows what the arm exists to reach. '
        f'Missing: {missing}'
    )


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
            f"The emitted WARNING pins this repository's dimension names "
            f'{pinned} instead of interpolating the derived set — the literal '
            f'is what a downstream agent copies. Offending line: {warning!r}'
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


def test_module_tests_degradation_token_floor_covers_every_declared_variant():
    """The hand-maintained token floor must cover every variant the document declares.

    :data:`_MODULE_TESTS_DEGRADATION_TOKENS` is a floor, not a derivation, so
    nothing mechanically keeps it in step with the gate document. This guards
    the gap directly: the document's OWN "Detail variant — module-tests ..."
    headings are counted independently of the tuple, then compared against how
    many payloads the tuple actually covers (`_module_tests_degradation_payloads`).
    A degradation variant added under a spelling the tuple does not name would
    grow the heading count without growing the covered-payload count, so this
    assertion fails loudly instead of the sweep above silently passing over it.
    """
    declared_variant_count = len(_MODULE_TESTS_DETAIL_VARIANT_HEADING.findall(_gate_text()))
    covered_payload_count = len(_module_tests_degradation_payloads())

    assert declared_variant_count == covered_payload_count, (
        f'The gate document declares {declared_variant_count} "module-tests" detail '
        f'variant(s) but {_MODULE_TESTS_DEGRADATION_TOKENS!r} only covers '
        f'{covered_payload_count} payload(s) — a variant was added under a spelling '
        f'this floor does not name. Add the new spelling to '
        f'_MODULE_TESTS_DEGRADATION_TOKENS.'
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

    assert not incomplete, f'Lock-step drift: these sites omit guards from the guard set {_GUARD_TOKENS}: {incomplete}'


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
