#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""ClaudeRuntime operation implementations — the ``ClaudeRuntime`` class body.

Relocated verbatim from ``claude_runtime.py`` (the entry module) to keep the
entry under the module-size ceiling. The entry stays the single home of every
module-level helper, constant, and monkeypatchable name; this module holds only
the ``class ClaudeRuntime(Runtime)`` operation implementations.

Correctness contract: the entry module (imported here as ``claude_runtime``) owns
the monkeypatchable constants (``_CLAUDE_PROJECTS_DIR``, ``_PLAN_DIR_NAME``) and
settings-path functions
(``_claude_global_settings_path``, ``_claude_project_settings_path``) plus every
other module-level helper the operations depend on. This module reaches each of
those names via ATTRIBUTE ACCESS at call time (``claude_runtime.<name>``) — never
a ``from``-import — so a test's monkeypatch of ``claude_runtime.<name>`` is
honored. The base class and the TOON/compose primitives are not monkeypatched, so
they are imported directly below.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import claude_runtime
import session_binding
from manage_terminal_title import _compose_body, compose
from runtime_base import Runtime, toon_error, toon_noop, toon_success


class ClaudeRuntime(Runtime):
    """Claude Code implementation of all 24 platform-runtime operations."""

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    def project_initial_setup(self, project_dir: str, target: str) -> str:
        """One-time project setup for the Claude Code target."""
        if target != "claude":
            return toon_error(
                "project initial-setup",
                "unknown_target",
                f"Target {target!r} is not in the registry; valid targets are: claude, opencode",
            )

        pd = claude_runtime._project_dir_path(project_dir)
        plan_dir = pd / claude_runtime._PLAN_DIR_NAME
        temp_dir = plan_dir / "temp"
        marshal_path = plan_dir / "marshal.json"
        settings_path = pd / ".claude" / "settings.json"

        # Create directory structure.
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to create .plan/temp/: {exc}",
            )

        # Write marshal.json with runtime.target.
        marshal_data: dict[str, Any] = {
            "runtime": {"target": "claude"},
            "project_dir": str(pd),
        }
        if not claude_runtime._write_json(marshal_path, marshal_data):
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to write marshal.json at {marshal_path}",
            )

        # Install the full terminal-title hook wiring into .claude/settings.json.
        install_result = claude_runtime._install_terminal_title_hooks(settings_path)
        hook_installed = install_result["io_ok"]

        return toon_success(
            "project initial-setup",
            {
                "target": "claude",
                "project_dir": str(pd),
                "marshal_written": True,
                "hook_installed": hook_installed,
            },
        )

    def project_install_hook(
        self,
        target: str,
        overwrite_statusline: bool = False,
        overwrite_env_disable: bool = False,
        enforcement: bool = False,
    ) -> str:
        """Install the full terminal-title hook wiring into the named settings file.

        Installs the SessionStart capture entry, seven render-trigger hook
        entries, the ``statusLine`` command, and
        ``env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE``. Each block is idempotent.

        When ``enforcement`` is True, installs ONLY the orthogonal PreToolUse
        enforcement entry (the ``claude_pretooluse_hook`` matcher-less entry) and
        does NOT install the terminal-title bundle. The two install modes are
        independent: ``project install-hook`` installs terminal-title;
        ``project install-hook --enforcement`` installs the enforcement entry;
        neither disturbs the other's entries.

        The ``target`` argument is one of two shapes:

        - ``"claude"`` — the platform identifier. For the terminal-title install
          this resolves to the project's Claude Code settings file via
          ``_claude_project_settings_path()`` (``.claude/settings.json`` when
          present, else ``.claude/settings.local.json``). For the
          ``enforcement`` install it pins ``.claude/settings.local.json`` via
          ``_claude_local_settings_path()`` — the operator-local opt-in belongs
          there and that is the file the ``display`` health-check enforcement
          label and the install contract both reference.
          This is the canonical invocation from the marshall-steward menu.
        - An absolute path ending in ``.json`` — explicit settings file path.
          Used by tests and recovery flows that need to target a specific file.

        Any other value (relative path, unknown identifier) is rejected with
        ``unknown_target`` rather than silently creating a stray file.

        The two ``overwrite_*`` flags govern conflict resolution when an
        existing ``statusLine`` or env value differs from ours:

        - ``overwrite_statusline=False`` (default): preserve the foreign value
          and report ``statusLine_status: already_present_other`` so the
          marshall-steward menu can surface an AskUserQuestion.
        - ``overwrite_statusline=True``: overwrite with our command and report
          ``statusLine_status: overwritten``.

        ``overwrite_env_disable`` carries identical semantics for the env entry.
        """
        if target == "claude":
            settings_path = (
                claude_runtime._claude_local_settings_path()
                if enforcement
                else claude_runtime._claude_project_settings_path()
            )
        else:
            candidate = Path(target)
            if candidate.is_absolute() and candidate.suffix == ".json":
                settings_path = candidate
            else:
                return toon_error(
                    "project install-hook",
                    "unknown_target",
                    f"target {target!r} must be the platform identifier 'claude' "
                    f"or an absolute path to a .json settings file",
                )

        # Orthogonal enforcement-only install path: install ONLY the PreToolUse
        # enforcement entry and return — never touch the terminal-title bundle.
        if enforcement:
            enforcement_result = claude_runtime._install_enforcement_hook(settings_path)
            if not enforcement_result["io_ok"]:
                return toon_error(
                    "project install-hook",
                    "io_error",
                    f"Failed to install enforcement hook into {settings_path}",
                )
            enforcement_status = enforcement_result["enforcement_status"]
            return toon_success(
                "project install-hook",
                {
                    "target": target,
                    "settings_path": str(settings_path),
                    "enforcement_installed": True,
                    "enforcement_status": enforcement_status,
                    "already_present": enforcement_status == "already_present",
                },
            )

        install_result = claude_runtime._install_terminal_title_hooks(
            settings_path,
            overwrite_statusline=overwrite_statusline,
            overwrite_env_disable=overwrite_env_disable,
        )
        if not install_result["io_ok"]:
            return toon_error(
                "project install-hook",
                "io_error",
                f"Failed to install terminal-title hooks into {settings_path}",
            )

        installed_events = install_result["installed_events"]
        already_present_events = install_result["already_present_events"]
        # Top-level convenience signal: True iff nothing fresh was installed
        # AND no overwrite-other signal needs the caller's attention.
        all_already_present = (
            not installed_events
            and install_result["statusLine_status"]
            in ("already_present", "already_present_other")
            and install_result["env_status"]
            in ("already_present", "already_present_other")
        )

        return toon_success(
            "project install-hook",
            {
                "target": target,
                "settings_path": str(settings_path),
                "hook_installed": True,
                "already_present": all_already_present,
                "installed_events": installed_events,
                "already_present_events": already_present_events,
                "statusLine_status": install_result["statusLine_status"],
                "env_status": install_result["env_status"],
            },
        )

    # ------------------------------------------------------------------
    # Filesystem layout resolution
    # ------------------------------------------------------------------

    def layout_skill_roots(self) -> str:
        """Return the Claude project-local-skill root: ``.claude/skills``."""
        return toon_success(
            "layout skill-roots",
            {"target": "claude", "roots": [".claude/skills"]},
        )

    def layout_bundle_cache_root(self) -> str:
        """Return the Claude deployed-bundle cache root.

        ``~/.claude/plugins/cache/plan-marshall`` — the single flat cache root
        under which installed marketplace bundles live on Claude.
        """
        import pathlib

        cache_root = pathlib.Path.home() / ".claude" / "plugins" / "cache" / "plan-marshall"
        return toon_success(
            "layout bundle-cache-root",
            {"target": "claude", "roots": [str(cache_root)]},
        )

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    def session_capture(self, plan_id: str) -> str:
        """Read $CLAUDE_CODE_SESSION_ID and store via manage-status."""
        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
        if not session_id:
            return toon_error(
                "session capture",
                "hook_not_configured",
                "$CLAUDE_CODE_SESSION_ID is unset; run marshall-steward to install the SessionStart hook",
            )

        stored = claude_runtime._manage_status_store_session(plan_id, session_id)
        return toon_success(
            "session capture",
            {
                "plan_id": plan_id,
                "session_id": session_id,
                "stored": stored,
            },
        )

    def session_render_title(self, statusline: bool = False) -> str:
        """Resolve session → plan, read ``status.json``, compose, and emit.

        Both invocation modes share one stdout contract: stdout carries the
        exact bytes Claude Code's host parser consumes, and **nothing else**.
        Mixed payloads — JSON envelope plus a TOON success/noop row glued to
        it, or TOON noop instead of empty output — violate the contract and
        are dropped by the host parser (see ``hook-authoring-guide.md`` §
        "Hook output contract").

        Hook mode (``statusline=False``):
          - Success: write the JSON envelope to stdout, return "".
          - Noop: write nothing to stdout, return "".
        statusLine mode (``statusline=True``):
          - Success: write plain ``{composed}`` to stdout, return "".
          - Noop: write nothing to stdout, return "".

        The title state (``current_phase``, ``short_description``,
        ``title_token``) is read from ``status.json`` — the SINGLE source of
        persisted title state — and the body-format + glyph vocabulary + icon
        palette live in the ``manage-terminal-title`` composer
        (:func:`manage_terminal_title.compose`), consumed via import. This
        module is the resolve+read+emit layer only; it owns neither the icon
        palette nor the body format. The ✅ terminal-icon override for
        ``complete``/``archived`` phases is applied inside ``compose``.

        Hook-mode envelope (Step 5) carries two reader channels in one JSON
        object. ``terminalSequence`` (the OSC-0 escape) is emitted for every
        event. ``hookSpecificOutput.sessionTitle`` — the web/desktop
        session-title channel, equivalent to ``/rename`` and UI-only — is
        emitted ONLY for the two events Claude Code supports it on:

          - ``UserPromptSubmit``; and
          - ``SessionStart`` when ``source ∈ {"startup", "resume"}`` (the
            ``"clear"`` and ``"compact"`` sources do NOT support it).

        For every other event the envelope stays exactly ``{"terminalSequence":
        osc_seq}`` and never carries a stray ``sessionTitle``. The
        ``sessionTitle`` body is the bare ``pm:{phase}[:{short}]`` body (via
        :func:`manage_terminal_title._compose_body`) WITHOUT the icon glyph,
        because the web title channel is static per-prompt text and cannot carry
        the live status icon. A missing or malformed ``hook_event_name`` /
        ``source`` omits ``sessionTitle`` and still emits ``terminalSequence``
        (best-effort/no-raise contract).

        Every return is the empty string so the wrapper ``main()`` (which
        skips ``print()`` on empty results) cannot append a TOON tail.
        """

        # Step 1: Read $CLAUDE_CODE_SESSION_ID.
        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
        if not session_id:
            return ""

        # Step 2: Resolve session_id → plan_id via the session cache. A plan
        # binding wins; when absent, an ORCHESTRATOR epic binding is the fallback
        # (Step 3) so the orchestrator title reaches the PRIMARY hook channel —
        # its /dev/tty push is only a blocking-window fallback, permanently inert
        # in a tty-less runtime (which is every context here).
        plan_id = claude_runtime._read_active_plan(session_id)

        # Step 3: Resolve the title state via status.json (the SINGLE source of
        # persisted title state — title-body.txt is no longer read anywhere). A
        # plan binding reads the plan status.json (live / worktree / archived
        # fallback); when no plan is bound, an orchestrator epic slug is resolved
        # and its state read via the existing orchestrator composer branch. The
        # plan read path is byte-for-byte unchanged (D5(c)) — the orchestrator
        # resolve is a parallel fallback reached only when the plan slot is empty.
        if plan_id:
            state = claude_runtime._read_title_state(plan_id)
        else:
            slug = claude_runtime._read_active_orchestrator(session_id)
            if not slug:
                return ""
            state = claude_runtime._read_orchestrator_title_state(slug)
        if state is None:
            return ""

        # Step 4: Parse the hook event (hook mode only) and compose the title.
        #
        # statusLine mode receives no hook stdin payload, so it composes with
        # process_state=None (the composer applies the active icon for
        # non-terminal phases and the ✅ override for terminal ones). Hook mode
        # reads the JSON payload Claude Code writes to stdin, then maps the event
        # + tool_name to the composer's neutral process state. The parse is
        # best-effort: missing, empty, or malformed stdin yields event=None and
        # never raises.
        #
        # The parsed ``hook_event_name`` and ``source`` are also retained for
        # Step 5's conditional ``sessionTitle`` emit. Both default to None so a
        # missing/malformed payload omits ``sessionTitle`` and still emits
        # ``terminalSequence``.
        hook_event_name: str | None = None
        source: str | None = None
        tool_name: str | None = None
        tool_command: str | None = None
        if not statusline:
            try:
                raw_payload = sys.stdin.read() if not sys.stdin.isatty() else ""
                payload = json.loads(raw_payload) if raw_payload.strip() else {}
                if isinstance(payload, dict):
                    hook_event_name = payload.get("hook_event_name")
                    source = payload.get("source")
                    tool_name = payload.get("tool_name")
                    tool_input = payload.get("tool_input")
                    if isinstance(tool_input, dict):
                        raw_command = tool_input.get("command")
                        if isinstance(raw_command, str):
                            tool_command = raw_command
            except (OSError, ValueError):
                hook_event_name = None
                source = None
                tool_name = None
                tool_command = None

        # SessionStart:clear is a session TEARDOWN, not a render. The cleared
        # session keeps no plan binding and its tab must return to the
        # terminal's own default, so this event performs the teardown and writes
        # NOTHING to stdout — a render here would repaint a title for a session
        # that no longer drives a plan.
        if not statusline and hook_event_name == "SessionStart" and source == "clear":
            self.session_teardown()
            return ""

        # Build-busy hook assist (D5): when a PreToolUse:Bash event carries a
        # build-wrapper command, force the persistent 🔨 build-busy title-token
        # for this render — set it in the in-memory state dict BEFORE compose so
        # this render paints ``🔨 pm:{phase}`` via the composer's icon-slot
        # override, AND persist it best-effort so the state survives to subsequent
        # renders and for the agent's D3 clear. The hook only SETs — it never
        # CLEARs, because a backgrounded build's PostToolUse:Bash fires
        # immediately (not at job end), so the clear is necessarily the agent's
        # D3 obligation. A non-build command / missing tool_input is a silent
        # no-op (the existing PreToolUse:Bash → ⚙ busy mapping remains the
        # fallback).
        if (
            not statusline
            and hook_event_name == "PreToolUse"
            and tool_name == "Bash"
            and claude_runtime._command_is_build(tool_command)
        ):
            state["title_token"] = "build-busy"
            # Paint 🔨 for this render via the in-memory token above; persist it
            # only for a plan-bound render. An orchestrator-bound render has no
            # plan status.json to write (plan_id is empty), so the persist is
            # skipped — the in-memory token still paints this render.
            if plan_id:
                claude_runtime._manage_status_set_title_token(plan_id, "build-busy")

        # Map the Claude hook event → the composer's target-neutral process
        # state, then compose. The composer no longer knows any Claude event
        # vocabulary; this mapping is the Claude-target half.
        process_state = claude_runtime._claude_event_to_process_state(hook_event_name, tool_name)
        composed = compose(state, process_state)
        if not composed:
            return ""

        # Step 5: Emit the title. Both modes write to stdout and return "".
        if statusline:
            try:
                sys.stdout.write(composed)
                sys.stdout.flush()
            except OSError:
                pass
            return ""

        try:
            osc_seq = f"\x1b]0;{composed}\x07"
            envelope: dict[str, Any] = {"terminalSequence": osc_seq}
            # Conditional web/desktop session-title channel: emit
            # ``hookSpecificOutput.sessionTitle`` (icon-free body) ONLY for the
            # two events Claude Code supports it on — UserPromptSubmit, and
            # SessionStart with source in {startup, resume}. All other events
            # keep the envelope as ``{"terminalSequence": osc_seq}``.
            emit_session_title = hook_event_name == "UserPromptSubmit" or (
                hook_event_name == "SessionStart" and source in ("startup", "resume")
            )
            if emit_session_title:
                bare_body = _compose_body(state)
                if bare_body:
                    envelope["hookSpecificOutput"] = {
                        "hookEventName": hook_event_name,
                        "sessionTitle": bare_body,
                    }
            sys.stdout.write(json.dumps(envelope))
            sys.stdout.flush()
        except OSError:
            pass
        return ""

    def session_push_title_token(
        self,
        plan_id: str,
        icon: str | None = None,
        store: str = "plans",
        slug: str | None = None,
    ) -> str:
        """Push a live terminal title for *plan_id* directly to ``/dev/tty``.

        ``/dev/tty`` is the **FALLBACK** delivery channel, not the primary one.
        The primary channel is the hook-mode ``terminalSequence`` envelope that
        Claude Code itself writes on every render-trigger event (see
        :meth:`session_render_title`); this push exists for the blocking windows
        no hook event spans (a long build, a CI wait, a lock hold). Off a
        controlling terminal — inside a dispatched agent, a CI runner, or a
        backgrounded process — ``/dev/tty`` is not openable and the push cannot
        land. That non-delivery is now **reported**, not swallowed: the return
        TOON carries ``pushed: false`` with ``reason: no_controlling_tty``, and
        every outcome names its channel via ``delivery: dev_tty_fallback`` so a
        caller can tell the fallback path from the hook-delivered one.

        Reads the plan's title state from ``status.json`` via
        :func:`_read_title_state`, composes the title string via
        :func:`manage_terminal_title.compose` (with *icon* as the push-mode icon
        override and ``event=None``), and writes the OSC escape
        (``\\x1b]0;{composed}\\x07``) directly to ``/dev/tty``.

        With ``store="orchestrator"`` the state read routes through
        :func:`claude_runtime._read_orchestrator_title_state` instead — the
        epic's ``status.json`` resolved via ``get_store_dir('orchestrator',
        slug)`` — and the composer renders the ``Orchestrator-{SlugName}``
        body. The orchestrator push additionally establishes the session→epic
        binding via :func:`session_binding.bind_orchestrator` (best-effort, from
        ``$CLAUDE_CODE_SESSION_ID``) BEFORE the ``/dev/tty`` attempt, so the
        hook-driven PRIMARY channel (:meth:`session_render_title`) resolves the
        epic and delivers its title on subsequent renders — the ``/dev/tty``
        write is only the immediate blocking-window FALLBACK. The orchestrator
        push also distinguishes a configured-OFF terminal-title feature
        (``pushed: false`` with ``reason: feature_inactive``) from the
        permanently-inert ``/dev/tty`` fallback (``reason: no_controlling_tty``),
        so a dead channel cannot masquerade as a configured-off one — no new
        config knob. Everything else downstream of the state read (compose,
        ``/dev/tty`` write, best-effort gating) is shared with the plans-store
        path: an absent / unrenderable state stays the existing no-op.

        ``icon`` is optional. When supplied it overrides the event-resolved icon
        for non-terminal phases (e.g. the lock ⏳/🔒 or build 🔨 glyph). When
        omitted (``None``) the composer applies its default active icon, so the
        push is a plain repaint of the current composed title — the shape the
        ``manage-status`` phase-write drive seam fires on every persisted
        title-state change.

        Best-effort: a no-op (``pushed: false``) when the state is absent /
        unrenderable (``reason: no_title_state``) or when ``/dev/tty`` is not
        openable (``reason: no_controlling_tty``). Never raises, and never
        changes the caller's status or exit code — only the observability of a
        non-delivery differs between the two reasons.

        Returns a success TOON noting whether the push reached a TTY, the
        ``reason`` when it did not, and the ``delivery`` channel on every
        ``/dev/tty`` attempt.
        """
        if store == "orchestrator":
            # Establish the session→epic binding as a best-effort side effect so
            # the hook-driven PRIMARY channel (session render-title) resolves the
            # epic and delivers its title on subsequent renders. Fired BEFORE the
            # /dev/tty attempt so the primary channel takes over on the next
            # render even when this fallback cannot land (which it never does in a
            # tty-less runtime).
            session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
            if session_id and slug:
                session_binding.bind_orchestrator(session_id, slug)
            state = claude_runtime._read_orchestrator_title_state(slug or "")
            entry_fields: dict[str, Any] = {"store": store, "slug": slug or ""}
        else:
            state = claude_runtime._read_title_state(plan_id)
            entry_fields = {"plan_id": plan_id}
        if state is None:
            return toon_success(
                "session push-title-token",
                {**entry_fields, "pushed": False, "reason": "no_title_state"},
            )

        composed = compose(state, None, icon_override=icon)
        if not composed:
            return toon_success(
                "session push-title-token",
                {**entry_fields, "pushed": False, "reason": "no_title_state"},
            )

        # For the orchestrator push, distinguish a configured-OFF terminal-title
        # feature (reason: feature_inactive) from the permanently-inert /dev/tty
        # fallback (reason: no_controlling_tty) reported below, so a caller can
        # tell "not wired up" from "wired up but no controlling terminal". The
        # epic binding was already established above, so the PRIMARY hook channel
        # still delivers once the feature is active — this fallback outcome does
        # not gate that.
        if store == "orchestrator" and not claude_runtime._terminal_title_active():
            return toon_success(
                "session push-title-token",
                {**entry_fields, "pushed": False, "reason": "feature_inactive"},
            )

        try:
            with open("/dev/tty", "w", encoding="utf-8") as tty:
                tty.write(f"\x1b]0;{composed}\x07")
                tty.flush()
        except OSError:
            return toon_success(
                "session push-title-token",
                {
                    **entry_fields,
                    "pushed": False,
                    "reason": "no_controlling_tty",
                    "delivery": "dev_tty_fallback",
                },
            )

        return toon_success(
            "session push-title-token",
            {**entry_fields, "pushed": True, "delivery": "dev_tty_fallback"},
        )

    def session_bind(self, plan_id: str, session_id: str | None = None) -> str:
        """Bind the running session to *plan_id* (last-driven-wins).

        Resolves ``session_id`` from the *session_id* argument or, when absent,
        from ``$CLAUDE_CODE_SESSION_ID``, then delegates to the pure
        :func:`session_binding.bind` policy — an unconditional write of the
        caller's own slot (no protect-active, no stale reclaim, no
        plan-dir-exists check). Best-effort: never raises.

        Returns a success TOON carrying ``bound`` (whether the slot was written).
        A missing session id or a validation/IO failure yields ``bound: False``
        with a ``reason``.
        """
        sid = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")
        if not sid:
            return toon_success(
                "session bind",
                {"plan_id": plan_id, "bound": False, "reason": "no_session_id"},
            )
        bound = session_binding.bind(sid, plan_id)
        result: dict[str, Any] = {
            "plan_id": plan_id,
            "session_id": sid,
            "bound": bound,
        }
        if not bound:
            result["reason"] = "invalid_or_io_error"
        return toon_success("session bind", result)

    def session_resolve_plan(self, session_id: str | None = None) -> str:
        """Resolve the running session's bound plan_id (the read side).

        Resolves ``session_id`` from the *session_id* argument or, when absent,
        from ``$CLAUDE_CODE_SESSION_ID``, then reads the binding through
        :func:`claude_runtime._read_active_plan` (the same read path
        ``session render-title`` uses). Best-effort: never raises.

        Returns a success TOON carrying ``resolved`` and the resolved ``plan_id``
        (empty string when unbound).
        """
        sid = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")
        if not sid:
            return toon_success(
                "session resolve-plan",
                {"resolved": False, "plan_id": "", "reason": "no_session_id"},
            )
        plan_id = claude_runtime._read_active_plan(sid)
        return toon_success(
            "session resolve-plan",
            {
                "session_id": sid,
                "resolved": bool(plan_id),
                "plan_id": plan_id or "",
            },
        )

    def session_doctor(self, fix: bool = False) -> str:
        """Visit every session directory under the cache root and report binding health.

        Delegates to the pure :func:`session_binding.doctor` policy — a
        reverse-index scan flagging any plan bound by more than one live session,
        plus (when *fix*) GC of slots whose plan is archived/deleted AND a prune
        of orphan directories that yield no live slot at all. The scan keeps no
        shared mutable index and is idempotent.

        Returns a success TOON carrying the conflict / stale / orphan report.
        Conflicts, stale slots, and orphan directories are all rendered as flat
        string rows (``plan_id=sess1,sess2``, ``session_id=plan_id``, and the bare
        ``session_id`` respectively) for a uniform TOON surface.
        """
        report = session_binding.doctor(fix)
        conflicts = [
            f"{c['plan_id']}={','.join(c['sessions'])}" for c in report["conflicts"]
        ]
        stale = [f"{s['session_id']}={s['plan_id']}" for s in report["stale"]]
        orphans = list(report["orphans"])
        return toon_success(
            "session doctor",
            {
                "fix": report["fix"],
                "scanned": report["scanned"],
                "conflict_count": len(conflicts),
                "conflicts": conflicts,
                "stale_count": len(stale),
                "stale": stale,
                "gc_removed": report["gc_removed"],
                "orphan_count": len(orphans),
                "orphans": orphans,
                "orphans_removed": report["orphans_removed"],
            },
        )

    def session_teardown(self) -> str:
        """Reset the terminal title and release this session's plan binding.

        Order is load-bearing: the ACTIVATION signal is read FIRST. When the
        terminal-title feature is not wired up (no render-hook entry on any
        render-trigger event and no ``statusLine`` command — see
        :func:`claude_runtime._terminal_title_active`), the op returns
        ``active: false`` / ``reason: feature_inactive`` having written NO title
        escape, opened NO ``/dev/tty``, mutated NO binding, and raised nothing.
        A project that never opted into terminal titles is never touched.

        When active: resolve the session id from ``$CLAUDE_CODE_SESSION_ID``,
        write the neutral-default reset escape ``\\x1b]0;\\x07`` (a bare OSC-0
        with an EMPTY payload, which returns the tab to the terminal's own
        default rather than painting some other string) to ``/dev/tty``
        best-effort, then drop the session's own ``active-plan`` slot via
        :func:`session_binding.unbind`.

        ``reset`` and ``unbound`` are reported INDEPENDENTLY: the title reset can
        land while the unbind fails (or the reverse — e.g. off a controlling
        terminal), and collapsing them into one flag would hide which half
        happened. Best-effort throughout: never raises.
        """
        if not claude_runtime._terminal_title_active():
            return toon_success(
                "session teardown",
                {
                    "active": False,
                    "reset": False,
                    "unbound": False,
                    "reason": "feature_inactive",
                },
            )

        reset = False
        try:
            with open("/dev/tty", "w", encoding="utf-8") as tty:
                tty.write("\x1b]0;\x07")
                tty.flush()
            reset = True
        except OSError:
            reset = False

        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
        unbound = session_binding.unbind(session_id) if session_id else False

        return toon_success(
            "session teardown",
            {"active": True, "reset": reset, "unbound": unbound},
        )

    def session_reload_directive(self) -> str:
        """Resolve the Claude post-upgrade reload directive: ``/reload-plugins``.

        RESOLVES + SURFACES only — a script cannot type a harness-level slash
        command, so the success payload carries the directive TEXT plus the
        monitor caveat for the operator/orchestrator to act on. On Claude
        ``/reload-plugins`` reloads the regenerated executor / agent set live;
        only registered monitors would force a full session restart, and
        plan-marshall registers none.
        """
        return toon_success(
            "session reload-directive",
            {
                "directive": "/reload-plugins",
                "caveat": (
                    "Only monitors require a full session restart; plan-marshall "
                    "registers no monitors, so /reload-plugins picks up the "
                    "regenerated executor / agent set live."
                ),
            },
        )

    # ------------------------------------------------------------------
    # Permission operations
    # ------------------------------------------------------------------

    def permission_configure(self, scope: str, permissions: list[str]) -> str:
        """Write a raw permission list to the Claude Code settings."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission configure",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        settings_path = claude_runtime._settings_path_for_scope(scope)
        settings = claude_runtime._load_settings(settings_path)
        if "error" in settings:
            return toon_error("permission configure", "invalid_settings", settings["error"])
        settings["permissions"]["allow"] = list(permissions)

        if not claude_runtime._save_settings(settings_path, settings):
            return toon_error(
                "permission configure",
                "io_error",
                f"Failed to write settings to {settings_path}",
            )

        return toon_success(
            "permission configure",
            {
                "scope": scope,
                "permissions_written": len(permissions),
                "target_file": str(settings_path),
            },
        )

    def permission_analyze(
        self, scope: str, checks: list[str], marshal_path: str | None
    ) -> str:
        """Read-only audit of permission configuration."""
        valid_scopes = ("global", "project", "both")
        if scope not in valid_scopes:
            return toon_error(
                "permission analyze",
                "invalid_scope",
                f"--scope must be 'global', 'project', or 'both'; got {scope!r}",
            )

        valid_checks = {"redundant", "suspicious", "missing-steps", "all"}
        for check in checks:
            if check not in valid_checks:
                return toon_error(
                    "permission analyze",
                    "invalid_check",
                    f"Unknown check {check!r}; valid checks are: redundant, suspicious, missing-steps, all",
                )

        # Expand 'all'.
        expanded = {"redundant", "suspicious", "missing-steps"} if "all" in checks else set(checks)

        if "missing-steps" in expanded and not marshal_path:
            return toon_error(
                "permission analyze",
                "marshal_not_found",
                "--marshal is required when 'missing-steps' check is included",
            )

        findings: list[dict[str, str]] = []
        checks_run = sorted(expanded)

        # Load settings files.
        global_path = claude_runtime._claude_global_settings_path()
        project_path = claude_runtime._claude_project_settings_path()
        global_settings = claude_runtime._load_settings(global_path) if scope in ("global", "both") else {}
        project_settings = claude_runtime._load_settings(project_path) if scope in ("project", "both") else {}

        global_allow: list[str] = global_settings.get("permissions", {}).get("allow", [])
        project_allow: list[str] = project_settings.get("permissions", {}).get("allow", [])

        # Redundant check: entries present in both global and project.
        if "redundant" in expanded:
            global_set = set(global_allow)
            project_set = set(project_allow)
            for perm in global_set & project_set:
                findings.append(
                    {
                        "check": "redundant",
                        "severity": "info",
                        "details": f"{perm} present in both global and project settings",
                    }
                )

        # Suspicious check: detect security anti-patterns.
        if "suspicious" in expanded:
            suspicious_patterns = [
                (r"Write\(/tmp/", "medium", "Write(/tmp/**) is a broad write permission; consider scoping to a specific path"),
                (r"Bash\(sudo:", "high", "Bash(sudo:*) grants unrestricted sudo; remove or restrict the pattern"),
                (r"Bash\(\*\)", "high", "Bash(*) allows any bash command; this is dangerously broad"),
                (r"Write\(/\*\*\)", "high", "Write(/**) grants write access to the entire filesystem"),
                (r"Read\(/\*\*\)", "medium", "Read(/**) grants read access to the entire filesystem"),
            ]
            all_allow = list(global_allow) + list(project_allow) if scope == "both" else (
                global_allow if scope == "global" else project_allow
            )
            for perm in all_allow:
                for pattern, severity, details in suspicious_patterns:
                    if re.search(pattern, perm):
                        findings.append({"check": "suspicious", "severity": severity, "details": details})

        # Missing-steps check: find project:{skill} steps without matching permission.
        if "missing-steps" in expanded and marshal_path:
            marshal_data, marshal_err = claude_runtime._load_marshal_config(marshal_path)
            if marshal_err:
                return toon_error("permission analyze", "invalid_marshal", marshal_err)
            steps = claude_runtime._extract_project_steps(marshal_data)
            target_allow = project_allow if scope == "project" else list(set(global_allow + project_allow))
            for step_entry in steps:
                skill_name = step_entry.get("skill", "")
                if skill_name and not claude_runtime._skill_permission_covered(skill_name, target_allow):
                    findings.append(
                        {
                            "check": "missing-steps",
                            "severity": "high",
                            "details": f"project:{skill_name} has no matching skill permission",
                        }
                    )

        summary: dict[str, int] = {"high": 0, "medium": 0, "info": 0}
        for f in findings:
            sev = f.get("severity", "info")
            if sev in summary:
                summary[sev] += 1

        return toon_success(
            "permission analyze",
            {
                "scope": scope,
                "checks_run": checks_run,
                "total_findings": len(findings),
                "findings": findings,
                "summary": summary,
            },
        )

    def permission_fix(
        self,
        scope: str,
        operation: str,
        permissions: list[str],
        dry_run: bool,
    ) -> str:
        """Apply hygienic fixes to permission configuration."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission fix",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        valid_ops = ("normalize", "add", "remove", "ensure", "consolidate")
        if operation not in valid_ops:
            return toon_error(
                "permission fix",
                "invalid_operation",
                f"--operation must be one of {valid_ops}; got {operation!r}",
            )

        settings_path = claude_runtime._settings_path_for_scope(scope)
        settings = claude_runtime._load_settings(settings_path)
        if "error" in settings:
            return toon_error("permission fix", "invalid_settings", settings["error"])
        allow: list[str] = settings["permissions"]["allow"]

        changes_applied = 0
        proposed_additions: list[str] = []

        if operation == "normalize":
            original = list(allow)
            # Remove duplicates and sort.
            deduped = list(dict.fromkeys(allow))
            sorted_allow = sorted(deduped)
            # Add defaults if missing.
            defaults = [
                "Edit(.plan/**)",
                "Write(.plan/**)",
                "Read(~/.claude/plugins/cache/**)",
                "Bash(python3 .plan/execute-script.py *)",
            ]
            for d in defaults:
                if d not in sorted_allow:
                    sorted_allow.append(d)
            sorted_allow = sorted(sorted_allow)
            changes_applied = len([p for p in sorted_allow if p not in original]) + (
                len(original) - len(deduped)
            )
            if not dry_run:
                settings["permissions"]["allow"] = sorted_allow
                claude_runtime._save_settings(settings_path, settings)

        elif operation == "add":
            for perm in permissions:
                if perm not in allow:
                    if not dry_run:
                        allow.append(perm)
                        changes_applied += 1
                    else:
                        proposed_additions.append(perm)
            if not dry_run:
                settings["permissions"]["allow"] = allow
                claude_runtime._save_settings(settings_path, settings)

        elif operation == "remove":
            original_len = len(allow)
            allow = [p for p in allow if p not in permissions]
            changes_applied = original_len - len(allow)
            if not dry_run:
                settings["permissions"]["allow"] = allow
                claude_runtime._save_settings(settings_path, settings)

        elif operation == "ensure":
            for perm in permissions:
                if perm not in allow:
                    if not dry_run:
                        allow.append(perm)
                        changes_applied += 1
                    else:
                        proposed_additions.append(perm)
            if not dry_run:
                settings["permissions"]["allow"] = allow
                claude_runtime._save_settings(settings_path, settings)

        elif operation == "consolidate":
            # Group permissions by tool type and base pattern; merge enumerated into wildcards.
            pattern = re.compile(r"^(\w+)\((.+)\)$")
            groups: dict[str, list[str]] = {}
            for perm in allow:
                m = pattern.match(perm)
                if m:
                    tool_type = m.group(1)
                    groups.setdefault(tool_type, []).append(perm)

            new_allow = list(allow)
            for tool_type, perms in groups.items():
                if len(perms) >= 3:
                    # Replace enumerated entries with a wildcard.
                    wildcard = f"{tool_type}(*)"
                    if wildcard not in new_allow:
                        for p in perms:
                            try:
                                new_allow.remove(p)
                                changes_applied += 1
                            except ValueError:
                                pass
                        new_allow.append(wildcard)

            if not dry_run:
                settings["permissions"]["allow"] = new_allow
                claude_runtime._save_settings(settings_path, settings)

        result: dict[str, Any] = {
            "scope": scope,
            "fix_operation": operation,
            "dry_run": dry_run,
            "target_file": str(settings_path),
            "changes_applied": 0 if dry_run else changes_applied,
        }
        if dry_run and proposed_additions:
            result["proposed_additions"] = proposed_additions

        return toon_success("permission fix", result)

    def permission_ensure_wildcards(
        self, scope: str, marketplace_dir: str, dry_run: bool
    ) -> str:
        """Ensure marketplace bundle wildcard permissions exist."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission ensure-wildcards",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        settings_path = claude_runtime._settings_path_for_scope(scope)
        settings = claude_runtime._load_settings(settings_path)
        if "error" in settings:
            return toon_error("permission ensure-wildcards", "invalid_settings", settings["error"])
        allow: list[str] = settings["permissions"]["allow"]

        # Discover bundles from the marketplace directory.
        mp_path = Path(marketplace_dir)
        bundles_scanned = 0
        wildcards_added = 0
        wildcards_already_present = 0
        proposed_additions: list[str] = []

        if mp_path.is_dir():
            try:
                bundle_dirs = sorted(mp_path.iterdir())
            except OSError:
                bundle_dirs = []
            for bundle_dir in bundle_dirs:
                if not bundle_dir.is_dir():
                    continue
                plugin_json = bundle_dir / ".claude-plugin" / "plugin.json"
                if not plugin_json.is_file():
                    continue
                bundles_scanned += 1
                bundle_name = bundle_dir.name
                skill_wildcard = f"Skill({bundle_name}:*)"
                cmd_wildcard = f"SlashCommand(/{bundle_name}:*)"
                for wildcard in (skill_wildcard, cmd_wildcard):
                    if wildcard in allow:
                        wildcards_already_present += 1
                    else:
                        if dry_run:
                            proposed_additions.append(wildcard)
                        else:
                            allow.append(wildcard)
                            wildcards_added += 1

        if not dry_run:
            settings["permissions"]["allow"] = allow
            claude_runtime._save_settings(settings_path, settings)

        result: dict[str, Any] = {
            "scope": scope,
            "marketplace_dir": marketplace_dir,
            "dry_run": dry_run,
            "bundles_scanned": bundles_scanned,
            "wildcards_added": 0 if dry_run else wildcards_added,
            "wildcards_already_present": wildcards_already_present,
            "target_file": str(settings_path),
        }
        if dry_run and proposed_additions:
            result["proposed_additions"] = proposed_additions

        return toon_success("permission ensure-wildcards", result)

    def permission_ensure_steps(
        self, marshal_path: str, scope: str, dry_run: bool
    ) -> str:
        """Ensure permissions exist for all project:{skill} steps."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission ensure-steps",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        mp = Path(marshal_path)
        if not mp.is_file():
            return toon_error(
                "permission ensure-steps",
                "marshal_not_found",
                f"{marshal_path} not found; run 'project initial-setup' first",
            )

        marshal_data, marshal_err = claude_runtime._load_marshal_config(marshal_path)
        if marshal_err:
            return toon_error("permission ensure-steps", "invalid_marshal", marshal_err)
        steps: list[dict[str, Any]] = claude_runtime._extract_project_steps(marshal_data)

        settings_path = claude_runtime._settings_path_for_scope(scope)
        settings = claude_runtime._load_settings(settings_path)
        if "error" in settings:
            return toon_error("permission ensure-steps", "invalid_settings", settings["error"])
        allow: list[str] = settings["permissions"]["allow"]

        steps_scanned = len(steps)
        permissions_added = 0
        permissions_already_present = 0
        proposed_additions: list[str] = []

        for step_entry in steps:
            skill_name = step_entry.get("skill", "")
            if not skill_name:
                continue
            skill_perm = f"Skill({skill_name})"
            if claude_runtime._skill_permission_covered(skill_name, allow):
                permissions_already_present += 1
            else:
                if dry_run:
                    proposed_additions.append(skill_perm)
                else:
                    allow.append(skill_perm)
                    permissions_added += 1

        if not dry_run:
            settings["permissions"]["allow"] = allow
            claude_runtime._save_settings(settings_path, settings)

        result: dict[str, Any] = {
            "marshal": marshal_path,
            "scope": scope,
            "dry_run": dry_run,
            "steps_scanned": steps_scanned,
            "permissions_added": 0 if dry_run else permissions_added,
            "permissions_already_present": permissions_already_present,
            "target_file": str(settings_path),
        }
        if dry_run and proposed_additions:
            result["proposed_additions"] = proposed_additions

        return toon_success("permission ensure-steps", result)

    def permission_web_analyze(self, scope: str) -> str:
        """Read-only analysis of WebFetch domain permissions."""
        valid_scopes = ("global", "project", "both")
        if scope not in valid_scopes:
            return toon_error(
                "permission web-analyze",
                "invalid_scope",
                f"--scope must be 'global', 'project', or 'both'; got {scope!r}",
            )

        _WF_RE = re.compile(r"^WebFetch\((.+)\)$")

        def _extract_webfetch_domains(allow: list[str]) -> list[str]:
            domains = []
            for perm in allow:
                m = _WF_RE.match(perm)
                if m:
                    domains.append(m.group(1))
            return domains

        global_allow: list[str] = []
        project_allow: list[str] = []

        if scope in ("global", "both"):
            gs = claude_runtime._load_settings(claude_runtime._claude_global_settings_path())
            global_allow = gs.get("permissions", {}).get("allow", [])

        if scope in ("project", "both"):
            ps = claude_runtime._load_settings(claude_runtime._claude_project_settings_path())
            project_allow = ps.get("permissions", {}).get("allow", [])

        global_domains = _extract_webfetch_domains(global_allow)
        project_domains = _extract_webfetch_domains(project_allow)

        # Categorize domains.
        _MAJOR_PATTERNS = re.compile(
            r"(github\.com|stackoverflow\.com|docs\.python\.org|docs\.oracle\.com|"
            r"developer\.mozilla\.org|npmjs\.com|pypi\.org|mvnrepository\.com|"
            r"api\.github\.com|raw\.githubusercontent\.com)"
        )
        _SUSPICIOUS_PATTERNS = re.compile(r"(\.xyz$|\.tk$|\.pw$|pastebin\.com|bit\.ly)")

        seen: set[str] = set()
        domain_rows: list[dict[str, Any]] = []

        for domain in global_domains:
            is_dup = domain in seen
            seen.add(domain)
            category = "major" if _MAJOR_PATTERNS.search(domain) else (
                "suspicious" if _SUSPICIOUS_PATTERNS.search(domain) else "unknown"
            )
            domain_rows.append(
                {"domain": domain, "category": category, "scope": "global", "duplicate": is_dup}
            )

        for domain in project_domains:
            is_dup = domain in seen
            seen.add(domain)
            category = "major" if _MAJOR_PATTERNS.search(domain) else (
                "suspicious" if _SUSPICIOUS_PATTERNS.search(domain) else "unknown"
            )
            domain_rows.append(
                {"domain": domain, "category": category, "scope": "project", "duplicate": is_dup}
            )

        return toon_success(
            "permission web-analyze",
            {
                "scope": scope,
                "total_domains": len(domain_rows),
                "domains": domain_rows,
            },
        )

    def permission_web_apply(
        self,
        scope: str,
        add: list[str],
        remove: list[str],
        dry_run: bool,
    ) -> str:
        """Add or remove WebFetch domain permissions."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission web-apply",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        settings_path = claude_runtime._settings_path_for_scope(scope)
        settings = claude_runtime._load_settings(settings_path)
        if "error" in settings:
            return toon_error("permission web-apply", "invalid_settings", settings["error"])
        allow: list[str] = settings["permissions"]["allow"]

        _WF_RE = re.compile(r"^WebFetch\((.+)\)$")

        # Build current domain set.
        current_domains = {m.group(1) for p in allow if (m := _WF_RE.match(p))}

        domains_added = 0
        domains_removed = 0

        if not dry_run:
            for domain in add:
                perm = f"WebFetch({domain})"
                if perm not in allow:
                    allow.append(perm)
                    domains_added += 1

            remove_set = {f"WebFetch({d})" for d in remove}
            original_len = len(allow)
            allow = [p for p in allow if p not in remove_set]
            domains_removed = original_len - len(allow)

            settings["permissions"]["allow"] = allow
            claude_runtime._save_settings(settings_path, settings)
        else:
            domains_added = sum(1 for d in add if d not in current_domains)
            domains_removed = 0
            for d in remove:
                for p in allow:
                    m = _WF_RE.match(p)
                    if m and m.group(1) == d:
                        domains_removed += 1
                        break

        return toon_success(
            "permission web-apply",
            {
                "scope": scope,
                "dry_run": dry_run,
                "domains_added": domains_added,
                "domains_removed": domains_removed,
                "target_file": str(settings_path),
            },
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def metrics_capture(
        self, plan_id: str, phase: str, total_tokens: int | None
    ) -> str:
        """Record token consumption for a planning phase on Claude."""
        if total_tokens is not None:
            # Manual override: store directly.
            claude_runtime._write_token_cursor(plan_id, phase, total_tokens)
            claude_runtime._manage_metrics_end_phase(plan_id, phase, total_tokens)
            return toon_success(
                "metrics capture",
                {
                    "plan_id": plan_id,
                    "phase": phase,
                    "tokens_captured": total_tokens,
                    "cursor_updated": True,
                    "source": "manual",
                },
            )

        # Automatic: read session_id from plan metadata, open JSONL, sum tokens.
        session_id = claude_runtime._manage_status_read_session(plan_id)
        if not session_id:
            return toon_noop(
                "metrics capture",
                "Session ID found but transcript/DB query returned no usage data for this phase",
                "Pass --total-tokens manually",
            )

        transcript = claude_runtime._find_transcript(session_id)
        if not transcript:
            return toon_noop(
                "metrics capture",
                "Session ID found but transcript/DB query returned no usage data for this phase",
                "Pass --total-tokens manually",
            )

        # Sum ALL tokens in transcript, subtract cursor (tokens from prior captures).
        transcript_total = claude_runtime._sum_tokens_from_jsonl(transcript)
        prior_cursor = claude_runtime._read_token_cursor(plan_id, phase)
        captured = max(0, transcript_total - prior_cursor)

        if captured == 0:
            return toon_noop(
                "metrics capture",
                "Session ID found but transcript/DB query returned no usage data for this phase",
                "Pass --total-tokens manually",
            )

        new_cursor = transcript_total
        claude_runtime._write_token_cursor(plan_id, phase, new_cursor)
        claude_runtime._manage_metrics_end_phase(plan_id, phase, captured)

        return toon_success(
            "metrics capture",
            {
                "plan_id": plan_id,
                "phase": phase,
                "session_id": session_id,
                "tokens_captured": captured,
                "cursor_updated": True,
            },
        )

    def metrics_normalized_tokens(
        self,
        session_id: str,
        windows: list[tuple[str, str, str]],
        output_file: str,
    ) -> str:
        """Walk the Claude transcript and write per-phase normalized tokens to JSON.

        Computes the per-phase ``{input, output, cache_read, cache_creation,
        total, billing_weighted_total, subagent_*}`` view from the session
        transcript, writes it to *output_file* as JSON, and returns a success TOON
        carrying the attribution counters. Returns a ``transcript_not_found`` no-op
        when no transcript can be located.
        """
        computed = claude_runtime._compute_normalized_tokens(session_id, windows)
        if computed is None:
            return toon_noop(
                "metrics normalized-tokens",
                "transcript_not_found",
                "pass --total-tokens manually to metrics capture",
            )

        per_phase, counters = computed
        try:
            out_path = Path(output_file)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(per_phase), encoding="utf-8")
        except OSError as exc:
            return toon_error(
                "metrics normalized-tokens",
                "io_error",
                f"Failed to write normalized-token result to {output_file}: {exc}",
            )

        return toon_success(
            "metrics normalized-tokens",
            {
                "session_id": session_id,
                "output_file": output_file,
                "phases_attributed": len(per_phase),
                **counters,
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
        """Return Claude Code Task: invocation parameters for a subagent."""
        # Locate the agent markdown file.
        agent_path = claude_runtime._find_agent_file(agent)
        if agent_path is None:
            return toon_error(
                "subagent dispatch",
                "prompt_not_found",
                f"Agent {agent!r} not found in marketplace tree",
            )

        # If a prompt_file override is provided, validate it exists.
        if prompt_file:
            pf = Path(prompt_file)
            if not pf.is_file():
                return toon_error(
                    "subagent dispatch",
                    "prompt_not_found",
                    f"prompt file not found: {prompt_file}",
                )
            try:
                prompt_body = pf.read_text(encoding="utf-8")
            except OSError:
                return toon_error(
                    "subagent dispatch",
                    "prompt_not_found",
                    f"prompt file not found: {prompt_file}",
                )
        else:
            try:
                prompt_body = agent_path.read_text(encoding="utf-8")
            except OSError:
                return toon_error(
                    "subagent dispatch",
                    "prompt_not_found",
                    f"Agent {agent!r} not found in marketplace tree",
                )

        # Parse frontmatter.
        fm = claude_runtime._parse_agent_frontmatter(agent_path)
        agent_description = fm.get("description", "")
        tools = fm.get("tools", [])

        # Check for unmapped tools.
        unmapped = [t for t in tools if t in claude_runtime._UNMAPPED_TOOLS]
        if unmapped:
            return toon_noop(
                "subagent dispatch",
                f"Agent {agent!r} requires unmapped tools: {', '.join(unmapped)}",
                "Remove unsupported tools from agent frontmatter or inline the agent logic",
            )

        # Merge context into prompt body.
        if context:
            context_block = "\n".join(f"{k}: {v}" for k, v in context.items())
            prompt_body = f"## Context\n\n{context_block}\n\n{prompt_body}"

        task_description = claude_runtime._short_description_from_agent(agent_description)

        return toon_success(
            "subagent dispatch",
            {
                "platform": "claude",
                "invocation": {
                    "tool": "Task",
                    "description": task_description,
                    "prompt": prompt_body,
                    "subagent_type": agent,
                },
            },
        )

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def _wait_for_outcome(
        self,
        observable: str,
        reference: str,
        outcome: str,
        bound_seconds: int,
        elapsed_seconds: float,
    ) -> str:
        """Build the normalised ``wait for`` success payload.

        No observable-shaped field crosses the boundary: the caller sees the
        kind token, its reference, the normalised outcome, whether that outcome
        is terminal, and the two bound figures.
        """
        return toon_success(
            "wait for",
            {
                "observable": observable,
                "reference": reference,
                "outcome": outcome,
                "terminal": outcome in claude_runtime.TERMINAL_OUTCOMES,
                "elapsed_seconds": int(elapsed_seconds),
                "bound_seconds": bound_seconds,
            },
        )

    def wait_for(self, observable: str, reference: str, bound_seconds: int) -> str:
        """Hold a bounded wait until a concrete observable reaches a terminal state.

        Realised as a bounded, re-issuable poll of the observable's own status
        surface. Claude Code exposes no Python API a runtime subprocess can
        register a background watch against, so there is no out-of-band channel
        to hold the wait on — the poll is the implementation, and it is a real
        one rather than a stub.

        Every non-success path is explicit: an unrecognised observable kind, a
        non-positive bound, an unreachable inspection channel, an unknown
        reference, and an out-of-vocabulary status each return a distinct
        ``error``. Bound exhaustion returns ``outcome: pending`` with
        ``terminal: false``. None of these is ever reported as a pass.
        """
        import time

        operation = "wait for"

        if observable not in claude_runtime.WAIT_OBSERVABLES:
            return toon_error(
                operation,
                "unsupported_observable",
                f"--observable {observable!r} is not an inspectable observable kind; "
                f"valid kinds: {', '.join(claude_runtime.WAIT_OBSERVABLES)}",
            )
        if bound_seconds < 1:
            return toon_error(
                operation,
                "invalid_bound",
                f"--bound-seconds must be a positive number of seconds; got {bound_seconds}",
            )

        channel_reason = claude_runtime.build_job_verify_channel()
        if channel_reason is not None:
            return toon_error(
                operation,
                "observable_unreachable",
                f"the {observable} inspection channel could not be reached "
                f"({channel_reason}); the wait is not held and no outcome is implied",
            )

        started = time.monotonic()
        while True:
            elapsed = time.monotonic() - started
            remaining = bound_seconds - elapsed
            if remaining <= 0:
                return self._wait_for_outcome(
                    observable,
                    reference,
                    claude_runtime.OUTCOME_PENDING,
                    bound_seconds,
                    elapsed,
                )

            poll_bound = max(1, int(min(remaining, claude_runtime._BUILD_JOB_POLL_BOUND_SECONDS)))
            payload = claude_runtime.build_job_poll(reference, poll_bound)
            wire_status = str(payload.get("status", ""))

            if wire_status == claude_runtime._BUILD_JOB_UNREACHABLE_STATUS:
                return toon_error(
                    operation,
                    "observable_unreachable",
                    f"the {observable} inspection channel became unreachable mid-wait "
                    f"({payload.get('reason', 'unreachable')}); no outcome is implied",
                )
            if wire_status == claude_runtime._BUILD_JOB_NOT_FOUND_STATUS:
                return toon_error(
                    operation,
                    "unknown_reference",
                    f"no {observable} is known for reference {reference!r}",
                )

            outcome = claude_runtime._BUILD_JOB_STATUS_TO_OUTCOME.get(wire_status)
            if outcome is not None:
                return self._wait_for_outcome(
                    observable,
                    reference,
                    outcome,
                    bound_seconds,
                    time.monotonic() - started,
                )
            if wire_status in claude_runtime._BUILD_JOB_NON_TERMINAL_STATUSES:
                continue

            return toon_error(
                operation,
                "unexpected_observable_status",
                f"the {observable} surface reported status {wire_status!r}, which is "
                "outside its documented vocabulary; refusing to infer an outcome",
            )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self, checks: str) -> str:
        """Verify Claude Code platform integration."""
        valid_checks = {"all", "permissions", "display", "mcp-diagnostics"}
        check_set_input: set[str] = {c.strip() for c in checks.split(",") if c.strip()}
        for c in check_set_input:
            if c not in valid_checks:
                return toon_error(
                    "health-check",
                    "invalid_check",
                    f"Unknown check {c!r}; valid checks are: all, permissions, display, mcp-diagnostics",
                )

        if "all" in check_set_input:
            checks_to_run = {"permissions", "display", "mcp-diagnostics", "hook"}
        else:
            checks_to_run = check_set_input | {"hook"}

        results: list[dict[str, Any]] = []
        all_healthy = True

        if "permissions" in checks_to_run:
            project_settings = claude_runtime._claude_project_settings_path()
            healthy = project_settings.is_file()
            detail = (
                f"settings.local.json present; allow array has "
                f"{len(claude_runtime._load_settings(project_settings).get('permissions', {}).get('allow', []))} entries"
                if healthy
                else "settings.local.json not found; run permission configure"
            )
            results.append({"check": "permissions", "healthy": healthy, "detail": detail})
            if not healthy:
                all_healthy = False

        if "display" in checks_to_run:
            # Read BOTH settings files — a hook entry can legitimately sit in
            # either (the install resolver prefers a pre-existing shared
            # settings.json; the enforcement install pins settings.local.json).
            # The sibling ``hook`` check already treats either file as
            # authoritative; the display check must too, or an install that
            # lands in the other file reports a false MISSING.
            display_main = claude_runtime._read_json(Path(".claude") / "settings.json") or {}
            display_local = claude_runtime._read_json(Path(".claude") / "settings.local.json") or {}
            merged = claude_runtime._merge_display_settings(display_main, display_local)
            lines, healthy = claude_runtime._diagnose_display_entries(merged)
            if healthy:
                detail = "; ".join(lines)
            else:
                detail = (
                    "; ".join(lines)
                    + "; run marshall-steward or project install-hook to install "
                    "any MISSING entry"
                )
            results.append({"check": "display", "healthy": healthy, "detail": detail})
            if not healthy:
                all_healthy = False

        if "mcp-diagnostics" in checks_to_run:
            # Attempt TCP connection to the JetBrains MCP server port.
            import socket

            mcp_host = "127.0.0.1"
            mcp_port = 64342
            try:
                with socket.create_connection((mcp_host, mcp_port), timeout=2):
                    healthy = True
                    detail = f"MCP server reachable at {mcp_host}:{mcp_port}"
            except (OSError, ConnectionRefusedError):
                healthy = False
                detail = f"MCP server not reachable at {mcp_host}:{mcp_port}; start JetBrains IDE with MCP plugin"
            results.append({"check": "mcp-diagnostics", "healthy": healthy, "detail": detail})
            if not healthy:
                all_healthy = False

        if "hook" in checks_to_run:
            def _hook_in_settings_file(path: Path) -> bool:
                """Return True when the SessionStart hook command is found in *path*."""
                if not path.is_file():
                    return False
                sd = claude_runtime._read_json(path) or {}
                hooks = sd.get("hooks")
                session_starts = hooks.get("SessionStart", []) if isinstance(hooks, dict) else []
                if not isinstance(session_starts, list):
                    session_starts = []
                for entry in session_starts:
                    if isinstance(entry, dict):
                        for h in entry.get("hooks", []):
                            if isinstance(h, dict) and h.get("command") == claude_runtime._HOOK_COMMAND:
                                return True
                return False

            settings_json = Path(".claude") / "settings.json"
            settings_local = Path(".claude") / "settings.local.json"
            in_settings_json = _hook_in_settings_file(settings_json)
            in_settings_local = _hook_in_settings_file(settings_local)
            healthy = in_settings_json or in_settings_local

            if in_settings_json and in_settings_local:
                detail = "SessionStart hook entry present in .claude/settings.json and .claude/settings.local.json"
            elif in_settings_json:
                detail = "SessionStart hook entry present in .claude/settings.json"
            elif in_settings_local:
                detail = "SessionStart hook entry present in .claude/settings.local.json"
            else:
                detail = (
                    "SessionStart hook entry missing from both .claude/settings.json and "
                    ".claude/settings.local.json; run marshall-steward to install"
                )

            results.append({"check": "hook", "healthy": healthy, "detail": detail})
            if not healthy:
                all_healthy = False

        return toon_success(
            "health-check",
            {
                "checks_run": [r["check"] for r in results],
                "all_healthy": all_healthy,
                "results": results,
            },
        )
