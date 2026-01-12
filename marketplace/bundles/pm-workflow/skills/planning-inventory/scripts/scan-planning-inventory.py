#!/usr/bin/env python3
"""
scan-planning-inventory.py

Scans marketplace for all planning-related components across bundles.
Uses marketplace-inventory with predefined planning patterns and organizes
results into core and derived categories.

Usage:
    python3 scan-planning-inventory.py [options]

Options:
    --format <value>        Output format: full, summary (default: full)
    --include-descriptions  Include component descriptions from frontmatter

Exit codes:
    0 - Success (JSON output)
    1 - Error (marketplace-inventory failed)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Planning-related name patterns
PLANNING_PATTERNS = [
    "plan-*",              # Core planning skills (plan-init, plan-execute, plan-finalize, etc.)
    "manage-*",            # Management skills (manage-tasks, manage-plan-documents, etc.)
    "*-workflow",          # Workflow skills (pr-workflow, git-workflow, etc.)
    "task-*",              # Task commands (task-implement)
    "pr-*",                # PR commands (pr-doctor) - note: also matches pr-workflow
    "*-task-plan",         # Task plan skills (plugin-task-plan)
    "*-solution-outline",  # Solution outline skills (plugin-solution-outline)
    "*-plan-*",            # Plan-prefixed skills (plugin-plan-implement)
]

# Bundles that contain planning-related components
# Note: pm-dev-java and pm-dev-frontend removed - they no longer have planning-specific components
PLANNING_BUNDLES = [
    "pm-workflow",
    "pm-plugin-development",
]

# Core planning bundle name
CORE_BUNDLE = "pm-workflow"


def find_marketplace_inventory_script() -> Path:
    """Find the marketplace-inventory script."""
    # Try relative to this script's location
    this_script = Path(__file__).resolve()
    marketplace_bundles = this_script.parent.parent.parent.parent.parent

    inventory_script = (
        marketplace_bundles /
        "plan-marshall" /
        "skills" /
        "marketplace-inventory" /
        "scripts" /
        "scan-marketplace-inventory.py"
    )

    if inventory_script.exists():
        return inventory_script

    # Try from cwd
    cwd_path = Path.cwd() / "marketplace/bundles/plan-marshall/skills/marketplace-inventory/scripts/scan-marketplace-inventory.py"
    if cwd_path.exists():
        return cwd_path

    raise FileNotFoundError("Cannot find scan-marketplace-inventory.py")


def run_marketplace_inventory(include_descriptions: bool) -> dict:
    """Run marketplace-inventory with planning filters."""
    script_path = find_marketplace_inventory_script()

    args = [
        sys.executable,
        str(script_path),
        "--bundles", ",".join(PLANNING_BUNDLES),
        "--name-pattern", "|".join(PLANNING_PATTERNS),
    ]

    if include_descriptions:
        args.append("--include-descriptions")

    result = subprocess.run(args, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"marketplace-inventory failed: {result.stderr}")

    return json.loads(result.stdout)


def categorize_components(inventory: dict) -> dict:
    """Categorize components into core and derived."""
    core = {
        "bundle": CORE_BUNDLE,
        "agents": [],
        "commands": [],
        "skills": [],
        "scripts": [],
    }
    derived = []

    for bundle in inventory.get("bundles", []):
        bundle_name = bundle["name"]

        if bundle_name == CORE_BUNDLE:
            core["agents"] = bundle.get("agents", [])
            core["commands"] = bundle.get("commands", [])
            core["skills"] = bundle.get("skills", [])
            core["scripts"] = bundle.get("scripts", [])
        else:
            # Derived bundle - only include if it has planning components
            if any(bundle.get(k) for k in ["agents", "commands", "skills", "scripts"]):
                derived.append({
                    "bundle": bundle_name,
                    "agents": bundle.get("agents", []),
                    "commands": bundle.get("commands", []),
                    "skills": bundle.get("skills", []),
                    "scripts": bundle.get("scripts", []),
                    "statistics": bundle.get("statistics", {}),
                })

    return {
        "core": core,
        "derived": derived,
    }


def calculate_statistics(categorized: dict) -> dict:
    """Calculate statistics for categorized components."""
    core = categorized["core"]
    derived = categorized["derived"]

    core_stats = {
        "agents": len(core["agents"]),
        "commands": len(core["commands"]),
        "skills": len(core["skills"]),
        "scripts": len(core["scripts"]),
    }
    core_stats["total"] = sum(core_stats.values())

    derived_stats = {
        "bundles": len(derived),
        "agents": sum(len(d["agents"]) for d in derived),
        "commands": sum(len(d["commands"]) for d in derived),
        "skills": sum(len(d["skills"]) for d in derived),
        "scripts": sum(len(d["scripts"]) for d in derived),
    }
    derived_stats["total"] = (
        derived_stats["agents"] +
        derived_stats["commands"] +
        derived_stats["skills"] +
        derived_stats["scripts"]
    )

    return {
        "core": core_stats,
        "derived": derived_stats,
        "total_components": core_stats["total"] + derived_stats["total"],
    }


def generate_summary(categorized: dict, stats: dict) -> dict:
    """Generate summary output format."""
    core = categorized["core"]
    derived = categorized["derived"]

    return {
        "core_bundle": CORE_BUNDLE,
        "core_components": [
            {"type": "skills", "names": [s["name"] for s in core["skills"]]},
            {"type": "agents", "names": [a["name"] for a in core["agents"]]},
            {"type": "commands", "names": [c["name"] for c in core["commands"]]},
        ],
        "derived_bundles": [
            {
                "bundle": d["bundle"],
                "agents": [a["name"] for a in d["agents"]],
                "skills": [s["name"] for s in d["skills"]],
            }
            for d in derived
        ],
        "statistics": stats,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scan marketplace for planning-related components"
    )
    parser.add_argument(
        "--format",
        choices=["full", "summary"],
        default="full",
        help="Output format (default: full)"
    )
    parser.add_argument(
        "--include-descriptions",
        action="store_true",
        help="Include component descriptions from frontmatter"
    )

    args = parser.parse_args()

    try:
        # Run marketplace inventory with planning filters
        inventory = run_marketplace_inventory(args.include_descriptions)

        # Categorize into core and derived
        categorized = categorize_components(inventory)

        # Calculate statistics
        stats = calculate_statistics(categorized)

        # Generate output
        if args.format == "summary":
            output = generate_summary(categorized, stats)
        else:
            output = {
                "patterns": PLANNING_PATTERNS,
                "bundles_scanned": PLANNING_BUNDLES,
                **categorized,
                "statistics": stats,
            }

        print(json.dumps(output, indent=2))
        return 0

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON from marketplace-inventory: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
