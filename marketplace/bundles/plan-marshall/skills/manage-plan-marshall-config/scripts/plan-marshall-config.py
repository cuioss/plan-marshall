#!/usr/bin/env python3
"""
Plan-Marshall configuration management for project-level infrastructure settings.

Manages .plan/marshal.json with noun-verb subcommand pattern.

Usage:
    plan-marshall-config.py skill-domains list
    plan-marshall-config.py skill-domains get --domain java
    plan-marshall-config.py system retention get
    plan-marshall-config.py plan phase-1-init get
    plan-marshall-config.py plan phase-6-verify set-step --step 1_quality_check --enabled false
    plan-marshall-config.py plan phase-7-finalize get
    plan-marshall-config.py init
"""

import argparse
import sys

from _cmd_ci import cmd_ci
from _cmd_ext_defaults import cmd_ext_defaults
from _cmd_init import cmd_init
from _cmd_skill_domains import (
    cmd_configure_task_executors,
    cmd_get_skills_by_profile,
    cmd_resolve_domain_skills,
    cmd_resolve_task_executor,
    cmd_resolve_workflow_skill_extension,
    cmd_skill_domains,
)
from _cmd_system_plan import cmd_plan, cmd_system

# Direct imports - PYTHONPATH set by executor
from _config_core import EXIT_ERROR


def _add_phase_subparser(plan_sub, phase_name: str, help_text: str, *, has_pipeline: bool = False,
                         has_scalar: bool = False, has_domain_steps: bool = False):
    """Add a phase sub-parser under the plan noun.

    Args:
        plan_sub: Plan subparsers object
        phase_name: Phase key (e.g., 'phase-1-init')
        help_text: Help text for the phase
        has_pipeline: If True, adds set-max-iterations and set-step verbs
        has_scalar: If True, adds set verb with --field/--value
        has_domain_steps: If True, adds set-domain-step and set-domain-step-agent verbs
    """
    p_phase = plan_sub.add_parser(phase_name, help=help_text)
    phase_sub = p_phase.add_subparsers(dest='verb', help='Operation')

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


def main():
    parser = argparse.ArgumentParser(
        description='Plan-Marshall configuration management', formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='noun', help='Noun (resource type)')

    # --- skill-domains ---
    p_sd = subparsers.add_parser('skill-domains', help='Manage implementation skill domains')
    sd_sub = p_sd.add_subparsers(dest='verb', help='Operation')

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

    # --- system ---
    p_sys = subparsers.add_parser('system', help='Manage system settings')
    sys_sub = p_sys.add_subparsers(dest='sub_noun', help='Sub-noun')

    p_ret = sys_sub.add_parser('retention', help='Manage retention settings')
    ret_sub = p_ret.add_subparsers(dest='verb', help='Operation')

    ret_sub.add_parser('get', help='Get retention settings')

    ret_set = ret_sub.add_parser('set', help='Set retention field')
    ret_set.add_argument('--field', required=True, help='Field name')
    ret_set.add_argument('--value', required=True, help='Field value')

    # --- plan (phase-based sub-nouns) ---
    p_plan = subparsers.add_parser('plan', help='Manage plan settings')
    plan_sub = p_plan.add_subparsers(dest='sub_noun', help='Phase sub-noun')

    _add_phase_subparser(plan_sub, 'phase-1-init', 'Init phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-2-refine', 'Refine phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-5-execute', 'Execute phase settings', has_scalar=True)
    _add_phase_subparser(plan_sub, 'phase-6-verify', 'Verify phase settings',
                         has_pipeline=True, has_domain_steps=True)
    _add_phase_subparser(plan_sub, 'phase-7-finalize', 'Finalize phase settings', has_pipeline=True)

    # --- ci ---
    p_ci = subparsers.add_parser('ci', help='Manage CI provider configuration')
    ci_sub = p_ci.add_subparsers(dest='verb', help='Operation')

    ci_sub.add_parser('get', help='Get full CI config')
    ci_sub.add_parser('get-provider', help='Get CI provider')
    ci_sub.add_parser('get-tools', help='Get authenticated tools')

    ci_get_cmd = ci_sub.add_parser('get-command', help='Get CI command by name')
    ci_get_cmd.add_argument('--name', required=True, help='Command name (e.g., issue-view, pr-create)')

    ci_set_prov = ci_sub.add_parser('set-provider', help='Set CI provider')
    ci_set_prov.add_argument('--provider', required=True, help='Provider name (github, gitlab, unknown)')
    ci_set_prov.add_argument('--repo-url', required=True, help='Repository URL')

    ci_set_tools = ci_sub.add_parser('set-tools', help='Set authenticated tools')
    ci_set_tools.add_argument('--tools', required=True, help='Comma-separated tool names')

    ci_persist = ci_sub.add_parser('persist', help='Persist full CI config (provider, commands, tools)')
    ci_persist.add_argument('--provider', required=True, help='Provider name (github, gitlab, unknown)')
    ci_persist.add_argument('--repo-url', required=True, help='Repository URL')
    ci_persist.add_argument('--commands', help='JSON object of command name to command string')
    ci_persist.add_argument('--tools', help='Comma-separated authenticated tool names')
    ci_persist.add_argument('--git-present', help='Whether git is present (true/false)')

    # --- ext-defaults ---
    p_ext = subparsers.add_parser('ext-defaults', help='Manage extension defaults (shared config)')
    ext_sub = p_ext.add_subparsers(dest='verb', help='Operation')

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

    # --- configure-task-executors ---
    subparsers.add_parser('configure-task-executors', help='Configure task executors from discovered profiles')

    # --- resolve-task-executor ---
    p_rte = subparsers.add_parser('resolve-task-executor', help='Resolve task executor skill for a profile')
    p_rte.add_argument('--profile', required=True, help='Profile name (e.g., implementation, module_testing)')

    args = parser.parse_args()

    if args.noun is None:
        parser.print_help()
        return EXIT_ERROR

    # Route to handler
    if args.noun == 'skill-domains':
        if not args.verb:
            p_sd.print_help()
            return EXIT_ERROR
        return cmd_skill_domains(args)
    elif args.noun == 'system':
        if not args.sub_noun or not args.verb:
            p_sys.print_help()
            return EXIT_ERROR
        return cmd_system(args)
    elif args.noun == 'plan':
        if not args.sub_noun or not args.verb:
            p_plan.print_help()
            return EXIT_ERROR
        return cmd_plan(args)
    elif args.noun == 'ci':
        if not args.verb:
            p_ci.print_help()
            return EXIT_ERROR
        return cmd_ci(args)
    elif args.noun == 'ext-defaults':
        if not args.verb:
            p_ext.print_help()
            return EXIT_ERROR
        return cmd_ext_defaults(args)
    elif args.noun == 'init':
        return cmd_init(args)
    elif args.noun == 'resolve-domain-skills':
        return cmd_resolve_domain_skills(args)
    elif args.noun == 'resolve-workflow-skill-extension':
        return cmd_resolve_workflow_skill_extension(args)
    elif args.noun == 'get-skills-by-profile':
        return cmd_get_skills_by_profile(args)
    elif args.noun == 'configure-task-executors':
        return cmd_configure_task_executors(args)
    elif args.noun == 'resolve-task-executor':
        return cmd_resolve_task_executor(args)
    else:
        parser.print_help()
        return EXIT_ERROR


if __name__ == '__main__':
    sys.exit(main())
