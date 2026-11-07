#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Domain categorization for WebFetch permission analysis.

This script performs pure domain analysis against trusted/known lists. It does
NOT perform settings I/O and does NOT render any permission-DSL string — all
settings reading, writing, and WebFetch grammar rendering is handled by the
platform-runtime (``permission_web_analyze`` / ``permission_web_apply``).

Usage:
    permission_web.py categorize --domains <json-array>
    permission_web.py --help

Subcommands:
    categorize     Categorize a list of domains against trusted/known lists

Examples:
    # Categorize specific domains
    permission_web.py categorize --domains '["docs.oracle.com", "suspicious-site.xyz"]'
"""

import re

from triage_helpers import (
    compile_patterns_from_config,
    create_workflow_cli,
    load_skill_config,
    make_error,
    parse_json_arg,
    safe_main,
)

# ============================================================================
# DOMAIN KNOWLEDGE (loaded from domain-lists.json)
# ============================================================================

_DOMAIN_CONFIG = load_skill_config(__file__, 'domain-lists.json')


def _extract_domain_names(entries: list) -> set[str]:
    """Extract domain names from enriched objects or plain strings.

    Supports both formats for backwards compatibility:
    - Enriched: {"domain": "example.com", "purpose": "...", "trust_level": "..."}
    - Plain: "example.com"
    """
    result: set[str] = set()
    for entry in entries:
        if isinstance(entry, dict):
            d = entry.get('domain', '')
            if d:
                result.add(d)
        # SHIM(B): plain-string domain entries in domain-lists.json, before the config switched to enriched {"domain": ...} objects.
        # shim-owner: workflow-permission-web
        # shim-floor: the domain-lists.json enrichment that converted every entry from a bare string to a {"domain", "purpose", "trust_level"} object (in-code anchor: the _note field documenting "reads 'domain' fields from enriched entries or plain strings")
        # shim-remove-when: no shipped or user domain-lists config carries plain-string domain entries
        elif isinstance(entry, str):
            result.add(entry)
    return result


# Domains from domain-lists.json — fully trusted, safe to recommend for global
MAJOR_DOMAINS: set[str] = _extract_domain_names(_DOMAIN_CONFIG.get('major_domains', []))

# High-reach developer platforms — commonly needed across projects
HIGH_REACH_DOMAINS: set[str] = _extract_domain_names(_DOMAIN_CONFIG.get('high_reach_domains', []))

# Red flags in domain names — loaded from array-of-objects, pre-compiled for performance
_RED_FLAGS: list[dict[str, str]] = _DOMAIN_CONFIG.get('red_flags', [])
_RED_FLAG_RAW_PATTERNS = [entry['pattern'] for entry in _RED_FLAGS if 'pattern' in entry]
_RED_FLAG_COMPILED_LIST = compile_patterns_from_config(
    _RED_FLAG_RAW_PATTERNS,
    'domain-lists.json [red_flags]',
)
_RED_FLAG_COMPILED: list[tuple[str, re.Pattern]] = [
    (raw, compiled) for raw, compiled in zip(_RED_FLAG_RAW_PATTERNS, _RED_FLAG_COMPILED_LIST, strict=True)
]

# Pre-computed union for subdomain matching — avoids recreating per call
_ALL_KNOWN_DOMAINS: set[str] = MAJOR_DOMAINS | HIGH_REACH_DOMAINS


# ============================================================================
# CORE FUNCTIONS
# ============================================================================


def categorize_domain(domain: str) -> str:
    """Categorize a single domain.

    Returns one of: universal, major, high_reach, unknown.
    Red flag detection is separate (check_red_flags).
    """
    if domain == '*':
        return 'universal'
    # Normalize: strip protocol, trailing slash, www. prefix
    clean = re.sub(r'^https?://', '', domain.lower().strip()).rstrip('/')
    # Strip www. prefix for matching — www.npmjs.com should match npmjs.com
    bare = clean.removeprefix('www.')
    if clean in MAJOR_DOMAINS or bare in MAJOR_DOMAINS:
        return 'major'
    if clean in HIGH_REACH_DOMAINS or bare in HIGH_REACH_DOMAINS:
        return 'high_reach'
    # Check if subdomain of a known domain (uses cached union)
    for known in _ALL_KNOWN_DOMAINS:
        if clean.endswith('.' + known):
            return 'major' if known in MAJOR_DOMAINS else 'high_reach'
    return 'unknown'


def check_red_flags(domain: str) -> list[str]:
    """Check domain for red flag patterns. Returns list of matched pattern strings."""
    flags = []
    clean = re.sub(r'^https?://', '', domain.lower().strip()).rstrip('/')
    for raw_pattern, compiled in _RED_FLAG_COMPILED:
        if compiled.search(clean):
            flags.append(raw_pattern)
    return flags


def categorize_domains(domains: list[str]) -> dict[str, list[str]]:
    """Categorize a list of domains into groups.

    Returns dict with keys: universal, major, high_reach, suspicious, unknown.
    """
    result: dict[str, list[str]] = {
        'universal': [],
        'major': [],
        'high_reach': [],
        'suspicious': [],
        'unknown': [],
    }
    for domain in domains:
        flags = check_red_flags(domain)
        if flags:
            result['suspicious'].append(domain)
        else:
            category = categorize_domain(domain)
            result[category].append(domain)
    return result


# ============================================================================
# CATEGORIZE SUBCOMMAND
# ============================================================================


def cmd_categorize(args):
    """Handle categorize subcommand."""
    domains, rc = parse_json_arg(args.domains, '--domains')
    if rc:
        return rc

    if not isinstance(domains, list):
        return make_error('Input must be a JSON array')

    categories = categorize_domains(domains)
    red_flags: dict[str, list[str]] = {}
    for domain in domains:
        flags = check_red_flags(domain)
        if flags:
            red_flags[domain] = flags

    result = {
        'total': len(domains),
        'categories': {k: len(v) for k, v in categories.items()},
        'categories_detail': categories,
        'red_flags': red_flags,
        'status': 'success',
    }

    return result


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = create_workflow_cli(
        description='WebFetch domain categorization',
        epilog="""
Examples:
  permission_web.py categorize --domains '["docs.oracle.com", "unknown-site.xyz"]'
""",
        subcommands=[
            {
                'name': 'categorize',
                'help': 'Categorize domains',
                'handler': cmd_categorize,
                'args': [{'flags': ['--domains'], 'required': True, 'help': 'JSON array of domain strings'}],
            },
        ],
    )
    args = parser.parse_args()
    from triage_helpers import print_toon as _output_toon

    return _output_toon(args.func(args))


if __name__ == '__main__':
    safe_main(main)()
