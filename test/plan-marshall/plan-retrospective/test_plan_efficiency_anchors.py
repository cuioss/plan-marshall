#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Key-space and population guards for the plan-efficiency calibration anchors.

``plan-retrospective/references/plan-efficiency.md`` § "2. Calibration anchors
table" is keyed on ``(scope_estimate, change_type)``. Its key space is NOT a
free-form list: it is the exact cross-product of two enums that live in other
files entirely, and both axes drift independently of the document. Before this
guard existed the table had rotted in BOTH directions at once — 8 of its 12 rows
were dead keys (``cross_cutting`` / ``complex`` were never members of
``SCOPE_ESTIMATE_VALUES``; ``refactor`` was never a canonical change_type) while
27 live pairs had no row at all. Neither direction was visible at the table,
because a lookup table looks complete no matter how few rows it has.

The guards here are therefore deliberately two-directional and deliberately
derived:

1. **Set equality, not superset** — ``parsed - expected`` (dead / non-canonical
   keys) and ``expected - parsed`` (unanchored pairs) are asserted SEPARATELY, so
   a failure names which kind of rot occurred. A retired enum value fails until
   its dead row is removed; a new enum value fails until it is anchored or
   explicitly ``fallback``-graded.
2. **Both axes re-derived at check time** — ``scope_estimate`` is imported from
   ``SCOPE_ESTIMATE_VALUES`` (``manage-solution-outline.py``); ``change_type`` is
   parsed from the Change-Type Definitions table in ``change-types.md`` and
   unioned with the planning-lane router's ``_DEEP_CHANGE_TYPES``. Neither axis is
   hand-copied into this module, so the test cannot silently agree with a stale
   document.
3. **The guard's own discrimination is tested** — ``test_..._pair_is_removed``
   and ``test_..._non_canonical_key_is_added`` run the same parse-and-diff over a
   MUTATED copy of the document and assert the corresponding direction fires.
   Set equality that is never observed failing is an assertion nobody has proven
   can fail.

The second cluster guards the POPULATION the audit-side sibling anchors score.
``audit.py``'s ``lane-lever-effectiveness`` checkpoint verdict scores a plan's
summed ``metrics.toon`` ``total_tokens`` against
``THRESHOLDS['checkpoint_token_targets']``. What that sum measures is a
default-plus-exception population: dispatched-subagent on every phase row except
those whose ``total_tokens_population`` is ``inline``, where ``manage-metrics
enrich`` folds a main-context figure in. The guards below pin the two facts that
are actually true of the built code:

- the sum takes ``total_tokens`` and ONLY ``total_tokens`` — the derived-cost
  ``billing_weighted_total`` measures what a phase cost to buy, not work done,
  and folding it in would inflate every checkpoint verdict; and
- an ``inline``-labelled row IS included, so the sum spans populations and is
  NOT a dispatched-only total.

The second is stated as a guard rather than left implicit precisely because the
tempting claim — "the verdict is computed over the dispatched population only" —
is FALSE of the built code: the inline fold was deliberately retained, so
asserting a dispatched-only population would pin a false claim into the suite.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module

# ---------------------------------------------------------------------------
# Source anchors — every one of these is a LIVE source, never a copied value
# ---------------------------------------------------------------------------

#: The document under guard: its § 2 table is the anchors key space.
_ANCHORS_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'references'
    / 'plan-efficiency.md'
)

#: Authoritative source of the canonical change_type vocabulary.
_CHANGE_TYPES_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'ref-workflow-architecture'
    / 'standards'
    / 'change-types.md'
)

#: The audit skill's deterministic computation core (no executor notation — it
#: runs via a direct ``python3 .../audit.py``, so it is loaded by file location).
_AUDIT_SCRIPT = (
    PROJECT_ROOT
    / '.claude'
    / 'skills'
    / 'audit-archived-plan-retrospectives'
    / 'scripts'
    / 'audit.py'
)

#: Heading prefixes the section slicer anchors on.
_ANCHORS_SECTION_HEADING = '### 2. Calibration anchors table'
_CANONICAL_CHANGE_TYPE_HEADING = '## Change-Type Definitions'

#: The two key columns of the § 2 anchors table, in order.
_ANCHOR_KEY_COLUMNS = ('scope_estimate', 'change_type')

#: A pair guaranteed to be outside the live cross-product — both halves are
#: retired keys the § 2 "Remapped calibration data" note names. Used only to
#: mutate a COPY of the document in the discrimination test; its
#: outside-ness is asserted there rather than assumed.
_RETIRED_PAIR = ('cross_cutting', 'refactor')


# ---------------------------------------------------------------------------
# Markdown table parsing (shared by both axes and by the mutation tests)
# ---------------------------------------------------------------------------

_SEPARATOR_CELL_RE = re.compile(r'^:?-{2,}:?$')


def _heading_level(line: str) -> int:
    """Return the ATX heading level of ``line`` (0 when it is not a heading)."""
    stripped = line.lstrip()
    if not stripped.startswith('#'):
        return 0
    return len(stripped) - len(stripped.lstrip('#'))


def _table_cells(line: str) -> list[str]:
    """Split one markdown table row into trimmed cells (``[]`` when not a row)."""
    stripped = line.strip()
    if not (stripped.startswith('|') and stripped.endswith('|') and len(stripped) > 1):
        return []
    return [cell.strip() for cell in stripped[1:-1].split('|')]


def _is_separator_row(cells: list[str]) -> bool:
    """True for a ``|---|---|`` alignment row."""
    return bool(cells) and all(_SEPARATOR_CELL_RE.match(cell) for cell in cells)


def _section_block(content: str, heading_prefix: str) -> str:
    """Return the body under ``heading_prefix``, up to the next same-or-higher heading.

    Slicing to the owning section is what keeps the parser from picking up an
    unrelated table elsewhere in the document.
    """
    lines = content.splitlines()
    start: int | None = None
    level = 0
    for index, line in enumerate(lines):
        if line.startswith(heading_prefix):
            start = index + 1
            level = _heading_level(line)
            break
    if start is None:
        raise AssertionError(
            f'Section heading starting with {heading_prefix!r} not found. The '
            f'anchors guard slices the document by heading; a rename must be '
            f'reflected here.'
        )
    end = len(lines)
    for index in range(start, len(lines)):
        found = _heading_level(lines[index])
        if found and found <= level:
            end = index
            break
    return '\n'.join(lines[start:end])


def _parse_keyed_table(block: str, key_columns: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Return one key tuple per data row of the table headed by ``key_columns``.

    Cells are stripped of markdown code ticks so a backticked header/key
    (``| `analysis` |``) compares equal to its bare form. Rows are returned as a
    LIST (not a set) so duplicate keys stay observable.
    """
    rows: list[tuple[str, ...]] = []
    in_table = False
    width = len(key_columns)
    for line in block.splitlines():
        cells = _table_cells(line)
        if not cells:
            in_table = False
            continue
        if _is_separator_row(cells):
            continue
        key = tuple(cell.strip('`') for cell in cells[:width])
        if not in_table:
            if key == key_columns:
                in_table = True
            continue
        rows.append(key)
    return rows


def _anchor_keys(content: str) -> list[tuple[str, str]]:
    """Parse the § 2 anchors table into its ``(scope_estimate, change_type)`` keys."""
    block = _section_block(content, _ANCHORS_SECTION_HEADING)
    rows = _parse_keyed_table(block, _ANCHOR_KEY_COLUMNS)
    if not rows:
        raise AssertionError(
            f'No anchors table rows parsed from {_ANCHORS_DOC}. The § 2 table must '
            f'be headed by | {" | ".join(_ANCHOR_KEY_COLUMNS)} | ... |.'
        )
    return [(row[0], row[1]) for row in rows]


# ---------------------------------------------------------------------------
# Live axes — re-derived from their owning sources, never hand-copied
# ---------------------------------------------------------------------------


def _live_scope_estimates() -> set[str]:
    """The live ``scope_estimate`` enum, imported from its owning script."""
    outline = load_script_module(
        'plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py'
    )
    return set(outline.SCOPE_ESTIMATE_VALUES)


def _canonical_change_types() -> set[str]:
    """The canonical change_type vocabulary, parsed from change-types.md."""
    block = _section_block(
        _CHANGE_TYPES_DOC.read_text(encoding='utf-8'), _CANONICAL_CHANGE_TYPE_HEADING
    )
    keys = {row[0] for row in _parse_keyed_table(block, ('Key',))}
    if not keys:
        raise AssertionError(
            f'No canonical change types parsed from {_CHANGE_TYPES_DOC}; the '
            f'Change-Type Definitions table shape changed.'
        )
    return keys


def _router_change_types() -> set[str]:
    """The change_type values the live planning-lane router actually scores."""
    lane = load_script_module('plan-marshall', 'manage-status', '_cmd_planning_lane.py')
    return set(lane._DEEP_CHANGE_TYPES)


def _live_change_types() -> set[str]:
    """The live change_type axis: canonical vocabulary ∪ router-scored values."""
    return _canonical_change_types() | _router_change_types()


def _expected_cross_product() -> set[tuple[str, str]]:
    """The exact ``(scope_estimate, change_type)`` key space the table must carry."""
    return {
        (scope, change_type)
        for scope in _live_scope_estimates()
        for change_type in _live_change_types()
    }


def _key_diff(
    parsed: list[tuple[str, str]], expected: set[tuple[str, str]]
) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Return ``(extra, missing)`` — dead/non-canonical keys and unanchored pairs."""
    parsed_set = set(parsed)
    return parsed_set - expected, expected - parsed_set


# ---------------------------------------------------------------------------
# Document mutation helpers (used only against in-memory copies)
# ---------------------------------------------------------------------------


def _remove_anchor_row(content: str, key: tuple[str, str]) -> str:
    """Return ``content`` with the § 2 row for ``key`` deleted."""
    scope, change_type = key
    row_re = re.compile(rf'^\|\s*{re.escape(scope)}\s*\|\s*{re.escape(change_type)}\s*\|')
    kept = [line for line in content.splitlines() if not row_re.match(line)]
    if len(kept) == len(content.splitlines()):
        raise AssertionError(f'Mutation helper found no row to remove for {key}.')
    return '\n'.join(kept)


def _insert_anchor_row(content: str, key: tuple[str, str]) -> str:
    """Return ``content`` with a row for ``key`` inserted into the § 2 table."""
    lines = content.splitlines()
    for index, line in enumerate(lines):
        cells = _table_cells(line)
        if tuple(cells[: len(_ANCHOR_KEY_COLUMNS)]) == _ANCHOR_KEY_COLUMNS:
            row = f'| {key[0]} | {key[1]} | fallback | — | — | Section 1 ratios |'
            # +2 skips the header row and its alignment separator.
            lines.insert(index + 2, row)
            return '\n'.join(lines)
    raise AssertionError('Mutation helper found no anchors-table header row.')


# ---------------------------------------------------------------------------
# audit.py loading + metrics fixtures
# ---------------------------------------------------------------------------


#: sys.modules key the audit core is registered under while it executes.
_AUDIT_MODULE_NAME = 'audit_anchors_under_test'


def _load_audit() -> Any:
    """Load the audit computation core by file location (it has no notation).

    The module MUST be registered in ``sys.modules`` BEFORE ``exec_module``:
    ``audit.py`` defines ``@dataclass`` types at import time, and
    ``dataclasses._is_type`` resolves ``sys.modules.get(cls.__module__)`` while
    processing each class. Executing an unregistered module makes that lookup
    return ``None`` and the import dies with ``AttributeError: 'NoneType' object
    has no attribute '__dict__'`` — the same registration ``conftest``'s
    ``load_script_module`` performs for exactly this reason.
    """
    cached = sys.modules.get(_AUDIT_MODULE_NAME)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(_AUDIT_MODULE_NAME, _AUDIT_SCRIPT)
    assert spec is not None, f'Failed to load module spec for {_AUDIT_SCRIPT}'
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[_AUDIT_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(_AUDIT_MODULE_NAME, None)
        raise
    return module


def _write_metrics(plan_dir: Path, body: str) -> Path:
    """Write ``work/metrics.toon`` under ``plan_dir`` and return the plan dir."""
    work = plan_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    (work / 'metrics.toon').write_text(body, encoding='utf-8')
    return plan_dir


# ===========================================================================
# Cross-product guard
# ===========================================================================


def test_anchor_table_keys_are_exactly_the_live_cross_product() -> None:
    """The § 2 table carries EXACTLY the live ``(scope_estimate, change_type)`` pairs.

    Set equality, asserted in both directions separately so the failure message
    names the kind of rot. Superset would let a dead key survive forever; subset
    would let a live pair go silently unanchored.
    """
    parsed = _anchor_keys(_ANCHORS_DOC.read_text(encoding='utf-8'))
    expected = _expected_cross_product()
    extra, missing = _key_diff(parsed, expected)

    assert not extra, (
        f'{_ANCHORS_DOC} § 2 carries {len(extra)} key(s) that are NOT in the live '
        f'cross-product: {sorted(extra)}. A retired enum value leaves a dead row '
        f'that can never match a real plan — remove the row (remapping its '
        f'calibration data onto a live band if it carries any).'
    )
    assert not missing, (
        f'{_ANCHORS_DOC} § 2 is missing {len(missing)} live pair(s): '
        f'{sorted(missing)}. Every pair in the key space must be present as a row, '
        f'either `anchored` or explicitly `fallback`-graded — a silently-absent '
        f'pair is the defect this guard exists to catch.'
    )


def test_anchor_table_has_no_duplicate_keys() -> None:
    """No ``(scope_estimate, change_type)`` pair appears twice in the § 2 table.

    Set equality alone cannot see a duplicate: two rows for one key collapse into
    one set member and the equality still holds while the lookup is ambiguous.
    """
    parsed = _anchor_keys(_ANCHORS_DOC.read_text(encoding='utf-8'))
    duplicates = sorted({key for key in parsed if parsed.count(key) > 1})

    assert not duplicates, (
        f'{_ANCHORS_DOC} § 2 carries duplicate key row(s): {duplicates}. A lookup '
        f'on a duplicated key is ambiguous — keep exactly one row per pair.'
    )


def test_cross_product_guard_fails_when_a_pair_is_removed() -> None:
    """Deleting one row makes the guard's ``expected - parsed`` direction fire.

    This is the discrimination proof for the "unanchored pair" direction: an
    equality assertion that has never been observed failing has not been shown to
    be capable of failing.
    """
    content = _ANCHORS_DOC.read_text(encoding='utf-8')
    expected = _expected_cross_product()
    victim = sorted(set(_anchor_keys(content)))[0]

    extra, missing = _key_diff(_anchor_keys(_remove_anchor_row(content, victim)), expected)

    assert missing == {victim}, (
        f'Removing the {victim} row should leave exactly that pair unanchored; the '
        f'guard reported {sorted(missing)}.'
    )
    assert not extra, f'Removing a row must not introduce extra keys; got {sorted(extra)}.'


def test_cross_product_guard_fails_when_a_non_canonical_key_is_added() -> None:
    """Adding a retired-key row makes the guard's ``parsed - expected`` direction fire.

    The discrimination proof for the "dead key" direction — the failure mode the
    table actually had, where ``cross_cutting`` / ``refactor`` rows outlived the
    enums that once contained them.
    """
    content = _ANCHORS_DOC.read_text(encoding='utf-8')
    expected = _expected_cross_product()
    assert _RETIRED_PAIR not in expected, (
        f'{_RETIRED_PAIR} is now a live pair, so it can no longer serve as the '
        f'out-of-cross-product mutation; pick a genuinely retired pair.'
    )

    extra, missing = _key_diff(_anchor_keys(_insert_anchor_row(content, _RETIRED_PAIR)), expected)

    assert extra == {_RETIRED_PAIR}, (
        f'Adding the {_RETIRED_PAIR} row should be reported as exactly that dead '
        f'key; the guard reported {sorted(extra)}.'
    )
    assert not missing, f'Adding a row must not make a live pair go missing; got {sorted(missing)}.'


def test_change_type_axis_is_derived_from_both_owning_sources() -> None:
    """The change_type axis is the canonical vocabulary UNIONED with the router's.

    ``feature_breaking`` is scored as a live change_type by the planning-lane
    router but is absent from the canonical Change-Type Definitions table — the
    source discrepancy § 2 records explicitly. Pinning it here means that when the
    two sources are eventually reconciled, this test fails and forces the § 2 note
    to be updated instead of quietly going stale.
    """
    canonical = _canonical_change_types()
    router = _router_change_types()

    assert 'feature_breaking' in router, (
        'The planning-lane router no longer scores `feature_breaking`; the § 2 '
        'source-discrepancy note in plan-efficiency.md must be updated.'
    )
    assert 'feature_breaking' not in canonical, (
        '`feature_breaking` is now part of the canonical Change-Type Definitions '
        'table; the § 2 source-discrepancy note in plan-efficiency.md is stale and '
        'the UNION wording should collapse to the canonical vocabulary.'
    )
    assert _live_change_types() == canonical | router


# ===========================================================================
# Population guard for the audit-side checkpoint anchors
# ===========================================================================


def test_checkpoint_total_sums_total_tokens_and_only_total_tokens(tmp_path: Path) -> None:
    """``_plan_total_tokens`` sums ``total_tokens`` — and nothing else.

    ``billing_weighted_total`` is a DERIVED-COST measure (what the phase cost to
    buy) over a different population than the work total the checkpoint targets
    score. Folding it in would inflate every verdict, so the guard fixes a
    metrics.toon that carries both fields with deliberately far-apart magnitudes:
    the summed result can only equal the ``total_tokens`` sum.
    """
    audit = _load_audit()
    plan_dir = _write_metrics(
        tmp_path / 'plan-a',
        '[1-init]\n'
        '  total_tokens: 100000\n'
        '  billing_weighted_total: 5000000\n'
        '[5-execute]\n'
        '  total_tokens: 200000\n'
        '  billing_weighted_total: 5000000\n',
    )

    total = audit._plan_total_tokens(audit.PlanInputs(plan_id='plan-a', plan_dir=plan_dir))

    assert total == 300000, (
        f'Checkpoint total is {total}, expected 300000 (the summed `total_tokens`). '
        f'A larger value means a second field — most likely the derived-cost '
        f'`billing_weighted_total` — was folded into the work total.'
    )


def test_checkpoint_total_spans_populations_when_an_inline_row_is_present(
    tmp_path: Path,
) -> None:
    """An ``inline``-labelled phase row IS summed — the total is not dispatched-only.

    This pins the AS-BUILT population honestly. ``manage-metrics enrich`` folds a
    zero-dispatch phase's main-context figure into ``total_tokens`` and marks the
    row ``inline``; that fold was deliberately RETAINED, so the checkpoint sum
    spans populations. Asserting a dispatched-only population here would pin a
    claim the code does not implement.
    """
    audit = _load_audit()
    plan_dir = _write_metrics(
        tmp_path / 'plan-b',
        '[1-init]\n'
        '  total_tokens: 40000\n'
        '  total_tokens_population: inline\n'
        '  inline_main_context_tokens: 40000\n'
        '[5-execute]\n'
        '  total_tokens: 60000\n'
        '  total_tokens_population: dispatched\n',
    )

    total = audit._plan_total_tokens(audit.PlanInputs(plan_id='plan-b', plan_dir=plan_dir))

    assert total == 100000, (
        f'Checkpoint total is {total}, expected 100000. The `inline`-labelled row '
        f'must still be summed — the checkpoint verdict is computed over a '
        f'default-plus-exception population that SPANS populations, not over the '
        f'dispatched population alone.'
    )


def test_lane_lever_verdict_is_unaffected_by_billing_weighted_total(tmp_path: Path) -> None:
    """The checkpoint verdict is identical with and without a billing column.

    The magnitudes are chosen so the two answers are distinguishable: the work
    total (300K) is inside the ``surgical`` target, while a total that folded the
    billing figures in (10.3M) would blow past it and flip the verdict to ``over``.
    A green here therefore means the verdict really is computed over the
    ``total_tokens`` sum alone.
    """
    audit = _load_audit()
    targets = audit.THRESHOLDS['checkpoint_token_targets']
    work_only = (
        '[1-init]\n  total_tokens: 100000\n[5-execute]\n  total_tokens: 200000\n'
    )
    with_billing = (
        '[1-init]\n'
        '  total_tokens: 100000\n'
        '  billing_weighted_total: 5000000\n'
        '[5-execute]\n'
        '  total_tokens: 200000\n'
        '  billing_weighted_total: 5000000\n'
    )

    def _row(name: str, body: str) -> dict[str, Any]:
        inputs = audit.PlanInputs(
            plan_id=name,
            plan_dir=_write_metrics(tmp_path / name, body),
            scope_estimate='surgical',
        )
        row = audit._lane_lever_row(inputs, targets)
        row.pop('plan_id')
        return dict(row)

    baseline = _row('plan-work-only', work_only)
    billed = _row('plan-with-billing', with_billing)

    assert baseline == billed, (
        'Adding a `billing_weighted_total` column to metrics.toon changed the '
        'lane-lever checkpoint row; the derived-cost figure must never reach the '
        'work total the verdict scores.'
    )
    assert baseline['verdict'] == 'within', (
        f"Expected a `within` verdict for a 300K surgical plan against target "
        f"{targets['surgical']}; got {baseline['verdict']}. If this flipped to "
        f'`over`, a second token field is being summed into the work total.'
    )


def test_checkpoint_targets_are_read_from_the_single_thresholds_constant() -> None:
    """The armed targets live in ``THRESHOLDS`` and cover the classed scope bands.

    The checkpoint classes are a deliberate SUBSET of the live ``scope_estimate``
    enum — an unlisted band scores ``unclassed`` rather than being silently
    graded against a borrowed target — so this asserts subset membership, not
    equality, and would catch a target keyed on a value the enum never had.
    """
    audit = _load_audit()
    targets = audit.THRESHOLDS['checkpoint_token_targets']
    live_scopes = _live_scope_estimates()

    assert targets, 'THRESHOLDS["checkpoint_token_targets"] is empty.'
    unknown = set(targets) - live_scopes
    assert not unknown, (
        f'THRESHOLDS["checkpoint_token_targets"] is keyed on {sorted(unknown)}, '
        f'which are not members of the live scope_estimate enum {sorted(live_scopes)} '
        f'— those targets can never be selected and the class reads `unclassed`.'
    )
    assert all(isinstance(value, int) and value > 0 for value in targets.values()), (
        f'Every checkpoint target must be a positive integer token budget; got {targets}.'
    )
