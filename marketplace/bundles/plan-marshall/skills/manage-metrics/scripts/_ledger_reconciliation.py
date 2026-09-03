#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic cross-ledger reconciliation for one plan's token records.

One plan run produces THREE independent token ledgers, and no two of them cover
the same population:

===============================  ==========================================
Ledger                           What it can hold
===============================  ==========================================
``execution.toon``               One row per ``record-step`` call, for the
``execution_log[]``              phases in :data:`EXECUTION_LOG_PHASES` and
                                 NO others — its writer refuses any other
                                 phase outright.
``work/metrics-dispatch-         One row per dispatch termination, for the
boundaries-{phase}.toon``        dispatch classes that call
                                 ``record-dispatch-boundary``. The other
                                 classes are excluded BY DECLARATION.
``work/metrics.toon``            A per-phase AGGREGATE across all six
                                 canonical phases. It holds sums rather than
                                 rows, so it cannot say WHICH dispatches it
                                 summed — only how many times the phase
                                 closed (``close_count``), which this module
                                 reads as the re-entry signal.
===============================  ==========================================

The two ROW ledgers are written by independent call sites with no shared
transaction and no shared key — the boundary row carries no ``step_id`` — so a
step can land in one and not the other **in both directions**. A step that ran
four times can therefore appear twice in one ledger and three times in the
other, and only their UNION shows all four. Nothing told a reader to take the
union; this module says so per phase.

It is PURE ARITHMETIC and reserves no judgement for itself: it joins on phase
and timestamp window, emits one finding per row present in one ledger and absent
from the other, and labels the two partiality shapes distinctly —

* ``boundary_never_closed`` — the phase recorded dispatches but its terminal
  close never fired, so its ``metrics.toon`` row carries no ``end_time``. Its
  rows exist; what no close recorded is the phase's own summary of them.
* ``row_absent_from_*`` — a specific row has no partner in the other ledger.

Conflating those two would report a whole unclosed phase as a pile of orphan
rows, and an orphan row as a closing failure.

⛔ A structural absence is DECLARED, never emitted as a finding. Every boundary
row of a phase outside :data:`EXECUTION_LOG_PHASES` is absent from the execution
log by construction, and reporting each one as a divergence would bury the real
findings under noise the ledgers can never resolve.

⛔ An unreadable source degrades the affected block to ``not_evaluated`` with a
reason, never to a clean verdict: a missing ``execution.toon`` would otherwise
turn every boundary row into an orphan and read as a catastrophic divergence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from toon_parser import parse_toon

#: Sort placeholder for a row whose timestamp did not parse. Such rows sort last
#: via the leading boolean, so this value is never compared against a real one;
#: it exists only to keep the key's two branches the same type.
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

#: The manifest holding ``execution_log[]``, at the plan directory root.
MANIFEST_FILENAME = 'execution.toon'

#: The phases ``execution_log[]`` can hold rows for. A hand-mirror of
#: ``VALID_RECORD_PHASES`` in
#: ``manage-execution-manifest/scripts/_manifest_core.py``, which this skill runs
#: in a different process from and cannot import. Held honest by the
#: contract-drift test ``test_reconciliation_execution_log_phases_match_writer``.
EXECUTION_LOG_PHASES = ('5-execute', '6-finalize')

#: The literal an OMITTED ``execution_log[]`` token-attribution column carries.
#: A hand-mirror of ``UNMEASURED_COLUMN_TOKEN`` in
#: ``manage-execution-manifest/scripts/_manifest_core.py`` (the writer), which
#: this skill runs in a different process from and cannot import — the same
#: cross-skill mirror shape :data:`EXECUTION_LOG_PHASES` already uses, and the
#: same literal this skill's own ``manage-metrics.UNMEASURED_COLUMN_TOKEN``
#: defines for the dispatch-boundary row. Held honest by the contract-drift test
#: ``test_reconciliation_unmeasured_token_matches_writer``.
UNMEASURED_COLUMN_TOKEN = 'unmeasured'

#: The three states an ``execution_log[]`` token column can be read in. An
#: unmeasured or unrecognised cell contributes NOTHING to a sum and is reported
#: as its own state — coercing either to ``0`` is what makes an unmeasured column
#: read as a measured zero.
COLUMN_MEASURED = 'measured'
COLUMN_UNMEASURED = 'unmeasured'
COLUMN_UNRECOGNISED = 'unrecognised'

#: Default pairing window. Both writers fire around the same dispatch return —
#: ``record-dispatch-boundary`` at the termination, ``record-step`` once the
#: orchestrator has recorded the outcome — with intervening script calls between
#: them. Five minutes is wide enough to pair a genuine partner across that gap
#: and narrow enough not to pair two different dispatches of a busy phase. It is
#: the one tunable in this module and is exposed as ``--window-seconds``.
DEFAULT_WINDOW_SECONDS = 300

#: Finding kinds. Each names WHICH ledger lacks the row, so a reader never has to
#: infer the direction from the surrounding text.
FINDING_ABSENT_FROM_BOUNDARY = 'row_absent_from_boundary_ledger'
FINDING_ABSENT_FROM_EXECUTION_LOG = 'row_absent_from_execution_log'
FINDING_BOUNDARY_NEVER_CLOSED = 'boundary_never_closed'
FINDING_PHASE_RE_ENTERED = 'phase_re_entered'

#: Per-phase evaluation states.
STATE_EVALUATED = 'evaluated'
STATE_STRUCTURALLY_EXCLUDED = 'structurally_excluded'
STATE_NOT_EVALUATED = 'not_evaluated'


def _parse_iso(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp to an AWARE datetime, tolerating a ``Z`` suffix.

    A stamp carrying no offset parses naive, and mixing naive and aware values in
    one phase makes ``_row_sort_key``'s sort and ``pair_rows``' subtraction raise
    ``TypeError`` — an uncaught crash, where this module's rule is that an input
    it cannot use degrades to a reported state rather than taking the process
    down. A naive stamp is therefore read as UTC, which is what both writers emit
    explicitly (``now_utc_iso()`` appends ``Z``; the boundary writer appends
    ``+00:00``) and so is the only reading consistent with the corpus.

    Returns ``None`` on anything unparseable, which callers surface as an
    unpairable row rather than dropping it.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _row_sort_key(row: dict[str, Any]) -> tuple[bool, datetime, str, str, int]:
    """A TOTAL ordering over rows, derived entirely from the row's own values.

    Sorting on the timestamp alone is not total: Python's sort is stable, so two
    rows sharing a timestamp keep the order they arrived in — which is the
    manifest's row order, not a property of the data. Downstream that order
    decides which of the tied rows ends up unpaired, so the same corpus written
    in a different order would name a different dispatch in the emitted finding.

    The tie-breakers are the remaining recorded fields, in a fixed order, so two
    rows can share a key only if they are indistinguishable on every value this
    module reads — in which case which one is reported is genuinely immaterial.
    """
    return (
        row['parsed_timestamp'] is None,
        row['parsed_timestamp'] or _EPOCH,
        str(row.get('step_id') or ''),
        str(row.get('termination_cause') or ''),
        int(row.get('total_tokens') or 0),
    )


def _as_int(value: object) -> int:
    """Coerce a TOON scalar to int, defaulting to 0. Booleans are not counts."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip('-').isdigit():
        return int(value)
    return 0


def read_token_column(value: object) -> tuple[int, str]:
    """Read an ``execution_log[]`` token column into ``(value, state)``.

    The three-state read the writer's absence-vs-zero contract requires. It keeps
    an int-parsing FLOOR — every historical all-numeric row parses exactly as it
    did before — and refuses to coerce the other two states into it:

    * an int (or an all-digit string) is :data:`COLUMN_MEASURED`, including a
      measured ``0``;
    * :data:`UNMEASURED_COLUMN_TOKEN` is :data:`COLUMN_UNMEASURED` — the writer
      recorded that nobody measured this column;
    * anything else, including an absent column, is :data:`COLUMN_UNRECOGNISED`.

    ⛔ The non-measured states carry ``0`` as their numeric placeholder so the
    row shape stays uniform, but the STATE is what a caller must branch on. Using
    the number alone re-creates the defect: ``_as_int`` returned ``0`` for the
    token, and that zero re-entered the reconciliation looking measured.
    """
    if isinstance(value, bool):
        return 0, COLUMN_UNRECOGNISED
    if isinstance(value, int):
        return value, COLUMN_MEASURED
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == UNMEASURED_COLUMN_TOKEN:
            return 0, COLUMN_UNMEASURED
        if stripped.lstrip('-').isdigit():
            return int(stripped), COLUMN_MEASURED
    return 0, COLUMN_UNRECOGNISED


def load_execution_log(plan_dir: Path) -> tuple[list[dict[str, Any]] | None, str]:
    """Return ``execution_log[]`` rows and a read state.

    ``None`` rows mean the manifest could not be read — distinct from a manifest
    that holds an empty log, which is a real, readable zero. The caller must not
    collapse the two: an unreadable manifest makes every boundary row look like
    an orphan.

    Args:
        plan_dir: The plan directory.

    Returns:
        ``(rows, reason)`` — ``rows`` is ``None`` on any read failure, and
        ``reason`` names it (empty string when the read succeeded).
    """
    path = plan_dir / MANIFEST_FILENAME
    if not path.exists():
        return None, f'{MANIFEST_FILENAME} not found'
    try:
        raw = path.read_text(encoding='utf-8')
    except OSError as exc:
        return None, f'{MANIFEST_FILENAME} unreadable: {exc}'
    parsed = parse_toon(raw)
    if not isinstance(parsed, dict):
        return None, f'{MANIFEST_FILENAME} did not parse as a mapping'
    rows = parsed.get('execution_log')
    if rows is None:
        return [], ''
    if not isinstance(rows, list):
        return None, 'execution_log is present but is not a row list'
    return [row for row in rows if isinstance(row, dict)], ''


def execution_rows_for_phase(rows: list[dict[str, Any]], phase: str) -> list[dict[str, Any]]:
    """Return this phase's execution-log rows, normalised and timestamp-ordered.

    A row with an unparseable timestamp is KEPT, with ``parsed_timestamp``
    ``None`` and ``timestamp`` left at its raw recorded value: it is a real
    recorded dispatch, and dropping it would silently shrink the population the
    reconciliation reports on. It can never pair (pairing needs two parsed
    timestamps), so it surfaces as an unpaired row — the honest outcome for a row
    whose position nothing can establish — and its finding still quotes the raw
    value, so a reader can see what could not be parsed.

    Each row also carries ``total_tokens_state`` (:func:`read_token_column`), so
    a downstream consumer can tell a MEASURED ``0`` from a column the writer
    recorded as unmeasured. The numeric field stays an int either way, which is
    what keeps the sort key and every arithmetic consumer unchanged; the state is
    the field that must be read before the number is presented as a measurement.
    """
    selected = [row for row in rows if str(row.get('phase')) == phase]
    normalised: list[dict[str, Any]] = []
    for row in selected:
        total_tokens, token_state = read_token_column(row.get('total_tokens'))
        normalised.append(
            {
                'step_id': str(row.get('step_id') or ''),
                'timestamp': row.get('timestamp'),
                'parsed_timestamp': _parse_iso(row.get('timestamp')),
                'total_tokens': total_tokens,
                'total_tokens_state': token_state,
                'outcome': str(row.get('outcome') or ''),
            }
        )
    return sorted(normalised, key=_row_sort_key)


def load_boundary_rows(path: Path) -> list[dict[str, Any]]:
    """Parse a phase's dispatch-boundary file into normalised rows.

    The row schema is positional —
    ``timestamp,termination_cause,total_tokens,tool_uses,duration_ms,+4`` — and
    the two header lines plus the ``rows[]`` schema line are skipped, matching
    the reader ``manage-metrics`` already uses for the sum. A short or malformed
    row is skipped rather than partially parsed.
    """
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding='utf-8')
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(('plan_id:', 'phase:', 'rows[]')):
            continue
        columns = stripped.split(',')
        if len(columns) < 3:
            continue
        timestamp = columns[0].strip()
        rows.append(
            {
                'timestamp': timestamp,
                'parsed_timestamp': _parse_iso(timestamp),
                'termination_cause': columns[1].strip(),
                'total_tokens': _as_int(columns[2].strip()),
            }
        )
    return sorted(rows, key=_row_sort_key)


def pair_rows(
    execution_rows: list[dict[str, Any]],
    boundary_rows: list[dict[str, Any]],
    window_seconds: int,
) -> tuple[list[tuple[dict, dict]], list[dict], list[dict]]:
    """Pair the two ledgers' rows on timestamp proximity, MAXIMALLY.

    The boundary row carries no ``step_id``, so the timestamp window is the only
    join available. Every execution-log row is eligible to pair with every
    boundary row inside the window, and this returns a pairing of **maximum
    size** — the fewest possible unpaired rows on both sides.

    ⛔ Maximum matching rather than nearest-first greedy, because the unpaired
    rows are what this module REPORTS. Greedy lets a row take a closer partner
    that another row needed, stranding both and emitting two findings where a
    perfect pairing exists: with boundary rows at t=0 and t=250 and execution
    rows at t=240 and t=500 inside a 300 s window, t=240 takes t=250 (gap 10)
    over t=0 (gap 240), and both remaining rows are reported absent although each
    has a legal partner. A finding that is an artefact of the pairing order is a
    false signal about the ledgers — precisely the class this verb exists to
    surface, manufactured by the verb itself.

    The reported sets do not depend on input order: this function sorts both row
    lists by a TOTAL key derived from the rows' own values (see
    :func:`_row_sort_key`), so a corpus written in any order produces the same
    result — and the guarantee holds for any caller, not only for the two readers
    that happen to sort already.

    ⚠ **What is guaranteed is the SIZE of the matching, not which rows fill it.**
    A corpus routinely admits several maximum matchings whose unpaired sets
    differ — measured at roughly a quarter of small random corpora — and the
    unpaired rows are what become findings, carrying a ``step_id`` and a token
    figure. So a finding identifies *a* row that could not be paired, never *the*
    divergent dispatch: where several rows were equally pairable, which one is
    named is settled by the traversal, not by the ledgers. Read the per-phase
    counts, which are exact, in preference to any single row's identity. This is
    inherent to reporting unpaired rows under a maximum matching and is a stated
    limit of this verb rather than a defect in it.

    Args:
        execution_rows: This phase's normalised execution-log rows.
        boundary_rows: This phase's normalised dispatch-boundary rows.
        window_seconds: Maximum absolute timestamp gap for a pair.

    Returns:
        ``(pairs, unpaired_execution, unpaired_boundary)``.
    """
    # Sort here rather than trusting the caller. Both production readers already
    # return sorted rows, so this is a no-op on the real path — but the stability
    # guarantee below is a property of the RESULT, and leaving it to the callers
    # would mean a future one passing rows in manifest order silently restores
    # the order-dependence this sort exists to remove.
    execution_rows = sorted(execution_rows, key=_row_sort_key)
    boundary_rows = sorted(boundary_rows, key=_row_sort_key)

    # Eligibility: a row with no parsable timestamp can never pair, and is left
    # for the caller to report — the honest outcome for a row whose position
    # nothing can establish.
    candidates: list[list[int]] = []
    for execution_row in execution_rows:
        execution_time = execution_row['parsed_timestamp']
        if execution_time is None:
            candidates.append([])
            continue
        eligible = []
        for index, boundary_row in enumerate(boundary_rows):
            boundary_time = boundary_row['parsed_timestamp']
            if boundary_time is None:
                continue
            if abs((execution_time - boundary_time).total_seconds()) <= window_seconds:
                eligible.append(index)
        candidates.append(eligible)

    # Kuhn's algorithm: for each execution row, try to find an augmenting path
    # through the eligibility graph, displacing earlier matches where doing so
    # frees a partner for them elsewhere. Row counts per phase are small, so the
    # O(V·E) cost is irrelevant beside the correctness of the reported set.
    matched_boundary: dict[int, int] = {}

    def _augment(execution_index: int, visited: set[int]) -> bool:
        for boundary_index in candidates[execution_index]:
            if boundary_index in visited:
                continue
            visited.add(boundary_index)
            holder = matched_boundary.get(boundary_index)
            if holder is None or _augment(holder, visited):
                matched_boundary[boundary_index] = execution_index
                return True
        return False

    for execution_index in range(len(execution_rows)):
        _augment(execution_index, set())

    matched_execution = {ex: bd for bd, ex in matched_boundary.items()}
    pairs = [
        (execution_rows[ex], boundary_rows[bd])
        for ex, bd in sorted(matched_execution.items())
    ]
    unpaired_execution = [
        row for index, row in enumerate(execution_rows) if index not in matched_execution
    ]
    unpaired_boundary = [
        row for index, row in enumerate(boundary_rows) if index not in matched_boundary
    ]
    return pairs, unpaired_execution, unpaired_boundary


def _phase_findings(
    phase: str,
    unpaired_execution: list[dict],
    unpaired_boundary: list[dict],
    structurally_excluded: bool,
) -> list[dict[str, Any]]:
    """One finding per unpaired row, in each direction.

    An execution-log finding publishes ``total_tokens_state`` beside its
    ``total_tokens``. Without it a row whose token column the writer recorded as
    UNMEASURED is reported carrying ``0``, and a reader has no way to tell that
    from a dispatch that genuinely spent nothing — the same absence-read-as-zero
    conflation the column state exists to end, arriving through the finding.
    """
    findings: list[dict[str, Any]] = []
    for row in unpaired_execution:
        findings.append(
            {
                'finding': FINDING_ABSENT_FROM_BOUNDARY,
                'phase': phase,
                'step_id': row['step_id'],
                'timestamp': row['timestamp'],
                'total_tokens': row['total_tokens'],
                'total_tokens_state': row.get('total_tokens_state', COLUMN_MEASURED),
                'detail': (
                    'recorded by record-step with no dispatch-boundary row in the window — '
                    'either the dispatch registers no boundary (a declared exclusion class) '
                    'or the boundary write was missed'
                ),
            }
        )
    if structurally_excluded:
        return findings
    for row in unpaired_boundary:
        findings.append(
            {
                'finding': FINDING_ABSENT_FROM_EXECUTION_LOG,
                'phase': phase,
                'step_id': '',
                'timestamp': row['timestamp'],
                'total_tokens': row['total_tokens'],
                'total_tokens_state': COLUMN_MEASURED,
                'detail': (
                    'a dispatch terminated and recorded its usage, but no record-step row '
                    'names it in the window — this spend is invisible to any execution_log sum'
                ),
            }
        )
    return findings


def reconcile_phase(
    phase: str,
    execution_rows: list[dict[str, Any]] | None,
    boundary_rows: list[dict[str, Any]],
    metrics_row: dict[str, Any],
    window_seconds: int,
    execution_log_reason: str,
) -> dict[str, Any]:
    """Reconcile one phase's two row ledgers against each other and its aggregate.

    Returns a per-phase block carrying its evaluation ``state``, the row counts
    on each side, the ``union_rows`` count, and its findings. ``union_rows`` is
    published because neither ledger's own count is the number of times the
    phase's steps ran — only the union is, and nothing else says so.
    """
    structurally_excluded = phase not in EXECUTION_LOG_PHASES

    if execution_rows is None:
        return {
            'phase': phase,
            'state': STATE_NOT_EVALUATED,
            'reason': execution_log_reason,
            'execution_log_rows': 0,
            'boundary_rows': len(boundary_rows),
            'paired_rows': 0,
            'union_rows': len(boundary_rows),
            'findings': [],
        }

    pairs, unpaired_execution, unpaired_boundary = pair_rows(
        execution_rows, boundary_rows, window_seconds
    )
    findings = _phase_findings(phase, unpaired_execution, unpaired_boundary, structurally_excluded)

    # The two partiality shapes, labelled distinctly from an absent row.
    if boundary_rows and not metrics_row.get('end_time'):
        findings.append(
            {
                'finding': FINDING_BOUNDARY_NEVER_CLOSED,
                'phase': phase,
                'step_id': '',
                'timestamp': '',
                'total_tokens': sum(row['total_tokens'] for row in boundary_rows),
                'total_tokens_state': COLUMN_MEASURED,
                'detail': (
                    f'{len(boundary_rows)} dispatch-boundary row(s) recorded but the phase '
                    'row carries no end_time — the rows are present and no close recorded '
                    "the phase's own summary of them, which is not the same defect as an "
                    'absent row'
                ),
            }
        )
    close_count = _as_int(metrics_row.get('close_count'))
    if close_count > 1:
        findings.append(
            {
                'finding': FINDING_PHASE_RE_ENTERED,
                'phase': phase,
                'step_id': '',
                'timestamp': '',
                'total_tokens': 0,
                # A re-entry finding measures no tokens — the ``0`` is a shape
                # placeholder keeping the finding rows uniform, and the state
                # says so rather than letting it read as a measured zero.
                'total_tokens_state': COLUMN_UNMEASURED,
                'detail': (
                    f'the phase closed {close_count} times, so its metrics.toon totals are '
                    'cumulative across closes while both row ledgers are append logs — a '
                    'row-count comparison against the aggregate is only valid within one close'
                ),
            }
        )

    return {
        'phase': phase,
        'state': STATE_STRUCTURALLY_EXCLUDED if structurally_excluded else STATE_EVALUATED,
        'reason': (
            'execution_log cannot hold rows for this phase — its writer accepts only '
            f'{", ".join(EXECUTION_LOG_PHASES)}, so every boundary row here is absent from it '
            'by construction and is declared rather than reported'
            if structurally_excluded
            else ''
        ),
        'execution_log_rows': len(execution_rows),
        'boundary_rows': len(boundary_rows),
        'paired_rows': len(pairs),
        'union_rows': len(pairs) + len(unpaired_execution) + len(unpaired_boundary),
        'findings': findings,
    }
