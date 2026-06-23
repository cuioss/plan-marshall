# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pure, platform-agnostic terminal-title composition.

This module owns the title-composition contract shared across the plan-marshall
terminal-title machinery. It is a **leaf library**: it imports neither
``manage-status`` nor ``platform-runtime``. ``platform-runtime`` imports it
one-directionally (via PYTHONPATH, the same way ``script-shared`` modules are
consumed) to resolve the composed title string after it has read ``status.json``.

The single public entry point is :func:`compose`, a pure function of
``(state_dict, event)`` that returns the ``'{icon} {glyph} {body}'`` string (or
``None`` for a true no-op). It performs NO filesystem or network I/O — the
caller passes the already-read plan state.

Composition has three independent inputs:

* **Body** — ``pm:{phase}[:{short}]`` for active phases, and the Completed body
  for terminal phases (``complete`` / ``archived``). See :func:`_compose_body`.
* **Glyph** — the ``title_token`` lock-state glyph (⏳/🔒), prepended when set
  for an active phase. Suppressed for terminal phases regardless of the
  persisted token state — a finished plan holds no live lock state. See
  :data:`TITLE_TOKEN_GLYPHS`.
* **Icon** — the process icon resolved from a target-neutral process state (➤
  active / ? waiting / ⚙ busy / ✓ done), with a terminal-state override to ✅
  (:data:`_ICON_TERMINAL`) for a finished plan regardless of the process state.
  See :func:`resolve_icon` and :func:`compose`.

The composer is target-neutral by construction: it knows nothing about Claude
hook events. The caller (e.g. ``platform-runtime``'s ``claude_runtime``) maps its
target-specific event vocabulary to one of the :data:`PROCESS_STATES` values and
passes that neutral state in.
"""

from __future__ import annotations

# --- Process-state enum (target-neutral) ------------------------------------
#
# The composer resolves the process icon from a target-neutral process state,
# NOT from any target's event vocabulary. A target runtime maps its own events
# (Claude's SessionStart/UserPromptSubmit/Notification/Stop/PreToolUse/...) to one
# of these values before calling :func:`compose` / :func:`resolve_icon`.
PROCESS_STATE_ACTIVE = "active"
PROCESS_STATE_WAITING = "waiting"
PROCESS_STATE_BUSY = "busy"
PROCESS_STATE_DONE = "done"

PROCESS_STATES: frozenset[str] = frozenset(
    {PROCESS_STATE_ACTIVE, PROCESS_STATE_WAITING, PROCESS_STATE_BUSY, PROCESS_STATE_DONE}
)

# --- Icon palette (process state → process icon) ----------------------------
#
#   ➤  active / in-progress
#   ?  waiting on user input ("needs attention")
#   ✓  done (per-turn done state)
#   ✅  terminal (whole plan complete / archived) — the thick U+2705 check-mark,
#       deliberately distinct from the thin ✓ ``_ICON_DONE`` used per turn.
#   ⚙  busy / executing a long-running tool, deliberately distinct from ➤
#       ``_ICON_ACTIVE`` and the ? ``_ICON_WAITING`` icon.
_ICON_ACTIVE = "➤"  # ➤
_ICON_WAITING = "?"
_ICON_DONE = "✓"  # ✓
_ICON_TERMINAL = "✅"  # ✅
_ICON_BUSY = "⚙"  # ⚙

# Process-state → icon map. The terminal-phase ✅ override is applied by
# :func:`compose`, NOT here.
_PROCESS_STATE_ICONS: dict[str, str] = {
    PROCESS_STATE_ACTIVE: _ICON_ACTIVE,
    PROCESS_STATE_WAITING: _ICON_WAITING,
    PROCESS_STATE_BUSY: _ICON_BUSY,
    PROCESS_STATE_DONE: _ICON_DONE,
}


# --- Title-token glyph vocabulary (lock state → glyph) ----------------------
#
# The two lock-coordination states surfaced inline in the terminal title.
# ``manage-status`` persists only the bare state string in the ``title_token``
# field; this map is the single owner of the state → glyph rendering.
TITLE_TOKEN_GLYPHS: dict[str, str] = {
    "lock-waiting": "⏳",  # ⏳
    "lock-owned": "\U0001f512",  # 🔒
}


# --- Terminal phases --------------------------------------------------------
#
# Phases for which the plan is finished: the icon is forced to ✅, the body is
# the Completed body (never ``None``), and the title_token glyph is suppressed,
# so a finished plan always renders with the terminal icon, never the ➤/?
# process icons, and never a lock glyph.
_TERMINAL_PHASES: frozenset[str] = frozenset({"complete", "archived"})

# Body prefix for an active phase and the Completed terminal body, respectively.
_BODY_PREFIX = "pm"
_COMPLETED_PHASE_LABEL = "Completed"


def resolve_icon(process_state: str | None) -> str:
    """Map a target-neutral process state to the canonical process icon.

    Palette (one of the :data:`PROCESS_STATES` values):

    - ``"active"`` → ``➤``
    - ``"waiting"`` → ``?`` (canonical "needs attention")
    - ``"busy"`` → ``⚙`` (busy / long-running tool)
    - ``"done"`` → ``✓``
    - Unknown / missing state → ``➤`` (defensive default)

    The function never raises; callers pass best-effort values and rely on the
    defensive default for any unmapped or missing input. The composer is
    target-neutral — the Claude hook-event → process-state mapping lives in the
    caller (``platform-runtime``'s ``claude_runtime``), NOT here. The
    terminal-phase ✅ override is applied by :func:`compose`, NOT here — this
    function resolves the process icon only.
    """
    return _PROCESS_STATE_ICONS.get(process_state, _ICON_ACTIVE)  # type: ignore[arg-type]


def _compose_body(state_dict: dict[str, object]) -> str | None:
    """Render the title body from the plan state dict.

    Returns:

    - ``pm:{phase}:{short}`` when ``current_phase`` is an active (non-terminal)
      phase and ``short_description`` is present.
    - ``pm:{phase}`` when active and no ``short_description``.
    - ``pm:Completed:{short}`` / ``pm:Completed`` when ``current_phase`` is a
      terminal phase (``complete`` / ``archived``) — the Completed body, NOT
      ``None``, so a finished plan still renders (with the ✅ override applied by
      :func:`compose`).
    - ``None`` only when ``current_phase`` is empty/missing (true no-op).

    Pure — operates solely on the passed ``state_dict``.
    """
    phase = state_dict.get("current_phase")
    if not phase or not isinstance(phase, str):
        return None

    short = state_dict.get("short_description")
    short_str = short.strip() if isinstance(short, str) else ""

    if phase in _TERMINAL_PHASES:
        label = _COMPLETED_PHASE_LABEL
    else:
        label = phase

    if short_str:
        return f"{_BODY_PREFIX}:{label}:{short_str}"
    return f"{_BODY_PREFIX}:{label}"


def compose(
    state_dict: dict[str, object],
    process_state: str | None,
    icon_override: str | None = None,
) -> str | None:
    """Compose the full ``'{icon} {glyph} {body}'`` terminal-title string.

    Pure function of the passed plan state and a target-neutral process state.
    Performs NO filesystem or network I/O.

    Args:
        state_dict: The plan state — ``current_phase`` (str), optional
            ``short_description`` (str), and optional ``title_token`` (one of
            the :data:`TITLE_TOKEN_GLYPHS` keys).
        process_state: The target-neutral process state driving the process icon
            — one of the :data:`PROCESS_STATES` values (``"active"``,
            ``"waiting"``, ``"busy"``, ``"done"``). ``None`` for push-mode /
            statusLine, where ``icon_override`` supplies the icon instead. The
            caller maps its own target-specific events to this neutral state.
        icon_override: Push-mode icon. When provided it supersedes the
            state-resolved icon for non-terminal phases. The terminal-phase ✅
            override still wins over ``icon_override`` for a finished plan.

    Returns:
        The composed ``'{icon} {glyph} {body}'`` string (glyph omitted when no
        ``title_token`` is set, and always omitted for terminal phases), or
        ``None`` when the body is ``None`` (true no-op — empty/missing
        ``current_phase``).

    Icon selection:

    - When ``current_phase`` is terminal (``complete`` / ``archived``), the icon
      is forced to ✅ (:data:`_ICON_TERMINAL`) regardless of ``process_state`` /
      ``icon_override`` — the process icons ➤ (active) and ? (waiting) MUST NOT
      appear for a finished plan.
    - Otherwise the icon is ``icon_override`` when given, else
      :func:`resolve_icon`\\(``process_state``).

    Glyph selection:

    - When ``current_phase`` is terminal (``complete`` / ``archived``), the
      ``title_token`` glyph is suppressed regardless of the persisted token
      state — a finished plan holds no live lock state, so it renders NO
      glyph for either of the two :data:`TITLE_TOKEN_GLYPHS` states (⏳/🔒).
      The suppression is token-agnostic by construction.
    - Otherwise (active phase) the glyph for the persisted ``title_token`` is
      prepended when set.
    """
    body = _compose_body(state_dict)
    if body is None:
        return None

    phase = state_dict.get("current_phase")
    is_terminal = isinstance(phase, str) and phase in _TERMINAL_PHASES
    if is_terminal:
        icon = _ICON_TERMINAL
    elif icon_override is not None:
        icon = icon_override
    else:
        icon = resolve_icon(process_state)

    # A finished plan holds no live lock state, so the title_token glyph is
    # suppressed for terminal phases. The suppression is at the glyph-prepend,
    # making it token-agnostic: both TITLE_TOKEN_GLYPHS states (⏳/🔒) are
    # uniformly suppressed for a terminal plan. The glyph only renders for
    # active phases.
    if not is_terminal:
        token = state_dict.get("title_token")
        glyph = TITLE_TOKEN_GLYPHS.get(token) if isinstance(token, str) else None
        if glyph:
            return f"{icon} {glyph} {body}"

    return f"{icon} {body}"
