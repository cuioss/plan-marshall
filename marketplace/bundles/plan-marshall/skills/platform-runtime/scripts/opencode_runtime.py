#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
OpenCode implementation of all 21 platform-runtime operations.

OpenCode-specific behaviour:
- Operations requiring a platform session id (session capture, session
  render-title) return ``no-op`` because OpenCode does not expose a session id
  to the shell environment (upstream issue #9292).
- project initial-setup succeeds but reports ``hook_installed: false`` for the
  same reason.
- All permission and web operations return an honest ``no-op`` with a reason
  and alternative: OpenCode has no validated permission backend, and the Claude
  permission grammar (``Skill()``/``Bash()``/``WebFetch()`` patterns) does not
  map onto OpenCode's settings format. These ops never fabricate a success that
  claims a write happened.
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
        enforcement: bool = False,
    ) -> str:
        """No-op: OpenCode has no Claude-style SessionStart settings hook."""
        return toon_noop(
            "project install-hook",
            "OpenCode has no Claude-style SessionStart settings hook to install"
            " (issue anomalyco/opencode#8619)",
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    # ------------------------------------------------------------------
    # Filesystem layout resolution
    # ------------------------------------------------------------------

    def layout_skill_roots(self) -> str:
        """Return the OpenCode project-local-skill roots (executor's root order).

        Mirrors ``generate_executor.py``'s OpenCode discovery-root list: the
        ``$OPENCODE_CONFIG_DIR`` override (when set), the project-local roots,
        and the ``~``-anchored user-global roots. The list is returned in
        priority order; callers probe first-match-wins.
        """
        import os
        import pathlib

        home = pathlib.Path.home()
        roots: list[str] = []

        env_config_dir = os.environ.get("OPENCODE_CONFIG_DIR", "")
        if env_config_dir:
            roots.append(str(pathlib.Path(env_config_dir) / "skills"))

        roots.extend(
            [
                ".opencode/skills",
                ".claude/skills",
                ".agents/skills",
                str(home / ".config" / "opencode" / "skills"),
                str(home / ".claude" / "skills"),
                str(home / ".agents" / "skills"),
            ]
        )

        return toon_success(
            "layout skill-roots",
            {"target": "opencode", "roots": roots},
        )

    def layout_bundle_cache_root(self) -> str:
        """Return the OpenCode deployed-bundle cache root(s).

        OpenCode has no separate single plugin-cache directory; deployed
        bundles live under the project-local-skill discovery roots themselves.
        Return the ``~``-anchored user-global skill roots (the cross-checkout
        discovery homes) in priority order, mirroring the executor's discovery
        order. Callers probe first-match-wins.
        """
        import os
        import pathlib

        home = pathlib.Path.home()
        roots: list[str] = []

        env_config_dir = os.environ.get("OPENCODE_CONFIG_DIR", "")
        if env_config_dir:
            roots.append(str(pathlib.Path(env_config_dir) / "skills"))

        roots.extend(
            [
                str(home / ".config" / "opencode" / "skills"),
                str(home / ".claude" / "skills"),
                str(home / ".agents" / "skills"),
            ]
        )

        return toon_success(
            "layout bundle-cache-root",
            {"target": "opencode", "roots": roots},
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

    def session_push_title_token(self, plan_id: str, icon: str | None = None) -> str:
        """No-op: OpenCode has no plugin-driven terminal-title push channel."""
        return toon_noop(
            "session push-title-token",
            "OpenCode has no plugin-driven terminal-title push channel"
            " (issue anomalyco/opencode#8619)",
            "Use OpenCode's built-in TUI status surface for plan visibility",
        )

    def session_bind(self, plan_id: str, session_id: str | None = None) -> str:
        """No-op: OpenCode does not expose a platform session id to bind."""
        return toon_noop(
            "session bind",
            "OpenCode does not expose a platform-provided session id to the shell,"
            " so there is no per-session slot to bind (issue #9292)",
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    def session_resolve_plan(self, session_id: str | None = None) -> str:
        """No-op: OpenCode does not expose a platform session id to resolve."""
        return toon_noop(
            "session resolve-plan",
            "OpenCode does not expose a platform-provided session id to the shell,"
            " so there is no per-session binding to resolve (issue #9292)",
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    def session_doctor(self, fix: bool = False) -> str:
        """No-op: OpenCode keeps no per-session active-plan cache to scan."""
        return toon_noop(
            "session doctor",
            "OpenCode does not expose a platform-provided session id, so there is"
            " no per-session active-plan cache to scan (issue #9292)",
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    # ------------------------------------------------------------------
    # Permission operations
    # ------------------------------------------------------------------

    # OpenCode has no validated permission backend. Each permission op returns
    # an honest ``no-op`` (reason + alternative) rather than a fabricated success
    # that claims a write happened. The Claude permission grammar
    # (``Skill()``/``Bash()``/``WebFetch()`` patterns, the
    # ``permissions.{allow,deny,ask}`` schema) is Claude-specific and does not
    # map onto OpenCode's settings format; surfacing a fake ``permissions_written``
    # count would mislead callers into believing the operation took effect.
    _PERMISSION_NOOP_REASON = (
        "OpenCode has no validated permission backend; the Claude permission "
        "grammar does not map onto OpenCode's settings format"
    )
    _PERMISSION_NOOP_ALTERNATIVE = (
        "Manage OpenCode permissions through OpenCode's own settings; this op is "
        "Claude-only"
    )

    def permission_configure(self, scope: str, permissions: list[str]) -> str:
        """Honest no-op: OpenCode has no validated permission-write backend."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission configure",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        return toon_noop(
            "permission configure",
            self._PERMISSION_NOOP_REASON,
            self._PERMISSION_NOOP_ALTERNATIVE,
        )

    def permission_analyze(
        self, scope: str, checks: list[str], marshal_path: str | None
    ) -> str:
        """Honest no-op: OpenCode has no Claude-grammar permission audit."""
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
        return toon_noop(
            "permission analyze",
            self._PERMISSION_NOOP_REASON,
            self._PERMISSION_NOOP_ALTERNATIVE,
        )

    def permission_fix(
        self,
        scope: str,
        operation: str,
        permissions: list[str],
        dry_run: bool,
    ) -> str:
        """Honest no-op: OpenCode has no validated permission-fix backend."""
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
        return toon_noop(
            "permission fix",
            self._PERMISSION_NOOP_REASON,
            self._PERMISSION_NOOP_ALTERNATIVE,
        )

    def permission_ensure_wildcards(
        self, scope: str, marketplace_dir: str, dry_run: bool
    ) -> str:
        """Honest no-op: OpenCode has no marketplace-wildcard permission backend."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission ensure-wildcards",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        return toon_noop(
            "permission ensure-wildcards",
            self._PERMISSION_NOOP_REASON,
            self._PERMISSION_NOOP_ALTERNATIVE,
        )

    def permission_ensure_steps(
        self, marshal_path: str, scope: str, dry_run: bool
    ) -> str:
        """Honest no-op: OpenCode has no per-step permission backend."""
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
        return toon_noop(
            "permission ensure-steps",
            self._PERMISSION_NOOP_REASON,
            self._PERMISSION_NOOP_ALTERNATIVE,
        )

    def permission_web_analyze(self, scope: str) -> str:
        """Honest no-op: OpenCode has no WebFetch-grammar permission audit."""
        valid_scopes = ("global", "project", "both")
        if scope not in valid_scopes:
            return toon_error(
                "permission web-analyze",
                "invalid_scope",
                f"--scope must be 'global', 'project', or 'both'; got {scope!r}",
            )
        return toon_noop(
            "permission web-analyze",
            self._PERMISSION_NOOP_REASON,
            self._PERMISSION_NOOP_ALTERNATIVE,
        )

    def permission_web_apply(
        self,
        scope: str,
        add: list[str],
        remove: list[str],
        dry_run: bool,
    ) -> str:
        """Honest no-op: OpenCode has no WebFetch-domain permission backend."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission web-apply",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        return toon_noop(
            "permission web-apply",
            self._PERMISSION_NOOP_REASON,
            self._PERMISSION_NOOP_ALTERNATIVE,
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

    def metrics_normalized_tokens(
        self,
        session_id: str,
        windows: list[tuple[str, str, str]],
        output_file: str,
    ) -> str:
        """Honest no-op: OpenCode exposes no session transcript to normalize.

        OpenCode does not provide a session transcript, so there is nothing to
        walk or normalize. Returns ``transcript_not_found`` so the
        finalize/retrospective enrich steps degrade gracefully (skip enrichment).
        """
        return toon_noop(
            "metrics normalized-tokens",
            "transcript_not_found",
            "pass --total-tokens manually to metrics capture",
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
                    "subagent_type": "execution-context-level-3",
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
