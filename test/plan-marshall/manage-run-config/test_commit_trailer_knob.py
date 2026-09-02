#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the commit-trailer subcommand group of manage-run-config.

Covers the commit_trailer knob:
- The default identity when the section is absent
- Independent per-half fallback, with the source of each half reported rather
  than left to be inferred from the value
- get/set round-trips that persist the commit_trailer object
- Rejection of values that would break the trailer line's own grammar
- The feature-defining input shape (a name carrying a space, an address
  carrying an @) driven through the CLI entry point
- Help wiring for the new subcommands

Mirrors the conventions of test_display_timezone_knob.py.
"""

import json

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')

DEFAULT_NAME = 'plan-marshall'
DEFAULT_EMAIL = 'noreply@cuioss.de'
DEFAULT_TRAILER = f'Co-Authored-By: {DEFAULT_NAME} <{DEFAULT_EMAIL}>'


def _write_config(plan_context, commit_trailer) -> None:
    """Persist a run-configuration carrying ``commit_trailer`` for one test."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'run-configuration.json').write_text(
        json.dumps({'version': 1, 'commands': {}, 'commit_trailer': commit_trailer})
    )


# =============================================================================
# get — default, persisted, and per-half source reporting
# =============================================================================


def test_get_defaults_to_plan_marshall_when_absent(plan_context):
    """get returns the plan-marshall identity on a project with no config file."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'commit-trailer', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('name') == DEFAULT_NAME
    assert data.get('email') == DEFAULT_EMAIL
    assert data.get('trailer') == DEFAULT_TRAILER


def test_get_names_no_vendor_identity_by_default(plan_context):
    """The default trailer names the system, not the assistant or its vendor."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'commit-trailer', 'get')

    trailer = result.toon().get('trailer', '').lower()
    assert 'claude' not in trailer
    assert 'anthropic' not in trailer


def test_get_reads_persisted_identity(plan_context):
    """get returns the persisted identity when both halves are stored."""
    _write_config(plan_context, {'name': 'my-system', 'email': 'bot@example.org'})

    result = run_script(SCRIPT_PATH, 'commit-trailer', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data.get('name') == 'my-system'
    assert data.get('email') == 'bot@example.org'
    assert data.get('trailer') == 'Co-Authored-By: my-system <bot@example.org>'


def test_get_reports_source_of_each_half_independently(plan_context):
    """A configured name beside a default email is reported as exactly that."""
    _write_config(plan_context, {'name': 'my-system'})

    result = run_script(SCRIPT_PATH, 'commit-trailer', 'get')

    data = result.toon()
    assert data.get('name') == 'my-system'
    assert data.get('name_source') == 'configured'
    assert data.get('email') == DEFAULT_EMAIL
    assert data.get('email_source') == 'default'


def test_get_reports_both_sources_as_default_when_absent(plan_context):
    """The unset state is distinguishable from an override matching the default.

    Negative control for the source fields: a value equal to the default must
    still report ``default``, or the source field would carry no signal.
    """
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'commit-trailer', 'get')

    data = result.toon()
    assert data.get('name_source') == 'default'
    assert data.get('email_source') == 'default'


def test_get_reports_configured_when_override_equals_default(plan_context):
    """Matched positive control: an explicit value equal to the default is `configured`."""
    _write_config(plan_context, {'name': DEFAULT_NAME, 'email': DEFAULT_EMAIL})

    result = run_script(SCRIPT_PATH, 'commit-trailer', 'get')

    data = result.toon()
    assert data.get('name_source') == 'configured'
    assert data.get('email_source') == 'configured'


# =============================================================================
# get — malformed stored values degrade to the default
# =============================================================================


def test_get_treats_empty_stored_name_as_absent(plan_context):
    """An empty stored half falls back rather than emitting an empty identity."""
    _write_config(plan_context, {'name': '   ', 'email': 'bot@example.org'})

    data = run_script(SCRIPT_PATH, 'commit-trailer', 'get').toon()

    assert data.get('name') == DEFAULT_NAME
    assert data.get('name_source') == 'default'


def test_get_treats_non_string_stored_half_as_absent(plan_context):
    """A wrong-typed stored half falls back instead of rendering a repr."""
    _write_config(plan_context, {'name': 42, 'email': 'bot@example.org'})

    data = run_script(SCRIPT_PATH, 'commit-trailer', 'get').toon()

    assert data.get('name') == DEFAULT_NAME
    assert data.get('name_source') == 'default'


def test_get_treats_angle_bracket_in_stored_name_as_absent(plan_context):
    """A stored value that would break the trailer grammar is not emitted."""
    _write_config(plan_context, {'name': 'evil <injected>', 'email': 'bot@example.org'})

    data = run_script(SCRIPT_PATH, 'commit-trailer', 'get').toon()

    assert data.get('name') == DEFAULT_NAME
    assert data.get('trailer') == f'Co-Authored-By: {DEFAULT_NAME} <bot@example.org>'


def test_get_treats_non_object_section_as_absent(plan_context):
    """A commit_trailer that is not an object degrades to the full default."""
    _write_config(plan_context, 'plan-marshall')

    data = run_script(SCRIPT_PATH, 'commit-trailer', 'get').toon()

    assert data.get('trailer') == DEFAULT_TRAILER


# =============================================================================
# set — round-trip, partial writes, and validation
# =============================================================================


def test_set_round_trips_both_halves(plan_context):
    """set persists both halves and a subsequent get reads them back."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    written = run_script(
        SCRIPT_PATH, 'commit-trailer', 'set', '--name', 'my system', '--email', 'bot@example.org'
    )

    assert written.success, f'Should succeed: {written.stderr}'
    data = run_script(SCRIPT_PATH, 'commit-trailer', 'get').toon()
    assert data.get('trailer') == 'Co-Authored-By: my system <bot@example.org>'


def test_set_email_alone_preserves_a_configured_name(plan_context):
    """Setting one half does not discard the other."""
    _write_config(plan_context, {'name': 'my-system', 'email': 'old@example.org'})

    run_script(SCRIPT_PATH, 'commit-trailer', 'set', '--email', 'new@example.org')

    data = run_script(SCRIPT_PATH, 'commit-trailer', 'get').toon()
    assert data.get('name') == 'my-system'
    assert data.get('email') == 'new@example.org'


def test_set_requires_at_least_one_half(plan_context):
    """set with neither flag is rejected rather than silently writing nothing."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    data = run_script(SCRIPT_PATH, 'commit-trailer', 'set').toon()

    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_value'


def test_set_rejects_angle_bracket_and_persists_nothing(plan_context):
    """A grammar-breaking name is rejected and leaves the stored value untouched."""
    _write_config(plan_context, {'name': 'my-system', 'email': 'bot@example.org'})

    data = run_script(SCRIPT_PATH, 'commit-trailer', 'set', '--name', 'evil <x>').toon()

    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_value'
    assert run_script(SCRIPT_PATH, 'commit-trailer', 'get').toon().get('name') == 'my-system'


def test_set_rejects_address_without_at_sign(plan_context):
    """An address with no @ is rejected — it could never resolve to an account."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    data = run_script(SCRIPT_PATH, 'commit-trailer', 'set', '--email', 'not-an-address').toon()

    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_value'


def test_set_rejects_empty_name(plan_context):
    """A whitespace-only name is rejected rather than stored."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    data = run_script(SCRIPT_PATH, 'commit-trailer', 'set', '--name', '   ').toon()

    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_value'


# =============================================================================
# CLI wiring
# =============================================================================


def test_commit_trailer_help_lists_subcommands():
    """--help exposes both sub-verbs of the group."""
    result = run_script(SCRIPT_PATH, 'commit-trailer', '--help')

    assert result.success
    assert 'get' in result.stdout
    assert 'set' in result.stdout


def test_commit_trailer_set_help_lists_flags():
    """set --help advertises both identity flags."""
    result = run_script(SCRIPT_PATH, 'commit-trailer', 'set', '--help')

    assert result.success
    assert '--name' in result.stdout
    assert '--email' in result.stdout
