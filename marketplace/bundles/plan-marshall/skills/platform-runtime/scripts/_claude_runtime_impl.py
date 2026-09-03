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
(``_claude_global_settings_path``, ``_claude_local_settings_path``) plus every
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
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import _chat_signal_reducer
import claude_runtime
import session_binding
from manage_terminal_title import _compose_body, compose
from runtime_base import (
    PERMISSION_FIX_OPERATIONS,
    Runtime,
    marshal_shape_error,
    toon_error,
    toon_noop,
    toon_success,
)
from toon_parser import serialize_toon


def _persisted(settings_path: Any, settings: dict[str, Any]) -> bool:
    """Write *settings*, returning whether the bytes actually reached disk."""
    return bool(claude_runtime._save_settings(settings_path, settings))


def _write_failed(settings_path: Any) -> str:
    """The single `io_error` response for a `permission fix` write that failed.

    Every mutating branch of ``permission_fix`` reports an unwritable settings
    file the same way, because the caller's situation is the same in each: the
    change was computed, nothing reached disk, and a `success` here would be a
    report of work that did not happen. Discarding the save result is the
    fail-open this shares its shape with — the counters would still be non-zero.
    """
    return toon_error(
        "permission fix",
        "io_error",
        f"Failed to write settings to {settings_path}",
    )


def _chat_signal_transcript_not_found() -> str:
    """The single ``transcript_not_found`` no-op for ``chat extract-signal``.

    Discovery returning nothing and the transcript vanishing mid-read are the
    same honest answer (no transcript can be located); both emit this no-op so
    the retrospective's ``transcript_unavailable`` skip token stays consistent
    with the runtime contract.
    """
    return toon_noop(
        "chat extract-signal",
        "transcript_not_found",
        "run on a target that exposes a session transcript, or "
        "record the session with session capture first",
    )


class ClaudeRuntime(Runtime):
    """Claude Code implementation of all 25 platform-runtime operations."""

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
        settings_path = claude_runtime._claude_local_settings_path(str(pd))

        # Create directory structure.
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to create .plan/temp/: {exc}",
            )

        # Read-modify-write marshal.json: set runtime.target and project_dir on
        # whatever the project already carries, so an initialized project keeps
        # every other top-level block. An unconditional write here would destroy
        # the whole config and still return marshal_written: True — the reported
        # success is precisely what makes that loss invisible.
        #
        # The failure edges mirror the sibling OpenCodeRuntime implementation of
        # this same contract operation, and there are THREE of them, not two: a
        # MISSING file starts from {}; an unreadable or unparseable one is caught
        # by the except clause below; and a PARSEABLE file of the wrong SHAPE is
        # caught by the marshal_shape_error guard after it. The parse edge and the
        # shape edge are separate — `json.loads` succeeding proves the bytes were
        # valid JSON, not that they were an object — and naming only the first
        # read as "corrupt input is handled" is what left `[]` and
        # `{"runtime": null}` crashing this verb with an uncaught TypeError.
        # All three corrupt cases deliberately refuse rather than fall back to {}:
        # that fallback would overwrite exactly the config this read exists to
        # preserve. The mirror holds by construction because both runtimes call
        # the one shared guard rather than each carrying a copy.
        try:
            if marshal_path.exists():
                # Untyped until the shape guard below runs — see marshal_shape_error.
                marshal_data: Any = json.loads(marshal_path.read_text(encoding="utf-8"))
            else:
                marshal_data = {}
        except (OSError, json.JSONDecodeError) as exc:
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to read marshal.json at {marshal_path}: {exc}",
            )

        shape_error = marshal_shape_error("project initial-setup", marshal_path, marshal_data)
        if shape_error is not None:
            return shape_error

        if "runtime" not in marshal_data:
            marshal_data["runtime"] = {}
        marshal_data["runtime"]["target"] = "claude"
        marshal_data["project_dir"] = str(pd)

        if not claude_runtime._write_json(marshal_path, marshal_data):
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to write marshal.json at {marshal_path}",
            )

        # Install the full terminal-title hook wiring into .claude/settings.local.json.
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

    #: Conflict keys ``project_install_hook``'s ``overwrite`` argument accepts on
    #: this target. The ABC leaves the key set target-defined; this is Claude's.
    _OVERWRITE_STATUSLINE = "statusline"
    _OVERWRITE_ENV_DISABLE = "env-disable"
    _OVERWRITE_KEYS = (_OVERWRITE_STATUSLINE, _OVERWRITE_ENV_DISABLE)

    def project_install_hook(
        self,
        target: str,
        overwrite: Sequence[str] = (),
        enforcement: bool = False,
    ) -> str:
        """Install the full terminal-title hook wiring into the Claude settings file.

        This is where the ABC's target-opaque "wire this target's session/display
        integration" becomes concrete Claude Code wiring. Installs the
        SessionStart capture entry, nine render entries across six render-trigger
        hook events (SessionStart:matcher-less, SessionStart:clear,
        UserPromptSubmit, Notification, Stop, PreToolUse:AskUserQuestion,
        PreToolUse:Bash, PostToolUse:AskUserQuestion, PostToolUse:Bash), the
        ``statusLine`` command, and ``env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE =
        "1"``. Re-invocation CONVERGES an already-present entry on the current
        shape rather than always making no change: an entry carrying a stale hook
        ``timeout`` is rewritten, and that outcome is reported distinguishably —
        in ``migrated_events`` on the terminal-title path, on ``capture_status``
        for the SessionStart capture entry (which owns none of the nine render
        labels), and as ``enforcement_status: migrated`` on the enforcement path.
        ``already_present`` is False whenever anything was installed OR
        migrated — the capture entry included — so it never reads as "nothing
        changed" over a run that rewrote a stale value.

        When ``enforcement`` is True, installs ONLY the orthogonal PreToolUse
        enforcement entry (the ``claude_pretooluse_hook`` matcher-less entry) and
        does NOT install the terminal-title bundle. The two install modes are
        independent: ``project install-hook`` installs terminal-title;
        ``project install-hook --enforcement`` installs the enforcement entry;
        neither disturbs the other's entries.

        **Settings-file resolution is this implementation's own.** The ABC hands
        over a target identifier and nothing else, and the location is derived
        here:

        - ``"claude"`` — the canonical invocation, and the only shape the router
          help documents. It resolves to ``.claude/settings.local.json`` via
          ``_claude_local_settings_path()`` for BOTH the terminal-title install
          and the ``enforcement`` install: both payloads are machine-local
          operator wiring, and ``.claude/settings.local.json`` is the gitignored
          file that never enters version control. That is also the file the
          ``display`` health-check enforcement label and the install contract
          both reference.
        - An absolute path ending in ``.json`` — a Claude-INTERNAL test and
          recovery override that names a specific settings file. It is not part
          of the ABC contract and is not advertised by the router; other targets
          need not honour any such shape.

        Any other value (relative path, unknown identifier) is rejected with
        ``unknown_target`` rather than silently creating a stray file.

        Claude's ``overwrite`` conflict keys are ``_OVERWRITE_KEYS``, and they
        govern what happens when an existing ``statusLine`` or env value differs
        from ours:

        - key absent (default): preserve the foreign value and report
          ``statusLine_status`` / ``env_status: already_present_other`` so the
          marshall-steward menu can surface an AskUserQuestion.
        - key present: overwrite with our value and report the corresponding
          status as ``overwritten``.

        An unrecognised key is rejected with ``unknown_overwrite_key`` — a typo
        must not read as "do not overwrite", which is the silent-wrong-answer the
        ABC's reject-rather-than-ignore rule exists to prevent.
        """
        unknown_keys = [key for key in overwrite if key not in self._OVERWRITE_KEYS]
        if unknown_keys:
            return toon_error(
                "project install-hook",
                "unknown_overwrite_key",
                f"overwrite key(s) {', '.join(repr(k) for k in unknown_keys)} "
                f"not recognised on this target; valid keys are: "
                f"{', '.join(self._OVERWRITE_KEYS)}",
            )
        overwrite_statusline = self._OVERWRITE_STATUSLINE in overwrite
        overwrite_env_disable = self._OVERWRITE_ENV_DISABLE in overwrite

        if target == "claude":
            settings_path = claude_runtime._claude_local_settings_path()
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
            # ``migrated`` is a DISTINCT status member, never a flavour of
            # ``already_present``, so this equality still means "nothing
            # changed".
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
        migrated_events = install_result["migrated_events"]
        capture_status = install_result["capture_status"]
        # Top-level convenience signal: True iff nothing fresh was installed,
        # nothing was converged, AND no overwrite-other signal needs the
        # caller's attention. A run that rewrote a stale timeout DID change the
        # file, so ``migrated_events`` clears this flag exactly as
        # ``installed_events`` does — and ``capture_status`` is folded in on the
        # same ground, since the capture entry reaches this computation only
        # through its own field.
        all_already_present = (
            not installed_events
            and not migrated_events
            and capture_status == "already_present"
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
                "migrated_events": migrated_events,
                "capture_status": capture_status,
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
        under which installed marketplace bundles live on Claude. The path is
        composed in ``claude_runtime._claude_bundle_cache_root``, which shares
        its cache segments with the default-permission renderer, so those two
        cannot drift. Other sites compose the same segments themselves because
        they cannot reach this helper — the steward's bootstrap detector runs
        before the plugin is resolvable, the resolver ``generate_executor.py``
        embeds runs standalone, and ``marketplace_paths`` composes the fallback
        this op's own consumers use when the layout op is unreachable, which
        importing back here would make circular.
        """
        return toon_success(
            "layout bundle-cache-root",
            {"target": "claude", "roots": [str(claude_runtime._claude_bundle_cache_root())]},
        )

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    def session_capture(self, plan_id: str) -> str:
        """Read ``$CLAUDE_CODE_SESSION_ID`` and APPEND it via ``manage-status``.

        The identity is a list, so a session captured here never displaces the
        identity of a session that captured earlier against the same plan.

        Claude Code exports the session id into the shell environment from its
        SessionStart hook, so an unset variable means the hook is not wired up
        rather than that no session exists. That is reported as an ``error`` with
        code ``hook_not_configured`` — the ABC's "ought to be reachable but is
        not" case — never as a silent pass.
        """
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

    @staticmethod
    def _render_outcome(outcome: str, **fields: Any) -> str:
        """Name this render's terminal outcome on stderr, and return "".

        Every exit from :meth:`session_render_title` routes through here, so
        "the render produced no title" is always distinguishable from "the
        render produced the correct title" — and each distinct no-op reason is
        distinguishable from the others. Before this seam every path returned
        a bare ``""``, which made a silently-dead render indistinguishable
        from a healthy one at every layer.

        The named outcome goes to **stderr**, never stdout. The stdout
        contract is load-bearing: stdout carries exactly the bytes the host
        parser consumes and nothing else, so the reason is surfaced beside the
        payload, never glued to it. The return value stays ``""`` for the same
        reason — the wrapper ``main()`` skips ``print()`` on an empty result,
        so a non-empty return would append a TOON tail to the host's stdout.

        Writing the row is itself best-effort: a stderr failure must not break
        a render that otherwise succeeded.
        """
        try:
            sys.stderr.write(
                toon_success("session render-title", {"outcome": outcome, **fields}) + "\n"
            )
        except OSError:
            pass
        return ""

    def session_render_title(self, statusline: bool = False) -> str:
        """Resolve session → plan, read ``status.json``, compose, and emit.

        Both invocation modes share one stdout contract: stdout carries the
        exact bytes Claude Code's host parser consumes, and **nothing else**.
        Mixed payloads — JSON envelope plus a TOON success/noop row glued to
        it, or TOON noop instead of empty output — violate the contract and
        are dropped by the host parser (see ``hook-authoring-guide.md`` §
        "Hook output contract").

        **Every exit is a NAMED outcome** reported on stderr via
        :meth:`_render_outcome` (stdout is untouched by it). The eight
        outcomes are:

        ============================ =========================================
        ``outcome``                  Meaning
        ============================ =========================================
        ``no_session_id``            ``$CLAUDE_CODE_SESSION_ID`` unset — the
                                     hook is not installed or not firing.
        ``no_binding``               Neither a plan nor an orchestrator epic is
                                     bound to this session.
        ``no_title_state``           A binding resolved but its ``status.json``
                                     is absent or unreadable.
        ``session_teardown``         ``SessionStart:clear`` — a deliberate
                                     terminal no-op, not a failed render.
        ``unrenderable_state``       State read but ``compose`` returned None
                                     (empty/missing ``current_phase``).
        ``statusline_written``       SUCCESS on the statusLine channel.
        ``hook_envelope_written``    SUCCESS on the delivering hook channel.
        ``write_failed``             The stdout write raised — the system
                                     believed it painted and did NOT. The most
                                     consequential outcome of the eight, which
                                     is exactly why it is named rather than
                                     swallowed.
        ============================ =========================================

        Two of these (``no_session_id``, ``session_teardown``) are *deliberate*
        terminal no-ops rather than failures; they are named so the distinction
        is visible, not so they read as errors.

        **Deferred — the statusLine rendered-state substitution.** A no-op on
        the statusLine channel writes nothing, and what the host then shows
        (the previous footer, a blank line, or its own default) is an
        UNCONFIRMED host fact. Substituting a rendered state here would require
        assuming that behaviour, so this ships the observability half only: the
        statusLine no-op paths are named, and no placeholder title is invented.
        Re-open only against a confirmed host check.

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
        skips ``print()`` on empty results) cannot append a TOON tail — the
        named outcome above rides stderr precisely so this stays true.
        """

        # Step 1: Read $CLAUDE_CODE_SESSION_ID.
        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
        if not session_id:
            # A deliberate terminal no-op, not a failure: without a session id
            # there is nothing to resolve. Named so an uninstalled or
            # non-firing hook is visible instead of looking like a quiet
            # success.
            return self._render_outcome("no_session_id", statusline=statusline)

        # Step 2: Resolve session_id → plan_id via the session cache. A plan
        # binding wins; when absent, an ORCHESTRATOR epic binding is the fallback
        # (Step 3) so the orchestrator title reaches the hook channel, which is
        # the sole channel that delivers.
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
                return self._render_outcome("no_binding", session_id=session_id)
            state = claude_runtime._read_orchestrator_title_state(slug)
        if state is None:
            return self._render_outcome(
                "no_title_state", plan_id=plan_id or "", session_id=session_id
            )

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
            # A deliberate terminal no-op: this event RETIRES the session, so
            # writing no title is the correct behaviour, not a failed render.
            return self._render_outcome("session_teardown", plan_id=plan_id or "")

        # Build-busy hook assist — the MACHINE-OWNED bracket around a Bash build
        # window. Both halves live on render events, which is what makes the
        # bracket machine-driven rather than an LLM-turn obligation:
        #
        #   PreToolUse:Bash  → SET   build-busy (owner: build-hook)
        #   PostToolUse:Bash → CLEAR build-busy (owner-scoped to build-hook)
        #
        # The mutation is applied to the in-memory state dict BEFORE compose, so
        # THIS render paints the corrected title. That co-location is the whole
        # design: per Channel Delivery Contract ruling (b2) a state write owes a
        # delivered repaint, and the hook envelope is event-driven rather than
        # callable on demand — so the clear MUST ride a render event to deliver
        # at all. Do NOT relocate either half to a non-rendering call site (a
        # plain status write, a wrapper script, an agent turn): the state would
        # be correct and the tab would keep painting 🔨 until some unrelated
        # event happened to fire.
        #
        # A non-build command / missing tool_input is a silent no-op on both
        # halves (the existing PreToolUse:Bash → ⚙ busy mapping remains the
        # fallback). The persist is skipped for an orchestrator-bound render,
        # which has no plan status.json to write (plan_id is empty) — the
        # in-memory mutation still paints this render.
        if (
            not statusline
            and tool_name == "Bash"
            and hook_event_name in ("PreToolUse", "PostToolUse")
            and claude_runtime._command_is_build(tool_command)
        ):
            if hook_event_name == "PreToolUse":
                state["title_token"] = {
                    "owner": claude_runtime._TITLE_TOKEN_OWNER_BUILD_HOOK,
                    "state": "build-busy",
                    "set_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                if plan_id:
                    claude_runtime._manage_status_set_title_token(plan_id, "build-busy")
            else:
                # Owner-scope the in-memory pop exactly as the persisted clear
                # scopes itself (``_manage_status_clear_title_token`` passes
                # ``--owner build-hook``). Popping unconditionally would drop a
                # live ``merge-lock`` token from THIS render's composed title
                # while its status.json record survives — the two halves of one
                # clear disagreeing about ownership.
                existing = state.get("title_token")
                if (
                    isinstance(existing, dict)
                    and existing.get("owner") == claude_runtime._TITLE_TOKEN_OWNER_BUILD_HOOK
                ):
                    state.pop("title_token", None)
                if plan_id:
                    claude_runtime._manage_status_clear_title_token(plan_id)

        # Map the Claude hook event → the composer's target-neutral process
        # state, then compose. The composer no longer knows any Claude event
        # vocabulary; this mapping is the Claude-target half.
        process_state = claude_runtime._claude_event_to_process_state(hook_event_name, tool_name)
        composed = compose(state, process_state)
        if not composed:
            return self._render_outcome("unrenderable_state", plan_id=plan_id or "")

        # Step 5: Emit the title. Both modes write to stdout and return "".
        if statusline:
            # DEFERRED (see the docstring): a no-op on this channel writes
            # nothing, and the host's response to an empty statusLine output is
            # an unconfirmed fact. No rendered-state substitution and no
            # placeholder title is invented here — only the outcome is named.
            try:
                sys.stdout.write(composed)
                sys.stdout.flush()
            except OSError as exc:
                return self._render_outcome(
                    "write_failed", channel="statusline", plan_id=plan_id or "", detail=str(exc)
                )
            return self._render_outcome("statusline_written", plan_id=plan_id or "")

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
        except OSError as exc:
            # The MOST consequential of the eight outcomes: this is the
            # delivering channel, so a swallowed failure here is the one case
            # where the system believes it painted and did not. It must not
            # return the same value a successful render returns — and the
            # terminal-delivered mark below MUST NOT fire, because nothing was
            # delivered.
            return self._render_outcome(
                "write_failed", channel="hook_envelope", plan_id=plan_id or "", detail=str(exc)
            )

        # The terminal title has now been DELIVERED on the hook envelope — the
        # one channel that reaches the tab. Discharging that obligation is what
        # releases an archived plan's session slot to the GC: until this mark
        # lands, session_binding exempts the slot so the pending render still has
        # a plan to resolve. Best-effort and a no-op for a non-archived plan.
        if plan_id and state.get("current_phase") in session_binding._TERMINAL_PHASES:
            claude_runtime._mark_terminal_delivered(plan_id)
        return self._render_outcome("hook_envelope_written", plan_id=plan_id or "")

    def session_push_title_token(
        self,
        plan_id: str,
        icon: str | None = None,
        store: str = "plans",
        slug: str | None = None,
    ) -> str:
        """Bind the session and settle *plan_id*'s title state for the next render.

        This seam **binds and persists — it does not repaint.** The hook-mode
        ``terminalSequence`` envelope that Claude Code writes on every
        render-trigger event (see :meth:`session_render_title`) is the sole
        delivery channel, and it is event-driven rather than callable on demand.
        A writer therefore reaches the terminal by settling the state the *next*
        render will read, and delivery is deferred to that event.

        Reads the title state from ``status.json`` via
        :func:`_read_title_state` and composes it via
        :func:`manage_terminal_title.compose` (with *icon* as the push-mode icon
        override and ``process_state=None``) to establish that the state is
        renderable. Nothing is written to any terminal device.

        With ``store="orchestrator"`` the state read routes through
        :func:`claude_runtime._read_orchestrator_title_state` instead — the
        epic's ``status.json`` resolved via ``get_store_dir('orchestrator',
        slug)`` — and the composer renders the ``Orchestrator-{SlugName}``
        body. The orchestrator branch additionally establishes the session→epic
        binding via :func:`session_binding.bind_orchestrator` (best-effort, from
        ``$CLAUDE_CODE_SESSION_ID``), which is what lets the hook-driven channel
        (:meth:`session_render_title`) resolve the epic and deliver its title on
        subsequent renders. That binding side effect is the load-bearing reason
        this seam exists. The orchestrator branch also reports a configured-OFF
        terminal-title feature as ``reason: feature_inactive``.

        ``icon`` is optional. When supplied it overrides the event-resolved icon
        for non-terminal phases (e.g. the lock ⏳/🔒 or build 🔨 glyph). When
        omitted (``None``) the composer applies its default active icon — the
        shape the ``manage-status`` phase-write drive seam fires on every
        persisted title-state change.

        Best-effort. Never raises, and never changes the caller's status or exit
        code. Both "nothing to settle" outcomes return ``status: success`` with a
        ``reason`` — state absent / unrenderable (``reason: no_title_state``) and
        feature configured off (``reason: feature_inactive``). Claude HAS a render
        channel, so it never declines this operation; it did its whole job in both
        cases and reports which one applied.

        Returns a success TOON carrying the store entry fields, plus ``reason``
        when the seam had nothing to settle. It carries no ``pushed`` and no
        ``delivery`` field: both described a repaint this seam does not perform,
        and delivery is the next render event's outcome, not this seam's.
        """
        if store == "orchestrator":
            # Establish the session→epic binding as a best-effort side effect so
            # the hook-driven delivery channel (session render-title) resolves the
            # epic and delivers its title on the next render event.
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
                {**entry_fields, "reason": "no_title_state"},
            )

        composed = compose(state, None, icon_override=icon)
        if not composed:
            return toon_success(
                "session push-title-token",
                {**entry_fields, "reason": "no_title_state"},
            )

        # The epic binding above is established regardless; this gate only reports
        # that a configured-OFF feature has no channel to deliver on.
        if store == "orchestrator" and not claude_runtime._terminal_title_active():
            return toon_success(
                "session push-title-token",
                {**entry_fields, "reason": "feature_inactive"},
            )

        return toon_success("session push-title-token", dict(entry_fields))

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
        """Release this session's plan binding at end of session.

        Releasing the binding is the whole of the teardown. The verb writes NO
        title reset escape: the only channel such a reset could have used
        (``/dev/tty``) is deleted, and nothing may be reset on a channel that
        cannot deliver.

        This is the SOLE binding-release point, reached only from the
        ``SessionStart:clear`` render trigger. ``manage-status``'s archive path
        deliberately does NOT call it — releasing at archive time would destroy
        the delivery route for the terminal state the archive just persisted,
        which the next render event still has to paint.

        Order is load-bearing: the ACTIVATION signal is read FIRST. When the
        terminal-title feature is not wired up (no render-hook entry on any
        render-trigger event and no ``statusLine`` command — see
        :func:`claude_runtime._terminal_title_active`), the op returns
        ``active: false`` / ``reason: feature_inactive`` having mutated NO
        binding and raised nothing. A project that never opted into terminal
        titles is never touched.

        When active: resolve the session id from ``$CLAUDE_CODE_SESSION_ID`` and
        drop the session's own slot via :func:`session_binding.unbind`.
        Best-effort throughout: never raises.
        """
        if not claude_runtime._terminal_title_active():
            return toon_success(
                "session teardown",
                {
                    "active": False,
                    "unbound": False,
                    "reason": "feature_inactive",
                },
            )

        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
        unbound = session_binding.unbind(session_id) if session_id else False

        return toon_success(
            "session teardown",
            {"active": True, "unbound": unbound},
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

    def permission_configure(self, scope: str, grants: list[dict[str, Any]]) -> str:
        """Write a semantic permission-intent list to the Claude Code settings."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission configure",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        rendered: list[str] = []
        for intent in grants:
            rules, err = claude_runtime._render_permission_intent(intent)
            if err or rules is None:
                return toon_error(
                    "permission configure",
                    "invalid_intent",
                    f"{err}; got {intent!r}",
                )
            rendered.extend(rules)

        settings_path = claude_runtime._settings_path_for_scope(scope)
        settings = claude_runtime._load_settings(settings_path)
        if "error" in settings:
            return toon_error("permission configure", "invalid_settings", settings["error"])
        settings["permissions"]["allow"] = rendered

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
                "permissions_written": len(rendered),
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
        # The READ selector: this operation audits, so it must inspect the file
        # whose entries actually take effect. The write selector prefers the
        # shared file, which would make the audit report on rules an operator's
        # own settings.local.json overrides.
        project_path = claude_runtime._claude_project_settings_read_path()
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
        arguments: list[Any],
        dry_run: bool,
    ) -> str:
        """Apply hygienic fixes to permission configuration."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission fix",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        valid_ops = PERMISSION_FIX_OPERATIONS
        if operation not in valid_ops:
            return toon_error(
                "permission fix",
                "invalid_operation",
                f"--operation must be one of {valid_ops}; got {operation!r}",
            )
        if operation == "protect-path":
            if not arguments:
                return toon_error(
                    "permission fix",
                    "invalid_operation",
                    "--permissions must name at least one directory path for 'protect-path'",
                )
            # Validate BEFORE loading settings, so an unprotectable path cannot
            # reach the renderer. A deny rule is a security control: a path this
            # cannot render faithfully is refused, never rendered approximately.
            for candidate in arguments:
                if not isinstance(candidate, str):
                    return toon_error(
                        "permission fix",
                        "invalid_operation",
                        f"protect-path arguments must be directory paths; got {candidate!r}",
                    )
                refusal = claude_runtime._reject_unprotectable_path(candidate)
                if refusal is not None:
                    return toon_error(
                        "permission fix",
                        "invalid_operation",
                        f"cannot protect {candidate!r}: {refusal}",
                    )
        elif operation in ("add", "remove", "ensure"):
            # Render the semantic intents once, up front, so a malformed intent
            # fails the whole operation before any settings are touched.
            for intent in arguments:
                rules, err = claude_runtime._render_permission_intent(intent)
                if err:
                    return toon_error(
                        "permission fix",
                        "invalid_intent",
                        f"{err}; got {intent!r}",
                    )

        settings_path = claude_runtime._settings_path_for_scope(scope)
        settings = claude_runtime._load_settings(settings_path)
        if "error" in settings:
            return toon_error("permission fix", "invalid_settings", settings["error"])
        allow: list[str] = settings["permissions"]["allow"]

        changes_applied = 0
        proposed_additions: list[dict[str, Any]] = []
        proposed_count = 0
        rules_rendered = 0

        if operation == "normalize":
            original = list(allow)
            # Remove duplicates and sort.
            deduped = list(dict.fromkeys(allow))
            sorted_allow = sorted(deduped)
            # Add defaults if missing. The plan-directory and bundle-cache rules
            # come from the single renderer in the entry module; the executor
            # permission is normalize's own addition.
            defaults = [
                *(rule for _rule_id, rule in claude_runtime._default_permission_rules()),
                "Bash(python3 .plan/execute-script.py *)",
            ]
            for d in defaults:
                if d not in sorted_allow:
                    sorted_allow.append(d)
            # Ensuring the defaults is two-sided, and this op is the second
            # surface that ensures them: a rule the renderer has retired is
            # pruned here for the same reason `ensure_default_permissions`
            # prunes it. Reading the same renderer but not the same retired set
            # would leave the two surfaces disagreeing on what "the defaults"
            # means, and an operator whose flow is `normalize` would keep the
            # startup warning the retirement exists to clear.
            retired = {rule for _rule_id, rule in claude_runtime._RETIRED_DEFAULT_RULES}
            pruned = len(retired.intersection(deduped))
            sorted_allow = sorted(p for p in sorted_allow if p not in retired)
            changes_applied = (
                len([p for p in sorted_allow if p not in original])
                + (len(original) - len(deduped))
                + pruned
            )
            if not dry_run:
                settings["permissions"]["allow"] = sorted_allow
                if not _persisted(settings_path, settings):
                    return _write_failed(settings_path)

        elif operation == "add":
            planned: set[str] = set()
            for intent in arguments:
                rules, _err = claude_runtime._render_permission_intent(intent)
                if rules is None:
                    continue
                new_rules = [r for r in rules if r not in allow and r not in planned]
                if not new_rules:
                    continue
                if not dry_run:
                    allow.extend(new_rules)
                    changes_applied += 1
                else:
                    planned.update(new_rules)
                    proposed_additions.append(intent)
            if not dry_run:
                settings["permissions"]["allow"] = allow
                if not _persisted(settings_path, settings):
                    return _write_failed(settings_path)

        elif operation == "remove":
            original_len = len(allow)
            remove_rules: set[str] = set()
            for intent in arguments:
                rules, _err = claude_runtime._render_permission_intent(intent)
                if rules is None:
                    continue
                remove_rules.update(rules)
            allow = [p for p in allow if p not in remove_rules]
            changes_applied = original_len - len(allow)
            if not dry_run:
                settings["permissions"]["allow"] = allow
                if not _persisted(settings_path, settings):
                    return _write_failed(settings_path)

        elif operation == "ensure":
            planned = set()
            for intent in arguments:
                rules, _err = claude_runtime._render_permission_intent(intent)
                if rules is None:
                    continue
                new_rules = [r for r in rules if r not in allow and r not in planned]
                if not new_rules:
                    continue
                if not dry_run:
                    allow.extend(new_rules)
                    changes_applied += 1
                else:
                    planned.update(new_rules)
                    proposed_additions.append(intent)
            if not dry_run:
                settings["permissions"]["allow"] = allow
                if not _persisted(settings_path, settings):
                    return _write_failed(settings_path)

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
                if not _persisted(settings_path, settings):
                    return _write_failed(settings_path)

        elif operation == "protect-path":
            # Goal-based: the caller names DIRECTORIES to protect; the deny-rule
            # grammar is rendered here and never crosses back. This is the one
            # fix operation that writes the deny list rather than the allow list.
            deny_value = settings["permissions"]["deny"]
            if not isinstance(deny_value, list):
                # Fail closed rather than raising out of the operation. This
                # is the only branch that indexes ``["deny"]``, so it is the
                # only one that can meet a `deny` of the wrong type, and the
                # only place the type can be checked.
                return toon_error(
                    "permission fix",
                    "invalid_settings",
                    f"permissions.deny must be a list; found {type(deny_value).__name__}",
                )
            deny: list[str] = deny_value
            # De-duplicate ACROSS the named paths, not only within each: two
            # paths can render the same rule (the same directory named twice,
            # or two spellings of one directory), and a `rules_total` that
            # counted them separately would report rules the caller will not
            # get — the count the per-path renderer already refuses to inflate.
            rendered: list[str] = []
            for protected_dir in arguments:
                rendered.extend(claude_runtime._protect_path_deny_rules(protected_dir))
            rendered = list(dict.fromkeys(rendered))
            rules_rendered = len(rendered)
            for rule in rendered:
                if rule in deny:
                    continue
                if dry_run:
                    proposed_count += 1
                else:
                    deny.append(rule)
                    changes_applied += 1
            # Write only when a rule was actually added: this operation is meant
            # to be re-run for its idempotence, and re-serializing an operator's
            # settings file on a call that changed nothing is a modification
            # they can see for no effect. The sibling branches save
            # unconditionally; `contract.md` records the asymmetry.
            if not dry_run and changes_applied:
                settings["permissions"]["deny"] = deny
                if not _persisted(settings_path, settings):
                    # A security control that reports success when the write
                    # failed tells an operator their credentials are guarded by
                    # rules that reached nothing. Fail loudly instead.
                    return _write_failed(settings_path)

        result: dict[str, Any] = {
            "scope": scope,
            "fix_operation": operation,
            "dry_run": dry_run,
            "target_file": str(settings_path),
            "changes_applied": 0 if dry_run else changes_applied,
        }
        if operation == "protect-path":
            # Counts only — a rendered deny rule must not reach the caller.
            # Named, not protected: three spellings of one directory are three
            # names and one protection. `rules_total` is the honest measure of
            # what was written.
            result["paths_named"] = len(arguments)
            result["rules_total"] = rules_rendered
            if dry_run:
                result["proposed_count"] = proposed_count
        elif dry_run and proposed_additions:
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
        proposed_additions: list[dict[str, Any]] = []

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
                    elif dry_run:
                        # Report the semantic intent once, not the two rendered
                        # wildcard rules: the operator states the bundle, the
                        # runtime owns the Skill/SlashCommand grammar.
                        if proposed_additions and proposed_additions[-1] == {
                            "kind": "bundle",
                            "name": bundle_name,
                        }:
                            continue
                        proposed_additions.append({"kind": "bundle", "name": bundle_name})
                    else:
                        allow.append(wildcard)
                        wildcards_added += 1

        if not dry_run:
            settings["permissions"]["allow"] = allow
            if not _persisted(settings_path, settings):
                return _write_failed(settings_path)

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
        proposed_additions: list[dict[str, Any]] = []

        planned_skills: set[str] = set()
        for step_entry in steps:
            skill_name = step_entry.get("skill", "")
            if not skill_name:
                continue
            if (
                claude_runtime._skill_permission_covered(skill_name, allow)
                or skill_name in planned_skills
            ):
                permissions_already_present += 1
            else:
                if dry_run:
                    planned_skills.add(skill_name)
                    proposed_additions.append({"kind": "skill", "name": skill_name})
                else:
                    allow.append(f"Skill({skill_name})")
                    permissions_added += 1

        if not dry_run:
            settings["permissions"]["allow"] = allow
            if not _persisted(settings_path, settings):
                return _write_failed(settings_path)

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
            # Read-side, so the read selector — same reason as permission_analyze.
            ps = claude_runtime._load_settings(
                claude_runtime._claude_project_settings_read_path()
            )
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
            if not _persisted(settings_path, settings):
                return _write_failed(settings_path)
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
    # Permission settings I/O — used by permission_common / permission_doctor
    # ------------------------------------------------------------------

    def permission_settings_path(
        self, scope: str, write: bool = False, project_dir: str | None = None
    ) -> str:
        """Resolve the Claude settings file path for a permission scope."""
        if scope == "global":
            return str(claude_runtime._claude_global_settings_path())
        if scope == "project":
            if write:
                return str(claude_runtime._claude_project_settings_path(project_dir))
            return str(claude_runtime._claude_project_settings_read_path(project_dir))
        raise ValueError(f"Unsupported scope: {scope!r}")

    def permission_load_settings(self, path: str) -> dict[str, Any]:
        """Load settings from a Claude JSON file."""
        return claude_runtime._load_settings(Path(path))

    def permission_save_settings(self, path: str, settings: dict[str, Any]) -> bool:
        """Persist settings to a Claude JSON file."""
        return claude_runtime._save_settings(Path(path), settings)

    def permission_ensure_defaults(
        self,
        settings: dict[str, Any],
        settings_path: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Ensure the default permission set and prune retired rules."""
        return claude_runtime.ensure_default_permissions(
            settings, Path(settings_path), dry_run
        )

    def permission_check_skill_coverage(
        self, skill: str, allow_list: list[str]
    ) -> str | None:
        """Check if a skill is covered by an allow rule."""
        return claude_runtime._skill_permission_covered(skill, allow_list)

    def permission_load_marshal_config(self, marshal_path: str) -> dict[str, Any]:
        """Load and parse marshal.json, returning a dict with an ``error`` key."""
        config, err = claude_runtime._load_marshal_config(marshal_path)
        if err is not None:
            return {"error": err}
        return config

    def permission_extract_project_steps(
        self, marshal_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Enumerate project:{skill} step references."""
        return claude_runtime._extract_project_steps(marshal_config)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def metrics_capture(
        self, plan_id: str, phase: str, total_tokens: int | None
    ) -> str:
        """Record token consumption for a planning phase on Claude.

        Reads the Claude session transcript and sums the tokens recorded since
        this phase's last capture. An explicit *total_tokens* bypasses the
        transcript scan and is stored as given.
        """
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
        total, billing_weighted_total, subagent_*}`` view plus the
        exploration-share counters
        ``{exploration,work,execute,orchestration,unclassified}_tool_calls`` and
        the matching ``_result_bytes`` from the session transcript, writes it to
        *output_file* as JSON, and returns a success TOON carrying the attribution
        counters — including ``unclassified_tool_calls``, the run-level count of
        tool names outside the classifier's population-derived domain.

        The transcripts this target walks are
        ``~/.claude/projects/.../{session_id}.jsonl`` and the session's
        ``{session_id}/subagents/agent-*.jsonl`` files; the records it recognises
        are ``message.usage`` four-field entries, ``<usage>`` return tags, and
        ``tool_use`` / ``tool_result`` content items. Its agent-instructions file
        — the ABC's target-defined doc-residency member — is ``CLAUDE.md``, which
        :func:`claude_runtime._classify_exploration_target` matches by basename.

        Because this target walks a real transcript, every emitted phase bucket
        carries the full counter key set, so a zero is a MEASURED zero. Counters
        are ABSENT only when no bucket is emitted at all. Returns a
        ``transcript_not_found`` no-op when no transcript can be located.
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

    def chat_extract_signal(self, session_id: str) -> str:
        """Reduce the Claude session transcript to its signal-bearing turns.

        Resolves *session_id* to the session JSONL exactly the way
        ``metrics normalized-tokens`` does (:func:`claude_runtime._find_transcript`),
        then reduces it via :func:`_chat_signal_reducer.reduce_chat_signal`,
        which owns the transcript-format knowledge. Returns the operation's
        seven-field normalized record on success; returns a
        ``transcript_not_found`` no-op when no transcript can be located, and
        a structured error when the resolved transcript could not be read.

        Read-budget policy is deliberately NOT applied here: the record's
        ``reduced_bytes`` is the raw reduced size for the caller to compare
        against its own budget.
        """
        transcript_path = claude_runtime._find_transcript(session_id)
        if transcript_path is None:
            return _chat_signal_transcript_not_found()
        try:
            record = _chat_signal_reducer.reduce_chat_signal(transcript_path)
        except FileNotFoundError:
            # The transcript vanished between discovery and read — it can no
            # longer be located, which is the same honest answer as discovery
            # returning nothing: a transcript_not_found no-op, NOT the io_error
            # OSError would otherwise swallow.
            return _chat_signal_transcript_not_found()
        except OSError as exc:
            return toon_error(
                "chat extract-signal",
                "io_error",
                f"Failed to read session transcript {transcript_path}: {exc}",
            )
        return toon_success(
            "chat extract-signal",
            {"session_id": session_id, "transcript_path": str(transcript_path), **record},
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
        """Return Claude Code ``Task:`` invocation parameters for a subagent.

        Uses ``Task`` as the Claude native tool name, and echoes the REQUESTED
        *agent* back as ``subagent_type`` so the caller's selection reaches the
        invocation.
        """
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
            # Read-side, so the read selector — uniform with the other audits.
            # The two selectors agree on this particular boolean (either answers
            # "some project settings file exists"), but a reader should not have
            # to re-derive that to know the rule has no exceptions.
            project_settings = claude_runtime._claude_project_settings_read_path()
            healthy = project_settings.is_file()
            # Name the file actually checked. This reported "settings.local.json"
            # unconditionally, so on a project carrying only the shared file the
            # detail named a file the check had not looked at.
            detail = (
                f"{project_settings.name} present; allow array has "
                f"{len(claude_runtime._load_settings(project_settings).get('permissions', {}).get('allow', []))} entries"
                if healthy
                else f"{project_settings.name} not found; run permission configure"
            )
            results.append({"check": "permissions", "healthy": healthy, "detail": detail})
            if not healthy:
                all_healthy = False

        if "display" in checks_to_run:
            # Read BOTH settings files — the install resolver pins
            # settings.local.json for the terminal-title and the enforcement
            # install alike, but a project set up before that pin can still
            # carry an entry in the shared settings.json. The sibling ``hook``
            # check already treats either file as authoritative; the display
            # check must too, or such an install reports a false MISSING.
            display_main = claude_runtime._read_json(Path(".claude") / "settings.json") or {}
            display_local = claude_runtime._read_json(Path(".claude") / "settings.local.json") or {}
            # Detect the dual-homed install BEFORE the merge: the merge
            # concatenates the per-event hook lists and the presence probes
            # return on the first match, so an entry installed in both files is
            # indistinguishable from a single-homed one afterwards. Report-only
            # and non-fatal — a divergent label is installed, so it does not
            # touch ``healthy`` and never trips the fail-closed gate below.
            divergent = claude_runtime._dual_homed_labels(display_main, display_local)
            merged = claude_runtime._merge_display_settings(display_main, display_local)
            lines, healthy = claude_runtime._diagnose_display_entries(merged, divergent)
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
                # Dual-homed: the same named, non-fatal state the ``display``
                # check reports per label. ``healthy`` stays True above — the
                # entry IS installed; the divergence is report-only.
                detail = (
                    f"SessionStart hook entry: {claude_runtime._DIVERGENCE_TOKEN} — "
                    "present in .claude/settings.json and .claude/settings.local.json"
                )
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

        # FAIL-CLOSED on the DISPLAY check specifically. An unhealthy display
        # verdict means the installed render-hook set diverges from the
        # expected set, which is a real, actionable misconfiguration — and
        # reporting it as ``status: success`` with ``all_healthy: false`` made
        # it invisible to every caller that branches on status, which is how a
        # divergence could sit unnoticed indefinitely.
        #
        # The fail is deliberately NOT generalised to every check: an
        # unreachable ``mcp-diagnostics`` port means "no JetBrains IDE is
        # running", an ordinary environmental condition rather than a
        # misconfiguration, so failing on it would train callers to ignore the
        # verb's status. ``all_healthy`` continues to report the aggregate for
        # those checks.
        fields: dict[str, Any] = {
            "checks_run": [r["check"] for r in results],
            "all_healthy": all_healthy,
            "results": results,
        }

        display_result = next((r for r in results if r["check"] == "display"), None)
        if display_result is not None and not display_result["healthy"]:
            # The failure carries the FULL per-check payload, not just an error
            # code: a caller that fails closed should still get the same report
            # it would have got on success, so failing costs it no diagnostic
            # information and there is no incentive to ignore the status.
            return serialize_toon(
                {
                    "status": "error",
                    "error": "display_unhealthy",
                    "message": f"display check failed — {display_result['detail']}",
                    "operation": "health-check",
                    **fields,
                }
            )

        return toon_success("health-check", fields)
