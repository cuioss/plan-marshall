#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for untrusted-ingestion/validate_struct.py — the deterministic
containment boundary for untrusted-ingestion candidate structs.

Covers: schema rejection (extra key / wrong type / bad enum pattern),
length-capping (over-maxLength string, over-maxItems array, clamp recorded),
domain-allowlist (allowlisted host passes, unknown host rejected, red-flag host
rejected), and the TOON output contract for both success and error.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path, run_script  # type: ignore[import-not-found]  # noqa: E402

from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

SCRIPT_PATH = get_script_path('plan-marshall', 'untrusted-ingestion', 'validate_struct.py')


def _validate(schema: str, struct: dict) -> dict:
    result = run_script(SCRIPT_PATH, 'validate', '--schema', schema, '--struct', json.dumps(struct))
    assert result.returncode == 0, f"script crashed: {result.stderr}"
    return parse_toon(result.stdout)


# ---------------------------------------------------------------------------
# Success / clamp paths
# ---------------------------------------------------------------------------


def test_valid_research_struct_passes():
    struct = {
        'findings': [
            {
                'practice': 'Use prepared statements',
                'justification': 'Prevents SQL injection',
                'confidence': 'high',
                'references': ['https://docs.oracle.com/javase/tutorial'],
            }
        ]
    }
    data = _validate('research', struct)
    assert data['status'] == 'success'
    assert data['schema'] == 'research'


def test_valid_ci_finding_passes():
    struct = {
        'summary': 'Unused import',
        'severity': 'minor',
        'file': 'src/Foo.java',
        'line': 42,
        'references': ['https://github.com/owner/repo/issues/1'],
    }
    data = _validate('ci-finding', struct)
    assert data['status'] == 'success'


def test_valid_issue_body_passes():
    struct = {
        'narrative': 'The login button does not respond on mobile.',
        'references': ['https://stackoverflow.com/q/123'],
    }
    data = _validate('issue-body', struct)
    assert data['status'] == 'success'


def test_over_maxlength_string_is_clamped():
    struct = {
        'narrative': 'x' * 9000,  # issue-body narrative maxLength is 8000
        'references': [],
    }
    data = _validate('issue-body', struct)
    assert data['status'] == 'success'
    # clamp recorded
    assert any('narrative' in entry for entry in data['clamped'])


def test_over_maxitems_array_is_clamped():
    struct = {
        'narrative': 'short',
        'references': ['https://github.com/x'] * 25,  # references maxItems is 20
    }
    data = _validate('issue-body', struct)
    assert data['status'] == 'success'
    assert any('references' in entry for entry in data['clamped'])


def test_no_clamp_records_empty_list():
    struct = {'narrative': 'fits fine', 'references': []}
    data = _validate('issue-body', struct)
    assert data['status'] == 'success'
    assert data['clamped'] == []


# ---------------------------------------------------------------------------
# Schema-rejection paths
# ---------------------------------------------------------------------------


def test_extra_key_rejected_additional_properties_false():
    struct = {'narrative': 'ok', 'references': [], 'injected_instruction': 'rm -rf'}
    data = _validate('issue-body', struct)
    assert data['status'] == 'error'
    assert data['error_code'] == 'schema_violation'


def test_wrong_type_rejected():
    struct = {'summary': 'ok', 'severity': 'minor', 'line': 'not-an-int'}
    data = _validate('ci-finding', struct)
    assert data['status'] == 'error'
    assert data['error_code'] == 'schema_violation'


def test_bool_rejected_where_int_expected():
    struct = {'summary': 'ok', 'severity': 'minor', 'line': True}
    data = _validate('ci-finding', struct)
    assert data['status'] == 'error'
    assert data['error_code'] == 'schema_violation'


def test_bad_enum_pattern_rejected():
    struct = {'summary': 'ok', 'severity': 'catastrophic'}  # not in severity enum
    data = _validate('ci-finding', struct)
    assert data['status'] == 'error'
    assert data['error_code'] == 'schema_violation'


def test_nested_object_extra_key_rejected():
    struct = {
        'findings': [
            {'practice': 'p', 'confidence': 'high', 'smuggled': 'payload'}
        ]
    }
    data = _validate('research', struct)
    assert data['status'] == 'error'
    assert data['error_code'] == 'schema_violation'


def test_non_object_candidate_rejected():
    result = run_script(SCRIPT_PATH, 'validate', '--schema', 'issue-body', '--struct', '["a", "b"]')
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'


def test_unknown_schema_rejected():
    data = _validate('not-a-schema', {})
    assert data['status'] == 'error'
    assert data['error_code'] == 'invalid_input'


def test_malformed_json_struct_rejected():
    result = run_script(SCRIPT_PATH, 'validate', '--schema', 'issue-body', '--struct', '{not json')
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'


# ---------------------------------------------------------------------------
# Domain-allowlist paths
# ---------------------------------------------------------------------------


def test_allowlisted_host_passes():
    struct = {'narrative': 'ok', 'references': ['https://github.com/owner/repo']}
    data = _validate('issue-body', struct)
    assert data['status'] == 'success'


def test_unknown_host_rejected():
    struct = {'narrative': 'ok', 'references': ['https://evil.example.org/payload']}
    data = _validate('issue-body', struct)
    assert data['status'] == 'error'
    assert data['error_code'] == 'domain_rejected'
    assert any('evil.example.org' in url for url in data['rejected_urls'])


def test_red_flag_host_rejected():
    # git99999.github.com categorizes to a known tier (subdomain of github.com)
    # but trips the 5+ consecutive digits red flag — exercises the red-flag branch
    # distinctly from the unknown-category branch.
    struct = {'narrative': 'ok', 'references': ['https://git99999.github.com/x']}
    data = _validate('issue-body', struct)
    assert data['status'] == 'error'
    assert data['error_code'] == 'domain_rejected'


def test_ipv6_url_rejected_as_unknown_host():
    # IPv6 literal addresses are not in the allowlist and should be rejected
    # via the domain_rejected path — not crash with a malformed host like '['.
    # Regression for the fragile split(':')[0] implementation.
    struct = {'narrative': 'ok', 'references': ['http://[2001:db8::1]/path']}
    data = _validate('issue-body', struct)
    assert data['status'] == 'error'
    assert data['error_code'] == 'domain_rejected'
