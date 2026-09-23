#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Derivation guard for the finalize-step ``post_run_review`` membership set.

A post-run-review step looks back over the finished run and reports on it. Three
such steps — ``project:finalize-step-review-retrospective``,
``default:lessons-capture`` and ``default:finalize-step-preference-emitter`` —
were ordered ahead of the merge gate ``default:branch-cleanup``, which hosts the
pre-merge review barrier, the bot re-review wait, triage and loop-back. Each
therefore emitted a confident verdict over evidence the gate had not yet
produced. The role was never a declared fact — it existed only as an effort role
sub-key picking a dispatch model level — so nothing constrained where such a step
could be ordered.

Membership is now a **derived frontmatter fact**: each step doc declares
``post_run_review: true`` in its own frontmatter, and the set is obtained by
reading that fact off every doc ``find_implementors()`` discovers. The governing
discriminator is two predicates, both of which must hold — **P1** the step's
output is a record/assessment about the just-finished run, and **P2** at least
one input it reads is only determined at or after the merge gate. These tests pin
that derivation:

(a) The derived set is **non-empty**. A derivation that silently returned nothing
    would make every other assertion here vacuous, so this is checked first and
    on its own.
(b) It contains every known member — the three that needed moving plus
    ``plan-marshall:plan-retrospective`` (already correctly placed),
    ``default:record-metrics`` and
    ``default:finalize-step-print-phase-breakdown`` (already post-gate,
    declaration-only). The two already-correct members are required too: a guard
    whose required set covered only the movers would re-create the
    population-not-derived defect it exists to remove.
(c) The merge gate is **discoverable**, so the ordering assertion below cannot
    pass merely because no threshold was found.
(d) No member is ordered before the merge gate, whose order is **dynamically
    resolved** from the discovered ``default:branch-cleanup`` record rather than
    the literal ``70`` — a future move of the gate must move the threshold with
    it instead of silently vacating this guard.
(e) No step declares both ``post_run_review: true`` and ``mutates_source: true``.
    The exclusion is a consequence of P2, not an independent axiom: a step that
    reads post-merge-determined evidence runs once the feature branch is already
    gone, so it cannot produce a pushable source edit.
(f) Every member declares a ``mutates_source`` key **explicitly** — present, not
    merely falsy-by-absence. This is the in-module counterpart to the
    ``mutates_source_declaration_missing`` quality-gate-time (plugin-doctor)
    rule; its external
    backstop is
    ``test/pm-plugin-development/plugin-doctor/test_analyze_mutates_source_order.py``
    ``::test_real_marketplace_has_zero_findings``.

Plus the per-member mutation guard: (b) is verified to fail for **each** required
member independently, so a guard that passes on one omission while missing
another cannot read as green.

Checks (a)-(f) all read DECLARATIONS. That is the limit of what a frontmatter
guard can prove, and it is exactly why the runtime arm below exists: a step whose
branch writes tracked source in violation of its own ``mutates_source: false``
declaration is invisible to every assertion above. The second half of this
module therefore drives ``phase-6-finalize/scripts/post_run_source_guard.py`` —
the seam item 5f of ``phase-6-finalize/SKILL.md`` calls once per post-run-band
step return — against **real worktree state** in a real throwaway git repository:

(g) A dirty TRACKED path outside ``.plan/`` is reported as an offender
    (**positive control** — the check can fail, and fails for the right reason).
(g2) A dirty TRACKED path UNDER ``.plan/`` (``marshal.json``, an architecture
    descriptor) is ALSO reported — the exemption is keyed on git trackedness, not
    on the ``.plan/`` prefix, so a tracked plan-config write left dirty after the
    merge gate is as unpushable as any other tracked source.
(h) A dirty UNTRACKED path under ``.plan/`` is NOT an offender (**negative
    control** — matched to (g2): the ordinary plan-state writes every finalize
    step makes (status, logs, findings) are untracked, so reporting them would
    fire the guard on every post-run step).

The controls are matched deliberately: (g)/(g2) alone would pass for a guard that
reports every dirty path, and (h) alone would pass for a guard that exempts the
whole ``.plan/`` prefix — which is the defect. Only the set pins the trackedness
predicate.

**The population is derived from discovery, never hardcoded**, so a step added
later is covered automatically. This module deliberately asserts **no cardinality
literal**: a hardcoded count is precisely the drift shape this plan removes. The
named-member assertions are lower bounds on a derived set, not a pinned
enumeration of it.

The derivation reuses the registry's OWN path — ``find_implementors()`` for the
population and ``extension_discovery._read_frontmatter_fields`` for the fact — so
no second parser exists to drift from the one the registry uses. This mirrors
``test_head_dependence_derivation.py``, the sibling guard for ``head_dependent``.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

import extension_discovery
from conftest import get_script_path, get_skill_dir, load_script_module, run_script
from extension_discovery import find_implementors
from file_ops import get_plan_dir

_guard = load_script_module('plan-marshall', 'phase-6-finalize', 'post_run_source_guard.py')
check_tracked_source = _guard.check_tracked_source

_yield_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_yield_mark_step')
_yield_assert_step = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_assert_step_recorded.py', '_yield_assert_step'
)
_yield_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_yield_lifecycle')

#: The canonical ext-point value whose implementors carry the fact.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The frontmatter key that IS the membership declaration.
_FACT_KEY = 'post_run_review'

#: The reciprocal fact. Mutually exclusive with _FACT_KEY, and required to be
#: declared explicitly on every member.
_MUTATES_SOURCE_KEY = 'mutates_source'

#: The merge gate. Its order is the ordering threshold, read off discovery.
_MERGE_GATE = 'default:branch-cleanup'

#: Members this plan MOVED from ahead of the merge gate to behind it.
_MOVED_MEMBERS = (
    'project:finalize-step-review-retrospective',
    'default:lessons-capture',
    'default:finalize-step-preference-emitter',
)

#: Members that were ALREADY correctly placed and needed only the declaration.
#: Required here for the same reason the movers are: a required set covering only
#: the movers would assert a hand-picked subset rather than the derived role.
_ALREADY_PLACED_MEMBERS = (
    'plan-marshall:plan-retrospective',
    'default:record-metrics',
    'default:finalize-step-print-phase-breakdown',
)

#: The lower bound the derived set must cover. NOT an enumeration of the set —
#: the set is derived and may legitimately be larger.
_REQUIRED_MEMBERS = _MOVED_MEMBERS + _ALREADY_PLACED_MEMBERS


def _declares_post_run_review(doc_path: Path) -> bool:
    """Read the ``post_run_review`` fact off one discovered step doc.

    Reuses ``_read_frontmatter_fields`` — the same extraction primitive
    ``_build_implementor_record`` uses for every other implementor field — rather
    than re-implementing a frontmatter parser. The coerced value is narrowed with
    ``bool()`` exactly the way the registry narrows ``default_on``, so every
    conditional boolean is read identically.
    """
    fields = extension_discovery._read_frontmatter_fields(doc_path, (_FACT_KEY,))
    return bool(fields.get(_FACT_KEY, False))


def _post_run_review_records() -> list[dict]:
    """Derive the post-run-review implementor records from discovery."""
    return [rec for rec in find_implementors(_EXT_POINT) if _declares_post_run_review(Path(rec['path']))]


def _post_run_review_names() -> set[str]:
    """Derive the post-run-review step-id set from discovery."""
    return {rec['name'] for rec in _post_run_review_records()}


def _missing_required(derived: set[str]) -> list[str]:
    """The membership predicate under test: which required members are absent.

    Factored out so the mutation guard can drive the SAME predicate the
    assertions use. A guard that re-implemented the check would prove nothing
    about the check that actually runs.
    """
    return [member for member in _REQUIRED_MEMBERS if member not in derived]


def _merge_gate_order() -> int | None:
    """Resolve the merge gate's order from discovery, never from a literal.

    Returns ``None`` when the gate is not discoverable — the vacuity case test
    (c) pins away, so the ordering assertion can never pass merely because no
    threshold was found.
    """
    for record in find_implementors(_EXT_POINT):
        if record.get('name') == _MERGE_GATE:
            return record.get('order')
    return None


_TRACKED_SOURCE = 'marketplace/bundles/demo/skills/demo/SKILL.md'

_TRACKED_PLAN_STATE = '.plan/local/status.json'

_UNTRACKED_PLAN_STATE = '.plan/local/logs/work.log'


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Run one git command against ``repo`` with a pinned, hermetic identity.

    Commit identity and signing are supplied per-invocation rather than read
    from the ambient environment so the fixture behaves identically on a
    developer machine with a global gitconfig and on a bare CI runner with
    none.
    """
    return subprocess.run(
        [
            'git',
            '-C',
            str(repo),
            '-c',
            'user.name=Test',
            '-c',
            'user.email=test@example.invalid',
            '-c',
            'commit.gpgsign=false',
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


def _write(repo: Path, rel_path: str, content: str) -> Path:
    """Write ``content`` to ``repo/rel_path``, creating parents as needed."""
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    return target


@pytest.fixture
def committed_repo(tmp_path: Path) -> Path:
    """A real git repository with one tracked source file and one tracked ``.plan/`` file.

    Both files are committed, so the worktree starts clean and any dirt a test
    introduces is unambiguously that test's own. The ``.plan/`` file is
    force-added because an ambient global ``core.excludesFile`` could otherwise
    keep it untracked — which would silently turn the tracked ``.plan/`` control
    into an untracked one. The untracked negative control writes its own,
    separately, so it does NOT go through this add.
    """
    repo = tmp_path / 'worktree'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    _write(repo, _TRACKED_SOURCE, '# demo skill\n')
    _write(repo, _TRACKED_PLAN_STATE, '{"phase": "6-finalize"}\n')
    _git(repo, 'add', '-f', _TRACKED_SOURCE, _TRACKED_PLAN_STATE)
    _git(repo, 'commit', '-m', 'chore: seed worktree')
    return repo


def test_derived_set_is_non_empty():
    """(a) The derivation resolves something — every later assertion depends on it."""
    derived = _post_run_review_names()

    assert derived, (
        'The post-run-review derivation returned an EMPTY set. Every membership '
        'assertion in this module would pass vacuously against an empty '
        'derivation, so this is checked first and separately. Either no step doc '
        f'declares {_FACT_KEY}: true, or find_implementors({_EXT_POINT!r}) '
        'discovered no step docs at all.'
    )


@pytest.mark.parametrize('omitted', _REQUIRED_MEMBERS)
def test_each_required_member_is_independently_load_bearing(omitted):
    """Mutation guard: dropping any ONE required member is detected on its own.

    Removing a single member from the derived set must make the membership
    predicate report exactly that member — no more, no fewer. This proves the
    check is sensitive to each member independently, so a derivation that
    silently omitted one while satisfying the others could never read as green.
    A single set-containment assertion cannot make that claim about itself.
    """
    derived = _post_run_review_names()
    assert omitted in derived, (
        f'Mutation guard precondition failed: {omitted} is not in the derived set, '
        'so removing it proves nothing. Fix the derivation first.'
    )

    mutated = derived - {omitted}

    assert _missing_required(mutated) == [omitted], (
        f'The membership predicate did not isolate {omitted} when it alone was '
        'removed from the derived set. A predicate that cannot detect each '
        'member independently can pass while silently missing one — which is '
        'exactly how a member goes unnoticed. '
        f'Reported missing: {_missing_required(mutated)}'
    )


def test_no_member_is_ordered_before_the_merge_gate():
    """(d) Every derived member runs after the merge gate.

    The threshold is READ from the discovered gate record, never hardcoded, so
    moving the gate moves the obligation with it. The comparison is strict:
    a step sharing the gate's order has no guaranteed ordering against it, so it
    cannot be relied on to run after the gate.

    The population is the DERIVED set, so a member added later is covered with no
    edit here.
    """
    merge_gate_order = _merge_gate_order()
    assert merge_gate_order is not None, 'Precondition failed — see test_merge_gate_is_discoverable.'

    offenders = [
        f'{rec["name"]} (order {rec.get("order")})'
        for rec in _post_run_review_records()
        if not isinstance(rec.get('order'), int) or rec['order'] <= merge_gate_order
    ]

    assert not offenders, (
        f'These {_FACT_KEY} steps are ordered at or before the merge gate '
        f'{_MERGE_GATE} (order {merge_gate_order}). A post-run-review step reads '
        'evidence that is only determined at or after that gate, so ordered ahead '
        'of it the step reports a confident verdict about evidence that does not '
        f'exist yet: {offenders}'
    )


def test_every_member_declares_mutates_source_explicitly():
    """(f) Every derived member settles the source-mutation claim explicitly.

    Being ordered after the merge gate, each member falls in the band where an
    ABSENT ``mutates_source`` key is itself a quality-gate-time (plugin-doctor)
    error — a silent
    omission is exactly how a source-mutating step slips past the ordering check
    without ever making the claim. Presence is asserted, not merely falsiness,
    because an absent key is falsy and would pass a truthiness check.

    The population is the DERIVED set, so a member added later is covered with no
    edit here.
    """
    offenders = []
    for record in _post_run_review_records():
        doc_path = Path(record['path'])
        fields = extension_discovery._read_frontmatter_fields(doc_path, (_MUTATES_SOURCE_KEY,))
        if _MUTATES_SOURCE_KEY not in fields:
            offenders.append(f'{record["name"]} ({doc_path})')

    assert not offenders, (
        f'These {_FACT_KEY} steps declare no {_MUTATES_SOURCE_KEY} key at all. '
        'A step ordered at or after the merge gate MUST settle the pushability '
        'claim explicitly — an omission reads as no-claim and evades the '
        f'ordering rule that governs source edits: {offenders}'
    )


def test_dirty_tracked_source_is_reported(committed_repo: Path):
    """(g) POSITIVE CONTROL — a dirty tracked source path is named as an offender.

    This is the branch the ``mutates_source: false`` declaration claims cannot
    happen. A guard that could not fail here would make the negative control
    below vacuous.
    """
    # Arrange — a post-run-band step writes tracked source after the merge gate.
    _write(committed_repo, _TRACKED_SOURCE, '# demo skill\n\nEdited post-merge.\n')

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is False, (
        'A dirty TRACKED source path outside .plan/ went unreported. That edit '
        'was made after the merge gate and has no push path, which is precisely '
        'the condition this guard exists to surface.'
    )
    assert offenders == [_TRACKED_SOURCE]


def test_dirty_tracked_plan_state_is_reported(committed_repo: Path):
    """(D5a POSITIVE CONTROL) A dirty TRACKED ``.plan/`` file IS reported.

    ``.plan/`` holds git-TRACKED files too — ``marshal.json`` and every
    architecture descriptor. A finalize step that leaves one dirty after the
    merge gate has an unpushable tracked edit, exactly like any other tracked
    source. The guard must name it; a bare ``.plan/`` prefix exemption hides it,
    which is the defect this plan closes. Seen RED before the fix (the prefix
    filter drops it), GREEN after (the exemption is trackedness-based).
    """
    # Arrange — an enrich-style write leaves a TRACKED .plan/ file dirty.
    _write(committed_repo, _TRACKED_PLAN_STATE, '{"phase": "6-finalize", "leaked": true}\n')

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is False, (
        'A dirty TRACKED .plan/ file was reported clean. The prefix exemption '
        'hid a tracked unpushable edit — the exact false-clean signal this guard '
        'must not emit.'
    )
    assert offenders == [_TRACKED_PLAN_STATE]


def test_untracked_source_file_is_not_reported(committed_repo: Path):
    """A brand-new untracked file is not an offender — the predicate is TRACKED.

    The predicate is "dirty AND tracked" (a ``.plan/`` path is exempt only when
    untracked). This pins the tracked conjunct for a NON-``.plan/`` path,
    independently of the untracked-``.plan/`` conjunct that (h) pins.
    """
    # Arrange — a new file that was never added to the index.
    _write(committed_repo, 'marketplace/bundles/demo/scratch.md', 'scratch\n')

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is True
    assert offenders == []


def test_renamed_tracked_source_reports_both_sides(committed_repo: Path):
    """A staged rename of tracked source names both the old and the new path.

    Porcelain reports a rename as one record carrying two paths; decoding only
    the first would drop the destination, and decoding only the record would
    misalign every later record in the ``-z`` stream.
    """
    # Arrange — stage a rename so git emits an R record with both paths.
    renamed = 'marketplace/bundles/demo/skills/demo/RENAMED.md'
    _git(committed_repo, 'mv', _TRACKED_SOURCE, renamed)

    # Act
    clean, offenders, error = check_tracked_source(committed_repo)

    # Assert
    assert error is None
    assert clean is False
    assert offenders == sorted([_TRACKED_SOURCE, renamed])


def test_cli_reports_offender_and_still_exits_zero(committed_repo: Path):
    """The non-blocking contract holds at the CLI boundary, not just in-process.

    Item 5f treats ``clean: false`` as a WARNING plus a finding and then
    proceeds. A non-zero exit here would make the advisory band blocking, which
    contradicts the band's documented placement after the merge gate.
    """
    # Arrange — the offending condition.
    _write(committed_repo, _TRACKED_SOURCE, '# demo skill\n\nEdited post-merge.\n')
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'post_run_source_guard.py')

    # Act
    result = run_script(
        script,
        'check',
        '--step-id',
        'default:lessons-capture',
        '--project-dir',
        str(committed_repo),
    )

    # Assert
    assert result.returncode == 0, (
        'The guard exited non-zero on a detected offender. The post-run band is '
        'advisory and never blocking, so the verdict rides the payload and the '
        f'exit code stays 0. stderr: {result.stderr}'
    )
    payload = result.toon()
    assert payload['status'] == 'success'
    assert payload['step_id'] == 'default:lessons-capture'
    assert payload['clean'] is False
    assert _TRACKED_SOURCE in str(payload['offending_paths'])


# =============================================================================
# Yield channel (D3 hardening)
#
# Every phase-6-finalize yield names itself from the CLOSED set — the composed
# manifest's frozen phase_6.steps — carries progress in --display-detail and
# control in --outcome/--loop-back-target, and leaves a reportable finding
# when the yield itself is absent. The helpers below build isolated plans
# (plan_context redirects PLAN_BASE_DIR into tmp) and write a minimal
# execution.toon so the roster derivation runs against a real manifest read.
# =============================================================================


def _yield_make_plan(plan_id: str) -> None:
    _yield_lifecycle.cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Yield Channel Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _yield_manifest_path(plan_id: str) -> Path:
    return get_plan_dir(plan_id) / 'execution.toon'


def _write_roster_manifest(plan_id: str, steps: list[str]) -> None:
    lines = ['manifest_version: 1', f'plan_id: {plan_id}', 'phase_6:', f'  steps[{len(steps)}]:']
    lines.extend(f'    - {step}' for step in steps)
    _yield_manifest_path(plan_id).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _mark_args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    display_detail: str | None = None,
    loop_back_target: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=False,
        display_detail=display_detail,
        head_at_completion=None,
        loop_back_target=loop_back_target,
        fact=None,
    )


def _assert_args(plan_id: str, phase: str, step: str) -> Namespace:
    return Namespace(plan_id=plan_id, phase=phase, step=step, require_terminal=True)


class TestClosedYieldNameSet:
    """A 6-finalize yield must name a member of the composed manifest roster."""

    def test_unknown_yield_name_is_refused_before_any_write(self, plan_context):
        plan_id = 'yield-unknown-name'
        _yield_make_plan(plan_id)
        _write_roster_manifest(plan_id, ['push', 'ci-verify'])

        result = _yield_mark_step.cmd_mark_step_done(_mark_args(plan_id, '6-finalize', 'not-a-real-step', 'done'))

        assert result['status'] == 'error'
        assert result['error'] == 'unknown_yield_name'
        assert result['step'] == 'not-a-real-step'

        # Nothing was written: the read side still reports the yield absent.
        check = _yield_assert_step.cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'not-a-real-step'))
        assert check['recorded'] is False

    def test_roster_member_records_normally(self, plan_context):
        plan_id = 'yield-known-name'
        _yield_make_plan(plan_id)
        _write_roster_manifest(plan_id, ['push', 'ci-verify'])

        result = _yield_mark_step.cmd_mark_step_done(
            _mark_args(plan_id, '6-finalize', 'push', 'skipped', display_detail='push deferred to the merge queue')
        )

        assert result['status'] == 'success'
        assert result['changed'] is True
        assert result['outcome'] == 'skipped'

    def test_phase_without_roster_is_recorded_without_membership_check(self, plan_context):
        plan_id = 'yield-unrostered-phase'
        _yield_make_plan(plan_id)

        result = _yield_mark_step.cmd_mark_step_done(
            _mark_args(plan_id, '5-execute', 'any-free-form-task-yield', 'done', display_detail='tasks settled')
        )

        assert result['status'] == 'success'
        assert result.get('warning') is None


class TestProgressSeparatedFromControl:
    """A bare control token as --display-detail is refused on every phase."""

    @pytest.mark.parametrize('token', ['done', 'skipped', 'loop_back', 'failed', '  FAILED  '])
    def test_bare_control_token_is_refused(self, plan_context, token):
        plan_id = 'yield-control-token'
        _yield_make_plan(plan_id)

        result = _yield_mark_step.cmd_mark_step_done(
            _mark_args(plan_id, '5-execute', 'some-step', 'done', display_detail=token)
        )

        assert result['status'] == 'error'
        assert result['error'] == 'display_detail_is_control_token'

    def test_real_narrative_records_normally(self, plan_context):
        plan_id = 'yield-real-narrative'
        _yield_make_plan(plan_id)

        result = _yield_mark_step.cmd_mark_step_done(
            _mark_args(plan_id, '5-execute', 'some-step', 'done', display_detail='Done: all green after rebase')
        )

        assert result['status'] == 'success'
        assert result['outcome'] == 'done'


class TestMissingYieldFinding:
    """An absent yield surfaces as a reportable finding, never as silence."""

    def test_missing_record_carries_finding_fields(self, plan_context):
        plan_id = 'yield-missing-finding'
        _yield_make_plan(plan_id)

        result = _yield_assert_step.cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'ci-verify'))

        assert result['status'] == 'error'
        assert result['error'] == 'step_record_missing'
        assert result['finding_type'] == 'missing-yield'
        assert result['finding_severity'] == 'error'
        assert 'ci-verify' in result['finding_title']
        assert '6-finalize' in result['finding_detail']


_AWAIT_DOC = get_skill_dir('plan-marshall', 'plan-marshall') / 'workflow' / 'await-long-running.md'


def test_next_step_binding_names_both_completion_toons():
    """The tool-output binding section pins which TOONs route the next step.

    The section must name both wait-class completion shapes — the ci-wait
    return and the ci barrier decision — so deleting or gutting the binding
    fails loudly instead of silently unbinding the yield path.
    """
    text = _AWAIT_DOC.read_text(encoding='utf-8')
    _heading, _, after = text.partition('### Next step arrives as tool output')
    assert after, 'the tool-output binding section is absent from await-long-running.md'
    section, _, _rest = after.partition('\n### ')
    assert 'final_status' in section
    assert 'barrier_status' in section
