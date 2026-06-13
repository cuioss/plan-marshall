#!/usr/bin/env python3
"""
Platform router for plan-marshall — dispatches 15 operations to the correct
target implementation based on ``runtime.target`` in ``.plan/marshal.json``.

Usage:
    python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \\
        <operation> [operation-specific args...]

Operations:
    project initial-setup   --project-dir <path>  --target claude|opencode
    project install-hook    --target <settings-file-path>
    session capture         --plan-id <id>
    session render-title    (no arguments)
    session push-title-token --plan-id <id>  --icon <glyph>
    permission configure    --scope project|global  --permissions <p1> [<p2> ...]
    permission analyze      --scope global|project|both  --checks <c1>[,<c2>]  [--marshal <path>]
    permission fix          --scope project|global  --operation <op>  [--permissions <p> ...] [--dry-run]
    permission ensure-wildcards  --scope project|global  [--marketplace-dir <path>] [--dry-run]
    permission ensure-steps --marshal <path>  --scope project|global  [--dry-run]
    permission web-analyze  --scope global|project|both
    permission web-apply    --scope project|global  [--add <json>]  [--remove <json>]  [--dry-run]
    metrics capture         --plan-id <id>  --phase <phase>  [--total-tokens <n>]
    subagent dispatch       --agent <name>  [--prompt-file <path>]  [--context <json>]
    health-check            --checks all|permissions|display|mcp-diagnostics

The router resolves ``PLAN_DIR_NAME`` (default ``.plan``) from the environment,
reads ``marshal.json``, looks up ``runtime.target``, and dispatches to the
appropriate ``Runtime`` subclass (``ClaudeRuntime`` or ``OpenCodeRuntime``).

Exit codes:
    0 — TOON printed on stdout (success, error, or no-op)
    1 — argument or routing error (printed to stderr)
    2 — runtime I/O error (printed to stderr)

TOON contract: see standards/contract.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: resolve sibling script directories onto sys.path.
# The executor sets PYTHONPATH before invocation, but the bootstrap guard
# ensures the router works when invoked directly (e.g., during bootstrap
# before the executor exists).
#
# The bootstrap is target-aware: it adds common libs (ref-toon-format,
# platform-runtime) unconditionally, then adds target-specific libs based
# on the detected platform.  Call _bootstrap_glob_discover() with the
# resolved target string to activate the full set.
# ---------------------------------------------------------------------------

# Libraries required by every target.
_COMMON_BOOTSTRAP_LIBS: tuple[str, ...] = (
    "ref-toon-format",
    "platform-runtime",
)

# Additional libraries required per target, discovered via glob within the
# skills root.  Keys match the ``runtime.target`` values in marshal.json.
_TARGET_BOOTSTRAP_LIBS: dict[str, tuple[str, ...]] = {
    "claude": (
        "tools-file-ops",
        "tools-permission-doctor",
        "tools-permission-fix",
        "workflow-permission-web",
        "script-shared",
    ),
    "opencode": (),
}


def _find_skills_root() -> Path | None:
    """Walk ancestors of this file to locate the marketplace ``skills/`` root.

    The root is the first ancestor directory named ``skills`` whose parent
    contains a ``.claude-plugin/plugin.json`` bundle manifest.

    Returns:
        The ``skills/`` ``Path`` when found, or ``None`` if not found.
    """
    for ancestor in Path(__file__).resolve().parents:
        if ancestor.name == "skills" and (
            ancestor.parent / ".claude-plugin" / "plugin.json"
        ).is_file():
            return ancestor
    return None


def _bootstrap_glob_discover(target: str | None = None) -> Path | None:
    """Add skill script directories to ``sys.path``, routing by target.

    Discovers the marketplace ``skills/`` root via ``_find_skills_root()``,
    then appends:

    1. Every directory in ``_COMMON_BOOTSTRAP_LIBS`` (always).
    2. Every directory in ``_TARGET_BOOTSTRAP_LIBS[target]`` when *target*
       is a known key (silently skipped for unknown or ``None`` targets).

    Each directory is appended only when it exists on disk and is not already
    present in ``sys.path``, so repeated calls are idempotent.

    Args:
        target: Platform target string (e.g. ``"claude"`` or ``"opencode"``).
                Pass ``None`` to add only the common libs.

    Returns:
        The resolved ``skills/`` root ``Path`` when the root was found, or
        ``None`` when the ancestor walk found no marketplace root.
    """
    skills_root = _find_skills_root()
    if skills_root is None:
        return None

    libs = list(_COMMON_BOOTSTRAP_LIBS)
    if target in _TARGET_BOOTSTRAP_LIBS:
        libs.extend(_TARGET_BOOTSTRAP_LIBS[target])

    for lib_name in libs:
        lib_dir = skills_root / lib_name / "scripts"
        if not lib_dir.is_dir():
            continue
        lib_path = str(lib_dir)
        if lib_path not in sys.path:
            sys.path.append(lib_path)

    return skills_root


# Run the common bootstrap immediately (before imports that depend on it).
# The target-specific libs are added in main() once the target is resolved
# from marshal.json.  This two-phase approach ensures the router's own
# imports (claude_runtime, opencode_runtime, runtime_base) work correctly
# while keeping target-specific paths out of the global sys.path when only
# the common libs are needed.
_bootstrap_glob_discover()

# ---------------------------------------------------------------------------
# Imports — deferred until after sys.path bootstrap above.
# ---------------------------------------------------------------------------
from claude_runtime import ClaudeRuntime  # type: ignore[import-not-found]  # noqa: E402
from opencode_runtime import OpenCodeRuntime  # type: ignore[import-not-found]  # noqa: E402
from runtime_base import Runtime, toon_error  # type: ignore[import-not-found]  # noqa: E402

# ---------------------------------------------------------------------------
# Target registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, type[Runtime]] = {
    "claude": ClaudeRuntime,
    "opencode": OpenCodeRuntime,
}

_PLAN_DIR_NAME = os.environ.get("PLAN_DIR_NAME", ".plan")


# ---------------------------------------------------------------------------
# Marshal.json loader
# ---------------------------------------------------------------------------


def _read_marshal(project_dir: str | None = None) -> dict[str, Any] | None:
    """Read .plan/marshal.json from project_dir (or cwd walk fallback)."""
    if project_dir:
        candidate = Path(project_dir) / _PLAN_DIR_NAME / "marshal.json"
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else None
            except (OSError, json.JSONDecodeError):
                return None
        return None

    # Walk up from cwd to find the nearest marshal.json.
    for parent in [Path.cwd(), *Path.cwd().parents]:
        candidate = parent / _PLAN_DIR_NAME / "marshal.json"
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else None
            except (OSError, json.JSONDecodeError):
                return None
    return None


def _resolve_target(marshal: dict[str, Any]) -> str | None:
    """Extract runtime.target from marshal data."""
    runtime = marshal.get("runtime")
    if not isinstance(runtime, dict):
        return None
    target = runtime.get("target")
    return str(target) if target else None


def _make_runtime(target: str) -> Runtime | None:
    """Instantiate the Runtime subclass for target, or None if unknown."""
    cls = _REGISTRY.get(target)
    if cls is None:
        return None
    return cls()


# ---------------------------------------------------------------------------
# Operation parsers
# ---------------------------------------------------------------------------


def _parse_json_list(raw: str) -> list[str]:
    """Parse a JSON array string to a list of strings, or raise ValueError."""
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError(f"expected JSON array, got {type(parsed).__name__}")
    return [str(item) for item in parsed]


def _parse_context(raw: str) -> dict[str, Any] | None:
    """Parse a JSON object string to a dict, or raise ValueError."""
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"expected JSON object, got {type(parsed).__name__}")
    return parsed


def _dispatch(runtime: Runtime, operation: str, remaining: list[str]) -> str:
    """Parse remaining args for the given operation and call runtime method."""

    # ------------------------------------------------------------------
    # project initial-setup
    # ------------------------------------------------------------------
    if operation == "project initial-setup":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime project initial-setup")
        p.add_argument("--project-dir", default=".")
        p.add_argument("--target", default="claude", choices=list(_REGISTRY))
        ns = p.parse_args(remaining)
        return runtime.project_initial_setup(ns.project_dir, ns.target)

    # ------------------------------------------------------------------
    # project install-hook
    # ------------------------------------------------------------------
    if operation == "project install-hook":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime project install-hook")
        p.add_argument("--target", required=True)
        p.add_argument("--overwrite-statusline", action="store_true",
                       help="Overwrite an existing statusLine whose command differs from the renderer")
        p.add_argument("--overwrite-env-disable", action="store_true",
                       help="Overwrite an existing env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE that is not '1'")
        ns = p.parse_args(remaining)
        return runtime.project_install_hook(
            ns.target,
            overwrite_statusline=ns.overwrite_statusline,
            overwrite_env_disable=ns.overwrite_env_disable,
        )

    # ------------------------------------------------------------------
    # session capture
    # ------------------------------------------------------------------
    if operation == "session capture":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime session capture")
        p.add_argument("--plan-id", required=True)
        ns = p.parse_args(remaining)
        return runtime.session_capture(ns.plan_id)

    # ------------------------------------------------------------------
    # session render-title
    # ------------------------------------------------------------------
    if operation == "session render-title":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime session render-title")
        p.add_argument("--statusline", action="store_true",
                       help="Emit plain text (statusLine mode) instead of the JSON envelope")
        ns = p.parse_args(remaining)
        return runtime.session_render_title(statusline=ns.statusline)

    # ------------------------------------------------------------------
    # session push-title-token
    # ------------------------------------------------------------------
    if operation == "session push-title-token":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime session push-title-token")
        p.add_argument("--plan-id", required=True)
        p.add_argument("--icon", required=True)
        ns = p.parse_args(remaining)
        return runtime.session_push_title_token(ns.plan_id, ns.icon)

    # ------------------------------------------------------------------
    # permission configure
    # ------------------------------------------------------------------
    if operation == "permission configure":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime permission configure")
        p.add_argument("--scope", required=True, choices=["project", "global"])
        p.add_argument("--permissions", nargs="+", required=True)
        ns = p.parse_args(remaining)
        return runtime.permission_configure(ns.scope, ns.permissions)

    # ------------------------------------------------------------------
    # permission analyze
    # ------------------------------------------------------------------
    if operation == "permission analyze":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime permission analyze")
        p.add_argument("--scope", required=True)
        p.add_argument("--checks", required=True,
                       help="Comma-separated: redundant,suspicious,missing-steps,all")
        p.add_argument("--marshal", default=None)
        ns = p.parse_args(remaining)
        checks = [c.strip() for c in ns.checks.split(",") if c.strip()]
        return runtime.permission_analyze(ns.scope, checks, ns.marshal)

    # ------------------------------------------------------------------
    # permission fix
    # ------------------------------------------------------------------
    if operation == "permission fix":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime permission fix")
        p.add_argument("--scope", required=True)
        p.add_argument("--operation", required=True,
                       choices=["normalize", "add", "remove", "ensure", "consolidate"])
        p.add_argument("--permissions", nargs="*", default=[])
        p.add_argument("--dry-run", action="store_true")
        ns = p.parse_args(remaining)
        return runtime.permission_fix(ns.scope, ns.operation, ns.permissions, ns.dry_run)

    # ------------------------------------------------------------------
    # permission ensure-wildcards
    # ------------------------------------------------------------------
    if operation == "permission ensure-wildcards":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime permission ensure-wildcards")
        p.add_argument("--scope", required=True)
        p.add_argument("--marketplace-dir", default="marketplace/")
        p.add_argument("--dry-run", action="store_true")
        ns = p.parse_args(remaining)
        return runtime.permission_ensure_wildcards(ns.scope, ns.marketplace_dir, ns.dry_run)

    # ------------------------------------------------------------------
    # permission ensure-steps
    # ------------------------------------------------------------------
    if operation == "permission ensure-steps":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime permission ensure-steps")
        p.add_argument("--marshal", required=True)
        p.add_argument("--scope", required=True)
        p.add_argument("--dry-run", action="store_true")
        ns = p.parse_args(remaining)
        return runtime.permission_ensure_steps(ns.marshal, ns.scope, ns.dry_run)

    # ------------------------------------------------------------------
    # permission web-analyze
    # ------------------------------------------------------------------
    if operation == "permission web-analyze":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime permission web-analyze")
        p.add_argument("--scope", required=True)
        ns = p.parse_args(remaining)
        return runtime.permission_web_analyze(ns.scope)

    # ------------------------------------------------------------------
    # permission web-apply
    # ------------------------------------------------------------------
    if operation == "permission web-apply":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime permission web-apply")
        p.add_argument("--scope", required=True)
        p.add_argument("--add", default="[]")
        p.add_argument("--remove", default="[]")
        p.add_argument("--dry-run", action="store_true")
        ns = p.parse_args(remaining)
        try:
            add_list = _parse_json_list(ns.add)
            remove_list = _parse_json_list(ns.remove)
        except (json.JSONDecodeError, ValueError) as exc:
            return toon_error(
                "permission web-apply",
                "invalid_argument",
                f"--add / --remove must be JSON arrays: {exc}",
            )
        return runtime.permission_web_apply(ns.scope, add_list, remove_list, ns.dry_run)

    # ------------------------------------------------------------------
    # metrics capture
    # ------------------------------------------------------------------
    if operation == "metrics capture":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime metrics capture")
        p.add_argument("--plan-id", required=True)
        p.add_argument("--phase", required=True)
        p.add_argument("--total-tokens", type=int, default=None)
        ns = p.parse_args(remaining)
        return runtime.metrics_capture(ns.plan_id, ns.phase, ns.total_tokens)

    # ------------------------------------------------------------------
    # subagent dispatch
    # ------------------------------------------------------------------
    if operation == "subagent dispatch":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime subagent dispatch")
        p.add_argument("--agent", required=True)
        p.add_argument("--prompt-file", default=None)
        p.add_argument("--context", default=None)
        ns = p.parse_args(remaining)
        context: dict[str, Any] | None = None
        if ns.context:
            try:
                context = _parse_context(ns.context)
            except (json.JSONDecodeError, ValueError) as exc:
                return toon_error(
                    "subagent dispatch",
                    "invalid_argument",
                    f"--context must be a JSON object: {exc}",
                )
        return runtime.subagent_dispatch(ns.agent, ns.prompt_file, context)

    # ------------------------------------------------------------------
    # health-check
    # ------------------------------------------------------------------
    if operation == "health-check":
        p = argparse.ArgumentParser(allow_abbrev=False, prog="platform_runtime health-check")
        p.add_argument("--checks", required=True,
                       help="Comma-separated: all,permissions,display,mcp-diagnostics")
        ns = p.parse_args(remaining)
        return runtime.health_check(ns.checks)

    # Unrecognized operation.
    return toon_error(
        operation,
        "unknown_operation",
        f"Unknown operation {operation!r}; "
        "valid operations: project initial-setup, project install-hook, "
        "session capture, session render-title, session push-title-token, "
        "permission configure, permission analyze, permission fix, "
        "permission ensure-wildcards, permission ensure-steps, "
        "permission web-analyze, permission web-apply, "
        "metrics capture, subagent dispatch, health-check",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def _build_operation(argv: list[str]) -> tuple[str, list[str]]:
    """Determine the two-word operation from argv and return (operation, remaining).

    Operations are two-word identifiers (e.g. ``project initial-setup``).
    Some are single-hyphenated second words (``health-check``).

    Supported prefix tokens: project, session, permission, metrics, subagent, health-check.
    """
    if not argv:
        return ("", [])

    # health-check is a special case — single token.
    if argv[0] == "health-check":
        return ("health-check", argv[1:])

    # All other operations have the form: <group> <subcommand>
    if len(argv) >= 2:
        group = argv[0]
        subcommand = argv[1]
        operation = f"{group} {subcommand}"
        return (operation, argv[2:])

    return (argv[0], [])


def main(argv: list[str] | None = None) -> int:
    """Router entry point. Returns exit code."""
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print(
            "usage: platform_runtime.py <operation> [args...]\n"
            "See standards/contract.md for supported operations.",
            file=sys.stderr,
        )
        return 1

    operation, remaining = _build_operation(argv)

    # ------------------------------------------------------------------
    # Determine project_dir for marshal.json lookup.
    # ``project initial-setup`` is the only operation that explicitly
    # supplies --project-dir before the executor exists; extract it here
    # so the marshal lookup works correctly for that path.
    # All other operations use cwd-walk.
    # ------------------------------------------------------------------
    project_dir: str | None = None
    if operation == "project initial-setup":
        # Peek at --project-dir without consuming remaining.
        peek = argparse.ArgumentParser(allow_abbrev=False, add_help=False)
        peek.add_argument("--project-dir", default=None)
        peek.add_argument("--target", default="claude")
        ns_peek, _ = peek.parse_known_args(remaining)
        if ns_peek.project_dir:
            project_dir = ns_peek.project_dir

    # ------------------------------------------------------------------
    # Load marshal.json and resolve target.
    # ``project initial-setup`` may run before marshal.json exists, so we
    # attempt the read but fall back to the --target argument when the
    # file is absent.
    # ------------------------------------------------------------------
    marshal = _read_marshal(project_dir)

    if marshal is not None:
        target = _resolve_target(marshal)
        if not target:
            # marshal.json found but runtime.target missing — default to claude.
            target = "claude"
    else:
        # marshal.json absent — only valid for ``project initial-setup``.
        if operation == "project initial-setup":
            # Extract --target from remaining to bootstrap the correct runtime.
            peek2 = argparse.ArgumentParser(allow_abbrev=False, add_help=False)
            peek2.add_argument("--target", default="claude")
            ns_peek2, _ = peek2.parse_known_args(remaining)
            target = ns_peek2.target
        else:
            print(
                toon_error(
                    operation,
                    "marshal_not_found",
                    ".plan/marshal.json not found; run 'project initial-setup' first",
                )
            )
            return 0

    # Activate target-specific bootstrap libs now that the target is known.
    # This extends sys.path with platform-specific skill libraries (e.g.
    # tools-permission-doctor for claude) so runtime subclasses can import
    # them without maintaining their own duplicate bootstrap blocks.
    _bootstrap_glob_discover(target)

    # Validate target against registry.
    runtime = _make_runtime(target)
    if runtime is None:
        print(
            toon_error(
                operation,
                "unknown_target",
                f"runtime.target {target!r} is not in the registry; "
                f"valid targets are: {', '.join(sorted(_REGISTRY))}",
            )
        )
        return 0

    # ------------------------------------------------------------------
    # Dispatch to the runtime implementation.
    # ------------------------------------------------------------------
    result = _dispatch(runtime, operation, remaining)
    # An empty-string return is the statusLine-mode sentinel: the runtime
    # already wrote the verbatim statusLine content to stdout (or wrote
    # nothing on the noop branches), and the caller MUST NOT append a
    # trailing newline that would render as an empty row under the prompt.
    # Every TOON return path produces a non-empty string, so the truthiness
    # check is sufficient.
    if result:
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
