#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _mem


def _stub_footprint(footprint: list[str] | None) -> None:
    """Stub the footprint seams so the activation pre-filters see the given state.

    The compose pre-filters derive the live plan footprint on demand instead of
    reading a seeded ``references.modified_files`` ledger. Two distinct seams are
    in play: the composer's own ``_mem._resolve_footprint`` (read by the
    canonical-verify pre-filter, the security-class gate and the build-verdict
    assertion), and ``extension_base._resolve_plan_footprint`` (read by
    ``should_execute_build``, which the pre-push-quality-gate pre-filter
    delegates to). Both are replaced so the injected state drives every
    activation decision, and both are kept in lock-step because they are
    symmetric peers that must never disagree about the same worktree.

    ``footprint`` carries the resolvers' THREE-state return verbatim: ``None``
    (unresolvable — no evidence), ``[]`` (resolvable and genuinely empty), or a
    non-empty path list. ``None`` is deliberately NOT collapsed into ``[]`` here;
    collapsing the two is the defect the split fixes. The
    ``TestPrePushQualityGatePreFilter`` autouse fixture restores both after each
    test.
    """
    import extension_base

    def _resolve(_plan_id):
        return None if footprint is None else list(footprint)

    _mem._resolve_footprint = _resolve
    extension_base._resolve_plan_footprint = _resolve
