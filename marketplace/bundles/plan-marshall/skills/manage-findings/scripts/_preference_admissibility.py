#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The single implementation of the authorship-admissibility rule.

Preference learning aggregates recurring user gate-dispositions into durable
architecture hints. This module owns the ONE rule that decides which findings may
seed such a recurrence at all, so both preference surfaces — the cross-plan
auditor and the per-plan emitter — apply the same predicate rather than each
carrying its own copy. The auditor (``audit-archived-plan-retrospectives``) is
delivered by this repository's project-local tree
(``.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py``), which
ships to no target; the emitter (``phase-6-finalize``
``finalize-step-preference-emitter``) ships in the bundle and reaches the rule
through ``manage-findings list``.

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

:func:`recognized_bot_kinds` returns ``None`` when the live registry does not
yield a usable recognized set — whether it could not be imported or parsed at
all, or it loaded and yielded NOTHING. The predicate then degrades to a
PRESENCE-only check rather than over-excluding every bot-attributed comment; the
pipeline-self coverage, which keys on an ABSENT ``bot_kind``, is unaffected
either way. ``None`` is therefore a first-class value of the contract, not an
error state — a caller must pass it through rather than substituting an empty
set, which would exclude every ``pr-comment`` instead of admitting the attributed
ones.

An EMPTY derived set collapses to that same ``None`` at the point of derivation,
because the registry loader reaches empty WITHOUT raising: it returns early when
its standards dir is absent and skips a doc it cannot read. An empty
``frozenset`` is not ``None``, so passing one on would publish basis
``recognized`` while excluding every bot-attributed comment — a vacuous
population disclosed as the strong check. Emptiness is therefore read as
"unresolved", never as "resolved, and nothing is recognized".

Which path ran travels with the result, so this module also owns the two values of
that disclosure — :data:`PREFERENCE_BASIS_RECOGNIZED` and
:data:`PREFERENCE_BASIS_PRESENCE_ONLY`. They live beside the rule whose two paths
they name, so the two consumers cannot drift apart on the vocabulary the way they
could while each declared its own copy.

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
importing this module.

What the degrade above covers on BOTH routes is a registry that RESOLVES and
yields nothing. A wholly UNIMPORTABLE ``bot_registry`` degrades here only on the
auditor route: in-bundle, ``_findings_core`` imports ``bot_registry`` at module
scope and calls it at import time to derive ``BOT_KINDS``, so an import failure
kills the ``manage-findings`` CLI before any verb dispatches and this function
never runs. The lazy import buys per-call isolation for this module; it does not
buy the in-bundle caller reachability of the degrade.

See ``phase-6-finalize/standards/disposition-to-hint-routing.md`` § "(e)
Authorship admissibility" for the shared contract this predicate implements.
"""

from typing import Any

# The finding type the authorship gate is scoped to. Every other type is
# unattributed tool output and is admitted unconditionally.
PR_COMMENT_TYPE = 'pr-comment'

# The two values of the ``preference_admissibility_basis`` disclosure both
# preference surfaces publish. ``recognized`` says the gate ran against the live
# registry-derived reviewer set; ``presence_only`` says that set was unresolvable
# and the rule took its documented degrade path, admitting any PRESENT
# ``bot_kind``. The degrade is deliberate — rejecting every bot-attributed comment
# instead would hand preference learning a clean zero over an unread population —
# but it must never pass as the strong check, so the basis travels with the result.
#
# Both consumers read these names from here: the per-plan surface
# (``_findings_core``) imports them, and the cross-plan auditor
# (``audit-archived-plan-retrospectives``, a project-local skill tree that ships
# to no target) reads them off the module object its loader already returns.
# Neither restates the literals.
PREFERENCE_BASIS_RECOGNIZED = 'recognized'
PREFERENCE_BASIS_PRESENCE_ONLY = 'presence_only'


def recognized_bot_kinds() -> frozenset[str] | None:
    """Return the live registry-derived recognized reviewer ``bot_kind`` set, or None.

    ``add_finding`` validates ``bot_kind`` against this set at WRITE time, but a
    consumer may read archived records DIRECTLY — an archived (legacy,
    de-registered, or hand-edited) record could carry a ``bot_kind`` that is not a
    real reviewer identity — so the gate re-derives the set from the live
    ``automatic-review`` registry rather than trusting an arbitrary stored string.

    An EMPTY derived set is reported as ``None``, never as an empty
    ``frozenset``. The registry loader reaches empty WITHOUT raising — it returns
    early when its standards dir is absent, and skips a doc it cannot read — so
    emptiness is a failure to resolve the population, not a population that is
    genuinely empty. Returning the empty set would publish basis ``recognized``
    while excluding EVERY bot-attributed ``pr-comment``: a gate reported as strong
    over a population it never read.

    Returns:
        The recognized ``bot_kind`` values, or ``None`` when the registry module
        cannot be loaded or parsed, or resolves but yields no bot kinds. ``None``
        means DEGRADE: the caller passes it to :func:`preference_admissible`,
        which then applies a presence-only check.
    """
    try:
        import bot_registry

        derived = frozenset(str(kind) for kind in bot_registry.bot_kinds())
    except Exception:  # any import/parse failure degrades to presence-only
        return None
    if not derived:  # resolvable-but-empty is unresolved, not resolved-and-empty
        return None
    return derived


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
