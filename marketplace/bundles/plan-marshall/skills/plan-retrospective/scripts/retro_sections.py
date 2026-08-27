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

#: Fragment key the plan-level footprint-derivation aggregate is injected under.
#: UNDERSCORE-PREFIXED deliberately: ``compile-report`` computes and injects this
#: record itself, so — exactly like ``_executive-summary`` — it must never be
#: registerable through ``collect-fragments add``. :func:`valid_aspect_keys`
#: filters it out by that prefix, so the exclusion is structural rather than a
#: second list to keep in step.
FOOTPRINT_AGGREGATE_KEY = '_footprint-derivation'

#: The aspects that consume the SHARED footprint derivation
#: (``_footprint_resolver.resolve_footprint`` and the helpers it composes), and so
#: go unmeasurable TOGETHER when that derivation cannot be resolved.
#:
#: This is a declaration of WHICH registry rows consume the derivation, not a
#: second copy of the roster: the roster itself is derived from
#: :data:`SECTION_SPEC` by :func:`footprint_consuming_aspect_keys`, so a member
#: named here with no registry row contributes nothing, and the reported order is
#: always the registry's own. Adding a footprint-consuming aspect means adding its
#: registry row (which any new aspect needs regardless) and naming it here — the
#: aggregate's ``producer_count`` then grows with no consumer edit.
#: ⛔ ``manifest-decisions`` (``check-manifest-consistency``) is deliberately NOT a
#: member, though it is often described as one. Measured against HEAD it publishes
#: no footprint-degradation verdict at all: a content sweep for the degradation
#: tokens below returns no match in that script, a sweep for
#: ``footprint_resolved`` / ``FOOTPRINT_UNRESOLVED`` returns none either, and it
#: carries a single ``resolve_footprint`` mention against the 9, 8 and 3 carried by
#: ``artifact-consistency``, ``log-analysis`` and ``routing-decisions``. A producer
#: with no degraded verdict reads as ``resolved`` on EVERY run, and one resolved
#: member suppresses the record — so rostering it would not make the aggregate
#: broader, it would make it incapable of ever firing. Add it here the moment it
#: grows a degradation verdict, not before.
#: ``outline-vs-shipped`` (``check-outline-vs-shipped``) IS a member on exactly that
#: test: it resolves the footprint through the shared chain and publishes
#: ``comparison: inconclusive`` — the first token below, as a VALUE — whenever no
#: tier answers, so it goes unmeasurable on the same missing derivation as the rest.
FOOTPRINT_CONSUMING_ASPECTS: tuple[str, ...] = (
    'artifact-consistency',
    'log-analysis',
    'outline-vs-shipped',
    'routing-decisions',
)

#: Tokens by which a footprint-consuming aspect DECLARES it could not derive the
#: footprint. Each is the producer's own existing honest-degradation token, read
#: rather than introduced — ``inconclusive`` is the per-check status the three
#: ``check-*`` aspects emit, and ``ARTIFACT_COVERAGE_UNMEASURABLE`` is the token
#: ``analyze-logs`` embeds in its warning finding's message.
#:
#: ⛔ HOW each token is matched is owned by ``compile-report._declares_degraded``
#: and differs PER TOKEN — ``inconclusive`` by equality against a verdict field,
#: the other as a substring of any string value. Read the rule there rather than
#: assuming one uniform match; neither shape is restated here.
FOOTPRINT_DEGRADED_TOKENS: tuple[str, ...] = (
    'inconclusive',
    'ARTIFACT_COVERAGE_UNMEASURABLE',
)

#: The compose-time producer of the same signal. It has NO aspect-registry entry —
#: it runs at manifest-compose time, not retrospective time — so it is named
#: explicitly and published under its own provenance, keeping the derived half of
#: the roster distinguishable from the declared one.
COMPOSE_TIME_PRODUCER = 'manage-execution-manifest'

#: The artifact the compose-time producer's verdict is read from, relative to the
#: plan directory.
COMPOSE_TIME_ARTIFACT = 'execution.toon'

#: The compose-time producer's own degradation token.
COMPOSE_TIME_DEGRADED_TOKEN = 'pre_push_quality_gate_inactive'

#: Provenance labels, published per roster member so a reader can tell the
#: registry-derived members from the single explicitly-named one.
PROVENANCE_ASPECT_REGISTRY = 'aspect_registry'
PROVENANCE_COMPOSE_TIME = 'named_compose_time_producer'

#: What the aggregate says it did with each roster member.
PRODUCER_DEGRADED = 'degraded'
PRODUCER_RESOLVED = 'resolved'

#: The member's artifact was not on disk, so nothing is known about its verdict.
#: Distinct from ``resolved`` in the way that matters: an unread member cannot
#: support an aggregate claim, so any of them suppresses the verdict.
PRODUCER_UNREAD = 'unread'

#: The aggregate fired: every roster member was read, and every one degraded.
AGGREGATE_UNMEASURABLE = 'unmeasurable'

#: The aggregate would have fired, but the roster was not fully read. Reported in
#: place of the verdict — an aggregate computed over a roster that was not fully
#: read is the vacuous-authority shape this signal exists to remove.
AGGREGATE_PARTIAL_COVERAGE = 'partial_coverage'

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
    # Footprint Derivation Coverage — the PLAN-LEVEL aggregate over every aspect
    # that consumes the shared footprint derivation. Injected by
    # ``compile-report`` itself (never registered by a producer), and conditional
    # on that injection: the record is absent whenever the aggregate neither
    # fired nor lost coverage, so the section then takes the ordinary benign-
    # omission path.
    #
    # Positioned BEFORE every aspect it aggregates so a reader meets the
    # plan-level caveat before any individual footprint-derived verdict, rather
    # than after having already read some of them at face value. It sits after
    # ``Goals vs Outcomes`` because inserting it anywhere later would break the
    # adjacency ``Chat History Analysis`` pins between ``Routing Decisions`` and
    # ``Proposed Lessons``.
    ('Footprint Derivation Coverage', FOOTPRINT_AGGREGATE_KEY, FOOTPRINT_AGGREGATE_KEY),
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
    # Outline vs Shipped is ALWAYS emitted (``conditional_trigger = None``), for
    # the same reason ``Direct gh/glab Usage`` and ``Execution-Context Dispatch
    # Audit`` are: the aspect runs for every plan, and a plan whose work matched
    # its outline emits a populated ``counts`` block with an EMPTY ``findings``
    # list. A self-trigger would refuse exactly that fragment while
    # ``_fragment_has_payload`` still reports payload — mis-classifying the
    # healthy, matched-control run as ``sections_dropped``, which is the state
    # this aspect most needs to render cleanly.
    #
    # Positioned after ``Chat History Analysis`` so it does not disturb the
    # adjacency that row pins between ``Routing Decisions`` and ``Proposed
    # Lessons``.
    ('Outline vs Shipped', 'outline-vs-shipped', None),
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


def footprint_consuming_aspect_keys() -> tuple[str, ...]:
    """Return the registry rows that consume the shared footprint derivation.

    DERIVED from :data:`SECTION_SPEC` — walked in registry order and filtered by
    :data:`FOOTPRINT_CONSUMING_ASPECTS` — rather than returning that tuple
    directly. The difference is what makes the aggregate's roster a property of
    the registry instead of a second list beside it: a name declared as a
    consumer but carrying no registry row contributes no roster member (it has no
    fragment to read, so counting it would manufacture a permanently-unread
    producer), and the reported order is always the registry's own.

    Four cross-checks in this skill previously hard-coded a population that then
    drifted from its authoritative source; deriving here is the direct answer to
    that shape.
    """
    declared = set(FOOTPRINT_CONSUMING_ASPECTS)
    return tuple(
        fragment_key
        for _heading, fragment_key, _trigger in SECTION_SPEC
        if fragment_key in declared
    )


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
