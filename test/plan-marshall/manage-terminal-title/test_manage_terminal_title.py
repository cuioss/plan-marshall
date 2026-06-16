#!/usr/bin/env python3
"""Tests for manage_terminal_title.py — the pure title-composition composer.

``manage_terminal_title`` is a leaf library: ``compose(state_dict, event)`` is a
pure function returning the ``'{icon} {glyph} {body}'`` terminal-title string (or
``None`` for a true no-op), performing NO filesystem or network I/O. These tests
exercise every composition code path documented in the module:

- :func:`compose` returns ``'{icon} {glyph} {body}'`` for each token state, and
  ``'{icon} {body}'`` (no glyph) when no ``title_token`` is set.
- The :data:`TITLE_TOKEN_GLYPHS` glyph map (⏳ / 🔒) is correct.
- :func:`resolve_icon` maps each hook event to the canonical process icon
  (➤ active / ? waiting / ✓ done / ⚙ busy) including the defensive default.
- The terminal-state override: ``current_phase`` in ``complete`` / ``archived``
  forces ✅ regardless of event, ➤/? never appear, and the Completed body
  renders.
- Terminal-phase glyph suppression: a finished plan holds no live lock state,
  so the ``title_token`` glyph (⏳ / 🔒) is suppressed for terminal phases
  across both token states, while active-phase glyphs are unaffected.
- Body format ``pm:{phase}[:{short}]`` for active phases.
- Purity: no I/O, deterministic — repeated calls with the same inputs return
  identical results.

The module is loaded in-process via ``load_script_module`` (it has no CLI to
subprocess) so ``compose`` / ``resolve_icon`` / the module constants are called
directly.
"""

from conftest import load_script_module

_mtt = load_script_module(
    "plan-marshall", "manage-terminal-title", "manage_terminal_title.py"
)

compose = _mtt.compose
resolve_icon = _mtt.resolve_icon
TITLE_TOKEN_GLYPHS = _mtt.TITLE_TOKEN_GLYPHS

# Icon literals mirrored from the module under test (kept local so a silent
# change to the module's palette is caught as a test failure rather than
# masked by importing the same constant).
ICON_ACTIVE = "➤"  # ➤
ICON_WAITING = "?"
ICON_DONE = "✓"  # ✓
ICON_TERMINAL = "✅"  # ✅
ICON_BUSY = "⚙"  # ⚙

GLYPH_LOCK_WAITING = "⏳"  # ⏳
GLYPH_LOCK_OWNED = "\U0001f512"  # 🔒


# =============================================================================
# TITLE_TOKEN_GLYPHS map correctness
# =============================================================================


class TestTitleTokenGlyphMap:
    """The two lock-state → glyph mappings are exact."""

    def test_lock_waiting_glyph(self):
        assert TITLE_TOKEN_GLYPHS["lock-waiting"] == GLYPH_LOCK_WAITING

    def test_lock_owned_glyph(self):
        assert TITLE_TOKEN_GLYPHS["lock-owned"] == GLYPH_LOCK_OWNED

    def test_exactly_two_states(self):
        # The vocabulary is closed at two states — guard against silent
        # additions/removals.
        assert set(TITLE_TOKEN_GLYPHS) == {
            "lock-waiting",
            "lock-owned",
        }


# =============================================================================
# resolve_icon — event → process icon
# =============================================================================


class TestResolveIconActive:
    """Events that resolve to the ➤ active icon."""

    def test_user_prompt_submit(self):
        assert resolve_icon("UserPromptSubmit") == ICON_ACTIVE

    def test_session_start(self):
        assert resolve_icon("SessionStart") == ICON_ACTIVE

    def test_post_tool_use_any_tool(self):
        assert resolve_icon("PostToolUse", "Bash") == ICON_ACTIVE

    def test_post_tool_use_ask_user_question(self):
        # PostToolUse with AskUserQuestion is active (the question was answered).
        assert resolve_icon("PostToolUse", "AskUserQuestion") == ICON_ACTIVE

    def test_unknown_event_defaults_active(self):
        assert resolve_icon("SomethingUnmapped") == ICON_ACTIVE

    def test_none_event_defaults_active(self):
        # Defensive default — never raises on a missing event.
        assert resolve_icon(None) == ICON_ACTIVE


class TestResolveIconWaiting:
    """Events that resolve to the ? waiting icon."""

    def test_notification(self):
        assert resolve_icon("Notification") == ICON_WAITING

    def test_pre_tool_use_ask_user_question(self):
        assert resolve_icon("PreToolUse", "AskUserQuestion") == ICON_WAITING

    def test_pre_tool_use_other_tool_is_active(self):
        # PreToolUse with a genuinely-other tool (neither AskUserQuestion nor
        # Bash) falls through to active.
        assert resolve_icon("PreToolUse", "Read") == ICON_ACTIVE
        assert resolve_icon("PreToolUse", "Write") == ICON_ACTIVE

    def test_pre_tool_use_no_tool_is_active(self):
        assert resolve_icon("PreToolUse") == ICON_ACTIVE


class TestResolveIconDone:
    """The Stop event resolves to the ✓ done icon."""

    def test_stop(self):
        assert resolve_icon("Stop") == ICON_DONE

    def test_done_icon_distinct_from_terminal(self):
        # The per-turn ✓ is deliberately distinct from the terminal ✅.
        assert ICON_DONE != ICON_TERMINAL


class TestResolveIconBusy:
    """PreToolUse + Bash resolves to the ⚙ busy icon (long-running tool)."""

    def test_pre_tool_use_bash_is_busy(self):
        assert resolve_icon("PreToolUse", "Bash") == ICON_BUSY

    def test_busy_icon_distinct_from_every_other_palette_literal(self):
        # ⚙ must be unambiguous against every other palette icon, including the
        # lock-state glyphs surfaced inline in the same title.
        assert ICON_BUSY not in {
            ICON_ACTIVE,
            ICON_WAITING,
            ICON_DONE,
            ICON_TERMINAL,
            GLYPH_LOCK_WAITING,
            GLYPH_LOCK_OWNED,
        }


# =============================================================================
# compose — body format pm:{phase}[:{short}]
# =============================================================================


class TestComposeBodyFormat:
    """Active-phase body renders as ``pm:{phase}`` or ``pm:{phase}:{short}``."""

    def test_phase_only(self):
        result = compose({"current_phase": "5-execute"}, "UserPromptSubmit")
        assert result == f"{ICON_ACTIVE} pm:5-execute"

    def test_phase_and_short_description(self):
        result = compose(
            {"current_phase": "5-execute", "short_description": "wire glyph"},
            "UserPromptSubmit",
        )
        assert result == f"{ICON_ACTIVE} pm:5-execute:wire glyph"

    def test_short_description_whitespace_only_omitted(self):
        # A whitespace-only short_description is treated as empty (no :short).
        result = compose(
            {"current_phase": "3-outline", "short_description": "   "},
            "UserPromptSubmit",
        )
        assert result == f"{ICON_ACTIVE} pm:3-outline"

    def test_short_description_is_stripped(self):
        result = compose(
            {"current_phase": "3-outline", "short_description": "  trim me  "},
            "UserPromptSubmit",
        )
        assert result == f"{ICON_ACTIVE} pm:3-outline:trim me"


# =============================================================================
# compose — glyph prepended for each token state, omitted when no token
# =============================================================================


class TestComposeGlyph:
    """``compose`` prepends the title_token glyph; omits it when absent."""

    def test_lock_waiting_token(self):
        result = compose(
            {"current_phase": "5-execute", "title_token": "lock-waiting"},
            "UserPromptSubmit",
        )
        assert result == f"{ICON_ACTIVE} {GLYPH_LOCK_WAITING} pm:5-execute"

    def test_lock_owned_token(self):
        result = compose(
            {"current_phase": "5-execute", "title_token": "lock-owned"},
            "UserPromptSubmit",
        )
        assert result == f"{ICON_ACTIVE} {GLYPH_LOCK_OWNED} pm:5-execute"

    def test_no_token_omits_glyph(self):
        result = compose({"current_phase": "5-execute"}, "UserPromptSubmit")
        # Exactly two space-separated parts: icon + body, no glyph segment.
        assert result == f"{ICON_ACTIVE} pm:5-execute"
        assert result.count(" ") == 1

    def test_unknown_token_omits_glyph(self):
        # A title_token not in the vocabulary maps to no glyph (None lookup).
        result = compose(
            {"current_phase": "5-execute", "title_token": "not-a-state"},
            "UserPromptSubmit",
        )
        assert result == f"{ICON_ACTIVE} pm:5-execute"

    def test_token_combines_with_short_description(self):
        result = compose(
            {
                "current_phase": "5-execute",
                "short_description": "do thing",
                "title_token": "lock-owned",
            },
            "Stop",
        )
        assert result == f"{ICON_DONE} {GLYPH_LOCK_OWNED} pm:5-execute:do thing"


# =============================================================================
# compose — event → icon resolution wired through compose
# =============================================================================


class TestComposeIconResolution:
    """compose uses resolve_icon for non-terminal phases."""

    def test_active_event(self):
        result = compose({"current_phase": "2-refine"}, "SessionStart")
        assert result.startswith(f"{ICON_ACTIVE} ")

    def test_waiting_event(self):
        result = compose({"current_phase": "2-refine"}, "Notification")
        assert result.startswith(f"{ICON_WAITING} ")

    def test_done_event(self):
        result = compose({"current_phase": "2-refine"}, "Stop")
        assert result.startswith(f"{ICON_DONE} ")

    def test_pre_tool_use_ask_user_question_waiting(self):
        result = compose(
            {"current_phase": "2-refine"}, "PreToolUse", tool_name="AskUserQuestion"
        )
        assert result.startswith(f"{ICON_WAITING} ")

    def test_pre_tool_use_bash_busy(self):
        result = compose(
            {"current_phase": "2-refine"}, "PreToolUse", tool_name="Bash"
        )
        assert result.startswith(f"{ICON_BUSY} ")

    def test_icon_override_supersedes_event(self):
        # Push-mode icon_override wins over the event-resolved icon for a
        # non-terminal phase.
        result = compose(
            {"current_phase": "2-refine"}, None, icon_override="⚑"
        )
        assert result == "⚑ pm:2-refine"


# =============================================================================
# compose — terminal-state override (✅, ➤/? suppressed, Completed body)
# =============================================================================


class TestComposeTerminalOverride:
    """A finished plan forces ✅ regardless of event; ➤/? never appear."""

    def test_complete_phase_forces_terminal_icon(self):
        result = compose({"current_phase": "complete"}, "UserPromptSubmit")
        assert result == f"{ICON_TERMINAL} pm:Completed"

    def test_archived_phase_forces_terminal_icon(self):
        result = compose({"current_phase": "archived"}, "UserPromptSubmit")
        assert result == f"{ICON_TERMINAL} pm:Completed"

    def test_terminal_override_ignores_notification_waiting(self):
        # Even a Notification (would otherwise be ?) yields ✅, not ?.
        result = compose({"current_phase": "complete"}, "Notification")
        assert result.startswith(f"{ICON_TERMINAL} ")
        assert ICON_WAITING not in result.split(" ")[0]

    def test_terminal_override_ignores_stop_done(self):
        result = compose({"current_phase": "archived"}, "Stop")
        assert result.startswith(f"{ICON_TERMINAL} ")

    def test_terminal_override_beats_icon_override(self):
        # The ✅ terminal override wins even over an explicit icon_override.
        result = compose(
            {"current_phase": "complete"}, None, icon_override="⚑"
        )
        assert result == f"{ICON_TERMINAL} pm:Completed"

    def test_completed_body_with_short_description(self):
        result = compose(
            {"current_phase": "complete", "short_description": "all done"},
            "UserPromptSubmit",
        )
        assert result == f"{ICON_TERMINAL} pm:Completed:all done"

    def test_process_icons_never_appear_for_terminal(self):
        # Neither ➤ nor ? ever leads a terminal-phase title.
        for event in ("UserPromptSubmit", "Notification", "SessionStart", "Stop"):
            result = compose({"current_phase": "complete"}, event)
            leading_icon = result.split(" ", 1)[0]
            assert leading_icon == ICON_TERMINAL
            assert leading_icon not in (ICON_ACTIVE, ICON_WAITING, ICON_DONE)


# =============================================================================
# compose — terminal-phase glyph suppression (both token states)
# =============================================================================

# The two lock token states paired with their glyph, iterated in-test as the
# full closed vocabulary of TITLE_TOKEN_GLYPHS so a silent state addition is
# caught (cross-checked against the map below). The two terminal phases that
# force the ✅ icon and the Completed body.
_ALL_TOKEN_STATES = [
    ("lock-waiting", GLYPH_LOCK_WAITING),
    ("lock-owned", GLYPH_LOCK_OWNED),
]
_TERMINAL_PHASES = ["complete", "archived"]


class TestComposeTerminalGlyphSuppression:
    """A finished plan suppresses the title_token glyph for every token state.

    A terminal phase holds no live lock state, so the glyph is suppressed
    regardless of the persisted ``title_token`` — across both states and
    both terminal phases (``complete`` / ``archived``). The Completed body and
    the ✅ terminal icon still render; only the glyph segment is dropped.
    """

    def test_token_states_cover_full_vocabulary(self):
        # Guard: the iterated state list mirrors the closed glyph vocabulary,
        # so a new token state cannot slip past the suppression matrix below.
        assert {state for state, _ in _ALL_TOKEN_STATES} == set(TITLE_TOKEN_GLYPHS)

    def test_glyph_suppressed_for_terminal_phase(self):
        # Both token states are suppressed for both terminal phases.
        for phase in _TERMINAL_PHASES:
            for token, glyph in _ALL_TOKEN_STATES:
                result = compose(
                    {"current_phase": phase, "title_token": token},
                    "Stop",
                )
                # No glyph segment: icon + body only; glyph never appears.
                assert result == f"{ICON_TERMINAL} pm:Completed", (phase, token)
                assert glyph not in result, (phase, token)
                # Exactly one space — two parts (icon + body), no glyph segment.
                assert result.count(" ") == 1, (phase, token)

    def test_glyph_suppressed_with_short_description(self):
        # Suppression holds even when a short_description widens the body.
        for phase in _TERMINAL_PHASES:
            for token, glyph in _ALL_TOKEN_STATES:
                result = compose(
                    {
                        "current_phase": phase,
                        "short_description": "wrap up",
                        "title_token": token,
                    },
                    "UserPromptSubmit",
                )
                assert result == f"{ICON_TERMINAL} pm:Completed:wrap up", (phase, token)
                assert glyph not in result, (phase, token)

    def test_glyph_suppressed_regardless_of_event(self):
        # The suppression is event-agnostic: every hook event yields the same
        # glyph-free terminal title.
        events = ("UserPromptSubmit", "Notification", "SessionStart", "Stop")
        for phase in _TERMINAL_PHASES:
            for token, glyph in _ALL_TOKEN_STATES:
                for event in events:
                    result = compose(
                        {"current_phase": phase, "title_token": token}, event
                    )
                    assert result == f"{ICON_TERMINAL} pm:Completed", (
                        phase,
                        token,
                        event,
                    )
                    assert glyph not in result, (phase, token, event)


class TestComposeActiveGlyphStillRenders:
    """Regression guard: active-phase glyphs are unaffected by the suppression.

    The terminal-phase suppression must not leak into active phases — every
    token state still prepends its glyph for a non-terminal phase.
    """

    def test_active_phase_glyph_renders(self):
        for token, glyph in _ALL_TOKEN_STATES:
            result = compose(
                {"current_phase": "5-execute", "title_token": token},
                "UserPromptSubmit",
            )
            assert result == f"{ICON_ACTIVE} {glyph} pm:5-execute", token
            assert glyph in result, token


# =============================================================================
# compose — no-op (empty / missing current_phase → None)
# =============================================================================


class TestComposeNoOp:
    """compose returns None only for an empty/missing current_phase."""

    def test_missing_phase_returns_none(self):
        assert compose({}, "UserPromptSubmit") is None

    def test_empty_phase_returns_none(self):
        assert compose({"current_phase": ""}, "UserPromptSubmit") is None

    def test_none_phase_returns_none(self):
        assert compose({"current_phase": None}, "UserPromptSubmit") is None

    def test_non_string_phase_returns_none(self):
        assert compose({"current_phase": 5}, "UserPromptSubmit") is None

    def test_noop_ignores_token_and_event(self):
        # No body → None even when a token and a done event are present.
        assert (
            compose(
                {"current_phase": "", "title_token": "lock-owned"},
                "Stop",
            )
            is None
        )


# =============================================================================
# Purity — deterministic, no I/O, input not mutated
# =============================================================================


class TestPurity:
    """compose is a pure function: deterministic and side-effect-free."""

    def test_deterministic_repeated_calls(self):
        state = {
            "current_phase": "5-execute",
            "short_description": "stable",
            "title_token": "lock-waiting",
        }
        first = compose(state, "UserPromptSubmit")
        second = compose(state, "UserPromptSubmit")
        third = compose(state, "UserPromptSubmit")
        assert first == second == third

    def test_input_dict_not_mutated(self):
        state = {
            "current_phase": "5-execute",
            "short_description": "keep me",
            "title_token": "lock-owned",
        }
        snapshot = dict(state)
        compose(state, "Stop")
        assert state == snapshot

    def test_resolve_icon_deterministic(self):
        assert resolve_icon("Stop") == resolve_icon("Stop")
        assert resolve_icon("PreToolUse", "AskUserQuestion") == resolve_icon(
            "PreToolUse", "AskUserQuestion"
        )
