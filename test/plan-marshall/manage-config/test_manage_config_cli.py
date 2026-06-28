#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process tests for the ``manage-config.py`` ``main()`` CLI dispatcher.

The existing manage-config suite exercises the per-noun ``cmd_*`` handlers
directly via ``Namespace(...)`` objects, which leaves the argparse parser
construction and the noun -> handler routing block in ``manage-config.py``
``main()`` entirely uncovered. These tests drive ``main()`` itself by patching
``sys.argv`` and catching the ``SystemExit`` raised by the ``@safe_main``
wrapper, asserting that each noun routes to the correct handler and that the
handler's real output reaches stdout as TOON.

``main()`` reads ``sys.argv`` (via ``parse_args_with_toon_errors``), so the
in-process invocation patches ``sys.argv`` rather than passing argv. The
``@safe_main`` wrapper turns the int return into ``sys.exit(<rc>)``: a
successful route exits 0 (the TOON — including a handler ``status: error`` —
is on stdout); an argparse rejection exits 2 with usage on stderr.

Isolation: the autouse ``_plan_base_dir_sandbox`` plus the explicit
``plan_context`` fixture redirect ``_config_core.MARSHAL_PATH`` into a per-test
tmp sandbox, so every seed/write lands in the sandbox, never the real
``.plan/`` tree.
"""

import sys

import pytest
from test_helpers import create_marshal_json, create_nested_marshal_json
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import load_script_module

# Loaded once per test module under a unique name so it does not clash with the
# other manage-config test modules that load the same source files.
_mc = load_script_module('plan-marshall', 'manage-config', 'manage-config.py', 'mc_cli_under_test')


def _drive(monkeypatch, capsys, *argv):
    """Run ``main()`` in-process with ``argv`` and return ``(code, out, err)``.

    Patches ``sys.argv`` so ``parse_args_with_toon_errors`` sees the requested
    tokens, then calls the ``@safe_main`` wrapper (which always raises
    ``SystemExit``). Returns the exit code plus captured stdout/stderr.
    """
    monkeypatch.setattr(sys, 'argv', ['manage-config.py', *argv])
    with pytest.raises(SystemExit) as exc:
        _mc.main()
    captured = capsys.readouterr()
    code = exc.value.code if exc.value.code is not None else 0
    return code, captured.out, captured.err


# =============================================================================
# Read-only / no-marshal routes
# =============================================================================


def test_main_coverage_expand_routes_and_expands(plan_context, monkeypatch, capsys):
    """`coverage expand` routes to cmd_coverage_expand and emits the cell instruction."""
    code, out, _ = _drive(monkeypatch, capsys, 'coverage', 'expand', '--thoroughness', 'T2', '--scope', 'artifact')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['thoroughness'] == 'T2'
    assert data['scope'] == 'artifact'
    # The composed instruction carries the breadth/depth phrasing from CoveragePresets.
    assert 'Breadth (artifact)' in out
    assert 'Depth (T2)' in out


def test_main_coverage_expand_coupling_violation_is_error(plan_context, monkeypatch, capsys):
    """`coverage expand T4/change-set` returns the coupling-violation error (exit 0, error TOON)."""
    code, out, _ = _drive(monkeypatch, capsys, 'coverage', 'expand', '--thoroughness', 'T4', '--scope', 'change-set')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert 'coverage_coupling_violation' in out


def test_main_aspect_classify_implementation(plan_context, monkeypatch, capsys):
    """`aspect-classify` routes to cmd_aspect_classify; an implementation-heavy request classifies as implementation."""
    code, out, _ = _drive(
        monkeypatch, capsys, 'aspect-classify', '--request-text', 'implement and build and add a new feature'
    )

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['aspect'] == 'implementation'


def test_main_aspect_classify_analysis(plan_context, monkeypatch, capsys):
    """An analysis-dominated request classifies as analysis above the 0.7 threshold."""
    code, out, _ = _drive(
        monkeypatch, capsys, 'aspect-classify', '--request-text', 'analyze audit review investigate'
    )

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['aspect'] == 'analysis'
    assert data['drops_build_steps'] is True


def test_main_recipe_match_routes(plan_context, monkeypatch, capsys):
    """`recipe-match` routes to cmd_recipe_match and returns a scored-matches envelope."""
    code, out, _ = _drive(monkeypatch, capsys, 'recipe-match', '--request-text', 'refactor the codebase to profile standards')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    # Routing-distinctive output keys produced only by cmd_recipe_match.
    assert 'meets_auto_route_threshold' in out
    assert 'recipes_evaluated' in out


def test_main_list_recipes_routes(plan_context, monkeypatch, capsys):
    """`list-recipes` routes to cmd_list_recipes and returns a recipes list."""
    code, out, _ = _drive(monkeypatch, capsys, 'list-recipes')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert 'recipes' in out
    assert 'count' in data


def test_main_list_finalize_steps_routes(plan_context, monkeypatch, capsys):
    """`list-finalize-steps` routes to cmd_list_finalize_steps and surfaces a built-in step."""
    code, out, _ = _drive(monkeypatch, capsys, 'list-finalize-steps')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    # The push step is a built-in finalize step; its presence proves the route.
    assert 'default:push' in out


def test_main_list_verify_steps_routes(plan_context, monkeypatch, capsys):
    """`list-verify-steps` routes to cmd_list_verify_steps and surfaces the canonical verify steps."""
    code, out, _ = _drive(monkeypatch, capsys, 'list-verify-steps')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert 'default:verify:quality-gate' in out


def test_main_resolve_recipe_not_found(plan_context, monkeypatch, capsys):
    """`resolve-recipe` with an unknown key routes to cmd_resolve_recipe and returns not-found."""
    code, out, _ = _drive(monkeypatch, capsys, 'resolve-recipe', '--recipe', 'no-such-recipe-xyz')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert 'Recipe not found' in out


def test_main_domain_detect_plan_not_found(plan_context, monkeypatch, capsys):
    """`domain-detect` for a missing plan routes to cmd_domain_detect and returns plan_dir_not_found."""
    code, out, _ = _drive(monkeypatch, capsys, 'domain-detect', '--plan-id', 'nonexistent-plan-xyz')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert data['error'] == 'plan_dir_not_found'


def test_main_build_decision_requires_plan_id(plan_context, monkeypatch, capsys):
    """`build-decision` without a plan id routes to cmd_build_decision and returns the missing-plan error."""
    code, out, _ = _drive(monkeypatch, capsys, 'build-decision', '--command', 'quality-gate')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert 'requires --plan-id' in out


# =============================================================================
# marshal-seeded routes (flat domain fixture)
# =============================================================================


def test_main_skill_domains_list(plan_context, monkeypatch, capsys):
    """`skill-domains list` routes to cmd_skill_domains and lists configured domains."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'skill-domains', 'list')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert 'java' in out


def test_main_skill_domains_get(plan_context, monkeypatch, capsys):
    """`skill-domains get --domain java` returns that domain's default skills."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'skill-domains', 'get', '--domain', 'java')

    assert code == 0
    assert 'pm-dev-java:java-core' in out


def test_main_system_retention_get(plan_context, monkeypatch, capsys):
    """`system retention get` routes to cmd_system and returns the retention block."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'system', 'retention', 'get')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert 'retention' in out


def test_main_project_get_returns_default_base_branch(plan_context, monkeypatch, capsys):
    """`project get --field default_base_branch` falls back to the canonical default when absent."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'project', 'get', '--field', 'default_base_branch')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['field'] == 'default_base_branch'
    assert data['value'] == 'main'


def test_main_plan_phase_get(plan_context, monkeypatch, capsys):
    """`plan phase-1-init get` routes through cmd_plan -> cmd_phase and echoes the phase key."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'plan', 'phase-1-init', 'get')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['phase'] == 'phase-1-init'


def test_main_ext_defaults_list_empty(plan_context, monkeypatch, capsys):
    """`ext-defaults list` routes to cmd_ext_defaults and reports an empty store on a fresh marshal."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'ext-defaults', 'list')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['count'] == 0


def test_main_ext_defaults_set_then_get_roundtrips(plan_context, monkeypatch, capsys):
    """`ext-defaults set` persists a value that a subsequent `get` returns."""
    create_marshal_json(plan_context.fixture_dir)

    code_set, out_set, _ = _drive(monkeypatch, capsys, 'ext-defaults', 'set', '--key', 'my_key', '--value', 'my_val')
    assert code_set == 0
    assert parse_toon(out_set)['status'] == 'success'

    code_get, out_get, _ = _drive(monkeypatch, capsys, 'ext-defaults', 'get', '--key', 'my_key')
    assert code_get == 0
    data = parse_toon(out_get)
    assert data['status'] == 'success'
    assert data['value'] == 'my_val'


def test_main_normalize_keys(plan_context, monkeypatch, capsys):
    """`normalize-keys` routes to the inline normalize handler and reports the normalized action."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'normalize-keys')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['action'] == 'normalized'


def test_main_sync_defaults(plan_context, monkeypatch, capsys):
    """`sync-defaults` routes to cmd_sync_defaults and reports the count of back-filled keys."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'sync-defaults')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert 'added_count' in data


def test_main_effort_read_default_inherits(plan_context, monkeypatch, capsys):
    """`effort read --default` returns `inherit` when no plan-wide effort is set."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'effort', 'read', '--default')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['level'] == 'inherit'


def test_main_effort_set_then_read_roundtrips(plan_context, monkeypatch, capsys):
    """`effort set --scope plan` persists a plan-wide level that `effort read --default` returns."""
    create_marshal_json(plan_context.fixture_dir)

    code_set, out_set, _ = _drive(monkeypatch, capsys, 'effort', 'set', '--scope', 'plan', '--level', 'level-3')
    assert code_set == 0
    set_data = parse_toon(out_set)
    assert set_data['status'] == 'success'
    assert set_data['target'] == 'plan.effort'

    code_read, out_read, _ = _drive(monkeypatch, capsys, 'effort', 'read', '--default')
    assert code_read == 0
    assert parse_toon(out_read)['level'] == 'level-3'


def test_main_effort_apply_preset(plan_context, monkeypatch, capsys):
    """`effort apply-preset --preset balanced` routes to cmd_effort_apply_preset and writes the preset."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'effort', 'apply-preset', '--preset', 'balanced')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['preset'] == 'balanced'
    assert 'roles_count' in data


def test_main_effort_resolve_target_inherits_canonical(plan_context, monkeypatch, capsys):
    """`effort resolve-target` resolves an unset role to the canonical execution-context target."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'effort', 'resolve-target', '--role', 'phase-1-init')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['target'] == 'execution-context'


def test_main_coverage_read_inherits(plan_context, monkeypatch, capsys):
    """`coverage read --phase` returns the inherit/inherit cell when no coverage is configured."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'coverage', 'read', '--phase', 'phase-5-execute')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['thoroughness'] == 'inherit'
    assert data['scope'] == 'inherit'


def test_main_coverage_resolve_reports_coupling_ok(plan_context, monkeypatch, capsys):
    """`coverage resolve` adds the `coupling: ok` field on a coherent resolved cell."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'coverage', 'resolve', '--phase', 'phase-5-execute')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['coupling'] == 'ok'


def test_main_finalize_steps_apply_preset(plan_context, monkeypatch, capsys):
    """`finalize-steps apply-preset --preset local` routes to the preset writer and reports the step count."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'finalize-steps', 'apply-preset', '--preset', 'local')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['preset'] == 'local'
    assert 'steps_count' in data


def test_main_build_map_read_missing_is_error(plan_context, monkeypatch, capsys):
    """`build-map read` fails closed (status error) when no build.map is seeded."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'build-map', 'read')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'


# =============================================================================
# marshal-seeded routes (nested domain fixture, bundle-backed profiles)
# =============================================================================


def test_main_resolve_domain_skills(plan_context, monkeypatch, capsys):
    """`resolve-domain-skills` resolves the java implementation profile from the bundle extension."""
    create_nested_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(
        monkeypatch, capsys, 'resolve-domain-skills', '--domain', 'java', '--profile', 'implementation'
    )

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['domain'] == 'java'
    assert data['profile'] == 'implementation'


def test_main_resolve_workflow_skill_extension(plan_context, monkeypatch, capsys):
    """`resolve-workflow-skill-extension` returns the registered triage extension for java."""
    create_nested_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(
        monkeypatch, capsys, 'resolve-workflow-skill-extension', '--domain', 'java', '--type', 'triage'
    )

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['extension'] == 'pm-dev-java:ext-triage-java'


def test_main_get_skills_by_profile(plan_context, monkeypatch, capsys):
    """`get-skills-by-profile` returns the per-profile skill grouping for a bundle-backed domain."""
    create_nested_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'get-skills-by-profile', '--domain', 'java')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert 'skills_by_profile' in out


def test_main_resolve_outline_skill_generic_fallback(plan_context, monkeypatch, capsys):
    """`resolve-outline-skill` falls back to the generic source when the domain has no outline_skill key."""
    create_nested_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'resolve-outline-skill', '--domain', 'java')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['source'] == 'generic'
    assert data['skill'] == 'none'


# =============================================================================
# skill-domains active-profiles + flat set (covers cmd_skill_domains branches via main)
# =============================================================================


def test_main_active_profiles_show_not_configured(plan_context, monkeypatch, capsys):
    """`skill-domains active-profiles` with no config reports not_configured."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'skill-domains', 'active-profiles')

    assert code == 0
    assert 'not_configured' in out


def test_main_active_profiles_set_global_then_show(plan_context, monkeypatch, capsys):
    """`active-profiles set` (global) persists profiles that the show view then surfaces."""
    create_marshal_json(plan_context.fixture_dir)

    code_set, out_set, _ = _drive(
        monkeypatch, capsys, 'skill-domains', 'active-profiles', 'set', '--profiles', 'quality,security'
    )
    assert code_set == 0
    set_data = parse_toon(out_set)
    assert set_data['status'] == 'success'
    assert set_data['scope'] == 'global'

    code_show, out_show, _ = _drive(monkeypatch, capsys, 'skill-domains', 'active-profiles')
    assert code_show == 0
    assert 'quality' in out_show
    assert 'security' in out_show


def test_main_active_profiles_set_per_domain(plan_context, monkeypatch, capsys):
    """`active-profiles set --domain` scopes the profiles to a single domain."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(
        monkeypatch, capsys, 'skill-domains', 'active-profiles', 'set', '--profiles', 'testing', '--domain', 'java'
    )

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['scope'] == 'java'


def test_main_active_profiles_set_unknown_domain_errors(plan_context, monkeypatch, capsys):
    """`active-profiles set --domain` rejects a domain that does not exist."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(
        monkeypatch, capsys, 'skill-domains', 'active-profiles', 'set', '--profiles', 'x', '--domain', 'nope'
    )

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'


def test_main_active_profiles_remove_global(plan_context, monkeypatch, capsys):
    """`active-profiles remove` clears the previously-set global profiles."""
    create_marshal_json(plan_context.fixture_dir)
    _drive(monkeypatch, capsys, 'skill-domains', 'active-profiles', 'set', '--profiles', 'quality')

    code, out, _ = _drive(monkeypatch, capsys, 'skill-domains', 'active-profiles', 'remove')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['scope'] == 'global'
    assert data['removed'] is True


def test_main_skill_domains_set_flat_updates_defaults(plan_context, monkeypatch, capsys):
    """`skill-domains set` on a flat domain rewrites its defaults list, observable via get."""
    create_marshal_json(plan_context.fixture_dir)

    code_set, out_set, _ = _drive(
        monkeypatch, capsys, 'skill-domains', 'set', '--domain', 'java', '--defaults', 'pm-dev-java:java-core,pm-dev-java:javadoc'
    )
    assert code_set == 0
    assert parse_toon(out_set)['status'] == 'success'

    code_get, out_get, _ = _drive(monkeypatch, capsys, 'skill-domains', 'get', '--domain', 'java')
    assert code_get == 0
    assert 'pm-dev-java:javadoc' in out_get


# =============================================================================
# init route + argparse rejection paths
# =============================================================================


def test_main_init_already_initialized_errors(plan_context, monkeypatch, capsys):
    """`init` on an already-seeded marshal routes to cmd_init and returns the already-exists guard error."""
    create_marshal_json(plan_context.fixture_dir)

    code, out, _ = _drive(monkeypatch, capsys, 'init')

    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert 'already exists' in out


def test_main_unknown_noun_exits_2(plan_context, monkeypatch, capsys):
    """An unrecognized noun is rejected by argparse with exit code 2."""
    code, _, err = _drive(monkeypatch, capsys, 'bogus-noun-xyz')

    assert code == 2
    assert 'invalid choice' in err or 'usage' in err.lower()


def test_main_no_arguments_exits_2(plan_context, monkeypatch, capsys):
    """Invoking with no noun is rejected by the required-subparser with exit code 2."""
    code, _, err = _drive(monkeypatch, capsys)

    assert code == 2
    assert err  # argparse prints a usage/error message to stderr


def test_main_effort_apply_preset_invalid_exits_2(plan_context, monkeypatch, capsys):
    """An unknown effort preset is rejected at the argparse type-validator layer with exit code 2."""
    create_marshal_json(plan_context.fixture_dir)

    code, _, err = _drive(monkeypatch, capsys, 'effort', 'apply-preset', '--preset', 'no-such-preset')

    assert code == 2
    assert err
