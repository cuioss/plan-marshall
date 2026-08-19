#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Covers: start-phase, end-phase, generate, enrich, accumulate-agent-usage subcommands.

Tier 2 (direct import) tests for cmd_* functions, with 2 subprocess
tests retained for CLI plumbing verification.
"""


import importlib.util
import json
from pathlib import Path

from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_enrich,
    ns_start_phase,
)

from conftest import get_script_path  # noqa: I001

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')


# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location('manage_metrics', SCRIPT_PATH)


assert _spec is not None and _spec.loader is not None


manage_metrics = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(manage_metrics)


cmd_accumulate_agent_usage = manage_metrics.cmd_accumulate_agent_usage


cmd_end_phase = manage_metrics.cmd_end_phase


cmd_enrich = manage_metrics.cmd_enrich


cmd_generate = manage_metrics.cmd_generate


cmd_record_dispatch_boundary = manage_metrics.cmd_record_dispatch_boundary


cmd_start_phase = manage_metrics.cmd_start_phase


# =============================================================================
# Helpers
# =============================================================================


def _pin_start_time_to_past(plan_id: str, phase: str) -> None:
    """Pin a phase's ``start_time`` far in the past so the wall span deterministically
    exceeds any test's worked window.

    ``cmd_end_phase`` derives ``duration_seconds`` from ``end_time - start_time`` and
    feeds it to ``_clamp_worked_to_wall``. When start→end fire back-to-back the real
    wall span is ~0ms locally but can reach ~1000ms on a slow CI runner, which made
    the forwarded worked window clamp to a machine-dependent value (flaky). Pinning
    ``start_time`` to a fixed instant well before ``now`` makes the wall span always
    exceed the worked window, so the clamp is a deterministic no-op and the forwarded /
    accumulator ``duration_ms`` flows through unchanged. The dedicated
    ``TestClampWorkedToWall`` unit tests cover the down-clamp branch directly.
    """
    data = manage_metrics.read_metrics_raw(plan_id)
    data['phases'].setdefault(phase, {})['start_time'] = '2020-01-01T00:00:00+00:00'
    manage_metrics.write_metrics(plan_id, data)


# =============================================================================
# require_plan_exists guard fixtures
# =============================================================================
#
# TASK-1 added a require_plan_exists guard to every plan-scoped writer in
# manage-metrics.py (start-phase, end-phase, generate, phase-boundary,
# accumulate-agent-usage, enrich). The guard returns ``error: plan_not_found``
# unless the plan directory carries a ``status.json`` sentinel. The
# ``plan_context`` fixture creates plan dirs without that sentinel, so every
# positive test below would otherwise trip the guard.
#
# The autouse fixture below patches ``manage_metrics.require_plan_exists`` so
# that, during these tests, it auto-materialises the ``status.json`` sentinel for
# any plan whose dir exists but is not explicitly registered as "unseeded". This
# is the real guard chokepoint — it fires regardless of whether a test resolves
# its plan dir before or after calling the writer. Guard-negative tests register
# their plan_id via ``_register_unseeded`` so the patched guard lets the genuine
# ``plan_not_found`` branch run.

_UNSEEDED_PLAN_IDS: set[str] = set()


def _register_unseeded(plan_id: str) -> str:
    """Mark ``plan_id`` so the autouse guard-seeder leaves it un-sentinelled.

    Returns the plan_id for inline use. Negative guard tests call this so the
    patched ``require_plan_exists`` runs its genuine ``plan_not_found`` branch.
    """
    _UNSEEDED_PLAN_IDS.add(plan_id)
    return plan_id


def _unseeded_plan_dir(plan_context, plan_id: str) -> Path:
    """Create a plan dir WITHOUT the ``status.json`` sentinel (orphan plan dir).

    Goes straight to ``plans_dir`` (bypassing any seeding helper) so the guard's
    ``plan_not_found`` branch fires. Asserts the sentinel is absent to keep the
    negative tests honest if the seeding policy ever changes. The returned path
    equals ``manage_metrics.get_plan_dir(plan_id)`` under the ``plan_context``
    ``PLAN_BASE_DIR`` redirect, so it matches the ``plan_dir`` the guard reports.
    """
    plan_dir: Path = plan_context.plans_dir / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    assert not (plan_dir / 'status.json').exists(), 'negative test requires an unseeded plan dir'
    return plan_dir


def _phase_breakdown_header(md_content: str) -> str:
    """Return the header row of the ## Phase Breakdown table."""
    lines = md_content.splitlines()
    bd_idx = lines.index('## Phase Breakdown')
    for line in lines[bd_idx:]:
        if line.startswith('| Phase'):
            return line
    raise AssertionError('Phase Breakdown header row not found')


# =============================================================================
# Test: dispatch-boundary reconciliation (D1) — _read_dispatch_boundary_totals
# and the cmd_generate same-population max reconciliation
# =============================================================================


def _write_dispatch_boundaries(plan_context, plan_id: str, phase: str, totals: list[int]) -> Path:
    """Write a dispatch-boundaries file for ``phase`` with one row per entry in ``totals``.

    Mirrors the writer's header + CSV-row layout (see cmd_record_dispatch_boundary /
    data-format.md § Per-Dispatch Context-Load Attribution). Each row places the
    supplied total in the ``total_tokens`` column (position 2) with fixed filler in
    the surrounding columns. Returns the file path.
    """
    path: Path = manage_metrics._dispatch_boundary_path(plan_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f'plan_id: {plan_id}\n'
        f'phase: {phase}\n'
        'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
        'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:\n'
    )
    rows = ''.join(
        f'2026-05-08T14:{i:02d}:11Z,budget_yield,{total},38,412390,38000,4000,210000,12000\n'
        for i, total in enumerate(totals)
    )
    path.write_text(header + rows, encoding='utf-8')
    return path


# =============================================================================
# Test: enrich delegates to the platform-runtime normalized-tokens op
# =============================================================================
#
# manage-metrics no longer parses a transcript. cmd_enrich computes this plan's
# phase windows, invokes the platform-runtime `metrics normalized-tokens` op via
# subprocess, reads the per-phase JSON sidecar the op writes, and persists the
# normalized numbers. These tests patch the subprocess boundary so the op's
# behaviour is simulated without a real Claude transcript.


_ENRICH_TWO_PHASE_METRICS = (
    'plan_id: {plan_id}\n\n'
    'phases:\n'
    '  5-execute:\n'
    '    start_time: 2026-01-01T10:00:00+00:00\n'
    '    end_time: 2026-01-01T11:00:00+00:00\n'
)


class _FakeCompleted:
    """Minimal stand-in for subprocess.CompletedProcess carrying a TOON stdout."""

    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.returncode = 0
        self.stderr = ''


def _patch_runtime_op(monkeypatch, *, status: str, per_phase: dict | None, counters: dict | None):
    """Patch subprocess.run so the runtime-op call writes *per_phase* and returns a TOON.

    The fake reads the ``--output-file`` argument from the constructed argv and
    writes ``per_phase`` to it as JSON (mirroring what the real Claude runtime op
    does), then returns a CompletedProcess whose stdout is a TOON envelope with the
    requested ``status`` and ``counters``.
    """
    counters = counters or {}

    def _fake_run(argv, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        output_file = None
        for i, token in enumerate(argv):
            if token == '--output-file' and i + 1 < len(argv):
                output_file = argv[i + 1]
        if status == 'success' and per_phase is not None and output_file is not None:
            Path(output_file).write_text(json.dumps(per_phase), encoding='utf-8')
        lines = [f'status: {status}', 'operation: metrics normalized-tokens']
        for key, value in counters.items():
            lines.append(f'{key}: {value}')
        return _FakeCompleted('\n'.join(lines) + '\n')

    monkeypatch.setattr(manage_metrics.subprocess, 'run', _fake_run)


# =============================================================================
# Test: first-class partiality fields (Tier 2 - direct import)
# =============================================================================


def _recorded_phase_row() -> dict:
    """A phase row that satisfies the recorded predicate (carries an end_time).

    A canonical phase is "recorded" iff its metrics.toon row carries an
    ``end_time`` (the boundary-close marker). The duration/agent fields are
    incidental — only ``end_time`` drives the partiality verdict — but they
    keep the seeded row shaped like a real closed phase.
    """
    return {
        'start_time': '2020-01-01T00:00:00+00:00',
        'end_time': '2020-01-01T00:10:00+00:00',
        'duration_seconds': 600,
        'agent_duration_ms': 60000,
    }


# =============================================================================
# Test: record-dispatch-boundary (Tier 2 - direct import)
# =============================================================================


# The 5 newly added termination causes (3 phase-6 + 2 phase-4 outcomes) along
# with the canonical destination phase for each. The legacy 5-value set
# (voluntary_checkpoint, task_complete_returned_verbatim, harness_cancellation,
# error, clean_exit_queue_empty) is unchanged and already exercised implicitly
# wherever cmd_record_dispatch_boundary is invoked; the new tests focus on the
# extension.
_NEW_TERMINATION_CAUSES_WITH_PHASE = [
    ('step_complete', '6-finalize'),
    ('blocked_user_review', '6-finalize'),
    ('blocked_session_restart', '6-finalize'),
    ('task_batch_complete', '4-plan'),
    ('agent_returned', '4-plan'),
]


# =============================================================================
# Exploration-share bucket contract drift
# =============================================================================


def _contract_counter_keys() -> set[str]:
    """Parse the exploration-share counter key set out of the platform-runtime contract.

    manage-metrics runs in a DIFFERENT process from the runtime producer, so
    ``_EXPLORATION_BUCKETS`` cannot import ``claude_runtime._TOOL_BUCKET_NAMES``
    and is necessarily a hand-mirror. The key set is therefore DERIVED here from
    ``Runtime.metrics_normalized_tokens.__doc__`` — the published contract both
    sides are mirroring — rather than restated, so a bucket added on either side
    fails this assertion instead of silently under-persisting (producer writes a
    counter manage-metrics never reads) or under-rendering (report omits a bucket
    the producer emits).

    Mirrors ``_contract_bucket_keys`` in
    ``test/plan-marshall/platform-runtime/test_metrics_tokens.py``, which parses
    the same docstring for the producer-side assertion.
    """
    import re

    from runtime_base import Runtime

    doc = Runtime.metrics_normalized_tokens.__doc__ or ''
    match = re.search(r'\{phase_name:\s*\{(.*?)\}\}', doc, re.DOTALL)
    assert match is not None, 'contract docstring no longer declares a per-phase bucket shape'
    declared = {key.strip() for key in match.group(1).split(',') if key.strip()}
    return {k for k in declared if k.endswith('_tool_calls') or k.endswith('_result_bytes')}


def _contract_attribution_keys() -> set[str]:
    """Parse the cache-read attribution key set out of the platform-runtime contract.

    Same cross-process hand-mirror problem as ``_contract_counter_keys`` above, so
    the same remedy: the key set is DERIVED from the published contract docstring
    rather than restated, and a key added on either side fails loudly here.
    """
    import re

    from runtime_base import Runtime

    doc = Runtime.metrics_normalized_tokens.__doc__ or ''
    match = re.search(r'\{phase_name:\s*\{(.*?)\}\}', doc, re.DOTALL)
    assert match is not None, 'contract docstring no longer declares a per-phase bucket shape'
    declared = {key.strip() for key in match.group(1).split(',') if key.strip()}
    return {
        k for k in declared if k.startswith('cache_read_attributed_') or k == 'cache_read_unattributed'
    }


def _contract_subsource_keys() -> set[str]:
    """Parse the exploration sub-source key set out of the platform-runtime contract.

    The sub-sources carry the ``_bytes`` suffix but deliberately NOT
    ``_result_bytes``, precisely so the counter family's suffix derivation cannot
    pick them up — so this parse selects on exactly that discriminator.
    """
    import re

    from runtime_base import Runtime

    doc = Runtime.metrics_normalized_tokens.__doc__ or ''
    match = re.search(r'\{phase_name:\s*\{(.*?)\}\}', doc, re.DOTALL)
    assert match is not None, 'contract docstring no longer declares a per-phase bucket shape'
    declared = {key.strip() for key in match.group(1).split(',') if key.strip()}
    return {
        k
        for k in declared
        if k.startswith('exploration_')
        and k.endswith('_bytes')
        and not k.endswith('_result_bytes')
    }


# =============================================================================
# Token-field population lattice contract
# =============================================================================

_SKILL_DIR = Path(SCRIPT_PATH).parent.parent


_DATA_FORMAT_MD = _SKILL_DIR / 'standards' / 'data-format.md'


_SKILL_MD = _SKILL_DIR / 'SKILL.md'


# The populations a lattice row may name. A row that invents a population outside
# this set fails rather than silently widening the vocabulary.
#
# ``population-discriminated`` is the deliberate, single-member class for a field
# whose population VARIES per row and whose row therefore carries an explicit
# discriminator. Only ``total_tokens`` is in it (discriminated by
# ``total_tokens_population``); admitting it as a named class is what keeps the
# lattice from having to state one population for a field that has two — the
# exact mislabel the lattice exists to prevent.
_LATTICE_POPULATIONS = {
    'dispatched-subagent',
    'main-context-window',
    'per-dispatch',
    'derived-cost',
    'population-discriminated',
}


# Phase-row fields that carry timing / bookkeeping rather than a usage
# measurement. This is deliberately an EXCLUSION list: a newly-added persisted
# field counts as usage-bearing — and so must be named in the lattice — unless
# it is explicitly classified here. The failure direction is therefore "classify
# the new field", never "silently omit it".
_NON_USAGE_ROW_FIELDS = {
    'start_time',
    'end_time',
    'close_count',
    'duration_seconds',
    'agent_duration_ms',
    'agent_duration_seconds',
    'idle_duration_ms',
    'boundary_non_monotonic',
    # Names which population `total_tokens` measures on this row. It is
    # bookkeeping ABOUT a measurement, not a measurement, so it takes no lattice
    # row of its own — it is specified in data-format.md's Per-Phase Fields
    # table and is what makes `total_tokens`'s `population-discriminated`
    # lattice entry readable.
    'total_tokens_population',
    # The cumulative-vs-last-close row scope declaration, written by
    # `_close_phase_accumulating` on every close. Same class as
    # `total_tokens_population` and excluded for the same reason: it is
    # bookkeeping ABOUT the row's other values (which of them the close summed
    # and which it replaced), not a measurement of its own, and it is specified
    # in data-format.md's Per-Phase Fields table and its Per-Field Write
    # Semantics section.
    'value_scope',
    'cumulative_fields',
    'last_close_fields',
}


# Dispatch-boundary columns that carry no usage measurement.
_NON_USAGE_BOUNDARY_COLUMNS = {'timestamp', 'termination_cause'}


# Computed by cmd_record_dispatch_boundary and returned in its TOON, but never
# persisted — no assignment site exposes it to the source-derived sweep below,
# so it is named here to keep the lattice's coverage honest.
_RETURN_ONLY_USAGE_FIELDS = {'rows_recorded'}


def _script_source() -> str:
    return Path(SCRIPT_PATH).read_text(encoding='utf-8')


def _derive_boundary_columns(source: str) -> set[str]:
    """Recover the dispatch-boundary column set from the script's header literal.

    The writer builds the TOON-tabular header from a split string literal, and an
    earlier docstring carries an abbreviated ``rows[]{...}`` form. Every candidate
    is parsed and the abbreviated ones (which contain an ellipsis column) are
    dropped, so the column set comes from the real header rather than the prose.
    """
    import re

    candidates: list[set[str]] = []
    for match in re.finditer(r'rows\[\]\{(.*?)\}', source, re.DOTALL):
        raw = match.group(1).replace("'", '').replace('\n', '')
        columns = {c.strip() for c in raw.split(',') if c.strip()}
        if any(c.startswith('.') for c in columns):
            continue
        candidates.append(columns)
    assert candidates, 'no dispatch-boundary rows[] header literal found in the script'
    return max(candidates, key=len)


def _derive_phase_row_fields(source: str) -> set[str]:
    """Recover every literal field key the script assigns onto a phase row."""
    import re

    pattern = re.compile(
        r"(?:phase|phase_data|phase_row|phases\[phase_name\])\['([a-z_]+)'\]\s*="
    )
    return set(pattern.findall(source))


def _derive_accumulator_fields(source: str) -> set[str]:
    """Recover the accumulator's field key set from the reader's allow-list literal."""
    import re

    match = re.search(r'if key not in \{([^}]*)\}', source, re.DOTALL)
    assert match is not None, 'accumulator key allow-list literal not found in the script'
    return {k.strip().strip("'") for k in match.group(1).split(',') if k.strip()}


def _derived_usage_fields() -> set[str]:
    """The token/usage field population, derived from the script — never hand-listed.

    A newly-added token field enters this set automatically (through one of the
    tuples, the boundary header, an assignment site, or the accumulator allow-list)
    and therefore fails the lattice-completeness assertion until the contract
    document names it with a population and a rendered flag.
    """
    source = _script_source()
    derived: set[str] = set()
    derived |= set(manage_metrics._EXPLORATION_COUNTER_FIELDS)
    derived |= set(manage_metrics._INLINE_MAIN_CONTEXT_FIELDS)
    derived |= _derive_boundary_columns(source) - _NON_USAGE_BOUNDARY_COLUMNS
    derived |= _derive_phase_row_fields(source) - _NON_USAGE_ROW_FIELDS
    derived |= _derive_accumulator_fields(source)
    derived |= _RETURN_ONLY_USAGE_FIELDS
    return derived


def _lattice_section(content: str) -> str:
    """Return the Token-Field Population Lattice section of data-format.md."""
    lines = content.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == '## Token-Field Population Lattice':
            start = i
            break
    assert start is not None, 'data-format.md carries no Token-Field Population Lattice section'
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith('## '):
            end = j
            break
    return '\n'.join(lines[start:end])


def _parse_lattice_directions(content: str) -> dict[str, list[list[str]]]:
    """Parse the lattice's per-direction table rows, keyed by direction number."""
    import re

    directions: dict[str, list[list[str]]] = {}
    current: str | None = None
    for line in _lattice_section(content).splitlines():
        heading = re.match(r'^### Direction (\d+)', line)
        if heading:
            current = heading.group(1)
            directions.setdefault(current, [])
            continue
        if current is None or not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 5 or cells[0] == 'Field' or set(cells[0]) <= {'-', ' '}:
            continue
        directions[current].append(cells)
    return directions


def _row_field(cell: str) -> str | None:
    """Extract the backticked field name from a lattice row's first cell."""
    import re

    match = re.search(r'`([a-z_]+)`', cell)
    return match.group(1) if match else None


def _fields_missing_from_lattice(content: str, derived: set[str]) -> set[str]:
    """Return the derived fields the lattice fails to name (either direction)."""
    named = {
        field
        for rows in _parse_lattice_directions(content).values()
        for cells in rows
        if (field := _row_field(cells[0])) is not None
    }
    return derived - named


# =============================================================================
# --termination-cause documentation-site contract
# =============================================================================


def _parse_termination_cause_sites(content: str) -> list[tuple[str, set[str]]]:
    """Discover EVERY occurrence of the --termination-cause value list in SKILL.md.

    Occurrences are found by scanning the document, never by a hard-coded site
    count — a fourth documentation site added later is picked up automatically and
    must match the enum like the rest. Two shapes are recognised: the brace-pipe
    form used inside the fenced command blocks, and the nested bullet enumeration
    under the ``--termination-cause`` parameter.
    """
    import re

    sites: list[tuple[str, set[str]]] = []

    for idx, match in enumerate(re.finditer(r'--termination-cause \{([^}]*)\}', content)):
        values = {v.strip() for v in match.group(1).split('|') if v.strip()}
        sites.append((f'brace-form-{idx + 1}', values))

    lines = content.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith('- `--termination-cause`'):
            continue
        values = set()
        for follow in lines[i + 1 :]:
            if follow.startswith('- ') or follow.startswith('#'):
                break
            nested = re.match(r'^\s+- `([a-z_]+)`', follow)
            if nested:
                values.add(nested.group(1))
        sites.append((f'bullet-form-{i + 1}', values))

    return sites


# =============================================================================
# --termination-cause value-set mirrors in sibling documents
# =============================================================================
#
# SKILL.md is not the only document that enumerates the DISPATCH_TERMINATION_CAUSES
# value set in prose. Two siblings hand-copy the same set and can therefore drift
# from the parser's ``choices`` exactly as SKILL.md could:
#
#   * plan-retrospective/references/logging-gap-analysis.md — the analyst-facing
#     DISPATCH_TERMINATION_CAUSE rule's canonical value set. This one HAD drifted
#     to a six-value subset (the defect these guards close): an analyst following
#     the reference literally would emit a per-cause distribution that omits every
#     cause past the sixth.
#   * standards/data-format.md — the dispatch-boundary ``termination_cause`` enum
#     line under Per-Dispatch Context-Load Attribution.
#
# Both are pinned to the live tuple here, deriving BOTH sides: the documented set
# is parsed out of the markdown and the expected set is read from
# DISPATCH_TERMINATION_CAUSES. A hand-copied expected list in the test would
# reproduce the very defect the guard exists to catch, so neither side is
# hand-listed. Each positive assertion is paired with a negative control that
# drops one value and proves the guard fails — a guard that cannot fail is not a
# guard.

_LOGGING_GAP_ANALYSIS_MD = (
    _SKILL_DIR.parent / 'plan-retrospective' / 'references' / 'logging-gap-analysis.md'
)


def _parse_backticked_value_list(content: str, anchor: str) -> list[str]:
    """Parse the backticked value enumeration following ``anchor``, in order.

    Returned as a LIST (document order, not deduplicated) so a caller can reject
    a duplicated value — a set would silently collapse duplicates and let a
    document that lists the same value twice mirror the tuple by accident. The
    anchor must occur EXACTLY once: a second occurrence (e.g. a second
    documentation site the single-anchor read would ignore) is a parse ambiguity
    and fails here rather than passing over a shrunken read. Whitespace is
    collapsed first so the parse is insensitive to how the prose wraps; from the
    end of the anchor the maximal run of comma-separated backtick-quoted value
    tokens is consumed, stopping at the first character that is neither a
    backticked token nor a separator (the terminating period).
    """
    import re

    normalized = re.sub(r'\s+', ' ', content)
    occurrences = normalized.count(anchor)
    assert occurrences == 1, f'anchor must occur exactly once, found {occurrences}: {anchor!r}'
    tail = normalized[normalized.find(anchor) + len(anchor):]
    run = re.match(r'\s*((?:`[a-z_]+`\s*,?\s*)+)', tail)
    assert run is not None, f'no backticked value enumeration follows anchor: {anchor!r}'
    return re.findall(r'`([a-z_]+)`', run.group(1))


def _parse_backticked_value_set(content: str, anchor: str) -> set[str]:
    """The enumeration as a set, rejecting a duplicated value before dedup."""
    values = _parse_backticked_value_list(content, anchor)
    duplicates = sorted({v for v in values if values.count(v) > 1})
    assert not duplicates, f'enumeration lists duplicate value(s): {duplicates}'
    return set(values)


def _assert_documented_set_matches_enum(content: str, anchor: str) -> None:
    """The guard proper: the documented enumeration equals the parser's tuple.

    Extracted so the negative controls below can execute THIS assertion under
    ``pytest.raises`` — proving the guard's own failure path runs on a mutated
    document, not merely that the underlying parsed sets differ.
    """
    expected = set(manage_metrics.DISPATCH_TERMINATION_CAUSES)
    documented = _parse_backticked_value_set(content, anchor)
    assert documented == expected, (
        'documented termination_cause set disagrees with DISPATCH_TERMINATION_CAUSES '
        f'(missing, unexpected): {sorted(expected - documented)}, {sorted(documented - expected)}'
    )


# =============================================================================
# total_tokens population labelling
# =============================================================================
#
# `total_tokens` is named for a TOTAL, not for a population, yet `cmd_enrich`
# folds a MAIN-CONTEXT measurement into it on a phase that dispatched nothing.
# The fold is deliberate and load-bearing (it is what keeps a zero-dispatch
# phase countable at n=6/6 and keeps the downstream zero-token predicates off
# it), so these tests do NOT assert the fold away. They assert the property the
# fold must never violate: no rendered figure presents a main-context
# measurement under a dispatched-population label, and the phase's population is
# legible at the point of render.


def _run_enrich_with_buckets(plan_id: str, monkeypatch, buckets: dict) -> dict:
    """Drive the real cmd_enrich with only the runtime transcript seam stubbed.

    Mirrors ``test_phase_boundary_inline._run_inline_enrich``: everything from the
    four-field write through the inline derivation and the population stamp runs
    for real, so these tests exercise the production branch rather than a
    re-implementation of it.
    """

    counters = {'message_count': 7, 'four_field_phases_attributed': len(buckets)}

    def _fake_op(session_id, windows):
        return dict(buckets), counters, 'success'

    monkeypatch.setattr(manage_metrics, '_run_normalized_tokens_op', _fake_op)
    result: dict = cmd_enrich(ns_enrich(plan_id, 'sess-population'))
    return result


def _phase_row(plan_id: str, phase: str) -> dict:
    row: dict = manage_metrics.read_metrics_raw(plan_id)['phases'][phase]
    return row


# Four-field bucket carrying a non-zero inline attribution (input + output +
# cache_creation = 6,000; cache_read is excluded from the derivation).
_INLINE_BUCKET = {
    'input_tokens': 4000,
    'output_tokens': 1500,
    'cache_read_input_tokens': 900000,
    'cache_creation_input_tokens': 500,
}


_INLINE_SUM = 4000 + 1500 + 500


def _total_tokens_cell(report: str) -> str:
    """Return the Tokens cell of the Phase Breakdown ``**Total**`` row."""
    total_line = next(ln for ln in report.splitlines() if ln.startswith('| **Total**'))
    return [c.strip() for c in total_line.strip('|').split('|')][4]


# =============================================================================
# billing_weighted_total as a first-class cost figure
# =============================================================================


def _seed_billing_phases(plan_id: str, billing_by_phase: dict[str, int]) -> None:
    """Record the given phases with tokens, then stamp a billing figure on each."""
    for phase in billing_by_phase:
        cmd_start_phase(ns_start_phase(plan_id, phase))
        cmd_end_phase(ns_end_phase(plan_id, phase, total_tokens=10000))
    data = manage_metrics.read_metrics_raw(plan_id)
    for phase, billing in billing_by_phase.items():
        data['phases'][phase]['billing_weighted_total'] = billing
    manage_metrics.write_metrics(plan_id, data)
