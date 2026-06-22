#!/usr/bin/env python3
"""Shared PreToolUse gate — single home of payload-field knowledge + context predicate.

This module is a pure-function library with no I/O of its own. Both the
observe-only capture leaf (``claude_pretooluse_capture.py``) and the enforcement
leaf (``claude_pretooluse_hook.py``) import it so that ALL knowledge of the
PreToolUse payload's field names and the context-gate predicate lives in exactly
one place — there is no field-name duplication across the two leaves.

It owns three things and nothing else:

1. ``parse(raw)`` — best-effort stdin-JSON parse that returns ``{}`` on empty or
   malformed input and never raises.
2. The field accessors the leaves read:
   - ``sub_agent_identity(payload)`` — Signal-1 source (sub-agent identity).
   - ``cwd(payload)`` — Signal-2 source (working directory).
   - ``tool_name(payload)`` / ``tool_input(payload)`` — the readers the
     enforcement matchers consume.
3. ``context_gate(payload)`` — the ``Signal1 OR Signal2`` predicate, fail-open
   (returns ``False`` when neither signal fires, so no enforcement is applied
   outside a plan-marshall plan context).

The field-name constants below are the single best-guess for the sub-agent
identity field, the cwd field, and the tool-name/tool-input fields. The
observe-only capture leaf (D2) validates them against real PreToolUse payloads;
if a best-guess name is wrong, it is corrected HERE — in this one module —
before the enforcement leaf is finalized.

This module owns NO rule matchers. The R1–R4 enforcement rules are
enforcement-only and live solely in the enforcement leaf.

Best-effort / no-raise throughout: every accessor degrades to a safe default
rather than raising, so a malformed payload can never break a caller.
"""
from __future__ import annotations

import json
import os
from typing import Any

# =============================================================================
# Field-name constants — the SINGLE source of payload-field knowledge.
#
# These are the best-guess field names the D2 capture leaf validates against the
# observed PreToolUse payload schema. Correct them HERE (and nowhere else) if a
# capture run reveals a different field name.
# =============================================================================

#: Field carrying the sub-agent identity (Signal 1). Empirically confirmed via the
#: D2 capture run: a dispatched sub-agent call carries ``agent_type`` (and also
#: ``agent_id``); a main-session call carries neither. The value is bundle-qualified
#: — e.g. ``plan-marshall:execution-context-level-4`` — so it is matched by the
#: ``:execution-context`` substring marker below, NOT by a bare prefix.
SUB_AGENT_IDENTITY_FIELD = "agent_type"

#: Documented fallback candidates for the Signal-1 identity field, checked in
#: order after ``SUB_AGENT_IDENTITY_FIELD``. Kept in this one module so a capture
#: correction is a single-line edit. The empirically-confirmed name (from the D2
#: capture) should be promoted to ``SUB_AGENT_IDENTITY_FIELD``.
SUB_AGENT_IDENTITY_FALLBACK_FIELDS = ("agent_id", "agent_name", "subagent_type")

#: Field carrying the working directory (Signal 2).
CWD_FIELD = "cwd"

#: Field carrying the invoked tool's name (e.g. ``"Bash"``, ``"Edit"``).
TOOL_NAME_FIELD = "tool_name"

#: Field carrying the invoked tool's input object (the per-tool argument struct
#: the enforcement matchers inspect — e.g. ``{"command": "..."}`` for Bash,
#: ``{"file_path": "..."}`` for Edit).
TOOL_INPUT_FIELD = "tool_input"

#: Substring marker the sub-agent identity value carries when the call originates
#: inside a dispatched execution-context sub-agent (Signal 1). The identity is
#: bundle-qualified (``{bundle}:execution-context[-reader]-level-N``), so the gate
#: matches this marker as a substring rather than a prefix — confirmed against real
#: payloads by the D2 capture run.
EXECUTION_CONTEXT_MARKER = ":execution-context"

#: Path segment that marks a plan worktree (Signal 2). A ``cwd`` resolving under
#: this segment indicates the call runs inside a plan-marshall plan worktree.
WORKTREE_PATH_SEGMENT = os.path.join(".plan", "local", "worktrees")


def parse(raw: str) -> dict[str, Any]:
    """Best-effort parse of the raw PreToolUse stdin payload.

    Returns the decoded JSON object, or an empty dict on empty, malformed, or
    non-object input. Never raises.

    Args:
        raw: The raw stdin string the hook received.

    Returns:
        The decoded payload dict, or ``{}`` when the input is empty, not valid
        JSON, or not a JSON object.
    """
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        decoded = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(decoded, dict):
        return {}
    return decoded


def sub_agent_identity(payload: dict[str, Any]) -> str | None:
    """Read the sub-agent identity field (Signal-1 source).

    Checks ``SUB_AGENT_IDENTITY_FIELD`` first, then each name in
    ``SUB_AGENT_IDENTITY_FALLBACK_FIELDS`` in order, returning the first
    non-empty string value found. Returns ``None`` when the payload is not a
    dict or no identity field carries a non-empty string.

    Args:
        payload: The parsed PreToolUse payload.

    Returns:
        The sub-agent identity string, or ``None`` when absent.
    """
    if not isinstance(payload, dict):
        return None
    for field in (SUB_AGENT_IDENTITY_FIELD, *SUB_AGENT_IDENTITY_FALLBACK_FIELDS):
        value = payload.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def cwd(payload: dict[str, Any]) -> str | None:
    """Read the working-directory field (Signal-2 source).

    Args:
        payload: The parsed PreToolUse payload.

    Returns:
        The ``cwd`` string, or ``None`` when the payload is not a dict or the
        field is absent or not a non-empty string.
    """
    if not isinstance(payload, dict):
        return None
    value = payload.get(CWD_FIELD)
    if isinstance(value, str) and value:
        return value
    return None


def tool_name(payload: dict[str, Any]) -> str | None:
    """Read the invoked tool's name.

    Args:
        payload: The parsed PreToolUse payload.

    Returns:
        The tool name (e.g. ``"Bash"``), or ``None`` when the payload is not a
        dict or the field is absent or not a non-empty string.
    """
    if not isinstance(payload, dict):
        return None
    value = payload.get(TOOL_NAME_FIELD)
    if isinstance(value, str) and value:
        return value
    return None


def tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Read the invoked tool's input object.

    Args:
        payload: The parsed PreToolUse payload.

    Returns:
        The tool-input dict, or ``{}`` when the payload is not a dict or the
        field is absent or not a dict. Always a dict so callers can index it
        without a None-check.
    """
    if not isinstance(payload, dict):
        return {}
    value = payload.get(TOOL_INPUT_FIELD)
    if isinstance(value, dict):
        return value
    return {}


def _signal_sub_agent(payload: dict[str, Any]) -> bool:
    """Signal 1 — the sub-agent identity carries the execution-context marker.

    The identity value is bundle-qualified (e.g.
    ``plan-marshall:execution-context-level-4``), so the marker is matched as a
    substring, not a prefix.
    """
    identity = sub_agent_identity(payload)
    return identity is not None and EXECUTION_CONTEXT_MARKER in identity


def _signal_worktree_cwd(payload: dict[str, Any]) -> bool:
    """Signal 2 — the cwd resolves under the plan-worktree path segment."""
    current = cwd(payload)
    if current is None:
        return False
    # Normalize to forward-slash and ensure both sides have directory boundaries
    # so a partial substring match (e.g. "worktrees-extra") cannot trigger this.
    normalized_cwd = current.replace("\\", "/").rstrip("/") + "/"
    normalized_segment = "/" + WORKTREE_PATH_SEGMENT.replace("\\", "/").strip("/") + "/"
    return normalized_segment in normalized_cwd


def context_gate(payload: dict[str, Any]) -> bool:
    """Return the ``Signal1 OR Signal2`` plan-context predicate (fail-open).

    The gate is the single-sourced decision for whether the call originates
    inside a plan-marshall plan context and is therefore eligible for
    enforcement:

    - **Signal 1** — the sub-agent identity carries the ``:execution-context``
      marker, e.g. ``plan-marshall:execution-context-level-4`` (the call runs
      inside a dispatched execution-context sub-agent).
    - **Signal 2** — the working directory resolves under
      ``.plan/local/worktrees/`` (the call runs inside a plan worktree).

    The gate is ``True`` when either signal fires (so an absent Signal-1 field
    still lets Signal 2 satisfy the gate, and vice versa) and ``False`` when
    neither fires — fail-open, so calls outside a plan context are never
    enforced.

    Args:
        payload: The parsed PreToolUse payload.

    Returns:
        ``True`` when Signal 1 OR Signal 2 fires; ``False`` otherwise.
    """
    return _signal_sub_agent(payload) or _signal_worktree_cwd(payload)
