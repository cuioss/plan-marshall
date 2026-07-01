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

The module is pure and side-effect-free: it declares the registry and a derived
key-set helper, nothing else. It imports no other module so both consumers can
load it from the shared ``plan-retrospective/scripts/`` directory on the executor
PYTHONPATH without pulling in transitive dependencies.
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
    # Manifest Decisions is conditional on its own fragment being present —
    # ``check-manifest-consistency`` only emits a fragment when execution.toon
    # exists, so plans pre-dating the manifest deliverable get no section.
    ('Manifest Decisions', 'manifest-decisions', 'manifest-decisions'),
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
