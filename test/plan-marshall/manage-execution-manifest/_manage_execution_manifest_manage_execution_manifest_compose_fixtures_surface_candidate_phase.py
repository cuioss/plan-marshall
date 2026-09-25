#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _mem, contextlib

# =============================================================================
# Pre-Filter: security_class_inactive (security-class finalize-step gate)
#
# finalize-step-security-audit is a candidate by default (it sits in
# DEFAULT_PHASE_6_STEPS) and belongs to the security class by declaring the
# frontmatter scalar ``persona: persona-security-expert``. The
# security_class_inactive pre-filter is NOT the peer of simplify_inactive: it
# shares no helper, and it reads NO change_type. It drops a security-class step
# only when affected_files_count == 0 AND the live footprint is empty — the
# genuine no-change-surface case. Everything else keeps the sweep, because
# change_type — even reconciled to the plan's settled classification — is
# orthogonal to the security surface: a bug_fix or feature plan can equally touch
# security-sensitive code, so the sweep gates on the change surface, not the type.
#
# The live footprint is stubbed per test so the assertions do not depend on
# ambient worktree state.
#
# See standards/decision-rules.md § Pre-Filter: security_class_inactive.
# =============================================================================


@contextlib.contextmanager
def _pinned_footprint(paths: list[str]):
    """Pin ``_resolve_footprint`` to a fixed path list for the duration of a compose."""
    original = _mem._resolve_footprint
    _mem._resolve_footprint = lambda plan_id: list(paths)
    try:
        yield
    finally:
        _mem._resolve_footprint = original
