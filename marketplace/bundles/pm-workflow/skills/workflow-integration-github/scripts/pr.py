#!/usr/bin/env python3
"""
PR workflow operations - fetch comments and triage them.

Usage:
    pr.py fetch-comments [--pr <number>]
    pr.py triage --comment <json>
    pr.py --help

Subcommands:
    fetch-comments    Fetch PR review comments from GitHub
    triage           Triage a single PR review comment

Examples:
    # Fetch comments for current branch's PR
    pr.py fetch-comments

    # Fetch comments for specific PR
    pr.py fetch-comments --pr 123

    # Triage a single comment
    pr.py triage --comment '{"id":"C1","body":"Please fix this","path":"src/Main.java","line":42}'
"""

import argparse
import json
import re
import subprocess
import sys


# ============================================================================
# TRIAGE CONFIGURATION
# ============================================================================

# Patterns for classification
PATTERNS = {
    "code_change": {
        "high": [
            r"security",
            r"vulnerability",
            r"injection",
            r"xss",
            r"csrf",
            r"bug",
            r"error",
            r"fix",
            r"broken",
            r"crash",
            r"null pointer",
            r"memory leak"
        ],
        "medium": [
            r"please\s+(?:add|remove|change|fix|update)",
            r"should\s+(?:be|have|use)",
            r"missing",
            r"incorrect",
            r"wrong"
        ],
        "low": [
            r"rename",
            r"variable name",
            r"naming",
            r"typo",
            r"spelling",
            r"formatting",
            r"style"
        ]
    },
    "explain": [
        r"why",
        r"explain",
        r"reasoning",
        r"rationale",
        r"how does",
        r"what is",
        r"can you clarify",
        r"\?"
    ],
    "ignore": [
        r"^lgtm",
        r"^approved",
        r"looks good",
        r"^nice",
        r"^thanks",
        r"\[bot\]",
        r"^nit:",
        r"^nitpick:"
    ]
}


# ============================================================================
# FETCH-COMMENTS SUBCOMMAND
# ============================================================================

def run_gh_command(args: list) -> tuple:
    """Run gh CLI command and return stdout, stderr, return code."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", "gh CLI not installed or not in PATH", 1


def get_current_pr_number() -> int:
    """Get PR number for current branch."""
    stdout, stderr, code = run_gh_command([
        "pr", "view", "--json", "number", "--jq", ".number"
    ])

    if code != 0:
        return None

    try:
        return int(stdout.strip())
    except ValueError:
        return None


def fetch_comments(pr_number: int) -> dict:
    """Fetch review comments for a PR."""
    # Fetch review threads with comments
    stdout, stderr, code = run_gh_command([
        "pr", "view", str(pr_number),
        "--json", "reviewThreads",
        "--jq", ".reviewThreads"
    ])

    if code != 0:
        return {
            "error": f"Failed to fetch PR: {stderr}",
            "status": "failure"
        }

    try:
        threads = json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError:
        return {
            "error": f"Failed to parse gh output: {stdout}",
            "status": "failure"
        }

    # Extract comments from threads
    comments = []
    for thread in threads:
        if "comments" not in thread:
            continue

        for comment in thread["comments"]:
            comments.append({
                "id": comment.get("id", "unknown"),
                "author": comment.get("author", {}).get("login", "unknown"),
                "body": comment.get("body", ""),
                "path": comment.get("path"),
                "line": comment.get("line"),
                "resolved": thread.get("isResolved", False)
            })

    return {
        "pr_number": pr_number,
        "comments": comments,
        "total_comments": len(comments),
        "unresolved_count": sum(1 for c in comments if not c["resolved"]),
        "status": "success"
    }


def cmd_fetch_comments(args):
    """Handle fetch-comments subcommand."""
    # Determine PR number
    pr_number = args.pr
    if not pr_number:
        pr_number = get_current_pr_number()
        if not pr_number:
            print(json.dumps({
                "error": "No PR found for current branch. Use --pr to specify.",
                "status": "failure"
            }, indent=2))
            return 1

    result = fetch_comments(pr_number)
    print(json.dumps(result, indent=2))

    return 0 if result.get("status") == "success" else 1


# ============================================================================
# TRIAGE SUBCOMMAND
# ============================================================================

def classify_comment(body: str) -> tuple:
    """Classify comment and determine action and priority."""
    body_lower = body.lower()

    # Check for ignore patterns first
    for pattern in PATTERNS["ignore"]:
        if re.search(pattern, body_lower):
            return "ignore", "none", "Automated or acknowledgment comment"

    # Check for code change patterns with priority
    for priority in ["high", "medium", "low"]:
        for pattern in PATTERNS["code_change"][priority]:
            if re.search(pattern, body_lower):
                return "code_change", priority, f"Matches {priority} priority pattern: {pattern}"

    # Check for explanation patterns
    for pattern in PATTERNS["explain"]:
        if re.search(pattern, body_lower):
            return "explain", "low", "Question or clarification request"

    # Default to code_change with low priority if none match
    if len(body) > 50:  # Substantial comment likely needs attention
        return "code_change", "low", "Substantial review comment requires attention"

    return "ignore", "none", "Brief comment with no actionable content"


def suggest_implementation(action: str, body: str, path: str, line: int) -> str:
    """Generate implementation suggestion based on action type."""
    if action == "ignore":
        return None

    if action == "explain":
        return f"Reply to comment at {path}:{line} with explanation of design decision"

    # For code_change, try to extract specific action
    body_lower = body.lower()

    if "add" in body_lower:
        return f"Add requested code/functionality at {path}:{line}"
    elif "remove" in body_lower or "delete" in body_lower:
        return f"Remove indicated code at {path}:{line}"
    elif "rename" in body_lower:
        return f"Rename as suggested at {path}:{line}"
    elif "fix" in body_lower:
        return f"Fix the issue indicated at {path}:{line}"
    else:
        return f"Review and address comment at {path}:{line}"


def triage_comment(comment: dict) -> dict:
    """Triage a single comment and return decision."""
    comment_id = comment.get("id", "unknown")
    body = comment.get("body", "")
    path = comment.get("path")
    line = comment.get("line")
    author = comment.get("author", "unknown")

    if not body:
        return {
            "comment_id": comment_id,
            "action": "ignore",
            "reason": "Empty comment body",
            "priority": "none",
            "suggested_implementation": None,
            "status": "success"
        }

    action, priority, reason = classify_comment(body)
    suggestion = suggest_implementation(action, body, path, line)

    return {
        "comment_id": comment_id,
        "author": author,
        "action": action,
        "reason": reason,
        "priority": priority,
        "location": f"{path}:{line}" if path and line else None,
        "suggested_implementation": suggestion,
        "status": "success"
    }


def cmd_triage(args):
    """Handle triage subcommand."""
    try:
        comment = json.loads(args.comment)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "error": f"Invalid JSON input: {e}",
            "status": "failure"
        }, indent=2))
        return 1

    result = triage_comment(comment)
    print(json.dumps(result, indent=2))

    return 0 if result.get("status") == "success" else 1


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PR workflow operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pr.py fetch-comments --pr 123
  pr.py triage --comment '{"id":"C1","body":"Please fix this"}'
"""
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # fetch-comments subcommand
    fetch_parser = subparsers.add_parser(
        "fetch-comments",
        help="Fetch PR review comments from GitHub"
    )
    fetch_parser.add_argument(
        "--pr",
        type=int,
        help="PR number (default: current branch's PR)"
    )
    fetch_parser.set_defaults(func=cmd_fetch_comments)

    # triage subcommand
    triage_parser = subparsers.add_parser(
        "triage",
        help="Triage a single PR review comment"
    )
    triage_parser.add_argument(
        "--comment",
        required=True,
        help="JSON string with comment data"
    )
    triage_parser.set_defaults(func=cmd_triage)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
