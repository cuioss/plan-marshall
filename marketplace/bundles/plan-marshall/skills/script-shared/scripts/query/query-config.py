#!/usr/bin/env python3
"""
Read-only skill resolution and discovery queries against marshal.json.

Exposes resolution commands that were previously only available through manage-config.
These commands consume configuration but never modify it.

Usage:
    query-config.py resolve-domain-skills --domain java --profile implementation
    query-config.py resolve-workflow-skill-extension --domain java --type outline
    query-config.py get-skills-by-profile --domain java
    query-config.py configure-execute-task-skills
    query-config.py resolve-execute-task-skill --profile implementation
    query-config.py list-recipes
    query-config.py resolve-recipe --recipe refactor-to-standards
    query-config.py resolve-outline-skill --domain java
    query-config.py list-finalize-steps
    query-config.py list-verify-steps
"""

import argparse

from _cmd_skill_domains import cmd_list_verify_steps
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

# Direct imports - PYTHONPATH set by executor
from file_ops import output_toon, safe_main


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Read-only skill resolution and discovery queries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )

    subparsers = parser.add_subparsers(dest='command', required=True, help='Query command')

    # --- resolve-domain-skills ---
    p_rds = subparsers.add_parser(
        'resolve-domain-skills', help='Resolve skills for domain and profile', allow_abbrev=False
    )
    p_rds.add_argument('--domain', required=True, help='Domain name (java, javascript)')
    p_rds.add_argument('--profile', required=True, help='Profile name (implementation, testing)')

    # --- resolve-workflow-skill-extension ---
    p_rwse = subparsers.add_parser(
        'resolve-workflow-skill-extension',
        help='Resolve workflow skill extension for domain and type',
        allow_abbrev=False,
    )
    p_rwse.add_argument('--domain', required=True, help='Domain name (java, javascript, etc.)')
    p_rwse.add_argument('--type', required=True, choices=['outline', 'triage'], help='Extension type (outline, triage)')

    # --- get-skills-by-profile ---
    p_gsbp = subparsers.add_parser(
        'get-skills-by-profile', help='Get skills organized by profile for architecture enrichment', allow_abbrev=False
    )
    p_gsbp.add_argument('--domain', required=True, help='Domain name (java, javascript, etc.)')

    # --- configure-execute-task-skills ---
    subparsers.add_parser(
        'configure-execute-task-skills',
        help='Configure execute-task skills from discovered profiles',
        allow_abbrev=False,
    )

    # --- resolve-execute-task-skill ---
    p_rte = subparsers.add_parser(
        'resolve-execute-task-skill', help='Resolve execute-task skill for a profile', allow_abbrev=False
    )
    p_rte.add_argument('--profile', required=True, help='Profile name (e.g., implementation, module_testing)')

    # --- list-recipes ---
    subparsers.add_parser('list-recipes', help='List all available recipes from configured domains', allow_abbrev=False)

    # --- resolve-recipe ---
    p_rr = subparsers.add_parser('resolve-recipe', help='Resolve a specific recipe by key', allow_abbrev=False)
    p_rr.add_argument('--recipe', required=True, help='Recipe key (e.g., refactor-to-standards)')

    # --- resolve-outline-skill ---
    p_ros = subparsers.add_parser('resolve-outline-skill', help='Resolve outline skill for domain', allow_abbrev=False)
    p_ros.add_argument('--domain', required=True, help='Domain key (e.g., plan-marshall-plugin-dev, java)')

    # --- list-finalize-steps ---
    subparsers.add_parser('list-finalize-steps', help='List all available finalize steps', allow_abbrev=False)

    # --- list-verify-steps ---
    subparsers.add_parser('list-verify-steps', help='List all available verify steps', allow_abbrev=False)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 2

    # Route to handler - reuse args object since handlers read named attributes
    # The handlers use args.domain, args.profile, etc. which are set by argparse
    handlers = {
        'resolve-domain-skills': cmd_resolve_domain_skills,
        'resolve-workflow-skill-extension': cmd_resolve_workflow_skill_extension,
        'get-skills-by-profile': cmd_get_skills_by_profile,
        'configure-execute-task-skills': cmd_configure_execute_task_skills,
        'resolve-execute-task-skill': cmd_resolve_execute_task_skill,
        'list-recipes': cmd_list_recipes,
        'resolve-recipe': cmd_resolve_recipe,
        'resolve-outline-skill': cmd_resolve_outline_skill,
        'list-finalize-steps': cmd_list_finalize_steps,
        'list-verify-steps': cmd_list_verify_steps,
    }

    handler = handlers.get(args.command)
    if handler:
        result = handler(args)
        output_toon(result)
        return 0

    parser.print_help()
    return 2


if __name__ == '__main__':
    main()
