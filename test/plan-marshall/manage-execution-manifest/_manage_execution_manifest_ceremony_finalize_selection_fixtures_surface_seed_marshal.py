#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import _mem


def _stub_footprint(footprint: list[str] | None) -> None:
    """Stub the footprint seams so activation pre-filters see the given state.

    Two seams resolve the live footprint independently: the composer's own
    ``_mem._resolve_footprint`` (the canonical-verify pre-filter, the
    security-class gate and the build-verdict assertion) and
    ``extension_base._resolve_plan_footprint`` (via ``should_execute_build``,
    which the pre-push-quality-gate pre-filter delegates to). Stub BOTH so the
    test state drives every activation decision, and keep them in lock-step —
    they are symmetric peers that must never disagree about the same worktree.

    ``footprint`` carries the resolvers' three-state return verbatim: ``None``
    (unresolvable — no evidence), ``[]`` (resolvable and genuinely empty), or a
    non-empty path list.
    """
    import extension_base

    def _resolve(_plan_id):
        return None if footprint is None else list(footprint)

    _mem._resolve_footprint = _resolve
    extension_base._resolve_plan_footprint = _resolve
