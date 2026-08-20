#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``findings store`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Unit tests for _findings_core.py - the storage engine for findings and Q-Gate findings.
"""


from conftest import get_scripts_dir, load_script_module

# Retained for the source-introspection test that reads _findings_core.py text.
_SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'manage-findings')


_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')


QGATE_PERSIST_OK = _findings_core.QGATE_PERSIST_OK


add_finding = _findings_core.add_finding


add_qgate_finding = _findings_core.add_qgate_finding


add_qgate_finding_checked = _findings_core.add_qgate_finding_checked


clear_qgate_findings = _findings_core.clear_qgate_findings


get_finding = _findings_core.get_finding


mark_finding_responded = _findings_core.mark_finding_responded


promote_finding = _findings_core.promote_finding


query_findings = _findings_core.query_findings


query_findings_unified = _findings_core.query_findings_unified


query_qgate_findings = _findings_core.query_qgate_findings


resolve_finding = _findings_core.resolve_finding


resolve_findings_by_type = _findings_core.resolve_findings_by_type


resolve_qgate_finding = _findings_core.resolve_qgate_finding


resolve_qgate_findings_by_evidence = _findings_core.resolve_qgate_findings_by_evidence


# =============================================================================
# Test: QGATE_PERSIST_OK — the published persist-outcome partition
# =============================================================================
#
# Every observed status is DERIVED by driving the primitive to produce it,
# never restated as a literal in the test — so the partition is checked against
# the primitive's real outcomes and cannot drift into agreeing with a stale copy
# of the vocabulary.


def _observed_qgate_statuses(plan_id: str) -> dict[str, str]:
    """Drive ``add_qgate_finding`` to produce each of its four real outcomes.

    Returns ``{outcome_name: observed_status}`` where every value came back from
    a real call — ``success`` (fresh append), ``deduplicated`` (identical pending
    record), ``reopened`` (matching resolved record) and ``error`` (a finding type
    outside ``FINDING_TYPES``, the live rejection mode).
    """
    fresh = add_qgate_finding(plan_id, '5-execute', 'qgate', 'build-error', 'Partition probe', 'Detail')
    dedup = add_qgate_finding(plan_id, '5-execute', 'qgate', 'build-error', 'Partition probe', 'Detail')

    resolved = add_qgate_finding(plan_id, '5-execute', 'qgate', 'build-error', 'Reopen probe', 'Detail')
    resolve_qgate_finding(plan_id, '5-execute', resolved['hash_id'], 'fixed')
    reopened = add_qgate_finding(plan_id, '5-execute', 'qgate', 'build-error', 'Reopen probe', 'Detail')

    rejected = add_qgate_finding(plan_id, '5-execute', 'qgate', 'not-a-finding-type', 'Rejected probe', 'Detail')

    return {
        'fresh': fresh['status'],
        'dedup': dedup['status'],
        'reopened': reopened['status'],
        'rejected': rejected['status'],
    }
