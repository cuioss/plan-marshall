#!/usr/bin/env python3
"""Filter inventory by bundle and component type.

Usage:
    filter-inventory.py filter --plan-id ID --bundle NAME --component-type TYPE

Output (TOON):
    status: success
    bundle: pm-dev-java
    component_type: skills
    file_count: 17
    files[17]:
      marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
      ...
"""

import argparse
import sys
from pathlib import Path

# Add plan-marshall modules to path
sys.path.insert(0, str(Path(__file__).parents[5]))
from marketplace.bundles.plan_marshall.skills.ref_toon_format.scripts.toon_parser import parse_toon


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
        print(f"  {path}")


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

    args = parser.parse_args()

    if args.command == "filter":
        filter_inventory(args.plan_id, args.bundle, args.component_type)


if __name__ == "__main__":
    main()
