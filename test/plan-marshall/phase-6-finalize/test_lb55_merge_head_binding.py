#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The merge barrier refuses a candidate its gates never saw.

``pre_merge_gate merge`` must not dispatch the merge verb on a clean findings
store alone. Every head-dependent finalize gate stamps ``head_at_completion``,
and a merge that does not compare those stamps with the tree being merged can
ship a head its gates had never seen.
"""

from __future__ import annotations

import pytest

from conftest import PROJECT_ROOT, load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'pre_merge_gate.py', register=False)

HEAD_GATED = 'a' * 40
HEAD_MERGED = 'b' * 40


@pytest.fixture(autouse=True)
def _merge_mutex_held(monkeypatch: pytest.MonkeyPatch) -> None:
    """Autouse: answer the merge-mutex proof "held by this plan".

    The mutex proof is another gate's subject
    (``test_pre_merge_gate_merge_lock_proof.py``); leaving the production reader in
    place here would make every head-binding case depend on whether the machine
    running the suite happens to hold the real ``.plan/local/merge.lock``.
    """
    monkeypatch.setattr(
        gate,
        '_merge_lock_holder_read',
        lambda: {'state': 'held', 'holder': 'lb55-plan', 'lock_path': '<test>'},
    )


def _status(head_by_step: dict[str, str | None]) -> dict:
    """A status payload whose 6-finalize step records carry ``head_at_completion``."""
    steps = {
        step: ({'outcome': 'done', 'head_at_completion': head} if head else {'outcome': 'done'})
        for step, head in head_by_step.items()
    }
    return {'metadata': {'phase_steps': {'6-finalize': steps}}}


def _participating():
    """The participation seam payload a head-binding case defaults to."""
    return {
        'status': 'success',
        'participation_complete': True,
        'roster_read': True,
        'required_bots': ['coderabbit'],
        'unproven_bots': [],
        'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated'}],
    }


def _merge(status, head, **kwargs):
    """Run the gate with stubbed findings, participation and merge seams.

    Participation is stubbed COMPLETE here because this module's subject is the head
    binding: the production participation reader spawns its own provider and predicate
    subprocesses, and the participation behaviour has its own cases in
    ``test_pre_merge_gate.py``.

    The merge-mutex proof is stubbed "held by this plan" for the same reason — it is
    another gate's subject (``test_pre_merge_gate_merge_lock_proof.py``), and leaving
    the production reader in place would make every case here depend on whether the
    machine running the suite holds the real ``.plan/local/merge.lock``.

    Head-dependence discovery and the verdict-currency classifier are stubbed too, for
    the same reason: the production forms read the repository's own finalize-step docs
    and spawn a ``verdict_currency`` executor call. A case that exercises one of those
    paths overrides the corresponding seam, and the production classifier has its own
    case in this module. Passing ``status_reader=None`` selects the production read.
    """
    flags = {
        'participation_check': lambda _pid, _pr, _project_dir: _participating(),
        'head_dependence_reader': lambda _step: (True, None),
        'classifier': lambda _step, _project_dir, _recorded: {
            'status': 'success',
            'verdict': 'invalidated',
            'reason': 'stub',
        },
        'status_reader': lambda _pid: status,
        'head_reader': lambda _dir: head,
    }
    flags.update(kwargs)
    return gate.merge(
        'lb55-plan',
        route='safe-merge',
        pr_number=7,
        project_dir='/tmp/does-not-matter',
        strategy='squash',
        findings_check=lambda _pid: {'status': 'success', 'blocking_count': 0},
        merge_runner=lambda _args: {'status': 'success', 'merged': True},
        **flags,
    )


def _merge_pre_seam(status, head, **kwargs):
    """Run the gate with ONLY the seams the pre-change module already accepted.

    The two cases marked red-before-the-change drive the production declaration
    reader and the production waiver row through these seams, so their failure
    against the unfixed module is the defect (a refused merge) rather than a
    missing keyword. They therefore must not pass the declaration seam. A case
    that needs the production declaration reader but not the production classifier
    passes it through ``kwargs``.
    """
    flags = {
        'status_reader': lambda _pid: status,
        'head_reader': lambda _dir: head,
        'participation_check': lambda _pid, _pr, _project_dir: _participating(),
    }
    flags.update(kwargs)
    return gate.merge(
        'lb55-plan',
        route='safe-merge',
        pr_number=7,
        project_dir='/tmp/does-not-matter',
        strategy='squash',
        findings_check=lambda _pid: {'status': 'success', 'blocking_count': 0},
        merge_runner=lambda _args: {'status': 'success', 'merged': True},
        **flags,
    )


def test_a_merge_candidate_newer_than_the_functional_review_head_refuses():
    """The unbound case: the gates stamped one head, the merge ships another."""
    status = _status(
        {
            'functional-review': HEAD_GATED,
            'pre-push-quality-gate': HEAD_GATED,
        }
    )

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'error'
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert result['dispatched'] is False, 'nothing may be dispatched on a refused head'
    named = {item['step'] for item in result['steps']}
    assert named == {'functional-review', 'pre-push-quality-gate'}
    for item in result['steps']:
        assert item['recorded_head'] == HEAD_GATED
        assert item['head'] == HEAD_MERGED
    assert 'loop-back close --waive-refire' in result['message'], (
        'the refusal must name the verb that records the waiver, not only the rule'
    )


def test_a_merge_with_no_stale_record_never_scans_the_step_population(monkeypatch):
    """A merge whose records all sit at the candidate pays for no declaration scan.

    The population scan walks every bundle and skill root, so running it before any
    record is known stale charges every ordinary merge for a check that answers
    nothing.
    """

    def _unexpected_scan():
        raise AssertionError('the head-dependence population was scanned for a merge that needed none')

    monkeypatch.setattr(gate, '_head_dependence_probe', _unexpected_scan)
    status = _status({'functional-review': HEAD_MERGED, 'pre-push-quality-gate': HEAD_MERGED})

    result = _merge(status, HEAD_MERGED, head_dependence_reader=None)

    assert result['status'] == 'success'
    assert result['dispatched'] is True


def _declared_merge_facts() -> list[str]:
    """Every fact key ``default:branch-cleanup`` declares, plus the required set."""
    return [
        'action=rebased',
        'upstream_commit_count=3',
        'merge_mechanism=pr_safe_merge',
        'merge_state=merged',
        'work_performed=true',
        'cleanup_owed=false',
        'head_binding_waived=none',
        'head_binding_unconsulted=none',
        'head_binding_fallback=none',
        'head_binding_status_read_fault=none',
    ]


def test_a_misspelled_fact_key_is_refused():
    """A key the step does not declare is a typo, and nothing is written.

    ``mark-step-done`` does not check keys against the step's ``records_facts``, so
    without this guard a misspelled key reaches the record and no reader of the
    step ever sees it.
    """
    written: list[list[str]] = []
    facts = [*_declared_merge_facts()[:-1], 'merge_stat=merged']

    result = gate.record_merge(
        'lb55-plan',
        facts=facts,
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert result['status'] == 'error'
    assert result['error'] == 'facts_malformed'
    assert 'merge_stat' in result['message']
    assert written == [], 'a refused fact set writes nothing'


def test_every_declared_fact_key_is_accepted():
    """CONTROL: every key the step declares passes the same validation."""
    written: list[list[str]] = []
    declared, reason = gate._declared_fact_keys()
    assert declared is not None, reason
    facts = _declared_merge_facts()
    assert {fact.split('=', 1)[0] for fact in facts} == declared

    result = gate.record_merge(
        'lb55-plan',
        facts=facts,
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert result['status'] == 'success', result
    assert written, 'the accepted fact set reaches the writer'
    for fact in facts:
        assert fact in written[0]


def test_an_unreadable_fact_declaration_refuses_the_record(monkeypatch):
    """A declaration nobody could read refuses the write, naming the fault.

    Failing open here would write facts no reader of the step can check, which is
    the same silent pass the key check exists to remove.
    """
    monkeypatch.setattr(gate, '_declared_fact_keys', lambda: (None, 'the population raised'))
    written: list[list[str]] = []

    result = gate.record_merge(
        'lb55-plan',
        facts=_declared_merge_facts(),
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert result['status'] == 'error'
    assert result['error'] == 'facts_declaration_unreadable'
    assert 'the population raised' in result['message']
    assert written == []


def test_a_rebase_count_without_an_action_is_refused():
    """A count names a rebase; a record with no action performed none.

    The merge-queue route never rebases, so an unpaired count would record one it
    could not have observed.
    """
    facts = [fact for fact in _declared_merge_facts() if not fact.startswith('action=')]
    facts = ['merge_mechanism=merge_queue' if fact.startswith('merge_mechanism=') else fact for fact in facts]
    written: list[list[str]] = []

    result = gate.record_merge(
        'lb55-plan',
        facts=facts,
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert result['status'] == 'error'
    assert result['error'] == 'upstream_count_without_action'
    assert written == []


def test_a_fault_text_with_a_quote_and_a_newline_is_recorded_intact():
    """The fault text is data, not prose: a quote and a newline survive verbatim.

    It carries the reader's own exception text, which can hold both, and any
    re-quoting or re-encoding on the way to the record would silently change what
    the fault said.
    """
    fault = 'the plan-status read raised (it\'s "broken")\nsecond line'
    written: list[list[str]] = []

    result = gate.record_merge(
        'lb55-plan',
        facts=[*_declared_merge_facts()[:-1], f'head_binding_status_read_fault={fault}'],
        mark_done_runner=lambda argv: written.append(list(argv)) or {'status': 'success'},
    )

    assert result['status'] == 'success', result
    assert f'head_binding_status_read_fault={fault}' in written[0]


def test_the_same_records_at_the_candidate_head_dispatch_the_merge():
    """⛔ MATCHED CONTROL — same records, candidate equal to them, the merge dispatches."""
    status = _status({'functional-review': HEAD_MERGED, 'pre-push-quality-gate': HEAD_MERGED})

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'success'
    assert result['dispatched'] is True
    assert result['findings_gate'] == 'clean'


def test_a_record_carrying_no_head_is_not_consulted():
    """A step that stamped no SHA was never anchored to a tree; the re-entry check owns it."""
    status = _status({'functional-review': None, 'code-review': None})

    result = _merge(status, HEAD_MERGED)

    assert result['dispatched'] is True, f'an unstamped record must not be read as a mismatch: {result!r}'


@pytest.mark.parametrize('status', [None, {}, {'metadata': {}}], ids=['unreadable', 'empty', 'no-steps'])
def test_an_unreadable_or_empty_status_passes(status):
    """Nothing recorded means nothing to compare — never a fabricated mismatch."""
    result = _merge(status, HEAD_MERGED)

    assert result['dispatched'] is True


def test_an_unreadable_local_head_passes():
    """A candidate that cannot be read is not a candidate that differs."""
    status = _status({'functional-review': HEAD_GATED})

    result = _merge(status, None)

    assert result['dispatched'] is True


# ---------------------------------------------------------------------------
# The merge gate honours the operator's re-fire waiver
# ---------------------------------------------------------------------------
#
# The dispatcher's re-entry table SKIPs a head-dependent step whose
# ``refire_waiver.head`` equals the live HEAD. The merge gate must read the same
# waiver the same way: a step the operator explicitly waived is not refused again
# at merge, and the waiver is void at any other head. Every case below is paired —
# a waiver honoured at its own head, and the same waiver void at any other head —
# so neither direction can pass by refusing (or admitting) everything.

HEAD_C = 'c' * 40


def _status_with_waivers(head_by_step: dict[str, str | None], waivers: dict[str, object]) -> dict:
    """A status payload whose records carry the given ``refire_waiver`` values."""
    status = _status(head_by_step)
    steps = status['metadata']['phase_steps']['6-finalize']
    for step, waiver in waivers.items():
        steps[step]['refire_waiver'] = waiver
    return status


def test_a_waiver_at_the_candidate_head_is_honoured_and_named_in_the_payload():
    """(a) Record at A, waiver at B == candidate: the merge dispatches."""
    status = _status_with_waivers(
        {'functional-review': HEAD_GATED},
        {'functional-review': {'head': HEAD_MERGED, 'basis': 'operator accepted the stale review'}},
    )

    result = _merge_pre_seam(status, HEAD_MERGED)

    assert result['status'] == 'success', result
    assert result['dispatched'] is True
    assert result['waived_steps'] == [
        {
            'step': 'functional-review',
            'waiver_head': HEAD_MERGED,
            'basis': 'operator accepted the stale review',
        }
    ]


def test_a_waiver_at_any_other_head_is_void_and_the_step_is_refused():
    """(b) MATCHED CONTROL: the same waiver at C != candidate is void."""
    status = _status_with_waivers(
        {'functional-review': HEAD_GATED},
        {'functional-review': {'head': HEAD_C, 'basis': 'waived for another tree'}},
    )

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'error'
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert {item['step'] for item in result['steps']} == {'functional-review'}
    assert 'waived_steps' not in result


@pytest.mark.parametrize(
    'waiver',
    [
        {'basis': 'no head at all'},
        {'head': HEAD_MERGED[:7], 'basis': 'abbreviated'},
        'not-a-dict',
        {'head': None},
    ],
    ids=['no-head', 'abbreviated', 'not-a-dict', 'head-is-null'],
)
def test_a_malformed_waiver_is_void_and_the_step_is_refused(waiver):
    """(c) A malformed waiver is never a get-out-of-jail key."""
    status = _status_with_waivers({'functional-review': HEAD_GATED}, {'functional-review': waiver})

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'error'
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert {item['step'] for item in result['steps']} == {'functional-review'}


def test_an_abbreviated_waiver_head_is_void_at_the_candidates_own_prefix():
    """The waiver head is FULL-SHA equality, never a prefix of the candidate.

    The abbreviated value is the candidate's own first seven characters, which is
    what a prefix-tolerant reader would honour. Asserting the predicate directly —
    as well as the refused merge above — is what makes a lost full-SHA check turn
    red instead of passing as "no waiver matched anyway".
    """
    assert gate._is_full_sha(HEAD_MERGED[:7]) is False
    record = {
        'outcome': 'done',
        'head_at_completion': HEAD_GATED,
        'refire_waiver': {'head': HEAD_MERGED[:7], 'basis': 'abbreviated'},
    }

    assert gate._valid_waiver_head(record) is None


def test_a_waiver_on_one_step_does_not_admit_a_second_stale_step():
    """(d) A waiver is per step, never a blanket admission for the record set."""
    status = _status_with_waivers(
        {'functional-review': HEAD_GATED, 'pre-push-quality-gate': HEAD_GATED},
        {'functional-review': {'head': HEAD_MERGED, 'basis': 'waived'}},
    )

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'error'
    assert {item['step'] for item in result['steps']} == {'pre-push-quality-gate'}


# ---------------------------------------------------------------------------
# Head-dependence comes from the declared fact
# ---------------------------------------------------------------------------
#
# The dispatcher decides head-dependence from the step doc's own
# ``head_dependent: true``, and the gate must decide it from the same fact: a
# stamp alone does not make a step head-dependent, so an undeclared step that
# carries one is listed as never consulted rather than refused with a remedy the
# dispatcher would never act on.


def test_an_undeclared_step_with_a_stale_stamp_is_listed_not_refused():
    """(a) An undeclared stamp is evidence, never an offence.

    Drives the PRODUCTION declaration reader: ``finalize-step-sync-baseline``
    genuinely declares no ``head_dependent`` fact, so against the unfixed module
    this merge is refused for the defect itself, not for a missing seam.
    """
    status = _status({'finalize-step-sync-baseline': HEAD_GATED})

    result = _merge_pre_seam(status, HEAD_MERGED)

    assert result['status'] == 'success', result
    assert result['dispatched'] is True
    assert result['unconsulted_stamps'] == [
        {'step': 'finalize-step-sync-baseline', 'recorded_head': HEAD_GATED},
    ]


def test_a_declared_step_with_the_same_stale_stamp_refuses():
    """(b) MATCHED CONTROL: the declared fact makes the same stamp an offence."""
    status = _status({'finalize-step-sync-baseline': HEAD_GATED})

    result = _merge(status, HEAD_MERGED, head_dependence_reader=lambda _step: (True, None))

    assert result['status'] == 'error'
    assert {item['step'] for item in result['steps']} == {'finalize-step-sync-baseline'}


def test_an_underivable_declaration_falls_back_to_field_presence_and_says_so():
    """(c) Discovery failure is fail-closed, and the payload names the fallback."""
    status = _status({'functional-review': HEAD_GATED})

    result = _merge(
        status,
        HEAD_MERGED,
        head_dependence_reader=lambda _step: (False, 'find_implementors raised'),
    )

    assert result['status'] == 'error'
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert result['head_dependence_fallback'] == [
        {'step': 'functional-review', 'reason': 'find_implementors raised'},
    ]


@pytest.mark.parametrize(
    ('verdict', 'dispatched'),
    [('preserved', True), ('invalidated', False)],
)
def test_the_classifier_decides_a_stale_declared_step(verdict, dispatched):
    """(d) The classifier's own verdict is what admits or refuses the record."""
    status = _status({'functional-review': HEAD_GATED})

    result = _merge(
        status,
        HEAD_MERGED,
        classifier=lambda _step, _project_dir, _recorded: {'status': 'success', 'verdict': verdict},
    )

    assert result['dispatched'] is dispatched
    if dispatched:
        assert result['status'] == 'success'
    else:
        assert result['error'] == gate.MERGE_HEAD_NOT_GATED


def test_the_production_classifier_is_reached_through_the_executor_seam(monkeypatch):
    """(d) The default classifier asks ``verdict_currency classify`` like every other verb."""
    calls: list[tuple[str, list[str]]] = []

    def _fake_run_verb(notation, argv, **_kwargs):
        calls.append((notation, list(argv)))
        return {'status': 'success', 'verdict': 'preserved', 'step': 'functional-review'}

    monkeypatch.setattr(gate, '_run_verb', _fake_run_verb)
    status = _status({'functional-review': HEAD_GATED})

    result = gate.merge(
        'lb55-plan',
        route='safe-merge',
        pr_number=7,
        project_dir='/abs/worktree',
        strategy='squash',
        findings_check=lambda _pid: {'status': 'success', 'blocking_count': 0},
        merge_runner=lambda _args: {'status': 'success', 'merged': True},
        status_reader=lambda _pid: status,
        head_reader=lambda _dir: HEAD_MERGED,
        participation_check=lambda _pid, _pr, _project_dir: {
            'status': 'success',
            'participation_complete': True,
            'roster_read': True,
            'required_bots': ['coderabbit'],
            'unproven_bots': [],
            'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated'}],
        },
        head_dependence_reader=lambda _step: (True, None),
    )

    assert result['dispatched'] is True
    assert calls == [
        (
            'plan-marshall:phase-6-finalize:verdict_currency',
            [
                'classify',
                '--step',
                'functional-review',
                '--worktree-path',
                '/abs/worktree',
                '--head-at-completion',
                HEAD_GATED,
                '--live-head',
                HEAD_MERGED,
            ],
        )
    ]


def test_the_currency_classifier_decides_and_the_entry_point_does_not():
    """The decision comes from the classifier, not from being inside ``pre_merge_gate merge``.

    A weaker test that only asserted the merge entry point exists would pass with the
    classifier bypassed. Here the SAME entry point dispatches or refuses purely on the
    classifier's verdict.
    """
    status = _status({'functional-review': HEAD_GATED})
    preserved = _merge(
        status,
        HEAD_MERGED,
        classifier=lambda _step, _project_dir, _recorded: {'status': 'success', 'verdict': 'preserved'},
    )
    invalidated = _merge(
        status,
        HEAD_MERGED,
        classifier=lambda _step, _project_dir, _recorded: {'status': 'success', 'verdict': 'invalidated'},
    )

    assert preserved['dispatched'] is True
    assert invalidated['error'] == gate.MERGE_HEAD_NOT_GATED


@pytest.mark.parametrize(
    ('step', 'expected'),
    [('functional-review', True), ('finalize-step-sync-baseline', False)],
)
def test_the_production_discovery_path_resolves_the_declared_fact(step, expected):
    """Anti-vacuity: the gate's default reader really reaches the step docs.

    Every other D2 case stubs this seam. If the import path, the discovery call or
    the frontmatter read stopped working, the gate would fall back to field presence
    forever and those cases would stay green — so this one asserts the real reader
    against the repository's own declared and undeclared steps.
    """
    assert gate._head_dependence(step) == (expected, None)


def test_the_undeclared_control_step_is_discovered_and_declares_no_fact():
    """Anti-vacuity for D2(a): ``(False, None)`` must mean "undeclared", not "unknown step".

    ``_derive_head_dependence`` answers ``(False, None)`` both for a step that
    declares no ``head_dependent`` fact and for one absent from the discovered
    implementor population. Without this assertion the (a) case would stay green if
    ``finalize-step-sync-baseline`` silently fell out of discovery — and the gate
    would stop enforcing a real head-dependent step with no failure to show it.
    """
    from extension_discovery import find_implementors

    ext_point = 'plan-marshall:extension-api/standards/ext-point-finalize-step'
    discovered = {str(record.get('name', '')).rsplit(':', 1)[-1] for record in find_implementors(ext_point)}

    assert 'finalize-step-sync-baseline' in discovered


# ---------------------------------------------------------------------------
# The status transport must preserve namespaced step keys
# ---------------------------------------------------------------------------
#
# ``mark-step-done`` stores a project-tier step under its ``project:`` id
# (``canonicalize_step_key`` preserves that prefix). The executor's TOON
# rendering then splits a ``project:step:`` line at its FIRST colon, so a gate
# that parsed that text would receive ``{'project': 'step: ...'}`` and skip the
# record — merging without checking a declared head-dependent step. The read is
# therefore the JSON resolver's, not the TOON rendering's.


def test_a_project_namespaced_step_record_survives_the_status_read(monkeypatch):
    """The status read keeps a ``project:`` key as a dict record, not a scalar."""
    from types import SimpleNamespace

    import _status_core

    status = _status(
        {
            'functional-review': HEAD_GATED,
            'project:finalize-step-plugin-doctor': HEAD_GATED,
        }
    )
    monkeypatch.setattr(
        _status_core,
        'resolve_plan_status',
        lambda _plan_id, any_checkout=False: SimpleNamespace(status=status),
    )

    read = gate._read_plan_status('lb55-plan')

    assert read.reason is None, read.reason
    records = read.payload['metadata']['phase_steps']['6-finalize']
    assert isinstance(records['project:finalize-step-plugin-doctor'], dict)


def test_a_namespaced_declared_step_is_judged_not_silently_skipped(monkeypatch):
    """End-to-end: a stale project-tier declared record refuses the merge."""
    from types import SimpleNamespace

    import _status_core

    status = _status({'project:finalize-step-plugin-doctor': HEAD_GATED})
    monkeypatch.setattr(
        _status_core,
        'resolve_plan_status',
        lambda _plan_id, any_checkout=False: SimpleNamespace(status=status),
    )

    result = _merge(
        status,
        HEAD_MERGED,
        status_reader=None,
        head_dependence_reader=lambda _step: (True, None),
    )

    assert result['status'] == 'error', result
    assert {item['step'] for item in result['steps']} == {'project:finalize-step-plugin-doctor'}


# ---------------------------------------------------------------------------
# "declares no head-dependence" and "could not be found" are different answers
# ---------------------------------------------------------------------------
#
# The declaration reader resolves a step that is simply ABSENT from the
# discovered finalize-step population to "not head-dependent", because
# ``mark-step-done`` records steps for every phase and a phase-5 step
# legitimately matches no finalize-step implementor. That answer is right for
# ``mark-step-done`` and wrong for the merge gate: a stale record for a
# head-dependent step the gate's own discovery does not return would be listed
# as "never consulted" and ADMITTED. The gate therefore asks the same discovery
# a distinguishing question, and an absent step takes the fail-closed
# field-presence fallback exactly as an underivable declaration does.


def _population_without(name: str, monkeypatch):
    """Stub the discovery so it returns the real population minus ``name``."""
    import extension_discovery

    real = extension_discovery.find_implementors

    def _filtered(ext_point: str):
        return [record for record in real(ext_point) if str(record.get('name', '')) != name]

    monkeypatch.setattr(extension_discovery, 'find_implementors', _filtered)


_STALE_CLASSIFIER_RESULT = {'status': 'success', 'verdict': 'invalidated', 'reason': 'stub'}


def _stale_classifier(_step, _project_dir, _recorded):
    """A classifier that never preserves the stale record (the refusal default)."""
    return dict(_STALE_CLASSIFIER_RESULT)


def test_a_stale_record_for_a_step_the_discovery_does_not_return_is_refused(monkeypatch):
    """A step absent from the discovered population is refused, never "undeclared"."""
    _population_without('default:functional-review', monkeypatch)
    status = _status({'functional-review': HEAD_GATED})

    result = _merge_pre_seam(status, HEAD_MERGED, classifier=_stale_classifier)

    assert result['status'] == 'error', result
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert {item['step'] for item in result['steps']} == {'functional-review'}
    assert result['head_dependence_fallback'] == [
        {'step': 'functional-review', 'reason': gate.POPULATION_ABSENT_REASON},
    ]
    assert 'unconsulted_stamps' not in result


def test_a_discovered_undeclared_step_is_still_listed_and_admitted():
    """MATCHED CONTROL: the distinguishing answer must not narrow the admitted set.

    ``finalize-step-sync-baseline`` IS discovered and declares no
    ``head_dependent`` fact, so its stamp stays evidence rather than an offence.
    Without this control a reader that simply refused every stale stamp would
    pass the case above.
    """
    status = _status({'finalize-step-sync-baseline': HEAD_GATED})

    result = _merge_pre_seam(status, HEAD_MERGED)

    assert result['status'] == 'success', result
    assert result['dispatched'] is True
    assert result['unconsulted_stamps'] == [
        {'step': 'finalize-step-sync-baseline', 'recorded_head': HEAD_GATED},
    ]


def test_a_declared_document_that_cannot_be_read_is_refused_not_listed(monkeypatch):
    """An unreadable declared document is "not derived", never "undeclared"."""
    import extension_discovery

    real = extension_discovery.find_implementors

    def _broken_path(ext_point: str):
        records = []
        for record in real(ext_point):
            if str(record.get('name', '')) == 'default:functional-review':
                record = {**record, 'path': '/nonexistent/functional-review.md'}
            records.append(record)
        return records

    monkeypatch.setattr(extension_discovery, 'find_implementors', _broken_path)
    status = _status({'functional-review': HEAD_GATED})

    result = _merge_pre_seam(status, HEAD_MERGED, classifier=_stale_classifier)

    assert result['status'] == 'error', result
    assert {item['step'] for item in result['steps']} == {'functional-review'}
    fallback = result['head_dependence_fallback']
    assert [item['step'] for item in fallback] == ['functional-review']
    assert 'could not be read' in fallback[0]['reason']
    assert 'unconsulted_stamps' not in result


@pytest.mark.parametrize('step', ['automatic-review', 'project:finalize-step-plugin-doctor'])
def test_a_bundle_tier_and_a_project_tier_step_resolve_through_the_production_reader(step, monkeypatch):
    """Both tiers reach their own document through the production reader.

    ``automatic-review`` is discovered from a bundle's ``skills/*/SKILL.md`` and
    ``project:finalize-step-plugin-doctor`` from the checkout's project-local
    skill root. Stubbing either tier would leave the discovery surface that
    actually matters for a real plan unexercised.

    The project-local scan resolves its root from the PROCESS cwd (the ADR-002
    cwd rule), so the cwd is pinned to the checkout that holds the document:
    otherwise the case would depend on where pytest happened to be launched.
    """
    monkeypatch.chdir(PROJECT_ROOT)

    assert gate._head_dependence(step) == (True, None)


def test_the_gate_discovers_the_population_once_per_merge(monkeypatch):
    """Three stale declared steps cost ONE discovery, not one each.

    The discovery walks every bundle, cache root and project-local skill root,
    and it runs while the cross-plan merge mutex is held: re-deriving the
    population per stale step would multiply that cost by the record count.
    """
    calls: list[int] = []
    real = gate._finalize_step_population

    def _counted():
        calls.append(1)
        return real()

    monkeypatch.setattr(gate, '_finalize_step_population', _counted)
    status = _status(
        {
            'functional-review': HEAD_GATED,
            'pre-push-quality-gate': HEAD_GATED,
            'automatic-review': HEAD_GATED,
        }
    )

    result = _merge_pre_seam(status, HEAD_MERGED, classifier=_stale_classifier)

    assert result['status'] == 'error', result
    assert {item['step'] for item in result['steps']} == {
        'functional-review',
        'pre-push-quality-gate',
        'automatic-review',
    }
    assert len(calls) == 1, f'the discovery ran {len(calls)} times for one merge'


def test_the_classifier_runs_only_for_the_records_the_dispatcher_would_retry(monkeypatch):
    """One classifier call per stale DECLARED ``done`` record, and none elsewhere.

    The classifier is the expensive half of the loop (an executor subprocess), and
    it runs while the cross-plan merge mutex is held. A ``done`` record is the only
    kind the classifier can preserve; a ``failed`` or ``loop_back`` record is
    retried by the dispatcher regardless of HEAD, so it goes straight to the
    refusal without paying for a verdict nobody would use.
    """
    calls: list[str] = []

    def _counting_classifier(step, _project_dir, _recorded):
        calls.append(step)
        return {'status': 'success', 'verdict': 'invalidated'}

    status = {
        'metadata': {
            'phase_steps': {
                '6-finalize': {
                    'functional-review': {'outcome': 'done', 'head_at_completion': HEAD_GATED},
                    'pre-push-quality-gate': {'outcome': 'done', 'head_at_completion': HEAD_GATED},
                    'automatic-review': {'outcome': 'loop_back', 'head_at_completion': HEAD_GATED},
                    'ci-verify': {'outcome': 'failed', 'head_at_completion': HEAD_GATED},
                }
            }
        }
    }

    result = _merge_pre_seam(status, HEAD_MERGED, classifier=_counting_classifier)

    assert result['status'] == 'error', result
    assert sorted(calls) == ['functional-review', 'pre-push-quality-gate']
    assert {item['step'] for item in result['steps']} == {
        'functional-review',
        'pre-push-quality-gate',
        'automatic-review',
        'ci-verify',
    }


def test_the_classifier_call_carries_the_modules_finite_bound(monkeypatch):
    """The delegated verb runs under the module's own timeout, never unbounded."""
    import inspect

    captured: dict = {}
    bound = inspect.signature(gate._run_verb).parameters['timeout'].default
    assert bound == gate._VERB_TIMEOUT_SECONDS
    assert isinstance(bound, int) and bound > 0

    def _fake_run_verb(notation, argv, **kwargs):
        captured['notation'] = notation
        captured['kwargs'] = kwargs
        return {'status': 'success', 'verdict': 'preserved'}

    monkeypatch.setattr(gate, '_run_verb', _fake_run_verb)
    status = _status({'functional-review': HEAD_GATED})

    result = _merge_pre_seam(status, HEAD_MERGED)

    assert result['dispatched'] is True, result
    assert captured['notation'] == 'plan-marshall:phase-6-finalize:verdict_currency'
    assert 'timeout' not in captured['kwargs'], 'the classifier must inherit the module bound'


@pytest.mark.parametrize(
    'verdict',
    [
        {'status': 'error', 'error': 'verdict_currency_unreadable'},
        {'status': 'timeout'},
        {'status': 'success'},
        {'status': 'success', 'verdict': 'unknown'},
    ],
    ids=['error', 'timeout', 'no-verdict', 'unknown-verdict'],
)
def test_every_non_preserved_classifier_answer_refuses(verdict):
    """Only ``success`` + ``preserved`` admits; every other answer refuses."""
    status = _status({'functional-review': HEAD_GATED})

    result = _merge(
        status,
        HEAD_MERGED,
        classifier=lambda _step, _project_dir, _recorded: verdict,
    )

    assert result['status'] == 'error', result
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert result['dispatched'] is False
