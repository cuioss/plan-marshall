#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
CLI script for plan metrics collection and reporting.

Usage:
    Start phase timing:
        python3 manage-metrics.py start-phase --plan-id <id> --phase <phase>

    End phase timing:
        python3 manage-metrics.py end-phase --plan-id <id> --phase <phase> [--total-tokens N] [--duration-ms N] [--tool-uses N]

    Generate metrics.md:
        python3 manage-metrics.py generate --plan-id <id>

    Atomic phase boundary (end-phase + start-phase + generate):
        python3 manage-metrics.py phase-boundary --plan-id <id> \
            --prev-phase <prev> --next-phase <next> \
            [--total-tokens N] [--duration-ms N] [--tool-uses N]

    Accumulate per-phase subagent usage on disk:
        python3 manage-metrics.py accumulate-agent-usage --plan-id <id> --phase <phase> \
            [--total-tokens N] [--tool-uses N] [--duration-ms N] [--retrospective-tokens N]

    Enrich from JSONL transcript (per-phase subagent <usage>):
        python3 manage-metrics.py enrich --plan-id <id> --session-id <sid>

    Reconcile the row ledgers against each other (read-only):
        python3 manage-metrics.py reconcile-ledgers --plan-id <id> [--window-seconds N]
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from _display_time import render_timestamp
from _ledger_reconciliation import (
    DEFAULT_WINDOW_SECONDS,
    EXECUTION_LOG_PHASES,
    execution_rows_for_phase,
    load_boundary_rows,
    load_execution_log,
    reconcile_phase,
)
from _plan_parsing import extract_deliverable_headings, parse_document_sections
from constants import FILE_STATUS, FILE_WORK_METRICS, PHASES
from file_ops import (
    PlanNotFoundError,
    atomic_write_file,
    format_duration,
    format_tokens_short,
    get_plan_dir,
    now_utc_iso,
    output_toon,
    require_plan_exists,
    safe_main,
)
from input_validation import (
    add_phase_arg,
    add_plan_id_arg,
    add_session_id_arg,
    is_valid_relative_path,
    parse_args_with_toon_errors,
    require_valid_plan_id,
)
from toon_parser import parse_toon

METRICS_FILE = FILE_WORK_METRICS
METRICS_MD = 'metrics.md'
PHASE_BREAKDOWN_DEFAULT_OUTPUT = 'work/phase-breakdown-output.txt'
PHASE_NAMES = list(PHASES)
ACCUMULATOR_FILE_TEMPLATE = 'work/metrics-accumulator-{phase}.toon'
DISPATCH_BOUNDARY_FILE_TEMPLATE = 'work/metrics-dispatch-boundaries-{phase}.toon'
DISPATCH_TERMINATION_CAUSES = (
    'voluntary_checkpoint',
    'task_complete_returned_verbatim',
    'budget_yield',
    'harness_cancellation',
    'error',
    'clean_exit_queue_empty',
    'step_complete',
    'blocked_user_review',
    'blocked_session_restart',
    'task_batch_complete',
    'agent_returned',
    # A dispatch that returned findings and signalled a loop-back. This is a
    # PRODUCTIVE non-completion — a success of the dispatched step (it examined
    # its surface and filed findings) AND a non-completion of the loop (its
    # findings send control back to an earlier phase). The taxonomy modelled how
    # a dispatch STOPPED but not the verdict a review-shaped dispatch returns, so
    # a findings-bearing loop-back had no member of its own and fell through to
    # `error` — conflating the most productive dispatches with fatal failures.
    # This member is the step-completion `loop_back` outcome's counterpart on the
    # dispatch ledger; the finalize dispatcher stamps it when a dispatched step's
    # `mark-step-done` recorded `outcome: loop_back` (see
    # phase-6-finalize/SKILL.md item 5c).
    'returned_with_findings',
)

# ---------------------------------------------------------------------------
# Per-dispatch context-load columns, and the unmeasured token
# ---------------------------------------------------------------------------
#
# The four per-dispatch context-load columns of the dispatch-boundary row, in
# canonical order. Module-level so the writer's header line, the writer's row
# builder, and the result TOON all read the SAME order — the canonical order /
# count / defaults are owned by ``standards/data-format.md`` (Per-Dispatch
# Context-Load Attribution).
_DISPATCH_CONTEXT_LOAD_COLUMNS = (
    'input_tokens',
    'output_tokens',
    'cache_read_input_tokens',
    'cache_creation_input_tokens',
)

# The literal a context-load column carries when its flag was OMITTED.
#
# These four columns are optional: a caller with no ``message.usage`` figure to
# forward passes no flag. Writing ``0`` for an omitted flag made "the caller
# passed no measurement" and "the dispatch loaded zero context" byte-identical
# rows — the exact conflation this module already forbids for
# ``_PRESENCE_PERSISTED_FIELDS`` under its absent-is-not-zero rule. The row is
# positional, so an unmeasured column cannot simply be dropped; it carries this
# token instead.
#
# The token gives readers a distinction that ``0`` alone destroyed: a measured
# zero is ``0``, a deliberately-unmeasured column is this literal, and any other
# unparseable cell is UNRECOGNISED — reported as such rather than folded into
# either neighbour. One residue the token cannot fix: a literal ``0`` this writer
# wrote BEFORE the token existed is byte-identical to a measured zero, so a reader
# adds a fourth state, INDETERMINATE, for a ``0`` in a row carrying no post-token
# fingerprint (see standards/data-format.md § Per-Dispatch Context-Load
# Attribution, "provenance of a measured zero").
UNMEASURED_COLUMN_TOKEN = 'unmeasured'

# ---------------------------------------------------------------------------
# Cumulative-vs-last-close row scope discriminator
# ---------------------------------------------------------------------------
#
# A phase can close more than once (a finalize loop-back re-enters an earlier
# phase under the same phase key), and ``_close_phase_accumulating`` then SUMS
# some of the row's fields across every close while ASSIGNING others from the
# latest close alone. That split existed only as prose in
# ``standards/data-format.md`` and in two docstrings, so a script consumer
# reading a ``close_count > 1`` row off disk had no field-level signal telling it
# which of the row's values are cumulative and which are last-close.
#
# ``value_scope`` is that signal, and it follows the ``total_tokens_population``
# precedent exactly: a row-level discriminator written at the WRITE site on every
# close, with a documented absent-reads-as default. On a re-entered row it is
# accompanied by ``cumulative_fields`` / ``last_close_fields``, which name the
# split explicitly — so the declaration is readable off the row itself and no
# consumer has to consult ``standards/data-format.md`` to interpret it.
VALUE_SCOPE_SINGLE_CLOSE = 'single_close'
VALUE_SCOPE_MIXED = 'mixed_cumulative_and_last_close'
VALUE_SCOPES = (VALUE_SCOPE_SINGLE_CLOSE, VALUE_SCOPE_MIXED)

# Fields whose value on a re-entered row is the SUM across every close.
_CUMULATIVE_ACROSS_CLOSES_FIELDS = (
    'close_count',
    'duration_seconds',
    'agent_duration_ms',
    'agent_duration_seconds',
    'total_tokens',
    'tool_uses',
    'retrospective_tokens',
)

# Fields scoped to the LATEST close alone — assigned unconditionally, never summed.
_LAST_CLOSE_SCOPED_FIELDS = ('start_time', 'end_time')

# ---------------------------------------------------------------------------
# Denominators, and the sampling-point discriminator
# ---------------------------------------------------------------------------
#
# ``metrics.toon`` persisted NUMERATORS only — ``total_tokens``, ``tool_uses``,
# ``duration_seconds``, ``billing_weighted_total`` — so a script reading it
# supported exactly one verdict: "this got more expensive". Every denominator
# lived outside the record and was re-derived at render time by an LLM, which is
# a figure nobody can check.
#
# Worse than absent, each denominator is a MOVING quantity: ``affected_files``
# grows during execute, the task count grows as fix-tasks are appended, and the
# deliverable count can change on a Q-Gate re-entry. The same numerator over the
# same plan therefore yields different ratios depending on WHEN the denominator
# was read — so a denominator without a stated sampling point is not a fixed
# reference class at all.
#
# The sampling point is therefore a FIELD, not a sentence, and it reuses the
# discriminator convention this module already uses twice
# (``total_tokens_population``, ``value_scope``): a closed value vocabulary, a
# documented absent-reads-as default, and a companion field per measurement. No
# second vocabulary is introduced.
#
# ``generate_time`` is currently the only member: every denominator here is
# counted from live plan state at the instant ``generate`` runs, which the
# record already dates through its own top-level ``updated`` key. A denominator
# whose sampling point cannot be determined is NOT WRITTEN — absent, never
# defaulted and never guessed, per this module's own absent-is-not-zero rule.
SAMPLING_POINT_GENERATE_TIME = 'generate_time'
SAMPLING_POINTS = (SAMPLING_POINT_GENERATE_TIME,)

# The suffix that turns a denominator's name into its sampling-point field.
_SAMPLING_POINT_SUFFIX = '_sampling_point'

# The denominator field names ``cmd_generate`` derives, in write order. Each is
# persisted ONLY together with its ``{name}_sampling_point`` companion — the two
# are written as a pair or not at all, so no reader can find a count whose
# reference moment is unstated.
_DENOMINATOR_FIELDS = ('deliverable_count', 'files_modified', 'tasks_completed')

# ---------------------------------------------------------------------------
# Token population discriminator
# ---------------------------------------------------------------------------
#
# ``total_tokens`` is named for a TOTAL, not for a population, yet the figure it
# carries is filled from two different measurements: a dispatched phase's
# ``<usage>`` envelopes, and — on a phase that dispatched nothing — the inline
# main-context sum that ``cmd_enrich`` folds in. The fold is deliberate and
# stays: it is what keeps an inline phase countable in the breakdown (the report
# reads n=6/6, not n=5/6) and what keeps every downstream zero-token predicate
# off a phase that really did cost something. What must NOT stay implicit is
# that the folded figure measures a DIFFERENT population than the field's name
# implies.
#
# ``total_tokens_population`` is that discriminator, persisted by ``cmd_enrich``
# on every phase row it touches so no render site and no consumer has to infer
# the population from a field name that does not state one.
POPULATION_DISPATCHED = 'dispatched'
POPULATION_INLINE = 'inline'
POPULATION_MIXED = 'mixed'
TOKEN_POPULATIONS = (POPULATION_DISPATCHED, POPULATION_INLINE, POPULATION_MIXED)

# Phase Breakdown ``Tokens`` column header. The header names a DEFAULT
# population plus the marking convention that carries the exceptions — the
# column is not single-population, so a bare ``Tokens (dispatched)`` would
# assert over a mixed column exactly the single-population claim this module
# exists to stop making. A label may state a default only when the exceptions
# are marked per row (``_POPULATION_CELL_SUFFIX``) and the annotation under the
# table declares that default; both hold here.
_TOKENS_COLUMN_HEADER = 'Tokens (dispatched unless marked)'

# Phase Breakdown ``Tokens`` cell suffix per population. ``dispatched`` renders
# bare and is declared as the column's default by the annotation under the
# table: marking every ordinary row would bury the rows that actually differ.
_POPULATION_CELL_SUFFIX = {
    POPULATION_INLINE: ' (inline)',
    POPULATION_MIXED: ' (mixed)',
}

# ``Total`` row ``Tokens`` cell suffix. The Total inherits the column's declared
# default, so a Total fed by an ``(inline)`` row is an exception and must be
# marked like any other: unmarked, it would assert the dispatched total it is
# not. Deliberately NOT ``(mixed)`` — that marker already means something else
# on a phase row (a dispatched cell whose row ALSO recorded inline spend).
_TOTAL_CROSS_POPULATION_SUFFIX = ' (spans populations)'

# ---------------------------------------------------------------------------
# The persisted aggregate — every figure the Total row renders
# ---------------------------------------------------------------------------
#
# The Total row and its ``(n=k/N)`` qualifier were computed at render time and
# written NOWHERE: ``write_metrics`` ran before the row was built, so the store's
# header carried no aggregate at all. The one figure a human quotes, and the
# population qualifier that makes it safe to quote, existed only in prose — a
# script reading the store had to re-sum the rows itself and re-derive a
# population, and could legitimately pick a different one than the renderer did.
# Two producers of one number, one of them unpersisted.
#
# Each column now persists a TRIPLE, and the render reads it back rather than
# keeping a second copy: the value, the count of phase rows that fed it
# (``_POPULATION_COUNT_SUFFIX``), and the shared denominator
# ``_TOTALS_DENOMINATOR_FIELD``. A value without its count cannot state its own
# coverage — the same reason ``dispatch_boundary_rows_recorded`` rides beside
# ``dispatch_boundary_total`` — and a count without its denominator is not a
# population statement. A ``0`` value beside a ``0`` count is therefore legible
# as the empty sum it is, not as a measured zero.
#
# The DURATION columns persist MILLISECONDS, the unit their per-phase operands
# are already held in (``agent_duration_ms`` / ``idle_duration_ms``). Persisting
# rounded seconds would put the store's precision below the render's: at 59.96 s
# a decisecond rounding flips ``format_duration`` from ``60.0s`` to ``1m0s``, so
# the store and the report would disagree about a figure the store exists to
# make checkable.
_TOTALS_FIELDS = {
    'worked': 'totals_worked_ms',
    'wall': 'totals_wall_ms',
    'idle': 'totals_idle_ms',
    'tokens': 'totals_tokens',
    'tool_uses': 'totals_tool_uses',
    'billing': 'totals_billing_weighted_total',
}

#: The columns whose persisted value is a millisecond duration.
_TOTALS_DURATION_COLUMNS = frozenset({'worked', 'wall', 'idle'})

_POPULATION_COUNT_SUFFIX = '_population_count'
_TOTALS_DENOMINATOR_FIELD = 'totals_population_denominator'
_TOTALS_SPANS_POPULATIONS_FIELD = 'totals_tokens_spans_populations'
_BOUNDARY_EXCLUDED_CLASSES_FIELD = 'dispatch_boundary_excluded_classes'

# ---------------------------------------------------------------------------
# Where a phase row's rendered Tokens cell came from
# ---------------------------------------------------------------------------
#
# The reconciliation picks the largest eligible dispatched measure, and the
# render then states WHICH measure won only in an annotation. Persisting the
# provenance turns that sentence into a field: a consumer reading the store can
# tell a cell backed by the recorded ``total_tokens`` from one backed by a
# competing measure, without re-running the comparison or parsing the markdown.
_TOKENS_CELL_SOURCE_FIELD = 'tokens_cell_source'

#: The Tokens cell for a phase that was never closed, carrying its
#: dispatch-boundary sum as a labelled FLOOR. A phase whose terminal close never
#: fired is simultaneously the phase most likely to be missing the marker and the
#: phase most likely to hold the largest figure — the boundary file is the only
#: durable record of what it spent, and dropping it makes a multi-million-token
#: phase render as ``-``.
TOKENS_SOURCE_UNCLOSED_BOUNDARY = 'unclosed_boundary_floor'

#: Its cell suffix. Deliberately NOT a ``TOKEN_POPULATIONS`` member: the figure
#: measures the dispatched population like any other boundary sum. What it
#: qualifies is COVERAGE, not population — this skill consumes the population
#: vocabulary and never extends it.
_UNCLOSED_BOUNDARY_CELL_SUFFIX = ' (boundary floor)'

# The four raw ``message.usage`` fields rendered per phase, with their bullet
# labels, in report order. Module-level so the render loop and the contract test
# read the SAME population: a fifth usage field added here must render under the
# group heading, and cannot slip in unlabelled. All four measure ONE population
# (main-context-window, per the Token-Field Population Lattice), so the group
# heading states that population outright rather than a default-plus-exception —
# there is no exception to mark.
_FOUR_FIELD_USAGE_LABELS = (
    ('input_tokens', 'Input tokens'),
    ('output_tokens', 'Output tokens'),
    ('cache_read_input_tokens', 'Cache read input tokens'),
    ('cache_creation_input_tokens', 'Cache creation input tokens'),
)

# The same four field names without their labels, DERIVED from the tuple above
# so the persist site and the render site walk one population.
#
# ``cmd_enrich``'s persistence loop previously spelled these four out as an
# inline literal. A hardcoded field list cannot drift VISIBLY: a fifth field
# added to ``_FOUR_FIELD_USAGE_LABELS`` would gain a render bullet and a contract
# test while never being persisted at all — and the render's presence guard would
# then read the omission as an absent measurement rather than as a persister that
# never looked. Deriving the loop's population from the canonical declaration is
# what makes adding a field a one-site change.
_FOUR_FIELD_USAGE_FIELDS = tuple(field for field, _label in _FOUR_FIELD_USAGE_LABELS)

_FOUR_FIELD_GROUP_HEADING = (
    '- **Main-context-window usage**: raw `message.usage` summed over this phase\'s parent '
    'turns and the subagent transcripts attributed to the same window. Every bullet below '
    'measures that one population'
)

# Phase Details ``Total tokens`` bullet qualifier per population. Every rendered
# total names its own population, so the bullet stays legible without reading
# the breakdown annotation first.
_POPULATION_BULLET_NOTE = {
    POPULATION_DISPATCHED: (
        "dispatched-subagent population — summed from the dispatched leaves' `<usage>` envelopes"
    ),
    POPULATION_INLINE: (
        'main-context-window population — this phase dispatched nothing, so enrich folded its '
        'inline main-context spend into this field; the same figure is recorded under its own '
        'population-honest name as inline_main_context_tokens'
    ),
    POPULATION_MIXED: (
        'dispatched-subagent population — this phase ALSO ran inline main-context steps, recorded '
        'separately as inline_main_context_tokens and NOT included here; the two populations are '
        'measured by different methods and are not additively comparable'
    ),
}

# The two "unattributed" residuals name the SAME word for two DIFFERENT
# quantities: a byte residual over exploration payload bytes, and a
# cache_read-token residual over the phase's recorded cache_read. They are
# separately computed, have different denominators, and differ materially in
# share — so a render that labelled both "unattributed" would let a consumer read
# one as the other (plan 030 D1). Each entry names the residual's DENOMINATOR
# field, and the render reads that field's value off the SAME row so the share is
# legible in place. Keyed by the persisted field name; every other
# ``_PRESENCE_PERSISTED_FIELDS`` member keeps the generic label. The QUANTITY is
# carried by the label itself (``… exploration bytes`` vs ``… cache_read tokens``)
# so neither figure is ever named merely ``unattributed``.
_UNATTRIBUTED_RENDER = {
    'exploration_unattributed_bytes': (
        'Unattributed exploration bytes',
        'exploration_result_bytes',
        'exploration payload bytes whose call exposed no recoverable target path (fails open here)',
    ),
    'cache_read_unattributed': (
        'Unattributed cache_read tokens',
        'cache_read_input_tokens',
        'cache_read tokens the turn-weighted residency walk could not tie to an observed payload',
    ),
}


def _token_population(phase_row: dict) -> str:
    """Return the population this phase row's ``total_tokens`` figure measures.

    An ABSENT value reads as ``dispatched``. That is the best available default,
    NOT a guarantee the row is dispatched-only: the absent set is wider than the
    never-enriched set. Two distinct rows reach it —

    * a row ``enrich`` never touched, whose ``total_tokens`` can only have come
      from dispatched ``<usage>`` / the accumulator (the default is exact here);
    * a row enriched by a PRE-labelling ``enrich``, which already received the
      inline fold but carries no discriminator (the default under-reports here —
      such a row renders unmarked and its Total takes no ``spans populations``
      marker).

    The second case is unrecoverable without re-enriching a transcript that is
    usually gone, so it is accepted rather than guessed at. Go-forward rows are
    always stamped. An unrecognised value reads as ``dispatched`` too, rather
    than rendering a marker no reader can interpret.
    """
    value = phase_row.get('total_tokens_population')
    return value if value in TOKEN_POPULATIONS else POPULATION_DISPATCHED


# ---------------------------------------------------------------------------
# Dispatched-population reconciliation
# ---------------------------------------------------------------------------
#
# THREE fields measure the same dispatched-subagent population by three
# independent routes, and they routinely disagree:
#
#   total_tokens           forwarded `<usage>` / the per-phase accumulator
#   dispatch_boundary_total sum of the per-dispatch boundary rows
#   subagent_total_tokens   enrich's post-hoc transcript walk
#
# Because they count the SAME leaves, they are reconciled by max(), never summed
# — a sum double-counts every leaf. The maximum recovers whichever route
# under-counted (#565: a leaf whose boundary row fired but whose accumulator fold
# was missed).
#
# The rule is applied SYMMETRICALLY to all three or to none. Comparing only two
# of them let the third exceed the rendered figure with the report never saying
# so. Two eligibility rules keep the comparison honest:
#
#   * A measure whose coverage is not exact may not win. Only
#     `dispatch_boundary_total` can diverge from `subagent_samples` (its file may
#     hold fewer rows than the phase had dispatches — PARTIAL, a floor — or, across
#     a resume/re-entry, MORE rows than were sampled — OVER, an impossible /
#     inflated figure). It is refused the maximum in BOTH cases; only an exact or
#     coverage-undecidable measure competes (see `_boundary_coverage_state`).
#   * A measure of a DIFFERENT population may not enter at all. On an `inline`
#     row `total_tokens` carries a main-context measurement (see
#     `_token_population`), so it is excluded — putting it in a
#     dispatched-population max would be the very mislabel the discriminator
#     exists to prevent.
_DISPATCHED_MEASURE_FIELDS = (
    'total_tokens',
    'dispatch_boundary_total',
    'subagent_total_tokens',
)

# ---------------------------------------------------------------------------
# The declared dispatch-boundary population — the classes it excludes
# ---------------------------------------------------------------------------
#
# ``dispatch_boundary_rows_recorded`` counts only the dispatches that call
# ``record-dispatch-boundary``. That call is issued from a SUBSET of the dispatch
# classes the orchestrator spawns, so the boundary population is a DECLARED SUBSET
# of the dispatched population ``enrich`` samples as ``subagent_samples`` — never
# the whole of it. The classes below register NO boundary; a
# ``dispatch_boundary_rows_recorded < subagent_samples`` shortfall is expected for
# exactly these classes. NAMING them is what turns a silent denominator gap into a
# declared exclusion — an un-named omission is indistinguishable from a class that
# did not run.
#
# Derived from the DISPATCHING code — the call graph in
# ``ref-workflow-architecture/standards/call-graph.md`` and the
# ``record-dispatch-boundary`` call sites in the phase workflow docs
# (``workflow/execution.md`` → 5-execute, ``workflow/planning-outline.md`` →
# 4-plan, ``phase-6-finalize/SKILL.md`` → 6-finalize) — NOT from any single run's
# emitted classes, which by construction cannot contain a class that never
# registers. Of the 9 dispatch classes the call graph enumerates, 3 register a
# boundary (phase-4-plan, phase-5-execute, phase-6-finalize); the 6 below do not.
DISPATCH_BOUNDARY_EXCLUDED_CLASSES = (
    'phase-2-refine',        # main envelope dispatch; issues no record-dispatch-boundary
    'phase-3-outline',       # main envelope dispatch; issues no record-dispatch-boundary
    'q-gate-validation',     # shared Q-Gate dispatch (fires from 2-refine / 3-outline / 4-plan)
    'verification-feedback', # shared triage dispatch (fires from 5-execute / 6-finalize)
    'research',              # ad-hoc research dispatch (any phase)
    'enrich-module',         # 6-finalize architecture-refresh parallel dispatch
)


def _boundary_coverage_state(phase_row: dict) -> str | None:
    """Classify ``dispatch_boundary_total``'s coverage against ``subagent_samples``.

    The two counts are produced by DIFFERENT mechanisms, so a coverage ratio only
    holds when both measure one population:

    - numerator ``dispatch_boundary_rows_recorded`` — the number of rows the
      boundary-file writer (``record-dispatch-boundary``) appended for this phase;
    - denominator ``subagent_samples`` — the count of dispatch returns
      ``enrich``'s transcript walk attributed to the phase window.

    Returns one of four commensurability outcomes:

    - ``None`` (UNDECIDABLE) — the row carries no ``subagent_samples``, so there is
      no reference count. Deliberately NOT partial: treating it as partial would
      refuse the maximum on every un-enriched plan and lose the accumulator-
      under-count recovery the reconciliation exists for.
    - ``'partial'`` — ``rows < samples``. The boundary file covers fewer dispatches
      than ``enrich`` sampled; the sum is a floor. Expected for the declared
      exclusion classes (see ``DISPATCH_BOUNDARY_EXCLUDED_CLASSES``).
    - ``'exact'`` — ``rows == samples``. The two independent counts agree.
    - ``'over'`` — ``rows > samples``. IMPOSSIBLE for a single population: the
      numerator exceeds the denominator. The two counts are drawn from different
      populations (e.g. a resumed / re-entered phase appends boundary rows the
      single-window ``enrich`` walk never re-counts), so this is not a coverage
      ratio at all — a loud failure, never ``complete``.
    """
    samples = phase_row.get('subagent_samples')
    if not isinstance(samples, int):
        return None
    rows = phase_row.get('dispatch_boundary_rows_recorded')
    if not isinstance(rows, int):
        return None
    if rows < samples:
        return 'partial'
    if rows > samples:
        return 'over'
    return 'exact'


def _boundary_measure_is_partial(phase_row: dict) -> bool | None:
    """Does ``dispatch_boundary_total`` under-cover the phase's dispatches?

    Thin wrapper over :func:`_boundary_coverage_state` preserved for callers that
    only need the under-coverage bit: ``True`` for ``'partial'``, ``False`` for
    ``'exact'`` / ``'over'`` (an over-covering measure is not *under*-covering),
    ``None`` when coverage is undecidable.
    """
    state = _boundary_coverage_state(phase_row)
    if state is None:
        return None
    return state == 'partial'


def _eligible_dispatched_measures(phase_row: dict) -> list[tuple[str, int]]:
    """Return the dispatched-population measures eligible for the maximum.

    Preserves ``_DISPATCHED_MEASURE_FIELDS`` order so an exact tie resolves
    deterministically to the earliest-declared measure.
    """
    population = _token_population(phase_row)
    boundary_state = _boundary_coverage_state(phase_row)

    eligible: list[tuple[str, int]] = []
    for field in _DISPATCHED_MEASURE_FIELDS:
        value = _coerce_numeric(phase_row.get(field))
        if not isinstance(value, (int, float)) or not value:
            continue
        if field == 'total_tokens' and population == POPULATION_INLINE:
            continue
        # A boundary sum is refused the maximum when it cannot be trusted as a
        # competing measurement: PARTIAL (a floor — fewer rows than dispatches) or
        # OVER (impossible — more rows than dispatches, so an inflated / double-
        # counted figure across a resume boundary). Only a coverage-decidable,
        # non-over measure competes.
        if field == 'dispatch_boundary_total' and boundary_state in ('partial', 'over'):
            continue
        eligible.append((field, int(value)))
    return eligible


def _reconcile_dispatched_measures(phase_row: dict) -> tuple[str, int] | None:
    """Return the ``(field, value)`` of the largest eligible dispatched measure.

    ``None`` when no measure is eligible — the inline-only row, whose single
    token figure belongs to another population and is rendered on its own.
    """
    eligible = _eligible_dispatched_measures(phase_row)
    if not eligible:
        return None
    return max(eligible, key=lambda item: item[1])


def _unclosed_boundary_floor(phase_row: dict) -> int | None:
    """Return the boundary sum a NEVER-CLOSED phase can still account for.

    A phase's recorded status is keyed solely off its ``end_time``, and that
    marker is stamped by the terminal close. The final phase is therefore both
    the one most likely to be missing it and the one most likely to hold the
    largest figure — and its ``work/metrics-dispatch-boundaries-{phase}.toon``
    file has been accumulating a row per dispatch the whole time, independent of
    whether the boundary ever closed.

    So when the row carries no ``end_time`` but does carry a
    ``dispatch_boundary_total``, that sum is folded into the phase's Tokens cell
    as a LABELLED floor. This is the same move ``enrich`` already makes when it
    folds inline main-context spend into a zero-dispatch phase's total and labels
    the row's population — same reason (a real cost that would otherwise render
    as nothing), applied to the dispatched population instead of the inline one.

    ⛔ The fold is deliberately scoped to the TOKEN figure. The phase keeps its
    place in ``phases_missing_end_time`` and its duration stays absent, because
    the boundary file records per-dispatch spans and cannot honestly supply a
    phase wall-clock the close never stamped.

    Returns:
        The boundary sum for an unclosed phase that recorded one, else ``None``.
    """
    if phase_row.get('end_time'):
        return None
    boundary_total = _coerce_numeric(phase_row.get('dispatch_boundary_total'))
    if not isinstance(boundary_total, (int, float)) or not boundary_total:
        return None
    return int(boundary_total)


def _reconciliation_relation_clause(value: int, beaten: int | None) -> str:
    """Render the TRUE relation of a winning measure to the ``total_tokens`` it met.

    The winning measure is compared against ``beaten`` (the row's recorded
    ``total_tokens``) and annotated with the relation that actually holds:

    - ``value > beaten`` → ``(> total_tokens N)`` — the measure recovered an
      under-count in ``total_tokens``.
    - ``value == beaten`` → ``(= total_tokens N; measures agree)`` — the
      reconciliation IDENTITY: two independent producers agree exactly. This is
      the single most valuable signal the surface emits; a strict ``>`` here would
      tell the reader the ledger under-counted when it agreed.
    - ``value < beaten`` → ``(< total_tokens N)`` — a genuine anomaly (the winner
      is below the total it was compared against), never dressed up as agreement.
    - ``beaten is None`` → ``(no recorded total_tokens)`` — nothing to compare.
    """
    if beaten is None:
        return ' (no recorded total_tokens)'
    if value > beaten:
        return f' (> total_tokens {beaten:,})'
    if value == beaten:
        return f' (= total_tokens {beaten:,}; measures agree)'
    return f' (< total_tokens {beaten:,})'


def _accumulator_path(plan_id: str, phase: str) -> Path:
    return get_plan_dir(plan_id) / ACCUMULATOR_FILE_TEMPLATE.format(phase=phase)


def _read_accumulator(plan_id: str, phase: str) -> dict[str, int]:
    """Read per-phase subagent-usage accumulator. Returns empty dict if absent or unparsable."""
    path = _accumulator_path(plan_id, phase)
    if not path.exists():
        return {}
    result: dict[str, int] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or ':' not in stripped:
            continue
        key, _, raw_val = stripped.partition(':')
        key = key.strip()
        if key not in {'total_tokens', 'tool_uses', 'duration_ms', 'samples', 'retrospective_tokens'}:
            continue
        try:
            result[key] = int(raw_val.strip())
        except ValueError:
            continue
    return result


def _write_accumulator(plan_id: str, phase: str, totals: dict[str, int]) -> None:
    path = _accumulator_path(plan_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f'plan_id: {plan_id}',
        f'phase: {phase}',
        f'total_tokens: {totals["total_tokens"]}',
        f'tool_uses: {totals["tool_uses"]}',
        f'duration_ms: {totals["duration_ms"]}',
        f'retrospective_tokens: {totals["retrospective_tokens"]}',
        f'samples: {totals["samples"]}',
        f'updated: {now_utc_iso()}',
    ]
    atomic_write_file(path, '\n'.join(lines) + '\n')


def _read_dispatch_boundary_totals(plan_id: str, phase: str) -> tuple[int, int]:
    """Sum the ``total_tokens`` column across a phase's dispatch-boundaries file.

    The dispatch-boundaries file (``work/metrics-dispatch-boundaries-{phase}.toon``)
    records one row per phase Task-dispatch termination, each carrying the
    dispatched agent's ``<usage>`` totals at return (see the writer in
    ``cmd_record_dispatch_boundary``). This reader sums the ``total_tokens``
    column — position 2 in the documented row schema
    ``rows[]{timestamp,termination_cause,total_tokens,...}`` — across every data
    row. The two header lines (``plan_id:`` / ``phase:``), the ``rows[]`` schema
    line, and any malformed / short row are skipped.

    Returns ``(total, rows_counted)``. The row count is returned alongside the
    sum because the sum ALONE cannot state its own coverage: a boundary file
    holding three of a phase's five dispatches sums to a smaller-but-honest-looking
    figure, and without the count nothing downstream can tell that measure apart
    from a complete one. ``rows_counted`` is what lets the reconciliation classify
    the measure's coverage (PARTIAL / exact / OVER) and refuse a partial or
    over-covering measure the maximum (see ``_boundary_coverage_state``).

    Returns ``(0, 0)`` when the file is absent, empty, or carries no parseable
    row — the caller (``cmd_generate``) treats that as a clean no-op, so a plan
    that never recorded a dispatch boundary reconciles to nothing.

    Args:
        plan_id: Plan identifier.
        phase: Canonical phase name whose boundaries file is summed.

    Returns:
        ``(summed total_tokens, number of data rows summed)``.
    """
    path = _dispatch_boundary_path(plan_id, phase)
    if not path.exists():
        return 0, 0
    total = 0
    rows = 0
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(('plan_id:', 'phase:', 'rows[]')):
            continue
        columns = stripped.split(',')
        if len(columns) < 3:
            continue
        try:
            total += int(columns[2].strip())
        except ValueError:
            continue
        rows += 1
    return total, rows


def _resolve_token_field(
    arg_value: int | None, accumulator: dict[str, int], key: str
) -> tuple[int | None, str | None]:
    """Resolve a usage field to its value AND its provenance.

    Explicit flag wins; fall back to the accumulator value when the flag is
    absent. The provenance half is what makes correct accumulation expressible
    at the write site, because the two sources carry different arithmetic:

    - ``'flag'`` — an explicit ``--total-tokens``-style value is a **per-close
      delta**. On a phase re-entry it must be ADDED to whatever the row already
      holds (see ``_apply_provenance``).
    - ``'accumulator'`` — the on-disk per-phase accumulator is **already
      cumulative** (``cmd_accumulate_agent_usage`` only ever sums and no verb
      resets it), so it must be ASSIGNED unchanged. Adding it would double-count
      every re-close.

    Returns:
        ``(value, source)`` where ``source`` is ``'flag'`` or ``'accumulator'``;
        ``(None, None)`` when neither source carries the field, which the write
        sites treat as "leave the row untouched" (never write a ``0``).
    """
    if arg_value is not None:
        return arg_value, 'flag'
    if key in accumulator:
        return accumulator[key], 'accumulator'
    return None, None


def _row_int(phase_data: dict, key: str) -> int:
    """Return a phase row's integer field, treating absent / non-numeric as 0."""
    value = phase_data.get(key)
    return int(value) if isinstance(value, (int, float)) else 0


def _apply_provenance(phase_data: dict, row_key: str, value: int, source: str | None) -> int:
    """Combine a resolved usage value with the row's existing value by provenance.

    The accumulate-on-re-entry rule for the token/tool fields: a ``'flag'``-sourced
    value is a per-close delta and is added to what the row already holds (absent
    treated as 0); any other provenance (``'accumulator'``) is already the
    cumulative total and is returned unchanged. Callers assign the result.
    """
    if source == 'flag':
        return _row_int(phase_data, row_key) + value
    return value


def _increment_close_count(phase_data: dict) -> None:
    """Record one more close of this phase row (absent ⇒ 0).

    ``close_count > 1`` is the inference-free re-entry marker: it is written at
    the write site on every close, so it never has to be inferred from timestamp
    ordering the way ``cmd_generate``'s ``boundary_monotonicity`` detector does.
    """
    phase_data['close_count'] = _row_int(phase_data, 'close_count') + 1


def _stamp_value_scope(phase_data: dict) -> None:
    """Declare on the row which of its values are cumulative and which are last-close.

    Written by ``_close_phase_accumulating`` on EVERY close, after every other
    field write, so the two field lists name only keys the row actually carries —
    a declaration that named an absent field would assert a value the row does
    not hold.

    - ``close_count <= 1`` → ``value_scope: single_close``. The split is vacuous
      (every value covers the one and only close), so the two list fields are
      NOT written, and any left over from a prior state are removed.
    - ``close_count > 1`` → ``value_scope: mixed_cumulative_and_last_close``,
      plus ``cumulative_fields`` / ``last_close_fields`` naming the split.

    **Absent reads as ``single_close``** — the best available default, NOT a
    guarantee, and the same honest-default shape ``_token_population`` documents.
    Two distinct rows reach the absent state: a row written before this
    discriminator existed whose ``close_count`` is 1 (the default is exact), and
    a pre-stamping re-entered row carrying ``close_count > 1`` (the default
    under-reports). A consumer that has ``close_count`` on the row SHOULD prefer
    it — ``close_count > 1`` is the authoritative re-entry marker; ``value_scope``
    exists to say what that re-entry did to the row's individual fields.
    """
    if _row_int(phase_data, 'close_count') > 1:
        phase_data['value_scope'] = VALUE_SCOPE_MIXED
        phase_data['cumulative_fields'] = ','.join(
            field for field in _CUMULATIVE_ACROSS_CLOSES_FIELDS if field in phase_data
        )
        phase_data['last_close_fields'] = ','.join(
            field for field in _LAST_CLOSE_SCOPED_FIELDS if field in phase_data
        )
        return
    phase_data['value_scope'] = VALUE_SCOPE_SINGLE_CLOSE
    phase_data.pop('cumulative_fields', None)
    phase_data.pop('last_close_fields', None)


def _guard_plan_exists(plan_id: str) -> dict | None:
    """Return a ``plan_not_found`` error dict when the plan dir is uninitialised.

    Plan-scoped writers in this module reach the plan directory through
    ``get_plan_dir`` and then ``mkdir(parents=True, ...)`` (directly or via
    ``atomic_write_file``). Without this guard a stray ``--plan-id`` for a plan
    that phase-1 never initialised silently creates an orphan plan tree just to
    hold a metrics artifact. Calling ``require_plan_exists`` first turns that
    silent side effect into a structured error.

    Returns ``None`` when the plan exists (caller proceeds); returns the error
    dict to be emitted verbatim when it does not. The error shape mirrors
    ``cmd_record_dispatch_boundary`` so every writer reports the same contract.
    """
    try:
        require_plan_exists(plan_id)
    except PlanNotFoundError as exc:
        return {
            'status': 'error',
            'error': 'plan_not_found',
            'message': str(exc),
            'plan_id': plan_id,
            'plan_dir': str(exc.plan_dir),
        }
    return None


def _coerce_numeric(value: object) -> int | float | str:
    """Try to coerce a value to int, then float, falling back to the original value."""
    if not isinstance(value, str):
        return value  # type: ignore[return-value]
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    try:
        return float(value)
    except (ValueError, TypeError):
        pass
    return value


# get_plan_dir imported from file_ops


def write_metrics(plan_id: str, data: dict) -> None:
    metrics_path = get_plan_dir(plan_id) / METRICS_FILE
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f'plan_id: {plan_id}')
    if 'updated' in data:
        lines.append(f'updated: {data["updated"]}')
    # Preserve any other top-level keys round-tripped from read_metrics_raw.
    # read_metrics_raw accepts arbitrary top-level keys (lines before the first
    # [phase] block); write_metrics must emit them back so cmd_generate's
    # read -> mutate -> write loop stays lossless over the full key set.
    for extra_key, extra_val in data.items():
        if extra_key in ('plan_id', 'updated', 'phases'):
            continue
        lines.append(f'{extra_key}: {extra_val}')
    lines.append('')

    phases = data.get('phases', {})
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        lines.append(f'[{phase_name}]')
        for key, val in phase.items():
            lines.append(f'  {key}: {val}')
        lines.append('')

    atomic_write_file(metrics_path, '\n'.join(lines) + '\n')


def read_metrics_raw(plan_id: str) -> dict:
    """Read metrics from custom TOON-like format."""
    metrics_path = get_plan_dir(plan_id) / METRICS_FILE
    if not metrics_path.exists():
        return {'phases': {}}

    content = metrics_path.read_text(encoding='utf-8')
    if not content.strip():
        return {'phases': {}}

    data: dict[str, object] = {'phases': {}}
    current_phase: str | None = None
    phases: dict[str, dict[str, object]] = {}

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('[') and stripped.endswith(']'):
            current_phase = stripped[1:-1]
            phases[current_phase] = {}
        elif current_phase and ':' in stripped:
            key, _, raw_val = stripped.partition(':')
            parsed_val: object = raw_val.strip()
            # Try numeric conversion
            try:
                parsed_val = int(raw_val.strip())
            except (ValueError, TypeError):
                try:
                    parsed_val = float(raw_val.strip())
                except (ValueError, TypeError):
                    pass
            phases[current_phase][key.strip()] = parsed_val
        elif not current_phase and ':' in stripped:
            key, _, raw_val = stripped.partition(':')
            data[key.strip()] = raw_val.strip()

    data['phases'] = phases

    return data


def cmd_start_phase(args: argparse.Namespace) -> dict:
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid phase: {phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    data = read_metrics_raw(plan_id)
    now = now_utc_iso()

    if phase not in data['phases']:
        data['phases'][phase] = {}

    data['phases'][phase]['start_time'] = now
    data['updated'] = now

    write_metrics(plan_id, data)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'start_time': now,
    }


def _clamp_worked_to_wall(phase_data: dict, duration_ms: int) -> int:
    """Bound the agent's worked window to the phase's recorded wall-clock span.

    No single agent can work longer than the phase's own wall-clock span, yet the
    1-init bootstrap ordering (`status.json.created` written *after* the init
    agent began working) can forward a `duration_ms` that exceeds the
    `created → end_time` wall-clock window, persisting a structurally-impossible
    ``agent_duration_seconds > duration_seconds`` row. When ``duration_seconds`` is
    present, clamp the worked value to it so the per-phase ``Worked <= Reported
    (wall)`` invariant always holds; otherwise return the value unchanged. The
    clamp only ever bounds — it never inflates a worked value below the wall span.

    Re-entry carries no carve-out here: this function bounds whatever value it is
    handed against whatever ``duration_seconds`` the row holds. On a re-entered
    phase the caller hands it the **summed** worked value and the row already
    holds the **accumulated** wall span, so the invariant survives accumulation
    without any special case. That ordering is the caller's obligation — clamping
    a per-close delta and adding the clamped result to an already-clamped value
    can sum past the accumulated wall span; see ``cmd_end_phase`` /
    ``cmd_phase_boundary``, which accumulate first and clamp the sum.
    """
    wall_seconds = phase_data.get('duration_seconds')
    if isinstance(wall_seconds, (int, float)):
        return min(duration_ms, int(round(float(wall_seconds) * 1000.0)))
    return duration_ms


def _accumulate_duration_seconds(phase_data: dict, prior_end_time: object, end_now: str) -> None:
    """Add this close's active wall span onto the row's ``duration_seconds``.

    ``duration_seconds`` carries no flag-vs-accumulator provenance — both writers
    compute it inline — so it is an unconditional add of a per-close **active
    span** rather than a provenance-keyed decision. The span runs from
    ``max(start_time, prior_end_time)`` to ``end_now``, which makes all three
    close shapes correct with one rule:

    - **First close** — ``prior_end_time`` is absent, so the anchor is
      ``start_time`` and the existing value is 0: byte-identical to a plain
      ``end_time - start_time`` assignment.
    - **Loop-back re-entry** — ``start_phase`` re-stamped a later ``start_time``,
      so it wins the ``max`` and only the new entry's span is added.
    - **Bare second close** (no intervening ``start-phase``) — the stale
      ``start_time`` loses to ``prior_end_time``, so only the genuinely-new span
      is added instead of double-counting the first entry.

    The accumulated value is the phase's total *active* wall time; it therefore
    deliberately does not satisfy ``duration_seconds == end_time - start_time`` on
    a re-entered row (``start_time`` stays re-entry-scoped). Unparseable
    timestamps leave the field untouched rather than writing a partial value.

    Args:
        phase_data: The phase row, mutated in place.
        prior_end_time: The row's ``end_time`` as captured BEFORE this close
            overwrote it, or a falsy value on a first close.
        end_now: This close's ``end_time`` ISO timestamp.
    """
    start_str = phase_data.get('start_time')
    if not start_str:
        return
    try:
        anchor_dt = datetime.fromisoformat(str(start_str))
        end_dt = datetime.fromisoformat(end_now)
        if prior_end_time:
            prior_dt = datetime.fromisoformat(str(prior_end_time))
            anchor_dt = max(anchor_dt, prior_dt)
        span_s = (end_dt - anchor_dt).total_seconds()
    except (ValueError, TypeError):
        return
    existing = phase_data.get('duration_seconds')
    base = float(existing) if isinstance(existing, (int, float)) else 0.0
    phase_data['duration_seconds'] = round(base + span_s, 1)


def _reconcile_accumulator_into_phase(phase_data: dict, accumulator: dict[str, int]) -> None:
    """Fold a phase's durable accumulator totals into its metrics row in place.

    The per-phase accumulator (``work/metrics-accumulator-{phase}.toon``) is the
    durable snapshot written after every subagent return. When a phase row was
    never closed by ``end-phase`` / ``phase-boundary`` — the terminal-phase gap
    where ``6-finalize`` accrued tokens but ``record-metrics`` never ran to fold
    them in — its accumulated totals would otherwise be dropped from the
    generated report. This helper backfills the row from the accumulator so the
    snapshot survives.

    Explicit-wins precedence: a field already present on the row (recorded by
    ``end-phase`` / ``phase-boundary``) is NEVER overwritten — only absent
    fields are backfilled, and only from a truthy accumulator value. Closed rows
    are therefore byte-identical to before. The accumulator's ``duration_ms`` is
    folded as ``agent_duration_ms`` (mirroring ``cmd_end_phase``): it is clamped
    to the phase wall-clock span and the derived ``agent_duration_seconds`` is
    written alongside it.
    """
    if not accumulator:
        return

    acc_tokens = accumulator.get('total_tokens')
    if acc_tokens and 'total_tokens' not in phase_data:
        phase_data['total_tokens'] = acc_tokens

    acc_tool_uses = accumulator.get('tool_uses')
    if acc_tool_uses and 'tool_uses' not in phase_data:
        phase_data['tool_uses'] = acc_tool_uses

    acc_duration_ms = accumulator.get('duration_ms')
    if acc_duration_ms and 'agent_duration_ms' not in phase_data:
        clamped = _clamp_worked_to_wall(phase_data, acc_duration_ms)
        phase_data['agent_duration_ms'] = clamped
        phase_data['agent_duration_seconds'] = round(clamped / 1000.0, 1)


def _close_phase_accumulating(
    phase_data: dict, plan_id: str, phase: str, args: argparse.Namespace, now: str
) -> dict[str, object]:
    """Close one phase row for one call, accumulating per-close totals onto it.

    Shared by ``cmd_end_phase`` and the phase-closing half of
    ``cmd_phase_boundary`` — both close a phase under the identical
    accumulate-on-re-entry contract. A phase can legitimately close more than
    once (a finalize loop-back re-enters an earlier phase under the same phase
    key), so this writer ACCUMULATES rather than replaces. Three distinct rules
    apply, because the fields do not share one arithmetic:

    - **Rule A (provenance-keyed)** for ``total_tokens``, ``tool_uses``,
      ``retrospective_tokens``, and the resolved worked ``duration_ms``: a
      ``'flag'``-sourced value is a per-close delta and is added to the row; an
      ``'accumulator'``-sourced value is already cumulative and is assigned. An
      unresolved field leaves the row untouched — never writes a ``0``.
    - **Rule B** for ``duration_seconds``: an unconditional add of this close's
      active span, anchored at ``max(start_time, prior_end_time)`` — see
      ``_accumulate_duration_seconds``.
    - **Rule C** for ``agent_duration_ms``: accumulate first, then clamp the SUM
      against the accumulated wall span, which keeps ``Worked <= Reported
      (wall)`` intact with no re-entry carve-out inside
      ``_clamp_worked_to_wall``.

    ``close_count`` is incremented on every close, making ``close_count > 1`` the
    inference-free re-entry marker ``cmd_generate`` renders. The three rules'
    consequence for the row — which fields the close SUMMED and which it
    REPLACED — is stamped onto the row itself by ``_stamp_value_scope`` as the
    last write of this function, so a consumer reading a re-entered row off disk
    gets the split without consulting ``standards/data-format.md``. Mutates
    ``phase_data`` in place; the caller stamps its own result dict from the
    mutated row plus the returned pre-provenance values.

    Returns:
        A dict with ``total_tokens`` / ``retrospective_tokens`` (the
        pre-provenance resolved values, ``None``/falsy when unresolved — callers
        use these to decide whether to surface the row's accumulated value in
        their own result) and ``accumulator`` (the on-disk accumulator dict,
        used to decide ``accumulator_used``).
    """
    # Capture the row's prior end_time BEFORE the unconditional stamp below
    # overwrites it — it is the active-span anchor for a close that follows an
    # earlier close with no intervening start-phase (see
    # _accumulate_duration_seconds).
    prior_end_time = phase_data.get('end_time')
    # Stamp end_time unconditionally: it is the sole marker cmd_generate's
    # end_time-presence check reads. An inline phase closes here with the usage
    # flags omitted (no agent <usage> envelope) and still carries the marker —
    # so it is never listed under phases_missing_end_time.
    phase_data['end_time'] = now

    # Rule B: add this close's active wall span onto duration_seconds. Must run
    # BEFORE the clamp below, which reads the accumulated span as its ceiling.
    _accumulate_duration_seconds(phase_data, prior_end_time, now)
    _increment_close_count(phase_data)

    # Read on-disk accumulator as fallback when explicit flags are absent.
    accumulator = _read_accumulator(plan_id, phase)
    duration_ms, duration_ms_source = _resolve_token_field(args.duration_ms, accumulator, 'duration_ms')
    total_tokens, total_tokens_source = _resolve_token_field(args.total_tokens, accumulator, 'total_tokens')
    tool_uses, tool_uses_source = _resolve_token_field(args.tool_uses, accumulator, 'tool_uses')

    # Rule C: accumulate the worked value first, then clamp the SUM against the
    # accumulated wall span — never clamp the delta and add it to an
    # already-clamped value, which can sum past that span.
    if duration_ms is not None:
        worked_total = _apply_provenance(phase_data, 'agent_duration_ms', duration_ms, duration_ms_source)
        worked_total = _clamp_worked_to_wall(phase_data, worked_total)
        phase_data['agent_duration_ms'] = worked_total
        phase_data['agent_duration_seconds'] = round(worked_total / 1000.0, 1)

    if total_tokens is not None:
        phase_data['total_tokens'] = _apply_provenance(
            phase_data, 'total_tokens', total_tokens, total_tokens_source
        )

    if tool_uses is not None:
        phase_data['tool_uses'] = _apply_provenance(phase_data, 'tool_uses', tool_uses, tool_uses_source)

    # Plan-retrospective spend attribution (default-absent): records the token
    # total attributable to the plan-retrospective dispatch within this phase
    # window. The retrospective dispatches under `--phase phase-6-finalize`, so
    # its spend is otherwise folded into the `[6-finalize]` total with no
    # separator. The audit's three metrics-related checks read this field to
    # exclude deliberate-analysis spend; plans archived before the producer
    # wiring landed simply lack it. The explicit `--retrospective-tokens` flag
    # is the override; absent it the value is read back from the accumulator
    # that the finalize retrospective step seeded via accumulate-agent-usage.
    retrospective_tokens, retrospective_tokens_source = _resolve_token_field(
        args.retrospective_tokens, accumulator, 'retrospective_tokens'
    )
    if retrospective_tokens:
        phase_data['retrospective_tokens'] = _apply_provenance(
            phase_data, 'retrospective_tokens', retrospective_tokens, retrospective_tokens_source
        )

    # LAST write of this function, deliberately: the declaration names only the
    # fields the row actually carries, so it must run after every field write
    # above.
    _stamp_value_scope(phase_data)

    return {
        'total_tokens': total_tokens,
        'retrospective_tokens': retrospective_tokens,
        'accumulator': accumulator,
    }


def cmd_end_phase(args: argparse.Namespace) -> dict:
    """Close a phase, accumulating its per-close totals onto the existing row.

    See ``_close_phase_accumulating`` for the authoritative statement of the
    three accumulate-on-re-entry rules this delegates to.
    """
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        return {'status': 'error', 'error': 'invalid_phase', 'message': f'Invalid phase: {phase}'}

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    data = read_metrics_raw(plan_id)
    now = now_utc_iso()

    if phase not in data['phases']:
        data['phases'][phase] = {}

    phase_data = data['phases'][phase]
    closed = _close_phase_accumulating(phase_data, plan_id, phase, args, now)
    total_tokens = closed['total_tokens']
    retrospective_tokens = closed['retrospective_tokens']
    accumulator = closed['accumulator']

    data['updated'] = now
    write_metrics(plan_id, data)

    result = {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'end_time': now,
        'close_count': phase_data['close_count'],
    }
    if 'duration_seconds' in phase_data:
        result['duration_seconds'] = phase_data['duration_seconds']
    if total_tokens is not None:
        result['total_tokens'] = phase_data['total_tokens']
    if retrospective_tokens:
        result['retrospective_tokens'] = phase_data['retrospective_tokens']
    if accumulator and args.total_tokens is None:
        result['accumulator_used'] = True

    return result


def _wall_clock_ms(phase: dict) -> int | None:
    """Return the wall-clock duration of a phase in milliseconds, or None.

    Prefers the persisted ``duration_seconds`` field; when absent, derives the
    span from ``start_time``/``end_time`` ISO timestamps. Returns None when no
    wall-clock signal is available.

    The timestamp-derived branch is a **first-entry-only approximation**, NOT an
    equivalent definition of the persisted field. ``duration_seconds`` accumulates
    every close's active span while ``start_time`` stays re-entry-scoped, so on a
    ``close_count > 1`` row the two disagree by the gap spent in another phase.
    The approximation is nonetheless safe here because it fires only when
    ``duration_seconds`` is absent, and an accumulated row always carries it — so
    the two branches can never disagree about the same row.
    """
    duration_seconds = phase.get('duration_seconds')
    if isinstance(duration_seconds, (int, float)):
        return int(round(float(duration_seconds) * 1000.0))
    start_str = phase.get('start_time')
    end_str = phase.get('end_time')
    if start_str and end_str:
        try:
            start_dt = datetime.fromisoformat(str(start_str).strip().replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(str(end_str).strip().replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
        return int(round((end_dt - start_dt).total_seconds() * 1000.0))
    return None


def _worked_ms(phase: dict) -> int:
    """Return worked time in ms: max(agent_duration_ms, subagent_duration_ms).

    Missing operands are treated as 0. Worked time is the effort actually spent
    on this phase. When a main-context (orchestrating) turn dispatches a
    subagent, the subagent's wall span overlaps with the orchestrator's own
    wall span — the orchestrator is awaiting the subagent return, not doing
    independent compute. Summing the two values double-counts that overlap and
    can produce `Worked > Reported (wall)`, which breaks the per-phase
    Worked <= wall invariant.

    The non-double-counting definition: take the maximum of the two attribution
    sources. When only one is present, that value wins. When both are present,
    the longer span subsumes the shorter overlap. The result is bounded above
    by the per-phase wall clock for any phase whose subagent dispatches stay
    within the phase window, so the Idle = max(0, wall - worked) residual is
    non-negative and meaningful.
    """
    agent = phase.get('agent_duration_ms')
    subagent = phase.get('subagent_duration_ms')
    agent_ms = int(agent) if isinstance(agent, (int, float)) else 0
    subagent_ms = int(subagent) if isinstance(subagent, (int, float)) else 0
    return max(agent_ms, subagent_ms)


def _parse_iso(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp string to a datetime, tolerating a ``Z`` suffix.

    Returns ``None`` for a missing / non-string / unparseable value so callers can
    skip a phase whose boundary timestamp was never recorded.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


def cmd_generate(args: argparse.Namespace) -> dict:
    plan_id = require_valid_plan_id(args)

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    data = read_metrics_raw(plan_id)
    phases = data.get('phases', {})

    if not phases:
        return {'status': 'error', 'error': 'no_data', 'message': 'No metrics data found'}

    # Reconcile each canonical phase against its durable on-disk accumulator
    # BEFORE deriving idle and rendering. A phase row that was never closed by
    # end-phase / phase-boundary (e.g. a 6-finalize interrupted, looped-back, or
    # never reaching record-metrics) still surfaces its accrued tokens because
    # the accumulator is the durable snapshot of record. Explicit-wins
    # precedence: rows already closed by end-phase / phase-boundary are left
    # byte-identical — only absent fields are backfilled.
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        _reconcile_accumulator_into_phase(phases[phase_name], _read_accumulator(plan_id, phase_name))

    # Persist each phase's dispatch-boundary sum AND the number of rows it summed.
    # Both are DISTINCT fields — the raw total_tokens is left byte-identical
    # (explicit-wins, never overwritten). The render below picks the largest
    # ELIGIBLE measure across all three competing measures of the dispatched
    # population; see the `_reconcile_dispatched_measures` block for the symmetric
    # rule and the two eligibility conditions. No-op when the boundary file is
    # absent (no rows, sum 0).
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        boundary_sum, boundary_rows = _read_dispatch_boundary_totals(plan_id, phase_name)
        if boundary_rows:
            # The row count persists whenever the file held rows, INCLUDING the
            # case where they sum to zero: the sum alone cannot state its own
            # coverage, and a measure that cannot state its coverage is the one
            # this field exists to make legible.
            phases[phase_name]['dispatch_boundary_rows_recorded'] = boundary_rows
        if boundary_sum:
            phases[phase_name]['dispatch_boundary_total'] = boundary_sum

    # Render-time boundary monotonicity detector. A finalize loop-back re-enters
    # an earlier phase (e.g. 5-execute) under its own phase key, so a LATER
    # phase's start_time can precede an EARLIER phase's already-closed end_time.
    # Walking the canonical PHASE_NAMES order, flag any phase whose start_time
    # precedes the maximum end_time seen so far in the sequence. This is a
    # READ-ONLY detector — it surfaces the anomaly (a top-level
    # `boundary_monotonicity` warning listing the phases plus a per-phase
    # `boundary_non_monotonic` annotation) and guards the idle residual below,
    # but NEVER mutates the recorded start_time / end_time boundary fields. It
    # does not touch the #812 end_time-presence check below.
    #
    # This detector is a timestamp-ordering signal only, and it names the LATER
    # phase rather than the re-entered one (the re-entered phase's fresh
    # start_time is what pushes the following phase's already-closed window out of
    # order). `close_count`, written at the write site, is the authoritative
    # re-entry marker — see the re_entered_phases detection below.
    non_monotonic_phases: list[str] = []
    prior_end_dt: datetime | None = None
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        start_dt = _parse_iso(phase.get('start_time'))
        end_dt = _parse_iso(phase.get('end_time'))
        if start_dt is not None and prior_end_dt is not None and start_dt < prior_end_dt:
            non_monotonic_phases.append(phase_name)
            phase['boundary_non_monotonic'] = 'true'
        if end_dt is not None and (prior_end_dt is None or end_dt > prior_end_dt):
            prior_end_dt = end_dt
    if non_monotonic_phases:
        data['boundary_monotonicity'] = ','.join(non_monotonic_phases)

    # Re-entry marker, read straight off the write site's close_count. Unlike the
    # timestamp detector above this needs no inference and names the phase that
    # was actually re-entered, so a reader can tell which row's totals are the
    # sum across multiple closes.
    re_entered_phases = [
        name for name in PHASE_NAMES if name in phases and _row_int(phases[name], 'close_count') > 1
    ]
    if re_entered_phases:
        data['re_entered_phases'] = ','.join(re_entered_phases)

    # Persist the per-phase idle residual back into metrics.toon before
    # rendering: idle = max(0, wall_clock - worked). Derived deterministically
    # from already-persisted fields via session-boundary inference — no new API.
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        wall_ms = _wall_clock_ms(phase)
        if wall_ms is None:
            continue
        if phase_name in non_monotonic_phases:
            # Guard: a re-entered (non-monotonic) phase's wall span overlaps an
            # earlier phase's already-closed window, so the idle residual derived
            # from it is corrupt. Zero it rather than emit a meaningless figure;
            # the boundary_monotonicity warning surfaces the anomaly instead.
            phase['idle_duration_ms'] = 0
            continue
        idle_ms = max(0, wall_ms - _worked_ms(phase))
        phase['idle_duration_ms'] = idle_ms

    # Read-cost decomposition (plan 030 D3). The read cost — cache_read_input_tokens
    # — is one opaque number that hides two levers: the average resident context
    # per API call, and the number of calls. Publish the resident-context factor as
    # a PERSISTED field so a consumer reads it off the row rather than re-deriving
    # it at render time; the second factor (turns) is the tool_uses count already on
    # the row, so it is not duplicated. Their product reconstructs the read cost:
    #   cache_read_input_tokens ≈ cache_read_per_tool_use × tool_uses
    # This is a DERIVED-COST ratio whose numerator (cache_read, main-context-window)
    # and denominator (tool_uses, dispatched-subagent) are DIFFERENT populations —
    # the ratio is disclosed as such, not read as a single-population measurement
    # (see data-format.md § Read-Cost Decomposition, and plan 030 D4). Written only
    # when both operands are present and tool_uses > 0; absent otherwise, never a
    # guessed zero. The field's presence is an INVARIANT — present iff derivable
    # from THIS regenerate's operands — so a stale value from an earlier generate
    # (whose operands no longer qualify) is REMOVED rather than left to render an
    # invalid identity or crash the render's tool_uses read. This mirrors the
    # denominator pair, which generate likewise drops when its source stops being
    # readable.
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        cache_read = phase.get('cache_read_input_tokens')
        tool_uses = phase.get('tool_uses')
        if (
            isinstance(cache_read, (int, float))
            and isinstance(tool_uses, (int, float))
            and int(tool_uses) > 0
        ):
            phase['cache_read_per_tool_use'] = round(int(cache_read) / int(tool_uses))
        else:
            phase.pop('cache_read_per_tool_use', None)

    # end_time-presence check over the canonical six-phase baseline.
    #
    # THE KEYS NAME THE PREDICATE THEY COMPUTE, and nothing wider. The check
    # asks exactly one question per canonical phase: does its metrics.toon row
    # carry an `end_time` — the boundary-close marker `end-phase` /
    # `phase-boundary` stamp, the same definition `cmd_boundary_status` uses for
    # a missing boundary? A phase with no row at all is missing it too.
    #
    # It is NOT a completeness verdict and NOT an internal-consistency check. A
    # row can carry `end_time` while its `tool_uses` is 0, its `total_tokens` is
    # non-zero, and its `duration_seconds` disagrees with its own stored span —
    # and this check will still report it as carrying the marker, because that
    # is the only thing it looked at. The keys were previously named `partial` /
    # `unrecorded_phases`, which asserted the wider verdict; they are renamed
    # (breaking, no dual-key shim) so the name states the predicate at the point
    # of use.
    #
    # Persisted as top-level keys in metrics.toon (round-tripped via
    # read_metrics_raw's arbitrary-top-level-key path): the bool as a true/false
    # token and the list comma-joined.
    phases_missing_end_time = [
        name for name in PHASE_NAMES if not phases.get(name, {}).get('end_time')
    ]
    any_phase_missing_end_time = len(phases_missing_end_time) > 0
    data['any_phase_missing_end_time'] = 'true' if any_phase_missing_end_time else 'false'
    data['phases_missing_end_time'] = ','.join(phases_missing_end_time)
    # The writer emits the NEW keys only and never the old ones. read_metrics_raw
    # round-trips arbitrary top-level keys, so a metrics.toon written before the
    # rename would otherwise carry BOTH the stale `partial` / `unrecorded_phases`
    # pair and the new keys after a regenerate — a dual-key emission the breaking
    # rename explicitly forbids, and one that would let a reader take the stale
    # pair as current. Dropping them here is a write-side refusal, not a
    # compatibility shim: no old key is ever produced, and no old key is read.
    data.pop('partial', None)
    data.pop('unrecorded_phases', None)

    # Inline main-context spend, present on EVERY row — as a figure, a measured
    # zero, or an explicit not-measured marker, but never as absence.
    #
    # `enrich` writes `inline_main_context_tokens` only on a truthy inline sum, so
    # the field was sparsely persisted and its absence conflated two facts: a
    # phase `enrich` measured and found no inline spend, and a phase `enrich`
    # never touched. The discriminator between them is already on the row —
    # `enrich` stamps `total_tokens_population` on every row it visits, on all
    # three of its branches — so the two states are separable without guessing.
    #
    # A row carrying the discriminator but no figure was MEASURED at zero and is
    # written `0`. A row carrying neither was never enriched and is written the
    # module's own `UNMEASURED_COLUMN_TOKEN`. The pre-labelling-`enrich` row
    # `_token_population` documents (folded, but carrying no discriminator) lands
    # in the unmeasured branch, which is the honest verdict for a row whose
    # enrich provenance is unrecoverable.
    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        if isinstance(_coerce_numeric(phase.get('inline_main_context_tokens')), (int, float)):
            # A real measurement, from `enrich`. Never overwritten.
            continue
        # Anything else — absent, or a sentinel this loop wrote on an earlier
        # generate — is RE-DERIVED from the current row rather than preserved, so
        # an `enrich` that has since measured the phase at zero is not shadowed by
        # a stale `unmeasured`. The field's non-numeric value is an invariant of
        # THIS regenerate's operands, the same rule `cache_read_per_tool_use`
        # follows above.
        phase['inline_main_context_tokens'] = (
            0 if phase.get('total_tokens_population') else UNMEASURED_COLUMN_TOKEN
        )

    # The store write is deliberately NOT here. Every figure the Total row renders
    # is derived below and must reach the store, so the single write — and the
    # denominators that must be stamped last before it — happen once the aggregate
    # exists. See "Persist the aggregate, then render the Total row FROM it".

    # Build metrics.md content
    lines = []
    lines.append(f'# Metrics: {plan_id}')
    lines.append('')
    lines.append(f'Generated: {render_timestamp(datetime.now(UTC), "%Y-%m-%d %H:%M:%S", " UTC")}')
    lines.append('')

    # Phase breakdown table
    lines.append('## Phase Breakdown')
    lines.append('')

    # end_time-presence marker: name the phases whose row carries no
    # boundary-close marker, and say what that does and does not mean. The
    # marker states the predicate rather than a completeness verdict — the
    # rendered wording is the reader's only key to what was actually checked.
    if any_phase_missing_end_time:
        lines.append(
            '> Phases missing an end_time boundary marker — '
            f'{", ".join(phases_missing_end_time)}. These rows were never closed by '
            'end-phase / phase-boundary, so their totals are absent and every column '
            'Total above is a floor. This is an end_time-presence check only: a phase '
            'NOT listed here carries the marker, which says nothing about whether its '
            'recorded figures are complete or internally consistent.'
        )
        lines.append('')

    # Re-entry marker: name every phase closed more than once, so a reader knows
    # which rows carry totals summed across multiple closes. This is the
    # authoritative re-entry signal (close_count is written at the write site);
    # the timestamp-derived warning below is a weaker inference that names the
    # later phase instead.
    if re_entered_phases:
        lines.append(
            f'> Re-entered phases: {", ".join(re_entered_phases)}. Totals for these '
            'phases are the sum across every close (close_count > 1).'
        )
        lines.append('')

    # Boundary-monotonicity warning: when a finalize loop-back re-entered an
    # earlier phase, a later phase's start_time precedes an earlier phase's
    # end_time. Surface it under the heading so a reader sees the idle residual
    # for those phases was guarded (zeroed) rather than derived from a corrupt
    # overlapping span.
    if non_monotonic_phases:
        lines.append(
            '> Boundary monotonicity warning: re-entered (non-monotonic) phase '
            f'boundaries detected — {", ".join(non_monotonic_phases)}. Idle residual '
            'guarded for these phases (a finalize loop-back re-enters an earlier phase).'
        )
        lines.append('')

    # Collect breakdown rows (phases that exist) preserving canonical phase order.
    # The completeness denominator is the canonical-six baseline (len(PHASE_NAMES)),
    # NOT the count of present rows: an entirely-absent phase must still make the
    # Total render as partial (n=k/6) rather than silently looking complete.
    breakdown_rows = [(name, phases[name]) for name in PHASE_NAMES if name in phases]
    breakdown_n = len(PHASE_NAMES)

    def _numeric(value: object) -> int | float | None:
        """Return value as int/float if it's a truthy number, else None.

        Symmetric per-cell rule: a per-phase cell is "present" iff the underlying
        raw value is a truthy numeric (zero or missing → absent → '-').
        """
        coerced = _coerce_numeric(value)
        if not isinstance(coerced, (int, float)):
            return None
        if not coerced:
            return None
        return coerced

    def _ms_cell(value_ms: int | None) -> tuple[str, int | None]:
        """Render a duration-in-ms value as a table cell.

        Returns (rendered_cell, value_for_total_in_ms). A truthy numeric renders
        via format_duration; zero or None renders '-' and contributes nothing to
        the Total. This is the symmetric per-cell present/absent rule applied
        uniformly to the Worked, Reported (wall), and Idle columns.

        The Total operand is returned in MILLISECONDS rather than seconds so the
        persisted aggregate keeps the operands' own precision — a per-column
        conversion to seconds before summing would put the store's granularity
        below the render's (see ``_TOTALS_FIELDS``).
        """
        if value_ms is None:
            return '-', None
        numeric = _numeric(value_ms)
        if numeric is None:
            return '-', None
        return format_duration(float(numeric) / 1000.0), int(numeric)

    # Per-column value subsets (for Total aggregation and partial-marker decisions).
    # The three duration subsets hold MILLISECONDS; see _ms_cell.
    worked_values: list[int] = []
    wall_values: list[int] = []
    idle_values: list[int] = []
    tokens_values: list[int] = []
    tool_uses_values: list[int] = []
    # Billing is a DERIVED-COST measure, aggregated in its own column and never
    # folded into the dispatched Tokens total: the two answer different questions
    # (what the work cost to buy vs how much dispatched work was done) and are
    # measured over different populations.
    billing_values: list[int] = []
    # Phases whose Tokens cell renders a competing dispatched measure rather than
    # the recorded total_tokens. Each entry is (phase, winning_field, winning
    # value, the total_tokens it beat) so the annotation can name WHICH measure
    # won and by how much, instead of asserting an unqualified "same-population
    # max" the comparison may not have earned.
    reconciled_phases: list[tuple[str, str, int, int | None]] = []
    # Phases whose token record is NOT a plain dispatched measurement, collected
    # so the population annotation under the table can name them. `inline` rows
    # render a main-context-window figure in the dispatched column (the enrich
    # fold); `mixed` rows render a dispatched figure that omits inline spend the
    # row records separately.
    inline_population_phases: list[str] = []
    mixed_population_phases: list[str] = []
    # Phases whose Tokens cell is a never-closed phase's dispatch-boundary floor,
    # collected so the annotation under the table can name them and their marker.
    unclosed_boundary_phases: list[tuple[str, int]] = []

    # Two-pass build: first collect all rows as tuples, then pad to uniform per-column width.
    header_row: tuple[str, ...] = (
        'Phase',
        'Worked',
        'Reported (wall)',
        'Idle',
        _TOKENS_COLUMN_HEADER,
        'Tool Uses',
        'Billing (cost)',
    )
    data_rows: list[tuple[str, ...]] = []

    for phase_name, phase in breakdown_rows:
        wall_ms = _wall_clock_ms(phase)
        worked_ms = _worked_ms(phase)
        idle_ms = phase.get('idle_duration_ms')
        idle_ms_int = int(idle_ms) if isinstance(idle_ms, (int, float)) else None

        worked_str, worked_val = _ms_cell(worked_ms)
        if worked_val is not None:
            worked_values.append(worked_val)

        wall_str, wall_val = _ms_cell(wall_ms)
        if wall_val is not None:
            wall_values.append(wall_val)

        idle_str, idle_val = _ms_cell(idle_ms_int)
        if idle_val is not None:
            idle_values.append(idle_val)

        # Symmetric same-population reconciliation across ALL THREE competing
        # measures of the dispatched population (never their sum — they count the
        # same leaves). The largest ELIGIBLE measure wins and feeds the Total via
        # tokens_values; a partial or over-covering boundary measure and a
        # cross-population total_tokens are all ineligible. When the winner is not
        # total_tokens, the phase is recorded so the annotation below names which
        # measure won.
        raw_tokens = _numeric(phase.get('total_tokens'))
        winner = _reconcile_dispatched_measures(phase)
        cell_source: str | None = None
        if winner is not None:
            winning_field, winning_value = winner
            if winning_field != 'total_tokens':
                reconciled_phases.append(
                    (phase_name, winning_field, winning_value,
                     int(raw_tokens) if raw_tokens is not None else None)
                )
            tokens_str = f'{winning_value:,}'
            tokens_values.append(winning_value)
            cell_source = winning_field
        elif raw_tokens is not None:
            # No eligible dispatched measure. The row still carries a figure —
            # the inline phase's main-context total — which renders on its own
            # and is marked `(inline)` by the population suffix below.
            tokens_str = f'{int(raw_tokens):,}'
            tokens_values.append(int(raw_tokens))
            cell_source = 'total_tokens'
        else:
            tokens_str = '-'

        # A never-closed phase's recorded dispatch spend: folded in where the
        # ordinary rules dropped it, and LABELLED in every case where it is what
        # the cell shows.
        #
        # Two distinct gaps close here, and the labelling half is the one that is
        # easy to miss. When the row carries no `subagent_samples`, coverage is
        # UNDECIDABLE, the boundary sum is already eligible, and it simply wins the
        # maximum — so the figure reaches the cell but renders as an ordinary
        # dispatched total, saying nothing about the phase never having closed.
        # That is the "technically correct, practically ignored" partiality this
        # deliverable exists to fix: the reader sees a number, not a floor. When
        # instead the sum is refused as PARTIAL or OVER, the cell can fall back to
        # `-` while the boundary file holds the phase's whole recorded spend, and a
        # multi-million-token phase disappears from the table entirely.
        #
        # So: fold only when the floor EXCEEDS whatever the ordinary rules produced
        # (it can raise a cell, never lower one, and never displaces a measure the
        # reconciliation trusted more) — then mark whenever the cell is the
        # boundary sum on an unclosed row, however it got there.
        floor = _unclosed_boundary_floor(phase)
        if floor is not None:
            current = tokens_values[-1] if cell_source else None
            if current is None or floor > current:
                if cell_source:
                    tokens_values[-1] = floor
                else:
                    tokens_values.append(floor)
                tokens_str = f'{floor:,}'
                cell_source = 'dispatch_boundary_total'
            if cell_source == 'dispatch_boundary_total':
                cell_source = TOKENS_SOURCE_UNCLOSED_BOUNDARY
                unclosed_boundary_phases.append((phase_name, floor))

        # Persist the cell's provenance so a consumer reads it off the row rather
        # than re-running the comparison or parsing the rendered annotation.
        if cell_source:
            phase[_TOKENS_CELL_SOURCE_FIELD] = cell_source
        else:
            phase.pop(_TOKENS_CELL_SOURCE_FIELD, None)

        # Declare the population at the point of render. The cell carries the
        # marker; the annotation under the table declares the unmarked default
        # and spells out what each marker means, so a reader never has to infer
        # the population from the column header's default.
        #
        # A phase is collected for the annotation ONLY when its cell actually
        # carries the marker. An absent cell renders `-`, takes no suffix, and
        # contributes nothing to the Total — naming it under "Marked `(inline)`"
        # would assert a marker the reader cannot find, and would make the Total
        # look cross-population when no inline figure fed it.
        population = _token_population(phase)
        if tokens_str != '-':
            tokens_str += _POPULATION_CELL_SUFFIX.get(population, '')
            if population == POPULATION_INLINE:
                inline_population_phases.append(phase_name)
            elif population == POPULATION_MIXED:
                mixed_population_phases.append(phase_name)
            # The coverage marker rides AFTER the population marker: they qualify
            # different things (which population the figure measures, and whether
            # it covers the whole phase), and a cell can legitimately carry both.
            if cell_source == TOKENS_SOURCE_UNCLOSED_BOUNDARY:
                tokens_str += _UNCLOSED_BOUNDARY_CELL_SUFFIX

        tool_uses = _numeric(phase.get('tool_uses'))
        tool_uses_str = str(int(tool_uses)) if tool_uses is not None else '-'
        if tool_uses is not None:
            tool_uses_values.append(int(tool_uses))

        billing = _numeric(phase.get('billing_weighted_total'))
        billing_str = f'{int(billing):,}' if billing is not None else '-'
        if billing is not None:
            billing_values.append(int(billing))

        data_rows.append(
            (phase_name, worked_str, wall_str, idle_str, tokens_str, tool_uses_str, billing_str)
        )

    # Persist the aggregate, then render the Total row FROM the persisted values.
    #
    # The order is the deliverable: every figure the Total row shows now exists in
    # the store as a value beside the count of phase rows that fed it, and the
    # render reads that pair back rather than holding a second, unpersisted copy.
    # A figure the render computes and does not persist is a number nobody can
    # check — and the qualifier is as load-bearing as the figure, because a sum
    # over 2 of 6 phases and a sum over 6 of 6 are different quantities that
    # render identically without it.
    column_values: dict[str, list[int]] = {
        'worked': worked_values,
        'wall': wall_values,
        'idle': idle_values,
        'tokens': tokens_values,
        'tool_uses': tool_uses_values,
        'billing': billing_values,
    }
    data[_TOTALS_DENOMINATOR_FIELD] = breakdown_n
    for column, values in column_values.items():
        field = _TOTALS_FIELDS[column]
        data[field] = sum(int(v) for v in values)
        data[f'{field}{_POPULATION_COUNT_SUFFIX}'] = len(values)
    # The Total is a cell in the same column and inherits the same declared
    # default, so it takes the same marking discipline as every other cell: when
    # an `(inline)` row fed the sum, the Total spans populations and says so.
    # Only `(inline)` rows cross-contaminate the sum — a `(mixed)` row's cell is
    # the dispatched figure, with its inline spend deliberately excluded.
    spans_populations = bool(inline_population_phases)
    data[_TOTALS_SPANS_POPULATIONS_FIELD] = 'true' if spans_populations else 'false'
    # The declared exclusion set, as DATA. It is the key to every boundary
    # coverage shortfall the report shows, and it previously existed only inside
    # the rendered annotation — so a script reading the store got the coverage
    # numbers without the declaration that makes them safe to interpret.
    data[_BOUNDARY_EXCLUDED_CLASSES_FIELD] = ','.join(DISPATCH_BOUNDARY_EXCLUDED_CLASSES)

    # Denominators + their sampling point. Written last among the derived
    # top-level keys so the pair's timestamp is the closest available stamp to
    # the write itself.
    _persist_denominators(plan_id, data)

    write_metrics(plan_id, data)

    def _total_str(column: str, formatter, *, is_duration: bool = False) -> str:
        """Apply the symmetric Total aggregation rule, reading the STORE.

        - Empty subset → '-'.
        - Subset smaller than breakdown_n → '{sum_str} (n=k/N)'.
        - Subset equal to breakdown_n → plain sum.
        """
        field = _TOTALS_FIELDS[column]
        total = int(data[field])
        k = int(data[f'{field}{_POPULATION_COUNT_SUFFIX}'])
        if k == 0:
            return '-'
        sum_str = format_duration(float(total) / 1000.0) if is_duration else formatter(total)
        if k < breakdown_n:
            return f'{sum_str} (n={k}/{breakdown_n})'
        return sum_str

    total_worked_str = _total_str('worked', str, is_duration=True)
    total_wall_str = _total_str('wall', str, is_duration=True)
    total_idle_str = _total_str('idle', str, is_duration=True)
    total_tokens_str = _total_str('tokens', lambda n: f'{n:,}')
    if spans_populations and total_tokens_str != '-':
        total_tokens_str += _TOTAL_CROSS_POPULATION_SUFFIX
    total_tool_uses_str = _total_str('tool_uses', str)
    total_billing_str = _total_str('billing', lambda n: f'{n:,}')

    total_row: tuple[str, ...] = (
        '**Total**',
        f'**{total_worked_str}**',
        f'**{total_wall_str}**',
        f'**{total_idle_str}**',
        f'**{total_tokens_str}**',
        f'**{total_tool_uses_str}**',
        f'**{total_billing_str}**',
    )

    # Compute per-column widths across header, data rows, and the bold-marked Total row.
    all_rows: list[tuple[str, ...]] = [header_row, *data_rows, total_row]
    column_count = len(header_row)
    widths = [max(len(row[c]) for row in all_rows) for c in range(column_count)]

    def _format_row(row: tuple[str, ...]) -> str:
        return '| ' + ' | '.join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + ' |'

    separator_line = '|' + '|'.join('-' * (widths[i] + 2) for i in range(column_count)) + '|'

    lines.append(_format_row(header_row))
    lines.append(separator_line)
    for row in data_rows:
        lines.append(_format_row(row))
    lines.append(_format_row(total_row))
    lines.append('')

    # Reconciliation annotation: name the phases whose Tokens cell renders a
    # competing dispatched measure instead of the recorded total, and state the
    # TRUE relation to that total. A winner that EQUALS total_tokens is the
    # reconciliation identity (agreement), not the under-count a blanket "> " would
    # assert; a smaller one is a genuine anomaly. See _reconciliation_relation_clause.
    if reconciled_phases:
        details = ', '.join(
            f'{name} → {field} {value:,}' + _reconciliation_relation_clause(value, beaten)
            for name, field, value, beaten in reconciled_phases
        )
        lines.append(
            '> Tokens reconciled across the competing measures of the dispatched '
            'population (largest eligible measure wins, never their sum, since all '
            'three count the same leaves; a partial or over-covering measure is '
            'ineligible): '
            f'{details}'
        )
        lines.append('')

    # Population annotation: the Tokens column is NOT single-population, and the
    # Total row therefore is not a dispatched total. Say so where the figures are
    # rendered rather than leaving the reader to infer it from a field name.
    #
    # ONE annotation line carries the default and every exception together: the
    # default declaration is the key to the column header's "unless marked"
    # clause, and a key separated from the markers it explains (by a blockquote
    # break) is a key the reader has to reassemble. Assembling the clauses means
    # the default renders whenever ANY marker appears — including a report whose
    # only exceptions are `(mixed)`, which a gate on the inline case alone would
    # leave with markers and no key.
    if inline_population_phases or mixed_population_phases:
        population_clauses = [
            '> Tokens population: an unmarked cell is a dispatched-subagent measurement — '
            'the default this column header declares.'
        ]
        if inline_population_phases:
            population_clauses.append(
                'Marked `(inline)` — the phase dispatched nothing, so the cell is the '
                'main-context-window measurement enrich folded into total_tokens (also recorded '
                f'under its own name as inline_main_context_tokens): {", ".join(inline_population_phases)}. '
                'The **Total** therefore sums more than one population and is not a dispatched '
                'total; its cell is marked `(spans populations)`.'
            )
        if mixed_population_phases:
            population_clauses.append(
                'Marked `(mixed)` — the cell is the phase\'s dispatched-subagent total; the inline '
                'main-context spend measured in the same window is recorded separately as '
                'inline_main_context_tokens and is excluded from both the cell and the **Total**: '
                f'{", ".join(mixed_population_phases)}.'
            )
        lines.append(' '.join(population_clauses))
        lines.append('')

    # Unclosed-boundary fold annotation. The cell marker is not self-explanatory —
    # it says the figure is a floor without saying why — so the key is rendered
    # wherever the marker appears, and states BOTH what was folded in and what was
    # deliberately not.
    if unclosed_boundary_phases:
        folded = ', '.join(f'{name} → {value:,}' for name, value in unclosed_boundary_phases)
        lines.append(
            '> Marked `(boundary floor)` — the phase was never closed by end-phase / '
            'phase-boundary, so it has no recorded total; the figure is the sum of its '
            'dispatch-boundary rows, which accumulate per dispatch and do not depend on '
            f'the phase boundary closing: {folded}. It is a FLOOR — it covers only the '
            'dispatch classes that register a boundary (see the declared exclusions '
            'below). The phase stays listed as missing its end_time marker and its '
            'duration stays absent: the boundary file records per-dispatch spans and '
            'cannot supply a phase wall-clock the close never stamped.'
        )
        lines.append('')

    # Declared dispatch-boundary population. Whenever the report carries a boundary
    # numerator (dispatch_boundary_*) or a subagent_samples denominator, NAME the
    # dispatch classes that register no boundary, so a
    # `dispatch_boundary_rows_recorded < subagent_samples` shortfall reads as a
    # DECLARED exclusion rather than as missing data — the coverage figures below
    # reference this declaration. Silent exclusion is the defect the ledger exists
    # to avoid; see DISPATCH_BOUNDARY_EXCLUDED_CLASSES (derived from the call graph).
    boundary_surface_present = any(
        isinstance(p.get('subagent_samples'), int)
        or _numeric(p.get('dispatch_boundary_total')) is not None
        or isinstance(p.get('dispatch_boundary_rows_recorded'), int)
        for p in phases.values()
    )
    if boundary_surface_present:
        lines.append(
            '> Dispatch-boundary population: dispatch_boundary_rows_recorded counts only the '
            'dispatch classes that call record-dispatch-boundary — a DECLARED SUBSET of the '
            'dispatched population enrich samples as subagent_samples, never the whole of it. '
            'These dispatch classes register no boundary and are excluded by declaration: '
            f'{", ".join(DISPATCH_BOUNDARY_EXCLUDED_CLASSES)}. A phase whose boundary rows fall '
            'short of its subagent_samples is short by exactly these excluded classes; boundary '
            'rows that EXCEED subagent_samples are a population failure, not a coverage figure.'
        )
        lines.append('')

    # Phase details
    lines.append('## Phase Details')
    lines.append('')

    for phase_name in PHASE_NAMES:
        if phase_name not in phases:
            continue
        phase = phases[phase_name]
        lines.append(f'### {phase_name}')
        lines.append('')

        start = phase.get('start_time', '-')
        end = phase.get('end_time', '-')
        lines.append(f'- **Start**: {start}')
        lines.append(f'- **End**: {end}')

        # Only a re-entered phase gets this bullet: a once-closed row carries no
        # reader-relevant close-count fact, and stating "1" on every phase would
        # bury the rows that actually accumulated.
        close_count = _row_int(phase, 'close_count')
        if close_count > 1:
            # Render the row's OWN declaration rather than restating the split
            # from this render site's knowledge — the row is the source of truth
            # (see _stamp_value_scope), and a hand-restated list here would be a
            # second copy free to drift from the writer's.
            cumulative = str(phase.get('cumulative_fields') or '').strip()
            last_close = str(phase.get('last_close_fields') or '').strip()
            split = (
                f' Cumulative across closes: {cumulative}. Latest close only: {last_close}.'
                if cumulative or last_close
                else ''
            )
            lines.append(
                f'- **Closes**: {close_count} (phase re-entered; the totals below are '
                'the sum across every close, and Start is the latest entry only).'
                + split
            )

        wall_ms = _wall_clock_ms(phase)
        if wall_ms:
            lines.append(f'- **Reported (wall-clock) duration**: {format_duration(wall_ms / 1000.0)}')

        worked_ms = _worked_ms(phase)
        if worked_ms:
            lines.append(f'- **Worked duration**: {format_duration(worked_ms / 1000.0)}')

        idle_ms = phase.get('idle_duration_ms')
        if isinstance(idle_ms, (int, float)) and idle_ms:
            lines.append(f'- **Idle duration**: {format_duration(float(idle_ms) / 1000.0)}')

        population = _token_population(phase)

        tokens = phase.get('total_tokens')
        if tokens:
            lines.append(
                f'- **Total tokens**: {int(tokens):,} ({_POPULATION_BULLET_NOTE[population]})'
            )

        boundary_total = phase.get('dispatch_boundary_total')
        if boundary_total:
            # The measure states its own coverage on every render. A boundary sum
            # that covers fewer dispatches than the phase had is a floor, and
            # saying so is the whole point of carrying rows_recorded — the prior
            # text asserted "same-population max" unconditionally, which a partial
            # measure has not earned.
            rows_recorded = phase.get('dispatch_boundary_rows_recorded')
            samples = phase.get('subagent_samples')
            boundary_state = _boundary_coverage_state(phase)
            if boundary_state is None:
                coverage = (
                    f'{rows_recorded} row(s) recorded, coverage undecidable — the phase '
                    'carries no subagent_samples to compare against'
                    if isinstance(rows_recorded, int)
                    else 'coverage undecidable'
                )
            elif boundary_state == 'partial':
                coverage = (
                    f'PARTIAL: {rows_recorded} of {samples} dispatch(es) recorded, so this '
                    'measure is a floor and is ineligible for the reconciliation maximum'
                )
            elif boundary_state == 'over':
                # Numerator > denominator is IMPOSSIBLE for one population. Never
                # 'complete': it is a loud failure that names both producers so the
                # reader sees the two counts are not commensurable, and the measure
                # is refused the maximum rather than inflating the Total.
                coverage = (
                    f'FAILURE: {rows_recorded} boundary rows recorded exceed {samples} '
                    'sampled dispatch(es) — the numerator (dispatch-boundary rows, written '
                    'by record-dispatch-boundary) and the denominator (subagent_samples, from '
                    "enrich's transcript walk) are different populations, so this is not a "
                    'coverage ratio; the measure is ineligible for the reconciliation maximum'
                )
            else:  # 'exact'
                coverage = (
                    f'{rows_recorded} of {samples} dispatch(es) recorded — complete '
                    '(numerator: dispatch-boundary rows; denominator: subagent_samples from enrich)'
                )
            won = any(
                name == phase_name and field == 'dispatch_boundary_total'
                for name, field, _v, _b in reconciled_phases
            )
            outcome = 'won the reconciliation maximum' if won else 'did not win the maximum'
            lines.append(
                f'- **Dispatch-boundary total**: {int(boundary_total):,} '
                f'(dispatched-subagent population; {coverage}; {outcome})'
            )

        # Guarded on the NUMERIC value, not on truthiness: the field is now
        # present on every row, and a measured `0` or the `unmeasured` sentinel
        # renders no bullet. The sentinel is a truthy string, so a bare
        # truthiness test would reach `int('unmeasured')`.
        inline_main_context = _numeric(phase.get('inline_main_context_tokens'))
        if inline_main_context:
            # The relationship to Total tokens differs by population, so the
            # bullet states which one applies. Claiming "surfaced alongside the
            # dispatched total, never replacing it" on an inline-only phase
            # would be false: there, this IS the figure Total tokens carries.
            if population == POPULATION_INLINE:
                relation = (
                    'this phase dispatched nothing, so this is the same figure Total tokens '
                    'carries, restated here under its own population-honest name'
                )
            else:
                relation = (
                    'surfaced alongside the dispatched Total tokens, which does not include it'
                )
            lines.append(
                f'- **Inline main-context tokens**: {int(inline_main_context):,} '
                '(main-context-window population, attributed via enrich phase-window usage — '
                f'input + output + cache_creation, excludes cache_read; {relation})'
            )

        tool_uses = phase.get('tool_uses')
        if tool_uses:
            lines.append(f'- **Tool uses**: {int(tool_uses)}')

        # Four-field usage view (sourced by `enrich` from subagent-transcript +
        # parent-window `message.usage` walks). Rendered per phase when present,
        # nested under a heading that names the population all four measure: an
        # API field name states no population at all, so these bullets were the
        # only rendered token figures carrying no population claim whatsoever.
        # The heading is the leaner form — one statement for four bullets — and
        # the nesting is what scopes it to them rather than to the whole list.
        four_field_bullets: list[str] = []
        for field, label in _FOUR_FIELD_USAGE_LABELS:
            value = phase.get(field)
            if isinstance(value, (int, float)) and value:
                four_field_bullets.append(f'  - **{label}**: {int(value):,}')
        if four_field_bullets:
            lines.append(_FOUR_FIELD_GROUP_HEADING)
            lines.extend(four_field_bullets)

        billing = phase.get('billing_weighted_total')
        if isinstance(billing, (int, float)) and billing:
            # A DEFINITION, not a disclaimer. The previous wording read as an
            # apology for rendering the figure at all; the incomparability with
            # the work columns is a stated property of a first-class cost
            # measure, not a reason to bury it.
            lines.append(
                f'- **Billing-weighted total**: {int(billing):,} '
                '(derived-cost population — input + output + 0.1 × cache_read + '
                '1.25 × cache_creation. What this phase cost to buy, over the '
                'main-context window; a different question from the dispatched '
                'work the Tokens column measures, so the two are never summed)'
            )

        # Read-cost decomposition (plan 030 D3): the two levers inside the opaque
        # read cost, stated as an identity so a reader sees what drives it. Both
        # factors are persisted (resident context here; turns is the tool_uses on
        # the row). The population caveat is stated inline because the ratio spans
        # two populations — the exact thing plan 030 exists to stop hiding.
        # Guard on ALL THREE operands, not on the factor alone: an archived or
        # hand-edited row could carry a stale cache_read_per_tool_use without a
        # live cache_read / positive tool_uses, and an unconditional tool_uses read
        # would then render an invalid identity or raise KeyError. generate's
        # persist step keeps the field's presence in step with derivability, so in
        # a freshly-generated row all three are present together; this render guard
        # is the defence for a row generate did not just write.
        resident = phase.get('cache_read_per_tool_use')
        cache_read = phase.get('cache_read_input_tokens')
        tool_uses_val = phase.get('tool_uses')
        if (
            isinstance(resident, (int, float))
            and isinstance(cache_read, (int, float))
            and isinstance(tool_uses_val, (int, float))
            and int(tool_uses_val) > 0
        ):
            turns = int(tool_uses_val)
            lines.append(
                f'- **Read-cost decomposition**: cache_read_input_tokens '
                f'({int(cache_read):,}) ≈ resident context per tool-use ({int(resident):,}) '
                f'× turns ({turns:,}). resident_context_per_call is a derived-cost ratio '
                '(main-context-window cache_read ÷ dispatched-subagent tool_uses — the '
                'two populations differ; see data-format.md § Read-Cost Decomposition), '
                'and turns is the tool_uses count already on the row'
            )

        # Transcript-supplied counters. RENDER-GUARD DIVERGENCE, deliberate: these
        # are guarded on PRESENCE (`field in phase`), not on the truthiness test
        # the four-field bullets above use. A stored 0 is a MEASURED zero here and
        # must render as `0`, while an absent counter (a runtime that declined the
        # transcript primitive) must render nothing — the truthiness guard would
        # collapse those two into the same blank output, destroying exactly the
        # distinction the persistence rule, the platform-runtime contract, and the
        # `exploration-share` corpus-exclusion rule are all built on. Do NOT
        # "harmonize" this back to the neighbouring truthiness form. The four-field
        # bullets keep theirs because for those fields zero and absent carry no
        # meaningful difference. The rule binds every group in
        # `_PRESENCE_PERSISTED_FIELDS` and for the two derived groups it binds
        # harder still: the sub-sources partition the exploration_result_bytes
        # bullet, and the cache-read residual rendering as `0` is what tells a
        # reader the split was fully explained.
        for field in _PRESENCE_PERSISTED_FIELDS:
            if field not in phase:
                continue
            value = int(phase[field])
            unattributed = _UNATTRIBUTED_RENDER.get(field)
            if unattributed is None:
                label = field.replace('_', ' ').capitalize()
                lines.append(f'- **{label}**: {value:,}')
                continue
            # An "unattributed" residual renders naming its QUANTITY (in the
            # label) and its DENOMINATOR (the field it is a residual of, with that
            # field's value off this same row), so the byte residual and the
            # cache_read residual can never be read as the same number (plan 030
            # D1). The denominator is co-present in every runtime-produced row; the
            # absent branch is a display fallback for a hand-edited/partial row,
            # not a measurement claim.
            label, denom_field, note = unattributed
            denom = phase.get(denom_field)
            if isinstance(denom, (int, float)):
                lines.append(
                    f'- **{label}**: {value:,} of {int(denom):,} {denom_field} ({note})'
                )
            else:
                lines.append(
                    f'- **{label}**: {value:,} ({note}; denominator {denom_field} '
                    'not recorded on this row)'
                )

        lines.append('')

    md_content = '\n'.join(lines)
    md_path = get_plan_dir(plan_id) / METRICS_MD
    atomic_write_file(md_path, md_content)

    # Read the aggregate back from the STORE rather than re-summing the render's
    # working lists. Re-summing here would make this return block a third producer
    # of the same figures, free to diverge from both the store and the table — the
    # very shape this deliverable removes. The duration fields are converted from
    # the persisted milliseconds at the point of use, so the returned second-scale
    # value and the persisted millisecond value are the same measurement.
    total_worked = int(data[_TOTALS_FIELDS['worked']]) / 1000.0
    total_wall = int(data[_TOTALS_FIELDS['wall']]) / 1000.0
    total_idle = int(data[_TOTALS_FIELDS['idle']]) / 1000.0
    total_tokens = int(data[_TOTALS_FIELDS['tokens']])
    # Aggregated separately and returned as its own field — never added to
    # total_tokens, which measures dispatched work rather than cost.
    total_billing_weighted = int(data[_TOTALS_FIELDS['billing']])

    # Echo each persisted denominator with its sampling point, and OMIT the pair
    # for a denominator that could not be counted — the same absent-is-not-zero
    # rule the persisted record follows, so a caller reading the return cannot
    # find a count without its reference moment either.
    denominators: dict[str, object] = {}
    for name in _DENOMINATOR_FIELDS:
        if name in data:
            denominators[name] = data[name]
            denominators[f'{name}{_SAMPLING_POINT_SUFFIX}'] = data[
                f'{name}{_SAMPLING_POINT_SUFFIX}'
            ]
    if 'denominators_sampled_at' in data:
        denominators['denominators_sampled_at'] = data['denominators_sampled_at']

    # Echo every persisted aggregate together with the count of phase rows that
    # fed it, DERIVED from `_TOTALS_FIELDS` so a column added there cannot reach
    # the report while staying absent from the return. A caller that reads a total
    # without its population count is back to quoting a figure whose coverage it
    # cannot state — the defect the persisted triple exists to close.
    totals_echo: dict[str, object] = {_TOTALS_DENOMINATOR_FIELD: data[_TOTALS_DENOMINATOR_FIELD]}
    for field in _TOTALS_FIELDS.values():
        count_field = f'{field}{_POPULATION_COUNT_SUFFIX}'
        totals_echo[field] = data[field]
        totals_echo[count_field] = data[count_field]
    totals_echo[_TOTALS_SPANS_POPULATIONS_FIELD] = data[_TOTALS_SPANS_POPULATIONS_FIELD]

    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': METRICS_MD,
        'phases_recorded': len(phases),
        **denominators,
        **totals_echo,
        'any_phase_missing_end_time': any_phase_missing_end_time,
        'phases_missing_end_time': phases_missing_end_time,
        'boundary_monotonicity': non_monotonic_phases,
        're_entered_phases': re_entered_phases,
        'total_worked_seconds': round(total_worked, 1),
        'total_wall_seconds': round(total_wall, 1),
        'total_idle_seconds': round(total_idle, 1),
        'total_tokens': total_tokens,
        'total_billing_weighted': total_billing_weighted,
        'total_worked_formatted': format_duration(total_worked),
        'total_wall_formatted': format_duration(total_wall),
        'total_idle_formatted': format_duration(total_idle),
        'total_tokens_formatted': format_tokens_short(total_tokens),
    }


_PHASE_BREAKDOWN_HEADING_RE = re.compile(r'^## Phase Breakdown\s*$')
_NEXT_H2_RE = re.compile(r'^## ')


def _extract_phase_breakdown_section(content: str) -> str | None:
    """Return the '## Phase Breakdown' section verbatim from metrics.md content.

    The section spans from the heading line up to (but not including) the next
    ``## `` heading or end-of-file. A single trailing blank line is normalised
    so the output ends with exactly one newline.

    Args:
        content: Full metrics.md file contents.

    Returns:
        The section as a string ending in a single newline, or ``None`` when
        the heading is absent.
    """
    lines = content.splitlines(keepends=True)
    start_idx: int | None = None
    for i, line in enumerate(lines):
        if _PHASE_BREAKDOWN_HEADING_RE.match(line):
            start_idx = i
            break
    if start_idx is None:
        return None
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if _NEXT_H2_RE.match(lines[j]):
            end_idx = j
            break
    section = ''.join(lines[start_idx:end_idx]).rstrip() + '\n'
    return section


def cmd_print_phase_breakdown(args: argparse.Namespace) -> dict:
    """Extract the '## Phase Breakdown' section from metrics.md and persist it.

    Default (``--output-file`` absent): write the extracted section to a known
    plan-relative artifact path (default ``work/phase-breakdown-output.txt``)
    and return a TOON envelope ``{status, plan_id, file, bytes_written}``.

    Explicit relative path: write the section to the supplied plan-relative
    path (parent directories are created as needed) and return the same TOON
    envelope. Absolute paths are rejected.

    Legacy stdout mode (``--output-file -``): write the section verbatim to
    stdout (no trailing TOON) and return a result dict carrying the
    ``_print_only`` sentinel so ``main`` skips the standard TOON emission.

    On error (missing metrics.md, missing section, invalid output path), a
    normal error TOON is returned via the standard emit path.
    """
    plan_id = require_valid_plan_id(args)
    md_path = get_plan_dir(plan_id) / METRICS_MD
    if not md_path.exists():
        return {
            'status': 'error',
            'error': 'metrics_md_not_found',
            'plan_id': plan_id,
            'message': f'metrics.md not found at {md_path}',
        }
    content = md_path.read_text(encoding='utf-8')
    section = _extract_phase_breakdown_section(content)
    if section is None:
        return {
            'status': 'error',
            'error': 'phase_breakdown_section_not_found',
            'plan_id': plan_id,
            'message': '## Phase Breakdown heading not found in metrics.md',
        }

    output_file = getattr(args, 'output_file', None)
    section_bytes = section.encode('utf-8')

    if output_file == '-':
        # Legacy stdout-only mode.
        sys.stdout.write(section)
        sys.stdout.flush()
        return {
            '_print_only': True,
            'status': 'success',
            'plan_id': plan_id,
            'bytes_written': len(section_bytes),
        }

    # Direct file-write mode (default + explicit relative path).
    relative_path = output_file if output_file else PHASE_BREAKDOWN_DEFAULT_OUTPUT
    if not is_valid_relative_path(relative_path):
        return {
            'status': 'error',
            'error': 'output_file_must_be_relative',
            'plan_id': plan_id,
            'message': (
                f'--output-file must be a plan-relative path '
                f'(no absolute paths, no traversal): {relative_path}'
            ),
        }
    file_path = get_plan_dir(plan_id) / relative_path
    # Defense-in-depth: verify resolved path stays within plan dir (guards symlinks, OS quirks).
    plan_dir_resolved = get_plan_dir(plan_id).resolve()
    if not file_path.resolve().is_relative_to(plan_dir_resolved):
        return {
            'status': 'error',
            'error': 'output_file_must_be_relative',
            'plan_id': plan_id,
            'message': (
                f'--output-file must be a plan-relative path '
                f'(no absolute paths, no traversal): {relative_path}'
            ),
        }
    atomic_write_file(file_path, section)
    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': relative_path,
        'bytes_written': len(section_bytes),
    }


def _count_deliverables(plan_id: str) -> int | None:
    """Count the plan's deliverables from ``solution_outline.md``.

    The grammar is NOT restated here. The count DELEGATES to
    ``_plan_parsing.extract_deliverable_headings`` applied to the outline's
    ``Deliverables`` section — the same extractor, over the same scope, that the
    retrospective's artifact-consistency check reads.
    ``manage-solution-outline list-deliverables`` counts through a SIBLING
    extractor in that same module (``extract_deliverables`` →
    ``split_deliverable_blocks``), and the two agree by construction rather than
    by coincidence: both match through the one module-level
    ``_plan_parsing.DELIVERABLE_HEADING_PATTERN``, so no edit can move one
    definition of a heading without moving the other. A private copy of the
    heading regex here would break that and make this module a SECOND producer
    of one number: a ``### N.`` heading under *Approach*, under *Risks*, or
    inside a fenced block showing deliverable syntax would be counted here and
    not there, and a reader of the two figures would have no way to tell which
    was right. Two disagreeing definitions of one denominator is the defect this
    module exists to close, so there is exactly one definition of the grammar
    and this is a caller of it.

    Persisting the count is what stops the plan-efficiency aspect re-deriving
    it (and silently re-dating it) at render time.

    Returns ``None`` for exactly one reason — the outline could not be READ
    (absent, or an ``OSError`` on read). A readable outline is a MEASURED
    count, including a measured ``0``: an outline with no ``Deliverables``
    section, or one whose Deliverables section carries no ``### N. Title``
    heading, was counted and the answer was zero. Absence is reserved for
    "the source could not be read" — see ``standards/data-format.md``
    § "A denominator with no determinable sampling point is not persisted".
    """
    path = get_plan_dir(plan_id) / 'solution_outline.md'
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return None
    sections = parse_document_sections(text)
    return len(extract_deliverable_headings(sections.get('deliverables', '')))


def _count_affected_files(plan_id: str) -> int | None:
    """Count the plan's declared ``affected_files`` from ``references.json``.

    This is a MOVING quantity — the list grows during execute — which is exactly
    why the count is worthless without the sampling point written beside it.

    Returns ``None`` for exactly one reason — the list could not be READ: the
    file is absent, unreadable, unparseable, or carries no ``affected_files``
    list at all. In every one of those the count was never taken, so the caller
    writes nothing.

    A PRESENT-but-empty ``affected_files`` list is a MEASURED ``0``, not an
    absence. That is a documented, legitimate plan state — a
    ``scope_estimate: none`` plan is pure analysis with no affected files — and
    collapsing it into absence would tell a reader that ``references.json``
    could not be read when it was read fine. The zero-vs-absent split is the
    same one ``_count_completed_tasks`` keeps, and the same one the
    dispatch-boundary row's ``unmeasured`` token keeps: a measured zero is a
    measurement.
    """
    path = get_plan_dir(plan_id) / 'references.json'
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    files = data.get('affected_files') if isinstance(data, dict) else None
    if not isinstance(files, list):
        return None
    return len(files)


def _count_completed_tasks(plan_id: str) -> int | None:
    """Count the plan's tasks recorded ``status: done``.

    Also a moving quantity: the task store grows as triage appends fix-tasks, so
    the same numerator over the same plan divides differently depending on when
    this ran.

    Returns ``None`` when the plan has no ``tasks/`` directory or no readable
    ``TASK-*.json`` at all — distinct from a plan whose tasks are all still
    pending, which legitimately counts ``0`` completed against a real
    population. The zero-vs-absent split is the point: an absent task store
    means the count was never taken.
    """
    tasks_dir = get_plan_dir(plan_id) / 'tasks'
    if not tasks_dir.is_dir():
        return None
    done = 0
    seen = 0
    for task_path in sorted(tasks_dir.glob('TASK-*.json')):
        try:
            task = json.loads(task_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        seen += 1
        if isinstance(task, dict) and task.get('status') == 'done':
            done += 1
    return done if seen else None


def _persist_denominators(plan_id: str, data: dict) -> None:
    """Write each determinable denominator together with its sampling point.

    The pair is atomic per denominator: a count is written ONLY alongside its
    ``{name}_sampling_point`` companion, so the record can never carry a figure
    whose reference moment is unstated. A denominator whose source could not be
    read is absent from the record entirely — the module's absent-is-not-zero
    rule, applied to the reference class rather than to a measurement.

    Every denominator here is counted from live plan state at the instant this
    ``generate`` ran, so all of them carry ``generate_time``. That value names
    the moment CLASS; the instant itself is stamped once as the plan-level
    ``denominators_sampled_at`` timestamp, written whenever at least one
    denominator was persisted. One shared timestamp is exact rather than
    approximate — every denominator in a single call is counted in that call —
    and it keeps the per-denominator surface to the two-field pair.

    A stale pair left by an earlier ``generate`` whose source has since become
    unreadable is REMOVED rather than kept, so the record never presents an old
    count beside a fresh sampling timestamp.

    Returns nothing; mutates ``data`` in place.
    """
    counters = {
        'deliverable_count': _count_deliverables,
        'files_modified': _count_affected_files,
        'tasks_completed': _count_completed_tasks,
    }
    persisted_any = False
    for name in _DENOMINATOR_FIELDS:
        value = counters[name](plan_id)
        if value is None:
            data.pop(name, None)
            data.pop(f'{name}{_SAMPLING_POINT_SUFFIX}', None)
            continue
        data[name] = value
        data[f'{name}{_SAMPLING_POINT_SUFFIX}'] = SAMPLING_POINT_GENERATE_TIME
        persisted_any = True
    if persisted_any:
        data['denominators_sampled_at'] = now_utc_iso()
    else:
        data.pop('denominators_sampled_at', None)


def _read_status_created(plan_id: str) -> str | None:
    """Return status.json.created (ISO timestamp) for the plan, or None on any failure.

    Used by cmd_phase_boundary to backfill 1-init.start_time at the first phase
    transition. Failure modes (missing status.json, malformed JSON, missing
    'created' key, non-string value) all return None — the renderer's
    agent-duration fallback still produces a meaningful Duration cell.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return None
    try:
        raw = status_path.read_text(encoding='utf-8')
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    created = data.get('created') if isinstance(data, dict) else None
    return created if isinstance(created, str) else None


def cmd_phase_boundary(args: argparse.Namespace) -> dict:
    """Atomically end the previous phase, start the next phase, and regenerate
    metrics.md in a single call.

    Equivalent to running, in order:
        end-phase   --phase {prev_phase} [--total-tokens N --duration-ms M --tool-uses K]
        start-phase --phase {next_phase}
        generate

    The fused call writes the same persisted state as the three-call sequence
    (work/metrics.toon and metrics.md). It is intended for orchestration
    boundaries where the caller knows the exact prev→next transition and
    wants a single script invocation instead of three.

    The optional token/duration/tool-uses flags are forwarded to the
    `end-phase` step. If the previous phase has not yet been started (no
    matching `start-phase`), it is recorded with end metadata only — same
    behaviour as the standalone `end-phase` command.

    Accumulate-on-re-entry: closing `--prev-phase` ADDS to that row rather than
    replacing it, so a finalize loop-back that re-enters an earlier phase keeps
    both entries' totals. The closing half delegates to
    `_close_phase_accumulating` — the shared writer `cmd_end_phase` also calls —
    see its docstring for the authoritative statement of the three
    accumulate-on-re-entry rules.

    Inline-phase recording mode: a phase that runs *inline* in the main
    orchestrator context (rather than as a dispatched `execution-context`
    leaf) produces no agent `<usage>` envelope, so the caller OMITS the
    `--total-tokens` / `--duration-ms` / `--tool-uses` flags. Omitting them is
    the sanctioned inline recording mode — NOT an incomplete call. The
    previous phase's `end_time` is stamped unconditionally below (independent
    of any usage flag), and `cmd_generate`'s end_time-presence check reads
    solely that marker. A timestamps-only closed row therefore carries the
    marker: it is never listed under `phases_missing_end_time` and never flips
    `any_phase_missing_end_time` to true. This is the path the inline
    1-init → 2-refine boundary and the recipe-inline (refine/outline)
    boundaries take; it preserves the #812 floor-not-truth semantics unchanged.
    """
    plan_id = require_valid_plan_id(args)
    prev_phase = args.prev_phase
    next_phase = args.next_phase

    if prev_phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid prev_phase: {prev_phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }
    if next_phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid next_phase: {next_phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    # Step 1: end the previous phase (mirrors cmd_end_phase semantics).
    data = read_metrics_raw(plan_id)
    end_now = now_utc_iso()

    if prev_phase not in data['phases']:
        data['phases'][prev_phase] = {}
    prev_data = data['phases'][prev_phase]

    # 1-init structural backfill: when transitioning out of 1-init for the
    # first time the phase row never went through cmd_start_phase, so
    # start_time is absent. Source it from status.json.created BEFORE closing
    # the row so the duration-computation path inside the shared closer catches
    # the backfill and writes duration_seconds in the same call.
    if prev_phase == '1-init' and not prev_data.get('start_time'):
        created_ts = _read_status_created(plan_id)
        if created_ts is not None:
            prev_data['start_time'] = created_ts

    closed = _close_phase_accumulating(prev_data, plan_id, prev_phase, args, end_now)
    total_tokens = closed['total_tokens']
    accumulator = closed['accumulator']

    # Step 2: start the next phase (mirrors cmd_start_phase semantics).
    start_now = now_utc_iso()
    if next_phase not in data['phases']:
        data['phases'][next_phase] = {}
    data['phases'][next_phase]['start_time'] = start_now
    data['updated'] = start_now

    write_metrics(plan_id, data)

    # Step 3: regenerate metrics.md from the current state.
    generate_result = cmd_generate(args)

    result = {
        'status': 'success',
        'plan_id': plan_id,
        'prev_phase': prev_phase,
        'next_phase': next_phase,
        'end_time': end_now,
        'start_time': start_now,
        'prev_close_count': prev_data['close_count'],
    }
    if 'duration_seconds' in prev_data:
        result['prev_duration_seconds'] = prev_data['duration_seconds']
    if total_tokens is not None:
        result['prev_total_tokens'] = prev_data['total_tokens']
    if accumulator and args.total_tokens is None:
        result['accumulator_used'] = True
    # Surface the generate side-effect outcome so callers can react if it
    # fell through to the no_data path (would only happen on a brand-new
    # plan where neither phase ever had a start_time recorded — should not
    # occur in normal phase boundary use).
    if generate_result.get('status') == 'success':
        result['metrics_file'] = generate_result.get('file', METRICS_MD)
        result['phases_recorded'] = generate_result.get('phases_recorded', 0)
    else:
        result['generate_status'] = generate_result.get('status', 'unknown')
        result['generate_message'] = generate_result.get('message', '')

    return result


def cmd_boundary_status(args: argparse.Namespace) -> dict:
    """Classify a metrics phase boundary as stamped / missing / not_applicable.

    Read-only resume-time detector. On cross-session re-entry the orchestrator
    calls this BEFORE dispatching the current phase to decide whether a missing
    `phase-boundary` must be stamped: if the prior session's phase skill
    self-transitioned the status, the resuming orchestrator's `manage-status
    transition` is a no-op and the paired `phase-boundary` call is skipped along
    with it, silently dropping a whole phase's token/duration attribution. This
    verb is the deterministic detection half of that reconciliation; it performs
    ZERO mutation of `work/metrics.toon`.

    Inputs:
        --next-phase  (required): the phase being entered on resume.
        --prev-phase  (optional): the phase that should have been closed before
            entering `--next-phase`. When omitted, only the "current phase has no
            start" condition is evaluated against `--next-phase`.

    Classification (computed from the persisted metrics.toon rows — the same
    `start_time` / `end_time` fields `end-phase` writes):
        - ``not_applicable``: a `--prev-phase` was supplied but that phase has no
            row at all (it never started) — there is no boundary to reconcile.
            When `--prev-phase` is omitted this classification never applies.
        - ``missing``: the boundary is half-stamped — the prev phase has a
            `start_time` but no `end_time`, OR the next phase has no `start_time`.
        - ``stamped``: the boundary is complete — when `--prev-phase` is supplied
            it has both `start_time` and `end_time` AND the next phase has a
            `start_time`; when `--prev-phase` is omitted the next phase has a
            `start_time`.

    Returns a TOON verdict carrying the classification, the offending field(s),
    and the prev/next phase names. The orchestrator prose reacts to `missing` by
    issuing an explicit `phase-boundary --prev-phase {prev} --next-phase {next}`
    call even though the status transition already happened.
    """
    plan_id = require_valid_plan_id(args)
    prev_phase = args.prev_phase
    next_phase = args.next_phase

    if next_phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid next_phase: {next_phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }
    if prev_phase is not None and prev_phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid prev_phase: {prev_phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    try:
        data = read_metrics_raw(plan_id)
    except OSError as exc:
        return {
            'status': 'error',
            'error': 'read_failed',
            'message': f'Failed to read metrics file: {exc}',
        }
    phases = data.get('phases', {})

    prev_data = phases.get(prev_phase) if prev_phase is not None else None
    next_data = phases.get(next_phase, {})

    next_has_start = bool(next_data.get('start_time'))

    # not_applicable: a prev phase was requested but it never started — nothing
    # to reconcile on the prev side.
    if prev_phase is not None and not prev_data:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'prev_phase': prev_phase,
            'next_phase': next_phase,
            'classification': 'not_applicable',
            'reason': 'prev phase has no metrics row (never started)',
        }

    # Collect the offending half-stamped fields.
    missing_fields: list[str] = []
    if prev_data is not None:
        if prev_data.get('start_time') and not prev_data.get('end_time'):
            missing_fields.append(f'{prev_phase}.end_time')
    if not next_has_start:
        missing_fields.append(f'{next_phase}.start_time')

    if missing_fields:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'prev_phase': prev_phase if prev_phase is not None else '-',
            'next_phase': next_phase,
            'classification': 'missing',
            'missing_fields': ','.join(missing_fields),
            'reason': 'half-stamped boundary — stamp the missing phase-boundary on resume',
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'prev_phase': prev_phase if prev_phase is not None else '-',
        'next_phase': next_phase,
        'classification': 'stamped',
        'reason': 'boundary fully recorded — proceed unchanged',
    }


def cmd_reconcile_ledgers(args: argparse.Namespace) -> dict:
    """Reconcile this plan's row ledgers against each other. Mutates NOTHING.

    Joins ``execution.toon``'s ``execution_log[]`` against each phase's
    ``work/metrics-dispatch-boundaries-{phase}.toon`` on phase and timestamp
    window, and emits one finding per row present in one ledger and absent from
    the other. The two partiality shapes are labelled distinctly — a phase whose
    boundary never closed is not the same defect as an absent row — and a phase
    the execution log structurally cannot cover is DECLARED rather than reported
    as a pile of divergences.

    See :mod:`_ledger_reconciliation` for the ledger populations and why they
    cannot agree by construction.

    The result publishes ``union_rows`` per phase and in the totals: neither
    ledger's own row count is the number of times a phase's steps ran, and
    without the union nothing tells a reader which count to take.
    """
    plan_id = require_valid_plan_id(args)

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    plan_dir = get_plan_dir(plan_id)
    execution_rows, execution_log_reason = load_execution_log(plan_dir)
    data = read_metrics_raw(plan_id)
    phases = data.get('phases', {})

    phase_blocks: list[dict] = []
    findings: list[dict] = []
    for phase_name in PHASE_NAMES:
        boundary_rows = load_boundary_rows(_dispatch_boundary_path(plan_id, phase_name))
        metrics_row = phases.get(phase_name) or {}
        if not boundary_rows and not metrics_row and not execution_rows:
            continue
        phase_rows = (
            None if execution_rows is None else execution_rows_for_phase(execution_rows, phase_name)
        )
        block = reconcile_phase(
            phase_name,
            phase_rows,
            boundary_rows,
            metrics_row,
            args.window_seconds,
            execution_log_reason,
        )
        if (
            block['execution_log_rows'] == 0
            and block['boundary_rows'] == 0
            and not block['findings']
        ):
            continue
        phase_blocks.append(block)
        findings.extend(block['findings'])

    return {
        'status': 'success',
        'plan_id': plan_id,
        'window_seconds': args.window_seconds,
        'execution_log_readable': execution_rows is not None,
        'execution_log_reason': execution_log_reason,
        'execution_log_population': ','.join(EXECUTION_LOG_PHASES),
        'phases': phase_blocks,
        'findings': findings,
        'findings_count': len(findings),
        # The union is the count a reader should take: neither ledger alone
        # observed every dispatch, and they diverge in both directions.
        'union_rows': sum(block['union_rows'] for block in phase_blocks),
        'execution_log_rows': sum(block['execution_log_rows'] for block in phase_blocks),
        'boundary_rows': sum(block['boundary_rows'] for block in phase_blocks),
    }


def cmd_accumulate_agent_usage(args: argparse.Namespace) -> dict:
    """Persist running per-phase totals of subagent <usage> data.

    Reads `.plan/local/plans/{plan_id}/work/metrics-accumulator-{phase}.toon`
    (initialising it when absent), sums in any provided values, increments
    the `samples` counter, and writes the file back. Idempotent across
    successive calls — the only authoritative state is on disk.

    Designed to be invoked from `phase-5-execute` and `phase-6-finalize`
    SKILL.md immediately after every Task-agent return, in place of the
    fragile model-context-only `agent_usage_totals` discipline.
    """
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid phase: {phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    existing = _read_accumulator(plan_id, phase)
    totals = {
        'total_tokens': int(existing.get('total_tokens', 0)),
        'tool_uses': int(existing.get('tool_uses', 0)),
        'duration_ms': int(existing.get('duration_ms', 0)),
        'retrospective_tokens': int(existing.get('retrospective_tokens', 0)),
        'samples': int(existing.get('samples', 0)),
    }
    if args.total_tokens is not None:
        totals['total_tokens'] += args.total_tokens
    if args.tool_uses is not None:
        totals['tool_uses'] += args.tool_uses
    if args.duration_ms is not None:
        totals['duration_ms'] += args.duration_ms
    if args.retrospective_tokens is not None:
        totals['retrospective_tokens'] += args.retrospective_tokens
    totals['samples'] += 1

    _write_accumulator(plan_id, phase, totals)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'total_tokens': totals['total_tokens'],
        'tool_uses': totals['tool_uses'],
        'duration_ms': totals['duration_ms'],
        'retrospective_tokens': totals['retrospective_tokens'],
        'samples': totals['samples'],
        'accumulator_file': str(_accumulator_path(plan_id, phase).relative_to(get_plan_dir(plan_id))),
    }


def _dispatch_boundary_path(plan_id: str, phase: str) -> Path:
    return get_plan_dir(plan_id) / DISPATCH_BOUNDARY_FILE_TEMPLATE.format(phase=phase)


def cmd_record_dispatch_boundary(args: argparse.Namespace) -> dict:
    """Record one tabular row per phase Task dispatch termination.

    Appends a TOON row to ``work/metrics-dispatch-boundaries-{phase}.toon``
    capturing why a phase Task dispatch ended (voluntary checkpoint,
    bare task_complete return, harness cancellation, error, unknown) along
    with the dispatched agent's <usage> totals at the time of return. The
    accumulating file becomes the audit trail for diagnosing
    `[OUTCOME]`-coverage gaps caused by agent-initiated re-dispatch.

    The file uses the same column layout for every row so plan-retrospective
    fact extractors can ingest it without a schema lookup. Each row carries the
    legacy five columns (``<timestamp>,<termination_cause>,<total_tokens>,
    <tool_uses>,<duration_ms>``) followed by the four per-dispatch context-load
    columns appended at the END (``input_tokens``, ``output_tokens``,
    ``cache_read_input_tokens``, ``cache_creation_input_tokens``) — the
    per-DISPATCH counterpart to the per-PHASE four-field view ``enrich`` writes.

    A context-load column whose flag was OMITTED carries the literal
    ``UNMEASURED_COLUMN_TOKEN`` rather than ``0``, and the corresponding key is
    ABSENT from the result TOON rather than returned as ``0``. This applies the
    module's own absent-is-not-zero persistence rule (the one
    ``_PRESENCE_PERSISTED_FIELDS`` already follows) to the ledger row: "the
    caller passed no measurement" and "the dispatch loaded zero context" are
    different facts and must not produce byte-identical rows. A *measured* zero
    is still written as ``0`` and still returned as ``0``. The legacy five
    columns are unchanged: they keep their ``0`` default, because nothing
    downstream distinguishes an absent from a zero on those.

    Appending at the END keeps the legacy five columns positionally unchanged so
    the existing plan-retrospective reader stays valid. The file's first line is
    a TOON-tabular header declaring the column order. The canonical column order
    / count / defaults are owned by ``standards/data-format.md`` (Per-Dispatch
    Context-Load Attribution section).
    """
    plan_id = require_valid_plan_id(args)
    phase = args.phase

    if phase not in PHASE_NAMES:
        return {
            'status': 'error',
            'error': 'invalid_phase',
            'message': f'Invalid phase: {phase}. Must be one of: {", ".join(PHASE_NAMES)}',
        }

    cause = args.termination_cause
    if cause not in DISPATCH_TERMINATION_CAUSES:
        return {
            'status': 'error',
            'error': 'invalid_termination_cause',
            'message': (
                f'Invalid termination_cause: {cause}. '
                f'Must be one of: {", ".join(DISPATCH_TERMINATION_CAUSES)}'
            ),
        }

    total_tokens = args.total_tokens if args.total_tokens is not None else 0
    tool_uses = args.tool_uses if args.tool_uses is not None else 0
    duration_ms = args.duration_ms if args.duration_ms is not None else 0
    # Four per-dispatch context-load columns (the four-field message.usage view at
    # dispatch termination). An OMITTED flag stays None here and is written as the
    # unmeasured token below — never coerced to 0, which would assert a
    # measurement the caller never took. Canonical column order / count /
    # unmeasured representation live in standards/data-format.md (Per-Dispatch
    # Context-Load Attribution).
    context_load: dict[str, int | None] = {
        column: getattr(args, column, None) for column in _DISPATCH_CONTEXT_LOAD_COLUMNS
    }

    # Guard at script side: refuse to record a dispatch boundary when the
    # plan directory does not exist (and was never initialised by phase-1).
    # Without this guard the `path.parent.mkdir(parents=True, ...)` below
    # silently creates an orphan plan tree just to hold the boundaries file.
    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    path = _dispatch_boundary_path(plan_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = now_utc_iso()
    # Legacy five columns first, then the four context-load columns appended at
    # the END so legacy readers stay positionally valid. An unmeasured
    # context-load column carries the token, not a 0.
    context_cells: list[str] = []
    for column in _DISPATCH_CONTEXT_LOAD_COLUMNS:
        measured = context_load[column]
        context_cells.append(UNMEASURED_COLUMN_TOKEN if measured is None else str(int(measured)))
    row = (
        f'{timestamp},{cause},{total_tokens},{tool_uses},{duration_ms},'
        + ','.join(context_cells)
    )

    if path.exists():
        existing = path.read_text(encoding='utf-8')
        if not existing.endswith('\n'):
            existing += '\n'
        new_content = existing + row + '\n'
    else:
        # Header documents the column contract for downstream readers.
        #
        # Deliberately a LITERAL, not f-string-derived from
        # _DISPATCH_CONTEXT_LOAD_COLUMNS: the lattice-completeness contract test
        # recovers this column set by scraping the `rows[]{...}` literal out of
        # this source file, and an interpolated header hands that scraper the
        # interpolation expression instead of the columns — silently defeating a
        # population-derived guard. The literal and the tuple are held in
        # lock-step by the two tests that pin them (the header-order test reads
        # this string, the positional test reads the tuple-built row).
        header = (
            f'plan_id: {plan_id}\n'
            f'phase: {phase}\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
            'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:\n'
        )
        new_content = header + row + '\n'

    atomic_write_file(path, new_content)

    # Count rows by counting the data lines (everything after the header lines).
    row_count = sum(
        1
        for line in new_content.splitlines()
        if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
    )

    result: dict[str, object] = {
        'status': 'success',
        'plan_id': plan_id,
        'phase': phase,
        'termination_cause': cause,
        'total_tokens': total_tokens,
        'tool_uses': tool_uses,
        'duration_ms': duration_ms,
    }
    # A context-load column the caller did not measure is ABSENT from the result,
    # mirroring what was written to the row. Returning 0 would re-assert, in the
    # caller's own reply, the measurement the row deliberately declines to claim.
    # A measured zero IS returned, as 0.
    unmeasured_columns: list[str] = []
    for column in _DISPATCH_CONTEXT_LOAD_COLUMNS:
        measured = context_load[column]
        if measured is None:
            unmeasured_columns.append(column)
        else:
            result[column] = int(measured)
    result['unmeasured_context_load_columns'] = ','.join(unmeasured_columns)
    result['timestamp'] = timestamp
    result['rows_recorded'] = row_count
    result['dispatch_boundary_file'] = str(path.relative_to(get_plan_dir(plan_id)))
    return result


def _phase_window_lookup(plan_id: str) -> list[tuple[str, datetime, datetime]]:
    """Return [(phase, start, end), ...] for phases with full timestamps."""
    data = read_metrics_raw(plan_id)
    windows: list[tuple[str, datetime, datetime]] = []
    for phase_name in PHASE_NAMES:
        phase_data = data.get('phases', {}).get(phase_name)
        if not phase_data:
            continue
        start_str = phase_data.get('start_time')
        end_str = phase_data.get('end_time')
        if not start_str or not end_str:
            continue
        try:
            start_dt = datetime.fromisoformat(str(start_str))
            end_dt = datetime.fromisoformat(str(end_str))
        except (ValueError, TypeError):
            continue
        windows.append((phase_name, start_dt, end_dt))
    return windows


def _run_normalized_tokens_op(
    session_id: str,
    windows: list[tuple[str, datetime, datetime]],
) -> tuple[dict[str, dict[str, int]] | None, dict[str, int], str | None]:
    """Invoke the platform-runtime ``metrics normalized-tokens`` op.

    The runtime owns the entire transcript engine (transcript discovery, JSONL
    parse, ``message.usage`` four-field parse, ``<usage>`` tag parse, cache-pricing
    weights). ``manage-metrics`` never parses a transcript itself — it hands the
    op the phase windows, lets the runtime write the per-phase normalized result
    to a JSON sidecar, then reads that file and persists the numbers.

    Returns ``(per_phase, counters, status)`` where:

    - ``per_phase`` maps each phase to its normalized bucket (or ``None`` on a
      ``no-op`` — no transcript — or any failure), and
    - ``counters`` carries the runtime's attribution counters (empty on no-op), and
    - ``status`` is the runtime op's TOON ``status`` field (``success`` / ``no-op``
      / ``error``) or ``None`` when the op could not be invoked.
    """
    serialized_windows = [[name, start.isoformat(), end.isoformat()] for name, start, end in windows]

    with tempfile.TemporaryDirectory(prefix='metrics-norm-tokens-') as tmpdir:
        windows_file = Path(tmpdir) / 'windows.json'
        output_file = Path(tmpdir) / 'normalized.json'
        windows_file.write_text(json.dumps(serialized_windows), encoding='utf-8')

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    '.plan/execute-script.py',
                    'plan-marshall:platform-runtime:platform_runtime',
                    'metrics',
                    'normalized-tokens',
                    '--session-id',
                    session_id,
                    '--windows-file',
                    str(windows_file),
                    '--output-file',
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return None, {}, None

        try:
            parsed = parse_toon(result.stdout)
        except (ValueError, KeyError):
            parsed = {}
        status = parsed.get('status')

        if status != 'success' or not output_file.is_file():
            return None, {}, status

        try:
            per_phase = json.loads(output_file.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return None, {}, status
        if not isinstance(per_phase, dict):
            return None, {}, status

        counters = {
            key: int(parsed[key])
            for key in (
                'message_count',
                'subagent_phases_attributed',
                'subagent_calls_attributed',
                'subagent_transcripts_walked',
                'four_field_phases_attributed',
                # Run-level count of tool names outside the classifier's
                # population-derived domain — non-zero means a new tool name was
                # counted rather than dropped, and the classifier needs extending.
                'unclassified_tool_calls',
            )
            if isinstance(parsed.get(key), (int, str)) and str(parsed.get(key)).isdigit()
        }
        return per_phase, counters, status


_INLINE_MAIN_CONTEXT_FIELDS = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens')

# Exploration-share buckets, in report order. ``exploration + work + execute`` is
# the share denominator; ``orchestration`` and ``unclassified`` are carried so the
# buckets partition the observed tool-call population and the exclusion from the
# ratio stays auditable.
#
# SOURCE OF TRUTH is the platform-runtime contract — ``Runtime.metrics_normalized_
# tokens.__doc__``'s per-phase bucket declaration (mirrored in
# ``platform-runtime/standards/contract.md``). This tuple is a hand-mirror of that
# declaration because manage-metrics runs in a DIFFERENT process from the runtime
# producer and cannot import ``claude_runtime._TOOL_BUCKET_NAMES`` across that
# boundary. The mirror is held honest by the contract-drift test
# ``test_exploration_buckets_match_platform_runtime_contract`` in
# ``test/plan-marshall/manage-metrics/test_manage_metrics.py``, which parses the
# same contract docstring and fails loudly when a bucket is added on either side —
# so a new bucket cannot silently under-persist or under-render here.
_EXPLORATION_BUCKETS = ('exploration', 'work', 'execute', 'orchestration', 'unclassified')

# The per-phase counter fields the platform-runtime transcript engine supplies.
# Persisted and rendered on a PRESENCE test, never a truthiness test — see the
# render-guard divergence note at the per-phase render.
_EXPLORATION_COUNTER_FIELDS = tuple(
    f'{bucket}_{measure}'
    for bucket in _EXPLORATION_BUCKETS
    for measure in ('tool_calls', 'result_bytes')
)

# The cache-read attribution group: one attributed field per byte source plus the
# single residual. DERIVED over ``_EXPLORATION_BUCKETS`` for the same reason the
# counter fields are — a bucket added there cannot leave this group behind — with
# ``cache_read_unattributed`` appended as the one member that is not per-bucket.
#
# SOURCE OF TRUTH is the platform-runtime contract — ``Runtime.metrics_normalized_
# tokens.__doc__``'s per-phase bucket declaration (mirrored in
# ``platform-runtime/standards/contract.md``). The residual is part of the group,
# never an optional extra: the attributed parts plus the residual reconcile
# EXACTLY to the phase's recorded ``cache_read_input_tokens``, so dropping the
# residual would silently turn a partial split into an apparently complete one.
_CACHE_READ_ATTRIBUTION_FIELDS = (
    *(f'cache_read_attributed_{bucket}' for bucket in _EXPLORATION_BUCKETS),
    'cache_read_unattributed',
)

# Exploration sub-sources, in report order. They re-cut the ``exploration``
# bucket's payload bytes by what each call TARGETED — code an index could answer
# vs a workflow/standard document that must stay resident — and ``unattributed``
# is the fail-open member for a call with no recoverable target path.
#
# SOURCE OF TRUTH is the platform-runtime contract — ``Runtime.metrics_normalized_
# tokens.__doc__``'s per-phase bucket declaration (mirrored in
# ``platform-runtime/standards/contract.md``). Held honest by the contract-drift
# test ``test_exploration_subsource_fields_match_platform_runtime_contract``.
_EXPLORATION_SUBSOURCES = ('index_answerable', 'doc_residency', 'unattributed')

# Deliberately SEPARATE from ``_EXPLORATION_COUNTER_FIELDS``, which stays a
# ten-member ``{bucket}_{measure}`` product. The sub-sources carry the ``_bytes``
# suffix rather than ``_result_bytes`` precisely so that family's derivation
# cannot pick them up: they partition ONE bucket's bytes, they are not a sixth
# bucket, and there is no ``_tool_calls`` counterpart.
_EXPLORATION_SUBSOURCE_FIELDS = tuple(
    f'exploration_{sub}_bytes' for sub in _EXPLORATION_SUBSOURCES
)

# Every transcript-supplied per-phase field that is persisted and rendered on a
# PRESENCE test rather than a truthiness test, in report order. The three groups
# stay separately named above (each has its own contract-drift test and its own
# key-set contract); this is the single iteration order both the persist site
# (``cmd_enrich``) and the render site (``cmd_generate``) walk, so the presence
# rule cannot be applied to one group and forgotten on another.
_PRESENCE_PERSISTED_FIELDS = (
    *_EXPLORATION_COUNTER_FIELDS,
    *_EXPLORATION_SUBSOURCE_FIELDS,
    *_CACHE_READ_ATTRIBUTION_FIELDS,
)

# The "unattributed" residuals among the presence-persisted fields, DERIVED from
# that set rather than hand-listed — so a new residual added to any source group
# is discovered here instead of silently falling through the render loop to the
# generic (denominator-less) label, which would regress D1's separation. Every
# member MUST carry a denominator-bearing render spec in ``_UNATTRIBUTED_RENDER``;
# the contract-drift test ``test_unattributed_render_map_covers_every_residual``
# fails loudly if the two ever diverge. Kept next to the derived set it guards.
_UNATTRIBUTED_RESIDUAL_FIELDS = frozenset(
    field for field in _PRESENCE_PERSISTED_FIELDS if 'unattributed' in field
)


def _inline_main_context_sum(phase_row: dict) -> int:
    """Sum a phase row's inline-attributable main-context usage.

    ``input_tokens + output_tokens + cache_creation_input_tokens`` —
    ``cache_read_input_tokens`` is EXCLUDED so the figure matches the
    dispatched-``<usage>`` total definition (fed via ``end-phase
    --total-tokens``, which also excludes cache reads). One derivation serves
    both signatures below: it is always written to
    ``inline_main_context_tokens``, and on the inline-only signature it is ALSO
    folded into ``total_tokens`` (which the row's
    ``total_tokens_population`` then labels ``inline``).
    """
    return sum(
        int(phase_row[field])
        for field in _INLINE_MAIN_CONTEXT_FIELDS
        if isinstance(phase_row.get(field), (int, float))
    )


def cmd_enrich(args: argparse.Namespace) -> dict:
    plan_id = require_valid_plan_id(args)
    session_id = args.session_id

    guard_error = _guard_plan_exists(plan_id)
    if guard_error is not None:
        return guard_error

    # Storage/aggregation role only: read this plan's own phase windows, hand them
    # to the platform-runtime transcript engine, and persist the normalized numbers
    # it returns. manage-metrics never parses a transcript itself.
    windows = _phase_window_lookup(plan_id)
    per_phase, counters, status = _run_normalized_tokens_op(session_id, windows)

    if per_phase is None:
        # no-op (no transcript on this target) or the op could not run — degrade
        # gracefully: nothing to enrich.
        return {
            'status': 'success',
            'plan_id': plan_id,
            'enriched': False,
            'message': f'No normalized-token data for session {session_id} (runtime status: {status})',
        }

    # Persist the runtime-computed per-phase normalized view. The runtime returns
    # both the four-field usage view (under the canonical message.usage keys) plus
    # the billing-weighted total, and the subagent <usage> attribution.
    data = read_metrics_raw(plan_id)
    data['session_message_count'] = counters.get('message_count', 0)
    data['updated'] = now_utc_iso()

    phases_state = data.setdefault('phases', {})

    for phase_name, bucket in per_phase.items():
        if not isinstance(bucket, dict):
            continue
        phase_row = phases_state.setdefault(phase_name, {})
        # Population DERIVED from the canonical label set the render walks, never
        # re-spelled here — see _FOUR_FIELD_USAGE_FIELDS.
        for field in _FOUR_FIELD_USAGE_FIELDS:
            if field in bucket:
                phase_row[field] = bucket[field]
        if 'billing_weighted_total' in bucket:
            phase_row['billing_weighted_total'] = bucket['billing_weighted_total']
        if 'subagent_total_tokens' in bucket:
            phase_row['subagent_total_tokens'] = bucket['subagent_total_tokens']
            phase_row['subagent_tool_uses'] = bucket.get('subagent_tool_uses', 0)
            phase_row['subagent_duration_ms'] = bucket.get('subagent_duration_ms', 0)
            phase_row['subagent_samples'] = bucket.get('subagent_samples', 0)

        # Transcript-supplied counters, written on a PRESENCE test. A runtime that
        # declines the transcript primitive supplies no counter at all, and
        # defaulting an absent counter to 0 would assert a measurement that was
        # never taken — making "never measured" indistinguishable from "measured,
        # and it explored nothing" (or, for the two derived groups, from "nothing
        # was index-answerable" and "the split was zero"). A MEASURED zero IS
        # persisted, as 0.
        for field in _PRESENCE_PERSISTED_FIELDS:
            if field in bucket:
                phase_row[field] = bucket[field]

        # Attribute the phase's inline main-context spend, and RECORD which
        # population the row's total_tokens ends up measuring.
        #
        # A phase that ran inline in the main context (phase-1-init, and the
        # recipe-inline refine/outline phases) produces no agent `<usage>`
        # envelope and no accumulator, so its closing phase-boundary omitted
        # --total-tokens and the row carries no total_tokens — yet enrich has
        # just attributed the parent-window `message.usage` data to it. Folding
        # that sum into total_tokens is DELIBERATE and stays: it is what keeps
        # the phase countable in the breakdown (the report reads n=6/6, not
        # n=5/6) and what keeps every downstream zero-token predicate off a
        # phase that really did cost something.
        #
        # What the fold must not do is present a main-context measurement under
        # a field named for the dispatched population, so it is accompanied by
        # two records, written together and never apart:
        #   * inline_main_context_tokens — the same figure under its own
        #     population-honest name, written on BOTH the inline-only and the
        #     mixed signature, so the inline measurement is never readable ONLY
        #     through a dispatched-population field.
        #   * total_tokens_population — the discriminator every render site and
        #     every consumer reads to know which population total_tokens
        #     measures on THIS row.
        #
        # The sum is input_tokens + output_tokens + cache_creation_input_tokens
        # ONLY — cache_read_input_tokens is EXCLUDED so the figure matches the
        # dispatched-phase `<usage>` total definition, which is fed via
        # end-phase --total-tokens and also excludes cache reads. Including
        # cache_read (two orders of magnitude larger — plan-13 archive: 1-init
        # 11.16M dominated by 11.09M cache_read) would over-count the inline row
        # by ~100x versus comparable dispatched rows. The four raw usage fields
        # stay persisted on the row above for billing analysis; only the derived
        # figure narrows.
        #
        # Explicit-wins throughout: a total_tokens already set by a dispatched
        # phase's `<usage>` / accumulator is truthy here and is NEVER
        # overwritten. The #812 end_time-presence check is untouched — a
        # timestamps-only inline close still carries its end_time marker.
        # The branch key is the DISCRIMINATOR, not the folded total, because the
        # inline-only branch below writes into the very field a truthiness test
        # would read. Keyed on `not total_tokens` alone, a SECOND enrich run over
        # the same metrics.toon sees the first run's own fold as a dispatched
        # total, falls through to the mixed branch, and re-stamps an inline-only
        # row `mixed` — a population claim no dispatch ever earned, which then
        # readmits the folded main-context figure to the dispatched maximum
        # (`_eligible_dispatched_measures`) and drops the Total's `(spans
        # populations)` marker. Reading `total_tokens_population` instead makes
        # the stamp idempotent: a re-run recognises its own prior fold. The fold
        # itself is unchanged. Explicit-wins survives intact — a genuine
        # dispatched total_tokens never carries POPULATION_INLINE, so it can
        # never select this branch.
        inline_main_context = _inline_main_context_sum(phase_row)
        already_inline = phase_row.get('total_tokens_population') == POPULATION_INLINE
        if already_inline or not phase_row.get('total_tokens'):
            # Inline-only signature: no dispatched total exists to preserve.
            if inline_main_context:
                phase_row['total_tokens'] = inline_main_context
                phase_row['inline_main_context_tokens'] = inline_main_context
                phase_row['total_tokens_population'] = POPULATION_INLINE
            else:
                phase_row['total_tokens_population'] = POPULATION_DISPATCHED
        elif inline_main_context:
            # Mixed signature (the 6-finalize shape): dispatched steps AND
            # inline main-context steps both ran in this window. total_tokens
            # stays the dispatched measurement; the inline part is a separate
            # field of a different population, not an addend.
            phase_row['inline_main_context_tokens'] = inline_main_context
            phase_row['total_tokens_population'] = POPULATION_MIXED
        else:
            phase_row['total_tokens_population'] = POPULATION_DISPATCHED

    write_metrics(plan_id, data)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'enriched': True,
        'message_count': counters.get('message_count', 0),
        'subagent_phases_attributed': counters.get('subagent_phases_attributed', 0),
        'subagent_calls_attributed': counters.get('subagent_calls_attributed', 0),
        'subagent_transcripts_walked': counters.get('subagent_transcripts_walked', 0),
        'four_field_phases_attributed': counters.get('four_field_phases_attributed', 0),
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Plan metrics collection and reporting', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # start-phase
    sp = subparsers.add_parser('start-phase', help='Record phase start timestamp', allow_abbrev=False)
    add_plan_id_arg(sp)
    add_phase_arg(sp)
    sp.set_defaults(func=cmd_start_phase)

    # end-phase
    ep = subparsers.add_parser(
        'end-phase', help='Record phase end timestamp and optional token data', allow_abbrev=False
    )
    add_plan_id_arg(ep)
    add_phase_arg(ep)
    ep.add_argument('--total-tokens', type=int, default=None, help='Total tokens from Task agent <usage>')
    ep.add_argument('--duration-ms', type=int, default=None, help='Duration in ms from Task agent <usage>')
    ep.add_argument('--tool-uses', type=int, default=None, help='Tool use count from Task agent <usage>')
    ep.add_argument(
        '--retrospective-tokens',
        type=int,
        default=None,
        help='Tokens attributable to the plan-retrospective dispatch within this phase window (recorded as the retrospective_tokens sub-field; default-absent)',
    )
    ep.set_defaults(func=cmd_end_phase)

    # generate
    gp = subparsers.add_parser('generate', help='Generate metrics.md from collected data', allow_abbrev=False)
    add_plan_id_arg(gp)
    gp.set_defaults(func=cmd_generate)

    # print-phase-breakdown
    pb_print = subparsers.add_parser(
        'print-phase-breakdown',
        help='Extract the ## Phase Breakdown section from metrics.md and persist it',
        description=(
            'Read metrics.md from the live plan directory, extract only the '
            '## Phase Breakdown section (table from heading to the next ## '
            'heading or EOF), and persist it. Default behavior writes the '
            "section verbatim to the plan-relative artifact path "
            f"'{PHASE_BREAKDOWN_DEFAULT_OUTPUT}' and emits a TOON envelope "
            '{status, plan_id, file, bytes_written}. Pass an explicit '
            "--output-file PATH to override the artifact path (plan-relative "
            'only; absolute paths are rejected). Pass --output-file - to use '
            'legacy stdout-only mode: the section is written verbatim to '
            'stdout with no TOON envelope (handy for ad-hoc inspection). On '
            'error (metrics.md missing, section missing, invalid path), a '
            'standard error TOON is emitted.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(pb_print)
    pb_print.add_argument(
        '--output-file',
        dest='output_file',
        default=None,
        help=(
            'Plan-relative artifact path to write the extracted section to '
            f"(default: '{PHASE_BREAKDOWN_DEFAULT_OUTPUT}'). Use '-' for "
            'stdout-only mode (legacy behavior, no TOON envelope).'
        ),
    )
    pb_print.set_defaults(func=cmd_print_phase_breakdown)

    # phase-boundary (fused end-phase + start-phase + generate)
    pb = subparsers.add_parser(
        'phase-boundary',
        help='Atomically end the previous phase, start the next, and regenerate metrics.md',
        description=(
            'Fused phase-transition recorder. Equivalent to running '
            '`end-phase --phase {prev}` (with the optional --total-tokens / '
            '--duration-ms / --tool-uses flags), then `start-phase --phase '
            '{next}`, then `generate`. Persisted output (work/metrics.toon and '
            'metrics.md) is identical to the three-call sequence.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(pb)
    pb.add_argument('--prev-phase', required=True, help='Phase name being closed (e.g. 1-init)')
    pb.add_argument('--next-phase', required=True, help='Phase name being entered (e.g. 2-refine)')
    pb.add_argument('--total-tokens', type=int, default=None, help='Total tokens forwarded to end-phase (optional)')
    pb.add_argument(
        '--duration-ms', type=int, default=None, help='Agent duration (ms) forwarded to end-phase (optional)'
    )
    pb.add_argument('--tool-uses', type=int, default=None, help='Tool use count forwarded to end-phase (optional)')
    pb.add_argument(
        '--retrospective-tokens',
        type=int,
        default=None,
        help='Tokens attributable to the plan-retrospective dispatch within the closing phase window (recorded as the retrospective_tokens sub-field; default-absent)',
    )
    pb.set_defaults(func=cmd_phase_boundary)

    # boundary-status (read-only resume-time half-stamped-boundary detector)
    bs = subparsers.add_parser(
        'boundary-status',
        help='Classify a phase boundary as stamped / missing / not_applicable (read-only)',
        description=(
            'Read-only resume-time detector for a half-stamped metrics phase '
            'boundary. Reads work/metrics.toon and classifies the boundary into '
            '--next-phase as one of: stamped (prev has start+end AND next has a '
            'start), missing (prev has a start but no end, OR next has no start), '
            'or not_applicable (a --prev-phase was supplied but never started). '
            'Performs ZERO mutation — it is the detection half of resume-time '
            'boundary reconciliation. The orchestrator calls it on cross-session '
            'resume before dispatching the current phase; on a missing verdict it '
            'stamps the boundary via `phase-boundary` even when the status '
            'transition already happened. Supply --prev-phase + --next-phase for '
            'a full boundary check, or --next-phase alone to check only the '
            '"current phase has no start" condition.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(bs)
    bs.add_argument('--prev-phase', default=None, help='Phase that should have been closed (optional)')
    bs.add_argument('--next-phase', required=True, help='Phase being entered on resume')
    bs.set_defaults(func=cmd_boundary_status)

    # reconcile-ledgers
    rl = subparsers.add_parser(
        'reconcile-ledgers',
        help='Reconcile the row ledgers against each other (read-only)',
        description=(
            'Deterministic cross-ledger reconciliation. Joins execution.toon\'s '
            'execution_log[] against each phase\'s '
            'work/metrics-dispatch-boundaries-{phase}.toon on phase and timestamp '
            'window, emitting one finding per row present in one ledger and '
            'absent from the other. The two partiality shapes are labelled '
            'distinctly: boundary_never_closed (the rows exist, the phase '
            'aggregate is missing) versus row_absent_from_* (a specific row has '
            'no partner). A phase the execution log structurally cannot cover is '
            'DECLARED, not reported as divergences. Publishes union_rows because '
            'neither ledger alone observed every dispatch. Mutates nothing.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(rl)
    rl.add_argument(
        '--window-seconds',
        type=int,
        default=DEFAULT_WINDOW_SECONDS,
        help=(
            'Maximum timestamp gap for pairing a row across the two ledgers '
            f'(default: {DEFAULT_WINDOW_SECONDS}). The boundary row carries no '
            'step_id, so the window is the only join available.'
        ),
    )
    rl.set_defaults(func=cmd_reconcile_ledgers)

    # accumulate-agent-usage
    acc = subparsers.add_parser(
        'accumulate-agent-usage',
        help='Persist running per-phase totals of subagent <usage> data',
        description=(
            'Add the supplied --total-tokens / --tool-uses / --duration-ms '
            'values to the per-phase accumulator file at '
            'work/metrics-accumulator-{phase}.toon, incrementing the samples '
            'counter. Initialises the file when absent and is idempotent across '
            'successive calls. cmd_end_phase / cmd_phase_boundary read this '
            'file as a fallback when their corresponding flags are omitted.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(acc)
    add_phase_arg(acc)
    acc.add_argument('--total-tokens', type=int, default=None, help='Subagent total_tokens to add to the running total')
    acc.add_argument('--tool-uses', type=int, default=None, help='Subagent tool_uses to add to the running total')
    acc.add_argument('--duration-ms', type=int, default=None, help='Subagent duration_ms to add to the running total')
    acc.add_argument(
        '--retrospective-tokens',
        type=int,
        default=None,
        help=(
            'Tokens attributable to the plan-retrospective dispatch to add to the running '
            'retrospective_tokens total (forwarded only when the just-returned step is the '
            'opt-in retrospective step; cmd_end_phase / cmd_phase_boundary read it back as a fallback)'
        ),
    )
    acc.set_defaults(func=cmd_accumulate_agent_usage)

    # record-dispatch-boundary
    rdb = subparsers.add_parser(
        'record-dispatch-boundary',
        help='Record one tabular row per phase Task dispatch termination',
        description=(
            'Append a TOON row to work/metrics-dispatch-boundaries-{phase}.toon '
            'capturing the termination cause of a phase Task dispatch '
            # Derived from the tuple, not hand-copied, so the help text cannot
            # drift from DISPATCH_TERMINATION_CAUSES — same guarantee `choices=`
            # (below) already gives. Eliminates a mirror rather than merely
            # guarding it.
            f'({" | ".join(DISPATCH_TERMINATION_CAUSES)}) '
            'and the '
            "dispatched agent's <usage> totals at the time of return. "
            '``clean_exit_queue_empty`` is the canonical value the '
            'orchestrator MUST use for a successful loop-exit (queue '
            'genuinely empty, verified by ``manage-tasks loop-exit-guard``); '
            'the recorder no longer accepts the legacy fallback value '
            '``unknown`` — missing or unrecognised causes are script errors. '
            'The orchestrator invokes this on every phase Task return so '
            'plan-retrospective can correlate agent-initiated re-dispatch '
            'events with [OUTCOME]-log coverage gaps.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(rdb)
    add_phase_arg(rdb)
    rdb.add_argument(
        '--termination-cause',
        required=True,
        choices=list(DISPATCH_TERMINATION_CAUSES),
        help='Why the phase Task dispatch terminated.',
    )
    rdb.add_argument(
        '--total-tokens',
        type=int,
        default=None,
        help="Subagent total_tokens at termination (from the agent's <usage>).",
    )
    rdb.add_argument(
        '--tool-uses',
        type=int,
        default=None,
        help="Subagent tool_uses at termination (from the agent's <usage>).",
    )
    rdb.add_argument(
        '--duration-ms',
        type=int,
        default=None,
        help="Subagent duration_ms at termination (from the agent's <usage>).",
    )
    rdb.add_argument(
        '--input-tokens',
        type=int,
        default=None,
        help=(
            'Dispatch context-load input_tokens at termination (message.usage). '
            f"Omit when unmeasured — the column is written as '{UNMEASURED_COLUMN_TOKEN}', "
            'NOT as 0, and the key is absent from the result TOON.'
        ),
    )
    rdb.add_argument(
        '--output-tokens',
        type=int,
        default=None,
        help=(
            'Dispatch context-load output_tokens at termination (message.usage). '
            f"Omit when unmeasured — written as '{UNMEASURED_COLUMN_TOKEN}', not 0."
        ),
    )
    rdb.add_argument(
        '--cache-read-input-tokens',
        type=int,
        default=None,
        help=(
            'Dispatch context-load cache_read_input_tokens at termination (message.usage). '
            f"Omit when unmeasured — written as '{UNMEASURED_COLUMN_TOKEN}', not 0."
        ),
    )
    rdb.add_argument(
        '--cache-creation-input-tokens',
        type=int,
        default=None,
        help=(
            'Dispatch context-load cache_creation_input_tokens at termination (message.usage). '
            f"Omit when unmeasured — written as '{UNMEASURED_COLUMN_TOKEN}', not 0."
        ),
    )
    rdb.set_defaults(func=cmd_record_dispatch_boundary)

    # enrich
    enr = subparsers.add_parser('enrich', help='Enrich metrics from JSONL transcript', allow_abbrev=False)
    add_plan_id_arg(enr)
    add_session_id_arg(enr)
    enr.set_defaults(func=cmd_enrich)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    if not result.pop('_print_only', False):
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
