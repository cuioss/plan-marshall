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
from triage_helpers import ErrorCode, load_config_file, make_error, parse_json_arg, safe_main  # type: ignore[import-not-found]

# ============================================================================
# DOMAIN KNOWLEDGE (loaded from domain-lists.json)
# ============================================================================

_DOMAIN_LISTS_FILE = Path(__file__).parent.parent / 'standards' / 'domain-lists.json'


_DOMAIN_CONFIG = load_config_file(_DOMAIN_LISTS_FILE, 'domain-lists.json')

# Domains from trusted-domains.md — fully trusted, safe to recommend for global
MAJOR_DOMAINS: set[str] = set(_DOMAIN_CONFIG.get('major_domains', []))

# High-reach developer platforms — commonly needed across projects
HIGH_REACH_DOMAINS: set[str] = set(_DOMAIN_CONFIG.get('high_reach_domains', []))

# Red flags in domain names — pre-compiled for performance
_RED_FLAG_RAW: list[str] = _DOMAIN_CONFIG.get('red_flag_patterns', [])
_RED_FLAG_COMPILED: list[re.Pattern] = [re.compile(p) for p in _RED_FLAG_RAW]


# ============================================================================
# CORE FUNCTIONS
# ============================================================================


def extract_webfetch_domains_by_section(settings: dict) -> dict[str, list[str]]:
    """Extract WebFetch domain permissions grouped by allow/deny section.

    Returns dict with 'allow' and 'deny' keys, each containing a list of domains.
    This preserves the semantic distinction so that deny-list domains are not
    mistakenly recommended for global allow-list promotion.
    """
    result: dict[str, list[str]] = {'allow': [], 'deny': []}
    permissions = settings.get('permissions', {})
    for section in ('allow', 'deny'):
        for entry in permissions.get(section, []):
            if isinstance(entry, str) and entry.startswith('WebFetch('):
                match = re.match(r'WebFetch\((.+)\)', entry)
                if match:
                    result[section].append(match.group(1))
    return result


def extract_webfetch_domains(settings: dict) -> list[str]:
    """Extract WebFetch domain permissions from a settings dict.

    Returns all domains from both 'permissions.allow' and 'permissions.deny'.
    Delegates to extract_webfetch_domains_by_section for the actual extraction.
    """
    by_section = extract_webfetch_domains_by_section(settings)
    return by_section['allow'] + by_section['deny']


def categorize_domain(domain: str) -> str:
    """Categorize a single domain.

    Returns one of: universal, major, high_reach, unknown.
    Red flag detection is separate (check_red_flags).
    """
    if domain == '*':
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
    """Check domain for red flag patterns. Returns list of matched pattern strings."""
    flags = []
    clean = domain.lower()
    for raw, compiled in zip(_RED_FLAG_RAW, _RED_FLAG_COMPILED):
        if compiled.search(clean):
            flags.append(raw)
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

    Note: Subdomain detection is conservative — it flags subdomains as redundant
    when the parent domain is present (e.g., api.github.com when github.com exists).
    WebFetch permissions are domain-scoped (not subdomain-specific), so this is
    correct for permission consolidation. The caller should present these as
    recommendations, not auto-remove.
    """
    result: dict[str, list[str]] = {
        'universal_redundant': [],
        'subdomain_redundant': [],
    }

    has_universal = '*' in domains
    specific = [d for d in domains if d != '*']

    if has_universal:
        result['universal_redundant'] = specific
        return result

    # Check subdomain redundancy (including www. prefix equivalence)
    redundant_set: set[str] = set()
    for domain in specific:
        for other in specific:
            if domain == other:
                continue
            # Standard subdomain: api.github.com is redundant if github.com is present
            if domain.endswith('.' + other):
                redundant_set.add(domain)
            # www. equivalence: www.github.com is redundant if github.com is present
            elif domain == 'www.' + other:
                redundant_set.add(domain)

    result['subdomain_redundant'] = sorted(redundant_set)
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
    denied_domains: set[str] = set()

    # Read global settings
    if args.global_file:
        global_path = Path(args.global_file).expanduser()
        if global_path.exists():
            try:
                settings = json.loads(global_path.read_text())
                by_section = extract_webfetch_domains_by_section(settings)
                global_domains = by_section['allow']
                denied_domains.update(by_section['deny'])
                stats['files_read'] += 1
            except json.JSONDecodeError as e:
                print(serialize_toon(make_error(f'Invalid JSON in global settings: {e}', code=ErrorCode.PARSE_ERROR, file=str(global_path))))
                return 1
        else:
            stats['global_missing'] = True

    # Read local settings
    if args.local_file:
        local_path = Path(args.local_file)
        if local_path.exists():
            try:
                settings = json.loads(local_path.read_text())
                by_section = extract_webfetch_domains_by_section(settings)
                local_domains = by_section['allow']
                denied_domains.update(by_section['deny'])
                stats['files_read'] += 1
            except json.JSONDecodeError as e:
                print(serialize_toon(make_error(f'Invalid JSON in local settings: {e}', code=ErrorCode.PARSE_ERROR, file=str(local_path))))
                return 1
        else:
            stats['local_missing'] = True

    # Analyze — only allow-list domains get categorization and recommendations.
    # Denied domains are reported separately so they aren't mistakenly promoted.
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
        'denied_domains': sorted(denied_domains),
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
    domains, rc = parse_json_arg(args.domains, '--domains')
    if rc:
        return rc

    if not isinstance(domains, list):
        print(serialize_toon(make_error('Input must be a JSON array')))
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
# APPLY SUBCOMMAND
# ============================================================================


def apply_recommendations(
    settings_path: Path,
    add_domains: list[str],
    remove_domains: list[str],
) -> dict[str, Any]:
    """Apply domain changes to a settings file deterministically.

    Reads the settings file, modifies the WebFetch permissions in
    ``permissions.allow``, and writes back. Does not touch other
    permission entries (Bash, Read, etc.) or other settings keys.

    Args:
        settings_path: Path to settings.json file.
        add_domains: Domains to add as WebFetch permissions.
        remove_domains: Domains to remove from WebFetch permissions.

    Returns:
        Dict with counts of added/removed and the final domain list.
    """
    if not settings_path.exists():
        return make_error(f'Settings file not found: {settings_path}', code=ErrorCode.NOT_FOUND)

    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError as e:
        return make_error(f'Invalid JSON: {e}', code=ErrorCode.PARSE_ERROR)

    permissions = settings.setdefault('permissions', {})
    allow_list: list[str] = permissions.get('allow', [])

    # Track existing WebFetch domains
    existing_wf = {
        entry for entry in allow_list
        if isinstance(entry, str) and entry.startswith('WebFetch(')
    }
    remove_entries = {f'WebFetch({d})' for d in remove_domains}
    add_entries = {f'WebFetch({d})' for d in add_domains}

    # Remove
    removed = 0
    new_allow = []
    for entry in allow_list:
        if entry in remove_entries:
            removed += 1
        else:
            new_allow.append(entry)

    # Add (only if not already present)
    added = 0
    for entry in sorted(add_entries):
        if entry not in existing_wf and entry not in remove_entries:
            new_allow.append(entry)
            added += 1

    # Sort WebFetch entries for consistent output while preserving non-WebFetch
    # entry order. Separate, sort WebFetch entries, then merge back.
    non_wf = [e for e in new_allow if not (isinstance(e, str) and e.startswith('WebFetch('))]
    wf_sorted = sorted(e for e in new_allow if isinstance(e, str) and e.startswith('WebFetch('))
    permissions['allow'] = non_wf + wf_sorted
    # Write back preserving key order (Python 3.7+ dicts are insertion-ordered,
    # json.dumps preserves that order). sort_keys is False by default.
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + '\n')

    # Extract final WebFetch domains for reporting
    final_domains = extract_webfetch_domains(settings)

    return {
        'file': str(settings_path),
        'added': added,
        'removed': removed,
        'final_domains': sorted(final_domains),
        'status': 'success',
    }


def cmd_apply(args):
    """Handle apply subcommand."""
    add_domains: list[str] = []
    remove_domains: list[str] = []

    if args.add:
        add_domains, rc = parse_json_arg(args.add, '--add')
        if rc:
            return rc

    if args.remove:
        remove_domains, rc = parse_json_arg(args.remove, '--remove')
        if rc:
            return rc

    if not add_domains and not remove_domains:
        print(serialize_toon(make_error('At least one of --add or --remove is required', code=ErrorCode.INVALID_INPUT)))
        return 1

    settings_path = Path(args.file).expanduser()
    result = apply_recommendations(settings_path, add_domains, remove_domains)
    print(serialize_toon(result))
    return 0 if result.get('status') == 'success' else 1


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
  permission_web.py apply --file ~/.claude/settings.json --add '["docs.oracle.com"]' --remove '["old.domain.com"]'
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

    # apply subcommand
    apply_parser = subparsers.add_parser('apply', help='Apply domain changes to a settings file')
    apply_parser.add_argument('--file', required=True, help='Path to settings.json file')
    apply_parser.add_argument('--add', help='JSON array of domains to add')
    apply_parser.add_argument('--remove', help='JSON array of domains to remove')
    apply_parser.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(safe_main(main))
