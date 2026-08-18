#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Canonical retrospective section registry shared by the producer and consumer.

This module is the single source of truth for the report's section→fragment-key
map. ``compile-report.py`` imports :data:`SECTION_SPEC` to drive its rendering
loop; ``collect-fragments.py`` imports :func:`valid_aspect_keys` to validate the
``--aspect`` key a producer registers against the set the consumer can actually
render. Keeping both scripts on one registry makes producer/consumer key drift
structurally impossible — a typo'd or renamed aspect key now fails loudly at
``collect-fragments add`` time instead of silently emptying a report section.

The module is pure and side-effect-free: it declares the registry, a derived
key-set helper, and the two vocabularies that make a section's *zero* legible
(:data:`ZERO_ATTRIBUTION_FIELDS` and :data:`ZERO_DECLARED_UNMEASURED_STATUSES`) —
nothing else. It imports no other module so both consumers can load it from the
shared ``plan-retrospective/scripts/`` directory on the executor PYTHONPATH
without pulling in transitive dependencies.
"""

from __future__ import annotations

# Section order matches ``references/report-structure.md``.
# Fragment keys MUST match the hyphenated aspect names produced by
# ``collect-fragments add --aspect <name>``. Underscored variants silently
# drop the corresponding section because the consumer lookup never finds the
# producer's payload.
SECTION_SPEC: tuple[tuple[str, str, str | None], ...] = (
    # (heading, fragment_key, conditional_trigger)
    # ``conditional_trigger`` is the fragment key whose presence is required
    # for the section to be emitted. ``None`` means always emit.
    ('Executive Summary', '_executive-summary', None),
    ('Goals vs Outcomes', 'request-result-alignment', None),
    ('Artifact Consistency', 'artifact-consistency', None),
    ('Log Analysis', 'log-analysis', None),
    # Phase Dispatch Boundaries — gated on the presence of at least one phase
    # entry with ``present: true``. The trigger key is the per-phase fragment
    # itself; the should_emit dispatch surfaces a dedicated boundary-presence
    # branch (lesson 2026-05-20-12-002).
    ('Phase Dispatch Boundaries', 'dispatch_boundaries', 'dispatch_boundaries'),
    ('Invariant Outcomes', 'invariant-summary', None),
    ('Plan Efficiency', 'plan-efficiency', None),
    ('LLM-to-Script Opportunities', 'llm-to-script-opportunities', None),
    ('Logging Gaps', 'logging-gap-analysis', None),
    ('Script Failure Analysis', 'script-failure-analysis', 'script-failure-analysis'),
    ('Permission Prompt Analysis', 'permission-prompt-analysis', 'permission-prompt-analysis'),
    # Direct gh/glab Usage is ALWAYS emitted (``conditional_trigger = None``). A
    # self-trigger would be wrong here: the aspect runs for every plan and a
    # clean run emits a populated counts block with an EMPTY findings list.
    # ``should_emit`` would refuse that fragment while ``_fragment_has_payload``
    # still reports payload, mis-classifying a healthy run as ``sections_dropped``.
    ('Direct gh/glab Usage', 'direct-gh-glab-usage', None),
    # Execution-Context Dispatch Audit is ALWAYS emitted for the same reason: a
    # clean trail yields populated counts with zero findings, which a
    # self-trigger would drop while ``_fragment_has_payload`` still sees payload.
    ('Execution-Context Dispatch Audit', 'execution-context-dispatch-audit', None),
    # Manifest Decisions is conditional on its own fragment being present —
    # ``check-manifest-consistency`` only emits a fragment when execution.toon
    # exists, so plans pre-dating the manifest deliverable get no section.
    ('Manifest Decisions', 'manifest-decisions', 'manifest-decisions'),
    # Routing Decisions is conditional on its own fragment being present —
    # ``check-routing-decisions`` grades the recorded routing/lane/posture
    # decisions against the realized footprint, mirroring the other conditional
    # analysis rows above (lesson 2026-06-20-17-003: a producer without this
    # render row ships the aspect dead).
    ('Routing Decisions', 'routing-decisions', 'routing-decisions'),
    # Chat History Analysis is conditional on its own fragment being present —
    # the aspect is skipped entirely when ``--session-id`` is absent, mirroring
    # the two conditional rows above. Its position (after Routing Decisions,
    # before Proposed Lessons) matches the SKILL.md aspect order: aspect 14 sits
    # between aspect 13 (routing-decisions) and aspect 15.
    #
    # The registry key is the HYPHENATED ``chat-history-analysis``. The
    # fragment's own body carries ``aspect: chat_history_analysis``
    # (underscored) — the two spellings are deliberately different, and keying
    # this row on the underscored form silently empties the section because the
    # consumer lookup never finds the producer's payload.
    ('Chat History Analysis', 'chat-history-analysis', 'chat-history-analysis'),
    ('Proposed Lessons', 'lessons-proposal', None),
)


def valid_aspect_keys() -> set[str]:
    """Return the set of aspect keys a producer may register through ``cmd_add``.

    Every ``fragment_key`` in :data:`SECTION_SPEC` whose name does NOT start with
    ``_`` is registerable. Underscore-prefixed keys (e.g. ``_executive-summary``)
    are injected directly by the orchestrator and never flow through
    ``collect-fragments add``, so they are excluded — ``cmd_add`` already rejects
    ``_``-prefixed keys, and that rule is preserved independently.
    """
    return {fragment_key for _heading, fragment_key, _trigger in SECTION_SPEC if not fragment_key.startswith('_')}


# Fields whose presence lets a reader tell a section's "zero findings" apart from
# "this section could not look". Every *"zero findings"* line carries that
# ambiguity, and naming the population that was examined — and held — is the
# discriminator. The vocabulary is DERIVED from what the deterministic aspects
# already publish, not invented here:
#
# * ``evaluated_population`` — ``standards/execution-context-dispatch-audit.md``
#   ("publishes the evaluated population beside every count so a zero is
#   legible"); emitted by ``check-dispatch-audit.py`` on its ``shape_violation``
#   and ``dispatch_coverage`` blocks. NOT on ``channel_completeness``, which
#   publishes ``dispatch_line_count`` / ``completion_count`` /
#   ``dispatched_step_count`` / ``ratio`` / ``confidence`` instead.
# * ``population`` — the fragment-schema key in ``references/log-analysis.md``
#   (e.g. ``population: plan_script_execution_log``), which names the corpus a
#   block's counts were taken over.
# * ``counts`` — the populated count block ``direct-gh-glab-usage.py`` emits
#   beside an empty ``findings`` list, whose ``total`` / ``by_surface`` entries
#   name what was counted. It is also a documented member of the fragment schema
#   every DOMAIN-contributed aspect follows (``extension-api/standards/
#   ext-point-retrospective.md`` names the shape as ``status``, ``aspect``,
#   ``counts``, ``findings[]``), so an extension aspect that honours its own
#   contract is attributed by construction.
#
# Where each name appears matters, because the probe has a depth. Measured
# against the producers above: ``counts``, ``checks`` and ``expected_invariants``
# are published at the TOP of a fragment; ``evaluated_population`` appears one
# level down inside ``shape_violation`` / ``dispatch_coverage``, and
# ``population`` one level down inside ``script_cost_rollup``.
# ``compile-report._names_checked_set`` therefore reads the top level AND one
# nesting level — a top-level-only read would flag a fragment that DOES name the
# population it examined, simply because it named it inside its fact block.
# * ``checks`` — the per-check roster ``check-artifact-consistency.py`` emits
#   (one ``{name, status, message}`` row per check performed). A named roster IS
#   the checked set, stated item by item rather than as a size.
# * ``expected_invariants`` — the invariant roster ``summarize-invariants.py``
#   evaluated, published beside its ``phases`` breakdown.
#
# Those last two were added after a sweep over the eight in-tree deterministic
# producers, which flagged ``check-artifact-consistency`` and
# ``summarize-invariants`` on every clean run. A third producer names its checked
# set the same way — ``check-manifest-consistency`` publishes ``checks`` on a
# plan that HAS an ``execution.toon`` and a clean cross-check — so ``checks``
# covers two of the three; do not read the pair of names below as a count of the
# producers they serve.
#
# A false positive here is not harmless: the whole point of the signal is that an
# unattributed zero is worth a reader's attention, and a list that cries wolf on
# its own producers stops being read. Note that the probe's live population is
# smaller than eight, and by how much depends on the plan: on a plan carrying an
# ``execution.toon`` exactly ONE of the eight (``script-failure-analysis``) is
# classified a drop and so never reaches ``written``; on a manifest-less plan
# ``manifest-decisions`` and ``routing-decisions`` are dropped as well, making
# three.
ZERO_ATTRIBUTION_FIELDS: tuple[str, ...] = (
    'evaluated_population',
    'population',
    'counts',
    'checks',
    'expected_invariants',
)

# Statuses with which a fragment DECLARES that it could not look, rather than
# reporting a zero it never measured. Such a fragment is already unambiguous, so
# it is not an unattributed zero. ``not_evaluated`` is the token
# ``standards/execution-context-dispatch-audit.md`` mandates in place of "a bare
# ``0`` a reader could mistake for evaluated-clean"; ``skipped`` is the
# graceful-skip status specified by ``references/chat-history-analysis.md``.
ZERO_DECLARED_UNMEASURED_STATUSES: frozenset[str] = frozenset({'not_evaluated', 'skipped'})
