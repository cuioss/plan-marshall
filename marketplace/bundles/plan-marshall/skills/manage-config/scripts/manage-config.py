#!/usr/bin/env python3
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

from _cmd_ext_defaults import cmd_ext_defaults
from _cmd_init import cmd_init
from _cmd_skill_domains import (
    cmd_list_verify_steps,
    cmd_skill_domains,
)
from _cmd_skill_resolution import (
    cmd_configure_execute_task_skills,
    cmd_get_skills_by_profile,
    cmd_list_finalize_steps,
    cmd_list_recipes,
    cmd_resolve_domain_skills,
    cmd_resolve_execute_task_skill,
    cmd_resolve_outline_skill,
    cmd_resolve_recipe,
    cmd_resolve_workflow_skill_extension,
)
from _cmd_system_plan import cmd_plan, cmd_system

# Direct imports - PYTHONPATH set by executor
from file_ops import output_toon, safe_main


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
    p_phase = plan_sub.add_parser(phase_name, help=help_text)
    phase_sub = p_phase.add_subparsers(dest='verb', required=True, help='Operation')

    # get (with optional --field)
    phase_get = phase_sub.add_parser('get', help=f'Get {phase_name} config')
    phase_get.add_argument('--field', help='Field name (optional, shows all if omitted)')

    if has_scalar:
        phase_set = phase_sub.add_parser('set', help=f'Set {phase_name} field')
        phase_set.add_argument('--field', required=True, help='Field name')
        phase_set.add_argument('--value', required=True, help='Field value')

    if has_pipeline:
        phase_set_iter = phase_sub.add_parser('set-max-iterations', help='Set max iterations')
        phase_set_iter.add_argument('--value', required=True, type=int, help='Max iterations value')

        phase_set_step = phase_sub.add_parser('set-step', help='Set generic boolean step')
        phase_set_step.add_argument('--step', required=True, help='Step key (e.g., 1_quality_check)')
        phase_set_step.add_argument('--enabled', required=True, help='true or false')

    if has_list_steps:
        phase_set_iter = phase_sub.add_parser('set-max-iterations', help='Set max iterations')
        phase_set_iter.add_argument('--value', required=True, type=int, help='Max iterations value')

        phase_set_steps = phase_sub.add_parser('set-steps', help='Replace entire steps list')
        phase_set_steps.add_argument('--steps', required=True, help='Comma-separated step list')

        phase_add_step = phase_sub.add_parser('add-step', help='Add step to list')
        phase_add_step.add_argument('--step', required=True, help='Step reference')
        phase_add_step.add_argument('--position', type=int, help='Insert position (0-based, default: append)')
        phase_add_step.add_argument('--after', help='Insert after this step name (takes precedence over --position)')

        phase_rm_step = phase_sub.add_parser('remove-step', help='Remove step from list')
        phase_rm_step.add_argument('--step', required=True, help='Step reference to remove')

        phase_set_order = phase_sub.add_parser(
            'set-step-order-override', help='Persist per-step order override for the phase'
        )
        phase_set_order.add_argument('--step', required=True, help='Step reference')
        phase_set_order.add_argument('--order', required=True, type=int, help='Override order value (int)')

        phase_rm_order = phase_sub.add_parser(
            'remove-step-order-override', help='Remove a previously persisted order override'
        )
        phase_rm_order.add_argument('--step', required=True, help='Step reference')

    if has_domain_steps:
        phase_set_ds = phase_sub.add_parser('set-domain-step', help='Enable/disable domain verification step')
        phase_set_ds.add_argument('--domain', required=True, help='Domain key (e.g., java)')
        phase_set_ds.add_argument('--step', required=True, help='Step key (e.g., 1_technical_impl)')
        phase_set_ds.add_argument('--enabled', required=True, help='true or false')

        phase_set_dsa = phase_sub.add_parser('set-domain-step-agent', help='Set domain step agent reference')
        phase_set_dsa.add_argument('--domain', required=True, help='Domain key (e.g., java)')
        phase_set_dsa.add_argument('--step', required=True, help='Step key (e.g., 1_technical_impl)')
        phase_set_dsa.add_argument('--agent', required=True, help='Fully-qualified agent reference')

    return p_phase


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Plan-Marshall configuration management', formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='noun', required=True, help='Noun (resource type)')

    # --- skill-domains ---
    p_sd = subparsers.add_parser('skill-domains', help='Manage implementation skill domains')
    sd_sub = p_sd.add_subparsers(dest='verb', required=True, help='Operation')

    sd_sub.add_parser('list', help='List all domains')

    sd_get = sd_sub.add_parser('get', help='Get domain config')
    sd_get.add_argument('--domain', required=True, help='Domain name')

    sd_get_def = sd_sub.add_parser('get-defaults', help='Get domain default skills')
    sd_get_def.add_argument('--domain', required=True, help='Domain name')

    sd_get_opt = sd_sub.add_parser('get-optionals', help='Get domain optional skills')
    sd_get_opt.add_argument('--domain', required=True, help='Domain name')

    sd_set = sd_sub.add_parser('set', help='Set domain config')
    sd_set.add_argument('--domain', required=True, help='Domain name')
    sd_set.add_argument('--profile', help='Profile name (core, implementation, testing, quality)')
    sd_set.add_argument('--defaults', help='Comma-separated default skills')
    sd_set.add_argument('--optionals', help='Comma-separated optional skills')

    sd_get_ext = sd_sub.add_parser('get-extensions', help='Get workflow skill extensions for domain')
    sd_get_ext.add_argument('--domain', required=True, help='Domain name')

    sd_set_ext = sd_sub.add_parser('set-extensions', help='Set workflow skill extension')
    sd_set_ext.add_argument('--domain', required=True, help='Domain name')
    sd_set_ext.add_argument('--type', required=True, choices=['outline', 'triage'], help='Extension type')
    sd_set_ext.add_argument('--skill', required=True, help='Extension skill reference (bundle:skill)')

    sd_add = sd_sub.add_parser('add', help='Add new domain')
    sd_add.add_argument('--domain', required=True, help='Domain name')
    sd_add.add_argument('--defaults', help='Comma-separated default skills')
    sd_add.add_argument('--optionals', help='Comma-separated optional skills')

    sd_val = sd_sub.add_parser('validate', help='Validate skill in domain')
    sd_val.add_argument('--domain', required=True, help='Domain name')
    sd_val.add_argument('--skill', required=True, help='Skill to validate')

    sd_sub.add_parser('detect', help='Auto-detect domains from project files')

    sd_sub.add_parser('get-available', help='Get available domains based on detected build systems')

    sd_configure = sd_sub.add_parser('configure', help='Configure selected domains')
    sd_configure.add_argument('--domains', required=True, help='Comma-separated domain names to enable')

    sd_sub.add_parser('discover-project', help='Discover project-level skills from .claude/skills/')

    sd_attach = sd_sub.add_parser('attach-project', help='Attach project-level skills to a domain')
    sd_attach.add_argument('--domain', required=True, help='Domain to attach skills to')
    sd_attach.add_argument('--skills', required=True, help='Comma-separated project:skill notations')

    # active-profiles subcommands
    sd_ap = sd_sub.add_parser('active-profiles', help='Manage active profile configuration')
    sd_ap_sub = sd_ap.add_subparsers(dest='ap_verb', help='Active profiles operation')

    sd_ap_set = sd_ap_sub.add_parser('set', help='Set active profiles (global or per-domain)')
    sd_ap_set.add_argument('--profiles', required=True, help='Comma-separated profile names')
    sd_ap_set.add_argument('--domain', help='Domain to set profiles for (omit for global)')

    sd_ap_remove = sd_ap_sub.add_parser('remove', help='Remove active profiles config')
    sd_ap_remove.add_argument('--domain', help='Domain to remove profiles from (omit for global)')

    # --- system ---
    p_sys = subparsers.add_parser('system', help='Manage system settings')
    sys_sub = p_sys.add_subparsers(dest='sub_noun', required=True, help='Sub-noun')

    p_ret = sys_sub.add_parser('retention', help='Manage retention settings')
    ret_sub = p_ret.add_subparsers(dest='verb', required=True, help='Operation')

    ret_sub.add_parser('get', help='Get retention settings')

    ret_set = ret_sub.add_parser('set', help='Set retention field')
    ret_set.add_argument('--field', required=True, help='Field name')
    ret_set.add_argument('--value', required=True, help='Field value')

    # --- plan (phase-based sub-nouns) ---
    p_plan = subparsers.add_parser('plan', help='Manage plan settings')
    plan_sub = p_plan.add_subparsers(dest='sub_noun', required=True, help='Phase sub-noun')

    _add_phase_subparser(plan_sub, 'phase-1-init', 'Init phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-2-refine', 'Refine phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-3-outline', 'Outline phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-4-plan', 'Plan phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-5-execute', 'Execute phase settings', has_scalar=True, has_list_steps=True)
    _add_phase_subparser(plan_sub, 'phase-6-finalize', 'Finalize phase settings', has_scalar=True, has_list_steps=True)

    # --- ext-defaults ---
    p_ext = subparsers.add_parser('ext-defaults', help='Manage extension defaults (shared config)')
    ext_sub = p_ext.add_subparsers(dest='verb', required=True, help='Operation')

    ext_get = ext_sub.add_parser('get', help='Get extension default value')
    ext_get.add_argument('--key', required=True, help='Key to retrieve')

    ext_set = ext_sub.add_parser('set', help='Set extension default value (always overwrites)')
    ext_set.add_argument('--key', required=True, help='Key to set')
    ext_set.add_argument('--value', required=True, help='Value (JSON or string)')

    ext_set_def = ext_sub.add_parser('set-default', help='Set value only if key does not exist (write-once)')
    ext_set_def.add_argument('--key', required=True, help='Key to set')
    ext_set_def.add_argument('--value', required=True, help='Value (JSON or string)')

    ext_sub.add_parser('list', help='List all extension defaults')

    ext_remove = ext_sub.add_parser('remove', help='Remove extension default')
    ext_remove.add_argument('--key', required=True, help='Key to remove')

    # --- init ---
    p_init = subparsers.add_parser('init', help='Initialize marshal.json')
    p_init.add_argument('--force', action='store_true', help='Overwrite existing')

    # --- resolve-domain-skills ---
    p_rds = subparsers.add_parser('resolve-domain-skills', help='Resolve skills for domain and profile')
    p_rds.add_argument('--domain', required=True, help='Domain name (java, javascript)')
    p_rds.add_argument('--profile', required=True, help='Profile name (implementation, testing)')

    # --- resolve-workflow-skill-extension ---
    p_rwse = subparsers.add_parser(
        'resolve-workflow-skill-extension', help='Resolve workflow skill extension for domain and type'
    )
    p_rwse.add_argument('--domain', required=True, help='Domain name (java, javascript, etc.)')
    p_rwse.add_argument('--type', required=True, choices=['outline', 'triage'], help='Extension type (outline, triage)')

    # --- get-skills-by-profile ---
    p_gsbp = subparsers.add_parser(
        'get-skills-by-profile', help='Get skills organized by profile for architecture enrichment'
    )
    p_gsbp.add_argument('--domain', required=True, help='Domain name (java, javascript, etc.)')

    # --- configure-execute-task-skills ---
    subparsers.add_parser(
        'configure-execute-task-skills', help='Configure execute-task skills from discovered profiles'
    )

    # --- resolve-execute-task-skill ---
    p_rte = subparsers.add_parser('resolve-execute-task-skill', help='Resolve execute-task skill for a profile')
    p_rte.add_argument('--profile', required=True, help='Profile name (e.g., implementation, module_testing)')

    # --- list-recipes ---
    subparsers.add_parser('list-recipes', help='List all available recipes from configured domains')

    # --- resolve-recipe ---
    p_rr = subparsers.add_parser('resolve-recipe', help='Resolve a specific recipe by key')
    p_rr.add_argument('--recipe', required=True, help='Recipe key (e.g., refactor-to-standards)')

    # --- resolve-outline-skill ---
    p_ros = subparsers.add_parser('resolve-outline-skill', help='Resolve outline skill for domain')
    p_ros.add_argument('--domain', required=True, help='Domain key (e.g., plan-marshall-plugin-dev, java)')

    # --- list-finalize-steps ---
    subparsers.add_parser('list-finalize-steps', help='List all available finalize steps')

    # --- list-verify-steps ---
    subparsers.add_parser('list-verify-steps', help='List all available verify steps')

    args = parser.parse_args()

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
    elif args.noun == 'init':
        result = cmd_init(args)
    elif args.noun == 'resolve-domain-skills':
        result = cmd_resolve_domain_skills(args)
    elif args.noun == 'resolve-workflow-skill-extension':
        result = cmd_resolve_workflow_skill_extension(args)
    elif args.noun == 'get-skills-by-profile':
        result = cmd_get_skills_by_profile(args)
    elif args.noun == 'configure-execute-task-skills':
        result = cmd_configure_execute_task_skills(args)
    elif args.noun == 'resolve-execute-task-skill':
        result = cmd_resolve_execute_task_skill(args)
    elif args.noun == 'list-recipes':
        result = cmd_list_recipes(args)
    elif args.noun == 'resolve-recipe':
        result = cmd_resolve_recipe(args)
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
