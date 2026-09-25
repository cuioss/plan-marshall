# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _role_of,
    cmd_compose,
    pytest,
    read_manifest,
)

# =============================================================================
# Role-loader and role-based intersection
#
# The composer derives a phase-5 candidate step's ``role:`` purely in-code from
# the trailing ``{canonical}`` segment of its ``verify:{canonical}`` step ID via
# ``_role_of`` (the ``_CANONICAL_TO_ROLE`` table) and uses the role for
# intersection in Rows 2, 3, 4, and 5 of the decision matrix. The tests below cover:
#
# (a) role-loader correctness for each canonical-verify step ID (and the
#     negative cases: external steps, unknown canonicals, retired fixed-name IDs)
# (b) Row 5 intersection produces the expected non-empty list when project
#     candidates carry the canonical-verify step IDs (e.g., ``verify:quality-gate``,
#     ``verify:module-tests``)
# (c) decision-log line shape (the canonical Rule N fired line) is byte-
#     identical to its pre-refactor form for at least one Row 5 fixture
# =============================================================================


class TestRoleLoader:
    """``_role_of`` resolves a phase-5 canonical-verify step ID to its derived role.

    Resolution is purely in-code via the ``_CANONICAL_TO_ROLE`` table, keyed on
    the trailing ``{canonical}`` segment of a ``verify:{canonical}`` step ID — no
    per-step role-file is read. The legacy fixed-name IDs (``quality_check`` /
    ``build_verify`` / ``coverage_check``) are gone and now resolve to None.
    """

    #: (step id, the role it resolves to). ``None`` means the id carries no derived
    #: role at all, which is how external steps, retired fixed-name ids, and
    #: unrecognised canonicals must all behave.
    CANONICAL_ROLES = [
        ('verify:quality-gate', 'quality-gate'),
        ('verify:module-tests', 'module-tests'),
        ('verify:coverage', 'coverage'),
        ('default:verify:quality-gate', 'quality-gate'),
        ('quality_check', None),
        ('build_verify', None),
        ('coverage_check', None),
        ('project:finalize-step-plugin-doctor', None),
        ('my-bundle:my-verify-step', None),
        ('verify:does-not-exist', None),
    ]

    @pytest.mark.parametrize(
        ('step_id', 'role'),
        CANONICAL_ROLES,
        ids=[f'{s}-resolves-to-{r}' for s, r in CANONICAL_ROLES],
    )
    def test_step_id_resolves_to_its_role(self, step_id, role):
        """Each step id resolves to its derived role, or to None when it has none.

        The `default:` prefix is stripped before lookup, so the prefixed and bare
        forms of a canonical must agree. A None row is the load-bearing half: an
        id that gained a role by accident would silently join a verification
        intersection it does not belong in.
        """
        cache: dict[str, str | None] = {}

        resolved = _role_of(step_id, cache)

        if role is None:
            # identity, not equality: None is a singleton sentinel, and `==` would
            # admit any object whose __eq__ returns True against it.
            assert resolved is None
        else:
            assert resolved == role

    def test_cache_returns_same_value_on_second_lookup(self):
        """The per-compose cache short-circuits the second call for the same step."""
        cache: dict[str, str | None] = {}
        first = _role_of('verify:quality-gate', cache)
        # Mutate cache to a sentinel — second call MUST observe the cached value,
        # not re-derive the role.
        cache['verify:quality-gate'] = 'mutated-sentinel'
        second = _role_of('verify:quality-gate', cache)
        assert first == 'quality-gate'
        assert second == 'mutated-sentinel'



class TestRoleBasedIntersection:
    """Rows 2, 4, and 5 intersect by ``role:`` rather than by literal step ID."""

    def test_row_5_surgical_bug_fix_with_built_in_candidates_produces_non_empty_phase_5(self, plan_context):
        """Row 5 + canonical-verify candidate IDs → both quality-gate and module-tests retained.

        Pins the regression: before this refactor the composer compared
        candidate IDs against literal {'quality-gate', 'module-tests'}, which
        never matched the step IDs callers actually pass. Role-based intersection
        derives each candidate's role from its ``verify:{canonical}`` segment and
        matches against `{quality-gate, module-tests}`.
        """
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-5-bug',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=1,
                phase_5_steps='verify:quality-gate,verify:module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('role-row-5-bug')
        assert manifest is not None
        # Both candidates derive roles in {quality-gate, module-tests} →
        # both survive the intersection.
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']

    def test_row_5_surgical_tech_debt_with_prefixed_built_in_candidates_produces_non_empty_phase_5(self, plan_context):
        """Row 5 + ``default:``-prefixed canonical-verify IDs → boundary normalized + roles match.

        Exercises the joint contract of boundary normalization (the existing
        `canonicalize_step_key` pass at intake) and role derivation: prefixed
        candidates lose the prefix at cmd_compose intake, then role lookup
        derives the role from each bare ``verify:{canonical}`` segment.
        """
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-5-tech-prefixed',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='default:verify:quality-gate,default:verify:module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
        manifest = read_manifest('role-row-5-tech-prefixed')
        assert manifest is not None
        # Boundary normalization strips `default:`; role intersection
        # then matches both bare step IDs.
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']

    def test_row_5_drops_coverage_role_from_phase_5(self, plan_context):
        """Row 5's role set is {quality-gate, module-tests} — coverage role is dropped."""
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-5-drop-coverage',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=1,
                phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('role-row-5-drop-coverage')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']
        assert 'verify:coverage' not in manifest['phase_5']['verification_steps']

    def test_row_5_drops_external_step_without_role(self, plan_context):
        """External (project: / bundle:skill) candidates have no role → dropped by intersection."""
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-5-drop-external',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=1,
                phase_5_steps='verify:quality-gate,project:my-verify-step,verify:module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('role-row-5-drop-external')
        assert manifest is not None
        # External step has no role → dropped; canonical-verify steps survive.
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']

    def test_row_4_tests_only_matches_only_module_tests_role(self, plan_context):
        """Row 4's role set is {module-tests} — only verify:module-tests (role: module-tests) survives."""
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-4',
                change_type='verification',
                scope_estimate='single_module',
                affected_files_count=4,
                phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage',
            )
        )
        assert result is not None and result['rule_fired'] == 'tests_only'
        manifest = read_manifest('role-row-4')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == ['verify:module-tests']

    def test_absent_module_tests_role_no_longer_diverts_the_matrix(self, plan_context):
        """A candidate set without a module-tests / coverage role takes the ordinary path.

        The retired ``docs_only`` row treated the ABSENCE of those roles as proof
        the plan was docs-only and emptied phase 5. The role intersection is a
        mechanism for selecting steps, never evidence about the footprint, so the
        row is gone: the same input now reaches the scope row and keeps its
        ``quality-gate`` candidate.
        """
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-3-docs',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=3,
                # Only verify:quality-gate (role: quality-gate) — no module-tests / coverage role.
                phase_5_steps='verify:quality-gate',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
        manifest = read_manifest('role-row-3-docs')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate']

    def test_same_row_fires_whether_or_not_a_module_tests_role_is_present(self, plan_context):
        """Presence or absence of a module-tests role selects the SAME row now.

        Under the retired row these two inputs diverged (``docs_only`` vs the
        scope row) on nothing but the candidate list's composition. The rule key
        must now be identical — only the selected step list differs.
        """
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-3-skip',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=3,
                phase_5_steps='verify:quality-gate,verify:module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
        manifest = read_manifest('role-row-3-skip')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == [
            'verify:quality-gate',
            'verify:module-tests',
        ]
