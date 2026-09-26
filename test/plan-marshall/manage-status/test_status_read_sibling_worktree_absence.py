# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_status_read_sibling_worktree_fixtures import (
    PLAN_ID,
    WORKTREES_DIRNAME,
    Path,
    _add_linked_worktree,
    _ns,
    _stub_locator,
    main_base,
    parse_toon,
    pytest,
    status_core,
    status_query,
)

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
