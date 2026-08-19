#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Tests for the ``aggregate`` subcommand of manage-lessons.py.
"""


from pathlib import Path
from unittest.mock import patch

from _aggregate_fixtures import (
    MARKETPLACE_BUNDLES_PATH,
    _derive_standards_dir,
    _make_lessons_dir,
    _mod,
    _run_aggregate,
    _seed_lesson,
)

# =============================================================================
# Case (a) — grouping by shared component
# =============================================================================


class TestGroupByComponent:
    """Two lessons that share a component (and have no cross-refs) form one
    multi-member group keyed at the shared-component tier — case (a).
    """

    def test_two_lessons_same_component_form_one_group(self, tmp_path):
        """Two lessons declaring the same ``component=`` value form one group;
        absorbed-row reasons cite the shared component.
        """
        lessons_dir = _make_lessons_dir(tmp_path)
        # No cross-refs in the bodies — only the shared component links them.
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-001',
            'Lesson Alpha',
            component='plan-marshall:phase-5-execute',
            body='Alpha body, no refs.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-002',
            'Lesson Beta',
            component='plan-marshall:phase-5-execute',
            body='Beta body, no refs.\n',
        )

        result = _run_aggregate(tmp_path)

        assert result['status'] == 'success'
        assert len(result['groups']) == 1
        group = result['groups'][0]
        assert group['absorb_count'] == 1
        # The shared-component tier is NOT enacted (only cross-ref enacts).
        assert group['tier'] == 'shared-component'
        assert group['enacted'] is False
        # Both lesson ids appear (one as primary, one absorbed)
        absorbed_ids = {row['lesson_id'] for row in group['absorbed']}
        assert {group['primary_id']} | absorbed_ids == {
            '2025-01-01-01-001',
            '2025-01-01-01-002',
        }
        # Reason cites the shared component
        for row in group['absorbed']:
            assert row['reason'] == 'shared component plan-marshall:phase-5-execute'

    def test_singleton_component_dropped(self, tmp_path):
        """Lessons whose component is unique form a singleton group and MUST
        be dropped from the output.
        """
        lessons_dir = _make_lessons_dir(tmp_path)
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-010',
            'Solo Lesson',
            component='plan-marshall:unique-skill',
            body='Solo body.\n',
        )

        result = _run_aggregate(tmp_path)

        assert result['status'] == 'success'
        assert result['groups'] == []
        assert result['top_n_commands'] == []


# =============================================================================
# Case (b) — grouping by shared standards directory
# =============================================================================


class TestGroupByStandardsDir:
    """Lessons whose components map to the same ``standards_dir`` form a
    shared-standards-dir group when no stronger tier links them — case (b).

    The standards_dir is derived from ``component`` as
    ``{bundles_root}/{bundle}/skills/{skill}/standards/`` where ``bundles_root``
    is resolved through the cache-aware ``find_marketplace_path`` resolver (see
    ``TestDeriveStandardsDirResolverPath`` below for the direct resolver-path
    coverage). Two lessons with the SAME component already group at the
    shared-component tier (case a), and ``_derive_standards_dir`` returns the
    empty string for any component value that is not exactly ``{bundle}:{skill}``.
    Lessons that share a standards_dir therefore share a component, so the
    shared-standards-dir tier is unreachable for the bare component shape; it is
    structurally exercised by the workflow-boundary test below, which relies on
    the same fall-through machinery.

    This test validates the tier-fall-through does not spuriously cluster
    unrelated lessons: distinct components that map to distinct standards-dirs
    yield no groups.
    """

    def test_distinct_components_distinct_standards_dirs_yields_no_groups(self, tmp_path):
        """Two lessons with distinct components produce no groups when their
        standards_dirs also differ — confirms the tier-fall-through does not
        spuriously cluster unrelated lessons.
        """
        lessons_dir = _make_lessons_dir(tmp_path)
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-101',
            'Lesson Gamma',
            component='plan-marshall:phase-1-init',
            body='Gamma body.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-102',
            'Lesson Delta',
            component='pm-dev-java:java-core',
            body='Delta body.\n',
        )

        result = _run_aggregate(tmp_path)

        assert result['status'] == 'success'
        assert result['groups'] == []


class TestDeriveStandardsDirResolverPath:
    """``_derive_standards_dir`` resolves the bundles root through the
    cache-aware ``find_marketplace_path`` resolver in script-shared rather than
    a hard-coded ``marketplace/bundles`` literal — the generalization landed in
    the implementation half of this deliverable.

    These tests pin the derivation directly (not through the aggregate verb) so
    they assert the resolver-path invocation and the no-literal-meta-path
    contract precisely:

    - the resolver IS called for a parseable ``{bundle}:{skill}`` component;
    - when the resolver returns a path, the derived dir is anchored on THAT
      path (no hard-coded source-layout assumption);
    - when the resolver returns ``None`` (no bundles tree found), the
      derivation falls back to the relative ``MARKETPLACE_BUNDLES_PATH``
      segment so the value still serves as a deterministic grouping key;
    - unparseable component shapes short-circuit to the empty string WITHOUT
      consulting the resolver.
    """

    def test_resolver_invoked_for_parseable_component(self):
        """A bare ``{bundle}:{skill}`` component triggers exactly one resolver
        call — the derivation no longer hard-codes the bundles root.
        """
        resolved = Path('/anchored/checkout/marketplace/bundles')
        with patch.object(_mod, 'find_marketplace_path', return_value=resolved) as mock_resolver:
            result = _derive_standards_dir('plan-marshall:phase-5-execute')

        mock_resolver.assert_called_once_with()
        assert result == (
            '/anchored/checkout/marketplace/bundles'
            '/plan-marshall/skills/phase-5-execute/standards/'
        )

    def test_derived_dir_anchored_on_resolved_path(self):
        """The derived standards dir is built from the resolver's returned path
        verbatim — a non-source-layout anchor (e.g. a plugin-cache install)
        flows straight through.
        """
        resolved = Path('/home/u/.claude/plugins/cache/pm/marketplace/bundles')
        with patch.object(_mod, 'find_marketplace_path', return_value=resolved):
            result = _derive_standards_dir('pm-dev-java:java-core')

        assert result == (
            '/home/u/.claude/plugins/cache/pm/marketplace/bundles'
            '/pm-dev-java/skills/java-core/standards/'
        )
        # No bare literal meta path is exercised when the resolver returns a path.
        assert not result.startswith(f'{MARKETPLACE_BUNDLES_PATH}/')

    def test_falls_back_to_relative_segment_when_resolver_returns_none(self):
        """When the resolver finds no bundles tree, the derivation falls back to
        the relative ``MARKETPLACE_BUNDLES_PATH`` segment — the value remains a
        deterministic per-component grouping key.
        """
        with patch.object(_mod, 'find_marketplace_path', return_value=None):
            result = _derive_standards_dir('plan-marshall:phase-1-init')

        assert result == (
            f'{MARKETPLACE_BUNDLES_PATH}/plan-marshall/skills/phase-1-init/standards/'
        )

    def test_unparseable_component_skips_resolver(self):
        """Component values that are not exactly ``{bundle}:{skill}`` return the
        empty string and MUST NOT consult the resolver (no wasted resolution).
        """
        with patch.object(_mod, 'find_marketplace_path') as mock_resolver:
            assert _derive_standards_dir('') == ''
            assert _derive_standards_dir('bare-no-colon') == ''
            assert _derive_standards_dir('plan-marshall:phase-5-execute:5') == ''
            assert _derive_standards_dir(':skill') == ''
            assert _derive_standards_dir('bundle:') == ''

        mock_resolver.assert_not_called()

    def test_no_literal_meta_path_when_resolver_diverges(self):
        """Confirms no literal meta path remains exercised: when the resolver
        points at a checkout that is NOT the meta-project source layout, the
        derived dir tracks the resolved location, never a baked-in literal.
        """
        divergent = Path('/some/other/worktree/marketplace/bundles')
        with patch.object(_mod, 'find_marketplace_path', return_value=divergent):
            result = _derive_standards_dir('plan-marshall:manage-lessons')

        assert result.startswith('/some/other/worktree/marketplace/bundles/')
        assert '/plan-marshall/skills/manage-lessons/standards/' in result


class TestGroupByWorkflowBoundary:
    """The shared-workflow-boundary tier is the weakest signal and only fires
    when no stronger signal links the candidate pair.

    With the current ``_derive_workflow_boundary`` rule (drops a trailing
    purely-numeric segment from a 3-segment component), we can construct two
    lessons with components ``a:b:1`` and ``a:b:2`` whose workflow_boundary
    both resolves to ``a:b`` while their component strings differ — so the
    shared-component tier does not fire but the shared-workflow-boundary tier
    does. This is the documented intent: lessons under
    ``plan-marshall:phase-5-execute:5`` and ``plan-marshall:phase-5-execute:6``
    are workflow-adjacent.
    """

    def test_three_segment_components_share_workflow_boundary(self, tmp_path):
        """Two lessons whose components differ only in trailing numeric segment
        cluster at the shared-workflow-boundary tier.
        """
        lessons_dir = _make_lessons_dir(tmp_path)
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-201',
            'Boundary One',
            component='plan-marshall:phase-5-execute:5',
            body='Body one.\n',
        )
        _seed_lesson(
            lessons_dir,
            '2025-01-01-01-202',
            'Boundary Two',
            component='plan-marshall:phase-5-execute:6',
            body='Body two.\n',
        )

        result = _run_aggregate(tmp_path)

        assert result['status'] == 'success'
        assert len(result['groups']) == 1
        group = result['groups'][0]
        assert group['absorb_count'] == 1
        # Workflow-boundary is the weakest tier and is never enacted.
        assert group['tier'] == 'shared-workflow-boundary'
        assert group['enacted'] is False
        for row in group['absorbed']:
            assert row['reason'] == (
                'shared workflow-boundary plan-marshall:phase-5-execute'
            )
