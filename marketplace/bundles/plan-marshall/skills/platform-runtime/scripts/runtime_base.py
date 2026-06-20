#!/usr/bin/env python3
"""
Abstract base class and shared TOON helpers for platform-runtime.

Defines the Runtime ABC with all 16 platform operations. Concrete subclasses
(ClaudeRuntime, OpenCodeRuntime) implement each operation for their target.

TOON helpers delegate to the canonical toon_parser from ref-toon-format — no
ad-hoc parsing or serialization in this module.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from toon_parser import serialize_toon

# =============================================================================
# TOON Response Builders
#
# Every public helper returns a ready-to-print string via serialize_toon().
# Callers pass these strings directly to print() or return them as the script
# body. No ad-hoc formatting is performed; all serialization goes through the
# canonical ref-toon-format module.
# =============================================================================


def toon_success(operation: str, result: dict[str, Any] | None = None) -> str:
    """Build a TOON success response.

    Args:
        operation: The operation name (e.g. "session capture").
        result: Optional dict of result fields to merge into the response.

    Returns:
        Serialized TOON string.
    """
    data: dict[str, Any] = {
        "status": "success",
        "operation": operation,
    }
    if result:
        data.update(result)
    return serialize_toon(data)


def toon_error(operation: str, code: str, message: str) -> str:
    """Build a TOON error response.

    Args:
        operation: The operation name.
        code: Machine-readable error code (e.g. "hook_not_configured").
        message: Human-readable explanation of the error.

    Returns:
        Serialized TOON string.
    """
    data: dict[str, Any] = {
        "status": "error",
        "operation": operation,
        "error": code,
        "message": message,
    }
    return serialize_toon(data)


def toon_noop(operation: str, reason: str, alternative: str) -> str:
    """Build a TOON no-op response.

    Args:
        operation: The operation name.
        reason: Why the operation is a no-op on this target.
        alternative: What the caller can do instead.

    Returns:
        Serialized TOON string.
    """
    data: dict[str, Any] = {
        "status": "no-op",
        "operation": operation,
        "reason": reason,
        "alternative": alternative,
    }
    return serialize_toon(data)


# =============================================================================
# Abstract Base Class
# =============================================================================


class Runtime(ABC):
    """Abstract base for platform-runtime target implementations.

    Subclasses must implement every abstract method.  The router
    (platform_runtime.py) instantiates the correct subclass based on
    ``runtime.target`` in ``.plan/marshal.json`` and dispatches the requested
    operation.

    All methods return a serialized TOON string ready for ``print()``.  Use
    the ``toon_success``, ``toon_error``, and ``toon_noop`` helpers from this
    module to build responses; never format TOON strings manually.
    """

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def project_initial_setup(self, project_dir: str, target: str) -> str:
        """One-time project setup.

        Creates ``.plan/``, seeds ``marshal.json`` with ``runtime.target``,
        ensures ``.plan/temp/`` exists, and installs any platform-specific
        session hook.

        Args:
            project_dir: Project root directory path.
            target: Platform target identifier (``"claude"`` or ``"opencode"``).

        Returns:
            Serialized TOON string (success or error).
        """

    @abstractmethod
    def project_install_hook(
        self,
        target: str,
        overwrite_statusline: bool = False,
        overwrite_env_disable: bool = False,
    ) -> str:
        """Install the full terminal-title hook wiring into a named settings file.

        Reads (or creates) *target* and idempotently installs the SessionStart
        capture entry, render entries across all five render-trigger hook events
        (SessionStart matcher-less + matcher:"clear", UserPromptSubmit,
        Notification, Stop, PostToolUse:AskUserQuestion), the ``statusLine``
        command, and ``env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE = "1"``.

        Unlike ``project_initial_setup``, this operation does not create
        ``.plan/`` or seed ``marshal.json`` — it only mutates the named file.

        Args:
            target: Path to the settings file the hooks are installed into
                (e.g. ``.claude/settings.local.json``).
            overwrite_statusline: When True, overwrite an existing
                ``statusLine`` whose command differs from the renderer; when
                False, preserve the foreign value and surface
                ``statusLine_status: already_present_other`` so the caller
                can prompt.
            overwrite_env_disable: Same semantics for
                ``env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE``.

        Returns:
            Serialized TOON string (success, error, or no-op) carrying
            ``target``, ``hook_installed``, ``already_present``,
            ``installed_events``, ``already_present_events``,
            ``statusLine_status``, and ``env_status`` fields.
        """

    # ------------------------------------------------------------------
    # Filesystem layout resolution
    # ------------------------------------------------------------------

    @abstractmethod
    def layout_skill_roots(self) -> str:
        """Resolve the project-local-skill discovery root(s) for this target.

        Returns the ordered list of directory paths (relative to a project
        root, or ``~``-anchored for user-global roots) where ``project:``
        skills — finalize-steps, recipes, verify-steps, domain-attachable
        skills — are discovered on this target. Callers resolve each returned
        root against the relevant base directory and probe in list order
        (first match wins).

        On Claude: returns the single ``.claude/skills`` root.

        On OpenCode: returns the multi-root list mirroring the executor's
        discovery order (``$OPENCODE_CONFIG_DIR/skills``, ``.opencode/skills``,
        ``.claude/skills``, ``.agents/skills`` and the ``~``-anchored
        user-global variants).

        The result does not change for the lifetime of a process (the target
        is fixed by ``marshal.json``), so callers memoise it per process —
        this is the documented mitigation for the subprocess hop on hot
        config/manifest paths.

        Returns:
            Serialized TOON string carrying ``roots[N]`` — the ordered list of
            project-local-skill discovery roots for the active target.
        """

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    @abstractmethod
    def session_capture(self, plan_id: str) -> str:
        """Read and persist the current platform session identifier.

        On Claude: reads ``$CLAUDE_CODE_SESSION_ID`` and stores it via
        ``manage-status``.  Returns ``error`` with code
        ``hook_not_configured`` when the env var is absent.

        On OpenCode: returns ``no-op`` because the platform does not expose a
        session id to the shell environment.

        Args:
            plan_id: Plan identifier used by ``manage-status``.

        Returns:
            Serialized TOON string (success, error, or no-op).
        """

    @abstractmethod
    def session_render_title(self, statusline: bool = False) -> str:
        """Render the current plan title in the terminal.

        Resolves session → plan, reads the title state from ``status.json``,
        composes the title via the ``manage-terminal-title`` composer, and
        emits the platform-appropriate sequence.

        Args:
            statusline: When True, the success branch emits plain text
                (``f"{icon} {body}"``) instead of the JSON envelope, matching
                the ``statusLine`` hook contract. Noop branches still emit
                nothing on stdout. Default ``False`` preserves the
                hook-driven JSON-envelope contract.

        Returns:
            Serialized TOON string (success or no-op).
        """

    @abstractmethod
    def session_push_title_token(self, plan_id: str, icon: str) -> str:
        """Push a live terminal title for *plan_id* directly to ``/dev/tty``.

        Resolves the plan's title state from ``status.json``, composes the
        ``'{icon} {glyph} {body}'`` string via the ``manage-terminal-title``
        composer (with *icon* as the push-mode icon override), and writes the
        OSC escape (``\\x1b]0;{composed}\\x07``) directly to ``/dev/tty``.

        This is push-mode emission for blocking callers (e.g. a lock/build
        acquire wait) that need the title refreshed without a hook firing.

        On Claude: best-effort — silent no-op when ``/dev/tty`` is not openable
        (CI / background / no controlling terminal); never raises.

        On OpenCode: returns ``no-op`` (no plugin-driven terminal-title channel).

        Args:
            plan_id: Plan identifier whose ``status.json`` supplies the title
                state.
            icon: The push-mode icon glyph that overrides the event-resolved
                icon for non-terminal phases.

        Returns:
            Serialized TOON string (success or no-op) noting whether the push
            reached a TTY.
        """

    # ------------------------------------------------------------------
    # Permission operations
    # ------------------------------------------------------------------

    @abstractmethod
    def permission_configure(self, scope: str, permissions: list[str]) -> str:
        """Write a raw permission list to the platform settings.

        Args:
            scope: ``"project"`` or ``"global"``.
            permissions: List of permission patterns to write.

        Returns:
            Serialized TOON string (success or error).
        """

    @abstractmethod
    def permission_analyze(
        self, scope: str, checks: list[str], marshal_path: str | None
    ) -> str:
        """Read-only audit of permission configuration.

        Args:
            scope: ``"global"``, ``"project"``, or ``"both"``.
            checks: List of check names: ``"redundant"``, ``"suspicious"``,
                ``"missing-steps"``, or ``"all"``.
            marshal_path: Path to ``marshal.json`` (required when
                ``"missing-steps"`` is in checks).

        Returns:
            Serialized TOON string (success or error).
        """

    @abstractmethod
    def permission_fix(
        self,
        scope: str,
        operation: str,
        permissions: list[str],
        dry_run: bool,
    ) -> str:
        """Apply hygienic fixes to permission configuration.

        Args:
            scope: ``"project"`` or ``"global"``.
            operation: One of ``"normalize"``, ``"add"``, ``"remove"``,
                ``"ensure"``, ``"consolidate"``.
            permissions: Patterns for ``add``/``remove``/``ensure`` (may be
                empty for ``normalize`` and ``consolidate``).
            dry_run: When ``True``, preview changes without applying.

        Returns:
            Serialized TOON string (success or error).
        """

    @abstractmethod
    def permission_ensure_wildcards(
        self, scope: str, marketplace_dir: str, dry_run: bool
    ) -> str:
        """Ensure marketplace bundle wildcard permissions exist.

        Args:
            scope: ``"project"`` or ``"global"``.
            marketplace_dir: Path to the marketplace directory.
            dry_run: When ``True``, preview changes without applying.

        Returns:
            Serialized TOON string (success or error).
        """

    @abstractmethod
    def permission_ensure_steps(
        self, marshal_path: str, scope: str, dry_run: bool
    ) -> str:
        """Ensure permissions exist for all ``project:{skill}`` steps.

        Args:
            marshal_path: Path to ``marshal.json``.
            scope: ``"project"`` or ``"global"``.
            dry_run: When ``True``, preview changes without applying.

        Returns:
            Serialized TOON string (success or error).
        """

    @abstractmethod
    def permission_web_analyze(self, scope: str) -> str:
        """Read-only analysis of WebFetch/webfetch domain permissions.

        Args:
            scope: ``"global"``, ``"project"``, or ``"both"``.

        Returns:
            Serialized TOON string (success or error).
        """

    @abstractmethod
    def permission_web_apply(
        self,
        scope: str,
        add: list[str],
        remove: list[str],
        dry_run: bool,
    ) -> str:
        """Add or remove web domain permissions.

        Args:
            scope: ``"project"`` or ``"global"``.
            add: Domain names to allow.
            remove: Domain names to remove.
            dry_run: When ``True``, preview changes without applying.

        Returns:
            Serialized TOON string (success or error).
        """

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @abstractmethod
    def metrics_capture(
        self, plan_id: str, phase: str, total_tokens: int | None
    ) -> str:
        """Record token consumption for a planning phase.

        On Claude: reads session transcript and sums tokens since the last
        capture for this phase.

        On OpenCode: returns ``no-op`` unless ``total_tokens`` is provided, in
        which case it stores the value directly.

        Args:
            plan_id: Plan identifier.
            phase: Phase identifier (e.g. ``"phase-1-init"``).
            total_tokens: Explicit token count (optional; bypasses transcript
                scan when provided).

        Returns:
            Serialized TOON string (success, error, or no-op).
        """

    # ------------------------------------------------------------------
    # Subagent dispatch
    # ------------------------------------------------------------------

    @abstractmethod
    def subagent_dispatch(
        self,
        agent: str,
        prompt_file: str | None,
        context: dict[str, Any] | None,
    ) -> str:
        """Return platform-specific subagent invocation parameters.

        Does NOT spawn the subagent; returns a TOON payload with the exact
        parameters the caller must pass to the platform's native tool (``Task:``
        on Claude, ``task`` on OpenCode).

        Returns ``no-op`` when the agent requires tools with no platform
        equivalent.

        Args:
            agent: Agent name without ``.md`` extension.
            prompt_file: Optional path to a prompt markdown file; when omitted
                the agent's own body is used.
            context: Optional key-value pairs to inject into the prompt.

        Returns:
            Serialized TOON string (success, error, or no-op).
        """

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    @abstractmethod
    def health_check(self, checks: str) -> str:
        """Verify platform integration.

        Args:
            checks: Comma-separated list of checks: ``"all"``,
                ``"permissions"``, ``"display"``, ``"mcp-diagnostics"``.

        Returns:
            Serialized TOON string (success or error).
        """
