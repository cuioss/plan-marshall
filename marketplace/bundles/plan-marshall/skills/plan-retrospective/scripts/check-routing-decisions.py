#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Routing-decision verification aspect — deterministic predicate re-evaluation.

Grades the routing decisions a run actually made (recipe-match, aspect
classification, and the execution-profile posture) against the realized
footprint, so the lane mechanism self-corrects. This is the per-plan analog of
the corpus-level recipe-match / track-selection-accuracy / token-economics audit
checks.

The script is DETERMINISTIC by design — it re-evaluates the named prune
predicates (owned by ``plan-marshall:extension-api/standards/ext-point-lane-element.md``)
against the realized footprint and emits TOON fact fragments. It reserves NO
cognition for itself: the OVER-PROVISIONED / UNDER-PROVISIONED / correct posture
counterfactual is an LLM judgment synthesized from these facts by the aspect's
reference contract (``references/routing-decision-verification.md``). The script
sets ``llm_judgement_required: true`` to mark that boundary.

Facts emitted:
  * ``posture`` / ``planning_lane`` — the recorded routing decisions.
  * ``mis_prune`` checks — for each prunable step ABSENT from the final
    ``phase_6.steps``, first resolve WHY it was removed from the recorded
    decision log, and only then re-evaluate its predicate. A step named by any
    recorded non-predicate removal mechanism is SKIPPED — its predicate never
    fired, so its absence proves nothing about the footprint. Those mechanisms
    are every gate reporting through the composer's shared subtraction-record
    line (recognised gate-agnostically, so the set follows the composer), plus the
    individually-shaped ones: ``unresolved_ask_provider_drop``,
    ``simplify_inactive``, a ``ceremony_finalize_selection`` resolving ``never``,
    and — for archived logs alone — ``posture_cutoff_legacy_aggregate`` and
    ``frozen_manifest_stale_legacy_backticked``.
    Only a step whose removal no recorded mechanism explains, in a decision log
    that was actually readable, has its predicate re-evaluated: a predicate that
    is now FALSE (e.g. ``sonar-roundtrip`` skipped as "no code delta" but the
    merged diff touched production code) is a mis-prune — the highest-value
    output. An absent or unreadable decision log substantiates no cause at all,
    so the verdict is ``inconclusive`` rather than a fabricated ``fail``.
  * ``cost_preview`` — the ``execution_log`` token sum beside the init preview,
    each naming the POPULATION it measures and the per-state row counts saying how
    much of that population the sum could READ, and a ``comparison`` verdict that
    feeds the ``cost_size_token_table`` recalibration loop only when the two
    populations match AND every in-population row carried a readable token column.
  * ``kept_step_yield`` — finding count as the adversarial-step yield proxy.
  * ``recompose_divergence`` — the lane_resolution decision-log LINE count. Not a
    recompose count despite the name; see :func:`lane_resolution_view`.

Inputs (all present at retrospective time): ``execution.toon`` (manifest +
``execution_log``), ``status.json`` (posture, ``planning_lane``), the
decision-log, and the findings JSONL.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from _decision_line_shapes import dropped_record_pattern
from _footprint_classification import (
    CATEGORY_PRODUCTION,
    CATEGORY_UNCLASSIFIED,
    classify_path,
    load_oracle_routes,
)
from _footprint_resolver import footprint_resolved, resolve_diff_file_path, resolve_footprint
from file_ops import base_path, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
)
from toon_parser import parse_toon

MANIFEST_FILENAME = 'execution.toon'
STATUS_FILENAME = 'status.json'
DECISION_LOG_RELPATH = ('logs', 'decision.log')

# The categories that make a realized footprint count as having touched
# production code. The classification itself is the ORACLE'S (``build.map`` in
# marshal.json), routed through the ``_footprint_classification`` module this
# check now SHARES with ``check-manifest-consistency`` — the two used to carry
# byte-identical private prefix tuples declaring a project-local dotfile tree to be
# bookkeeping, which a build extension may route as ``production`` — a project-local
# skill root is routed exactly that way on some targets.
#
# ``unclassified`` counts as production, and that is fail-closed rather than
# sloppy: an unclassified path might be production, and the verdict this feeds is a
# mis-prune FAIL — a step pruned as ``no_code_delta`` when code did change.
# Answering "not production" for a path nobody could classify would turn an unknown
# into an exoneration.
#
# ``unclassified`` is NARROWER than "no declared route covers it": the shared
# classifier recognises documentation and test files by convention where the oracle
# is silent, so an unrouted ``README.md`` or ``test_foo.py`` is ``documentation`` /
# ``test`` and does NOT reach this set. That is what keeps a docs-only or tests-only
# footprint from being read as production in a project whose ``build.map`` carries
# no route for them — the exact false-positive the convention rungs exist to
# prevent.
_PRODUCTION_CATEGORIES = frozenset({CATEGORY_PRODUCTION, CATEGORY_UNCLASSIFIED})

# Prunable steps whose absence from the final phase_6.steps is re-checked against
# the realized footprint. Each maps to its ``prunable_when`` predicate id — the
# vocabulary is owned by ext-point-lane-element.md; this map records only which
# step carries which predicate for the deterministic re-evaluation.
#
# RE-DERIVATION OBLIGATION: the removal-cause readers below must between them
# recognise every recorded mechanism that can remove one of THESE members from
# ``phase_6.steps`` without its predicate firing. An unrecognised removal
# mechanism reintroduces the false ``mis_prune`` verdict by that route.
#
# Most of that obligation is now discharged structurally rather than by
# enumeration: every gate reporting through the composer's shared
# subtraction-record line is recognised gate-agnostically, so a new gate in that
# family needs no edit here. The obligation still binds for a mechanism that
# renders its OWN line shape — adding a step to this map, or adding a
# differently-shaped emission to the composer, obliges a re-derivation against the
# composer's EMITTERS — the ``_emit_decision_log`` call sites in
# ``manage-execution-manifest.py``. Re-derive against the CODE, not against
# ``standards/decision-rules.md``: that document's renderings are current and
# correct for the shapes it covers, but it does not enumerate every gate (its
# pre-filter list omits ``terminal_emission_orchestration_gate``), so a doc-only
# re-derivation can miss a live mechanism.
_PRUNABLE_PREDICATES = {
    'sonar-roundtrip': 'no_code_delta',
    'finalize-step-simplify': 'no_code_delta',
}

# The lane_resolution decision-log caller tag.
_LANE_DECISION_RE = re.compile(r'lane_resolution\b')

# Recorded non-predicate removal mechanisms. A step named by any of these left
# ``phase_6.steps`` for a reason orthogonal to its prune predicate, so its absence
# is NOT evidence the predicate fired.
#
# The composer's subtraction-record family — every gate that reports a drop
# through ``_log_dropped_records`` — is recognised by the SHARED shape imported
# from ``_decision_line_shapes``, the same definition the writer renders with.
# That family is matched gate-AGNOSTICALLY and the gate name becomes the recorded
# cause, so a gate added to the composer later is recognised without an edit here.
#
# This replaces a hand-written per-gate enumeration that had drifted in two
# separate ways, both of which manufactured false ``mis_prune`` verdicts:
#
#   * its ``posture_cutoff`` pattern still matched the RETIRED aggregate line
#     shape (``execution_profile=…`` before the verb, a
#     ``(tier above posture cutoff)`` trailing clause). The composer had since
#     moved to one line per dropped step with the posture in a trailing
#     parenthetical and the gate's own reason after the colon, so the pattern
#     could not match any line the emitter produced — every posture-cutoff drop
#     fell through to predicate re-evaluation. The comment this replaces asserted
#     each shape was "copied verbatim from the emitter contract"; the contract
#     document was correct and current, and the pattern was not.
#   * ``decision_matrix`` was absent from the enumeration entirely, so the
#     ``early_terminate_analysis`` and ``verification_no_files`` rows — which
#     narrow ``phase_6`` to the analysis minimum and thereby drop BOTH prunable
#     steps — recorded a cause no pattern read.
#
# The patterns below do NOT report through the shared shape (each renders its own
# line), so each keeps a pattern of its own, re-derived against its emitter. They
# are named rather than counted, because a count here goes stale the moment one is
# added — which has already happened to this file twice.
#
# ``ceremony_finalize_selection`` shares one line shape across both
# directions — ``added {step} to`` and ``dropped {step} from``. Only the
# ``dropped ... from`` direction is a removal; the ``added`` direction is a
# force-include and MUST NOT be read as a cause.
_DROPPED_RECORD_RE = dropped_record_pattern()

_REMOVAL_CAUSE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        # Retained because this script reads archived plans
        # (`resolve_plan_dir(mode='archived', ...)`) and an archived log is
        # immutable history: dropping the pattern would leave every pre-change
        # archive resolving NO cause for its posture-cutoff drops, falling through
        # to predicate re-evaluation and producing exactly the false `mis_prune`
        # this mechanism exists to end — a regression introduced by the fix, on the
        # corpus the fix was meant to make readable. It is also the only pattern
        # that renders a Python list repr, so it is what keeps
        # `_parse_step_tokens`'s list branch reachable.
        #
        # SHIM(B): the RETIRED aggregate `lane_resolution` decision-log line —
        # `execution_profile=…` BEFORE the verb, the dropped steps rendered as a
        # Python list repr, and a trailing `(tier above posture cutoff)` clause.
        # The live emitter writes one line per dropped step with the posture in a
        # trailing parenthetical and the gate's reason after the colon, so no
        # current run can produce this shape; only archived logs still carry it.
        # shim-owner: plan-retrospective
        # shim-floor: the `manage-execution-manifest` composer change that replaced
        #   the single aggregate `lane_resolution` line with one
        #   `_log_dropped_records` line per dropped step, moving `execution_profile`
        #   into a trailing parenthetical and the gate's own reason after the colon.
        # shim-remove-when: no archived plan this reader can open still retains a
        #   decision.log carrying a line this pattern matches. Establish that by
        #   scanning the retained archive corpus for lines the EMITTER actually
        #   produced — never by reading
        #   `manage-execution-manifest/standards/decision-rules.md`. Substituting
        #   that document for the emitter is precisely what left this pattern's
        #   predecessor dead in production while its test stayed green, because doc
        #   → regex and doc → test-literal is a closed loop the emitter never enters
        #   (lesson 2026-08-08-20-001, Instance 1). The honest expectation is that
        #   this trigger does not fire while pre-change archives are retained.
        'posture_cutoff_legacy_aggregate',
        re.compile(
            r'lane_resolution\s+—\s+execution_profile=[^,]+,\s+dropped\s+(?P<steps>.+?)'
            r'\s+from\s+phase_6\.steps\s+\(tier above posture cutoff\)'
        ),
    ),
    (
        # Retained for the same reason as the aggregate pattern above: an archived
        # decision.log is immutable history, and this reader is the only thing that
        # can still read it. Without this pattern every pre-change archive resolves
        # NO cause for its reconcile-dropped steps and falls through to predicate
        # re-evaluation — the false `mis_prune` the fix was meant to end, reappearing
        # on the corpus the fix was meant to make readable.
        #
        # The backticks are REQUIRED by this pattern, which is what keeps it
        # disjoint from the live shape: the current emitter renders the step bare
        # and through the shared `[STATUS]` subtraction-record formatter, so a live
        # line is matched by `_DROPPED_RECORD_RE` and can never also match here.
        #
        # SHIM(B): the RETIRED `reconcile` dropped-step decision-log line — no
        # `[STATUS]` tag, and the step id wrapped in backticks.
        # shim-owner: plan-retrospective
        # shim-floor: the `manage-execution-manifest` reconcile change that routed
        #   the `frozen_manifest_stale` emission through
        #   `_decision_line_shapes.format_dropped_record`, adding the `[STATUS]` tag
        #   and dropping the backticks around the step id.
        # shim-remove-when: no archived plan this reader can open still retains a
        #   decision.log carrying a line this pattern matches. Establish that by
        #   scanning the retained archive corpus for lines the EMITTER actually
        #   produced — never by reading
        #   `manage-execution-manifest/standards/decision-rules.md`; doc → regex and
        #   doc → test-literal is a closed loop the emitter never enters. The honest
        #   expectation is that this trigger does not fire while pre-change archives
        #   are retained.
        'frozen_manifest_stale_legacy_backticked',
        re.compile(
            r'frozen_manifest_stale\s+—\s+dropped\s+`(?P<steps>[^`]+)`'
            r'\s+from\s+phase_6\.steps'
        ),
    ),
    (
        'unresolved_ask_provider_drop',
        re.compile(
            r'unresolved_ask_provider_drop\s+—\s+dropped\s+(?P<steps>.+?)'
            r'\s+from\s+phase_6\.steps\s+\(unresolved lane:ask, provider absent\)'
        ),
    ),
    (
        'simplify_inactive',
        re.compile(r'(?P<steps>finalize-step-simplify)\s+omitted\s+—\s+change_type='),
    ),
    (
        'ceremony_finalize_never',
        re.compile(
            r'ceremony_finalize selection\s+—\s+finalize\.\w+=[^,]+,\s+dropped\s+(?P<steps>.+?)'
            r'\s+from\s+phase_6\.steps'
        ),
    ),
)

# Removal-cause tokens for rows where no recorded mechanism applies.
_CAUSE_NOT_REMOVED = 'not_removed'
_CAUSE_NOT_EVALUATED = 'not_evaluated'
_CAUSE_PREDICATE_EVALUATED = 'predicate_evaluated'
_CAUSE_UNESTABLISHABLE = 'unestablishable'


def _bare_step(name: str) -> str:
    """Normalize a step key to its bare form.

    Recorded decision-log lines may name a step with a ``default:`` /
    ``project:`` prefix while ``_PRUNABLE_PREDICATES`` keys are bare. Both sides
    are normalized with the same ``rsplit(':', 1)`` rule ``_phase_6_steps``
    applies, so a prefixed recorded drop matches the bare predicate key.
    """
    return name.rsplit(':', 1)[-1] if ':' in name else name


def _parse_step_tokens(raw: str) -> list[str]:
    """Split a decision-log ``{steps}`` capture into bare step names.

    Every CURRENT emitter names one step per line, so the live path is a single
    bare (or ``default:``/``project:``-prefixed) step reference.

    The Python-list-repr form (``['a', 'b']``) is retired on the WRITING side:
    ``lane_resolution`` rendered it while it emitted one aggregate line per
    compose, and it now reports one line per dropped step through the shared
    subtraction-record shape, whose ``\\S+`` capture could not match a list repr in
    any case.

    The branch is still reachable, and by exactly one route: the
    ``posture_cutoff_legacy_aggregate`` pattern in ``_REMOVAL_CAUSE_PATTERNS``,
    which matches that retired line in ARCHIVED decision logs. Archived logs are
    immutable history and this reader is the only thing that can still read them,
    so removing either the pattern or this branch would make every pre-change
    archive resolve no cause for its posture-cutoff drops.
    """
    text = raw.strip()
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1]
    tokens = []
    for part in text.split(','):
        token = part.strip().strip('\'"').strip()
        if token:
            tokens.append(_bare_step(token))
    return tokens


def resolve_removal_causes(decision_lines: list[str]) -> dict[str, str]:
    """Return ``{bare_step_name: removal_cause}`` from the recorded decision log.

    Pure over its input — no filesystem access. The first mechanism that names a
    step wins, so a step removed once and later re-added-then-dropped keeps its
    earliest recorded cause.

    Two families are read. The shared subtraction-record shape
    (``_DROPPED_RECORD_RE``, rendered by the composer's ``_log_dropped_records``)
    is matched first and contributes the emitting gate's own name as the cause:
    EVERY gate that reports through that helper, whatever it is called and
    whenever it was added. The family is deliberately not enumerated here —
    enumerating it is what left ``decision_matrix`` unrecognised, and any list
    written now would be one composer change away from being wrong again. Read the
    live membership off ``_log_dropped_records``'s call sites when you need it.

    The mechanisms in ``_REMOVAL_CAUSE_PATTERNS`` render their own line shapes and
    are matched individually.
    """
    causes: dict[str, str] = {}
    for line in decision_lines:
        shared = _DROPPED_RECORD_RE.search(line)
        if shared is not None:
            for step in _parse_step_tokens(shared.group('steps')):
                causes.setdefault(step, shared.group('gate'))
        for cause, pattern in _REMOVAL_CAUSE_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            for step in _parse_step_tokens(match.group('steps')):
                causes.setdefault(step, cause)
    return causes


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f'Unknown mode: {mode!r}')


def load_manifest(plan_dir: Path) -> dict[str, Any] | None:
    """Return the parsed manifest dict, or ``None`` when ``execution.toon`` is absent."""
    manifest_path = plan_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        raw = manifest_path.read_text(encoding='utf-8')
    except OSError:
        return None
    parsed = parse_toon(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f'{MANIFEST_FILENAME} must parse to a top-level dict')
    return parsed


def load_status_metadata(plan_dir: Path) -> dict[str, Any]:
    """Return ``status.metadata`` (empty dict when status.json is absent/malformed)."""
    status_path = plan_dir / STATUS_FILENAME
    if not status_path.exists():
        return {}
    try:
        status = json.loads(status_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    metadata = status.get('metadata') if isinstance(status, dict) else None
    return metadata if isinstance(metadata, dict) else {}


def load_decision_log_lines(plan_dir: Path) -> tuple[list[str], bool]:
    """Return ``(lines, log_readable)`` for the plan's decision log.

    ``log_readable`` is ``True`` only when the file existed AND was read
    successfully. A missing or unreadable log yields ``([], False)`` — the
    explicit discriminator that separates "the log records no removal cause for
    this step" (positive evidence) from "no log was available to record one"
    (no evidence at all). Collapsing both to ``[]``, as the previous loader did,
    is exactly the ambiguity that let an unestablishable cause be reported as a
    substantiated mis-prune.
    """
    log_path = plan_dir.joinpath(*DECISION_LOG_RELPATH)
    if not log_path.exists():
        return [], False
    try:
        return log_path.read_text(encoding='utf-8').splitlines(), True
    except OSError:
        return [], False


def lane_resolution_view(decision_lines: list[str]) -> list[str]:
    """Return the ``lane_resolution`` subset of ``decision_lines``.

    The thin view feeding the report-facing ``recompose_divergence`` /
    ``recorded_lane_decisions`` fields. Widening the underlying loader must not
    change what those two fields count, so the filter lives here rather than in
    the loader.

    ⚠ **This is a count of LINES, not of composes.** Under the retired aggregate
    emission the composer wrote one ``lane_resolution`` line per compose, so the
    line count WAS the recompose count and the field name was accurate. The
    composer now emits one line per dropped step plus one per lane warning
    (``manage-execution-manifest.py``, ``_log_dropped_records`` /
    ``lane_resolution warning``), so this count is drops-plus-warnings and rises
    with the SIZE of a single compose's subtraction rather than with the number of
    composes. It is the same emitter change that broke the ``posture_cutoff``
    removal-cause pattern, reaching a second consumer in this file.

    The count is left as-is rather than re-derived: reconstructing a compose count
    from the current lines needs a per-compose delimiter the emitter does not
    provide. What is fixed here is the CLAIM — the reader is told what the number
    counts, so it is not read as a recompose count. Deriving a real recompose
    signal needs an emitter change and belongs with the composer.
    """
    return [line for line in decision_lines if _LANE_DECISION_RE.search(line)]


def load_diff_files(diff_file: str | None, plan_dir: Path) -> list[str] | None:
    """Return the realized footprint from a pre-saved diff file, or ``None`` if omitted.

    ``--diff-file`` carries one path per line (the end-of-execute diff). OMITTED →
    ``None``, the omitted-input sentinel; the caller (``cmd_run``) then recovers the
    footprint through the shared whole-chain resolver, and only a still-unresolvable
    footprint degrades the predicate re-evaluation to a skip (never a false positive).

    ⛔ **Omission is tested as ``diff_file is None``, and the return distinguishes an
    omitted argument from a supplied-and-empty one.** A truthiness test conflates
    three states this function must keep apart: omitted, supplied-and-empty
    (``--diff-file ""``), and supplied-naming-an-empty-file. The last is a RESOLVED,
    genuinely-empty footprint — the run really did change nothing — and returning
    ``[]`` for it lets the caller distinguish that from ``None``. Collapsing them
    sends a supplied input down the omitted path, which is the same
    could-not-look-versus-nothing-to-look-at conflation the raising behaviour below
    exists to prevent, arriving by a different door.

    A SUPPLIED path is a different case and is treated as one. It is resolved
    plan-relative first and cwd-relative second (:func:`resolve_diff_file_path`),
    matching both the documented capture pattern (``--diff-file
    work/footprint.txt``) and the sibling ``collect-fragments add --fragment-file``
    flag in the same workflow — and if no candidate exists it RAISES. Returning an
    empty list there would report a could-not-look with the same token as a
    nothing-to-look-at, and that token reads benign in every downstream summary:
    the documented invocation silently degraded to a skip while the identical file
    passed as an absolute path found a real violation.
    """
    if diff_file is None:
        return None
    path = resolve_diff_file_path(diff_file, plan_dir)
    try:
        return [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    except OSError as e:
        raise ValueError(f'Diff file could not be read: {diff_file}: {e}') from e


def footprint_has_production(files: list[str]) -> bool:
    """Return True when the realized footprint touched production code.

    The per-path verdict comes from the declared ``build.map`` oracle via
    :func:`classify_path`; a path falls in :data:`_PRODUCTION_CATEGORIES` when the
    oracle routes it ``production``, or when it resolves to ``unclassified`` — which
    is narrower than "unrouted", since documentation and test files are recognised
    by convention where the oracle is silent. See that constant for why an
    unclassifiable path counts.
    """
    routes = load_oracle_routes()
    return any(classify_path(path, routes) in _PRODUCTION_CATEGORIES for path in files)


# ---------------------------------------------------------------------------
# The execution_log's population, and the population-match gate
# ---------------------------------------------------------------------------
#
# ``execution_log[]`` is NOT a whole-plan ledger and cannot become one: its
# writer refuses any row whose phase is outside ``VALID_RECORD_PHASES``
# (``manage-execution-manifest/scripts/_manifest_core.py``), so a sum over it
# measures phases 5 and 6 and NOTHING else. Naming that sum ``actual_tokens``
# asserted a whole-plan actual it never held.
#
# This tuple is a hand-mirror of that writer-side constant, held in the same
# cross-skill shape ``manage-metrics``'s ``_EXPLORATION_BUCKETS`` uses: the two
# skills run in different processes and this script cannot import the manifest
# skill's private module. The mirror is held honest by the contract-drift test
# ``test_execution_log_population_matches_writer`` in
# ``test/plan-marshall/plan-retrospective/test_check_routing_decisions.py``,
# which imports ``VALID_RECORD_PHASES`` from the writer and fails loudly when a
# phase is added or removed on either side.
EXECUTION_LOG_PHASES = ('5-execute', '6-finalize')

#: The literal an OMITTED ``execution_log[]`` token column carries. A hand-mirror
#: of ``UNMEASURED_COLUMN_TOKEN`` in
#: ``manage-execution-manifest/scripts/_manifest_core.py``, held in the same
#: cross-skill shape :data:`EXECUTION_LOG_PHASES` already uses above — this script
#: runs in a different process from the writer and cannot import its private
#: module. Held honest by the contract-drift test
#: ``test_unmeasured_token_matches_writer``.
UNMEASURED_COLUMN_TOKEN = 'unmeasured'

#: The population label the ``execution_log`` sum carries. A comma-joined phase
#: list rather than a coined vocabulary word: this script is a CONSUMER of the
#: population vocabulary, never its author, and the phase set is the exact,
#: checkable statement of what the sum covers.
EXECUTION_LOG_POPULATION = ','.join(EXECUTION_LOG_PHASES)

#: The metadata key naming the population the persisted cost preview measures.
#: No producer writes the preview itself today, so no producer writes this
#: either — which is precisely why an absent value must NOT read as "matches".
PREDICTED_POPULATION_KEY = 'execution_profile_cost_preview_population'

#: The population value used when the record states none. It never equals
#: ``EXECUTION_LOG_POPULATION``, so an unstated population always refuses.
POPULATION_UNSTATED = 'unstated'

#: ``cost_preview.comparison`` verdicts. ``not_attempted`` — no prediction was
#: recorded, so there is nothing to compare. ``refused`` — a prediction exists
#: but measures a different population than the sum, so no delta is emitted.
#: ``computed`` — the two populations match and the delta is trustworthy.
COMPARISON_NOT_ATTEMPTED = 'not_attempted'
COMPARISON_REFUSED = 'refused'
COMPARISON_COMPUTED = 'computed'


def summarize_execution_log_tokens(manifest: dict[str, Any]) -> dict[str, int]:
    """Sum ``total_tokens`` over the in-population rows AND state the sum's coverage.

    Filtered to :data:`EXECUTION_LOG_PHASES`, which is the population
    :data:`EXECUTION_LOG_POPULATION` publishes beside the figure. Summing every
    row regardless of phase and then labelling the result with a phase list makes
    the label a promise about the writer rather than a property of the sum — and
    a manifest carrying an out-of-population row (hand-edited, or archived from
    before the writer's phase gate existed) would then be summed under a label
    naming phases it did not measure. That is this plan's own keeper rule applied
    to its own deliverable: the figure carries its population, or it is not named
    for one.

    ⛔ **A phase filter is not the only way a sum can be partial.** The writer's
    token columns are three-state: a measured value, :data:`UNMEASURED_COLUMN_TOKEN`
    for a column whose flag the caller OMITTED, or an unrecognised cell. Both
    non-measured states contribute nothing, so a sum taken over them is a FLOOR —
    and a sum published without saying how many rows it could not read is exactly
    the fabricated total the token exists to prevent, reconstructed one level up.
    The int-parsing branch is kept unchanged, so every historical all-numeric row
    still parses and still sums as before.

    Returns:
        ``{'total_tokens', 'rows_in_population', 'rows_measured',
        'rows_unmeasured', 'rows_unrecognised'}`` — the sum plus the per-state row
        counts it was taken over. ``rows_measured + rows_unmeasured +
        rows_unrecognised == rows_in_population`` holds unconditionally.
    """
    coverage = {
        'total_tokens': 0,
        'rows_in_population': 0,
        'rows_measured': 0,
        'rows_unmeasured': 0,
        'rows_unrecognised': 0,
    }
    rows = manifest.get('execution_log')
    if not isinstance(rows, list):
        return coverage
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get('phase')) not in EXECUTION_LOG_PHASES:
            continue
        coverage['rows_in_population'] += 1
        value = row.get('total_tokens')
        if isinstance(value, bool):
            # A bool is not a token count; it is an unreadable cell.
            coverage['rows_unrecognised'] += 1
        elif isinstance(value, int):
            coverage['total_tokens'] += value
            coverage['rows_measured'] += 1
        elif isinstance(value, str):
            # Strip ONCE and branch on the stripped value. Stripping for the
            # unmeasured comparison but not for the digit test made a padded
            # numeric token (`' 12000'`) match neither arm: it fell to
            # unrecognised and its count was silently dropped from the sum —
            # an under-count wearing the shape of an unreadable cell, which is
            # the measured-vs-unmeasured conflation this module exists to
            # report rather than commit.
            stripped = value.strip()
            if stripped == UNMEASURED_COLUMN_TOKEN:
                coverage['rows_unmeasured'] += 1
            elif stripped.isdigit():
                coverage['total_tokens'] += int(stripped)
                coverage['rows_measured'] += 1
            else:
                coverage['rows_unrecognised'] += 1
        else:
            coverage['rows_unrecognised'] += 1
    return coverage


def sum_execution_log_tokens(manifest: dict[str, Any]) -> int:
    """Return only the token sum from :func:`summarize_execution_log_tokens`.

    The thin accessor kept for callers that need the figure alone. Anything that
    PRESENTS the figure must take the full coverage dict instead — a sum quoted
    without its per-state row counts cannot state how much of its population it
    actually read.
    """
    return summarize_execution_log_tokens(manifest)['total_tokens']


def _phase_6_steps(manifest: dict[str, Any]) -> list[str]:
    phase_6 = manifest.get('phase_6')
    if isinstance(phase_6, dict):
        steps = phase_6.get('steps')
        if isinstance(steps, list):
            return [str(s) for s in steps]
    return []


def evaluate_mis_prunes(
    manifest: dict[str, Any],
    footprint: list[str],
    have_footprint: bool,
    decision_lines: list[str],
    log_readable: bool,
) -> list[dict[str, Any]]:
    """Resolve each absent prunable step's REMOVAL CAUSE, then re-evaluate its predicate.

    The removal *fact* never implies the removal *cause*: a prunable step can
    leave ``phase_6.steps`` through recorded mechanisms that are all orthogonal to
    the footprint (the composer's shared subtraction-record family plus the
    individually-shaped mechanisms in ``_REMOVAL_CAUSE_PATTERNS``). The recorded
    decision log is consulted FIRST, and the predicate is re-evaluated only for a
    step whose removal no recorded mechanism explains.

    The verdict rules are mutually exclusive and jointly exhaustive over an
    absent step:

    ===================================================  ==============
    Absent step's state                                  Verdict
    ===================================================  ==============
    Footprint unresolvable                               ``skip``
    Named by a recorded non-predicate cause              ``skip``
    Log unreadable / absent (``log_readable == False``)  ``inconclusive``
    Readable log names no cause, predicate now false     ``fail``
    Readable log names no cause, predicate still holds   ``pass``
    ===================================================  ==============

    ``log_readable`` is the SOLE discriminator between ``fail`` and
    ``inconclusive``. The composer emits a decision-log line for every recorded
    removal mechanism, so a *readable* log naming no cause for this step is
    positive evidence the predicate is the remover — a substantiated ``fail``.
    An *unreadable or absent* log substantiates nothing, so the honest verdict is
    ``inconclusive``.

    That inference is only as sound as the reader's coverage of the emitted
    shapes: a mechanism the reader cannot parse is indistinguishable from one the
    composer never recorded, and turns this branch into a false ``fail``. Reading
    the composer's subtraction-record family through the writer's own shared shape
    is what keeps coverage from depending on a hand-maintained list.

    Every returned row carries ``removal_cause``: the mechanism token for a
    recorded removal, ``predicate_evaluated`` where the predicate actually ran,
    and a descriptive token otherwise.
    """
    final_steps = {s.rsplit(':', 1)[-1] if ':' in s else s for s in _phase_6_steps(manifest)}
    bare_final = set(_phase_6_steps(manifest)) | final_steps
    has_production = footprint_has_production(footprint)
    removal_causes = resolve_removal_causes(decision_lines)
    checks: list[dict[str, Any]] = []
    for step, predicate in _PRUNABLE_PREDICATES.items():
        absent = step not in bare_final
        if not absent:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'pass',
                'predicate': predicate,
                'removal_cause': _CAUSE_NOT_REMOVED,
                'detail': 'step ran',
            })
            continue
        if not have_footprint:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'skip',
                'predicate': predicate,
                'removal_cause': _CAUSE_NOT_EVALUATED,
                'detail': 'footprint unresolvable',
            })
            continue
        recorded_cause = removal_causes.get(step)
        if recorded_cause is not None:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'skip',
                'predicate': predicate,
                'removal_cause': recorded_cause,
                'detail': f'dropped by {recorded_cause}, prune predicate not evaluated',
            })
            continue
        if not log_readable:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'inconclusive',
                'predicate': predicate,
                'removal_cause': _CAUSE_UNESTABLISHABLE,
                'detail': 'removal cause unestablishable — decision log absent or unreadable',
            })
            continue
        # no_code_delta predicate is now FALSE when the diff touched production.
        if predicate == 'no_code_delta' and has_production:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'fail',
                'predicate': predicate,
                'removal_cause': _CAUSE_PREDICATE_EVALUATED,
                'detail': f'{step} skipped as no_code_delta but the realized footprint touched production code',
            })
        else:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'pass',
                'predicate': predicate,
                'removal_cause': _CAUSE_PREDICATE_EVALUATED,
                'detail': 'predicate still holds',
            })
    return checks


#: Emitted check status → its ``summary`` bucket name. The map is total over the
#: set :func:`evaluate_mis_prunes` emits — ``pass`` / ``fail`` / ``skip`` /
#: ``inconclusive`` — rather than a table of exceptions, which is what lets
#: :func:`summarize_checks` report an explicit zero for each so an absent key is
#: never mistaken for a measured zero. ``inconclusive``'s bucket name is the
#: status itself. A status with no row here is still counted, under its own name.
_STATUS_BUCKETS: dict[str, str] = {
    'pass': 'passed',
    'fail': 'failed',
    'skip': 'skipped',
    'inconclusive': 'inconclusive',
}


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    """Return the per-status counts for ``checks``, total over what was emitted.

    Every known status gets an explicit zero, and an UNKNOWN status is counted
    under its own name rather than dropped, so ``sum(result.values()) ==
    len(checks)`` holds unconditionally.

    That second half is the point, and it is the sibling
    ``check-manifest-consistency.summarize_checks``'s rule rather than a variation
    on it. The three hard-coded ``pass``/``fail``/``skip`` comprehensions this
    replaces counted only the statuses the literal happened to name, so every
    ``inconclusive`` verdict — a status this very module emits, and the honest one
    for an unreadable decision log — landed in no bucket at all and read to a
    summary consumer as a check that does not exist. Silently dropping an
    unrecognised verdict is the absent-reads-as-nothing defect this aspect exists
    to surface, so it must not be reproduced in the aspect's own summary.
    """
    summary = dict.fromkeys(_STATUS_BUCKETS.values(), 0)
    for check in checks:
        bucket = _STATUS_BUCKETS.get(check['status'], check['status'])
        summary[bucket] = summary.get(bucket, 0) + 1
    return summary


def evaluate_cost_preview(manifest: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Place the init cost preview beside the ``execution_log`` sum, population-matched.

    The recorded figure is the summed ``execution_log`` attribution, emitted as
    ``execution_log_tokens`` — NOT ``actual_tokens``. It is a sum over phases
    ``5-execute`` and ``6-finalize`` alone (see :data:`EXECUTION_LOG_PHASES`), so
    the old name asserted a whole-plan actual the ledger never held, and did so
    under the one word a reader trusts least critically.

    The prediction is ``status.metadata.execution_profile_cost_preview`` and its
    population companion :data:`PREDICTED_POPULATION_KEY`. **The delta is emitted
    only when the two populations are equal.** A population-mismatched
    subtraction is the defect — not the field name — because it produces a
    *plausible* number: the ``cost_size_token_table`` recalibration loop
    reads ``delta_pct``, and a delta between a 2-of-6-phase sum and a prediction
    covering some other phase set would recalibrate the cost model against a
    quantity nobody measured. Withholding the delta is what turns that silent
    choice into a legible refusal.

    ``comparison`` is always present and is one of
    :data:`COMPARISON_NOT_ATTEMPTED` (no prediction recorded — the state EVERY
    run is in today, since no producer writes the key),
    :data:`COMPARISON_REFUSED` (populations differ, OR the population is EMPTY,
    OR the sum does not cover its own population because some rows carry an
    unmeasured / unrecognised token column), or :data:`COMPARISON_COMPUTED`
    (populations match AND the population is non-empty AND every in-population
    row was readable; ``delta_tokens`` and ``delta_pct`` accompany it and nowhere
    else).

    The later refusals are the same rule as the first, applied to COVERAGE rather
    than to scope: a delta taken against a floor is as plausible-looking, and as
    unusable for recalibration, as a delta taken across populations. The
    ``execution_log_rows_*`` fields publish the coverage either way, so a reader
    sees the size of the gap and not only its existence.

    ⛔ **The empty-population refusal is not a special case of the coverage one —
    it is what stops the coverage guard from passing VACUOUSLY.** Over zero
    in-population rows the sum is ``0``, ``rows_unmeasured`` and
    ``rows_unrecognised`` are both ``0``, and "every in-population row carried a
    readable token column" is vacuously TRUE — so a manifest with no
    ``execution_log`` at all (composed but never run, or one whose rows were
    never recorded) fell through to :data:`COMPARISON_COMPUTED` and emitted
    ``delta_tokens = 0 - predicted``: a confident delta against a fabricated
    zero, fed straight into the ``cost_size_token_table`` recalibration loop. The
    refusal is therefore keyed on the POPULATION SIZE, which the block publishes
    beside it, rather than on a count of unreadable rows that an empty population
    can never produce.

    Args:
        manifest: The parsed ``execution.toon`` manifest.
        metadata: The ``status.json`` metadata block.

    Returns:
        The ``cost_preview`` fact block.
    """
    coverage = summarize_execution_log_tokens(manifest)
    execution_log_tokens = coverage['total_tokens']
    unreadable_rows = coverage['rows_unmeasured'] + coverage['rows_unrecognised']
    raw_predicted = metadata.get('execution_profile_cost_preview')
    predicted: int | None = None
    # `.strip()` before the digit test so a padded value is read rather than
    # silently discarded — the population field beside it is already stripped,
    # and one function reading two fields by two rules is how the third state
    # below goes unnoticed.
    if isinstance(raw_predicted, bool):
        predicted = None
    elif isinstance(raw_predicted, int):
        predicted = raw_predicted
    elif isinstance(raw_predicted, str) and raw_predicted.strip().isdigit():
        predicted = int(raw_predicted.strip())
    # RECORDED BUT UNPARSEABLE is a third state, and it is not absence. A value
    # that is present and cannot be read (`'12.5'`, `'abc'`, `'-100'`) previously
    # collapsed into `not_attempted` under the reason "no cost preview recorded",
    # which states an absence the record contradicts — the silent choice this
    # deliverable exists to replace with a legible one, committed by the code
    # that replaces it.
    recorded_unparseable = predicted is None and raw_predicted is not None

    raw_population = metadata.get(PREDICTED_POPULATION_KEY)
    predicted_population = (
        raw_population.strip()
        if isinstance(raw_population, str) and raw_population.strip()
        else POPULATION_UNSTATED
    )

    preview: dict[str, Any] = {
        'execution_log_tokens': execution_log_tokens,
        'execution_log_population': EXECUTION_LOG_POPULATION,
        # How much of that population the sum could actually READ. A sum quoted
        # without these is a figure whose coverage nobody stated — the same
        # defect as a figure quoted without its population, one level down.
        'execution_log_rows_in_population': coverage['rows_in_population'],
        'execution_log_rows_measured': coverage['rows_measured'],
        'execution_log_rows_unmeasured': coverage['rows_unmeasured'],
        'execution_log_rows_unrecognised': coverage['rows_unrecognised'],
        'predicted_tokens': predicted,
        'predicted_population': predicted_population if predicted is not None else POPULATION_UNSTATED,
    }

    if predicted is None:
        preview['comparison'] = COMPARISON_NOT_ATTEMPTED
        preview['comparison_reason'] = (
            'status.metadata.execution_profile_cost_preview holds '
            f'{raw_predicted!r}, which is not a token count — the comparison is '
            'not attempted, and this is a recorded value that could not be read '
            'rather than an absent one'
            if recorded_unparseable
            else 'no cost preview recorded in status.metadata.execution_profile_cost_preview'
        )
        return preview

    if predicted_population != EXECUTION_LOG_POPULATION:
        preview['comparison'] = COMPARISON_REFUSED
        preview['comparison_reason'] = (
            'population_mismatch: the recorded sum measures '
            f'{EXECUTION_LOG_POPULATION} while the prediction measures '
            f'{predicted_population}; no delta is emitted, because subtracting '
            'across populations yields a plausible number that would recalibrate '
            'cost_size_token_table against a quantity nobody measured'
        )
        return preview

    if not coverage['rows_in_population']:
        # The populations match by NAME, but the sum was taken over NO ROWS. This
        # branch MUST precede the coverage branch below, because that branch
        # cannot fire here: `rows_unmeasured + rows_unrecognised` is 0 over an
        # empty population, so "every in-population row was readable" is
        # VACUOUSLY true and the fall-through emitted `delta_tokens =
        # 0 - predicted` as a COMPUTED comparison. The refusal keys on the
        # population size — the quantity an empty population actually moves —
        # and names it in the reason so the `0` beside it reads as an
        # unpopulated sum rather than as a measured total.
        preview['comparison'] = COMPARISON_REFUSED
        preview['comparison_reason'] = (
            f'empty_population: the manifest execution_log holds no '
            f'{EXECUTION_LOG_POPULATION} row at all '
            f'({coverage["rows_in_population"]} in-population rows), so the recorded '
            'sum of 0 measures nothing; no delta is emitted, because subtracting a '
            'prediction from an unpopulated sum yields a confident-looking delta '
            'against a fabricated zero'
        )
        return preview

    if unreadable_rows:
        # The populations match, but the SUM does not cover its own population:
        # some rows carry an unmeasured or unrecognised token column, so the
        # figure is a floor. Subtracting a prediction from a floor yields a
        # plausible number that would recalibrate `cost_size_token_table` against
        # a quantity nobody measured — the same reason a population mismatch
        # refuses, applied to coverage instead of scope.
        preview['comparison'] = COMPARISON_REFUSED
        preview['comparison_reason'] = (
            f'incomplete_measurement: {coverage["rows_measured"]} of '
            f'{coverage["rows_in_population"]} in-population row(s) carry a readable '
            f'total_tokens ({coverage["rows_unmeasured"]} unmeasured, '
            f'{coverage["rows_unrecognised"]} unrecognised), so the recorded sum is a '
            'FLOOR rather than a total; no delta is emitted, because a delta against a '
            'floor reads as a measurement of the gap'
        )
        return preview

    preview['comparison'] = COMPARISON_COMPUTED
    preview['delta_tokens'] = execution_log_tokens - predicted
    preview['delta_pct'] = (
        round((execution_log_tokens - predicted) / predicted * 100, 1) if predicted else None
    )
    return preview


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    plan_id = args.plan_id or plan_dir.name

    manifest = load_manifest(plan_dir)
    if manifest is None:
        return {
            'status': 'skipped',
            'aspect': 'routing-decisions',
            'plan_id': plan_id,
            'plan_dir': str(plan_dir),
            'manifest_present': False,
            'reason': f'{MANIFEST_FILENAME} not found',
            'checks': [],
            # DERIVED from the one bucket definition (``_STATUS_BUCKETS``, via
            # ``summarize_checks``) rather than restated as a literal. The literal
            # it replaces carried three keys and omitted ``inconclusive``, so every
            # archived plan predating ``execution.toon`` handed a consumer reading
            # ``summary['inconclusive']`` — which the four-bucket completeness
            # contract in ``references/routing-decision-verification.md`` invites —
            # a missing key. Sum closure held only because ``checks`` is empty.
            # Same construction as the sibling ``check-manifest-consistency.py``
            # skipped return, so the vocabulary here cannot drift from its source.
            'summary': summarize_checks([]),
        }

    metadata = load_status_metadata(plan_dir)
    decision_lines, log_readable = load_decision_log_lines(plan_dir)
    lane_decision_entries = lane_resolution_view(decision_lines)

    # Footprint resolution: prefer an explicitly-supplied ``--diff-file`` (the live
    # end-of-execute diff the retrospective saves), and otherwise recover through the
    # SHARED whole-chain resolver so a POST-MERGE run — no diff-file, worktree gone —
    # re-evaluates the prune predicates against the realized footprint instead of
    # skipping. This is the D4 "one footprint resolution, two consumers": the recall
    # check (check-artifact-consistency) and this mis-prune check recover together off
    # the same resolution. An unresolvable footprint yields have_footprint=False → the
    # mis-prune checks SKIP (the negative control), never a fabricated fail.
    supplied_footprint = load_diff_files(args.diff_file, plan_dir)
    if supplied_footprint is not None:
        # Supplied — including a file that legitimately names nothing. That is a
        # RESOLVED empty footprint, not an unresolvable one, so it must not fall
        # through to the recovery chain and be re-reported as `unresolved`.
        footprint = supplied_footprint
        footprint_source = 'diff_file'
        have_footprint = True
    else:
        resolved = resolve_footprint(plan_dir, args.plan_id if args.mode == 'live' else None)
        if footprint_resolved(resolved):
            footprint = sorted(resolved)
            footprint_source = 'resolved'
            have_footprint = True
        else:
            footprint = []
            footprint_source = 'unresolved'
            have_footprint = False

    mis_prune_checks = evaluate_mis_prunes(
        manifest, footprint, have_footprint, decision_lines, log_readable
    )
    cost_preview = evaluate_cost_preview(manifest, metadata)

    summary = summarize_checks(mis_prune_checks)

    return {
        'status': 'success',
        'aspect': 'routing-decisions',
        'plan_id': plan_id,
        'plan_dir': str(plan_dir),
        'manifest_present': True,
        # Recorded routing decisions (facts).
        'posture': metadata.get('execution_profile'),
        'planning_lane': metadata.get('planning_lane'),
        # Deterministic predicate re-evaluation.
        'footprint_source': footprint_source,
        'mis_prune_checks': mis_prune_checks,
        'cost_preview': cost_preview,
        # Forensic facts for the LLM judgment.
        'recompose_divergence': {'lane_resolution_log_entries': len(lane_decision_entries)},
        'recorded_lane_decisions': lane_decision_entries,
        'summary': summary,
        # The OVER/UNDER posture counterfactual is an LLM judgment over the facts
        # above — NOT computed here. See references/routing-decision-verification.md.
        'llm_judgement_required': True,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Routing-decision verification aspect — deterministic predicate re-evaluation',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Re-evaluate routing-decision predicates', allow_abbrev=False)
    add_plan_id_arg(run_parser, required=False)
    run_parser.add_argument(
        '--archived-plan-path',
        help='Absolute path to archived plan directory (archived mode)',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.add_argument(
        '--diff-file',
        default=None,
        help=(
            'Pre-saved realized footprint (one path per line). A relative path is '
            'resolved against the plan directory first and the cwd second; a supplied '
            'path that resolves to nothing is an error, never an empty footprint. When '
            'ABSENT, the footprint is recovered through the shared resolver '
            '(realized-footprint capture -> merge-commit -> legacy key). Drives the '
            'prune-predicate re-evaluation.'
        ),
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
