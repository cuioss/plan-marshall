#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression suite for the absent-findings-store discriminator.

Driven through the ``manage-findings.py`` CLI entry point rather than the core
functions, so the argparse surface — including the presence set of the read-only
``--any-checkout`` flag — is exercised alongside the store behaviour.

Seven scenarios, six of which carry a matched control:

1. **Non-benign zero** — a ``plan_id`` with no directory under the resolved root.
   Every one of the five CLI read verbs refuses and names the root it looked
   under. RED before the store handle landed, GREEN after.
2. **Benign zero (the load-bearing control)** — a plan directory that exists and
   has filed nothing. ``list`` still returns ``status: success`` /
   ``total_count: 0``. GREEN both before AND after: a change that turned every
   zero into an error would pass scenario 1 and fail here, which is the
   documented inverse defect.
3. **Resolved and populated** — the happy path is undisturbed, and reports
   ``present``.
4. **Cross-checkout read** — ``--any-checkout`` reads a worktree-resident plan
   from the main root; the same call without the flag refuses and names the
   worktree; and the WRITE verbs reject the flag at the argparse layer.
5. **Cross-store write leak** — ``promote`` / ``resolve`` handed a Q-Gate or
   assessment hash refuse and leave the file byte-identical, while the same verbs
   handed a genuine plan-finding hash still succeed and still write.
6. **Phantom-store creation** — the three ``add`` verbs refuse against an absent
   plan directory AND create nothing on disk (a filesystem probe, because a guard
   that errors *after* mkdir would pass a payload-only assertion), while the same
   verbs against a real plan with no ``artifacts/findings/`` yet still succeed
   and still create the file.
7. **The ``ingest`` refusal** — ``ingest`` is a read-AND-write verb defined
   outside ``_findings_core``, and it was the one operation surface the store
   guard did not reach. Against an absent plan directory it returns the SAME named
   refusal every other surface returns; against a resolved-but-empty store it
   still returns a genuine success with three zero counts; and against a resolved
   store holding a pending ``raw_input`` finding it still promotes.

   ⛔ The regression is directional and both directions are pinned. BEFORE the
   store handle existed, ``ingest`` answered an absent store with ``status:
   success`` and ``promoted: 0 / rejected: 0 / skipped: 0`` — the clean zero this
   suite exists to abolish. Between the handle landing and this guard it answered
   with ``error: internal_error`` / ``message: findings``, an opaque
   ``KeyError('findings')`` raised by subscripting a refusal payload that carries
   no such key. The scenario asserts the refusal is neither of those: not a
   success (the original defect) and not an unnamed crash (the regression).
"""

import json
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-findings', 'manage-findings.py')

#: The exact set of read verbs ``--any-checkout`` is declared on. Held here as
#: the argv prefix each one needs, so scenario 1 runs over the whole set rather
#: than over a sample of it.
READ_VERBS = {
    'list': ('list',),
    'get': ('get', '--hash-id', 'deadbe'),
    'qgate list': ('qgate', 'list', '--phase', '5-execute'),
    'assessment list': ('assessment', 'list'),
    'assessment get': ('assessment', 'get', '--hash-id', 'deadbe'),
}

#: The write verbs that must NOT accept ``--any-checkout``, with enough argv to
#: reach the flag rejection rather than a missing-required-argument rejection.
WRITE_VERBS = {
    'resolve': ('resolve', '--hash-id', 'deadbe', '--resolution', 'fixed'),
    'promote': ('promote', '--hash-id', 'deadbe', '--promoted-to', 'architecture'),
    'ingest': ('ingest',),
    'qgate resolve': ('qgate', 'resolve', '--hash-id', 'deadbe', '--resolution', 'fixed', '--phase', '5-execute'),
    'qgate clear': ('qgate', 'clear', '--phase', '5-execute'),
    'assessment clear': ('assessment', 'clear'),
}


def _root() -> Path:
    """The runtime-state root the CLI subprocess will resolve.

    Read from the live resolver rather than reconstructed, so the test and the
    subprocess cannot disagree about which sandbox is in play.
    """
    from file_ops import get_base_dir  # local import: resolved per test, after the sandbox fixture

    return get_base_dir()


def _cli(*args: str, **kwargs) -> tuple[int, dict]:
    """Run the CLI and return ``(exit_code, parsed_toon)``."""
    result = run_script(SCRIPT_PATH, *args, **kwargs)
    try:
        payload = parse_toon(result.stdout)
    except Exception:  # broad on purpose: an unparsable payload is reported as empty, never swallowed
        payload = {}
    return result.returncode, (payload if isinstance(payload, dict) else {})


def _seed_plan_dir(plan_id: str) -> Path:
    """Materialize ``plans/{plan_id}/`` — what phase-1-init does in production."""
    plan_dir = _root() / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    return plan_dir


# =============================================================================
# Scenario 1 — the non-benign zero
# =============================================================================


@pytest.mark.parametrize('verb', sorted(READ_VERBS))
def test_every_read_verb_refuses_a_plan_absent_from_the_resolved_root(verb):
    plan_id = 'regression-absent-plan'
    assert not (_root() / 'plans' / plan_id).exists()

    _code, payload = _cli(*READ_VERBS[verb], '--plan-id', plan_id)

    assert payload.get('status') == 'error', f'{verb} did not refuse: {payload}'
    assert payload.get('error') == 'findings_store_unresolved'
    assert payload.get('findings_store_state') == 'plan_absent'
    assert payload.get('unresolved_store') is True
    assert str(_root()) in str(payload.get('message', '')), (
        f'{verb} refused without naming the resolved root'
    )


# =============================================================================
# Scenario 2 — the benign zero (matched control, green before AND after)
# =============================================================================


def test_a_resolved_plan_that_filed_nothing_still_reports_a_genuine_zero():
    plan_id = 'regression-benign-zero'
    _seed_plan_dir(plan_id)

    _code, payload = _cli('list', '--plan-id', plan_id)

    assert payload['status'] == 'success'
    assert payload['total_count'] == 0
    assert payload['findings_store_state'] == 'missing'
    assert payload['unresolved_store'] is False


def test_the_two_zeros_are_distinguishable_in_one_comparison():
    """The whole point, stated as a single comparison.

    Asserting the two cases in separate tests leaves open that they still agree
    on the field a caller branches on; this pins them as DIFFERENT answers to the
    same question.
    """
    _seed_plan_dir('regression-pair-resolved')

    _code_a, benign = _cli('list', '--plan-id', 'regression-pair-resolved')
    _code_b, absent = _cli('list', '--plan-id', 'regression-pair-missing')

    assert benign['status'] != absent['status']
    assert benign['findings_store_state'] != absent['findings_store_state']


# =============================================================================
# Scenario 3 — resolved and populated
# =============================================================================


def test_a_populated_store_reports_present_and_the_unchanged_counts():
    plan_id = 'regression-populated'
    _seed_plan_dir(plan_id)

    code, added = _cli(
        'add', '--plan-id', plan_id, '--type', 'bug', '--title', 'T', '--detail', 'D'
    )
    assert code == 0 and added['status'] == 'success', added

    _code, payload = _cli('list', '--plan-id', plan_id)

    assert payload['status'] == 'success'
    assert payload['total_count'] == 1
    assert payload['filtered_count'] == 1
    assert payload['findings_store_state'] == 'present'


# =============================================================================
# Scenario 4 — the cross-checkout read (D2)
# =============================================================================


_LOCATOR_STUB = '''#!/usr/bin/env python3
"""Stub executor standing in for the ``locate-plan-checkout`` consult.

The real verb shells out through the generated executor, which does not exist in
a sandboxed test root. Only the LOCATOR boundary is stubbed: the store handle,
the adoption of the reported checkout, the CLI flag surface and the read itself
all run for real against a genuine on-disk worktree-resident store.
"""
print("""status: success
plan_id: {plan_id}
location: worktree
worktree_path: {worktree_path}""")
'''


def _materialize_worktree_resident_plan(plan_id: str) -> Path:
    """Build a real worktree-resident store and the locator stub that finds it.

    Returns the worktree root. The worktree-resident findings are filed through
    the CLI itself (pointed at the worktree's own runtime-state root), so the
    records under test are written by the production code path rather than by
    hand-assembled JSONL.
    """
    root = _root()
    worktree = root / 'worktrees' / plan_id
    worktree_local = worktree / '.plan' / 'local'
    (worktree_local / 'plans' / plan_id).mkdir(parents=True)

    code, added = _cli(
        'add', '--plan-id', plan_id, '--type', 'bug',
        '--title', 'Worktree-resident finding', '--detail', 'D',
        env_overrides={'PLAN_BASE_DIR': str(worktree_local)},
    )
    assert code == 0 and added['status'] == 'success', added

    (root / 'execute-script.py').write_text(
        _LOCATOR_STUB.format(plan_id=plan_id, worktree_path=str(worktree)),
        encoding='utf-8',
    )
    return worktree


def test_any_checkout_reads_a_worktree_resident_plan_from_the_main_root():
    plan_id = 'regression-cross-checkout'
    _materialize_worktree_resident_plan(plan_id)
    assert not (_root() / 'plans' / plan_id).exists(), (
        'the plan must be absent from the MAIN root for this to be a cross-checkout read'
    )

    _code, payload = _cli('list', '--plan-id', plan_id, '--any-checkout')

    assert payload['status'] == 'success', payload
    assert payload['findings_store_state'] == 'present'
    assert payload['total_count'] == 1


def test_without_the_flag_the_same_call_refuses_and_names_the_worktree():
    """Matched negative control: the flag is what changes the answer, not the setup."""
    plan_id = 'regression-cross-checkout-noflag'
    worktree = _materialize_worktree_resident_plan(plan_id)

    _code, payload = _cli('list', '--plan-id', plan_id)

    assert payload['status'] == 'error'
    assert payload['findings_store_state'] == 'plan_absent'
    assert str(worktree) in str(payload.get('message', '')), (
        'the refusal must name the checkout that actually holds the plan'
    )


@pytest.mark.parametrize('verb', sorted(WRITE_VERBS))
def test_no_write_verb_accepts_any_checkout(verb):
    """The presence set is enforced by argparse, not by documentation.

    Asserted against the CLI surface itself: a write verb handed the flag exits
    2, so copying the flag onto one later fails a test rather than passing
    review.
    """
    result = run_script(
        SCRIPT_PATH, *WRITE_VERBS[verb], '--plan-id', 'regression-flag-set', '--any-checkout'
    )
    assert result.returncode == 2, (
        f'{verb} accepted --any-checkout (exit {result.returncode}); '
        'the flag is read-only and must be rejected on every write verb'
    )


@pytest.mark.parametrize('verb', sorted(READ_VERBS))
def test_every_read_verb_accepts_any_checkout(verb):
    """The matched positive direction: the flag IS declared on all five reads.

    Without this, the refusal above is equally consistent with the flag not
    existing at all.
    """
    plan_id = 'regression-flag-read'
    _seed_plan_dir(plan_id)

    result = run_script(SCRIPT_PATH, *READ_VERBS[verb], '--plan-id', plan_id, '--any-checkout')

    assert result.returncode != 2, f'{verb} rejected --any-checkout: {result.stderr}'


# =============================================================================
# Scenario 5 — the cross-store write leak (D5 / B2)
# =============================================================================


def _seed_cross_store(plan_id: str) -> tuple[str, str, str, Path]:
    """Seed one plan finding, one Q-Gate finding and one assessment via the CLI."""
    _seed_plan_dir(plan_id)
    _code, finding = _cli(
        'add', '--plan-id', plan_id, '--type', 'bug', '--title', 'Plan', '--detail', 'D'
    )
    _code, qgate = _cli(
        'qgate', 'add', '--plan-id', plan_id, '--phase', '5-execute',
        '--source', 'qgate', '--type', 'bug', '--title', 'QGate', '--detail', 'D',
    )
    _code, assessment = _cli(
        'assessment', 'add', '--plan-id', plan_id,
        '--file-path', 'src/a.py', '--certainty', 'UNCERTAIN', '--confidence', '50',
    )
    findings_dir = _root() / 'plans' / plan_id / 'artifacts' / 'findings'
    return finding['hash_id'], qgate['hash_id'], assessment['hash_id'], findings_dir


@pytest.mark.parametrize('sibling', ['qgate', 'assessment'])
@pytest.mark.parametrize('verb', ['resolve', 'promote'])
def test_a_write_verb_handed_a_sibling_store_hash_refuses_and_writes_nothing(verb, sibling):
    plan_id = f'regression-leak-{verb}-{sibling}'
    _plan_hash, qgate_hash, assessment_hash, findings_dir = _seed_cross_store(plan_id)

    if sibling == 'qgate':
        target_path = findings_dir / 'qgate-5-execute.jsonl'
        target_hash = qgate_hash
    else:
        target_path = findings_dir / 'assessments.jsonl'
        target_hash = assessment_hash
    before = target_path.read_bytes()

    args = (
        ('resolve', '--hash-id', target_hash, '--resolution', 'fixed')
        if verb == 'resolve'
        else ('promote', '--hash-id', target_hash, '--promoted-to', 'architecture')
    )
    _code, payload = _cli(*args, '--plan-id', plan_id)

    assert payload['status'] == 'error', payload
    assert payload['error'] == 'finding_in_other_store'
    assert payload['use_verb']
    assert target_path.read_bytes() == before, f'{verb} mutated the {sibling} store'


@pytest.mark.parametrize('verb', ['resolve', 'promote'])
def test_the_same_write_verb_still_writes_a_genuine_plan_finding(verb):
    """Matched negative control: the guard rejects nothing legitimate."""
    plan_id = f'regression-leak-ok-{verb}'
    plan_hash, _qgate_hash, _assessment_hash, findings_dir = _seed_cross_store(plan_id)

    bug_path = findings_dir / 'bug.jsonl'
    before = bug_path.read_bytes()

    args = (
        ('resolve', '--hash-id', plan_hash, '--resolution', 'fixed')
        if verb == 'resolve'
        else ('promote', '--hash-id', plan_hash, '--promoted-to', 'architecture')
    )
    _code, payload = _cli(*args, '--plan-id', plan_id)

    assert payload['status'] == 'success', payload
    assert bug_path.read_bytes() != before, f'{verb} reported success without writing'
    record = json.loads(bug_path.read_text(encoding='utf-8').splitlines()[0])
    assert record['hash_id'] == plan_hash


# =============================================================================
# Scenario 6 — phantom-store creation (Shape C)
# =============================================================================


#: The three ``add`` CLI verbs, with the argv each needs beyond ``--plan-id``.
ADD_VERBS = {
    'add': ('add', '--type', 'bug', '--title', 'T', '--detail', 'D'),
    'qgate add': (
        'qgate', 'add', '--phase', '5-execute', '--source', 'qgate',
        '--type', 'bug', '--title', 'T', '--detail', 'D',
    ),
    'assessment add': (
        'assessment', 'add', '--file-path', 'src/a.py',
        '--certainty', 'UNCERTAIN', '--confidence', '50',
    ),
}

#: The file each ``add`` verb creates on its first successful write, used by the
#: scenario-6 negative control.
ADD_VERB_ARTIFACT = {
    'add': 'bug.jsonl',
    'qgate add': 'qgate-5-execute.jsonl',
    'assessment add': 'assessments.jsonl',
}


@pytest.mark.parametrize('verb', sorted(ADD_VERBS))
def test_an_add_against_an_absent_plan_refuses_and_creates_nothing(verb):
    """Positive control, asserted on the FILESYSTEM as well as the payload.

    ``append_jsonl``'s ``ensure_parent_dir`` mkdirs the whole chain, so a guard
    that returns an error but still reaches the append would satisfy a
    payload-only assertion while leaving exactly the phantom store this refusal
    exists to prevent.
    """
    plan_id = f'regression-phantom-{verb.replace(" ", "-")}'
    plan_dir = _root() / 'plans' / plan_id
    assert not plan_dir.exists()

    _code, payload = _cli(*ADD_VERBS[verb], '--plan-id', plan_id)

    assert payload['status'] == 'error', payload
    assert payload['error'] == 'findings_store_unresolved'
    assert payload['findings_store_state'] == 'plan_absent'
    assert not plan_dir.exists(), f'{verb} manufactured {plan_dir} while refusing'


@pytest.mark.parametrize('verb', sorted(ADD_VERBS))
def test_a_real_plans_first_ever_finding_still_lands(verb):
    """Matched negative control: the guard keys on the PLAN directory.

    A guard keyed on ``artifacts/findings/`` instead would refuse here — breaking
    every plan's first-ever finding — and would still pass the positive control
    above. Both directions are required.
    """
    plan_id = f'regression-first-{verb.replace(" ", "-")}'
    plan_dir = _seed_plan_dir(plan_id)
    findings_dir = plan_dir / 'artifacts' / 'findings'
    assert not findings_dir.exists(), 'the control must start with no findings directory'

    code, payload = _cli(*ADD_VERBS[verb], '--plan-id', plan_id)

    assert code == 0, payload
    assert payload['status'] == 'success', payload
    assert (findings_dir / ADD_VERB_ARTIFACT[verb]).is_file(), (
        f'{verb} reported success without creating its store file'
    )


# =============================================================================
# Scenario 7 — the ``ingest`` refusal (the read-AND-write surface)
# =============================================================================


#: The three counts ``ingest`` publishes on a successful pass. Held as a set so
#: the assertions below name the whole triple rather than sampling one of it — a
#: pre-guard ``ingest`` produced a zero on all three at once, so checking one
#: would leave the other two unpinned.
_INGEST_COUNTS = ('promoted', 'rejected', 'skipped')


def test_ingest_refuses_a_plan_absent_from_the_resolved_root():
    """The positive control — and it pins BOTH prior wrong answers as excluded.

    ``ingest`` reads the pending findings and writes back to them, so an unreached
    store makes its counts a three-way zero over records it never looked at. The
    refusal must be the SAME named error every other surface returns, so a caller
    branching on ``error`` has one vocabulary to know rather than one per verb.
    """
    plan_id = 'regression-ingest-absent'
    assert not (_root() / 'plans' / plan_id).exists()

    code, payload = _cli('ingest', '--plan-id', plan_id)

    assert payload.get('status') == 'error', f'ingest did not refuse: {payload}'
    assert payload.get('error') == 'findings_store_unresolved', (
        'ingest must return the shared refusal code, not a bespoke one and not an '
        f'unnamed crash: {payload}'
    )
    assert payload.get('findings_store_state') == 'plan_absent'
    assert payload.get('unresolved_store') is True
    assert str(_root()) in str(payload.get('message', '')), (
        'the refusal must name the resolved root it looked under'
    )
    # The two answers this replaces, excluded explicitly. `internal_error` was the
    # KeyError('findings') regression; a `success` with zero counts was the
    # original clean-zero defect.
    assert payload.get('error') != 'internal_error'
    for count in _INGEST_COUNTS:
        assert count not in payload, (
            f'a refused ingest must publish no {count} count — a count computed '
            'against a store nobody reached is exactly the defect under test'
        )

    # The exit code is compared against a SIBLING verb refusing the SAME plan
    # rather than asserted as a constant. This surface reports outcomes in the
    # TOON ``status`` and exits 0 for a structured refusal on every verb; pinning
    # a literal here would assert a convention this scenario does not own, and
    # would fail for the whole surface the day that convention changed. What the
    # scenario DOES own is that ingest refuses exactly as its siblings do.
    sibling_code, sibling = _cli('list', '--plan-id', plan_id)
    assert code == sibling_code, (
        f'ingest exited {code} where the sibling read verb exited {sibling_code}; '
        'one unreached store must produce one refusal shape across every verb'
    )
    assert payload.get('error') == sibling.get('error')
    assert payload.get('findings_store_state') == sibling.get('findings_store_state')


def test_ingest_against_a_resolved_but_empty_store_is_a_genuine_success():
    """Matched negative control: the benign zero survives the guard.

    Without this direction the refusal above is equally consistent with a fix that
    turned EVERY ingest zero into an error — the documented inverse defect, which
    would make the finalize verification-feedback pass fail on every plan that has
    nothing to ingest.
    """
    plan_id = 'regression-ingest-benign'
    _seed_plan_dir(plan_id)

    code, payload = _cli('ingest', '--plan-id', plan_id)

    assert code == 0, payload
    assert payload['status'] == 'success'
    assert payload['findings_store_state'] == 'missing'
    assert payload['unresolved_store'] is False
    for count in _INGEST_COUNTS:
        assert payload[count] == 0, f'{count} should be a genuine zero here: {payload}'


def test_the_two_ingest_zeros_are_distinguishable_in_one_comparison():
    """The property the whole scenario turns on, stated as a single comparison.

    Asserting the refusal and the benign zero in separate tests leaves open that
    they still agree on the field a caller branches on. Before the guard they were
    byte-identical ``status: success`` payloads with the same three zeros.
    """
    _seed_plan_dir('regression-ingest-pair-resolved')

    _code_a, benign = _cli('ingest', '--plan-id', 'regression-ingest-pair-resolved')
    _code_b, absent = _cli('ingest', '--plan-id', 'regression-ingest-pair-missing')

    assert benign['status'] != absent['status']
    assert benign['findings_store_state'] != absent['findings_store_state']
    assert benign['unresolved_store'] is not absent['unresolved_store']


def test_ingest_still_promotes_against_a_resolved_populated_store():
    """Matched positive control on the HAPPY path: the guard blocks nothing real.

    The refusal keys on the PLAN directory, never on ``artifacts/findings/``, and
    the write paths are composed from the same resolved handle the read used. This
    exercises both: a real plan's pending ``raw_input`` is still validated and
    still promoted to the top-level field.
    """
    plan_id = 'regression-ingest-populated'
    _seed_plan_dir(plan_id)

    code, added = _cli(
        'add', '--plan-id', plan_id, '--type', 'pr-comment',
        '--title', 'T', '--detail', 'placeholder',
        '--raw-input', 'detail=promoted detail text',
    )
    assert code == 0 and added['status'] == 'success', added

    code, payload = _cli('ingest', '--plan-id', plan_id)

    assert code == 0, payload
    assert payload['status'] == 'success', payload
    assert payload['findings_store_state'] == 'present'
    assert payload['promoted'] == 1, payload

    _code, listed = _cli('list', '--plan-id', plan_id)
    record_path = _root() / 'plans' / plan_id / 'artifacts' / 'findings' / 'pr-comment.jsonl'
    record = json.loads(record_path.read_text(encoding='utf-8').splitlines()[0])
    assert record['detail'] == 'promoted detail text', (
        'ingest reported a promotion without writing it — the write path must '
        'address the same store the read resolved'
    )
    assert listed['status'] == 'success'
