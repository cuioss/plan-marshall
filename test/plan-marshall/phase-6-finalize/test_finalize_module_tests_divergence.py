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

#: The three quality-gate dimensions ONLY whole-tree scope reaches. A
#: degradation WARNING naming fewer than all three is a partial-truth signal.
_WHOLE_TREE_ONLY_DIMENSIONS = ('plugin-doctor', '.claude/', 'marketplace/targets')

#: Guard 1's whole-tree arm, as the ADJACENT phrase "whole-tree quality-gate"
#: (tolerating only markdown emphasis/backtick noise between the two words).
#: Adjacency is load-bearing: a mere-proximity match would be satisfied by the
#: pre-fix prose, where "whole-tree" belongs to test-compile or module-tests and
#: never to quality-gate — which is exactly the drift this sweep must catch. So
#: every lock-step site spells the arm as one adjacent phrase.
_WHOLE_TREE_QUALITY_GATE = re.compile(
    r'whole-tree[\s`*_]{0,4}quality-gate', re.IGNORECASE
)

#: The whole-tree (no bundle argument) quality-gate invocation.
_WHOLE_TREE_QG_INVOCATION = re.compile(r'run --command-args "quality-gate"')

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
# Three quality-gate dimensions exist ONLY at whole-tree scope (the
# marketplace-wide plugin-doctor pass, the `.claude/` ruff coverage, and the
# `marketplace/targets` SPDX coverage). A purely bundle-scoped guard 1 can never
# reach them, so they surface first at remote CI. These tests pin that guard 1
# carries a whole-tree arm, that any skip path degrades honestly by naming all
# three dimensions, and that the lock-step sites describing the guard set cannot
# drift apart one site at a time.


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


def _names_all_three_dimensions(text: str) -> bool:
    return all(dimension in text for dimension in _WHOLE_TREE_ONLY_DIMENSIONS)


def _degradation_warning_lines() -> list[str]:
    """Return the WARNING lines covering the whole-tree quality-gate skip path."""
    return [
        line
        for line in _gate_text().splitlines()
        if '[WARNING]' in line and _WHOLE_TREE_QUALITY_GATE.search(line)
    ]


def test_whole_tree_quality_gate_pass_is_reachable_from_the_gate_document():
    text = _gate_text()

    assert _WHOLE_TREE_QG_INVOCATION.search(text), (
        'The gate document must carry a whole-tree (no bundle argument) '
        'quality-gate invocation — without it the three whole-tree-only '
        'dimensions are unreachable from the pre-push gate'
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


def test_degradation_warning_names_all_three_dimensions():
    warnings = _degradation_warning_lines()

    assert warnings, (
        'The gate document must carry an honest-degradation WARNING for the '
        'whole-tree quality-gate skip path — a silent skip is prohibited'
    )
    for warning in warnings:
        assert _names_all_three_dimensions(warning), (
            f'A whole-tree quality-gate degradation WARNING must name ALL '
            f'THREE un-gated dimensions {_WHOLE_TREE_ONLY_DIMENSIONS} — never a '
            f'singular "the whole-tree dimension". Offending line: {warning!r}'
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
