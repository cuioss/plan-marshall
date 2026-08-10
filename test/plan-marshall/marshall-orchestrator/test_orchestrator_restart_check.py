#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``cleanup restart-check`` verb of the marshall-orchestrator script.

Exercises the readiness seam against a SCAFFOLDED FIXTURE EPIC under
``PLAN_BASE_DIR`` isolation — never the live ``truthful-signals`` tree.

The verb's whole value is that it refuses to state a confident verdict it cannot
support, so the module is organised around that refusal:

- **Shape** — every signal row carries a verdict, an evidence field, and the
  population it was derived from, and the report carries the sample instant
  beside the verdict. A row missing any of the four is a bare score.
- **Per-signal matched controls** — each owned signal has a ``ready`` control,
  a degraded control, and (where the signal admits one) BOTH a ``not_ready``
  and an ``indeterminate`` control, asserted to be distinct outcomes. An
  unreadable observation must land on ``indeterminate``; landing it on
  ``not_ready`` is the confident-signal defect this verb exists to remove.
- **Floor** — the overall verdict is the floor over the PARTICIPATING rows.
  One ``indeterminate`` among otherwise-``ready`` rows floors the report, and a
  ``not_ready`` row floors it further.
- **The unowned arm** — ``registry_parity`` reports ``not_available``, names
  the spec that owns the surface, and is excluded from the floor. Its presence
  is pinned so a future author cannot quietly delete the field instead of
  implementing it, and a source scan proves no registry/version surface is read
  here at all.

The ``worktree`` signal observes the real repository through the module's single
git seam, so every test that needs a determinate worktree verdict substitutes a
stub for that seam. Leaving it live would make the suite's verdict depend on
whether the developer's tree happened to be clean.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'marshall-orchestrator', 'orchestrator.py')

_orch = load_script_module(
    'plan-marshall', 'marshall-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

cmd_cleanup_restart_check = _orch.cmd_cleanup_restart_check
readiness_floor = _orch._readiness_floor
READINESS_ORDER = _orch.READINESS_ORDER
READY = _orch.READY
NOT_READY = _orch.NOT_READY
INDETERMINATE = _orch.READINESS_INDETERMINATE
NOT_AVAILABLE = _orch.NOT_AVAILABLE
REGISTRY_PARITY_OWNER = _orch.REGISTRY_PARITY_OWNER
INBOX_SUBDIR = _orch.INBOX_SUBDIR

SLUG = 'fixture-restart-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'
CLEAN_SHA = '1234567890abcdef1234567890abcdef12345678'

#: The signals this component OWNS — the ones that participate in the floor.
OWNED_SIGNALS = ('phase', 'running_plans', 'corpus_reconciliation', 'inbox', 'worktree')
#: The one arm whose surface belongs to another component.
UNOWNED_SIGNAL = 'registry_parity'


# =============================================================================
# Fixture builders
# =============================================================================


def _epic_dir(plan_context) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / SLUG


def _row(plan_id: str, status: str = 'shipped') -> dict:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': 'WS-01',
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _write_status(plan_context, rows: list, phase: str = 'orchestrating') -> Path:
    """Write a kind=orchestrator fixture status.json into the isolated store."""
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Restart Epic',
        'phase': phase,
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': 'fixture',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _write_spec(plan_context, name: str) -> Path:
    """Write one readable staged spec so the corpus has a real population."""
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('# Fixture spec\n\n## Claim Labels\n\n- OBSERVED: a claim\n', encoding='utf-8')
    return path


def _write_broken_spec(plan_context, name: str) -> Path:
    """Write a spec whose bytes are not decodable — an UNREADABLE observation."""
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\xff\xfe not valid utf-8 \xff')
    return path


def _make_inbox(plan_context, queued: int = 0, archived: int = 0) -> Path:
    """Materialize a PRESENT inbox/ carrying ``queued`` and ``archived`` messages.

    Message names follow the channel's own ``{sender}-{NNN}.md`` grammar, so the
    counts the verb derives come from real messages rather than from stray files
    the counter would ignore.
    """
    inbox: Path = _epic_dir(plan_context) / INBOX_SUBDIR
    inbox.mkdir(parents=True, exist_ok=True)
    for index in range(queued):
        (inbox / f'fixture-plan-{index + 1:03d}.md').write_text('queued\n', encoding='utf-8')
    if archived:
        archive = inbox / 'archive'
        archive.mkdir(parents=True, exist_ok=True)
        for index in range(archived):
            (archive / f'fixture-plan-{index + 900:03d}.md').write_text('done\n', encoding='utf-8')
    return inbox


def _git_stub(head: str = CLEAN_SHA, porcelain: str = '', unreadable: str | None = None):
    """Build a double for the module's single git seam.

    The seam takes a read-only OPERATION NAME, not argv — the operation-to-argv
    table in the module is the sole authority for what git is asked to do — so
    the double is keyed on the same names and is checked against the module's
    live table by ``test_the_stub_covers_every_declared_read_operation``.

    ``unreadable`` names the operation that must report as UNOBSERVABLE
    (``(None, reason)``), which is how the worktree signal's indeterminate arm is
    reached without depending on the host repository's state.
    """

    def _read(operation: str) -> tuple:
        if unreadable is not None and operation == unreadable:
            return None, f'git {operation} exited 128'
        if operation == 'head-sha':
            return head, ''
        return porcelain, ''

    return _read


def _ready_epic(plan_context, monkeypatch) -> None:
    """Materialize an epic on which EVERY owned signal is ``ready``.

    This is the baseline every degraded control mutates exactly one signal away
    from, so each control isolates the signal it names.
    """
    _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
    _write_spec(plan_context, 'PLAN-01-alpha.md')
    _write_spec(plan_context, 'PLAN-02-beta.md')
    _make_inbox(plan_context, queued=0, archived=2)
    monkeypatch.setattr(_orch, '_git_read', _git_stub())


def _run() -> dict:
    result: dict = cmd_cleanup_restart_check(Namespace(slug=SLUG))
    return result


def _signal_row(result: dict, name: str) -> dict:
    rows: list[dict] = [row for row in result['signals'] if row['signal'] == name]
    assert len(rows) == 1, f'expected exactly one {name!r} row, got {len(rows)}'
    return rows[0]


def _verdicts(result: dict) -> dict:
    return {row['signal']: row['verdict'] for row in result['signals']}


# =============================================================================
# Report shape — no bare scores, and the sample instant rides the verdict
# =============================================================================


class TestRestartCheckShape:
    def test_should_return_one_row_per_signal(self, plan_context, monkeypatch):
        """Non-empty-population guard: the signal roster must materialize."""
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        assert result['status'] == 'success'
        assert result['operation'] == 'cleanup-restart-check'
        assert sorted(row['signal'] for row in result['signals']) == sorted(
            [*OWNED_SIGNALS, UNOWNED_SIGNAL]
        )
        assert result['signals_total'] == len(result['signals']) == len(OWNED_SIGNALS) + 1

    def test_every_signal_carries_a_verdict_evidence_and_a_population(
        self, plan_context, monkeypatch
    ):
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        for row in result['signals']:
            assert set(row) == {'signal', 'verdict', 'evidence', 'population'}
            assert row['verdict'], f'{row["signal"]} carries no verdict'
            assert row['evidence'].strip(), f'{row["signal"]} carries no evidence'
            assert row['population'].strip(), f'{row["signal"]} carries no population'

    def test_each_population_names_what_it_counted(self, plan_context, monkeypatch):
        # A population is only useful if it names the set — a bare integer would
        # be another unattributed number.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context, queued=0, archived=3)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        result = _run()

        assert 'plans[]: 1 row(s) scanned' == _signal_row(result, 'running_plans')['population']
        assert (
            '1 queue row(s) and 1 spec file(s)'
            == _signal_row(result, 'corpus_reconciliation')['population']
        )
        assert 'inbox/: 0 queued and 3 archived' == _signal_row(result, 'inbox')['population']
        assert CLEAN_SHA in _signal_row(result, 'worktree')['population']

    def test_should_carry_the_sample_instant_beside_the_verdict(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        assert result['sampled_at'].endswith('Z')
        assert result['verdict'] in READINESS_ORDER

    def test_should_ride_the_scored_count_beside_the_total(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        assert result['signals_total'] == len(OWNED_SIGNALS) + 1
        assert result['signals_scored'] == len(OWNED_SIGNALS)

    def test_should_error_when_the_epic_has_no_store_tree(self, plan_context):
        result = cmd_cleanup_restart_check(Namespace(slug='absent-restart-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_cleanup_restart_check(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# Per-signal matched controls
# =============================================================================


class TestPhaseSignal:
    def test_a_readable_phase_is_ready(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'phase')

        assert row['verdict'] == READY
        assert 'orchestrating' in row['evidence']

    def test_an_unreadable_phase_is_indeterminate_not_not_ready(self, plan_context, monkeypatch):
        # Degraded control: no status.json at all, so the phase cannot be looked
        # at. Not looking is not the same as looking and finding a problem.
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'phase')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != NOT_READY


class TestRunningPlansSignal:
    def test_a_quiet_queue_is_ready(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'running_plans')

        assert row['verdict'] == READY
        assert row['population'] == 'plans[]: 2 row(s) scanned'

    def test_an_in_flight_plan_is_not_ready_and_is_named(self, plan_context, monkeypatch):
        # Positive control for the DEFINITE hazard arm — a restart mid-run loses
        # the run's context, which is an observed problem, not an unknown.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02', status='running')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'running_plans')

        assert row['verdict'] == NOT_READY
        assert 'PLAN-02' in row['evidence']
        assert row['population'] == 'plans[]: 2 row(s) scanned'

    def test_an_unreadable_queue_is_indeterminate_not_not_ready(self, plan_context, monkeypatch):
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'running_plans')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != NOT_READY
        assert row['population'] == 'plans[]: not readable'


class TestCorpusSignal:
    def test_a_reconciled_corpus_is_ready(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'corpus_reconciliation')

        assert row['verdict'] == READY
        assert row['population'] == '2 queue row(s) and 2 spec file(s)'

    def test_an_orphan_row_is_not_ready(self, plan_context, monkeypatch):
        # Observed and understood: the queue and the specs genuinely disagree.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'corpus_reconciliation')

        assert row['verdict'] == NOT_READY
        assert '1 row(s) without a spec' in row['evidence']

    def test_an_unreadable_spec_is_indeterminate_and_outranks_the_orphan(
        self, plan_context, monkeypatch
    ):
        # The corpus could not be read in full, so the orphan finding computed
        # over the readable part is not a verdict this signal may assert.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02'), _row('PLAN-03')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_broken_spec(plan_context, 'PLAN-02-broken.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'corpus_reconciliation')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != NOT_READY
        assert '1 spec file(s) could not be read' in row['evidence']
        assert row['population'] == '3 queue row(s) and 2 spec file(s)'


class TestInboxSignal:
    def test_an_empty_present_inbox_is_ready(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'inbox')

        assert row['verdict'] == READY
        assert row['population'] == 'inbox/: 0 queued and 2 archived'

    def test_a_queued_message_is_not_ready(self, plan_context, monkeypatch):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context, queued=2)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'inbox')

        assert row['verdict'] == NOT_READY
        assert '2 message(s) still queued' in row['evidence']

    def test_an_absent_inbox_is_indeterminate_never_a_confident_zero(
        self, plan_context, monkeypatch
    ):
        # The two zeros are told apart by the payload: an absent inbox/ is
        # *could not look*, and reporting it as "0 queued — ready" would be the
        # confident zero this whole seam refuses to emit.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'inbox')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != READY
        assert row['population'] == 'inbox/: missing'


class TestWorktreeSignal:
    def test_a_clean_worktree_is_ready_and_names_its_head(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'worktree')

        assert row['verdict'] == READY
        assert CLEAN_SHA in row['evidence']

    def test_an_uncommitted_path_is_not_ready(self, plan_context, monkeypatch):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(
            _orch, '_git_read', _git_stub(porcelain=' M a/b.py\n?? c/d.py\n')
        )

        row = _signal_row(_run(), 'worktree')

        assert row['verdict'] == NOT_READY
        assert '2 uncommitted path(s)' in row['evidence']

    def test_an_unreadable_head_is_indeterminate_not_not_ready(self, plan_context, monkeypatch):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub(unreadable='head-sha'))

        row = _signal_row(_run(), 'worktree')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != NOT_READY
        assert row['population'] == 'git: not readable'

    def test_an_unreadable_status_is_indeterminate_even_when_head_resolves(
        self, plan_context, monkeypatch
    ):
        # Half an observation is not an observation: knowing the sha without
        # knowing whether the tree is clean cannot support a ready verdict.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub(unreadable='worktree-status'))

        row = _signal_row(_run(), 'worktree')

        assert row['verdict'] == INDETERMINATE


# =============================================================================
# The git seam's read-only contract — the table is the authority
# =============================================================================

#: Git subcommands that only OBSERVE. The seam's declared operations are checked
#: against this set rather than against a list of forbidden mutators, because an
#: allowlist fails closed: a mutating subcommand nobody thought to forbid is
#: rejected by default instead of slipping through a denylist's gaps.
READ_ONLY_GIT_SUBCOMMANDS = frozenset(
    {
        'rev-parse',
        'status',
        'log',
        'show',
        'diff',
        'ls-files',
        'ls-tree',
        'cat-file',
        'describe',
        'symbolic-ref',
        'for-each-ref',
        'rev-list',
    }
)


class TestGitSeamIsReadOnlyByConstruction:
    """`cleanup restart-check` is a readiness PROBE, so its one git seam must be
    incapable of writing — not merely uninvoked with a write today."""

    def test_the_declared_operation_population_is_non_empty(self):
        # Non-empty-population guard: every assertion below iterates this table,
        # so an empty one would make all of them vacuously pass.
        operations = _orch._GIT_READ_OPERATIONS

        assert operations, 'the seam declares no read operations'
        assert set(operations) == {'head-sha', 'worktree-status'}, (
            f'the declared operation set changed: {sorted(operations)}'
        )

    def test_every_declared_operation_expands_to_a_read_only_subcommand(self):
        operations = _orch._GIT_READ_OPERATIONS

        offenders = {
            name: argv
            for name, argv in operations.items()
            if not argv or argv[0] not in READ_ONLY_GIT_SUBCOMMANDS
        }

        assert offenders == {}, (
            f'of {len(operations)} declared operation(s), these do not expand to a read-only '
            f'git subcommand: {offenders}'
        )

    def test_an_undeclared_operation_fails_loud_rather_than_reporting_git_unreadable(self):
        # The truthfulness half. Degrading an unknown operation to the seam's
        # `(None, reason)` unobservable path would report a defect in this module
        # as an environmental one — a caller would read "git is not readable" and
        # investigate the repository instead of the code.
        try:
            _orch._git_read('no-such-operation')
        except KeyError:
            return
        raise AssertionError('an undeclared operation did not fail loud')

    def test_no_caller_supplies_git_arguments(self):
        # The structural half: callers must NAME an operation. A surviving
        # `_git_read([...])` call site would mean the argv is composed at the
        # call site again, which is exactly what the table exists to prevent.
        source = SCRIPT_PATH.read_text(encoding='utf-8')

        assert '_git_read(' in source, 'the scan did not read the module under test'
        assert '_git_read([' not in source, 'a caller still passes argv to the git seam'

    def test_the_stub_covers_every_declared_read_operation(self):
        # Keeps the double honest against the seam it doubles: a newly declared
        # operation that the stub does not answer would silently return the
        # porcelain fall-through, and every test using the stub would assert
        # against a value the real seam never produces.
        operations = _orch._GIT_READ_OPERATIONS
        stub = _git_stub(porcelain=' M a/b.py\n')

        answers = {name: stub(name) for name in operations}

        assert len(answers) == len(operations)
        assert answers['head-sha'] == (CLEAN_SHA, '')
        assert answers['worktree-status'] == (' M a/b.py\n', '')
        for name in operations:
            assert stub(name)[0] is not None, f'the stub does not answer {name!r}'


# =============================================================================
# The unowned arm — present, named, and outside the floor
# =============================================================================


class TestRegistryParityArm:
    def test_the_field_is_present_and_names_its_owning_spec(self, plan_context, monkeypatch):
        # Pins the field's PRESENCE so a future author cannot delete the arm
        # instead of implementing it — a deleted arm reads as a clean report.
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), UNOWNED_SIGNAL)

        assert row['verdict'] == NOT_AVAILABLE
        assert REGISTRY_PARITY_OWNER == 'PLAN-TRUTH-059'
        assert REGISTRY_PARITY_OWNER in row['evidence']

    def test_the_unowned_verdict_is_outside_the_floor_vocabulary(self):
        # Structural guard behind the exclusion: the floor is a min over
        # READINESS_ORDER, so a verdict outside that tuple cannot reach it.
        assert READINESS_ORDER == (NOT_READY, INDETERMINATE, READY)
        assert NOT_AVAILABLE not in READINESS_ORDER

    def test_a_not_available_arm_does_not_degrade_a_fully_ready_report(
        self, plan_context, monkeypatch
    ):
        # The behavioural half: every OWNED signal is ready, the unowned arm is
        # present, and the report is ready rather than degraded by it.
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        verdicts = _verdicts(result)
        assert {verdicts[name] for name in OWNED_SIGNALS} == {READY}
        assert verdicts[UNOWNED_SIGNAL] == NOT_AVAILABLE
        assert result['verdict'] == READY
        assert result['signals_scored'] == len(OWNED_SIGNALS)

    def test_the_seam_reads_no_registry_or_version_surface(self):
        # The deliverable builds no parity reader at all. Scanning the module
        # itself is what makes that a checked property rather than a claim.
        source = SCRIPT_PATH.read_text(encoding='utf-8')

        assert 'cleanup-restart-check' in source, 'the scan did not read the module under test'
        for token in ('installPath', 'MARSHALL_VERSION'):
            assert token not in source, f'{token} is read here; the parity surface is not ours'


# =============================================================================
# The floor
# =============================================================================


class TestReadinessFloor:
    def test_one_indeterminate_signal_floors_an_otherwise_ready_report(
        self, plan_context, monkeypatch
    ):
        # Exactly one signal is degraded — the absent inbox/ — and it is the
        # unobservable kind, so the report may not claim ready.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        result = _run()

        verdicts = _verdicts(result)
        assert verdicts['inbox'] == INDETERMINATE
        assert {verdicts[name] for name in OWNED_SIGNALS if name != 'inbox'} == {READY}
        assert result['verdict'] == INDETERMINATE

    def test_a_not_ready_signal_floors_below_an_indeterminate_one(self, plan_context, monkeypatch):
        # Both degraded kinds are present at once; the definite hazard wins.
        _write_status(plan_context, [_row('PLAN-01', status='running')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        result = _run()

        verdicts = _verdicts(result)
        assert verdicts['running_plans'] == NOT_READY
        assert verdicts['inbox'] == INDETERMINATE
        assert result['verdict'] == NOT_READY

    def test_the_floor_over_no_participating_signal_is_indeterminate(self):
        # Nothing observed is not the same as everything fine.
        assert readiness_floor([]) == INDETERMINATE

    def test_the_floor_is_the_worst_participating_verdict(self):
        assert readiness_floor([READY, READY]) == READY
        assert readiness_floor([READY, INDETERMINATE]) == INDETERMINATE
        assert readiness_floor([READY, INDETERMINATE, NOT_READY]) == NOT_READY


# =============================================================================
# Read-only boundary
# =============================================================================


class TestRestartCheckReadOnlyBoundary:
    def test_restart_check_leaves_the_fixture_tree_byte_identical(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)
        root = _epic_dir(plan_context)
        before = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert before, 'fixture tree did not materialize'

        result = _run()

        after = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert after == before
        assert result['status'] == 'success'


# =============================================================================
# CLI boundary (constructed argv at the subprocess boundary)
# =============================================================================


class TestRestartCheckCli:
    def test_should_report_through_cli(self, plan_context):
        # The subprocess observes the REAL repository through the git seam, so
        # the assertions here are structural: the overall verdict legitimately
        # varies with the host tree and is asserted in-process instead.
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)

        result = run_script(
            SCRIPT_PATH, 'cleanup', 'restart-check', '--slug', SLUG, env_overrides=env
        )

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'operation: cleanup-restart-check' in result.stdout
        assert f'signals_total: {len(OWNED_SIGNALS) + 1}' in result.stdout
        assert f'signals_scored: {len(OWNED_SIGNALS)}' in result.stdout
        assert REGISTRY_PARITY_OWNER in result.stdout
