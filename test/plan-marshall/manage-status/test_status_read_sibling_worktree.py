#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``manage-status``' read-verb sibling-worktree resolution (D10).

Under ADR-002 a phase-5+ plan's directory MOVES into its own worktree, so it is
absent from every other checkout by design. ``require_status`` answered that
absence with a bare ``file_not_found``, a refusal structurally incapable of
returning presence for such a plan — and reading it as "the plan is dead"
destroyed live coordination state.

The fix has two halves, and both are pinned here:

* the READ verbs consult ``git-workflow locate-plan-checkout`` on a local miss and
  adopt the holding checkout's document, publishing WHICH checkout answered;
* the refusal, when no reachable checkout holds the plan, carries an explicit
  discriminator saying whether the look substantiates absence at all.

⛔ The fallback is read-only. ``require_status`` also gates the WRITE verbs, and
they commit through a LOCALLY resolved path, so a write that resolved a sibling
plan would write the document into the wrong tree. ``TestWriteVerbsKeepTheStrictGate``
reddens if that gate is removed.

**What is real and what is stubbed.** The git repository, the linked worktree, the
moved-in plan directory and every status read are REAL: the tests build the
production layout with ``git worktree add`` and point the resolver at the main
checkout's base, so the read genuinely runs from a different tree than the one
holding the plan. Only ``_run_locator`` — the process hop into ``git-workflow`` —
is stubbed, at its own named seam, standing in for that verb's documented
``{location, worktree_path}`` contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from marketplace_paths import WORKTREES_DIRNAME
from toon_parser import parse_toon

from conftest import load_script_module, parse_ns

status_query = load_script_module(
    'plan-marshall', 'manage-status', '_status_query.py', '_status_query_sibling_worktree_under_test'
)
# ``_status_query``'s module body ran its ``from _status_core import ...`` above,
# which cached the core module under its own name. That instance — not a second
# ``load_script_module`` alias — is the one the query verbs actually call into, so
# it is the one a stub has to be attached to.
status_core = sys.modules['_status_core']

PLAN_ID = 'sibling-worktree-plan'


# =============================================================================
# Fixture helpers — a real repo with a real linked worktree
# =============================================================================


def _init_repo(repo: Path) -> None:
    """Initialise a fixture git repo in the canonical plan-marshall layout."""
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n', encoding='utf-8')
    plan_dir = repo / '.plan'
    plan_dir.mkdir(exist_ok=True)
    (plan_dir / 'marshal.json').write_text('{"system": {}, "plan": {}}\n', encoding='utf-8')
    (repo / '.gitignore').write_text('.plan/local\n.plan/execute-script.py\n', encoding='utf-8')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)
    (plan_dir / 'local' / 'plans').mkdir(parents=True, exist_ok=True)


def _status_document(current_phase: str = '5-execute') -> dict[str, object]:
    return {
        'title': 'A plan that moved into its worktree',
        'current_phase': current_phase,
        'phases': [
            {'name': '1-init', 'status': 'done'},
            {'name': '5-execute', 'status': 'in_progress'},
        ],
        'metadata': {'use_worktree': True},
        'created': '2026-01-01T00:00:00Z',
        'updated': '2026-01-01T00:00:00Z',
    }


def _add_linked_worktree(repo: Path, base: Path, plan_id: str) -> Path:
    """Create a REAL linked worktree at the canonical slot and move a plan into it.

    The slot is composed from the resolved base plus the shared
    :data:`WORKTREES_DIRNAME` segment — the same join ``worktree-create``
    materializes — so the fixture reproduces the production layout rather than an
    approximation of it. It is deliberately built from ``base`` (always under
    ``tmp_path``) rather than from whatever ``get_worktree_root()`` returns, so a
    resolver that failed to honour the override could never make a test write
    outside its own temporary tree; the precondition assertion in
    :func:`_assert_worktree_root_honours_override` is what checks the two agree.
    """
    worktree_root = base / WORKTREES_DIRNAME
    worktree_root.mkdir(parents=True, exist_ok=True)
    target = worktree_root / plan_id
    subprocess.run(
        ['git', '-C', str(repo), 'worktree', 'add', '-q', '-b', f'feature/{plan_id}', str(target)],
        check=True,
    )
    moved_in = target / '.plan' / 'local' / 'plans' / plan_id
    moved_in.mkdir(parents=True, exist_ok=True)
    (moved_in / 'status.json').write_text(json.dumps(_status_document()), encoding='utf-8')
    return target


def _assert_worktree_root_honours_override(base: Path) -> None:
    """Pin the layout the fixture was built against to the one the code resolves."""
    assert status_core.get_worktree_root() == base / WORKTREES_DIRNAME


@pytest.fixture
def main_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real repo whose ``.plan/local`` is the resolved base. Returns that base."""
    repo = tmp_path / 'main'
    _init_repo(repo)
    base = repo / '.plan' / 'local'
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return base


def _ns(*argv: str) -> Namespace:
    """A namespace built by the production parser, so every default is the real one."""
    namespace: Namespace = parse_ns('plan-marshall', 'manage-status', 'manage-status.py', *argv, register=False)
    return namespace


def _stub_locator(monkeypatch: pytest.MonkeyPatch, lookup) -> list[str]:
    """Replace the process hop with ``lookup``; return the list of plan ids it saw."""
    seen: list[str] = []

    def fake(plan_id: str):
        seen.append(plan_id)
        return lookup

    monkeypatch.setattr(status_core, '_run_locator', fake)
    return seen


# =============================================================================
# The read verbs resolve a plan that lives in a sibling worktree
# =============================================================================


class TestSiblingWorktreeRead:
    def test_read_from_another_tree_returns_the_worktree_resident_plan(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A real linked worktree holds the plan; the resolver is anchored at the
        # MAIN checkout, so this read runs from a different tree than the one the
        # plan lives in — the exact shape that used to answer file_not_found.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        _assert_worktree_root_honours_override(main_base)
        assert not (main_base / 'plans' / PLAN_ID / 'status.json').exists()
        _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_read(_ns('read', '--plan-id', PLAN_ID))

        assert result is not None, 'the read refused a plan that is alive in a sibling worktree'
        assert result['status'] == 'success'
        assert result['plan']['current_phase'] == '5-execute'
        assert result['plan']['title'] == 'A plan that moved into its worktree'

    def test_read_names_the_checkout_that_answered(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The provenance is what lets a caller tell a local read from a foreign one.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_read(_ns('read', '--plan-id', PLAN_ID))

        assert result is not None
        assert result['resolved_from'] == 'worktree'
        assert result['resolved_checkout'] == str(worktree)

    def test_a_locally_resolved_read_is_labelled_current_and_names_no_checkout(
        self, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Provenance rides EVERY read, so the local case is positively labelled
        # rather than being the absence of a field.
        plan_dir = main_base / 'plans' / PLAN_ID
        plan_dir.mkdir(parents=True)
        (plan_dir / 'status.json').write_text(json.dumps(_status_document('2-refine')), encoding='utf-8')
        seen = _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        result = status_query.cmd_read(_ns('read', '--plan-id', PLAN_ID))

        assert result is not None
        assert result['resolved_from'] == 'current'
        assert 'resolved_checkout' not in result
        assert seen == [], 'a local hit must not pay for the locator consult'

    @pytest.mark.parametrize('verb', ['progress', 'get-context'])
    def test_the_other_read_verbs_resolve_the_sibling_plan_too(
        self, verb: str, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # progress and get-context share the widened gate with read; a verb that
        # kept the strict one would refuse and return None here.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))
        handler = {'progress': status_query.cmd_progress, 'get-context': status_query.cmd_get_context}[verb]

        result = handler(_ns(verb, '--plan-id', PLAN_ID))

        assert result is not None
        assert result['status'] == 'success'
        assert result['resolved_from'] == 'worktree'

    def test_metadata_get_resolves_the_sibling_plan(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_metadata(_ns('metadata', '--plan-id', PLAN_ID, '--get', '--field', 'use_worktree'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['value'] is True
        assert result['resolved_from'] == 'worktree'


# =============================================================================
# The refusal discriminator — absent here is not absent anywhere
# =============================================================================


class TestAbsenceDiscriminator:
    def test_a_locator_verdict_from_main_scope_substantiates_absence(
        self, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The conjunction that DOES justify the claim: the locator rendered a
        # verdict and the scope observes main plus every sibling worktree.
        _stub_locator(monkeypatch, status_core._LOOKUP_NO_HOLDER)

        resolution = status_core.resolve_plan_status('nobody-has-this', any_checkout=True)

        assert resolution.status is None
        assert resolution.scope == 'main'
        assert resolution.visibility == status_core.PLAN_ABSENT_ANYWHERE

    def test_absence_from_a_worktree_local_scope_is_not_absence(
        self, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A pinned worktree's base is blind to sibling worktrees, so its miss says
        # nothing about whether the plan exists elsewhere.
        monkeypatch.setattr(status_core, 'get_base_dir', lambda: main_base / WORKTREES_DIRNAME / 'wt-x' / 'local')
        _stub_locator(monkeypatch, status_core._LOOKUP_NO_HOLDER)

        resolution = status_core.resolve_plan_status('nobody-has-this', any_checkout=True)

        assert resolution.scope == 'worktree_local'
        assert resolution.visibility == status_core.PLAN_NOT_VISIBLE_FROM_SCOPE

    def test_a_degraded_locator_never_claims_absence(self, main_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # The locator could not answer — no executor, a non-zero exit, an
        # unparsable payload. A miss on top of that establishes nothing, and the
        # main scope alone must not upgrade it into a claim about every checkout.
        #
        # The worktree slot must EXIST for a degraded consult to be reachable at
        # all: with no slot the pre-gate renders _LOOKUP_NO_HOLDER by itself and
        # the consult never runs, which is a different state pinned by
        # ``test_the_slot_pre_gate_answers_without_spawning_the_locator``. The
        # ``seen`` assertion below is what keeps the two apart — without it this
        # test passes through the pre-gate path and checks nothing it claims to.
        (main_base / WORKTREES_DIRNAME / 'nobody-has-this').mkdir(parents=True)
        seen = _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        resolution = status_core.resolve_plan_status('nobody-has-this', any_checkout=True)

        assert seen == ['nobody-has-this'], 'the locator was never consulted, so nothing degraded'
        assert resolution.scope == 'main'
        assert resolution.visibility == status_core.PLAN_NOT_VISIBLE_FROM_SCOPE

    def test_a_strict_gate_never_claims_absence(self, main_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # A write verb never consults the locator, so its refusal reports only
        # what the local look established.
        seen = _stub_locator(monkeypatch, status_core._LOOKUP_NO_HOLDER)

        resolution = status_core.resolve_plan_status('nobody-has-this', any_checkout=False)

        assert seen == []
        assert resolution.visibility == status_core.PLAN_NOT_VISIBLE_FROM_SCOPE

    def test_the_emitted_refusal_carries_the_discriminator(
        self, main_base: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # The bare refusal is what the deliverable exists to end: the payload must
        # keep its file_not_found code AND say how wide the look reached.
        _stub_locator(monkeypatch, status_core._LOOKUP_NO_HOLDER)

        result = status_query.cmd_read(_ns('read', '--plan-id', 'nobody-has-this'))

        assert result is None
        payload = parse_toon(capsys.readouterr().out)
        assert payload['error'] == 'file_not_found'
        assert payload['scope'] == 'main'
        assert payload['plan_visibility'] == status_core.PLAN_ABSENT_ANYWHERE

    def test_the_sibling_outcome_is_distinguishable_from_the_refusal(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The two outcomes must not be told apart by absence-of-a-field alone:
        # one is a success naming its checkout, the other a refusal naming its scope.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))
        found = status_core.resolve_plan_status(PLAN_ID, any_checkout=True)

        _stub_locator(monkeypatch, status_core._LOOKUP_NO_HOLDER)
        missing = status_core.resolve_plan_status('nobody-has-this', any_checkout=True)

        assert (found.location, found.visibility) == ('worktree', None)
        assert (missing.location, missing.visibility) == ('not_found', status_core.PLAN_ABSENT_ANYWHERE)
        assert found.checkout_path == str(worktree)
        assert missing.checkout_path is None

    def test_the_slot_pre_gate_answers_without_spawning_the_locator(
        self, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No worktree slot exists for the plan, so the verb has nothing to find and
        # its answer is known in advance — an ANSWER, not a degraded consult.
        seen = _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        lookup = status_core._locate_plan_checkout('nobody-has-this')

        assert seen == []
        assert lookup == status_core._LOOKUP_NO_HOLDER


# =============================================================================
# ⛔ The write verbs keep the strict gate
# =============================================================================


class TestWriteVerbsKeepTheStrictGate:
    def test_metadata_set_refuses_a_sibling_plan_and_writes_no_local_document(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Removing the read-only gate reddens this: require_status would hand the
        # sibling's document to the --set branch, which commits through the
        # LOCALLY resolved path and would materialize status.json in the wrong tree.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        sibling_status = worktree / '.plan' / 'local' / 'plans' / PLAN_ID / 'status.json'
        before = sibling_status.read_text(encoding='utf-8')
        seen = _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_metadata(
            _ns('metadata', '--plan-id', PLAN_ID, '--set', '--field', 'change_type', '--value', 'bug_fix')
        )

        assert result is None, 'the write verb resolved a sibling-worktree plan'
        assert seen == [], 'the write path consulted the sibling-worktree locator'
        assert not (main_base / 'plans' / PLAN_ID / 'status.json').exists()
        assert sibling_status.read_text(encoding='utf-8') == before

    def test_set_phase_refuses_a_sibling_plan_and_writes_no_local_document(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        seen = _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_set_phase(_ns('set-phase', '--plan-id', PLAN_ID, '--phase', '5-execute'))

        assert result is None
        assert seen == []
        assert not (main_base / 'plans' / PLAN_ID / 'status.json').exists()

    def test_get_worktree_path_keeps_the_strict_gate(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # This read verb is deliberately excluded: locate-plan-checkout calls back
        # into it, so opting it in would make the consult call itself.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        seen = _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_get_worktree_path(_ns('get-worktree-path', '--plan-id', PLAN_ID))

        assert result is None
        assert seen == []


# =============================================================================
# cmd_list is UNCHANGED — pinning the refuted half of the original hypothesis
# =============================================================================


class TestCmdListUnchanged:
    def test_cmd_list_still_scans_worktrees_and_publishes_scope(self, main_base: Path, tmp_path: Path) -> None:
        # The `list` half of the fold was refuted at outline time: the scan and the
        # scope field already shipped. Pinned here so a later reader cannot mistake
        # the untouched verb for an unfixed one.
        _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)

        result = status_query.cmd_list(_ns('list'))

        assert result['scope'] == 'main'
        assert [(plan['id'], plan['location']) for plan in result['plans']] == [(PLAN_ID, 'worktree')]

    def test_cmd_list_carries_no_read_verb_provenance(self, main_base: Path, tmp_path: Path) -> None:
        # The enumeration answers a different question than a single-plan read, so
        # it gains none of the read verbs' provenance fields.
        _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)

        result = status_query.cmd_list(_ns('list'))

        assert 'resolved_from' not in result
        assert 'plan_visibility' not in result


# =============================================================================
# A non-object ``metadata`` field is an input, not a crash
#
# status.json is on-disk and operator-editable, so ``"metadata": null`` is a
# reachable input rather than a hypothetical. Neither of the two guards that
# stood here keys on the VALUE: ``.get('metadata', {})`` applies its default only
# when the KEY IS ABSENT, and ``'metadata' not in status`` is satisfied by an
# explicit null — so both fell through to an AttributeError on None.
# =============================================================================


def _write_local_plan(base: Path, plan_id: str, metadata: object) -> Path:
    """Write a local plan document whose ``metadata`` field is ``metadata`` verbatim.

    Verbatim is the point: the fixture must be able to place a JSON ``null`` (and
    a non-object scalar) where every other fixture in this file places a dict.
    """
    plan_dir = base / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    document = _status_document('2-refine')
    document['metadata'] = metadata
    (plan_dir / 'status.json').write_text(json.dumps(document), encoding='utf-8')
    return plan_dir / 'status.json'


class TestANonObjectMetadataFieldIsHandled:
    """Both branches normalize; neither raises. The dict cells are matched controls.

    Without the dict cells the guard is equally consistent with a normalization
    that discards every caller's real metadata, which would pass the null cells
    and silently destroy state on the ordinary path.
    """

    @pytest.mark.parametrize('metadata', [None, 'a string', 42, ['a', 'list']])
    def test_metadata_get_reports_not_found_instead_of_raising(
        self, metadata: object, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — the widened any-checkout READ branch, over a document whose
        # metadata is not an object.
        _write_local_plan(main_base, PLAN_ID, metadata)
        _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        # Act
        result = status_query.cmd_metadata(_ns('metadata', '--plan-id', PLAN_ID, '--get', '--field', 'use_worktree'))

        # Assert — a structured verdict, and an available_fields list that is
        # empty because it was DERIVED from a normalized empty mapping.
        assert result is not None
        assert result['status'] == 'not_found'
        assert result['available_fields'] == []

    def test_metadata_get_still_returns_a_real_value(self, main_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Matched control — normalization must not flatten a genuine object.
        _write_local_plan(main_base, PLAN_ID, {'use_worktree': True, 'other': 'x'})
        _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        result = status_query.cmd_metadata(_ns('metadata', '--plan-id', PLAN_ID, '--get', '--field', 'use_worktree'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['value'] is True

    @pytest.mark.parametrize('metadata', [None, 'a string', 42])
    def test_metadata_set_writes_through_instead_of_raising(
        self, metadata: object, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — the sibling WRITE branch, whose ``'metadata' not in status``
        # guard an explicit null walks straight past.
        status_path = _write_local_plan(main_base, PLAN_ID, metadata)
        _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        # Act
        result = status_query.cmd_metadata(
            _ns('metadata', '--plan-id', PLAN_ID, '--set', '--field', 'change_type', '--value', 'bug_fix')
        )

        # Assert — and the correction reaches DISK, not only the in-memory view.
        assert result is not None
        assert result['status'] == 'success'
        assert result['value'] == 'bug_fix'
        assert json.loads(status_path.read_text(encoding='utf-8'))['metadata'] == {'change_type': 'bug_fix'}

    def test_metadata_set_preserves_existing_sibling_fields(
        self, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Matched control — the normalization must be a no-op on a real object, so
        # a set never becomes a wipe of everything already recorded.
        status_path = _write_local_plan(main_base, PLAN_ID, {'use_worktree': True})
        _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        result = status_query.cmd_metadata(
            _ns('metadata', '--plan-id', PLAN_ID, '--set', '--field', 'change_type', '--value', 'bug_fix')
        )

        assert result is not None
        assert result['status'] == 'success'
        persisted = json.loads(status_path.read_text(encoding='utf-8'))['metadata']
        assert persisted == {'use_worktree': True, 'change_type': 'bug_fix'}
