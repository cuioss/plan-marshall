#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Plan-Marshall configuration management for project-level infrastructure settings.

Manages .plan/marshal.json with noun-verb subcommand pattern.

Usage:
    manage-config.py skill-domains list
    manage-config.py skill-domains get --domain java
    manage-config.py system retention get
    manage-config.py plan phase-1-init get
    manage-config.py plan phase-5-execute set-step --step verification_1_quality_check --enabled false
    manage-config.py plan phase-6-finalize get
    manage-config.py init
"""

import argparse

from _cmd_aspect_classify import cmd_aspect_classify
from _cmd_build_map import cmd_build_decision, cmd_build_map
from _cmd_coverage import cmd_coverage_expand, cmd_coverage_read, cmd_coverage_resolve
from _cmd_domain_detect import cmd_domain_detect
from _cmd_effort import (
    cmd_effort,
    cmd_effort_apply_preset,
    cmd_effort_resolve_target,
    cmd_effort_set,
)
from _cmd_ext_defaults import cmd_ext_defaults
from _cmd_finalize_steps import cmd_finalize_steps_apply_preset
from _cmd_init import cmd_init
from _cmd_recipe_match import cmd_recipe_match
from _cmd_skill_domains import (
    cmd_list_verify_steps,
    cmd_skill_domains,
)
from _cmd_skill_resolution import (
    cmd_get_skills_by_profile,
    cmd_list_finalize_steps,
    cmd_list_recipes,
    cmd_resolve_domain_skills,
    cmd_resolve_outline_skill,
    cmd_resolve_recipe,
    cmd_resolve_workflow_skill_extension,
)
from _cmd_steps_sort import cmd_steps_sort
from _cmd_sync_defaults import cmd_sync_defaults
from _cmd_system_plan import cmd_plan, cmd_project, cmd_system
from _config_core import normalize_keys

# Direct imports - PYTHONPATH set by executor
from effort_presets import EffortPresets
from file_ops import output_toon, safe_main
from finalize_step_presets import FinalizeStepPresets
from input_validation import (
    add_domain_arg,
    add_field_arg,
    parse_args_with_toon_errors,
)


def _add_phase_subparser(
    plan_sub,
    phase_name: str,
    help_text: str,
    *,
    has_pipeline: bool = False,
    has_scalar: bool = False,
    has_domain_steps: bool = False,
    has_list_steps: bool = False,
):
    """Add a phase sub-parser under the plan noun.

    Args:
        plan_sub: Plan subparsers object
        phase_name: Phase key (e.g., 'phase-1-init')
        help_text: Help text for the phase
        has_pipeline: If True, adds set-max-iterations and set-step (boolean) verbs
        has_scalar: If True, adds set verb with --field/--value
        has_domain_steps: If True, adds set-domain-step and set-domain-step-agent verbs
        has_list_steps: If True, adds set-steps, add-step, remove-step verbs (ordered list)
    """
    p_phase = plan_sub.add_parser(phase_name, help=help_text, allow_abbrev=False)
    phase_sub = p_phase.add_subparsers(dest='verb', required=True, help='Operation')

    # get (with optional --field)
    phase_get = phase_sub.add_parser('get', help=f'Get {phase_name} config', allow_abbrev=False)
    add_field_arg(phase_get, required=False)

    # remove-field: delete an arbitrary persisted key under the phase section
    # (e.g. the legacy plan.phase-5-execute.steps key). Available on every phase.
    phase_remove_field = phase_sub.add_parser(
        'remove-field', help=f'Remove an arbitrary key from {phase_name} config', allow_abbrev=False
    )
    add_field_arg(phase_remove_field)

    if has_scalar:
        phase_set = phase_sub.add_parser('set', help=f'Set {phase_name} field', allow_abbrev=False)
        add_field_arg(phase_set)
        phase_set.add_argument('--value', required=True, help='Field value')

    if has_pipeline:
        phase_set_iter = phase_sub.add_parser('set-max-iterations', help='Set max iterations', allow_abbrev=False)
        phase_set_iter.add_argument('--value', required=True, type=int, help='Max iterations value')

        phase_set_step = phase_sub.add_parser('set-step', help='Set generic boolean step', allow_abbrev=False)
        phase_set_step.add_argument('--step', required=True, help='Step key (e.g., 1_quality_check)')
        phase_set_step.add_argument('--enabled', required=True, help='true or false')

    if has_list_steps:
        phase_set_iter = phase_sub.add_parser('set-max-iterations', help='Set max iterations', allow_abbrev=False)
        phase_set_iter.add_argument('--value', required=True, type=int, help='Max iterations value')

        phase_set_steps = phase_sub.add_parser('set-steps', help='Replace entire steps list', allow_abbrev=False)
        phase_set_steps.add_argument('--steps', required=True, help='Comma-separated step list')

        phase_add_step = phase_sub.add_parser('add-step', help='Add step to list', allow_abbrev=False)
        phase_add_step.add_argument('--step', required=True, help='Step reference')

        phase_rm_step = phase_sub.add_parser('remove-step', help='Remove step from list', allow_abbrev=False)
        phase_rm_step.add_argument('--step', required=True, help='Step reference to remove')

        # One-stop step verb: `step get` returns the complete nested param object
        # for a step id in a single call; `step set` writes one step-owned param.
        # Both operate on the marshal.json keyed-map step structure.
        phase_step = phase_sub.add_parser(
            'step', help='Get/set a step\'s nested param object (keyed-map)', allow_abbrev=False
        )
        step_sub = phase_step.add_subparsers(dest='step_verb', required=True, help='Step operation')

        step_get = step_sub.add_parser(
            'get', help='Get the complete nested param object for a step', allow_abbrev=False
        )
        step_get.add_argument('--step-id', required=True, help='Step id (e.g., default:sonar-roundtrip)')

        step_set = step_sub.add_parser(
            'set', help='Set one step-owned param into a step\'s nested object', allow_abbrev=False
        )
        step_set.add_argument('--step-id', required=True, help='Step id (e.g., default:branch-cleanup)')
        step_set.add_argument('--param', required=True, help='Param key (e.g., pr_merge_strategy)')
        step_set.add_argument('--value', required=True, help='Param value')

    if has_domain_steps:
        phase_set_ds = phase_sub.add_parser(
            'set-domain-step', help='Enable/disable domain verification step', allow_abbrev=False
        )
        add_domain_arg(phase_set_ds)
        phase_set_ds.add_argument('--step', required=True, help='Step key (e.g., 1_technical_impl)')
        phase_set_ds.add_argument('--enabled', required=True, help='true or false')

        phase_set_dsa = phase_sub.add_parser(
            'set-domain-step-agent', help='Set domain step agent reference', allow_abbrev=False
        )
        add_domain_arg(phase_set_dsa)
        phase_set_dsa.add_argument('--step', required=True, help='Step key (e.g., 1_technical_impl)')
        phase_set_dsa.add_argument('--agent', required=True, help='Fully-qualified agent reference')

    return p_phase


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Plan-Marshall configuration management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )

    subparsers = parser.add_subparsers(dest='noun', required=True, help='Noun (resource type)')

    # --- skill-domains ---
    p_sd = subparsers.add_parser('skill-domains', help='Manage implementation skill domains', allow_abbrev=False)
    sd_sub = p_sd.add_subparsers(dest='verb', required=True, help='Operation')

    sd_sub.add_parser('list', help='List all domains', allow_abbrev=False)

    sd_get = sd_sub.add_parser('get', help='Get domain config', allow_abbrev=False)
    add_domain_arg(sd_get)

    sd_get_def = sd_sub.add_parser('get-defaults', help='Get domain default skills', allow_abbrev=False)
    add_domain_arg(sd_get_def)

    sd_get_opt = sd_sub.add_parser('get-optionals', help='Get domain optional skills', allow_abbrev=False)
    add_domain_arg(sd_get_opt)

    sd_set = sd_sub.add_parser('set', help='Set domain config', allow_abbrev=False)
    add_domain_arg(sd_set)
    sd_set.add_argument('--profile', help='Profile name (core, implementation, testing, quality)')
    sd_set.add_argument('--defaults', help='Comma-separated default skills')
    sd_set.add_argument('--optionals', help='Comma-separated optional skills')

    sd_get_ext = sd_sub.add_parser(
        'get-extensions', help='Get workflow skill extensions for domain', allow_abbrev=False
    )
    add_domain_arg(sd_get_ext)

    sd_set_ext = sd_sub.add_parser('set-extensions', help='Set workflow skill extension', allow_abbrev=False)
    add_domain_arg(sd_set_ext)
    sd_set_ext.add_argument(
        '--type', required=True, choices=['outline', 'triage'], help='Extension type'
    )
    sd_set_ext.add_argument('--skill', required=True, help='Extension skill reference (bundle:skill)')

    sd_add = sd_sub.add_parser('add', help='Add new domain', allow_abbrev=False)
    add_domain_arg(sd_add)
    sd_add.add_argument('--defaults', help='Comma-separated default skills')
    sd_add.add_argument('--optionals', help='Comma-separated optional skills')

    sd_val = sd_sub.add_parser('validate', help='Validate skill in domain', allow_abbrev=False)
    add_domain_arg(sd_val)
    sd_val.add_argument('--skill', required=True, help='Skill to validate')

    sd_sub.add_parser('detect', help='Auto-detect domains from project files', allow_abbrev=False)

    sd_sub.add_parser('get-available', help='Get available domains based on detected build systems', allow_abbrev=False)

    sd_configure = sd_sub.add_parser('configure', help='Configure selected domains', allow_abbrev=False)
    sd_configure.add_argument('--domains', required=True, help='Comma-separated domain names to enable')

    sd_sub.add_parser('discover-project', help="Discover project-level skills from the target's project-local-skill roots", allow_abbrev=False)

    sd_attach = sd_sub.add_parser('attach-project', help='Attach project-level skills to a domain', allow_abbrev=False)
    add_domain_arg(sd_attach)
    sd_attach.add_argument('--skills', required=True, help='Comma-separated project:skill notations')

    # active-profiles subcommands
    sd_ap = sd_sub.add_parser('active-profiles', help='Manage active profile configuration', allow_abbrev=False)
    sd_ap_sub = sd_ap.add_subparsers(dest='ap_verb', help='Active profiles operation')

    sd_ap_set = sd_ap_sub.add_parser('set', help='Set active profiles (global or per-domain)', allow_abbrev=False)
    sd_ap_set.add_argument('--profiles', required=True, help='Comma-separated profile names')
    add_domain_arg(sd_ap_set, required=False)

    sd_ap_remove = sd_ap_sub.add_parser('remove', help='Remove active profiles config', allow_abbrev=False)
    add_domain_arg(sd_ap_remove, required=False)

    # --- system ---
    p_sys = subparsers.add_parser('system', help='Manage system settings', allow_abbrev=False)
    sys_sub = p_sys.add_subparsers(dest='sub_noun', required=True, help='Sub-noun')

    p_ret = sys_sub.add_parser('retention', help='Manage retention settings', allow_abbrev=False)
    ret_sub = p_ret.add_subparsers(dest='verb', required=True, help='Operation')

    ret_sub.add_parser('get', help='Get retention settings', allow_abbrev=False)

    ret_set = ret_sub.add_parser('set', help='Set retention field', allow_abbrev=False)
    add_field_arg(ret_set)
    ret_set.add_argument('--value', required=True, help='Field value')

    # --- project (project-level config) ---
    p_proj = subparsers.add_parser('project', help='Manage project-level settings', allow_abbrev=False)
    proj_sub = p_proj.add_subparsers(dest='verb', required=True, help='Operation')

    proj_get = proj_sub.add_parser('get', help='Get a project field', allow_abbrev=False)
    add_field_arg(proj_get)

    proj_set = proj_sub.add_parser('set', help='Set a project field', allow_abbrev=False)
    add_field_arg(proj_set)
    proj_set.add_argument('--value', required=True, help='Field value')

    # --- plan (phase-based sub-nouns) ---
    p_plan = subparsers.add_parser('plan', help='Manage plan settings', allow_abbrev=False)
    plan_sub = p_plan.add_subparsers(dest='sub_noun', required=True, help='Phase sub-noun')

    _add_phase_subparser(plan_sub, 'phase-1-init', 'Init phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-2-refine', 'Refine phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-3-outline', 'Outline phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-4-plan', 'Plan phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-5-execute', 'Execute phase settings', has_scalar=True, has_list_steps=True)
    _add_phase_subparser(plan_sub, 'phase-6-finalize', 'Finalize phase settings', has_scalar=True, has_list_steps=True)

    # --- ext-defaults ---
    p_ext = subparsers.add_parser('ext-defaults', help='Manage extension defaults (shared config)', allow_abbrev=False)
    ext_sub = p_ext.add_subparsers(dest='verb', required=True, help='Operation')

    ext_get = ext_sub.add_parser('get', help='Get extension default value', allow_abbrev=False)
    ext_get.add_argument('--key', required=True, help='Key to retrieve')

    ext_set = ext_sub.add_parser('set', help='Set extension default value (always overwrites)', allow_abbrev=False)
    ext_set.add_argument('--key', required=True, help='Key to set')
    ext_set.add_argument('--value', required=True, help='Value (JSON or string)')

    ext_set_def = ext_sub.add_parser(
        'set-default', help='Set value only if key does not exist (write-once)', allow_abbrev=False
    )
    ext_set_def.add_argument('--key', required=True, help='Key to set')
    ext_set_def.add_argument('--value', required=True, help='Value (JSON or string)')

    ext_sub.add_parser('list', help='List all extension defaults', allow_abbrev=False)

    ext_remove = ext_sub.add_parser('remove', help='Remove extension default', allow_abbrev=False)
    ext_remove.add_argument('--key', required=True, help='Key to remove')

    # --- build-map ---
    p_bm = subparsers.add_parser(
        'build-map',
        help='Seed/read the file-to-build contract (build_map block)',
        allow_abbrev=False,
    )
    bm_sub = p_bm.add_subparsers(dest='verb', required=True, help='Operation')
    bm_seed = bm_sub.add_parser(
        'seed',
        help='Seed build_map from applicable domains, write-once (existing seed preserved unless --force)',
        allow_abbrev=False,
    )
    bm_seed.add_argument(
        '--force',
        action='store_true',
        help='Clear any existing build_map and re-derive a clean one from current project state '
        '(bypasses the write-once guard)',
    )
    bm_sub.add_parser(
        'read',
        help='Return the effective build map from build.map',
        allow_abbrev=False,
    )
    bm_sub.add_parser(
        'drift',
        help='Diff the persisted build.map against the live derivation (read-only; in_sync + added/removed globs)',
        allow_abbrev=False,
    )

    # --- build-decision ---
    p_bd = subparsers.add_parser(
        'build-decision',
        help='Decide whether a canonical command must run for a plan footprint '
        '(build / not_necessary verdict)',
        allow_abbrev=False,
    )
    p_bd.add_argument(
        '--command',
        required=True,
        help='Canonical command under decision (e.g. quality-gate / verify / coverage)',
    )
    p_bd.add_argument(
        '--plan-id',
        dest='plan_id',
        help='Plan identifier whose live footprint gates the decision',
    )
    p_bd.add_argument(
        '--audit-plan-id',
        dest='audit_plan_id',
        help='Alias for --plan-id (execution-log attribution parity with other verbs)',
    )

    # --- init ---
    p_init = subparsers.add_parser('init', help='Initialize marshal.json', allow_abbrev=False)
    p_init.add_argument('--force', action='store_true', help='Overwrite existing')

    # --- normalize-keys ---
    subparsers.add_parser(
        'normalize-keys',
        help='Re-write marshal.json with the canonical top-level key order (silent, idempotent)',
        allow_abbrev=False,
    )

    # --- steps-sort ---
    subparsers.add_parser(
        'steps-sort',
        help='Re-sort plan.phase-6-finalize.steps into ascending frontmatter order '
        '(silent, idempotent, values byte-identical)',
        allow_abbrev=False,
    )

    # --- sync-defaults ---
    p_sync = subparsers.add_parser(
        'sync-defaults',
        help='Non-destructively merge keys present in defaults but absent from the live marshal.json',
        allow_abbrev=False,
    )
    p_sync.add_argument(
        '--audit-plan-id',
        dest='audit_plan_id',
        help='Plan identifier for execution-log attribution (optional).',
    )

    # --- effort ---
    p_effort = subparsers.add_parser(
        'effort',
        help='Manage per-phase effort levels (read resolver, preset writer)',
        allow_abbrev=False,
    )
    effort_sub = p_effort.add_subparsers(dest='verb', required=True, help='Operation')
    effort_read = effort_sub.add_parser(
        'read',
        help='Resolve the effort keyword for a role (or fetch `plan.effort`)',
        allow_abbrev=False,
    )
    # Accepted lookup forms (validated in `_split_role`):
    #   --role <group>             bare-group lookup (e.g. "phase-1-init")
    #   --role <group>.<subkey>    dotted form (e.g. "phase-6-finalize.verification-feedback")
    #   --phase <group> --role <s> two-flag form (e.g. "--phase phase-6-finalize --role verification-feedback")
    #   --phase <group>            bare-group lookup via --phase
    #   --default                  short-circuit to `plan.effort`
    # `--default` is mutually exclusive with the role/phase forms.
    effort_read.add_argument(
        '--role',
        help=(
            'Role key (see effort-roles.md registry). Accepted forms: bare '
            'group "phase-1-init"; dotted "phase-3-outline"; or use --phase '
            'plus a bare subkey ("--phase phase-6-finalize --role '
            'verification-feedback").'
        ),
    )
    effort_read.add_argument(
        '--phase',
        help=(
            'Role group (e.g. "phase-6-finalize"). May be used alone for a '
            'bare-group lookup, or paired with a bare-subkey --role for '
            'the two-flag form; --role must not itself include a dot in '
            'the two-flag form.'
        ),
    )
    effort_read.add_argument(
        '--default',
        action='store_true',
        help='Return `plan.effort` directly (no role/phase lookup).',
    )

    effort_resolve_target = effort_sub.add_parser(
        'resolve-target',
        help='Resolve a role to its execution-context-{level} variant target name',
        allow_abbrev=False,
    )
    effort_resolve_target.add_argument(
        '--role',
        help=(
            'Role key (same accepted forms as `effort read --role`). '
            'Returns the variant target name `execution-context-{level}` '
            '(or the canonical `execution-context` when the resolved level '
            'is `inherit`).'
        ),
    )
    effort_resolve_target.add_argument(
        '--phase',
        help='Role group; may be used alone or paired with --role.',
    )
    effort_resolve_target.add_argument(
        '--default',
        action='store_true',
        help='Resolve via `plan.effort` (no role/phase lookup).',
    )
    effort_apply_preset = effort_sub.add_parser(
        'apply-preset',
        help='Write per-phase effort attributes from a named preset',
        allow_abbrev=False,
    )
    # Validation uses ``type=`` rather than ``choices=`` so the documented
    # case-insensitive / underscore-alias behaviour (``HIGH_END``,
    # ``high_end``, ``Balanced``) works end-to-end through the CLI, not
    # just for programmatic callers of :meth:`EffortPresets.get`. A plain
    # ``choices=EffortPresets.all_names()`` would enforce exact,
    # case-sensitive matching of the canonical names and reject the
    # documented aliases before the handler runs. The ``type=`` callable
    # normalises and validates in one step, and unknown names raise
    # :class:`argparse.ArgumentTypeError` so argparse still emits a usage
    # error with exit code 2 (preserving the existing CLI contract that
    # bogus presets are rejected at the argparse layer).
    def _preset_arg(value: str) -> str:
        try:
            EffortPresets.get(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from exc
        return value

    canonical_names = ', '.join(EffortPresets.all_names())
    effort_apply_preset.add_argument(
        '--preset',
        required=True,
        type=_preset_arg,
        metavar='PRESET',
        help=(
            f'Preset name (canonical: {canonical_names}; '
            'case-insensitive, underscore variants accepted; '
            'see effort_presets.py for per-preset values)'
        ),
    )

    effort_set = effort_sub.add_parser(
        'set',
        help='Surgically write one effort scope (per-scope writer)',
        allow_abbrev=False,
    )
    effort_set.add_argument(
        '--scope',
        required=True,
        help=(
            "Effort scope to write: a dotted '{phase}.{role}' nested scope "
            '(e.g. "phase-6-finalize.verification-feedback"), or the literal '
            '"plan" for the plan-wide scalar fallback. The nested write '
            'preserves sibling sub-keys; a pre-existing scalar effort string '
            'is normalised into an object first.'
        ),
    )
    effort_set.add_argument(
        '--level',
        required=True,
        help='Effort level keyword (level-1..level-7 or inherit).',
    )

    # --- coverage ---
    # Two-dial coverage contract: thoroughness (T1-T5) x scope
    # (change-set..overall). The read/resolve verbs mirror the `effort`
    # resolver's lookup shape (--phase / --role / --default), resolving each
    # field independently and validating the scope<->thoroughness coupling
    # constraint at lookup time.
    p_coverage = subparsers.add_parser(
        'coverage',
        help='Resolve the per-phase coverage cell (thoroughness x scope)',
        allow_abbrev=False,
    )
    coverage_sub = p_coverage.add_subparsers(dest='verb', required=True, help='Operation')

    coverage_read = coverage_sub.add_parser(
        'read',
        help='Resolve the (thoroughness, scope) cell for a phase/role',
        allow_abbrev=False,
    )
    coverage_read.add_argument(
        '--role',
        help='Phase group (e.g. "phase-5-execute"); synonym for --phase.',
    )
    coverage_read.add_argument(
        '--phase',
        help='Phase group (e.g. "phase-5-execute").',
    )
    coverage_read.add_argument(
        '--default',
        action='store_true',
        help='Return `plan.coverage` directly (no phase/role lookup).',
    )

    coverage_resolve = coverage_sub.add_parser(
        'resolve',
        help='Resolve the coverage cell plus the coupling result for downstream consumers',
        allow_abbrev=False,
    )
    coverage_resolve.add_argument(
        '--role',
        help='Phase group (same accepted forms as `coverage read --role`).',
    )
    coverage_resolve.add_argument(
        '--phase',
        help='Phase group; synonym for --role.',
    )
    coverage_resolve.add_argument(
        '--default',
        action='store_true',
        help='Resolve via `plan.coverage` (no phase/role lookup).',
    )

    coverage_expand = coverage_sub.add_parser(
        'expand',
        help='Expand a (thoroughness, scope) cell into the contract instruction block',
        allow_abbrev=False,
    )
    coverage_expand.add_argument(
        '--thoroughness',
        required=True,
        help='Thoroughness rung (T1-T5 or inherit).',
    )
    coverage_expand.add_argument(
        '--scope',
        required=True,
        help='Scope rung (change-set/artifact/component/module/overall or inherit).',
    )

    # --- finalize-steps ---
    p_finalize_steps = subparsers.add_parser(
        'finalize-steps',
        help='Manage phase-6-finalize step lists (preset writer)',
        allow_abbrev=False,
    )
    finalize_steps_sub = p_finalize_steps.add_subparsers(dest='verb', required=True, help='Operation')
    finalize_steps_apply_preset = finalize_steps_sub.add_parser(
        'apply-preset',
        help='Write plan.phase-6-finalize.steps from a named preset',
        allow_abbrev=False,
    )

    # Validation uses ``type=`` rather than ``choices=`` so the documented
    # case-insensitive behaviour (``Local``, ``FULL``) works end-to-end
    # through the CLI. Unknown names raise :class:`argparse.ArgumentTypeError`
    # so argparse emits a usage error with exit code 2 (preserving the CLI
    # contract that bogus presets are rejected at the argparse layer).
    def _finalize_preset_arg(value: str) -> str:
        try:
            FinalizeStepPresets.get(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from exc
        return value

    finalize_canonical_names = ', '.join(FinalizeStepPresets.all_names())
    finalize_steps_apply_preset.add_argument(
        '--preset',
        required=True,
        type=_finalize_preset_arg,
        metavar='PRESET',
        help=(
            f'Preset name (canonical: {finalize_canonical_names}; '
            'case-insensitive; see finalize_step_presets.py for per-preset '
            'step lists)'
        ),
    )

    # --- resolve-domain-skills ---
    p_rds = subparsers.add_parser(
        'resolve-domain-skills', help='Resolve skills for domain and profile', allow_abbrev=False
    )
    add_domain_arg(p_rds)
    p_rds.add_argument('--profile', required=True, help='Profile name (implementation, testing)')

    # --- resolve-workflow-skill-extension ---
    p_rwse = subparsers.add_parser(
        'resolve-workflow-skill-extension',
        help='Resolve workflow skill extension for domain and type',
        allow_abbrev=False,
    )
    add_domain_arg(p_rwse)
    p_rwse.add_argument('--type', required=True, choices=['outline', 'triage'], help='Extension type (outline, triage)')

    # --- get-skills-by-profile ---
    p_gsbp = subparsers.add_parser(
        'get-skills-by-profile',
        help='Get skills organized by profile for architecture enrichment',
        allow_abbrev=False,
    )
    add_domain_arg(p_gsbp)

    # --- list-recipes ---
    subparsers.add_parser('list-recipes', help='List all available recipes from configured domains', allow_abbrev=False)

    # --- resolve-recipe ---
    p_rr = subparsers.add_parser('resolve-recipe', help='Resolve a specific recipe by key', allow_abbrev=False)
    p_rr.add_argument('--recipe', required=True, help='Recipe key (e.g., refactor-to-standards)')

    # --- recipe-match ---
    # Tier 1 recipe-match: score free-form --request-text against the live
    # recipe registry via the shared recipe_scoring core. Heuristic-first,
    # zero LLM call inside the script (the bounded LLM fallback is the
    # orchestrator's responsibility).
    p_rm = subparsers.add_parser(
        'recipe-match',
        help='Score request text against the recipe registry (deterministic, heuristic-first)',
        allow_abbrev=False,
    )
    p_rm.add_argument('--request-text', dest='request_text', required=True, help='Free-form request narrative to score')
    p_rm.add_argument(
        '--threshold',
        type=float,
        default=0.6,
        help='Auto-route confidence threshold (default 0.6); top match >= threshold sets meets_auto_route_threshold',
    )

    # --- aspect-classify ---
    # Deterministic request-aspect classifier: score free-form --request-text
    # against fixed analysis/planning/implementation keyword tables (reusing
    # recipe_scoring.tokenize). A winning aspect is accepted only when it
    # clears the >= 0.7 threshold; below it the safe implementation fallback
    # keeps build/quality-gate/test gates. Heuristic-first, zero LLM call.
    p_ac = subparsers.add_parser(
        'aspect-classify',
        help='Classify request text as analysis/planning/implementation (deterministic, heuristic-first)',
        allow_abbrev=False,
    )
    p_ac.add_argument('--request-text', dest='request_text', required=True, help='Free-form request narrative to classify')
    p_ac.add_argument(
        '--threshold',
        type=float,
        default=0.7,
        help='Acceptance threshold (default 0.7); a winning aspect score below this falls back to implementation',
    )

    # --- resolve-outline-skill ---
    p_ros = subparsers.add_parser('resolve-outline-skill', help='Resolve outline skill for domain', allow_abbrev=False)
    add_domain_arg(p_ros)

    # --- list-finalize-steps ---
    subparsers.add_parser('list-finalize-steps', help='List all available finalize steps', allow_abbrev=False)

    # --- list-verify-steps ---
    subparsers.add_parser('list-verify-steps', help='List all available verify steps', allow_abbrev=False)

    # --- domain-detect ---
    p_dd = subparsers.add_parser(
        'domain-detect',
        help='Deterministic domain detector for phase-1-init Step 7 (no LLM dispatch)',
        description=(
            "Walk the plan's clarified-request narrative for explicit mentions of "
            "configured skill_domains and return the matching domain. Single-domain "
            "projects auto-select. Multi-match or no-match returns ambiguous=true so "
            "the caller raises an AskUserQuestion — no LLM fallback applies."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    p_dd.add_argument('--plan-id', dest='plan_id', required=True, help='Plan identifier')
    p_dd.add_argument(
        '--domain-override',
        dest='domain_override',
        help='Explicit domain (bypasses narrative scan; must match a configured domain key).',
    )

    args = parse_args_with_toon_errors(parser)

    if args.noun is None:
        parser.print_help()
        return 2

    # Route to handler
    result = None
    if args.noun == 'skill-domains':
        if not args.verb:
            p_sd.print_help()
            return 2
        result = cmd_skill_domains(args)
    elif args.noun == 'system':
        if not args.sub_noun or not args.verb:
            p_sys.print_help()
            return 2
        result = cmd_system(args)
    elif args.noun == 'project':
        if not args.verb:
            p_proj.print_help()
            return 2
        result = cmd_project(args)
    elif args.noun == 'plan':
        if not args.sub_noun or not args.verb:
            p_plan.print_help()
            return 2
        result = cmd_plan(args)
    elif args.noun == 'ext-defaults':
        if not args.verb:
            p_ext.print_help()
            return 2
        result = cmd_ext_defaults(args)
    elif args.noun == 'build-map':
        if not args.verb:
            p_bm.print_help()
            return 2
        result = cmd_build_map(args)
    elif args.noun == 'build-decision':
        result = cmd_build_decision(args)
    elif args.noun == 'init':
        result = cmd_init(args)
    elif args.noun == 'normalize-keys':
        try:
            outcome = normalize_keys()
            result = {'status': 'success', **outcome}
        except Exception as e:
            result = {'status': 'error', 'error': str(e)}
    elif args.noun == 'steps-sort':
        result = cmd_steps_sort(args)
    elif args.noun == 'sync-defaults':
        result = cmd_sync_defaults(args)
    elif args.noun == 'effort':
        if not args.verb:
            p_effort.print_help()
            return 2
        if args.verb == 'apply-preset':
            result = cmd_effort_apply_preset(args)
        elif args.verb == 'resolve-target':
            result = cmd_effort_resolve_target(args)
        elif args.verb == 'set':
            result = cmd_effort_set(args)
        else:
            result = cmd_effort(args)
    elif args.noun == 'coverage':
        if not args.verb:
            p_coverage.print_help()
            return 2
        if args.verb == 'resolve':
            result = cmd_coverage_resolve(args)
        elif args.verb == 'expand':
            result = cmd_coverage_expand(args)
        else:
            result = cmd_coverage_read(args)
    elif args.noun == 'finalize-steps':
        if not args.verb:
            p_finalize_steps.print_help()
            return 2
        if args.verb == 'apply-preset':
            result = cmd_finalize_steps_apply_preset(args)
        else:
            p_finalize_steps.print_help()
            return 2
    elif args.noun == 'resolve-domain-skills':
        result = cmd_resolve_domain_skills(args)
    elif args.noun == 'resolve-workflow-skill-extension':
        result = cmd_resolve_workflow_skill_extension(args)
    elif args.noun == 'get-skills-by-profile':
        result = cmd_get_skills_by_profile(args)
    elif args.noun == 'domain-detect':
        result = cmd_domain_detect(args)
    elif args.noun == 'list-recipes':
        result = cmd_list_recipes(args)
    elif args.noun == 'resolve-recipe':
        result = cmd_resolve_recipe(args)
    elif args.noun == 'recipe-match':
        result = cmd_recipe_match(args)
    elif args.noun == 'aspect-classify':
        result = cmd_aspect_classify(args)
    elif args.noun == 'resolve-outline-skill':
        result = cmd_resolve_outline_skill(args)
    elif args.noun == 'list-finalize-steps':
        result = cmd_list_finalize_steps(args)
    elif args.noun == 'list-verify-steps':
        result = cmd_list_verify_steps(args)
    else:
        parser.print_help()
        return 2

    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
