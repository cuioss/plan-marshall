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
    disclosure = [line for line in text.splitlines() if '[WARNING]' in line and 'unresolved_paths' in line]
    assert disclosure, (
        'The gate document must emit a [WARNING] naming the unresolved paths — '
        'a parsed-but-undisclosed field is a silent drop (ADR-014)'
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

    uncovered = [item for item in items if not any(d in item for d in _WHOLE_TREE_ONLY_DIMENSIONS)]
    assert not uncovered, (
        f'These enumerated dimensions are matched by no token in '
        f'{_WHOLE_TREE_ONLY_DIMENSIONS}, so the worked example could omit them '
        f'while every sweep stayed green: {uncovered}'
    )


def test_no_module_tests_degradation_variant_claims_the_arm_is_green():
    """A degraded arm is never reported green — the deliverable's load-bearing property.

    The population is DERIVED from the gate document's own payloads, so a variant
    added later for a fourth non-run path is swept without editing this file.

    ⛔ The forbidden shape is the ARM-SPECIFIC claim
    (:data:`_FORBIDDEN_GREEN_CLAIM`), not the word "green" anywhere in the payload.
    A blanket ban would condemn the same variants the gate document sanctions: each
    of them reports the arms that DID run as green in the same breath as naming the
    one that did not, and the document's rule is that a variant contains "green"
    for no dimension it did not gate. Banning the word outright would also delete
    real outcome from the step record — the reader would lose which arms passed —
    which is the completeness floor traded away for a simpler predicate.
    """
    payloads = _module_tests_degradation_payloads()

    assert payloads, (
        f'No documented display_detail payload reports a non-run module-tests arm '
        f'(looked for {_MODULE_TESTS_DEGRADATION_TOKENS}), so every module-tests '
        f'degradation path reaches Branch A with only its default string — the exact '
        f'misreport this sweep exists to prevent, and it would pass vacuously'
    )

    claiming_green = [payload for payload in payloads if _FORBIDDEN_GREEN_CLAIM in payload]

    assert not claiming_green, (
        f'These degradation payload(s) report the module-tests arm as green while '
        f'naming it as not run — a step record that contradicts itself, and the one '
        f'a consumer reads instead of the work log: {claiming_green}'
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

    stale = [name for name, body in sites.items() if not _WHOLE_TREE_QUALITY_GATE.search(body)]

    assert not stale, (
        f'Lock-step drift: these sites describe the guard set without naming '
        f"guard 1's whole-tree arm, so one site was updated and another left "
        f'stale: {sorted(stale)}'
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
