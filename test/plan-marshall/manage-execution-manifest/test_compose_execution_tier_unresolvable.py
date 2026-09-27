# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_compose_execution_tier_fixtures import (
    Any,
    _clear_arch_resolve_cache,
    _mem,
    pytest,
)


class TestUnresolvableStepProvenance:
    """D3: an ``unresolvable_step`` error names WHERE the failing step came from.

    A step id in the emitted list is either authored in marshal.json or appended
    by execution_tier COMMAND routing from a derived ``verification.commands``
    entry. The error message must distinguish them, so a reader traces a routed
    step to the emitting build verb rather than hunting a marshal.json key that
    does not exist (the diagnosability gap that let one defect be filed five times).
    """

    _ROUTED_STEP = 'verify:perf-suite'

    def test_routed_step_error_names_routing_origin(self):
        """A routed (non-marshal) unresolvable step is attributed to derive-verification."""
        # marshal_map is {} (provided but empty) → the step has no marshal.json origin.
        result = _mem.check_emitted_steps_resolvable([self._ROUTED_STEP], [], {}, None)

        assert result is not None
        assert result['phase'] == 'phase_5'
        assert result['step_id'] == self._ROUTED_STEP
        message = result['message']
        assert 'execution_tier COMMAND routing' in message
        assert 'derive-verification' in message
        assert 'NOT authored in marshal.json' in message

    def test_marshal_authored_step_error_names_marshal_json(self):
        """Control: a marshal.json-authored unresolvable step is attributed to marshal.json."""
        marshal_map = {self._ROUTED_STEP: {'some': 'params'}}
        result = _mem.check_emitted_steps_resolvable([self._ROUTED_STEP], [], marshal_map, None)

        assert result is not None
        message = result['message']
        assert 'in marshal.json is unresolvable' in message
        assert 'execution_tier COMMAND routing' not in message

    def test_no_step_map_message_states_the_origin_is_undetermined(self):
        """With no step map read, the message SAYS the origin could not be determined.

        The branch previously stated no origin at all, which reads as "the origin was
        checked and nothing was found" — indistinguishable from a step genuinely
        absent from a map that WAS read. The two are different situations: this one
        holds no key map to answer the question from. Naming the indeterminacy is
        what separates them, and it is the only claim this branch can honestly make.
        """
        result = _mem.check_emitted_steps_resolvable(['verify:compile'], [], None, None)

        assert result is not None
        message = result['message']
        assert 'origin (authored vs routed) could not be determined' in message
        # It is an indeterminacy, not a marshal.json origin claim.
        assert 'in marshal.json is unresolvable' not in message
        assert 'NOT authored in marshal.json' not in message

    def test_phase_6_absent_step_is_not_attributed_to_derive_verification(self):
        """A phase-6 step absent from the map is NOT misattributed to derive-verification.

        derive-verification emits phase-5 verification commands only; a phase-6
        finalize step has no execution_tier routing path, so an unresolvable
        phase-6 step absent from the marshal map gets a neutral composer-injected
        note, never a false derive-verification attribution."""
        # marshal_phase_6_map is {} (provided, empty) → the step has no marshal origin.
        result = _mem.check_emitted_steps_resolvable([], ['bogus-finalize-step'], None, {})

        assert result is not None
        assert result['phase'] == 'phase_6'
        message = result['message']
        assert 'derive-verification' not in message
        assert 'composer-injected' in message

    # ---- the reason literal makes no origin claim (D8a) --------------------
    #
    # The wrapper is the SINGLE place provenance is stated, because it is the only
    # layer that can tell a marshal.json-authored id from a routed / composer-
    # injected one. A reason literal that also claimed an origin contradicted the
    # wrapper on exactly the inputs where the wrapper says "NOT authored in
    # marshal.json" — the message asserted both at once.

    #: The origin-claim substring removed from every reason literal.
    _ORIGIN_CLAIM = 'referenced by `marshal.json`'

    #: The input shapes on which the wrapper produces a NOT-authored message that
    #: CARRIES a provenance marker, paired with that marker and a fragment of the
    #: reason it must still state. The reason fragment is the ANTI-VACUITY control:
    #: without it, a message that lost its reason entirely would sail through the
    #: absence assertion. The three cases cover both reason producers that carried
    #: the substring (the external-implementor probe and the standards-file check)
    #: plus the unknown-canonical producer that never did.
    #:
    #: This is NOT the whole not-authored population. Every case here supplies a
    #: dict map for the phase under test, so none reaches the CSV-fallback branch,
    #: which is entered when the phase's map is None and which states no provenance
    #: marker at all. That branch is covered separately by
    #: ``test_csv_fallback_branch_claims_no_origin`` below — it needs its own test
    #: precisely because it has no marker to parametrize over, which is how it
    #: escaped a table that asserted completeness.
    _NON_AUTHORED_CASES: dict[str, dict[str, Any]] = {
        'phase5_routed_unknown_canonical': {
            'phase_5_steps': ['verify:perf-suite'],
            'phase_6_steps': [],
            'phase_5_map': {},
            'phase_6_map': None,
            'marker': 'NOT authored in marshal.json',
            'reason_fragment': 'names an unknown canonical',
        },
        'phase5_routed_external_step': {
            'phase_5_steps': ['my-bundle:ghost-verify'],
            'phase_6_steps': [],
            'phase_5_map': {},
            'phase_6_map': None,
            'marker': 'NOT authored in marshal.json',
            'reason_fragment': 'is not a discovered ext-point-build-verify-step implementor',
        },
        'phase6_composer_injected_builtin': {
            'phase_5_steps': [],
            'phase_6_steps': ['bogus-finalize-step'],
            'phase_5_map': None,
            'phase_6_map': {},
            'marker': 'composer-injected',
            'reason_fragment': 'is missing standards file',
        },
    }

    @pytest.mark.parametrize('case_id', sorted(_NON_AUTHORED_CASES))
    def test_non_authored_message_makes_no_origin_claim(self, case_id: str):
        """A routed / composer-injected message never claims a marshal.json origin."""
        case = self._NON_AUTHORED_CASES[case_id]
        result = _mem.check_emitted_steps_resolvable(
            case['phase_5_steps'],
            case['phase_6_steps'],
            case['phase_5_map'],
            case['phase_6_map'],
        )

        assert result is not None, f'{case_id}: the step was expected to be unresolvable'
        message = result['message']
        # Anti-vacuity: the message still STATES its reason and its provenance...
        assert case['reason_fragment'] in message, (
            f'{case_id}: the reason went missing entirely, so the absence assertion '
            f'below would pass for the wrong reason — message: {message!r}'
        )
        assert case['marker'] in message, (
            f'{case_id}: expected the not-authored provenance marker {case["marker"]!r} — message: {message!r}'
        )
        # ...and makes no origin claim inside that reason.
        assert self._ORIGIN_CLAIM not in message, (
            f'{case_id}: the reason claims a marshal.json origin the wrapper '
            f'simultaneously denies — message: {message!r}'
        )

    def test_csv_fallback_branch_claims_no_origin(self):
        """The no-marshal-map branch states NO origin — it holds no map to name one from.

        ``_read_marshal_phase_step_map`` returns None when marshal.json is absent,
        the phase keys are missing, or the value is not a dict. The wrapper then
        falls back to the emitted id as the best identifier available. Naming
        marshal.json in that message would send the reader hunting a key in a
        section that may not exist — the same diagnosability harm the reason
        literals had removed, one layer up.

        The parametrized table above cannot reach this branch: every case there
        supplies a dict map for the phase under test.
        """
        result = _mem.check_emitted_steps_resolvable(['verify:perf-suite'], [], None, None)

        assert result is not None, 'the step was expected to be unresolvable'
        message = result['message']
        # Anti-vacuity: the message still states its reason...
        assert 'names an unknown canonical' in message, (
            f'the reason went missing entirely, so the absence assertions below '
            f'would pass for the wrong reason — message: {message!r}'
        )
        # ...and claims no marshal.json origin, in the reason OR the wrapper phrasing.
        assert self._ORIGIN_CLAIM not in message, f'the reason claims a marshal.json origin — message: {message!r}'
        assert 'in marshal.json is unresolvable' not in message, (
            f'the wrapper asserts a marshal.json origin on the one branch that holds '
            f'no marshal.json key map — message: {message!r}'
        )

    def test_marshal_authored_message_states_origin_only_in_the_wrapper(self):
        """Control: the authored branch keeps its origin claim — in the WRAPPER only.

        The origin did not vanish, it moved: the wrapper's own
        ``in marshal.json is unresolvable`` phrasing still names marshal.json, while
        the reason embedded after the colon no longer does.
        """
        result = _mem.check_emitted_steps_resolvable([], ['bogus-finalize-step'], None, {'bogus-finalize-step': {}})

        assert result is not None
        message = result['message']
        assert 'in marshal.json is unresolvable' in message
        assert 'is missing standards file' in message
        assert self._ORIGIN_CLAIM not in message

    def test_reason_reads_contiguously_where_the_origin_claim_used_to_sit(self):
        """The substring was REMOVED, not the clause around it TRUNCATED.

        Asserting that the step id and the reason now read contiguously is what
        distinguishes a surgical removal from a message that simply lost its tail.
        """
        result = _mem.check_emitted_steps_resolvable([], ['bogus-finalize-step'], None, {})

        assert result is not None
        assert 'step `bogus-finalize-step` is missing standards file' in result['message']

    def test_remediation_hint_survives_the_origin_claim_removal(self):
        """The ``without sweeping `marshal.json``` hint is ADVICE, not an origin claim.

        It names the likely repair, so it survives the removal; only the claim about
        where the step id CAME FROM was dropped. Pinning both halves in one test is
        what keeps a future sweep from over-reaching into the remediation text.
        """
        result = _mem.check_emitted_steps_resolvable([], ['bogus-finalize-step'], None, {})

        assert result is not None
        assert 'without sweeping `marshal.json`' in result['message']
        assert self._ORIGIN_CLAIM not in result['message']
