#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for untrusted-ingestion/validate_struct.py — the deterministic
containment boundary for untrusted-ingestion candidate structs.

Covers: schema rejection (extra key / wrong type / bad enum pattern),
length-capping (over-maxLength string, over-maxItems array, clamp recorded),
domain-allowlist (allowlisted host passes, unknown host rejected, red-flag host
rejected), and the TOON output contract for both success and error.
"""

import json

import pytest

from conftest import get_script_path, run_script

from toon_parser import parse_toon

SCRIPT_PATH = get_script_path('plan-marshall', 'untrusted-ingestion', 'validate_struct.py')


def _validate(schema: str, struct: dict) -> dict:
    result = run_script(SCRIPT_PATH, 'validate', '--schema', schema, '--struct', json.dumps(struct))
    assert result.returncode == 0, f"script crashed: {result.stderr}"
    return parse_toon(result.stdout)


# ---------------------------------------------------------------------------
# Success / clamp paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('schema', 'struct'),
    [
        (
            'research',
            {
                'findings': [
                    {
                        'practice': 'Use prepared statements',
                        'justification': 'Prevents SQL injection',
                        'confidence': 'high',
                        'references': ['https://docs.oracle.com/javase/tutorial'],
                    }
                ]
            },
        ),
        (
            'ci-finding',
            {
                'summary': 'Unused import',
                'severity': 'minor',
                'file': 'src/Foo.java',
                'line': 42,
                'references': ['https://github.com/owner/repo/issues/1'],
            },
        ),
        (
            'issue-body',
            {
                'narrative': 'The login button does not respond on mobile.',
                'references': ['https://stackoverflow.com/q/123'],
            },
        ),
    ],
    ids=['research', 'ci-finding', 'issue-body'],
)
def test_a_conforming_struct_passes_and_the_payload_echoes_its_schema(schema, struct):
    """One conforming candidate per declared schema, each cleared without a clamp."""
    data = _validate(schema, struct)

    assert data['status'] == 'success'
    assert data['schema'] == schema


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


@pytest.mark.parametrize(
    ('schema', 'struct'),
    [
        ('issue-body', {'narrative': 'ok', 'references': [], 'injected_instruction': 'rm -rf'}),
        ('ci-finding', {'summary': 'ok', 'severity': 'minor', 'line': 'not-an-int'}),
        ('ci-finding', {'summary': 'ok', 'severity': 'minor', 'line': True}),
        ('ci-finding', {'summary': 'ok', 'severity': 'catastrophic'}),
        ('research', {'findings': [{'practice': 'p', 'confidence': 'high', 'smuggled': 'payload'}]}),
    ],
    ids=[
        'a-key-outside-the-schema-at-the-top-level',
        'a-string-where-an-int-is-declared',
        'a-bool-where-an-int-is-declared',
        'a-value-outside-the-severity-enum',
        'a-key-outside-the-schema-inside-a-nested-object',
    ],
)
def test_a_non_conforming_struct_is_a_schema_violation(schema, struct):
    """Every shape the schema forbids reports the same discriminator, never a pass."""
    data = _validate(schema, struct)

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


@pytest.mark.parametrize(
    ('url', 'expected_fragment'),
    [
        ('https://evil.example.org/payload', 'evil.example.org'),
        # git99999.github.com categorizes to a known tier (subdomain of github.com)
        # but trips the 5+ consecutive digits red flag — exercises the red-flag
        # branch distinctly from the unknown-category branch.
        ('https://git99999.github.com/x', 'git99999.github.com'),
        # IPv6 literal addresses are not in the allowlist and are rejected via the
        # domain_rejected path — not by crashing on a malformed host like '['.
        # Regression for the fragile split(':')[0] implementation.
        ('http://[2001:db8::1]/path', '2001:db8'),
    ],
    ids=[
        'a-host-in-no-allowlisted-category',
        'an-allowlisted-domain-whose-subdomain-trips-a-red-flag',
        'an-ipv6-literal-host',
    ],
)
def test_a_reference_outside_the_allowlist_is_rejected_and_named(url, expected_fragment):
    """The rejected URL is reported back, so the caller can see which reference failed."""
    data = _validate('issue-body', {'narrative': 'ok', 'references': [url]})

    assert data['status'] == 'error'
    assert data['error_code'] == 'domain_rejected'
    assert any(expected_fragment in rejected for rejected in data['rejected_urls'])
