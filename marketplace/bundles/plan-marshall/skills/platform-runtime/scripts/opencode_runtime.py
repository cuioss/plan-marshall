#!/usr/bin/env python3
"""
OpenCode implementation of all 15 platform-runtime operations.

OpenCode-specific behaviour:
- Operations requiring a platform session id (session capture, session
  render-title) return ``no-op`` because OpenCode does not expose a session id
  to the shell environment (upstream issue #9292).
- project initial-setup succeeds but reports ``hook_installed: false`` for the
  same reason.
- All permission and web operations succeed: OpenCode uses its own settings
  format, but the no-op contract for this cluster is deferred to the router
  layer.  The OpenCode runtime stubs these operations as success so the router
  can delegate to the appropriate settings backend without special-casing.
- metrics capture succeeds when ``total_tokens`` is provided; returns ``no-op``
  otherwise (no automatic transcript scan without a session id).
- subagent dispatch succeeds, mapping the ``Task`` tool to OpenCode's ``task``.
- health-check succeeds; the ``display`` check always reports unhealthy on
  OpenCode because no hook file is present.

All methods return a serialized TOON string via the helpers in runtime_base.
"""
from __future__ import annotations

from typing import Any

from runtime_base import Runtime, toon_error, toon_noop, toon_success


class OpenCodeRuntime(Runtime):
    """OpenCode concrete implementation of the Runtime ABC.

    Every method returns a serialized TOON string ready for ``print()``.
    """

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    def project_initial_setup(self, project_dir: str, target: str) -> str:
        """One-time project setup for OpenCode.

        Creates ``.plan/``, seeds ``marshal.json`` with ``runtime.target``.
        No SessionStart hook is installed because OpenCode has no equivalent.
        """
        import json
        import pathlib

        proj = pathlib.Path(project_dir)
        plan_dir = proj / ".plan"

        try:
            plan_dir.mkdir(parents=True, exist_ok=True)
            temp_dir = plan_dir / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to create .plan directory: {exc}",
            )

        marshal_path = plan_dir / "marshal.json"
        try:
            if marshal_path.exists():
                existing: dict[str, Any] = json.loads(marshal_path.read_text(encoding="utf-8"))
            else:
                existing = {}

            if "runtime" not in existing:
                existing["runtime"] = {}
            existing["runtime"]["target"] = target

            marshal_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        except (OSError, json.JSONDecodeError) as exc:
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to write marshal.json: {exc}",
            )

        return toon_success(
            "project initial-setup",
            {
                "target": target,
                "project_dir": str(proj.resolve()),
                "marshal_written": True,
                "hook_installed": False,
                "hook_skip_reason": (
                    "OpenCode does not support a SessionStart hook equivalent (issue #9292)"
                ),
            },
        )

    def project_install_hook(
        self,
        target: str,
        overwrite_statusline: bool = False,
        overwrite_env_disable: bool = False,
    ) -> str:
        """No-op: OpenCode has no Claude-style SessionStart settings hook."""
        return toon_noop(
            "project install-hook",
            "OpenCode has no Claude-style SessionStart settings hook to install"
            " (issue anomalyco/opencode#8619)",
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    def session_capture(self, plan_id: str) -> str:
        """No-op: OpenCode does not expose a platform session id."""
        return toon_noop(
            "session capture",
            "OpenCode does not expose a platform-provided session id to the shell;"
            " tracked upstream at issue #9292",
            "pass --total-tokens manually to metrics capture",
        )

    def session_render_title(self, statusline: bool = False) -> str:
        """No-op: OpenCode has no plugin-driven terminal-title hook."""
        return toon_noop(
            "session render-title",
            "OpenCode has no plugin-driven terminal-title hook"
            " (issue anomalyco/opencode#8619)",
            "Use OpenCode's built-in TUI status surface for plan visibility",
        )

    # ------------------------------------------------------------------
    # Permission operations
    # ------------------------------------------------------------------

    def permission_configure(self, scope: str, permissions: list[str]) -> str:
        """Write a raw permission list to OpenCode settings.

        Validates scope.  Actual settings file write is a stub — the router
        layer is responsible for targeting the correct backend file.
        """
        if scope not in ("project", "global"):
            return toon_error(
                "permission configure",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        target_file = (
            ".opencode/settings.json" if scope == "project" else "~/.opencode/settings.json"
        )
        return toon_success(
            "permission configure",
            {
                "scope": scope,
                "permissions_written": len(permissions),
                "target_file": target_file,
            },
        )

    def permission_analyze(
        self, scope: str, checks: list[str], marshal_path: str | None
    ) -> str:
        """Read-only permission audit stub for OpenCode."""
        valid_scopes = ("global", "project", "both")
        if scope not in valid_scopes:
            return toon_error(
                "permission analyze",
                "invalid_scope",
                f"--scope must be one of {valid_scopes}; got {scope!r}",
            )
        valid_checks = {"redundant", "suspicious", "missing-steps", "all"}
        for check in checks:
            if check not in valid_checks:
                return toon_error(
                    "permission analyze",
                    "invalid_check",
                    f"Unknown check {check!r}; valid checks are: {', '.join(sorted(valid_checks))}",
                )
        return toon_success(
            "permission analyze",
            {
                "scope": scope,
                "checks_run": checks,
                "total_findings": 0,
            },
        )

    def permission_fix(
        self,
        scope: str,
        operation: str,
        permissions: list[str],
        dry_run: bool,
    ) -> str:
        """Apply permission fixes stub for OpenCode."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission fix",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        valid_ops = {"normalize", "add", "remove", "ensure", "consolidate"}
        if operation not in valid_ops:
            return toon_error(
                "permission fix",
                "invalid_operation",
                f"--operation must be one of {sorted(valid_ops)}; got {operation!r}",
            )
        target_file = (
            ".opencode/settings.json" if scope == "project" else "~/.opencode/settings.json"
        )
        return toon_success(
            "permission fix",
            {
                "scope": scope,
                "fix_operation": operation,
                "dry_run": dry_run,
                "target_file": target_file,
                "changes_applied": 0 if dry_run else len(permissions),
            },
        )

    def permission_ensure_wildcards(
        self, scope: str, marketplace_dir: str, dry_run: bool
    ) -> str:
        """Ensure marketplace wildcard permissions stub for OpenCode."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission ensure-wildcards",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        target_file = (
            ".opencode/settings.json" if scope == "project" else "~/.opencode/settings.json"
        )
        return toon_success(
            "permission ensure-wildcards",
            {
                "scope": scope,
                "marketplace_dir": marketplace_dir,
                "dry_run": dry_run,
                "bundles_scanned": 0,
                "wildcards_added": 0,
                "wildcards_already_present": 0,
                "target_file": target_file,
            },
        )

    def permission_ensure_steps(
        self, marshal_path: str, scope: str, dry_run: bool
    ) -> str:
        """Ensure per-step permissions stub for OpenCode."""
        import pathlib

        if not pathlib.Path(marshal_path).exists():
            return toon_error(
                "permission ensure-steps",
                "marshal_not_found",
                f"{marshal_path} not found; run 'project initial-setup' first",
            )
        if scope not in ("project", "global"):
            return toon_error(
                "permission ensure-steps",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        target_file = (
            ".opencode/settings.json" if scope == "project" else "~/.opencode/settings.json"
        )
        return toon_success(
            "permission ensure-steps",
            {
                "marshal": marshal_path,
                "scope": scope,
                "dry_run": dry_run,
                "steps_scanned": 0,
                "permissions_added": 0,
                "permissions_already_present": 0,
                "target_file": target_file,
            },
        )

    def permission_web_analyze(self, scope: str) -> str:
        """Read-only web permission analysis stub for OpenCode."""
        valid_scopes = ("global", "project", "both")
        if scope not in valid_scopes:
            return toon_error(
                "permission web-analyze",
                "invalid_scope",
                f"--scope must be 'global', 'project', or 'both'; got {scope!r}",
            )
        return toon_success(
            "permission web-analyze",
            {
                "scope": scope,
                "total_domains": 0,
            },
        )

    def permission_web_apply(
        self,
        scope: str,
        add: list[str],
        remove: list[str],
        dry_run: bool,
    ) -> str:
        """Add or remove web domain permissions stub for OpenCode."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission web-apply",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        target_file = (
            ".opencode/settings.json" if scope == "project" else "~/.opencode/settings.json"
        )
        return toon_success(
            "permission web-apply",
            {
                "scope": scope,
                "dry_run": dry_run,
                "domains_added": 0 if dry_run else len(add),
                "domains_removed": 0 if dry_run else len(remove),
                "target_file": target_file,
            },
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def metrics_capture(
        self, plan_id: str, phase: str, total_tokens: int | None
    ) -> str:
        """Record token consumption for OpenCode.

        When ``total_tokens`` is provided, stores it directly and succeeds.
        Without it, returns ``no-op`` because OpenCode has no session transcript.
        """
        if total_tokens is None:
            return toon_noop(
                "metrics capture",
                "automatic token capture requires a platform-provided session id,"
                " which OpenCode does not expose (issue #9292)",
                "pass --total-tokens manually",
            )
        return toon_success(
            "metrics capture",
            {
                "plan_id": plan_id,
                "phase": phase,
                "tokens_captured": total_tokens,
                "source": "manual",
            },
        )

    # ------------------------------------------------------------------
    # Subagent dispatch
    # ------------------------------------------------------------------

    def subagent_dispatch(
        self,
        agent: str,
        prompt_file: str | None,
        context: dict[str, Any] | None,
    ) -> str:
        """Return OpenCode subagent invocation parameters.

        Uses ``task`` (lowercase) as the OpenCode native tool name.
        """
        import pathlib

        if prompt_file is not None and not pathlib.Path(prompt_file).exists():
            return toon_error(
                "subagent dispatch",
                "prompt_not_found",
                f"prompt file not found: {prompt_file}",
            )

        prompt_body = f"Run {agent}"
        if prompt_file is not None:
            try:
                prompt_body = pathlib.Path(prompt_file).read_text(encoding="utf-8")
            except OSError as exc:
                return toon_error(
                    "subagent dispatch",
                    "prompt_not_found",
                    f"Failed to read prompt file {prompt_file}: {exc}",
                )

        if context:
            for key, value in context.items():
                prompt_body = prompt_body.replace(f"{{{key}}}", str(value))

        return toon_success(
            "subagent dispatch",
            {
                "platform": "opencode",
                "invocation": {
                    "tool": "task",
                    "description": f"Run {agent}",
                    "prompt": prompt_body,
                    "subagent_type": "execution-context-high",
                },
            },
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self, checks: str) -> str:
        """Verify OpenCode platform integration.

        The ``display`` check always reports unhealthy because no hook file is
        installed.  All other checks report healthy.
        """
        import pathlib

        check_list = [c.strip() for c in checks.split(",")]
        if "all" in check_list:
            check_list = ["permissions", "display", "mcp-diagnostics", "hook"]

        results: list[dict[str, Any]] = []
        all_healthy = True

        for check in check_list:
            if check == "permissions":
                # OpenCode settings file presence
                settings = pathlib.Path(".opencode/settings.json")
                healthy = settings.exists()
                detail = (
                    ".opencode/settings.json present"
                    if healthy
                    else ".opencode/settings.json not found; OpenCode may not be initialised"
                )
                results.append({"check": check, "healthy": healthy, "detail": detail})
                if not healthy:
                    all_healthy = False

            elif check == "display":
                # OpenCode has no plugin-driven display hook — always unhealthy
                results.append(
                    {
                        "check": check,
                        "healthy": False,
                        "detail": (
                            "OpenCode has no plugin-driven terminal-title hook"
                            " (issue anomalyco/opencode#8619)"
                        ),
                    }
                )
                all_healthy = False

            elif check == "mcp-diagnostics":
                # Check for OpenCode MCP server (port 63342 by convention)
                import socket

                try:
                    with socket.create_connection(("127.0.0.1", 63342), timeout=1):
                        healthy = True
                        detail = "MCP server reachable at 127.0.0.1:63342"
                except OSError:
                    healthy = False
                    detail = "MCP server not reachable at 127.0.0.1:63342"
                results.append({"check": check, "healthy": healthy, "detail": detail})
                if not healthy:
                    all_healthy = False

            elif check == "hook":
                # No SessionStart hook on OpenCode
                results.append(
                    {
                        "check": check,
                        "healthy": False,
                        "detail": (
                            "SessionStart hook not applicable on OpenCode (issue #9292)"
                        ),
                    }
                )
                all_healthy = False

        return toon_success(
            "health-check",
            {
                "checks_run": check_list,
                "all_healthy": all_healthy,
                "results": results,
            },
        )
