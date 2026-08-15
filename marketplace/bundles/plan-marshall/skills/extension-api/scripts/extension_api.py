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

Also serves the operator-facing read behind the resolver-configuration menu:
``derivation-resolvers list`` joins the DISCOVERED Axis-C resolvers against the
machine-local ``derivation_resolvers`` binding, so the menu renders which
resolvers exist, which are active, and over which files — every field read from
the resolver or the store that owns it rather than transcribed into a menu
document that would go stale the moment a resolver changed.

Registered as notation ``plan-marshall:extension-api:extension_api`` exposing the
``resolve-skills --profile {profile} --plan-id {plan_id}`` and
``derivation-resolvers list`` subcommands.
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


def _always_enabled(resolver_id: str, section: dict[str, Any]) -> bool:
    """The fail-open stand-in used when the run-config store cannot be read."""
    del resolver_id, section  # unused — the fail-open answer is unconditional
    return True


def list_derivation_resolvers() -> dict[str, Any]:
    """Report every discovered Axis-C resolver joined against its configured state.

    The single read the resolver-configuration menu renders. It answers the three
    questions the menu asks, each from the surface that owns the answer:

    * **which resolvers exist** — ``discover_derivation_resolvers()``, the same
      discovery the graph seam dispatches through, so the menu can never list a
      resolver the seam would not run (or miss one it would);
    * **which are active** — ``run_config.is_derivation_resolver_enabled()``,
      the machine-local binding, defaulting to active when unconfigured;
    * **over which files** — each resolver's own ``derivation_file_patterns()``,
      which is descriptive metadata and never a filter.

    Discovery is deliberately NOT filtered by the binding: the menu must show a
    disabled resolver in order to offer re-enabling it, so the join reports the
    full discovered set with an ``enabled`` flag rather than a pruned list.

    Returns:
        A TOON-ready dict carrying ``status``, ``resolvers`` (one
        ``{id, origin, enabled, configured, file_patterns}`` record per
        discovered resolver, sorted by id), ``count``, and ``enabled_count``.
        An unavailable extension-api or run-config path degrades to an empty
        roster rather than an error — the menu then reports "none discovered",
        which is the truthful answer for an envelope with no extensions loaded.
    """
    try:
        from extension_discovery import discover_derivation_resolvers
    except ImportError:
        return {'status': 'success', 'resolvers': [], 'count': 0, 'enabled_count': 0}

    try:
        records = discover_derivation_resolvers()
    except Exception:
        return {'status': 'success', 'resolvers': [], 'count': 0, 'enabled_count': 0}

    # ONE snapshot of the store for the whole roster, not one read per resolver.
    # Failing open matches the seam's own gate: an unreadable store leaves every
    # resolver active rather than reporting a graph-blanking falsehood.
    section: dict[str, Any] = {}
    enabled_of = _always_enabled
    try:
        from run_config import is_derivation_resolver_enabled, read_derivation_resolvers_section

        section = read_derivation_resolvers_section()
        enabled_of = is_derivation_resolver_enabled
    except Exception:
        pass

    resolvers: list[dict[str, Any]] = []
    for record in records:
        resolver_id = record.get('id', '')
        module = record.get('module')
        try:
            patterns = list(module.derivation_file_patterns()) if module is not None else []
        except Exception:
            patterns = []
        # Guarded per resolver, matching the seam's own gate: one malformed
        # entry costs that resolver's state, never the whole roster, and it
        # fails OPEN so a store problem can never render as "disabled".
        try:
            enabled = enabled_of(resolver_id, section)
        except Exception:
            enabled = True
        resolvers.append(
            {
                'id': resolver_id,
                'origin': record.get('origin', 'unknown'),
                'enabled': enabled,
                'configured': resolver_id in section,
                'file_patterns': patterns,
            }
        )

    resolvers.sort(key=lambda entry: entry['id'])
    return {
        'status': 'success',
        'resolvers': resolvers,
        'count': len(resolvers),
        'enabled_count': sum(1 for entry in resolvers if entry['enabled']),
    }


def cmd_derivation_resolvers_list(args) -> dict[str, Any]:
    del args  # unused — fixed-shape verb
    return list_derivation_resolvers()


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
    resolve_parser.set_defaults(func=cmd_resolve_skills)

    dr_parser = subparsers.add_parser(
        'derivation-resolvers',
        help='Report the discovered derivation resolvers and their configured state',
        allow_abbrev=False,
    )
    dr_subparsers = dr_parser.add_subparsers(dest='derivation_resolvers_command', required=True)
    dr_list = dr_subparsers.add_parser(
        'list',
        help='List discovered resolvers with enabled state and declared file patterns',
        allow_abbrev=False,
    )
    dr_list.set_defaults(func=cmd_derivation_resolvers_list)

    args = parse_args_with_toon_errors(parser)

    # Every subparser sets its own handler, so dispatch is explicit rather than
    # defaulting: a future verb added without ``set_defaults`` fails loudly here
    # instead of silently routing into whichever handler happened to be the
    # fallback and dying on an argument it never declared.
    result = args.func(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
