#!/usr/bin/env python3
"""Module tests for the ``plan-doctor`` skill.

Covers the post-hoc plan-artifact diagnostics that scan ``TASK-*.json``
files for unresolved lesson-ID references. The five contract cases
required by TASK-006:

    (a) Clean plan with no lesson-ID-shaped tokens → empty findings.
    (b) Plan with one phantom ID in a TASK description → 1 finding with
        correct ``plan_id`` / ``task_file`` / ``token`` / ``reason``.
    (c) Plan with a *valid* (live) lesson ID → no finding.
    (d) Plan with a malformed 4-segment token → no finding (regex shape
        rejects it before the inventory lookup).
    (e) ``--all`` sweep over a fixture directory containing mixed
        clean/dirty plans → finding count + per-plan attribution match
        the seeded data.

All cases follow the AAA pattern (arrange / act / assert) and exercise
the script via subprocess invocation through ``conftest.run_script``,
mirroring the Tier-3 CLI-plumbing pattern in
``test_manage_tasks.py`` / ``test_manage_tasks_input_validation.py``.

Direct ``PYTHONPATH``-rigged python invocation is intentionally avoided
(see CLAUDE.md hard rules); the test runner exposes the script through
the executor mappings so the production notation
``plan-marshall:plan-doctor:plan_doctor`` is what gets exercised in
production. Here we use ``run_script`` against the resolved script path —
``run_script`` propagates ``_MARKETPLACE_SCRIPT_DIRS`` on ``PYTHONPATH``
so cross-skill imports (``input_validation``, ``file_ops`` …) resolve
exactly as they do under the executor.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Insert this test directory at the FRONT of sys.path so the helper module
# resolves to the per-test-package version rather than any same-named
# module that happened to load earlier (sys.modules caches by name and
# pytest's collection order is not stable across runs). The module is
# named ``_doctor_fixtures`` rather than ``_fixtures`` to avoid colliding
# with the unrelated ``_fixtures.py`` in
# ``test/plan-marshall/plan-retrospective/``: Python's module cache keys
# on the bare module name, and the executor-built sys.path keeps every
# test subdirectory reachable, so two ``_fixtures`` modules in the same
# tree shadow each other in collection order. Using a domain-prefixed
# name keeps both helpers loadable at the same time and complies with
# the task contract's "NOT conftest.py" requirement.
sys.path.insert(0, str(Path(__file__).parent))

from _doctor_fixtures import (  # type: ignore[import-not-found]  # noqa: E402
    REAL_LESSON_IDS,
    make_archived_plan,
    make_healthy_plan,
    make_plan_with_tasks,
    make_status_json,
    make_worktree_dir,
    seed_lesson_inventory,
)

from conftest import (  # type: ignore[import-not-found]
    get_script_path,
    run_script,
)

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-doctor', 'plan_doctor.py')


# =============================================================================
# Helpers
# =============================================================================


def _scan_plan(plan_id: str):
    """Invoke ``plan_doctor scan --plan-id <id> --no-emit`` and return the result.

    ``--no-emit`` is used throughout because these tests assert on the TOON
    summary contract; the Q-Gate write path is exercised separately by
    ``manage-findings`` tests. The subprocess inherits ``PLAN_BASE_DIR``
    from ``plan_context`` so plan, lessons, and Q-Gate paths all resolve
    against the per-test ``tmp_path``.
    """
    return run_script(SCRIPT_PATH, 'scan', '--plan-id', plan_id, '--no-emit')


def _scan_all():
    """Invoke ``plan_doctor scan --all --no-emit`` and return the result."""
    return run_script(SCRIPT_PATH, 'scan', '--all', '--no-emit')


def _findings(payload: dict) -> list[dict]:
    """Normalise the ``findings`` slot to a list of dicts.

    The TOON parser surfaces a single-row table as a dict (not a list),
    so callers that expect "0-or-many" semantics need this coercion to
    avoid a brittle ``isinstance(list)`` check at every assertion site.
    """
    raw = payload.get('findings', []) or []
    if isinstance(raw, dict):
        return [raw]
    return list(raw)


# =============================================================================
# Case (a): clean plan — no lesson-ID-shaped tokens at all → empty findings
# =============================================================================


def test_clean_plan_yields_empty_findings(plan_context):
    # Arrange — one plan, two tasks, prose with no lesson-ID-shaped tokens.
    plan_id = 'doctor-case-a-clean'
    plan_dir = plan_context.plan_dir_for(plan_id)
    seed_lesson_inventory(plan_context.fixture_dir)
    make_plan_with_tasks(
        plan_dir,
        [
            {
                'title': 'Implement validator',
                'description': 'Add input validation to the auth service.',
            },
            {
                'title': 'Add unit tests',
                'description': 'Cover the new validator with AAA-pattern tests.',
            },
        ],
    )

    # Act
    result = _scan_plan(plan_id)

    # Assert — exit 0 (no findings), summary echoes both files, zero rows.
    assert result.returncode == 0, result.stderr
    payload = result.toon()
    assert payload['status'] == 'success'
    assert payload['checked_files'] == 2
    assert payload['findings_count'] == 0
    assert _findings(payload) == []


# =============================================================================
# Case (b): one phantom ID in a TASK description → exactly 1 finding
# =============================================================================


def test_phantom_lesson_id_yields_one_finding_with_correct_attribution(plan_context):
    # Arrange — one task contains a syntactically-valid lesson ID that does
    # NOT exist in the seeded inventory. We pick a future-dated ID so it is
    # guaranteed not to collide with real fixtures.
    plan_id = 'doctor-case-b-phantom'
    phantom = '2099-01-01-00-001'
    plan_dir = plan_context.plan_dir_for(plan_id)
    seed_lesson_inventory(plan_context.fixture_dir)
    files = make_plan_with_tasks(
        plan_dir,
        [
            {
                'title': 'Refactor token store',
                # Phantom ID embedded in prose, mid-sentence.
                'description': (f'Apply lesson {phantom} to the token store implementation.'),
            },
        ],
    )
    expected_file = files[0].name  # 'TASK-001.json'

    # Act
    result = _scan_plan(plan_id)

    # Assert — exit 1 (findings present), exactly one finding with full
    # attribution: plan_id, task_file, token, reason.
    assert result.returncode == 1, result.stderr
    payload = result.toon()
    assert payload['status'] == 'success'
    assert payload['checked_files'] == 1
    assert payload['findings_count'] == 1

    findings = _findings(payload)
    assert len(findings) == 1
    finding = findings[0]
    assert finding['plan_id'] == plan_id
    assert finding['task_file'] == expected_file
    assert finding['token'] == phantom
    assert finding['reason'] == 'phantom_lesson_id'


# =============================================================================
# Case (c): live (valid) lesson ID → no finding
# =============================================================================


def test_valid_lesson_id_yields_no_finding(plan_context):
    # Arrange — task references a lesson ID that DOES exist in the seeded
    # inventory. The reference is in prose (not a code block) to mirror the
    # production usage pattern in plan request/outline documents.
    plan_id = 'doctor-case-c-valid'
    valid_id = REAL_LESSON_IDS[0]  # '2026-04-24-12-003' — guaranteed live.
    plan_dir = plan_context.plan_dir_for(plan_id)
    seed_lesson_inventory(plan_context.fixture_dir)
    make_plan_with_tasks(
        plan_dir,
        [
            {
                'title': 'Apply existing lesson',
                'description': (f'See lesson {valid_id} for the canonical pattern.'),
            },
        ],
    )

    # Act
    result = _scan_plan(plan_id)

    # Assert — exit 0; one file checked; zero findings (the token resolved
    # against the live inventory).
    assert result.returncode == 0, result.stderr
    payload = result.toon()
    assert payload['status'] == 'success'
    assert payload['checked_files'] == 1
    assert payload['findings_count'] == 0
    assert _findings(payload) == []


# =============================================================================
# Case (d): malformed 4-segment token → regex rejects it, no finding
# =============================================================================


def test_malformed_four_segment_token_yields_no_finding(plan_context):
    # Arrange — the canonical regex requires 5 dash-separated segments
    # (YYYY-MM-DD-HH-NNN). A 4-segment token shaped YYYY-MM-DD-NNN must be
    # filtered out by the regex shape itself, BEFORE any inventory lookup.
    # That is why the assertion checks ``checked_files == 1`` and
    # ``findings_count == 0`` — the file was scanned but no candidate token
    # made it past the shape filter.
    plan_id = 'doctor-case-d-malformed'
    plan_dir = plan_context.plan_dir_for(plan_id)
    seed_lesson_inventory(plan_context.fixture_dir)
    make_plan_with_tasks(
        plan_dir,
        [
            {
                'title': 'Looks-lessonish but is not',
                'description': (
                    # 4-segment shape — must NOT trigger an inventory lookup.
                    'Reference 2026-04-29-001 is a typo, not a lesson ID.'
                ),
            },
        ],
    )

    # Act
    result = _scan_plan(plan_id)

    # Assert
    assert result.returncode == 0, result.stderr
    payload = result.toon()
    assert payload['status'] == 'success'
    assert payload['checked_files'] == 1
    assert payload['findings_count'] == 0
    assert _findings(payload) == []


# =============================================================================
# Case (e): ``--all`` over mixed clean/dirty plans → counts + attribution
# =============================================================================


def test_scan_all_aggregates_findings_with_per_plan_attribution(plan_context):
    # The plan_context fixture pre-creates an empty ``pytest-test`` plan dir
    # which the ``--all`` directory rules would otherwise flag as an orphan
    # and bump ``plans_scanned`` to 4. Remove it so the sweep sees exactly
    # the three plans seeded below.
    shutil.rmtree(plan_context.plan_dir_for(plan_context.plan_id), ignore_errors=True)
    # Arrange — three plans in the same fixture directory:
    #   * ``mixed-clean`` (no findings)
    #   * ``mixed-dirty-one`` (1 phantom in TASK-001)
    #   * ``mixed-dirty-two`` (1 phantom in TASK-001 + 1 valid ID in TASK-002,
    #     so only 1 finding from this plan)
    # Total expected: 2 findings, attributed to the two dirty plans, with
    # the matching task files. We use ``plan_context`` for the LAST plan so
    # ``PLAN_BASE_DIR`` survives the sweep, then materialise the other two
    # under the same ``fixture_dir``.
    phantom_one = '2099-01-01-00-001'
    phantom_two = '2099-12-31-23-999'
    valid_id = REAL_LESSON_IDS[1]  # '2026-04-29-10-001'

    clean_dir = plan_context.plan_dir_for('mixed-clean')
    seed_lesson_inventory(plan_context.fixture_dir)
    # Plan 1: clean.
    make_plan_with_tasks(
        clean_dir,
        [
            {
                'title': 'Clean task',
                'description': 'No lesson references at all.',
            },
        ],
    )

    # Plan 2: one phantom finding.
    dirty_one_dir = plan_context.fixture_dir / 'plans' / 'mixed-dirty-one'
    dirty_one_dir.mkdir(parents=True, exist_ok=True)
    make_plan_with_tasks(
        dirty_one_dir,
        [
            {
                'title': 'Phantom one',
                'description': f'Bogus lesson {phantom_one} reference.',
            },
        ],
    )

    # Plan 3: one phantom + one valid → 1 finding (the phantom only).
    dirty_two_dir = plan_context.fixture_dir / 'plans' / 'mixed-dirty-two'
    dirty_two_dir.mkdir(parents=True, exist_ok=True)
    make_plan_with_tasks(
        dirty_two_dir,
        [
            {
                'title': 'Phantom two',
                'description': f'Another bogus {phantom_two} reference.',
            },
            {
                'title': 'Valid reference',
                'description': f'See lesson {valid_id} (this one exists).',
            },
        ],
    )

    # Act
    result = _scan_all()

    # Assert — exit 1 (findings present); all four task files were parsed
    # successfully (1 + 1 + 2); two PHANTOM findings; per-plan attribution
    # matches the seeded layout. The directory rules (orphan etc.) also
    # run on ``--all`` and may fire on the bare fixture plan-dirs above;
    # this test asserts only on the phantom-lesson surface (lesson-ID
    # sweep), so we filter by reason before counting.
    assert result.returncode == 1, result.stderr
    payload = result.toon()
    assert payload['status'] == 'success'
    assert payload['checked_files'] == 4
    summary = payload.get('summary') or {}
    assert int(summary.get('plans_scanned', 0)) == 3
    # ``--no-emit`` was passed; surface that in the summary so callers
    # know the Q-Gate store was untouched.
    assert str(summary.get('emit_to_qgate')).lower() == 'false'

    phantom_findings = [f for f in _findings(payload) if f.get('reason') == 'phantom_lesson_id']
    assert len(phantom_findings) == 2
    findings = phantom_findings
    by_plan: dict[str, list[dict]] = {}
    for finding in findings:
        by_plan.setdefault(finding['plan_id'], []).append(finding)

    # The clean plan must contribute zero findings — its absence from
    # ``by_plan`` is the assertion.
    assert 'mixed-clean' not in by_plan
    # The two dirty plans contribute one finding each, with the right
    # task file and token attribution.
    assert {f['token'] for f in by_plan['mixed-dirty-one']} == {phantom_one}
    assert {f['task_file'] for f in by_plan['mixed-dirty-one']} == {'TASK-001.json'}
    assert {f['token'] for f in by_plan['mixed-dirty-two']} == {phantom_two}
    assert {f['task_file'] for f in by_plan['mixed-dirty-two']} == {'TASK-001.json'}
    # All findings carry the canonical reason code.
    assert {f['reason'] for f in findings} == {'phantom_lesson_id'}


# =============================================================================
# Directory-rule helpers (orphan / stuck-low-confidence / dangling-worktree)
# =============================================================================


def _findings_by_reason(payload: dict, reason: str) -> list[dict]:
    """Filter the TOON ``findings`` slot to entries matching ``reason``."""
    return [f for f in _findings(payload) if f.get('reason') == reason]


# =============================================================================
# Rule 1 — orphan-plan-directory (cases a, b, c)
# =============================================================================


def test_orphan_rule_case_a_logs_only_plan_dir_flagged_with_rm_rf(plan_context):
    # Arrange — a plan dir that has only ``logs/`` (no status.json, no
    # plan-defining artifacts). plan_context seeds ``plans/{plan_id}/`` for
    # the named plan so we use a SEPARATE plan-id ('orphan-logs-only') and
    # build it under the same fixture_dir; the plan_context-anchored plan is
    # cleared to keep --all from seeing the placeholder.
    shutil.rmtree(plan_context.plan_dir_for(plan_context.plan_id), ignore_errors=True)
    host_dir = plan_context.plan_dir_for('rule1-host')
    seed_lesson_inventory(plan_context.fixture_dir)
    # plan_context creates ``plans/rule1-host/`` as a bare dir; the
    # directory rules see it as an orphan unless we populate it.
    # Materializing a healthy shape keeps Rule 1 focused on the
    # ACTUAL orphan introduced below.
    make_healthy_plan(host_dir)

    orphan_id = 'orphan-logs-only'
    orphan_dir = plan_context.fixture_dir / 'plans' / orphan_id
    # logs/ present, nothing else. No status.json → orphan + rm_rf safe.
    (orphan_dir / 'logs').mkdir(parents=True)

    # Act — directory rules only run on --all.
    result = _scan_all()

    # Assert — exit 1 (findings present), the orphan is flagged with the
    # ``rm_rf`` remediation (logs/ exists but empty).
    assert result.returncode == 1, result.stderr
    payload = result.toon()
    orphan_findings = _findings_by_reason(payload, 'orphan_plan_directory')
    assert len(orphan_findings) == 1
    finding = orphan_findings[0]
    assert finding['plan_id'] == orphan_id
    assert finding['remediation'] == 'rm_rf'
    assert finding['rule'] == 'orphan_plan_directory'


def test_orphan_rule_case_b_status_only_no_artifacts_flagged_with_archive(plan_context):
    # Arrange — status.json is present but NONE of request.md /
    # references.json / solution_outline.md exist. logs/ has content so the
    # remediation upgrades to ``archive_with_reason``.
    host_dir = plan_context.plan_dir_for('rule1-host-b')
    seed_lesson_inventory(plan_context.fixture_dir)
    make_healthy_plan(host_dir)

    orphan_id = 'orphan-status-no-artifacts'
    orphan_dir = plan_context.fixture_dir / 'plans' / orphan_id
    make_status_json(orphan_dir, current_phase='3-outline')
    # Logs with at least one file → archive_with_reason path.
    logs_dir = orphan_dir / 'logs'
    logs_dir.mkdir(parents=True)
    (logs_dir / 'work.log').write_text('previous activity\n', encoding='utf-8')

    # Act
    result = _scan_all()

    # Assert — exit 1, finding has archive_with_reason remediation.
    assert result.returncode == 1, result.stderr
    payload = result.toon()
    orphan_findings = _findings_by_reason(payload, 'orphan_plan_directory')
    matching = [f for f in orphan_findings if f['plan_id'] == orphan_id]
    assert len(matching) == 1
    assert matching[0]['remediation'] == 'archive_with_reason'


def test_orphan_rule_case_c_healthy_plan_dir_yields_no_finding(plan_context):
    # Arrange — a fully-formed plan dir (status.json + request.md) must
    # NOT fire Rule 1. The plan_context-anchored plan IS the healthy plan
    # so we don't have to coordinate with --all listing.
    shutil.rmtree(plan_context.plan_dir_for(plan_context.plan_id), ignore_errors=True)
    plan_dir = plan_context.plan_dir_for('healthy-plan')
    seed_lesson_inventory(plan_context.fixture_dir)
    make_healthy_plan(plan_dir)
    # Make sure the plan has at least one task so the lesson-ID scan
    # has something to do (Rule 1 is independent, but this matches
    # production "healthy" usage).
    make_plan_with_tasks(
        plan_dir,
        [{'title': 'work', 'description': 'no lesson references'}],
    )

    # Act
    result = _scan_all()

    # Assert — no orphan findings of any kind.
    payload = result.toon()
    orphan_findings = _findings_by_reason(payload, 'orphan_plan_directory')
    assert orphan_findings == []


# =============================================================================
# Rule 3 — dangling-worktree (case d)
# =============================================================================


def test_dangling_worktree_rule_case_d_worktree_without_plan_flagged(plan_context):
    # Arrange — a worktree directory whose corresponding plan dir is absent.
    plan_context.plan_dir_for('rule3-host')
    seed_lesson_inventory(plan_context.fixture_dir)
    # Live plan + matching worktree → must NOT be flagged.
    live_id = 'live-plan-with-wt'
    live_dir = plan_context.fixture_dir / 'plans' / live_id
    make_healthy_plan(live_dir)
    make_worktree_dir(plan_context.fixture_dir, live_id)

    # Dangling worktree → must be flagged.
    dangling_id = 'dangling-wt-no-plan'
    make_worktree_dir(plan_context.fixture_dir, dangling_id)

    # Act
    result = _scan_all()

    # Assert
    payload = result.toon()
    dangling_findings = _findings_by_reason(payload, 'dangling_worktree')
    by_plan = {f['plan_id'] for f in dangling_findings}
    assert dangling_id in by_plan
    assert live_id not in by_plan


# =============================================================================
# Rule 2 — stuck-low-confidence-archive (cases e, f, g)
# =============================================================================


def test_stuck_low_confidence_case_e_low_conf_no_reason_flagged(plan_context):
    # Arrange — archived plan stuck at refine with low confidence and NO
    # ``archived_reason`` → Rule 2 fires.
    plan_context.plan_dir_for('rule2-host')
    seed_lesson_inventory(plan_context.fixture_dir)

    stuck_id = 'stuck-low-conf-no-reason'
    make_archived_plan(
        plan_context.fixture_dir,
        stuck_id,
        confidence=47.0,
        archived_reason=None,
    )

    # Act
    result = _scan_all()

    # Assert
    payload = result.toon()
    findings = _findings_by_reason(payload, 'stuck_low_confidence_archive')
    matching = [f for f in findings if f['plan_id'] == stuck_id]
    assert len(matching) == 1
    finding = matching[0]
    # Confidence echoed as float; threshold is the default 95.0.
    assert float(finding['confidence']) == 47.0
    assert float(finding['threshold']) == 95.0


def test_stuck_low_confidence_case_f_low_conf_with_reason_not_flagged(plan_context):
    # Arrange — low confidence BUT operator recorded an archived_reason.
    # Rule 2 must NOT fire (the audit trail explains the abandonment).
    plan_context.plan_dir_for('rule2-host-f')
    seed_lesson_inventory(plan_context.fixture_dir)

    documented_id = 'low-conf-with-reason'
    make_archived_plan(
        plan_context.fixture_dir,
        documented_id,
        confidence=47.0,
        archived_reason='operator abandoned: request too vague',
    )

    # Act
    result = _scan_all()

    # Assert — the documented plan is absent from Rule 2 findings.
    payload = result.toon()
    findings = _findings_by_reason(payload, 'stuck_low_confidence_archive')
    by_plan = {f['plan_id'] for f in findings}
    assert documented_id not in by_plan


def test_stuck_low_confidence_case_g_healthy_archive_not_flagged(plan_context):
    # Arrange — archived plan that completed normally: confidence at or
    # above threshold AND every phase done. Rule 2 must NOT fire.
    plan_context.plan_dir_for('rule2-host-g')
    seed_lesson_inventory(plan_context.fixture_dir)

    complete_id = 'archived-complete'
    all_done = {
        '1-init': 'done',
        '2-refine': 'done',
        '3-outline': 'done',
        '4-plan': 'done',
        '5-execute': 'done',
        '6-finalize': 'done',
    }
    make_archived_plan(
        plan_context.fixture_dir,
        complete_id,
        confidence=98.0,
        phase_statuses=all_done,
        archived_reason=None,
    )

    # Act
    result = _scan_all()

    # Assert — the healthy archive is not flagged.
    payload = result.toon()
    findings = _findings_by_reason(payload, 'stuck_low_confidence_archive')
    by_plan = {f['plan_id'] for f in findings}
    assert complete_id not in by_plan


# =============================================================================
# Single-plan scan does NOT run directory rules
# =============================================================================


def test_single_plan_scan_skips_directory_rules(plan_context):
    # Arrange — orphan plan dir present, but the targeted scan uses
    # ``--plan-id healthy``. Directory rules must NOT fire on the
    # single-plan path (per plan_doctor.cmd_scan's documented behaviour).
    plan_dir = plan_context.plan_dir_for('single-target')
    seed_lesson_inventory(plan_context.fixture_dir)
    make_healthy_plan(plan_dir)

    orphan_id = 'orphan-should-be-ignored'
    orphan_dir = plan_context.fixture_dir / 'plans' / orphan_id
    (orphan_dir / 'logs').mkdir(parents=True)

    # Act — single-plan scan against the healthy plan only.
    result = _scan_plan('single-target')

    # Assert — no directory-rule findings even though the orphan exists.
    payload = result.toon()
    assert _findings_by_reason(payload, 'orphan_plan_directory') == []
    assert _findings_by_reason(payload, 'dangling_worktree') == []
    assert _findings_by_reason(payload, 'stuck_low_confidence_archive') == []
