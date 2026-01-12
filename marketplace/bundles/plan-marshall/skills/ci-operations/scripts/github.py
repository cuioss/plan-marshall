#!/usr/bin/env python3
"""GitHub operations via gh CLI.

Subcommands:
    pr create       Create a pull request
    pr reviews      Get PR reviews
    ci status       Check CI status for a PR
    ci wait         Wait for CI to complete
    issue create    Create an issue

Usage:
    python3 github.py pr create --title "Title" --body "Body" [--base main] [--draft]
    python3 github.py pr reviews --pr-number 123
    python3 github.py ci status --pr-number 123
    python3 github.py ci wait --pr-number 123 [--timeout 300] [--interval 30]
    python3 github.py issue create --title "Title" --body "Body" [--labels "bug,priority:high"]

Output: TOON format
"""

import argparse
import json
import subprocess
import sys
import time


def run_gh(args: list[str], capture_json: bool = False) -> tuple[int, str, str]:
    """Run gh CLI command and return (returncode, stdout, stderr)."""
    cmd = ["gh"] + args
    if capture_json:
        cmd.extend(["--json"] if "--json" not in args else [])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", "gh CLI not found. Install from https://cli.github.com/"
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def check_auth() -> tuple[bool, str]:
    """Check if gh is authenticated. Returns (is_authenticated, error_message)."""
    returncode, _, stderr = run_gh(["auth", "status"])
    if returncode != 0:
        return False, "Not authenticated. Run 'gh auth login' first."
    return True, ""


def output_error(operation: str, error: str, context: str = "") -> int:
    """Output error in TOON format to stderr."""
    print("status: error", file=sys.stderr)
    print(f"operation: {operation}", file=sys.stderr)
    print(f"error: {error}", file=sys.stderr)
    if context:
        print(f"context: {context}", file=sys.stderr)
    return 1


def cmd_pr_create(args: argparse.Namespace) -> int:
    """Handle 'pr create' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error("pr_create", err)

    # Build command
    gh_args = ["pr", "create", "--title", args.title, "--body", args.body]
    if args.base:
        gh_args.extend(["--base", args.base])
    if args.draft:
        gh_args.append("--draft")

    # Execute
    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return output_error("pr_create", "Failed to create PR", stderr.strip())

    # Parse the URL from output (gh pr create outputs the URL)
    pr_url = stdout.strip()

    # Get PR number from URL
    pr_number = "unknown"
    if "/pull/" in pr_url:
        try:
            pr_number = pr_url.split("/pull/")[1].split("/")[0].split("?")[0]
        except (IndexError, ValueError):
            pass

    # Output TOON
    print("status: success")
    print("operation: pr_create")
    print(f"pr_number: {pr_number}")
    print(f"pr_url: {pr_url}")
    return 0


def cmd_pr_reviews(args: argparse.Namespace) -> int:
    """Handle 'pr reviews' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error("pr_reviews", err)

    # Get reviews
    returncode, stdout, stderr = run_gh([
        "pr", "view", str(args.pr_number),
        "--json", "reviews"
    ])
    if returncode != 0:
        return output_error("pr_reviews", f"Failed to get reviews for PR {args.pr_number}", stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
        reviews = data.get("reviews", [])
    except json.JSONDecodeError:
        return output_error("pr_reviews", "Failed to parse gh output", stdout[:100])

    # Output TOON
    print("status: success")
    print("operation: pr_reviews")
    print(f"pr_number: {args.pr_number}")
    print(f"review_count: {len(reviews)}")
    print()
    print(f"reviews[{len(reviews)}]{{user,state,submitted_at}}:")
    for review in reviews:
        user = review.get("author", {}).get("login", "unknown")
        state = review.get("state", "UNKNOWN")
        submitted = review.get("submittedAt", "-")
        print(f"{user}\t{state}\t{submitted}")
    return 0


def cmd_ci_status(args: argparse.Namespace) -> int:
    """Handle 'ci status' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error("ci_status", err)

    # Get checks (bucket field contains pass/fail result)
    returncode, stdout, stderr = run_gh([
        "pr", "checks", str(args.pr_number),
        "--json", "name,state,bucket"
    ])
    if returncode != 0:
        return output_error("ci_status", f"Failed to get CI status for PR {args.pr_number}", stderr.strip())

    # Parse JSON
    try:
        checks = json.loads(stdout)
    except json.JSONDecodeError:
        return output_error("ci_status", "Failed to parse gh output", stdout[:100])

    # Determine overall status (bucket: pass, fail, pending, skipped)
    if not checks:
        overall = "none"
    elif all(c.get("bucket") == "pass" for c in checks):
        overall = "success"
    elif any(c.get("bucket") == "fail" for c in checks):
        overall = "failure"
    elif all(c.get("bucket") in ("pass", "skipped") for c in checks):
        overall = "success"
    else:
        overall = "pending"

    # Output TOON
    print("status: success")
    print("operation: ci_status")
    print(f"pr_number: {args.pr_number}")
    print(f"overall_status: {overall}")
    print(f"check_count: {len(checks)}")
    print()
    print(f"checks[{len(checks)}]{{name,state,result}}:")
    for check in checks:
        name = check.get("name", "unknown")
        state = check.get("state", "unknown")
        bucket = check.get("bucket") or "-"
        print(f"{name}\t{state}\t{bucket}")
    return 0


def cmd_ci_wait(args: argparse.Namespace) -> int:
    """Handle 'ci wait' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error("ci_wait", err)

    start_time = time.time()
    polls = 0
    timeout = args.timeout
    interval = args.interval

    while True:
        polls += 1
        elapsed = time.time() - start_time

        # Check timeout
        if elapsed >= timeout:
            print("status: error", file=sys.stderr)
            print("operation: ci_wait", file=sys.stderr)
            print("error: Timeout waiting for CI", file=sys.stderr)
            print(f"pr_number: {args.pr_number}", file=sys.stderr)
            print(f"duration_sec: {int(elapsed)}", file=sys.stderr)
            print("last_status: pending", file=sys.stderr)
            return 1

        # Get checks (bucket field contains pass/fail result)
        returncode, stdout, stderr = run_gh([
            "pr", "checks", str(args.pr_number),
            "--json", "name,state,bucket"
        ])
        if returncode != 0:
            return output_error("ci_wait", f"Failed to get CI status for PR {args.pr_number}", stderr.strip())

        # Parse and check status
        try:
            checks = json.loads(stdout)
        except json.JSONDecodeError:
            return output_error("ci_wait", "Failed to parse gh output", stdout[:100])

        # Check if all completed (bucket != pending means completed)
        if checks and all(c.get("bucket") != "pending" for c in checks):
            # Determine final status (bucket: pass, fail, skipped)
            if all(c.get("bucket") in ("pass", "skipped") for c in checks):
                final_status = "success"
            elif any(c.get("bucket") == "fail" for c in checks):
                final_status = "failure"
            else:
                final_status = "mixed"

            # Output TOON
            print("status: success")
            print("operation: ci_wait")
            print(f"pr_number: {args.pr_number}")
            print(f"final_status: {final_status}")
            print(f"duration_sec: {int(elapsed)}")
            print(f"polls: {polls}")
            return 0

        # Wait before next poll
        time.sleep(interval)


def cmd_issue_create(args: argparse.Namespace) -> int:
    """Handle 'issue create' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error("issue_create", err)

    # Build command
    gh_args = ["issue", "create", "--title", args.title, "--body", args.body]
    if args.labels:
        gh_args.extend(["--label", args.labels])

    # Execute
    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return output_error("issue_create", "Failed to create issue", stderr.strip())

    # Parse the URL from output
    issue_url = stdout.strip()

    # Get issue number from URL
    issue_number = "unknown"
    if "/issues/" in issue_url:
        try:
            issue_number = issue_url.split("/issues/")[1].split("/")[0].split("?")[0]
        except (IndexError, ValueError):
            pass

    # Output TOON
    print("status: success")
    print("operation: issue_create")
    print(f"issue_number: {issue_number}")
    print(f"issue_url: {issue_url}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GitHub operations via gh CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # pr subcommand
    pr_parser = subparsers.add_parser("pr", help="Pull request operations")
    pr_subparsers = pr_parser.add_subparsers(dest="pr_command", required=True)

    # pr create
    pr_create_parser = pr_subparsers.add_parser("create", help="Create a pull request")
    pr_create_parser.add_argument("--title", required=True, help="PR title")
    pr_create_parser.add_argument("--body", required=True, help="PR description")
    pr_create_parser.add_argument("--base", help="Base branch (default: repo default)")
    pr_create_parser.add_argument("--draft", action="store_true", help="Create as draft PR")

    # pr reviews
    pr_reviews_parser = pr_subparsers.add_parser("reviews", help="Get PR reviews")
    pr_reviews_parser.add_argument("--pr-number", required=True, type=int, help="PR number")

    # ci subcommand
    ci_parser = subparsers.add_parser("ci", help="CI operations")
    ci_subparsers = ci_parser.add_subparsers(dest="ci_command", required=True)

    # ci status
    ci_status_parser = ci_subparsers.add_parser("status", help="Check CI status")
    ci_status_parser.add_argument("--pr-number", required=True, type=int, help="PR number")

    # ci wait
    ci_wait_parser = ci_subparsers.add_parser("wait", help="Wait for CI to complete")
    ci_wait_parser.add_argument("--pr-number", required=True, type=int, help="PR number")
    ci_wait_parser.add_argument("--timeout", type=int, default=300, help="Max wait time in seconds (default: 300)")
    ci_wait_parser.add_argument("--interval", type=int, default=30, help="Poll interval in seconds (default: 30)")

    # issue subcommand
    issue_parser = subparsers.add_parser("issue", help="Issue operations")
    issue_subparsers = issue_parser.add_subparsers(dest="issue_command", required=True)

    # issue create
    issue_create_parser = issue_subparsers.add_parser("create", help="Create an issue")
    issue_create_parser.add_argument("--title", required=True, help="Issue title")
    issue_create_parser.add_argument("--body", required=True, help="Issue description")
    issue_create_parser.add_argument("--labels", help="Comma-separated labels")

    args = parser.parse_args()

    if args.command == "pr":
        if args.pr_command == "create":
            return cmd_pr_create(args)
        elif args.pr_command == "reviews":
            return cmd_pr_reviews(args)
    elif args.command == "ci":
        if args.ci_command == "status":
            return cmd_ci_status(args)
        elif args.ci_command == "wait":
            return cmd_ci_wait(args)
    elif args.command == "issue":
        if args.issue_command == "create":
            return cmd_issue_create(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
