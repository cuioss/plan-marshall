#!/usr/bin/env python3
"""
WebFetch permission analysis - domain categorization, duplicate detection, and consolidation.

Usage:
    permission_web.py analyze --global-file <path> --local-file <path>
    permission_web.py categorize --domains <json-array>
    permission_web.py --help

Subcommands:
    analyze        Analyze WebFetch permissions from settings files
    categorize     Categorize a list of domains against trusted/known lists

Examples:
    # Analyze global and local settings
    permission_web.py analyze --global-file ~/.claude/settings.json --local-file .claude/settings.local.json

    # Categorize specific domains
    permission_web.py categorize --domains '["docs.oracle.com", "suspicious-site.xyz"]'
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]
from triage_helpers import safe_main  # type: ignore[import-not-found]

# ============================================================================
# DOMAIN KNOWLEDGE (loaded from domain-lists.json)
# ============================================================================

_DOMAIN_LISTS_FILE = Path(__file__).parent.parent / 'standards' / 'domain-lists.json'


def _load_domain_lists() -> dict[str, Any]:
    """Load domain lists from domain-lists.json config file."""
    try:
        with open(_DOMAIN_LISTS_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f'WARNING: Failed to load {_DOMAIN_LISTS_FILE}: {e}', file=sys.stderr)
        return {}


_DOMAIN_CONFIG = _load_domain_lists()

# Domains from trusted-domains.md — fully trusted, safe to recommend for global
MAJOR_DOMAINS: set[str] = set(_DOMAIN_CONFIG.get('major_domains', []))

# High-reach developer platforms — commonly needed across projects
HIGH_REACH_DOMAINS: set[str] = set(_DOMAIN_CONFIG.get('high_reach_domains', []))

# Red flags in domain names
RED_FLAG_PATTERNS: list[str] = _DOMAIN_CONFIG.get('red_flag_patterns', [])


# ============================================================================
# CORE FUNCTIONS
# ============================================================================


def extract_webfetch_domains(settings: dict) -> list[str]:
    """Extract WebFetch domain permissions from a settings dict.

    Looks for WebFetch entries in both 'permissions.allow' and 'permissions.deny'.
    Returns domain strings (e.g., 'docs.oracle.com' from 'WebFetch(docs.oracle.com)').
    """
    domains = []
    permissions = settings.get('permissions', {})
    for section in ('allow', 'deny'):
        for entry in permissions.get(section, []):
            if isinstance(entry, str) and entry.startswith('WebFetch('):
                # Extract domain from WebFetch(domain)
                match = re.match(r'WebFetch\((.+)\)', entry)
                if match:
                    domains.append(match.group(1))
    return domains


def categorize_domain(domain: str) -> str:
    """Categorize a single domain.

    Returns one of: universal, major, high_reach, unknown.
    Red flag detection is separate (check_red_flags).
    """
    if domain == '*' or domain == 'domain:*':
        return 'universal'
    # Normalize: strip protocol, trailing slash
    clean = domain.lower().strip().rstrip('/')
    if clean in MAJOR_DOMAINS:
        return 'major'
    if clean in HIGH_REACH_DOMAINS:
        return 'high_reach'
    # Check if subdomain of a known domain
    for known in MAJOR_DOMAINS | HIGH_REACH_DOMAINS:
        if clean.endswith('.' + known):
            return 'major' if known in MAJOR_DOMAINS else 'high_reach'
    return 'unknown'


def check_red_flags(domain: str) -> list[str]:
    """Check domain for red flag patterns. Returns list of matched flags."""
    flags = []
    clean = domain.lower()
    for pattern in RED_FLAG_PATTERNS:
        if re.search(pattern, clean):
            flags.append(pattern)
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


def find_duplicates(global_domains: list[str], local_domains: list[str]) -> list[str]:
    """Find domains that appear in both global and local settings."""
    return sorted(set(global_domains) & set(local_domains))


def find_redundant(domains: list[str]) -> dict[str, list[str]]:
    """Find redundant permissions.

    Returns dict with:
    - 'universal_redundant': domains made redundant by wildcard
    - 'subdomain_redundant': subdomains redundant when parent is approved
    """
    result: dict[str, list[str]] = {
        'universal_redundant': [],
        'subdomain_redundant': [],
    }

    has_universal = any(d in ('*', 'domain:*') for d in domains)
    specific = [d for d in domains if d not in ('*', 'domain:*')]

    if has_universal:
        result['universal_redundant'] = specific
        return result

    # Check subdomain redundancy
    for domain in specific:
        for other in specific:
            if domain != other and domain.endswith('.' + other):
                result['subdomain_redundant'].append(domain)

    return result


def generate_recommendations(
    categories: dict[str, list[str]],
    duplicates: list[str],
    redundant: dict[str, list[str]],
) -> list[dict[str, str]]:
    """Generate consolidation recommendations."""
    recs: list[dict[str, str]] = []

    if redundant['universal_redundant']:
        recs.append({
            'action': 'remove',
            'reason': 'Redundant — universal wildcard (*) covers all domains',
            'domains': ', '.join(redundant['universal_redundant']),
        })

    if duplicates:
        recs.append({
            'action': 'deduplicate',
            'reason': 'Duplicated across global and local settings',
            'domains': ', '.join(duplicates),
        })

    if redundant['subdomain_redundant']:
        recs.append({
            'action': 'remove',
            'reason': 'Subdomain already covered by parent domain',
            'domains': ', '.join(redundant['subdomain_redundant']),
        })

    if categories['major']:
        recs.append({
            'action': 'move_to_global',
            'reason': 'Major documentation domains — safe for global settings',
            'domains': ', '.join(sorted(categories['major'])),
        })

    if categories['high_reach']:
        recs.append({
            'action': 'move_to_global',
            'reason': 'High-reach developer platforms — commonly needed across projects',
            'domains': ', '.join(sorted(categories['high_reach'])),
        })

    if categories['suspicious']:
        recs.append({
            'action': 'review_for_removal',
            'reason': 'Domain matches red flag patterns — investigate before keeping',
            'domains': ', '.join(sorted(categories['suspicious'])),
        })

    if categories['unknown']:
        recs.append({
            'action': 'research',
            'reason': 'Unknown domain — needs security assessment before categorizing',
            'domains': ', '.join(sorted(categories['unknown'])),
        })

    return recs


# ============================================================================
# ANALYZE SUBCOMMAND
# ============================================================================


def cmd_analyze(args):
    """Handle analyze subcommand."""
    stats: dict[str, Any] = {
        'domains_analyzed': 0,
        'files_read': 0,
        'duplicates_found': 0,
        'redundant_found': 0,
    }

    global_domains: list[str] = []
    local_domains: list[str] = []

    # Read global settings
    if args.global_file:
        global_path = Path(args.global_file).expanduser()
        if global_path.exists():
            try:
                settings = json.loads(global_path.read_text())
                global_domains = extract_webfetch_domains(settings)
                stats['files_read'] += 1
            except json.JSONDecodeError as e:
                print(serialize_toon({
                    'error': f'Invalid JSON in global settings: {e}',
                    'file': str(global_path),
                    'status': 'failure',
                }))
                return 1
        else:
            stats['global_missing'] = True

    # Read local settings
    if args.local_file:
        local_path = Path(args.local_file)
        if local_path.exists():
            try:
                settings = json.loads(local_path.read_text())
                local_domains = extract_webfetch_domains(settings)
                stats['files_read'] += 1
            except json.JSONDecodeError as e:
                print(serialize_toon({
                    'error': f'Invalid JSON in local settings: {e}',
                    'file': str(local_path),
                    'status': 'failure',
                }))
                return 1
        else:
            stats['local_missing'] = True

    # Analyze
    all_domains = sorted(set(global_domains + local_domains))
    stats['domains_analyzed'] = len(all_domains)

    categories = categorize_domains(all_domains)
    duplicates = find_duplicates(global_domains, local_domains)
    redundant = find_redundant(all_domains)
    recommendations = generate_recommendations(categories, duplicates, redundant)

    stats['duplicates_found'] = len(duplicates)
    stats['redundant_found'] = (
        len(redundant['universal_redundant']) + len(redundant['subdomain_redundant'])
    )

    result = {
        'global_count': len(global_domains),
        'local_count': len(local_domains),
        'total_unique': len(all_domains),
        'categories': {k: len(v) for k, v in categories.items()},
        'categories_detail': categories,
        'duplicates': duplicates,
        'redundant': redundant,
        'recommendations': recommendations,
        'statistics': stats,
        'status': 'success',
    }

    print(serialize_toon(result))
    return 0


# ============================================================================
# CATEGORIZE SUBCOMMAND
# ============================================================================


def cmd_categorize(args):
    """Handle categorize subcommand."""
    try:
        domains = json.loads(args.domains)
    except json.JSONDecodeError as e:
        print(serialize_toon({'error': f'Invalid JSON: {e}', 'status': 'failure'}))
        return 1

    if not isinstance(domains, list):
        print(serialize_toon({'error': 'Input must be a JSON array', 'status': 'failure'}))
        return 1

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

    print(serialize_toon(result))
    return 0


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='WebFetch permission analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  permission_web.py analyze --global-file ~/.claude/settings.json --local-file .claude/settings.local.json
  permission_web.py categorize --domains '["docs.oracle.com", "unknown-site.xyz"]'
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # analyze subcommand
    analyze_parser = subparsers.add_parser('analyze', help='Analyze WebFetch permissions from settings')
    analyze_parser.add_argument('--global-file', help='Path to global settings.json')
    analyze_parser.add_argument('--local-file', help='Path to local settings.local.json')
    analyze_parser.set_defaults(func=cmd_analyze)

    # categorize subcommand
    cat_parser = subparsers.add_parser('categorize', help='Categorize domains')
    cat_parser.add_argument('--domains', required=True, help='JSON array of domain strings')
    cat_parser.set_defaults(func=cmd_categorize)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(safe_main(main))
