#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``record-step`` subcommand of manage-execution-manifest.py.

The ``record-step`` subcommand appends per-step execution-log rows (outcome +
token attribution) to the manifest's ``execution_log[]`` section. These tests
cover:

- appending ``executed`` / ``skipped`` / ``error`` rows with token attribution;
- the three-state token columns: an explicitly-passed value (including ``0``) is a
  MEASURED value, an OMITTED flag records the ``unmeasured`` token, and the two
  differ in the file bytes;
- the five-way outcome partition — a productive ``loop_back``, a clean run with a
  negative verdict (``failed``), and a dispatch that raised (``error``) are three
  different situations and are recorded as three different values;
- the ordered append-log semantics (re-recording the same step appends another
  row; reading back reflects the recorded sequence);
- ``execution_log_count`` tracking the running row count;
- the missing-manifest error path (TOON ``file_not_found``);
- input-validation rejection of an unknown phase / outcome;
- a CLI subprocess roundtrip exercising the executor plumbing.

Mirrors the tier-2 direct-import + CLI-subprocess split used by the sibling
``test_manage_execution_manifest_read.py`` / ``_validate.py`` suites.
"""

from argparse import Namespace

import pytest

from conftest import get_script_path, load_script_module, parse_ns, run_script

# Script path for subprocess (CLI plumbing) tests. Split into module-level string
# constants so the `parse_ns` calls below stay statically resolvable for the
# loader-registration walker in `test_conftest_loader_contract`.
_BUNDLE = 'plan-marshall'
_SKILL = 'manage-execution-manifest'
_SCRIPT_NAME = 'manage-execution-manifest.py'

SCRIPT_PATH = get_script_path(_BUNDLE, _SKILL, _SCRIPT_NAME)

# Tier 2 direct imports, resolved by (bundle, skill, script).


_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_script'
)
cmd_compose = _mem.cmd_compose
cmd_record_step = _mem.cmd_record_step
read_manifest = _mem.read_manifest
get_plan_dir = _mem.get_plan_dir
EXECUTION_LOG_KEY = _mem.EXECUTION_LOG_KEY
MANIFEST_FILENAME = _mem.MANIFEST_FILENAME
UNMEASURED_COLUMN_TOKEN = _mem.UNMEASURED_COLUMN_TOKEN
VALID_RECORD_PHASES = _mem.VALID_RECORD_PHASES
VALID_RECORD_OUTCOMES = _mem.VALID_RECORD_OUTCOMES
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Step-ownership routing primitives live in _manifest_core (loaded directly:
# the hyphenated entry does not re-export them). See the "Step ownership"
# section in _manifest_core.py.
_core = load_script_module(
    'plan-marshall', 'manage-execution-manifest', '_manifest_core.py', module_name='_mem_core'
)
owner_of = _core.owner_of
is_leaf_dispatchable = _core.is_leaf_dispatchable
validate_step_owner = _core.validate_step_owner
VALID_STEP_OWNERS = _core.VALID_STEP_OWNERS
DEFAULT_STEP_OWNER = _core.DEFAULT_STEP_OWNER
ORCHESTRATOR_OWNED_STEPS = _core.ORCHESTRATOR_OWNED_STEPS

# Quiet down the best-effort decision-log writes so tests don't depend on a
# running executor / a resolvable plan log dir.
_mem._log_decision = lambda *a, **kw: None
_mem._log_record_step = lambda *a, **kw: None

# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'rec-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps,
        commit_and_push=commit_and_push,
    )


def _record_ns(
    plan_id: str = 'rec-plan',
    step_id: str = 'verify:quality-gate',
    phase: str = '5-execute',
    outcome: str = 'executed',
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
) -> Namespace:
    """Build ``record-step`` args through the script's OWN parser.

    ``None`` means the flag is OMITTED from the argv — the state the writer
    records as the ``unmeasured`` token. That distinction cannot be expressed by a
    hand-built ``argparse.Namespace``: the whole discriminator lives in the
    parser's ``default=None``, so a namespace assembled by hand bypasses the one
    thing under test and would let the omitted case pass against a writer that
    still defaults to ``0``.
    """
    argv = [
        'record-step',
        '--plan-id', plan_id,
        '--step-id', step_id,
        '--phase', phase,
        '--outcome', outcome,
    ]
    for flag, value in (
        ('--total-tokens', total_tokens),
        ('--tool-uses', tool_uses),
        ('--duration-ms', duration_ms),
    ):
        if value is not None:
            argv += [flag, str(value)]
    ns: Namespace = parse_ns(_BUNDLE, _SKILL, _SCRIPT_NAME, *argv, register=False)
    return ns


def _compose(plan_id: str) -> None:
    """Materialize a manifest for ``plan_id`` (record-step requires one)."""
    cmd_compose(_compose_ns(plan_id=plan_id))


# =============================================================================
# Append + token-attribution tests
# =============================================================================


def test_record_executed_appends_row_with_token_attribution(plan_context):
    """An executed record appends one row carrying its token-attribution triple."""
    _compose('rec-exec')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-exec',
            step_id='verify:quality-gate',
            phase='5-execute',
            outcome='executed',
            total_tokens=1200,
            tool_uses=7,
            duration_ms=4200,
        )
    )

    assert result is not None
    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['step_id'] == 'verify:quality-gate'
    assert result['phase'] == '5-execute'
    assert result['outcome'] == 'executed'
    assert result['total_tokens'] == 1200
    assert result['tool_uses'] == 7
    assert result['duration_ms'] == 4200
    assert result['execution_log_count'] == 1
    assert 'timestamp' in result


def test_record_executed_persists_row_to_manifest(plan_context):
    """The appended row is persisted into the manifest's execution_log section."""
    _compose('rec-persist')

    cmd_record_step(
        _record_ns(
            plan_id='rec-persist',
            step_id='verify:module-tests',
            total_tokens=900,
            tool_uses=3,
            duration_ms=1500,
        )
    )

    manifest = read_manifest('rec-persist')
    assert manifest is not None
    log = manifest[EXECUTION_LOG_KEY]
    assert isinstance(log, list)
    assert len(log) == 1
    entry = log[0]
    assert entry['step_id'] == 'verify:module-tests'
    assert entry['outcome'] == 'executed'
    assert entry['total_tokens'] == 900
    assert entry['tool_uses'] == 3
    assert entry['duration_ms'] == 1500
    assert 'timestamp' in entry


def test_record_skipped_appends_row(plan_context):
    """A skipped step records a row with the skipped outcome."""
    _compose('rec-skip')

    result = cmd_record_step(
        _record_ns(plan_id='rec-skip', step_id='verify:coverage', outcome='skipped')
    )

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'skipped'
    manifest = read_manifest('rec-skip')
    assert manifest is not None
    assert manifest[EXECUTION_LOG_KEY][0]['outcome'] == 'skipped'


def test_record_error_outcome_appends_row(plan_context):
    """An error step records a row with the error outcome."""
    _compose('rec-error')

    result = cmd_record_step(
        _record_ns(plan_id='rec-error', step_id='ci-verify', phase='6-finalize', outcome='error')
    )

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'error'
    assert result['phase'] == '6-finalize'


def test_explicitly_passed_zero_is_a_measured_zero(plan_context):
    """``--total-tokens 0`` is a MEASUREMENT and is stored as the integer ``0``.

    A skipped step genuinely consumed nothing, and its caller says so by passing
    the flag. Nothing about that row may read as unmeasured.
    """
    _compose('rec-measured-zero')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-measured-zero',
            step_id='verify:quality-gate',
            outcome='skipped',
            total_tokens=0,
            tool_uses=0,
            duration_ms=0,
        )
    )

    assert result is not None
    assert result['total_tokens'] == 0
    assert result['tool_uses'] == 0
    assert result['duration_ms'] == 0
    entry = read_manifest('rec-measured-zero')[EXECUTION_LOG_KEY][0]
    assert entry['total_tokens'] == 0
    assert entry['tool_uses'] == 0
    assert entry['duration_ms'] == 0


def test_omitted_flags_record_the_unmeasured_token(plan_context):
    """OMITTING the flags records the token — never a fabricated ``0``."""
    _compose('rec-unmeasured')

    result = cmd_record_step(
        _record_ns(plan_id='rec-unmeasured', step_id='verify:quality-gate', outcome='executed')
    )

    assert result is not None
    assert result['total_tokens'] == UNMEASURED_COLUMN_TOKEN
    assert result['tool_uses'] == UNMEASURED_COLUMN_TOKEN
    assert result['duration_ms'] == UNMEASURED_COLUMN_TOKEN
    entry = read_manifest('rec-unmeasured')[EXECUTION_LOG_KEY][0]
    assert entry['total_tokens'] == UNMEASURED_COLUMN_TOKEN
    assert entry['tool_uses'] == UNMEASURED_COLUMN_TOKEN
    assert entry['duration_ms'] == UNMEASURED_COLUMN_TOKEN


def test_a_measured_zero_and_an_omitted_flag_differ_in_the_file_bytes(plan_context):
    """The distinction survives to disk — asserted on the BYTES, not a round trip.

    ⛔ A round-trip assertion (write, then read back through the same reader)
    passes against the defect: if the writer collapsed both states to ``0`` the
    reader would faithfully return ``0`` twice and the assertion would still be
    about self-consistency rather than about the distinction. Reading the raw
    ``execution.toon`` text is what makes this test capable of failing against a
    writer that fabricates the zero.
    """
    _compose('rec-bytes')
    cmd_record_step(
        _record_ns(
            plan_id='rec-bytes',
            step_id='measured',
            outcome='skipped',
            total_tokens=0,
            tool_uses=0,
            duration_ms=0,
        )
    )
    cmd_record_step(_record_ns(plan_id='rec-bytes', step_id='omitted', outcome='executed'))

    raw = (get_plan_dir('rec-bytes') / MANIFEST_FILENAME).read_text(encoding='utf-8')
    measured_line = next(line for line in raw.splitlines() if line.strip().startswith('measured,'))
    omitted_line = next(line for line in raw.splitlines() if line.strip().startswith('omitted,'))

    assert measured_line != omitted_line
    assert UNMEASURED_COLUMN_TOKEN not in measured_line
    assert UNMEASURED_COLUMN_TOKEN in omitted_line


def test_the_parser_supplies_none_not_zero_for_an_omitted_flag(plan_context):
    """The discriminator lives in the PARSER's default, so it is pinned there.

    ``default=0`` would make an omitted flag reach the handler byte-identical to
    an explicit ``0``, and no care in the handler could recover the distinction.
    The handler test above cannot see that regression — it would keep passing
    while every omitted column silently became a measured zero.
    """
    omitted = _record_ns(plan_id='rec-parser', step_id='verify:quality-gate')
    supplied = _record_ns(plan_id='rec-parser', step_id='verify:quality-gate', total_tokens=0)

    assert omitted.total_tokens is None
    assert omitted.tool_uses is None
    assert omitted.duration_ms is None
    assert supplied.total_tokens == 0


def test_unmeasured_token_matches_the_sibling_ledger():
    """The mirrored literal agrees with ``manage-metrics``' own definition.

    The absence-vs-zero contract is a property of the ledger FAMILY, so the two
    skills define the same literal independently (they run in different processes
    and neither may import the other's private module). Nothing but this check
    stops the two drifting into two different tokens, at which point every
    cross-ledger reader would silently classify one skill's unmeasured column as
    unrecognised.
    """
    metrics = load_script_module(
        'plan-marshall', 'manage-metrics', 'manage-metrics.py', module_name='_mm_token_drift'
    )

    assert UNMEASURED_COLUMN_TOKEN == metrics.UNMEASURED_COLUMN_TOKEN


def test_record_negative_token_values_clamped_to_zero(plan_context):
    """Negative attribution inputs are clamped to zero (max(0, ...))."""
    _compose('rec-neg')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-neg',
            step_id='verify:quality-gate',
            total_tokens=-50,
            tool_uses=-1,
            duration_ms=-999,
        )
    )

    assert result is not None
    assert result['total_tokens'] == 0
    assert result['tool_uses'] == 0
    assert result['duration_ms'] == 0


# =============================================================================
# Ordered append-log semantics
# =============================================================================


def test_record_appends_in_order_and_count_increments(plan_context):
    """Repeated records append rows deterministically; reading back reflects order."""
    _compose('rec-order')

    r1 = cmd_record_step(_record_ns(plan_id='rec-order', step_id='verify:quality-gate', outcome='executed'))
    r2 = cmd_record_step(_record_ns(plan_id='rec-order', step_id='verify:module-tests', outcome='executed'))
    r3 = cmd_record_step(_record_ns(plan_id='rec-order', step_id='verify:coverage', outcome='skipped'))

    # running count tracks the append log
    assert r1['execution_log_count'] == 1
    assert r2['execution_log_count'] == 2
    assert r3['execution_log_count'] == 3

    # read-back preserves the recorded sequence
    log = read_manifest('rec-order')[EXECUTION_LOG_KEY]
    assert [e['step_id'] for e in log] == ['verify:quality-gate', 'verify:module-tests', 'verify:coverage']
    assert [e['outcome'] for e in log] == ['executed', 'executed', 'skipped']


def test_record_same_step_twice_appends_two_rows(plan_context):
    """The log is an ordered append log, not a keyed map — repeats append."""
    _compose('rec-dup')

    cmd_record_step(_record_ns(plan_id='rec-dup', step_id='verify:quality-gate', outcome='error'))
    result = cmd_record_step(_record_ns(plan_id='rec-dup', step_id='verify:quality-gate', outcome='executed'))

    assert result['execution_log_count'] == 2
    log = read_manifest('rec-dup')[EXECUTION_LOG_KEY]
    assert len(log) == 2
    assert log[0]['outcome'] == 'error'
    assert log[1]['outcome'] == 'executed'


# =============================================================================
# Canonical step-key: --step-id is canonicalized before the row is appended
# =============================================================================


def test_record_default_prefixed_step_id_stored_canonicalized(plan_context):
    """A ``default:``-prefixed --step-id is stored under the bare canonical key.

    The record-step handler routes --step-id through the shared
    canonicalize_step_key so execution-log keys reconcile with the manifest's
    phase-step keys.
    """
    _compose('rec-canon-default')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-canon-default',
            step_id='default:push',
            phase='6-finalize',
            outcome='executed',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['step_id'] == 'push'
    entry = read_manifest('rec-canon-default')[EXECUTION_LOG_KEY][0]
    assert entry['step_id'] == 'push'


def test_record_promoted_alias_step_id_stored_bare(plan_context):
    """A promoted ``plan-marshall:automatic-review`` --step-id stores as bare ``automatic-review``."""
    _compose('rec-canon-promoted')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-canon-promoted',
            step_id='plan-marshall:automatic-review',
            phase='6-finalize',
            outcome='executed',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['step_id'] == 'automatic-review'
    entry = read_manifest('rec-canon-promoted')[EXECUTION_LOG_KEY][0]
    assert entry['step_id'] == 'automatic-review'


def test_record_project_prefixed_step_id_preserved(plan_context):
    """A ``project:``-prefixed --step-id is preserved verbatim (not stripped to bare)."""
    _compose('rec-canon-project')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-canon-project',
            step_id='project:finalize-step-plugin-doctor',
            phase='6-finalize',
            outcome='executed',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['step_id'] == 'project:finalize-step-plugin-doctor'
    entry = read_manifest('rec-canon-project')[EXECUTION_LOG_KEY][0]
    assert entry['step_id'] == 'project:finalize-step-plugin-doctor'


# =============================================================================
# Error / validation paths
# =============================================================================


def test_record_missing_manifest_returns_none_with_toon_error(plan_context, capsys):
    """record-step against a plan with no manifest emits file_not_found via TOON."""
    # no compose for this plan id.
    result = cmd_record_step(_record_ns(plan_id='rec-no-manifest'))

    assert result is None
    captured = capsys.readouterr()
    assert 'file_not_found' in captured.out


def test_record_invalid_phase_returns_error(plan_context):
    """An unknown phase is rejected with an invalid_phase error dict."""
    _compose('rec-bad-phase')

    result = cmd_record_step(_record_ns(plan_id='rec-bad-phase', phase='7-deploy'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    # No row written.
    assert EXECUTION_LOG_KEY not in (read_manifest('rec-bad-phase') or {})


def test_record_invalid_outcome_returns_error(plan_context):
    """An unknown outcome is rejected with an invalid_outcome error dict."""
    _compose('rec-bad-outcome')

    result = cmd_record_step(_record_ns(plan_id='rec-bad-outcome', outcome='maybe'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_outcome'
    assert EXECUTION_LOG_KEY not in (read_manifest('rec-bad-outcome') or {})


def test_record_phase_validated_before_manifest_read(plan_context):
    """Phase validation fires even when no manifest exists (pure input guard)."""
    # no compose.
    result = cmd_record_step(_record_ns(plan_id='rec-guard', phase='nope'))

    assert result is not None
    assert result['error'] == 'invalid_phase'


def test_valid_record_enums_are_the_documented_sets(plan_context):
    """Guard the contract constants the record-step subcommand validates against."""
    assert VALID_RECORD_PHASES == ('5-execute', '6-finalize')
    assert VALID_RECORD_OUTCOMES == ('executed', 'skipped', 'loop_back', 'failed', 'error')


def test_a_productive_loop_back_is_recordable_as_itself(plan_context):
    """⛔ A findings-bearing return is a loop-back, not an error.

    Before the partition it was recorded as `error`, so every archive-wide
    analysis that counts errors mis-graded a multi-round self-review as a
    defect — the more thoroughly a gate worked, the worse its plan looked.
    """
    _compose('rec-loop-back')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-loop-back',
            step_id='pre-submission-self-review',
            phase='6-finalize',
            outcome='loop_back',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'loop_back'
    assert read_manifest('rec-loop-back')[EXECUTION_LOG_KEY][0]['outcome'] == 'loop_back'


def test_a_clean_run_with_a_negative_verdict_is_recordable_as_failed(plan_context):
    """`failed` stays reachable, and separably so, for a red gate.

    A step that RAN CLEANLY and self-assessed not-clean is neither a productive
    hand-back nor a dispatch that raised; collapsing it into either loses the
    one fact the row exists to carry.
    """
    _compose('rec-failed')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-failed',
            step_id='pre-push-quality-gate',
            phase='6-finalize',
            outcome='failed',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'failed'


def test_the_five_outcomes_are_pairwise_distinct_on_disk(plan_context):
    """The partition is a property of the ROWS, not of a reader's convention.

    Recording all five and reading them back is what makes the ledger's own
    bytes answer "which situation was this" — the question a single collapsed
    `error` value could not answer at all.
    """
    _compose('rec-partition')
    for outcome in VALID_RECORD_OUTCOMES:
        cmd_record_step(
            _record_ns(
                plan_id='rec-partition',
                step_id=f'step-{outcome}',
                phase='6-finalize',
                outcome=outcome,
            )
        )

    rows = read_manifest('rec-partition')[EXECUTION_LOG_KEY]

    assert [row['outcome'] for row in rows] == list(VALID_RECORD_OUTCOMES)
    assert len({row['outcome'] for row in rows}) == len(VALID_RECORD_OUTCOMES)


def test_an_outcome_outside_the_partition_is_still_refused(plan_context):
    """Widening the vocabulary must not widen it to anything.

    Without this the two additions above would be indistinguishable from
    dropping the membership check altogether.
    """
    _compose('rec-partition-closed')

    result = cmd_record_step(
        _record_ns(plan_id='rec-partition-closed', step_id='x', outcome='returned_with_findings')
    )

    assert result is not None
    assert result['error'] == 'invalid_outcome'


@pytest.mark.parametrize('outcome', ['skipped', 'loop_back', 'failed'])
def test_a_step_outcome_is_representable_in_the_manifest_ledger(plan_context, outcome):
    """Cross-ledger representability, derived from BOTH parsers rather than asserted.

    A step records its situation on `status.metadata.phase_steps` through
    `mark-step-done`, and the dispatcher mirrors it into the manifest's
    `execution_log[]` through `record-step`. If one vocabulary can express a
    situation the other cannot, the mirror has to collapse it — which is exactly
    how a productive loop-back became an `error` row in the first place.

    Acceptance is probed through each script's OWN parser and handler, so this
    cannot pass against a literal list that has drifted from either surface.
    `done` is deliberately excluded: it maps to `executed`, the one value the
    two vocabularies name differently by design.
    """
    parse_ns(
        'plan-marshall',
        'manage-status',
        'manage-status.py',
        'mark-step-done',
        '--plan-id', 'rec-cross-ledger',
        '--phase', '6-finalize',
        '--step', 'a-step',
        '--outcome', outcome,
        register=False,
    )

    # plan_id is kebab-case-validated, so an outcome carrying an underscore
    # (`loop_back`) cannot be interpolated into one verbatim.
    plan_id = 'rec-cross-' + outcome.replace('_', '-')
    _compose(plan_id)
    result = cmd_record_step(
        _record_ns(plan_id=plan_id, step_id='a-step', phase='6-finalize', outcome=outcome)
    )

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == outcome


# =============================================================================
# Step-ownership routing (orchestrator-owned vs leaf-dispatchable)
# =============================================================================


def test_valid_step_owners_vocabulary():
    """The declared owner vocabulary is the closed two-value set."""
    assert VALID_STEP_OWNERS == ('orchestrator-owned', 'leaf-dispatchable')
    assert DEFAULT_STEP_OWNER == 'leaf-dispatchable'


def test_validate_step_owner_accepts_declared_and_rejects_unknown():
    """validate_step_owner is a membership predicate over VALID_STEP_OWNERS."""
    assert validate_step_owner('orchestrator-owned') is True
    assert validate_step_owner('leaf-dispatchable') is True
    assert validate_step_owner('main-only') is False
    assert validate_step_owner('') is False


def test_owner_of_sub_dispatching_steps_are_orchestrator_owned():
    """The known sub-dispatching finalize steps resolve to orchestrator-owned."""
    for step in (
        'finalize-step-plugin-doctor',
        'pre-submission-self-review',
        'automatic-review',
        'finalize-step-simplify',
    ):
        assert owner_of(step) == 'orchestrator-owned', step
        assert step in ORCHESTRATOR_OWNED_STEPS


def test_owner_of_strips_default_and_project_prefixes():
    """default:- and project:-prefixed spellings classify identically to the bare name."""
    assert owner_of('project:finalize-step-plugin-doctor') == 'orchestrator-owned'
    assert owner_of('default:pre-submission-self-review') == 'orchestrator-owned'
    assert owner_of('default:finalize-step-simplify') == 'orchestrator-owned'


def test_owner_of_defaults_leaf_dispatchable():
    """Steps not in the registry default to leaf-dispatchable."""
    for step in ('push', 'create-pr', 'ci-verify', 'verify:quality-gate', 'archive-plan'):
        assert owner_of(step) == 'leaf-dispatchable', step


def test_is_leaf_dispatchable_rejects_orchestrator_owned_step():
    """A dispatched leaf must never be handed an orchestrator-owned step."""
    assert is_leaf_dispatchable('project:finalize-step-plugin-doctor') is False
    assert is_leaf_dispatchable('automatic-review') is False
    # A leaf-dispatchable step is accepted.
    assert is_leaf_dispatchable('push') is True
    assert is_leaf_dispatchable('verify:quality-gate') is True


# =============================================================================
# CLI plumbing (subprocess) tests
# =============================================================================


def test_cli_record_step_roundtrip(plan_context):
    """record-step over the CLI appends a row and echoes the success TOON."""
    # compose a manifest via the CLI so the subprocess sees it.
    compose = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-rec',
        '--plan-change-type',
        'feature',
        '--track',
        'complex',
        '--scope-estimate',
        'multi_module',
        '--affected-files-count',
        '5',
    )
    assert compose.returncode == 0

    result = run_script(
        SCRIPT_PATH,
        'record-step',
        '--plan-id',
        'cli-rec',
        '--step-id',
        'verify:quality-gate',
        '--phase',
        '5-execute',
        '--outcome',
        'executed',
        '--total-tokens',
        '1500',
        '--tool-uses',
        '4',
        '--duration-ms',
        '2200',
    )

    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'success'
    assert data['recorded'] is True
    assert data['step_id'] == 'verify:quality-gate'
    assert data['outcome'] == 'executed'
    assert data['total_tokens'] == 1500
    assert data['tool_uses'] == 4
    assert data['duration_ms'] == 2200
    assert data['execution_log_count'] == 1


def test_cli_record_step_missing_manifest_emits_toon_error(plan_context):
    """record-step over the CLI without a manifest emits file_not_found via TOON."""
    result = run_script(
        SCRIPT_PATH,
        'record-step',
        '--plan-id',
        'cli-rec-missing',
        '--step-id',
        'verify:quality-gate',
        '--phase',
        '5-execute',
        '--outcome',
        'executed',
    )

    # TOON contract: script exits 0 on missing-file errors.
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'file_not_found'
