# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the examined-analysis population that gates green-build auto-resolve.

The defect these pin: a green build cleared every ``build-error`` and
``lint-issue`` finding regardless of what it examined, so a ``./pw compile`` run
resolved a 129-item ``plugin-doctor`` record — four times — while its own
resolution detail recorded ``0 test(s) executed``.

Every guard here carries a MATCHED PAIR. A refusal test that passes because the
guard fired is indistinguishable from one that passes because the guard refuses
everything, so each negative half is stated beside a positive half that must
disagree with it. The finding-type map is additionally asserted TOTAL over its own
population, so a newly-added finding type cannot acquire an implicit empty
analysis set — which would read as "no analysis is required" and clear on every
build, silently reinstating the defect.
"""

import _build_examined as examined


class TestUnknownIsNotEmpty:
    """The population's two "nothing to go on" states are distinct VALUES.

    They behave alike (both clear nothing) but they say different things, and the
    published reason has to be able to tell them apart — a refusal that cannot
    name its cause is the same opaque signal this module replaces.
    """

    def test_unrecognised_command_yields_unknown(self):
        assert examined.examined_analyses('publish-artifacts core') is None

    def test_recognised_command_yields_a_measured_set(self):
        # The matched positive: the SAME resolver, on a command it knows, returns
        # a real set — so the None above is a property of the command, not of a
        # resolver that always declines.
        assert examined.examined_analyses('compile plan-marshall') == frozenset({'compile'})

    def test_blank_and_missing_command_args_yield_unknown(self):
        assert examined.examined_analyses(None) is None
        assert examined.examined_analyses('') is None
        assert examined.examined_analyses('   ') is None

    def test_scope_tokens_do_not_change_which_analyses_ran(self):
        # Trailing tokens are scope, not analysis selection: a module-scoped gate
        # performs the same KINDS of analysis over less code.
        assert examined.examined_analyses('quality-gate') == examined.examined_analyses(
            'quality-gate pm-plugin-development'
        )

    def test_clean_is_absent_rather_than_mapped_to_empty(self):
        # `clean verify` is a real chain whose later goals do work, so recording
        # `clean` as a measured "examined nothing" would publish a false
        # measurement. Absent means unknown, which is the honest verdict.
        assert 'clean' not in examined.CANONICAL_ANALYSES
        assert examined.examined_analyses('clean verify') is None


class TestCompileCannotClearALintIssue:
    """The reproduced defect, and the control that proves the fix discriminates."""

    def test_compile_run_does_not_entitle_clearing_a_lint_issue(self):
        # NEGATIVE — finding 23fa96's exact conditions: a green `compile` run.
        analyses = examined.examined_analyses('compile pm-plugin-development')
        tests_run = examined.resolve_tests_run(analyses, None)

        clearable = examined.clearable_finding_types(analyses, tests_run)

        assert 'lint-issue' not in clearable
        assert clearable == ('build-error',)

    def test_quality_gate_run_does_entitle_clearing_a_lint_issue(self):
        # POSITIVE — the discriminator. The same finding type, the same helper,
        # a build class that CAN evaluate the lint dimension: it clears. Without
        # this half the negative above is satisfied by a blanket disable.
        analyses = examined.examined_analyses('quality-gate pm-plugin-development')
        tests_run = examined.resolve_tests_run(analyses, None)

        clearable = examined.clearable_finding_types(analyses, tests_run)

        assert 'lint-issue' in clearable

    def test_unknown_population_entitles_nothing_at_all(self):
        assert examined.clearable_finding_types(None, None) == ()
        assert examined.clearable_finding_types(None, 500) == ()

    def test_measured_empty_population_entitles_nothing_at_all(self):
        assert examined.clearable_finding_types(frozenset(), 0) == ()


class TestTestFailureNeedsAMeasuredNonZeroCount:
    """``test-failure`` keeps the stronger requirement, now unknown-aware."""

    def test_measured_non_zero_count_clears_test_failure(self):
        analyses = examined.examined_analyses('module-tests plan-marshall')
        assert examined.clearable_finding_types(analyses, 2750) == ('test-failure',)

    def test_measured_zero_count_does_not_clear_test_failure(self):
        analyses = examined.examined_analyses('module-tests plan-marshall')
        assert examined.clearable_finding_types(analyses, 0) == ()

    def test_unknown_count_does_not_clear_test_failure(self):
        # The daemon-routed case: the gate DOES run tests, but the count could
        # not be read. Unknown must refuse exactly as a measured zero does — and
        # must be reported differently.
        analyses = examined.examined_analyses('module-tests plan-marshall')
        assert examined.clearable_finding_types(analyses, None) == ()
        assert examined.refusal_reason(analyses, None) == 'tests_unmeasured'
        assert examined.refusal_reason(analyses, 0) == 'tests_executed_zero'

    def test_verify_clears_every_type_when_tests_were_measured(self):
        analyses = examined.examined_analyses('verify plan-marshall')
        clearable = examined.clearable_finding_types(analyses, 7)
        assert set(clearable) == set(examined.BUILD_FINDING_TYPES)

    def test_verify_clears_all_but_test_failure_when_the_count_is_unknown(self):
        # The matched half of the row above: the SAME command, the same green,
        # only the count's measurability differs — and only `test-failure` moves.
        analyses = examined.examined_analyses('verify plan-marshall')
        clearable = examined.clearable_finding_types(analyses, None)
        assert set(clearable) == set(examined.BUILD_FINDING_TYPES) - {'test-failure'}


class TestResolveTestsRunKeepsZeroAndUnknownApart:
    """A zero is published only when it was genuinely measured."""

    def test_parsed_total_is_authoritative_whatever_it_says(self):
        analyses = examined.examined_analyses('module-tests plan-marshall')
        assert examined.resolve_tests_run(analyses, 2750) == 2750
        assert examined.resolve_tests_run(analyses, 0) == 0

    def test_non_test_gate_with_no_summary_genuinely_ran_zero(self):
        analyses = examined.examined_analyses('quality-gate plan-marshall')
        assert examined.resolve_tests_run(analyses, None) == 0

    def test_test_gate_with_no_summary_is_unknown_not_zero(self):
        analyses = examined.examined_analyses('module-tests plan-marshall')
        assert examined.resolve_tests_run(analyses, None) is None

    def test_unknown_analyses_make_an_absent_summary_unknown(self):
        assert examined.resolve_tests_run(None, None) is None


class TestMapsArePopulationDerived:
    """Guards over a set must be derived from that set, not written beside it."""

    def test_finding_type_map_is_total_over_the_finding_type_population(self):
        # The population is non-empty, so this cannot pass vacuously.
        assert examined.BUILD_FINDING_TYPES
        assert set(examined.FINDING_TYPE_ANALYSES) == set(examined.BUILD_FINDING_TYPES)

    def test_no_finding_type_carries_an_empty_analysis_set(self):
        # An empty set would intersect nothing and clear on no build; the
        # dangerous direction is a type ADDED without a mapping, which the
        # totality assertion above catches. This pins the other end.
        for finding_type, analyses in examined.FINDING_TYPE_ANALYSES.items():
            assert analyses, finding_type

    def test_every_canonical_maps_only_to_declared_analysis_kinds(self):
        declared = {examined.ANALYSIS_COMPILE, examined.ANALYSIS_LINT, examined.ANALYSIS_TEST}
        assert examined.CANONICAL_ANALYSES
        for canonical, analyses in examined.CANONICAL_ANALYSES.items():
            assert analyses <= declared, canonical

    def test_every_finding_type_is_reachable_from_some_canonical(self):
        # A type whose required analyses no canonical command produces could
        # never be cleared by any build — an un-askable question rather than a
        # strict guard.
        reachable: set[str] = set()
        for analyses in examined.CANONICAL_ANALYSES.values():
            reachable |= analyses
        for finding_type, required in examined.FINDING_TYPE_ANALYSES.items():
            assert required & reachable, finding_type


class TestRefusalReasonNamesItsCause:
    """Every refusal path is reachable and reports a distinct cause."""

    def test_no_reason_when_something_is_clearable(self):
        analyses = examined.examined_analyses('quality-gate')
        assert examined.refusal_reason(analyses, 0) is None

    def test_unknown_population(self):
        assert examined.refusal_reason(None, None) == 'population_unknown'

    def test_measured_empty_population(self):
        assert examined.refusal_reason(frozenset(), 0) == 'population_empty'

    def test_analysis_that_reaches_no_finding_type(self):
        # Reachable over the function's declared domain (an arbitrary analysis
        # set), which is what makes this a live branch rather than dead code: a
        # future analysis kind with no finding type mapped to it lands here.
        assert (
            examined.refusal_reason(frozenset({'provenance-audit'}), 0)
            == 'no_analysis_reaches_a_finding_type'
        )


class TestPopulationLabelPublishesWhatWasExamined:
    """The label is stamped into every resolution detail, so it must be legible."""

    def test_unknown_renders_as_the_word_not_as_a_zero(self):
        label = examined.population_label(None, None)
        assert 'analyses examined: unknown' in label
        assert 'unknown test(s) executed' in label

    def test_measured_population_renders_its_members_and_count(self):
        analyses = examined.examined_analyses('verify')
        label = examined.population_label(analyses, 2750)
        assert 'compile, lint, test' in label
        assert '2750 test(s) executed' in label

    def test_measured_empty_analysis_set_renders_as_none(self):
        assert 'analyses examined: none' in examined.population_label(frozenset(), 0)
