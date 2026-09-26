# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _mem,
    _read_execution_profile,
    _write_marshal_with_ci,
    _write_status_metadata,
    json,
)


def test_read_recipe_source_unit(plan_context):
    """Direct unit coverage of the status-metadata provenance surrogate."""
    read_recipe_source = _mem._read_recipe_source

    # No status.json → None.
    assert read_recipe_source('rrs-missing') is None

    # plan_source wins over recipe_key; whitespace trimmed.
    _write_status_metadata(
        plan_context, 'rrs-both', {'plan_source': '  2026-06-02-08-002  ', 'recipe_key': 'lesson_cleanup'}
    )
    assert read_recipe_source('rrs-both') == '2026-06-02-08-002'

    # recipe_key fallback when plan_source absent.
    _write_status_metadata(plan_context, 'rrs-key', {'recipe_key': 'lesson_cleanup'})
    assert read_recipe_source('rrs-key') == 'lesson_cleanup'

    # Empty / blank provenance values are treated as absent.
    _write_status_metadata(plan_context, 'rrs-blank', {'plan_source': '   ', 'recipe_key': ''})
    assert read_recipe_source('rrs-blank') is None


def test_read_recipe_source_malformed_status_degrades_to_none(plan_context):
    """A corrupt-but-present status.json degrades to None instead of crashing."""
    plan_dir = plan_context.plan_dir_for('rrs-malformed')
    (plan_dir / 'status.json').write_text('{ this is not: valid json', encoding='utf-8')
    assert _mem._read_recipe_source('rrs-malformed') is None


# =============================================================================
# _read_ci_provider — direct regression coverage for the dissolved ci block
# (D3 — ci.provider read-path removal)
#
# The legacy ``ci.provider`` short-identifier read-path is gone. The provider
# is now resolved exclusively from the ``providers[]`` entry whose
# ``category == 'ci'``. These tests pin that contract directly against
# ``_read_ci_provider`` (rather than only end-to-end through the guard).
# =============================================================================


def test_read_ci_provider_resolves_github_from_providers_no_ci_block(plan_context):
    """``providers[]`` github entry resolves to 'github' with NO ci block present."""
    _write_marshal_with_ci(plan_context.fixture_dir, provider='github')
    assert _mem._read_ci_provider() == 'github'


def test_read_ci_provider_resolves_gitlab_from_providers_no_ci_block(plan_context):
    """``providers[]`` gitlab entry resolves to 'gitlab' with NO ci block present."""
    _write_marshal_with_ci(plan_context.fixture_dir, provider='gitlab')
    assert _mem._read_ci_provider() == 'gitlab'


def test_read_ci_provider_ignores_legacy_ci_provider_block(plan_context):
    """A stale ``ci.provider`` block alone resolves to None — the read-path is removed.

    Before D3, ``ci.provider`` was a first-match-wins source. After dissolution
    the composer ignores the ``ci`` block entirely; only ``providers[]`` is
    consulted. A marshal.json carrying ONLY the legacy block must resolve to
    None so a stale field can never silently re-activate the guard.
    """
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps({'ci': {'provider': 'github'}}), encoding='utf-8')
    assert _mem._read_ci_provider() is None


def test_read_ci_provider_returns_none_when_no_providers(plan_context):
    """No ``providers[]`` and no ci block -> None (the no-CI baseline)."""
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps({'plan': {'phase-6-finalize': {}}}), encoding='utf-8')
    assert _mem._read_ci_provider() is None


def test_read_execution_profile_defaults_full_when_absent(plan_context):
    """_read_execution_profile returns full when status.json is absent."""
    assert _read_execution_profile('no-such-plan') == 'full'


def test_read_execution_profile_reads_persisted_posture(plan_context):
    """_read_execution_profile returns the persisted status.metadata.execution_profile."""
    _write_status_metadata(plan_context, 'lane-read-posture', {'execution_profile': 'minimal'})
    assert _read_execution_profile('lane-read-posture') == 'minimal'
