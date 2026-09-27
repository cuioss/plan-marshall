# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_refire_report_fixtures import SCRIPT_PATH, run_script


def test_cli_roundtrip_reports_file_not_found_for_a_missing_manifest(plan_context):
    """CLI plumbing: the verb is reachable through the executor entry point."""
    result = run_script(SCRIPT_PATH, 'refire-report', '--plan-id', 'no-such-plan')

    assert 'file_not_found' in result.stdout
