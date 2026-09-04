#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The single implementation of the authorship-admissibility rule.

Preference learning aggregates recurring user gate-dispositions into durable
architecture hints. This module owns the ONE rule that decides which findings may
seed such a recurrence at all, so both preference surfaces — the cross-plan
auditor (``.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py``)
and the per-plan emitter (``phase-6-finalize`` ``finalize-step-preference-emitter``,
which reaches it through ``manage-findings list``) — apply the same predicate
rather than each carrying its own copy.

The rule, and why it is shaped this way
---------------------------------------

A ``pr-comment`` finding contributes to preference learning ONLY when it is
positively attributed to a recognized external reviewer bot — i.e. it carries a
``bot_kind`` that is one of the registry-derived reviewer identities the ingest
verb stamps from the comment author login.

A ``pr-comment`` with no ``bot_kind`` cannot be told apart from the pipeline's own
posted comments: the ingest verb records the pipeline's own PR comments (a
review-trigger comment, a description-restore) with ``bot_kind`` absent, exactly
as it records an unattributed human comment. Admitting such a comment would let the pipeline's own
control traffic become evidence about the pipeline's preferences — a
SELF-REINFORCING measurement artifact that grows with pipeline chattiness rather
than with operator judgement. There is no self-login signal on the finding to
identify "self" directly (the comment-preparation verb stamps no marker), so this
gate fails CLOSED on positive external attribution instead of trying to recognize
self.

Non-comment findings (lint/sonar/bug/test-failure/…) carry no author and are never
pipeline-authored PR chatter; they are unaffected — their tool-disposition
recurrences are exactly the signal preference learning exists to capture.

Degrade-to-presence-only
------------------------

:func:`recognized_bot_kinds` returns ``None`` when the live registry cannot be
resolved. The predicate then degrades to a PRESENCE-only check rather than
over-excluding every bot-attributed comment; the pipeline-self coverage, which
keys on an ABSENT ``bot_kind``, is unaffected either way. ``None`` is therefore a
first-class value of the contract, not an error state — a caller must pass it
through rather than substituting an empty set, which would exclude every
``pr-comment`` instead of admitting the attributed ones.

Import surface
--------------

Stdlib-only apart from ``bot_registry``, the data-not-code reviewer registry this
module derives the recognized set from — the same registry ``_findings_core``'s
``BOT_KINDS`` derives from, so the write-time guard and this aggregation-time gate
cannot disagree about which identities are real.

``bot_registry`` is imported LAZILY, inside :func:`recognized_bot_kinds`, and
resolving it is the CALLER's responsibility — the two callers reach it by
different routes. In-bundle the executor supplies every marketplace ``scripts/``
dir on ``PYTHONPATH``. The auditor runs as a direct ``python3 …/audit.py``
invocation with no executor ``PYTHONPATH`` at all, so it injects both this
module's directory and ``automatic-review/scripts`` onto ``sys.path`` before
importing this module. Either way an unresolvable registry is not an error here:
it takes the degrade path above.

See ``phase-6-finalize/standards/disposition-to-hint-routing.md`` § "(e)
Authorship admissibility" for the shared contract this predicate implements.
"""

from typing import Any

# The finding type the authorship gate is scoped to. Every other type is
# unattributed tool output and is admitted unconditionally.
PR_COMMENT_TYPE = 'pr-comment'


def recognized_bot_kinds() -> frozenset[str] | None:
    """Return the live registry-derived recognized reviewer ``bot_kind`` set, or None.

    ``add_finding`` validates ``bot_kind`` against this set at WRITE time, but a
    consumer may read archived records DIRECTLY — an archived (legacy,
    de-registered, or hand-edited) record could carry a ``bot_kind`` that is not a
    real reviewer identity — so the gate re-derives the set from the live
    ``automatic-review`` registry rather than trusting an arbitrary stored string.

    Returns:
        The recognized ``bot_kind`` values, or ``None`` when the registry module
        cannot be loaded or parsed. ``None`` means DEGRADE: the caller passes it to
        :func:`preference_admissible`, which then applies a presence-only check.
    """
    try:
        import bot_registry  # noqa: PLC0415

        return frozenset(str(kind) for kind in bot_registry.bot_kinds())
    except Exception:  # noqa: BLE001 — any import/parse failure degrades to presence-only
        return None


def preference_admissible(
    obj: dict[str, Any], recognized_bot_kinds: frozenset[str] | None
) -> bool:
    """Return False for a finding that must not seed a preference recurrence.

    Args:
        obj: The finding record.
        recognized_bot_kinds: The recognized reviewer identities, or ``None`` when
            the registry could not be resolved (degrade to a presence-only check).

    Returns:
        Whether the finding is authorship-admissible as preference evidence.
    """
    if obj.get('type') == PR_COMMENT_TYPE:
        bot_kind = obj.get('bot_kind')
        if not (isinstance(bot_kind, str) and bot_kind.strip()):
            return False
        if recognized_bot_kinds is None:
            return True
        return bot_kind.strip() in recognized_bot_kinds
    return True
