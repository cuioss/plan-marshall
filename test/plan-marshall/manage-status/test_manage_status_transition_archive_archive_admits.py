# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_manage_status_transition_archive_fixtures import (
    Namespace,
    _seed_finalize_phase_plan,
    _stub_finding_queries,
    cmd_archive,
)


def test_archive_admits_when_no_actionable_finding(plan_context, monkeypatch):
    """POSITIVE control: a clean normal-completion archive proceeds."""
    _stub_finding_queries(monkeypatch, {})
    plan_id = 'finalize-clean-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result['status'] == 'success'
    assert 'archived_to' in result
