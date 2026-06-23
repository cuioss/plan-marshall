#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the multi-domain recipe selection metadata contract.

The built-in "Refactor to Profile Standards" recipe selection flow persists its
choices to ``status.json`` metadata via ``manage-status metadata --set`` and
reads them back via ``--get``. No new persistence script is introduced — the
flow relies entirely on the existing verbatim-string storage of
``manage-status metadata`` (only ``BOOLEAN_METADATA_FIELDS`` are coerced; every
other field, including comma-separated strings, is stored and returned
verbatim).

These tests lock that round-trip contract for the multi-domain field set the
selection flow depends on:

- ``recipe_domains``                       — comma-separated auto-detected domains
- ``recipe_selected_skills__{domain}``     — one field per domain, independent
- ``recipe_profile`` / ``recipe_package_source`` — single values

Each test uses a unique ``plan_id`` (PlanContext isolation) to avoid cross-test
contamination in the shared fixture tree.
"""

import json
from argparse import Namespace

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_cmd_query')

cmd_create = _lifecycle.cmd_create
cmd_metadata = _query.cmd_metadata


def _create_plan(plan_id: str) -> None:
    """Create a minimal plan for metadata round-trip tests."""
    cmd_create(Namespace(plan_id=plan_id, title='Multi-domain recipe', phases='1-init', force=False))


def _set(plan_id: str, field: str, value: str):
    return cmd_metadata(Namespace(plan_id=plan_id, set=True, get=False, field=field, value=value))


def _get(plan_id: str, field: str):
    return cmd_metadata(Namespace(plan_id=plan_id, set=False, get=True, field=field, value=None))


# =============================================================================
# recipe_domains — comma-separated round-trip
# =============================================================================


def test_recipe_domains_comma_separated_round_trips(plan_context):
    """``recipe_domains`` set as a comma-separated string round-trips verbatim."""
    plan_id = 'multidomain-domains-roundtrip'
    _create_plan(plan_id)

    set_result = _set(plan_id, 'recipe_domains', 'java,javascript')
    assert set_result['status'] == 'success'
    assert set_result['value'] == 'java,javascript'

    get_result = _get(plan_id, 'recipe_domains')
    assert get_result['status'] == 'success'
    assert get_result['field'] == 'recipe_domains'
    assert get_result['value'] == 'java,javascript'


def test_recipe_domains_single_domain_round_trips(plan_context):
    """A single auto-detected domain round-trips without a trailing separator."""
    plan_id = 'multidomain-single-domain'
    _create_plan(plan_id)

    _set(plan_id, 'recipe_domains', 'java')
    get_result = _get(plan_id, 'recipe_domains')

    assert get_result['status'] == 'success'
    assert get_result['value'] == 'java'


def test_recipe_domains_stored_as_string_not_coerced(plan_context):
    """``recipe_domains`` is NOT in the boolean allowlist — stored verbatim as str.

    Confirms the comma-separated value is persisted to ``status.json`` as a
    plain string (no JSON parsing, no list coercion). The selection flow relies
    on the value coming back as the exact comma-separated string it wrote.
    """
    plan_id = 'multidomain-string-storage'
    _create_plan(plan_id)

    _set(plan_id, 'recipe_domains', 'java,javascript')

    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    content = json.loads(status_file.read_text(encoding='utf-8'))
    stored = content['metadata']['recipe_domains']
    assert stored == 'java,javascript'
    assert isinstance(stored, str)


# =============================================================================
# recipe_selected_skills__{domain} — independent per-domain fields
# =============================================================================


def test_per_domain_selected_skills_coexist_independently(plan_context):
    """Multiple ``recipe_selected_skills__{domain}`` fields coexist and round-trip
    independently — writing one domain's set does not disturb another's."""
    plan_id = 'multidomain-per-domain-skills'
    _create_plan(plan_id)

    java_skills = 'pm-dev-java:java-core,pm-dev-java:junit-core'
    js_skills = 'pm-dev-frontend:javascript,pm-dev-frontend:jest-testing'

    _set(plan_id, 'recipe_selected_skills__java', java_skills)
    _set(plan_id, 'recipe_selected_skills__javascript', js_skills)

    java_result = _get(plan_id, 'recipe_selected_skills__java')
    js_result = _get(plan_id, 'recipe_selected_skills__javascript')

    assert java_result['status'] == 'success'
    assert java_result['value'] == java_skills
    assert js_result['status'] == 'success'
    assert js_result['value'] == js_skills
    # Cross-check: each field is independent — neither leaked into the other.
    assert java_result['value'] != js_result['value']


def test_per_domain_field_returns_exact_persisted_value(plan_context):
    """``--get`` of a per-domain field returns exactly the persisted
    comma-separated value (no reordering, no whitespace mangling)."""
    plan_id = 'multidomain-exact-value'
    _create_plan(plan_id)

    skills = 'pm-dev-java:java-core,pm-dev-java:java-null-safety,pm-dev-java:junit-core'
    _set(plan_id, 'recipe_selected_skills__java', skills)

    result = _get(plan_id, 'recipe_selected_skills__java')
    assert result['status'] == 'success'
    assert result['value'] == skills


def test_per_domain_field_persisted_as_string(plan_context):
    """A per-domain skills field is persisted to ``status.json`` as a verbatim str."""
    plan_id = 'multidomain-per-domain-storage'
    _create_plan(plan_id)

    skills = 'pm-dev-frontend:javascript,pm-dev-frontend:css'
    _set(plan_id, 'recipe_selected_skills__javascript', skills)

    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    content = json.loads(status_file.read_text(encoding='utf-8'))
    stored = content['metadata']['recipe_selected_skills__javascript']
    assert stored == skills
    assert isinstance(stored, str)


def test_per_domain_field_missing_returns_not_found(plan_context):
    """A ``recipe_selected_skills__{domain}`` field for an unselected domain is
    absent — ``--get`` returns ``not_found`` rather than a spurious value."""
    plan_id = 'multidomain-missing-domain'
    _create_plan(plan_id)

    _set(plan_id, 'recipe_selected_skills__java', 'pm-dev-java:java-core')

    result = _get(plan_id, 'recipe_selected_skills__python')
    assert result['status'] == 'not_found'
    assert result['field'] == 'recipe_selected_skills__python'


# =============================================================================
# recipe_profile / recipe_package_source — single-value round-trip
# =============================================================================


def test_recipe_profile_round_trips(plan_context):
    """``recipe_profile`` round-trips a single value (any profile, not a fixed pair)."""
    plan_id = 'multidomain-profile'
    _create_plan(plan_id)

    _set(plan_id, 'recipe_profile', 'implementation')
    result = _get(plan_id, 'recipe_profile')

    assert result['status'] == 'success'
    assert result['value'] == 'implementation'


def test_recipe_profile_accepts_arbitrary_profile_name(plan_context):
    """The profile set is open — a profile beyond implementation/module_testing
    (e.g. ``documentation``) round-trips identically."""
    plan_id = 'multidomain-arbitrary-profile'
    _create_plan(plan_id)

    _set(plan_id, 'recipe_profile', 'documentation')
    result = _get(plan_id, 'recipe_profile')

    assert result['status'] == 'success'
    assert result['value'] == 'documentation'


def test_recipe_package_source_round_trips(plan_context):
    """``recipe_package_source`` (data-driven from the profile) round-trips."""
    plan_id = 'multidomain-package-source'
    _create_plan(plan_id)

    _set(plan_id, 'recipe_package_source', 'test_packages')
    result = _get(plan_id, 'recipe_package_source')

    assert result['status'] == 'success'
    assert result['value'] == 'test_packages'


# =============================================================================
# Full multi-domain selection set — end-to-end coexistence
# =============================================================================


def test_full_multidomain_field_set_coexists(plan_context):
    """The complete multi-domain selection set the recipe flow persists —
    ``recipe_domains`` + per-domain skills + ``recipe_profile`` +
    ``recipe_package_source`` — coexists in one plan and each field round-trips
    independently of the others."""
    plan_id = 'multidomain-full-set'
    _create_plan(plan_id)

    _set(plan_id, 'recipe_domains', 'java,javascript')
    _set(plan_id, 'recipe_profile', 'implementation')
    _set(plan_id, 'recipe_package_source', 'packages')
    _set(plan_id, 'recipe_selected_skills__java', 'pm-dev-java:java-core')
    _set(plan_id, 'recipe_selected_skills__javascript', 'pm-dev-frontend:javascript')

    assert _get(plan_id, 'recipe_domains')['value'] == 'java,javascript'
    assert _get(plan_id, 'recipe_profile')['value'] == 'implementation'
    assert _get(plan_id, 'recipe_package_source')['value'] == 'packages'
    assert _get(plan_id, 'recipe_selected_skills__java')['value'] == 'pm-dev-java:java-core'
    assert _get(plan_id, 'recipe_selected_skills__javascript')['value'] == 'pm-dev-frontend:javascript'

    # All fields are present together in the persisted metadata block.
    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    metadata = json.loads(status_file.read_text(encoding='utf-8'))['metadata']
    assert {
        'recipe_domains',
        'recipe_profile',
        'recipe_package_source',
        'recipe_selected_skills__java',
        'recipe_selected_skills__javascript',
    } <= set(metadata.keys())
