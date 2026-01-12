#!/usr/bin/env python3
"""Report generation functions for doctor-marketplace."""

from typing import Dict, List, Optional

from _doctor_shared import categorize_all_issues, extract_bundle_name
from _cmd_categorize import categorize_fix


def count_issues_by_type(all_issues: List[Dict]) -> Dict[str, int]:
    """Count issues by their type."""
    counts: Dict[str, int] = {}
    for issue in all_issues:
        itype = issue.get("type", "unknown")
        counts[itype] = counts.get(itype, 0) + 1
    return counts


def count_issues_by_bundle(analysis_results: List[Dict]) -> Dict[str, Dict[str, int]]:
    """Count issues by bundle with safe/risky breakdown."""
    counts: Dict[str, Dict[str, int]] = {}
    for result in analysis_results:
        path = result.get("component", {}).get("path", "")
        bundle_name = extract_bundle_name(path)

        if bundle_name not in counts:
            counts[bundle_name] = {"total": 0, "safe": 0, "risky": 0}

        for issue in result.get("issues", []):
            counts[bundle_name]["total"] += 1
            if issue.get("fixable", False):
                cat = categorize_fix(issue)
                counts[bundle_name]["safe" if cat == "safe" else "risky"] += 1

    return counts


def extract_components_for_tool_analysis(analysis_results: List[Dict]) -> List[Dict]:
    """Extract components needing semantic tool coverage analysis by LLM."""
    components = []
    for result in analysis_results:
        tc = result.get("analysis", {}).get("coverage", {}).get("tool_coverage", {})
        if tc.get("needs_llm_analysis"):
            comp = result.get("component", {})
            components.append({
                "file": comp.get("path", ""),
                "type": comp.get("type", ""),
                "bundle": result.get("bundle", ""),
                "declared_tools": tc.get("declared_tools", [])
            })
    return components


def build_llm_review_items(categorized: Dict) -> List[Dict]:
    """Build list of items requiring LLM review."""
    items = []
    for issue in categorized["risky"]:
        items.append({
            "type": issue.get("type"),
            "file": issue.get("file"),
            "description": issue.get("description", ""),
            "action_required": "Review and confirm fix"
        })
    for issue in categorized["unfixable"]:
        items.append({
            "type": issue.get("type"),
            "file": issue.get("file"),
            "description": issue.get("description", ""),
            "action_required": "Manual investigation required"
        })
    return items


def generate_report(scan_results: Dict, analysis_results: List[Dict], fix_results: Optional[Dict] = None) -> Dict:
    """Generate comprehensive report for LLM review.

    Includes:
    - Deterministic issues found by script (structural violations)
    - Components needing tool coverage analysis by LLM (semantic work)
    """
    # Aggregate all issues
    all_issues = []
    for result in analysis_results:
        all_issues.extend(result.get("issues", []))

    categorized = categorize_all_issues(all_issues)
    components_for_tool_analysis = extract_components_for_tool_analysis(analysis_results)

    report = {
        "summary": {
            "total_bundles": scan_results.get("total_bundles", 0),
            "total_components": scan_results.get("total_components", 0),
            "total_issues": len(all_issues),
            "safe_fixes": len(categorized["safe"]),
            "risky_fixes": len(categorized["risky"]),
            "unfixable": len(categorized["unfixable"]),
            "components_needing_tool_analysis": len(components_for_tool_analysis)
        },
        "issues_by_type": count_issues_by_type(all_issues),
        "issues_by_bundle": count_issues_by_bundle(analysis_results),
        "safe_fixes": categorized["safe"],
        "risky_fixes": categorized["risky"],
        "unfixable_issues": categorized["unfixable"],
        "components_for_tool_analysis": components_for_tool_analysis,
        "llm_review_items": build_llm_review_items(categorized)
    }

    if fix_results:
        report["fix_results"] = {
            "applied": len(fix_results.get("applied", [])),
            "failed": len(fix_results.get("failed", [])),
            "skipped": len(fix_results.get("skipped", []))
        }

    return report
