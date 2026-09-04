#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
OpenCode implementation of all 25 platform-runtime operations.

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
- wait for returns ``no-op``: OpenCode's runtime holds no wait channel, so the
  caller runs the observable's own bounded-wait verb in-turn instead.

All methods return a serialized TOON string via the helpers in runtime_base.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from runtime_base import (
    PERMISSION_FIX_OPERATIONS,
    Runtime,
    marshal_shape_error,
    toon_error,
    toon_noop,
    toon_success,
)


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
        # Three corrupt-input edges, mirroring the sibling ClaudeRuntime: a MISSING
        # file starts from {}; an unreadable or unparseable one is caught by the
        # except clause; and a PARSEABLE file of the wrong SHAPE is refused by the
        # shared marshal_shape_error guard. The parse edge and the shape edge are
        # separate — a successful json.loads proves the bytes were valid JSON, not
        # that they were an object — so `[]` and `{"runtime": null}` used to reach
        # the seeding assignments and raise an uncaught TypeError here too. The
        # mirror holds by construction because both runtimes call the ONE shared
        # guard rather than each carrying its own copy.
        try:
            if marshal_path.exists():
                # Untyped until the shape guard below runs — see marshal_shape_error.
                existing: Any = json.loads(marshal_path.read_text(encoding="utf-8"))
            else:
                existing = {}
        except (OSError, json.JSONDecodeError) as exc:
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to read marshal.json: {exc}",
            )

        shape_error = marshal_shape_error("project initial-setup", marshal_path, existing)
        if shape_error is not None:
            return shape_error

        if "runtime" not in existing:
            existing["runtime"] = {}
        existing["runtime"]["target"] = target

        try:
            marshal_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        except OSError as exc:
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
        overwrite: Sequence[str] = (),
        enforcement: bool = False,
    ) -> str:
        """No-op: OpenCode exposes no session/display integration to wire.

        The decline is honest rather than a stub: OpenCode offers no hook channel
        at all (issue anomalyco/opencode#8619), so there is no configuration to
        write and no conflict an ``overwrite`` key could resolve. Declining every
        invocation — both install modes, any key set — is the whole behaviour.
        """
        return toon_noop(
            "project install-hook",
            "OpenCode exposes no session/display hook channel to wire"
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
        """No-op: OpenCode does not expose a platform session id.

        This is the ABC's "exposes no session identifier at all" case, not its
        "ought to be reachable but is not" case: there is no wiring that could
        supply one (upstream issue #9292), so the decline is ``no-op`` rather
        than ``hook_not_configured``.
        """
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

    def session_push_title_token(
        self,
        plan_id: str,
        icon: str | None = None,
        store: str = "plans",
        slug: str | None = None,
    ) -> str:
        """No-op: OpenCode has neither a session id to bind nor a render channel."""
        return toon_noop(
            "session push-title-token",
            "OpenCode exposes no platform-provided session id to bind"
            " (issue #9292) and has no plugin-driven terminal-title render channel"
            " for a later event to deliver on (issue anomalyco/opencode#8619)",
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

    def session_teardown(self) -> str:
        """No-op: OpenCode exposes no session binding to release."""
        return toon_noop(
            "session teardown",
            "OpenCode does not expose a platform-provided session id to the shell,"
            " so there is no per-session binding to release (issue #9292)",
            "Use OpenCode's built-in session mechanism for plan visibility",
        )

    def session_reload_directive(self) -> str:
        """No-op: OpenCode has no live plugin-reload command equivalent to
        Claude's ``/reload-plugins``; a full session restart is required to pick
        up the regenerated executor / agent set."""
        return toon_noop(
            "session reload-directive",
            "OpenCode exposes no live plugin-reload command equivalent to Claude's"
            " /reload-plugins",
            "Restart the OpenCode session to pick up the regenerated executor /"
            " agent set",
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

    def permission_configure(self, scope: str, grants: list[dict[str, Any]]) -> str:
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
        arguments: list[Any],
        dry_run: bool,
    ) -> str:
        """Honest no-op: OpenCode has no validated permission-fix backend."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission fix",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )
        valid_ops = set(PERMISSION_FIX_OPERATIONS)
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
    # Permission settings I/O — honest no-ops for OpenCode
    # ------------------------------------------------------------------

    def permission_settings_path(
        self, scope: str, write: bool = False, project_dir: str | None = None
    ) -> str:
        """Decline — OpenCode has no permission settings files."""
        raise RuntimeError(
            f"permission_settings_path: {self._PERMISSION_NOOP_REASON}"
        )

    def permission_load_settings(self, path: str) -> dict[str, Any]:
        """Decline — OpenCode has no permission settings files."""
        return {}

    def permission_save_settings(
        self, path: str, settings: dict[str, Any]
    ) -> bool:
        """Decline — OpenCode has no permission settings files."""
        return False

    def permission_ensure_defaults(
        self,
        settings: dict[str, Any],
        settings_path: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Decline — OpenCode has no permission settings files."""
        return {
            "defaults_added": [],
            "defaults_added_count": 0,
            "defaults_removed": [],
            "defaults_removed_count": 0,
            "applied": False,
        }

    def permission_check_skill_coverage(
        self, skill: str, allow_list: list[str]
    ) -> str | None:
        """Decline — OpenCode has no permission settings files."""
        return None

    def permission_load_marshal_config(self, marshal_path: str) -> dict[str, Any]:
        """Load marshal.json — target-neutral, same schema on every target."""
        marshal = Path(marshal_path)
        if not marshal.exists():
            return {"error": f"marshal.json not found: {marshal_path}"}
        try:
            data = json.loads(marshal.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return {"error": f"Invalid JSON in {marshal_path}: {exc}"}
        except OSError as exc:
            return {"error": f"Could not read {marshal_path}: {exc}"}
        if not isinstance(data, dict):
            return {"error": f"Invalid marshal.json (expected object) in {marshal_path}"}
        return data

    def permission_extract_project_steps(
        self, marshal_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Enumerate project:{skill} step references — target-neutral.

        Scans the same phases as the Claude side: ``plan.{phase-5-execute}.steps``
        and ``plan.{phase-6-finalize}.steps``, returning one ``{skill, step,
        phase}`` dict per ``project:``-prefixed entry. Marshal.json is a shared,
        target-neutral file, so the schema is identical across targets.
        """
        if "error" in marshal_config:
            return []
        plan = marshal_config.get("plan", {})
        if not isinstance(plan, dict):
            return []
        steps: list[dict[str, Any]] = []
        for phase in ("phase-5-execute", "phase-6-finalize"):
            phase_config = plan.get(phase, {})
            if not isinstance(phase_config, dict):
                continue
            entries = phase_config.get("steps", [])
            if not isinstance(entries, list):
                continue
            for step in entries:
                if (
                    isinstance(step, str)
                    and step.startswith("project:")
                    and len(step) > len("project:")
                ):
                    steps.append(
                        {
                            "skill": step[len("project:") :],
                            "step": step,
                            "phase": phase,
                        }
                    )
        return steps

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def metrics_capture(
        self, plan_id: str, phase: str, total_tokens: int | None
    ) -> str:
        """Record token consumption for OpenCode.

        This operation is an honest ``no-op`` on OpenCode — on EVERY input,
        manual count included.

        OpenCode exposes no session transcript, so auto-capture has nothing to
        sum. And this target reaches no persistence boundary: the token-cursor
        write and the ``manage-metrics end-phase`` call live in the Claude
        runtime, so even an explicit ``--total-tokens`` cannot be stored here.
        The Runtime contract therefore forbids returning ``success`` for a
        manual count — a success the caller cannot distinguish from a stored one
        turns a declined measurement into a silently lost one. The target
        declines instead, naming the reason and the alternative.

        Do NOT "helpfully" return a success carrying the count: that was the
        fabricate-success defect this no-op exists to close. The recommended
        remediation is to relocate the (target-neutral) metrics persistence
        boundary to a shared home so both runtimes can reach it; until then,
        OpenCode declines rather than lying about a write it cannot perform.
        """
        if total_tokens is None:
            reason = (
                "automatic token capture requires a platform-provided session id,"
                " which OpenCode does not expose (issue #9292)"
            )
            alternative = (
                "run metrics capture on the Claude target, or wire a shared"
                " metrics-persistence boundary OpenCode can reach"
            )
        else:
            reason = (
                "OpenCode reaches no token-persistence boundary, so an explicit"
                " count cannot be stored (issue #9292)"
            )
            alternative = (
                "run metrics capture on the Claude target, or wire a shared"
                " metrics-persistence boundary OpenCode can reach"
            )
        return toon_noop(
            "metrics capture",
            reason,
            alternative,
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

        **Counters are ABSENT here, never zero.** This method constructs no
        per-phase bucket, writes no *output_file*, and returns no counters, which
        is exactly the required shape: OpenCode declines the primitive rather than
        reporting a measurement it never took. Do NOT "helpfully" add a
        zero-initialized bucket carrying the exploration-share counters — a zero
        asserts "measured, and it was none", which would make an unmeasured target
        indistinguishable from a target that genuinely explored nothing and would
        silently pollute the corpus the ``exploration-share`` audit check reads.
        This is the declinable-primitive posture of ADR-011 and the
        explicit-unknown rule of ADR-009.
        """
        return toon_noop(
            "metrics normalized-tokens",
            "transcript_not_found",
            "pass --total-tokens manually to metrics capture",
        )

    def chat_extract_signal(self, session_id: str) -> str:
        """Honest no-op: OpenCode exposes no session transcript to reduce.

        OpenCode does not provide a session transcript, so there is nothing to
        locate or reduce. Returns ``transcript_not_found`` so the
        chat-history aspect degrades gracefully (skip enrichment).

        **Signal fields are ABSENT here, never zero.** This method performs no
        reduction and returns no ``operator_turn_count`` / ``gate_decision_count``
        / ``no_signal`` fields, which is exactly the required shape: OpenCode
        declines the primitive rather than reporting a measurement it never
        took. Do NOT "helpfully" add a zero-initialized ``no_signal: true`` and
        empty ``reduced_transcript`` — a zero asserts "measured, and there was
        none", which would make an unmeasured target indistinguishable from a
        target whose transcript genuinely carried no operator signal and would
        silently pollute the corpus that reads those fields. This is the
        declinable-primitive posture of ADR-011 and the explicit-unknown rule
        of ADR-009.
        """
        return toon_noop(
            "chat extract-signal",
            "transcript_not_found",
            "run on a target that exposes a session transcript, or "
            "record the session with session capture first",
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

        Uses ``task`` (lowercase) as the OpenCode native tool name, and echoes
        the REQUESTED *agent* back as ``subagent_type`` so the caller's
        selection reaches the invocation instead of being discarded.
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
                    "subagent_type": agent,
                },
            },
        )

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def wait_for(self, observable: str, reference: str, bound_seconds: int) -> str:
        """No-op: OpenCode's runtime holds no wait channel.

        The decline is not hollow. Every liveness surface a runtime-held wait
        would need is already absent on this target — no platform-provided
        session id (issue #9292), no hook channel (issue anomalyco/opencode#8619)
        — and the OpenCode runtime bootstraps none of the shared build layer the
        observables are inspected through. A wait held here would be an
        unobservable block with no re-attach path.

        The alternative is real, shipped behaviour on this target, not a
        weaker stand-in for a capability OpenCode lacks entirely: the
        observable's own bounded-wait verb runs in-turn, and
        checkpoint-and-re-dispatch remains available when the bound is large.
        """
        return toon_noop(
            "wait for",
            "OpenCode's runtime holds no wait channel — it has no platform-provided"
            " session id (issue #9292), no hook channel"
            " (issue anomalyco/opencode#8619), and no shared build layer to inspect"
            " an observable through, so a wait held here would be unobservable and"
            " could not be re-attached",
            "Invoke the observable's own bounded-wait verb synchronously in-turn"
            " (build-server-client wait, ci checks wait), or checkpoint and"
            " re-dispatch to re-establish the wait from persisted state",
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
