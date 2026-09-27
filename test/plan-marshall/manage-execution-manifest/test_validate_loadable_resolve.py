# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_validate_loadable_fixtures import _mem


class TestResolveStepOrderVerdict:
    """The tri-state resolver distinguishes ORDERLESS from UNRESOLVABLE."""

    def test_resolved_builtin_returns_order_and_resolved_verdict(self):
        assert _mem._resolve_step_order_verdict('push') == (11, _mem._ORDER_RESOLVED)

    def test_resolved_builtin_accepts_default_prefix(self):
        assert _mem._resolve_step_order_verdict('default:push') == (11, _mem._ORDER_RESOLVED)

    def test_resolved_project_step(self):
        order, verdict = _mem._resolve_step_order_verdict('project:finalize-step-deploy-target')
        assert (order, verdict) == (81, _mem._ORDER_RESOLVED)

    def test_missing_source_file_is_source_unresolvable(self):
        order, verdict = _mem._resolve_step_order_verdict('ghost-step-that-does-not-exist')
        assert order is None
        assert verdict == _mem._ORDER_SOURCE_UNRESOLVABLE

    def test_bundle_skill_step_is_not_applicable(self):
        # A bundle:skill step has no project-local source BY DESIGN — orderless
        # legitimately, so it must not be conflated with an unresolvable one.
        order, verdict = _mem._resolve_step_order_verdict('plan-marshall:plan-retrospective')
        assert order is None
        assert verdict == _mem._ORDER_NOT_APPLICABLE

    def test_source_without_order_key_is_not_declared(self, monkeypatch):
        # The reachable trigger: the source file EXISTS (so the resolution gate
        # passes it) but declares no readable integer `order:`.
        import _manifest_validation as _mv

        monkeypatch.setattr(_mv, '_read_frontmatter_order', lambda path: None)
        order, verdict = _mv._resolve_step_order_verdict('push')
        assert order is None
        assert verdict == _mv._ORDER_NOT_DECLARED

    def test_resolve_step_order_is_the_order_only_projection(self):
        # The legacy accessor keeps its int|None contract for the sort and the
        # seed-path check.
        assert _mem._resolve_step_order('push') == 11
        assert _mem._resolve_step_order('ghost-step-that-does-not-exist') is None
        assert _mem._resolve_step_order('plan-marshall:plan-retrospective') is None
