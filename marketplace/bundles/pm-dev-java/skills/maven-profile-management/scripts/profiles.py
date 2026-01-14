#!/usr/bin/env python3
"""Maven profile management CLI.

Provides profile listing, classification, and mapping persistence
using architecture API for data access.
"""

import argparse
import re
import sys
from typing import Any

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from _architecture_core import (  # type: ignore[import-not-found]
    DataNotFoundError,
    load_derived_data,
    print_toon_list,
    print_toon_table,
)
from run_config import ext_defaults_get  # type: ignore[import-not-found]

# Extension defaults keys for profile configuration
EXT_KEY_PROFILES_SKIP = 'build.maven.profiles.skip'
EXT_KEY_PROFILES_MAP = 'build.maven.profiles.map.canonical'


# =============================================================================
# Profile Classification Patterns
# =============================================================================

# Patterns for automatic profile classification
PROFILE_PATTERNS = {
    'integration-tests': [
        r'(?:integration|it|e2e|acceptance)[-_]?tests?',
        r'local[-_]?integration',
        r'failsafe',
    ],
    'coverage': [
        r'jacoco',
        r'cobertura',
        r'coverage',
        r'istanbul',
    ],
    'benchmark': [
        r'jmh',
        r'perf(?:ormance)?',
        r'bench(?:mark)?',
        r'stress',
    ],
    'quality-gate': [
        r'pre[-_]?commit',
        r'checkstyle',
        r'spotbugs',
        r'pmd',
        r'quality',
        r'lint',
    ],
}

# Profiles that should be skipped (internal/release/config)
SKIP_PATTERNS = [
    r'apache[-_]?release',
    r'skip[-_]?(?:unit[-_]?)?tests?',
    r'use[-_]?(?:apache[-_]?)?snapshots?',
    r'release',
    r'gpg',
    r'deploy',
    r'sign',
    r'sonatype',
    r'ossrh',
]


def get_configured_skip_profiles(project_dir: str = '.') -> set[str]:
    """Get set of profile IDs configured to skip in run-configuration.json.

    Reads from extension_defaults.build.maven.profiles.skip which is a
    comma-separated list of profile IDs that should not be prompted for
    classification.

    Args:
        project_dir: Project directory path

    Returns:
        Set of profile IDs to skip
    """
    skip_value = ext_defaults_get(EXT_KEY_PROFILES_SKIP, project_dir)
    if not skip_value:
        return set()

    # Parse comma-separated list, stripping whitespace
    return {p.strip() for p in skip_value.split(',') if p.strip()}


def get_configured_mapped_profiles(project_dir: str = '.') -> set[str]:
    """Get set of profile IDs that have explicit canonical mappings.

    Reads from extension_defaults.build.maven.profiles.map.canonical which is a
    comma-separated list of profile:canonical pairs.

    Args:
        project_dir: Project directory path

    Returns:
        Set of profile IDs that have mappings configured
    """
    map_value = ext_defaults_get(EXT_KEY_PROFILES_MAP, project_dir)
    if not map_value:
        return set()

    # Parse comma-separated pairs (profile:canonical), extract profile IDs
    mapped = set()
    for pair in map_value.split(','):
        pair = pair.strip()
        if ':' in pair:
            profile_id = pair.split(':')[0].strip()
            if profile_id:
                mapped.add(profile_id)
    return mapped


# =============================================================================
# API Functions
# =============================================================================


def list_profiles(project_dir: str = '.', module_name: str | None = None) -> dict[str, Any]:
    """List Maven profiles from derived data.

    Args:
        project_dir: Project directory path
        module_name: Optional module filter

    Returns:
        Dict with profiles grouped by module
    """
    derived = load_derived_data(project_dir)
    modules = derived.get('modules', {})

    result: dict[str, Any] = {'modules': [], 'total_profiles': 0, 'unmatched_count': 0}

    for name, data in modules.items():
        # Filter by module if specified
        if module_name and name != module_name:
            continue

        # Only process Maven modules
        build_systems = data.get('build_systems', [])
        if 'maven' not in build_systems:
            continue

        metadata = data.get('metadata', {})
        profiles = metadata.get('profiles', [])

        if not profiles:
            continue

        module_info: dict[str, Any] = {'name': name, 'profiles': []}

        for profile in profiles:
            profile_id = profile.get('id', '')
            canonical = profile.get('canonical', '')
            is_unmatched = canonical == 'NO-MATCH-FOUND'

            module_info['profiles'].append({'id': profile_id, 'canonical': canonical, 'unmatched': is_unmatched})

            result['total_profiles'] += 1
            if is_unmatched:
                result['unmatched_count'] += 1

        result['modules'].append(module_info)

    return result


def classify_profile(profile_id: str) -> dict[str, str]:
    """Classify a profile by pattern matching.

    Args:
        profile_id: Maven profile ID

    Returns:
        Dict with classification result
    """
    profile_lower = profile_id.lower()

    # Check skip patterns first
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, profile_lower):
            return {
                'profile_id': profile_id,
                'classification': 'skip',
                'reason': f'Matches skip pattern: {pattern}',
                'confidence': 'high',
            }

    # Check canonical patterns
    for canonical, patterns in PROFILE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, profile_lower):
                return {
                    'profile_id': profile_id,
                    'classification': canonical,
                    'reason': f'Matches pattern: {pattern}',
                    'confidence': 'high',
                }

    # No match
    return {'profile_id': profile_id, 'classification': 'unknown', 'reason': 'No pattern matched', 'confidence': 'low'}


def get_unmatched_profiles(project_dir: str = '.') -> list[str]:
    """Get deduplicated list of unmatched profiles across all modules.

    Filters out profiles that are configured in run-configuration.json:
    - extension_defaults.build.maven.profiles.skip (profiles to skip)
    - extension_defaults.build.maven.profiles.map.canonical (profiles with mappings)

    Args:
        project_dir: Project directory path

    Returns:
        List of unmatched profile IDs (excluding configured profiles)
    """
    result = list_profiles(project_dir)
    unmatched = set()

    for module in result['modules']:
        for profile in module['profiles']:
            if profile['unmatched']:
                unmatched.add(profile['id'])

    # Filter out profiles configured in run-configuration.json
    skip_profiles = get_configured_skip_profiles(project_dir)
    mapped_profiles = get_configured_mapped_profiles(project_dir)
    unmatched = unmatched - skip_profiles - mapped_profiles

    return sorted(unmatched)


def suggest_classifications(project_dir: str = '.') -> list[dict[str, str]]:
    """Suggest classifications for unmatched profiles.

    Args:
        project_dir: Project directory path

    Returns:
        List of suggestions with profile_id, suggested, and reason
    """
    unmatched = get_unmatched_profiles(project_dir)
    suggestions = []

    for profile_id in unmatched:
        classification = classify_profile(profile_id)
        suggestions.append(
            {
                'profile_id': profile_id,
                'suggested': classification['classification'],
                'reason': classification['reason'],
                'confidence': classification['confidence'],
            }
        )

    return suggestions


# =============================================================================
# CLI Handlers
# =============================================================================


def cmd_list(args: argparse.Namespace) -> int:
    """CLI handler for list command."""
    try:
        result = list_profiles(args.project_dir, args.module)

        print(f'total_profiles: {result["total_profiles"]}')
        print(f'unmatched_count: {result["unmatched_count"]}')
        print()

        for module in result['modules']:
            print(f'module: {module["name"]}')
            if module['profiles']:
                items = [{'id': p['id'], 'canonical': p['canonical']} for p in module['profiles']]
                print_toon_table('profiles', items, ['id', 'canonical'])
            print()

        return 0
    except DataNotFoundError as e:
        print(f'error: {e}', file=sys.stderr)
        print("resolution: Run 'architecture.py discover' first", file=sys.stderr)
        return 1
    except Exception as e:
        print(f'error: {e}', file=sys.stderr)
        return 1


def cmd_unmatched(args: argparse.Namespace) -> int:
    """CLI handler for unmatched command."""
    try:
        unmatched = get_unmatched_profiles(args.project_dir)

        print(f'count: {len(unmatched)}')
        if unmatched:
            print_toon_list('profiles', unmatched)

        return 0
    except DataNotFoundError as e:
        print(f'error: {e}', file=sys.stderr)
        return 1
    except Exception as e:
        print(f'error: {e}', file=sys.stderr)
        return 1


def cmd_classify(args: argparse.Namespace) -> int:
    """CLI handler for classify command."""
    result = classify_profile(args.profile_id)

    print(f'profile_id: {result["profile_id"]}')
    print(f'classification: {result["classification"]}')
    print(f'reason: {result["reason"]}')
    print(f'confidence: {result["confidence"]}')

    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    """CLI handler for suggest command."""
    try:
        suggestions = suggest_classifications(args.project_dir)

        print(f'count: {len(suggestions)}')
        if suggestions:
            print()
            print_toon_table('suggestions', suggestions, ['profile_id', 'suggested', 'confidence', 'reason'])

        return 0
    except DataNotFoundError as e:
        print(f'error: {e}', file=sys.stderr)
        return 1
    except Exception as e:
        print(f'error: {e}', file=sys.stderr)
        return 1


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description='Maven profile management operations')
    parser.add_argument('--project-dir', default='.', help='Project directory (default: current directory)')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # list - List all profiles
    list_parser = subparsers.add_parser('list', help='List Maven profiles from all modules')
    list_parser.add_argument('--module', help='Filter by module name')

    # unmatched - List unmatched profiles
    subparsers.add_parser('unmatched', help='List unmatched profiles (NO-MATCH-FOUND)')

    # classify - Classify a single profile
    classify_parser = subparsers.add_parser('classify', help='Classify a profile by pattern matching')
    classify_parser.add_argument('profile_id', help='Profile ID to classify')

    # suggest - Suggest classifications for unmatched
    subparsers.add_parser('suggest', help='Suggest classifications for unmatched profiles')

    args = parser.parse_args()

    handlers = {
        'list': cmd_list,
        'unmatched': cmd_unmatched,
        'classify': cmd_classify,
        'suggest': cmd_suggest,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
