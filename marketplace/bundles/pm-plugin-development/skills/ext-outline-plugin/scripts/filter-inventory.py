#!/usr/bin/env python3
"""Filter inventory by bundle and component type.

Usage:
    filter-inventory.py filter --plan-id ID --bundle NAME --component-type TYPE
    filter-inventory.py impact-analysis --plan-id ID

Output (TOON):
    status: success
    bundle: pm-dev-java
    component_type: skills
    file_count: 17
    files[17]:
      - marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
      - ...
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]


def file_path_to_notation(path: str) -> str | None:
    """Convert file path to component notation.

    Patterns:
        marketplace/bundles/{b}/skills/{s}/SKILL.md → {b}:{s}
        marketplace/bundles/{b}/commands/{c}.md → {b}:commands:{c}
        marketplace/bundles/{b}/agents/{a}.md → {b}:agents:{a}
    """
    parts = path.split('/')
    if 'skills' in parts:
        idx = parts.index('skills')
        if idx > 0 and idx + 1 < len(parts):
            return f"{parts[idx - 1]}:{parts[idx + 1]}"
    if 'commands' in parts:
        idx = parts.index('commands')
        if idx > 0 and idx + 1 < len(parts):
            return f"{parts[idx - 1]}:commands:{parts[idx + 1].replace('.md', '')}"
    if 'agents' in parts:
        idx = parts.index('agents')
        if idx > 0 and idx + 1 < len(parts):
            return f"{parts[idx - 1]}:agents:{parts[idx + 1].replace('.md', '')}"
    return None


def notation_to_file_path(notation: str) -> str | None:
    """Convert component notation to file path.

    Patterns:
        {b}:{s} → marketplace/bundles/{b}/skills/{s}/SKILL.md
        {b}:commands:{c} → marketplace/bundles/{b}/commands/{c}.md
        {b}:agents:{a} → marketplace/bundles/{b}/agents/{a}.md
        {b}:{s}:{sc} → marketplace/bundles/{b}/skills/{s}/scripts/{sc}.py
    """
    parts = notation.split(":")
    if len(parts) == 2:
        bundle, skill = parts
        return f"marketplace/bundles/{bundle}/skills/{skill}/SKILL.md"
    if len(parts) == 3:
        bundle, middle, name = parts
        if middle == "commands":
            return f"marketplace/bundles/{bundle}/commands/{name}.md"
        if middle == "agents":
            return f"marketplace/bundles/{bundle}/agents/{name}.md"
        # Script: bundle:skill:script
        return f"marketplace/bundles/{bundle}/skills/{middle}/scripts/{name}.py"
    return None


def get_component_type(file_path: str) -> str:
    """Determine component type from file path."""
    if '/skills/' in file_path:
        return 'skills'
    if '/commands/' in file_path:
        return 'commands'
    if '/agents/' in file_path:
        return 'agents'
    return 'unknown'


def log_decision(plan_id: str, message: str) -> None:
    """Log a decision to the plan's decision log."""
    subprocess.run(
        [
            sys.executable, '.plan/execute-script.py',
            'plan-marshall:manage-logging:manage-log',
            'decision', plan_id, 'INFO',
            f'(pm-plugin-development:ext-outline-plugin) {message}'
        ],
        capture_output=True,
        text=True
    )


def impact_analysis(plan_id: str) -> None:
    """Run impact analysis: resolve rdeps and expand inventory."""
    plan_dir = Path(".plan/plans") / plan_id
    inventory_path = plan_dir / "work" / "inventory_filtered.toon"
    dep_analysis_path = plan_dir / "work" / "dependency_analysis.toon"

    if not inventory_path.exists():
        print("status: error")
        print(f"message: Inventory not found: {inventory_path}")
        sys.exit(1)

    # Read current inventory
    content = inventory_path.read_text()
    inventory = parse_toon(content)

    # Get all primary files from inventory
    primary_files: list[str] = []
    for component_type in ['skills', 'commands', 'agents']:
        primary_files.extend(inventory.get('inventory', {}).get(component_type, []))

    # Convert paths to notations (filter out None values)
    notations: list[str] = [
        n for f in primary_files
        if (n := file_path_to_notation(f)) is not None
    ]

    # Resolve reverse dependencies for each component
    all_dependents: set[str] = set()
    for notation in notations:
        result = subprocess.run(
            [
                sys.executable, '.plan/execute-script.py',
                'pm-plugin-development:tools-marketplace-inventory:resolve-dependencies',
                'rdeps', '--component', notation, '--dep-types', 'skill,script',
                '--direct-result', '--format', 'json'
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("status: error")
            print(f"message: resolve-dependencies failed for {notation}")
            print(f"stderr: {result.stderr}")
            sys.exit(1)

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("status: error")
            print(f"message: Invalid JSON from resolve-dependencies for {notation}")
            print(f"stdout: {result.stdout}")
            sys.exit(1)

        if data.get('status') == 'error':
            print("status: error")
            print(f"message: resolve-dependencies error: {data.get('error', 'unknown')}")
            sys.exit(1)

        for dep in data.get('dependents', []):
            all_dependents.add(dep['component'])

    # Expand inventory with dependents not already in scope
    added: list[str] = []
    for dep_notation in all_dependents:
        file_path = notation_to_file_path(dep_notation)
        if file_path and file_path not in primary_files:
            added.append(file_path)
            component_type = get_component_type(file_path)
            if component_type != 'unknown':
                if 'inventory' not in inventory:
                    inventory['inventory'] = {}
                if component_type not in inventory['inventory']:
                    inventory['inventory'][component_type] = []
                inventory['inventory'][component_type].append(file_path)

    # Write expanded inventory
    inventory_path.write_text(serialize_toon(inventory))

    # Write dependency analysis
    analysis = {
        'status': 'success',
        'primary_count': len(primary_files),
        'dependents_found': len(all_dependents),
        'dependents_added': len(added),
        'added_files': added,
    }
    dep_analysis_path.write_text(serialize_toon(analysis))

    # Log decision
    log_decision(plan_id, f"Impact analysis: found {len(all_dependents)} dependents, adding {len(added)} to scope")

    # Output result
    print("status: success")
    print(f"primary_count: {len(primary_files)}")
    print(f"dependents_found: {len(all_dependents)}")
    print(f"dependents_added: {len(added)}")


def filter_inventory(plan_id: str, bundle: str, component_type: str) -> None:
    """Filter inventory_filtered.toon by bundle and component type."""
    plan_dir = Path(".plan/plans") / plan_id
    inventory_path = plan_dir / "work" / "inventory_filtered.toon"

    if not inventory_path.exists():
        print("status: error")
        print(f"message: Inventory not found: {inventory_path}")
        sys.exit(1)

    # Parse inventory
    content = inventory_path.read_text()
    data = parse_toon(content)

    # Get inventory section
    inventory = data.get("inventory", {})
    all_paths = inventory.get(component_type, [])

    if not all_paths:
        print("status: success")
        print(f"bundle: {bundle}")
        print(f"component_type: {component_type}")
        print("file_count: 0")
        print("files[0]:")
        return

    # Filter by bundle - path pattern: marketplace/bundles/{bundle}/...
    bundle_prefix = f"marketplace/bundles/{bundle}/"
    filtered = [p for p in all_paths if p.startswith(bundle_prefix)]

    # Output
    print("status: success")
    print(f"bundle: {bundle}")
    print(f"component_type: {component_type}")
    print(f"file_count: {len(filtered)}")
    print(f"files[{len(filtered)}]:")
    for path in filtered:
        print(f"  - {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter inventory by bundle and component type")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # filter command
    filter_cmd = subparsers.add_parser("filter", help="Filter inventory")
    filter_cmd.add_argument("--plan-id", required=True, help="Plan identifier")
    filter_cmd.add_argument("--bundle", required=True, help="Bundle name to filter")
    filter_cmd.add_argument("--component-type", required=True,
                           choices=["skills", "commands", "agents"],
                           help="Component type to filter")

    # impact-analysis command
    impact_cmd = subparsers.add_parser("impact-analysis", help="Resolve rdeps and expand inventory")
    impact_cmd.add_argument("--plan-id", required=True, help="Plan identifier")

    args = parser.parse_args()

    if args.command == "filter":
        filter_inventory(args.plan_id, args.bundle, args.component_type)
    elif args.command == "impact-analysis":
        impact_analysis(args.plan_id)


if __name__ == "__main__":
    main()
