# ruff: noqa: I001, E402
"""Suite-coverage meta-test — the test-layer replacement for the deleted
runtime ``zero-match-rule`` detector.

The deleted ``_analyze_zero_match_rule.py`` proved "a rule is alive" from a
parallel ``FIXTURE_CORPUS`` that DUPLICATED positive test cases the analyzer
suite already carried. This meta-test reframes the invariant as a TEST-LAYER
suite-coverage property and derives "fired" from running each registered
analyzer over a positive fixture in ``_fixtures.py`` (NOT a live xdist
session-tap):

    registered_rule_ids(MARKETPLACE_ROOT) - fired_rule_ids() - EXEMPT_RULE_IDS == ∅

Where:

- ``registered_rule_ids(root)`` — every audit-tracked rule ID the analyzers
  emit (the same population the provenance audit pins).
- ``fired_rule_ids()`` — the union of rule IDs every fixture in
  ``_fixtures.build_fixture_corpus`` emits when run over its own scratch tree,
  plus the cross-file rules derived from ``crossfile_verified_findings``.
  "Fired" means "fired against its positive fixture".
- ``EXEMPT_RULE_IDS`` — the shrunken, per-entry-justified set of rules that
  structurally cannot fire on a static positive fixture.

A registered rule that is neither fired nor exempt is a real coverage gap: the
assertion message names it so the fix is unambiguous (author a firing fixture
in ``_fixtures.py``, or add a justified exemption here).
"""

from conftest import MARKETPLACE_ROOT

from _fixtures import fired_rule_ids, registered_rule_ids

# ---------------------------------------------------------------------------
# Exempt set — genuinely un-fixturable rules, each with a one-line justification.
# ---------------------------------------------------------------------------
#
# These three rules fire ONLY by deriving a script's live ``--help`` surface
# through a subprocess executor probe (a synthetic ``.plan/execute-script.py``
# shim + notation-map + spawned argparse script per probe). They cannot fire on
# a pure-static positive fixture the way the other registered rules do — their
# firing mechanism is a subprocess-driven ``--help`` derivation, not a static
# analyzer pass over fixture files.
EXEMPT_RULE_IDS: frozenset[str] = frozenset(
    {
        # Validates documented invocations against each script's live --help
        # surface (derive_script_tree spawns the executor per notation).
        'manage-invocation-invalid',
        # Paired with manage-invocation-invalid in the same --help-derivation
        # analyzer (_analyze_manage_invocation); fires for an in-scope SKILL.md
        # whose Canonical-invocations block is absent, gated behind the same
        # subprocess surface derivation.
        'missing-canonical-block',
        # Probes --help via subprocess for every documented notation/verb pair
        # against the live executor (analyze_script_call_drift calls _run_help).
        'script-call-drift',
        # Intermediate routing tag only — never an emitted finding's rule_id.
        # _doctor_analysis.analyze_subdocuments tags a display-detail subdoc
        # issue with this literal, but extract_issues_from_subdoc_analysis
        # remaps it to the concrete DISPLAY_DETAIL_* code before emission, so no
        # analyze_component finding ever carries this id (it is registered only
        # via the intermediate string literal).
        'subdoc-display-detail-violation',
    }
)


def test_zero_match_suite_coverage():
    """Every non-exempt registered rule fires against its positive fixture.

    The build-failing invariant: ``registered - fired - EXEMPT == ∅``. A
    non-empty gap means a registered rule has no firing positive fixture in
    ``_fixtures.py`` and is not justified-exempt — write the fixture (preferred)
    or add a justified ``EXEMPT_RULE_IDS`` entry.
    """
    registered = registered_rule_ids(MARKETPLACE_ROOT)
    fired = fired_rule_ids()

    uncovered = sorted(registered - fired - EXEMPT_RULE_IDS)

    assert not uncovered, (
        'Registered plugin-doctor rules with no firing positive fixture and no '
        f'justified exemption: {uncovered}\n'
        'For each: author a firing fixture in '
        'test/pm-plugin-development/plugin-doctor/_fixtures.py '
        '(build_fixture_corpus), or — only if the rule structurally cannot fire '
        'on a static positive fixture — add a per-entry-justified EXEMPT_RULE_IDS '
        'entry here.'
    )


def test_exempt_rule_ids_are_all_registered():
    """Every EXEMPT entry must be a real registered rule (no stale exemptions).

    A stale or misspelled exemption for a deleted or non-existent rule fails
    here and forces a prune — the mechanical abuse-governance guard so the
    exempt set cannot silently rot or accrete unregistered entries.
    """
    registered = registered_rule_ids(MARKETPLACE_ROOT)

    unregistered = sorted(EXEMPT_RULE_IDS - registered)

    assert not unregistered, (
        f'EXEMPT_RULE_IDS contains entries that are not registered rules: '
        f'{unregistered}\n'
        'Prune the stale/misspelled exemption — an exemption for a deleted or '
        'non-existent rule masks coverage and must not persist.'
    )
