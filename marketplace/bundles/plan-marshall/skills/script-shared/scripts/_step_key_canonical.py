# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single-source canonical resolver for manifest step keys.

Every write and read of a step record — ``mark-step-done`` (manage-status),
``assert-step-recorded`` (manage-status), ``record-step`` (manage-execution-
manifest), and every manifest-internal boundary-normalization call site — routes
its step id through :func:`canonicalize_step_key` so the write key and the read
key are computed identically. A genuine prefix mismatch then fails loud instead
of being silently tolerated by a near-miss verdict, and a bare-vs-``default:``
variant reconciles to the same canonical key.

Canonicalization has two composed operations, applied in order:

1. **Promoted built-in alias map** — a ``{bundle}:{skill}`` id that was promoted
   out of a former built-in finalize doc into a top-level bundle skill
   (:data:`PROMOTED_BUILTIN_STEP_IDS`) maps to its bare built-in name
   (``plan-marshall:automatic-review`` → ``automatic-review``).
2. **Default-prefix strip** — a leading ``default:`` prefix is stripped to the
   bare manifest key (``default:push`` → ``push``).

Every other id — ``project:`` steps, genuinely opt-in ``{bundle}:{skill}`` steps
(e.g. ``plan-marshall:plan-retrospective``) — is preserved verbatim so the
dispatcher still routes it as a typed step. The function is idempotent: it is a
fixed point on any already-canonical input.

This module is pure (no I/O, no subprocess, no git) and stdlib-only, and lives at
the ``script-shared/scripts/`` top level so every consuming bundle imports it by
bare name (``from _step_key_canonical import canonicalize_step_key``).
"""

from __future__ import annotations

# Promoted built-in-equivalent bundle finalize steps: their ``{bundle}:{skill}``
# id canonicalizes to a bare name exactly like a ``default:`` step. These skills
# were promoted out of a former ``phase-6-finalize`` built-in doc into a
# top-level bundle skill (``default_on: true``, seeded into the default finalize
# set), so the composer, snapshot, lane, owner, step-params, and step-record
# machinery must treat the bundle-prefixed id and its bare form identically.
# Genuinely opt-in ``{bundle}:{skill}`` steps (e.g. ``plan-marshall:plan-
# retrospective``) are NOT listed here and keep their prefix verbatim so the
# dispatcher routes them as typed SKILL steps.
PROMOTED_BUILTIN_STEP_IDS: dict[str, str] = {
    'plan-marshall:automatic-review': 'automatic-review',
}

_DEFAULT_PREFIX = 'default:'


def canonicalize_step_key(step: str) -> str:
    """Return the canonical (bare) manifest key for a step id.

    First maps a promoted built-in-equivalent bundle step id
    (:data:`PROMOTED_BUILTIN_STEP_IDS`) to its bare name, then strips a leading
    ``default:`` prefix. ``project:`` and other ``{bundle}:{skill}`` ids are
    preserved verbatim. The function is idempotent — a fixed point on an
    already-canonical input.
    """
    if step in PROMOTED_BUILTIN_STEP_IDS:
        return PROMOTED_BUILTIN_STEP_IDS[step]
    if step.startswith(_DEFAULT_PREFIX):
        return step[len(_DEFAULT_PREFIX) :]
    return step
