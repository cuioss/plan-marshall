#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings."""


from _findings_store_fixtures import _SCRIPTS_DIR

# =============================================================================
# Test: resolve_qgate_findings_by_evidence (D3 — self-review loop-back resolution)
#
# A loop-back that lands a fix transitions the corresponding finding; a finding
# with no evidenced fix is left alone. Both directions are asserted — the second
# is the important one: a finding marked `fixed` without a landed change touching
# its file is strictly worse than one left `pending`.
# =============================================================================

def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: the module docstring's
    Storage block and the ``get_findings_dir`` / ``get_findings_path`` /
    ``get_qgate_path`` / ``get_assessments_path`` docstrings must spell the
    findings location as ``.plan/local/plans/`` — the legacy bare
    ``.plan/plans/`` form is incorrect since runtime state moved under
    ``.plan/local``.
    """
    import re

    source = (_SCRIPTS_DIR / '_findings_core.py').read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'
