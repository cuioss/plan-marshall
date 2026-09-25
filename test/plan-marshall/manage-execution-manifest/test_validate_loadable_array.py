# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_validate_loadable_fixtures import (
    _compose_ns,
    _mem,
    _validate_loadable_ns,
    cmd_compose,
    cmd_validate_loadable,
)

# =============================================================================
# Array-authority contract (--all) — composed array is authoritative for order
# =============================================================================
#
# D4 array-authority contract: once the manifest is composed, ``phase_6.steps``
# is the authoritative execution order. The ``--all`` path therefore does NOT
# re-assert ascending order against each step's frontmatter ``order:`` — only
# standards-file loadability is a hard error here. The ascending-order guard
# lives exclusively on the pre-composition SEED path (``--check-seed``, below).
# The order-resolution helpers (``_resolve_step_order``, ``_check_ascending_order``)
# are retained because ``--check-seed`` still consumes them.


class TestArrayAuthorityContract:
    def test_in_order_phase_6_steps_pass(self, plan_context):
        """An --all manifest whose steps are in ascending order returns success."""
        cmd_compose(_compose_ns('vl-order-ok'))
        manifest = _mem.read_manifest('vl-order-ok')
        assert manifest is not None
        # Built-in steps in ascending order (push=11, create-pr=20)
        # followed by project steps in ascending order (81, 85).
        manifest['phase_6']['steps'] = [
            'push',
            'create-pr',
            'project:finalize-step-deploy-target',
            'project:finalize-step-sync-plugin-cache',
        ]
        _mem.write_manifest('vl-order-ok', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-order-ok', use_all=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['unloadable_count'] == 0
        assert 'error' not in result

    def test_frontmatter_array_disagreement_does_not_fail(self, plan_context):
        """Per D4, a composed array whose order disagrees with frontmatter still passes.

        The legacy guard returned ``order_inversion`` here. Under the array-authority
        contract the composed ``phase_6.steps`` array is authoritative, so the same
        out-of-frontmatter-order manifest now returns ``status: success`` with no
        order error — only loadability is a hard error on the ``--all`` path.
        """
        cmd_compose(_compose_ns('vl-order-disagree'))
        manifest = _mem.read_manifest('vl-order-disagree')
        assert manifest is not None
        # Frontmatter order would call this an inversion: sync-plugin-cache (85)
        # precedes deploy-target (81). The array says this is the intended order.
        manifest['phase_6']['steps'] = [
            'push',
            'project:finalize-step-sync-plugin-cache',
            'project:finalize-step-deploy-target',
        ]
        _mem.write_manifest('vl-order-disagree', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-order-disagree', use_all=True))
        assert result is not None
        # No order_inversion error — the array is authoritative.
        assert result['status'] == 'success'
        assert 'error' not in result
        assert 'order_inversion' not in result.values()
        # All steps load, so unloadable_count is zero and results is the full walk.
        assert result['unloadable_count'] == 0
        assert isinstance(result['results'], list)
        assert len(result['results']) == 3

    def test_project_step_order_resolves_from_project_local_skill_md(self):
        """project: step order is read from .claude/skills/{name}/SKILL.md frontmatter.

        deploy-target sits at order 81 and sync-plugin-cache at 85. The
        consumer-shipped built-in default:finalize-step-preference-emitter now
        sits post-merge at order 992 (the post-run-review band), so the former
        deploy-target-vs-preference-emitter deconfliction that once explained the
        81 value no longer applies — the two steps no longer share a
        neighbourhood in the order space."""
        assert _mem._resolve_step_order('project:finalize-step-deploy-target') == 81
        assert _mem._resolve_step_order('project:finalize-step-sync-plugin-cache') == 85

    def test_builtin_step_order_resolves_from_standards_frontmatter(self):
        """Built-in step order is read from its standards/workflow doc frontmatter."""
        assert _mem._resolve_step_order('push') == 11
        assert _mem._resolve_step_order('default:push') == 11
        assert _mem._resolve_step_order('create-pr') == 20

    def test_all_path_reports_only_loadability_not_order(self, plan_context):
        """The --all walk surfaces unloadable steps but never an order error.

        Mixes resolvable-order steps, an unresolvable-order bundle:skill step, and
        a ghost step (no standards file). The ghost step is unloadable, but that is
        a loadability concern; the array is authoritative for order, so no order
        check runs and status stays success on the strength of loadability alone.
        """
        # _resolve_step_order returns None for a non-existent step and for a
        # bundle:skill external step (no project-local SKILL.md).
        assert _mem._resolve_step_order('ghost-step-not-on-disk') is None
        assert _mem._resolve_step_order('plan-marshall:plan-retrospective') is None

        cmd_compose(_compose_ns('vl-order-skip'))
        manifest = _mem.read_manifest('vl-order-skip')
        assert manifest is not None
        manifest['phase_6']['steps'] = [
            'push',
            'plan-marshall:plan-retrospective',
            'project:finalize-step-deploy-target',
            'ghost-step-not-on-disk',
            'project:finalize-step-sync-plugin-cache',
        ]
        _mem.write_manifest('vl-order-skip', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-order-skip', use_all=True))
        assert result is not None
        # The ghost step is unloadable (no standards file); status stays success
        # only because loadability is the sole hard error on the --all path —
        # order is never checked against frontmatter under the array-authority
        # contract.
        assert result['status'] == 'success'
        assert 'error' not in result
        assert result['unloadable_count'] == 1

    def test_single_step_id_path_reports_no_order_error(self, plan_context):
        """--step-id reports loadability only; no order error on any path now."""
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-order-single', step_id='project:finalize-step-sync-plugin-cache')
        )
        assert result is not None
        assert result['status'] == 'success'
        assert result['loadable'] is True
        # No order_inversion error on the single-step path.
        assert result.get('error') != 'order_inversion'

    def test_check_ascending_order_helper_returns_none_for_ascending(self):
        """The _check_ascending_order helper returns None for an ascending list."""
        assert _mem._check_ascending_order(['push', 'create-pr']) is None

    def test_check_ascending_order_helper_detects_inversion(self):
        """The _check_ascending_order helper returns a diagnostic for an inversion."""
        message = _mem._check_ascending_order(['create-pr', 'push'])
        assert message is not None
        assert 'push' in message
        assert 'create-pr' in message
