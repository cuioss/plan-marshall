#!/usr/bin/env python3
"""
doctor-marketplace.py - Batch marketplace analysis and fixing.

Provides automated batch operations across the entire marketplace:
- scan: Discover all components (agents, commands, skills, scripts)
- analyze: Batch analyze all components for issues
- fix: Apply safe fixes automatically across marketplace
- report: Generate comprehensive report for LLM review

This is Phase 1 of the hybrid doctor workflow. It handles deterministic
operations that can be fully automated. Phase 2 (LLM) handles semantic
analysis and complex fixes.

Output: JSON to stdout.

Usage:
    python3 doctor-marketplace.py scan [--bundles NAMES]
    python3 doctor-marketplace.py analyze [--bundles NAMES] [--type TYPE]
    python3 doctor-marketplace.py fix [--bundles NAMES] [--dry-run]
    python3 doctor-marketplace.py report [--bundles NAMES] [--output FILE]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from _doctor_analysis import analyze_component
from _doctor_fixes import apply_safe_fixes
from _doctor_report import generate_report
from _doctor_shared import (
    categorize_all_issues,
    discover_components,
    ensure_report_dir,
    find_bundles,
    find_marketplace_root,
    get_report_dir,
    get_report_filename,
)

SCRIPT_DIR = Path(__file__).parent

# =============================================================================
# Subcommands
# =============================================================================


def cmd_scan(args) -> int:
    """Scan marketplace and list all components."""
    marketplace_root = find_marketplace_root()
    if not marketplace_root:
        print(json.dumps({'error': 'Marketplace directory not found'}), file=sys.stderr)
        return 1

    bundle_filter = None
    if args.bundles:
        bundle_filter = {b.strip() for b in args.bundles.split(',') if b.strip()}

    bundles = find_bundles(marketplace_root, bundle_filter)

    results: dict[str, object] = {
        'marketplace_root': str(marketplace_root),
        'bundles': [],
        'total_bundles': 0,
        'total_components': 0,
    }
    bundles_list: list[dict] = []

    total_components = 0
    for bundle_dir in bundles:
        components = discover_components(bundle_dir)
        bundle_total = sum(len(v) for v in components.values())
        total_components += bundle_total

        bundles_list.append(
            {
                'name': bundle_dir.name,
                'path': str(bundle_dir),
                'components': components,
                'counts': {
                    'agents': len(components['agents']),
                    'commands': len(components['commands']),
                    'skills': len(components['skills']),
                    'scripts': len(components['scripts']),
                    'total': bundle_total,
                },
            }
        )

    results['bundles'] = bundles_list
    results['total_bundles'] = len(bundles)
    results['total_components'] = total_components

    print(json.dumps(results, indent=2))
    return 0


def cmd_analyze(args) -> int:
    """Analyze all components for issues."""
    marketplace_root = find_marketplace_root()
    if not marketplace_root:
        print(json.dumps({'error': 'Marketplace directory not found'}), file=sys.stderr)
        return 1

    bundle_filter = None
    if args.bundles:
        bundle_filter = {b.strip() for b in args.bundles.split(',') if b.strip()}

    type_filter = None
    if args.type:
        type_filter = {t.strip() for t in args.type.split(',') if t.strip()}

    bundles = find_bundles(marketplace_root, bundle_filter)

    all_analysis = []
    total_issues = 0

    for bundle_dir in bundles:
        components = discover_components(bundle_dir)

        # Filter by type if specified
        component_list = []
        if not type_filter or 'agent' in type_filter or 'agents' in type_filter:
            component_list.extend(components['agents'])
        if not type_filter or 'command' in type_filter or 'commands' in type_filter:
            component_list.extend(components['commands'])
        if not type_filter or 'skill' in type_filter or 'skills' in type_filter:
            component_list.extend(components['skills'])

        for component in component_list:
            result = analyze_component(component)
            result['bundle'] = bundle_dir.name
            all_analysis.append(result)
            total_issues += result.get('issue_count', 0)

    # Categorize all issues
    all_issues = []
    for result in all_analysis:
        all_issues.extend(result.get('issues', []))

    categorized = categorize_all_issues(all_issues)

    output = {
        'analysis': all_analysis,
        'summary': {
            'total_components': len(all_analysis),
            'total_issues': total_issues,
            'safe_fixes': len(categorized['safe']),
            'risky_fixes': len(categorized['risky']),
            'unfixable': len(categorized['unfixable']),
        },
        'categorized': categorized,
    }

    print(json.dumps(output, indent=2))
    return 0


def cmd_fix(args) -> int:
    """Apply safe fixes across marketplace."""
    marketplace_root = find_marketplace_root()
    if not marketplace_root:
        print(json.dumps({'error': 'Marketplace directory not found'}), file=sys.stderr)
        return 1

    bundle_filter = None
    if args.bundles:
        bundle_filter = {b.strip() for b in args.bundles.split(',') if b.strip()}

    bundles = find_bundles(marketplace_root, bundle_filter)

    # First analyze to find issues
    all_issues = []
    for bundle_dir in bundles:
        components = discover_components(bundle_dir)
        for comp_type in ['agents', 'commands', 'skills']:
            for component in components[comp_type]:
                result = analyze_component(component)
                all_issues.extend(result.get('issues', []))

    # Categorize and get safe fixes only
    categorized = categorize_all_issues(all_issues)
    safe_issues = categorized['safe']

    if not safe_issues:
        output = {
            'status': 'no_fixes_needed',
            'message': 'No safe fixes to apply',
            'dry_run': args.dry_run,
            'total_issues': len(all_issues),
            'risky_issues': len(categorized['risky']),
            'unfixable_issues': len(categorized['unfixable']),
        }
        print(json.dumps(output, indent=2))
        return 0

    # Apply safe fixes
    fix_results = apply_safe_fixes(safe_issues, marketplace_root, SCRIPT_DIR, args.dry_run)

    output = {
        'status': 'completed',
        'dry_run': args.dry_run,
        'total_safe_issues': len(safe_issues),
        'applied': len(fix_results['applied']),
        'failed': len(fix_results['failed']),
        'skipped': len(fix_results['skipped']),
        'details': fix_results,
        'remaining': {'risky_issues': len(categorized['risky']), 'unfixable_issues': len(categorized['unfixable'])},
    }

    print(json.dumps(output, indent=2))
    return 0 if not fix_results['failed'] else 1


def cmd_report(args) -> int:
    """Generate comprehensive report for LLM review."""
    marketplace_root = find_marketplace_root()
    if not marketplace_root:
        print(json.dumps({'error': 'Marketplace directory not found'}), file=sys.stderr)
        return 1

    bundle_filter = None
    if args.bundles:
        bundle_filter = {b.strip() for b in args.bundles.split(',') if b.strip()}

    bundles = find_bundles(marketplace_root, bundle_filter)

    # Scan
    scan_results = {'total_bundles': len(bundles), 'total_components': 0}

    # Analyze all
    all_analysis = []
    for bundle_dir in bundles:
        components = discover_components(bundle_dir)
        total = sum(len(v) for v in components.values())
        scan_results['total_components'] += total

        for comp_type in ['agents', 'commands', 'skills']:
            for component in components[comp_type]:
                result = analyze_component(component)
                result['bundle'] = bundle_dir.name
                all_analysis.append(result)

    # Generate report
    report = generate_report(scan_results, all_analysis)

    # Determine output directory and filename
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

    # Determine scope for filename
    if len(bundles) == 1:
        # Single bundle - use bundle name
        scope = bundles[0].name
    elif bundle_filter:
        # Multiple specific bundles - join names (limit length)
        scope = '-'.join(sorted(bundle_filter)[:3])
        if len(bundle_filter) > 3:
            scope += f'-and-{len(bundle_filter) - 3}-more'
    else:
        # All bundles
        scope = 'marketplace'

    if args.output:
        report_dir = Path(args.output)
    else:
        report_dir = get_report_dir()

    json_filename = get_report_filename(timestamp, scope)

    # Create directory and write JSON report
    ensure_report_dir(report_dir)
    json_path = report_dir / json_filename
    findings_filename = f'{timestamp}-{scope}-findings.md'

    output_json = json.dumps(report, indent=2)
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(output_json)

    # Output success message
    print(
        json.dumps(
            {
                'status': 'success',
                'report_dir': str(report_dir),
                'report_file': str(json_path),
                'findings_file': str(report_dir / findings_filename),
                'summary': report['summary'],
                'next_step': 'LLM should read report_file and create findings.md with analysis',
            },
            indent=2,
        )
    )

    return 0


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description='Batch marketplace analysis and fixing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan entire marketplace
  %(prog)s scan

  # Scan specific bundles
  %(prog)s scan --bundles pm-dev-java,pm-workflow

  # Analyze all components
  %(prog)s analyze

  # Analyze only agents and commands
  %(prog)s analyze --type agents,commands

  # Preview safe fixes (dry run)
  %(prog)s fix --dry-run

  # Apply safe fixes
  %(prog)s fix

  # Generate report for LLM review
  %(prog)s report --output .plan/temp/my-report
""",
    )

    subparsers = parser.add_subparsers(dest='command', help='Operation to perform')

    # scan subcommand
    p_scan = subparsers.add_parser('scan', help='Scan marketplace components')
    p_scan.add_argument('--bundles', help='Comma-separated list of bundle names to scan')
    p_scan.set_defaults(func=cmd_scan)

    # analyze subcommand
    p_analyze = subparsers.add_parser('analyze', help='Analyze all components for issues')
    p_analyze.add_argument('--bundles', help='Comma-separated list of bundle names')
    p_analyze.add_argument('--type', help='Component types to analyze (agents,commands,skills)')
    p_analyze.set_defaults(func=cmd_analyze)

    # fix subcommand
    p_fix = subparsers.add_parser('fix', help='Apply safe fixes across marketplace')
    p_fix.add_argument('--bundles', help='Comma-separated list of bundle names')
    p_fix.add_argument('--dry-run', action='store_true', help='Preview fixes without applying')
    p_fix.set_defaults(func=cmd_fix)

    # report subcommand
    p_report = subparsers.add_parser('report', help='Generate comprehensive report')
    p_report.add_argument('--bundles', help='Comma-separated list of bundle names')
    p_report.add_argument('--output', '-o', help='Output directory for report')
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
