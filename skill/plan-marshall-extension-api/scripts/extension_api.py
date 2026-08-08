#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Plan-scoped security-skill resolver for the finalize-step-security-audit engine.

Reads a plan's ``references.json`` domains and aggregates each domain's
profile-scoped skills (the ``security`` profile in the finalize-step use case)
into a single deduped ``extra_security_skills`` map. The per-domain resolution
reuses ``manage-config``'s ``resolve-domain-skills`` path verbatim — there is no
parallel resolver. A domain that declares no matching profile resolves to a
per-domain error that is swallowed as a graceful no-op (it contributes nothing,
so the audit runs action-general only for that domain).

Registered as notation ``plan-marshall:extension-api:extension_api`` exposing the
single ``resolve-skills --profile {profile} --plan-id {plan_id}`` subcommand.
"""

import argparse
from types import SimpleNamespace
from typing import Any

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from _cmd_skill_resolution import cmd_resolve_domain_skills
from _references_core import require_references
from file_ops import output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
)


def resolve_security_skills(plan_id: str, profile: str) -> dict[str, Any]:
    """Aggregate the profile-scoped skills for every domain in a plan's references.

    Reads ``references.json.domains`` for *plan_id* and, for each domain, reuses
    :func:`cmd_resolve_domain_skills` to resolve the named *profile*'s skill set
    (core + profile ``defaults`` and ``optionals``). The resolved skills are
    aggregated and deduped across domains into one ``notation -> description``
    map; the first occurrence of a notation wins its description. A domain that
    declares no matching profile resolves to a ``status: error`` result that is
    swallowed as a graceful no-op — that domain contributes nothing.

    Args:
        plan_id: Plan identifier (already validated).
        profile: Profile name to resolve per domain (e.g. ``security``).

    Returns:
        A TOON-ready dict carrying ``status``, ``plan_id``, ``profile``,
        ``domains_resolved`` (the domains that contributed skills), and
        ``extra_security_skills`` (the deduped ``notation -> description`` map).
        When ``references.json`` is absent, the upstream error dict is propagated
        unchanged.
    """
    refs = require_references(plan_id)
    if refs.get('status') == 'error':
        return refs

    domains = refs.get('domains') or []

    extra_security_skills: dict[str, str] = {}
    domains_resolved: list[str] = []

    for domain in domains:
        result = cmd_resolve_domain_skills(SimpleNamespace(domain=domain, profile=profile))
        if result.get('status') != 'success':
            # Domain declares no matching profile (or is otherwise unresolvable)
            # -> graceful no-op: it contributes nothing to the aggregate.
            continue
        domains_resolved.append(domain)
        for notation, description in result.get('defaults', {}).items():
            extra_security_skills.setdefault(notation, description)
        for notation, description in result.get('optionals', {}).items():
            extra_security_skills.setdefault(notation, description)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'profile': profile,
        'domains_resolved': domains_resolved,
        'extra_security_skills': extra_security_skills,
    }


def cmd_resolve_skills(args) -> dict[str, Any]:
    return resolve_security_skills(args.plan_id, args.profile)


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Plan-scoped per-domain profile-skill resolver',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    resolve_parser = subparsers.add_parser(
        'resolve-skills',
        help="Aggregate a plan's per-domain profile skills (e.g. security)",
        allow_abbrev=False,
    )
    add_plan_id_arg(resolve_parser)
    resolve_parser.add_argument(
        '--profile',
        required=True,
        help='Profile name to resolve per domain (e.g. security)',
    )

    args = parse_args_with_toon_errors(parser)

    result = cmd_resolve_skills(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
