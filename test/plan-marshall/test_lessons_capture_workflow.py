#!/usr/bin/env python3
"""Regression tests for the dispatcher-level lessons-capture Signal Gate (B4).

The deterministic three-signal Signal Gate (pending Q-Gate findings,
``automated-review`` step outcome, script-failure clusters) was relocated
from the body of
``marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md``
into the phase-6-finalize SKILL.md dispatcher (Step 3 item 4b). When all
three signal counts are zero, the dispatcher marks the step skipped
WITHOUT dispatching the LLM envelope, eliminating the spawn cost. When at
least one signal is non-zero, the dispatcher forwards the three observed
counts to the LLM body as runtime inputs so the body never re-issues the
signal queries.

These tests assert the structural shape of both endpoints:

* The dispatcher-level gate in ``phase-6-finalize/SKILL.md`` names all
  three signal sources, exposes the three-zero short-circuit, marks the
  step ``--outcome skipped`` with the canonical display-detail, and
  forwards the three count fields on dispatch when at least one signal
  is non-zero.
* The workflow body in ``lessons-capture.md`` no longer carries the
  Signal Gate section (the early-return guard, the three signal-source
  queries, the skip branch). The body's intro prose explicitly names the
  dispatcher-level move and documents the three runtime-input fields.
* The body's Mark Step Complete section no longer carries a Branch C
  example for the skipped outcome — that responsibility now sits in the
  dispatcher.

These assertions are deliberately structural — they catch drift between
the dispatcher narrative and the workflow body's behavioural contract
without re-implementing the gate logic in Python.
"""

from pathlib import Path

_BUNDLE_ROOT = (
    Path(__file__).parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
)

_WORKFLOW_PATH = _BUNDLE_ROOT / 'workflow' / 'lessons-capture.md'
_DISPATCHER_PATH = _BUNDLE_ROOT / 'SKILL.md'


def _read_workflow() -> str:
    """Read the workflow body once per test for substring assertions."""
    return _WORKFLOW_PATH.read_text(encoding='utf-8')


def _read_dispatcher() -> str:
    """Read the phase-6-finalize SKILL.md dispatcher once per test."""
    return _DISPATCHER_PATH.read_text(encoding='utf-8')


class TestDispatcherSignalGateStructure:
    """Structural assertions on the dispatcher-level Signal Gate in
    ``phase-6-finalize/SKILL.md`` Step 3 item 4b."""

    def test_dispatcher_signal_gate_section_present(self) -> None:
        """The dispatcher MUST declare a Lessons-capture Signal Gate
        sub-step so the manifest-driven FOR loop locates it."""
        body = _read_dispatcher()
        assert 'Lessons-capture Signal Gate' in body, (
            'phase-6-finalize/SKILL.md must declare a '
            '"Lessons-capture Signal Gate" sub-step inside Step 3 '
            'item 4b'
        )

    def test_dispatcher_gate_runs_before_dispatch(self) -> None:
        """The gate MUST sit BEFORE item 5 (Dispatch with timeout
        wrapper) so the envelope spawn cost is avoided on the skip
        branch."""
        body = _read_dispatcher()
        gate_idx = body.find('Lessons-capture Signal Gate')
        dispatch_idx = body.find('5. Dispatch with timeout wrapper')
        assert gate_idx != -1 and dispatch_idx != -1, (
            'phase-6-finalize/SKILL.md must contain both the '
            'Lessons-capture Signal Gate and the Step 3 item 5 '
            'dispatch wrapper'
        )
        assert gate_idx < dispatch_idx, (
            'Lessons-capture Signal Gate must precede item 5 '
            'so the dispatch is skipped when all three signals are zero'
        )


class TestDispatcherGateSourcesNamed:
    """The dispatcher Signal Gate MUST explicitly name all three signal
    sources so the manifest narrative documents which counts to read."""

    def test_qgate_findings_signal_named(self) -> None:
        """Signal 1 — Q-Gate findings (pending OR resolved-in-run) via
        per-phase ``manage-findings qgate list --phase {phase}
        --resolution {value}`` invocations whose ``filtered_count`` values
        are summed.

        Reconciles the pre-existing test drift: the live SKILL.md prose
        reads ``filtered_count`` (NOT ``total_count``) for the per-phase
        counts — the call filters by ``--resolution``, so the matching
        count lives in ``filtered_count``. This assertion now matches the
        live contract.
        """
        body = _read_dispatcher()
        for phase in ('2-refine', '3-outline', '4-plan', '5-execute', '6-finalize'):
            assert phase in body, (
                f'Dispatcher Signal Gate must enumerate phase {phase} '
                f'in its per-phase Q-Gate findings loop'
            )
        assert 'qgate list' in body and '--resolution pending' in body, (
            'Dispatcher Signal Gate must invoke '
            '"manage-findings qgate list --resolution pending"'
        )
        assert 'filtered_count' in body, (
            'Dispatcher Signal Gate must read the "filtered_count" field '
            '(NOT "total_count") from each per-phase manage-findings '
            'qgate list TOON output — the call filters by --resolution'
        )

    def test_qgate_resolved_in_run_signal_named(self) -> None:
        """Signal 1 symmetric facet — the dispatcher Signal Gate MUST also
        count Q-Gate findings RESOLVED in-run (the four non-pending
        resolutions) so Signal 1 fires on either pending OR
        resolved-in-run findings, symmetric with Signals 2 and 3."""
        body = _read_dispatcher()
        for resolution in ('fixed', 'suppressed', 'accepted', 'taken_into_account'):
            assert f'--resolution {resolution}' in body, (
                f'Dispatcher Signal Gate must query the non-pending '
                f'resolution "{resolution}" to count Q-Gate findings '
                f'resolved in-run'
            )
        assert 'resolved-in-run' in body or 'resolved_subtotal' in body, (
            'Dispatcher Signal Gate Signal-1 prose must name the '
            'resolved-in-run facet (e.g. "resolved-in-run" / '
            '"resolved_subtotal") as an additional positive trigger'
        )

    def test_automated_review_signal_named(self) -> None:
        """Signal 2 — ``automated-review`` step outcome via
        ``manage-status read``."""
        body = _read_dispatcher()
        assert 'automated-review' in body, (
            'Dispatcher Signal Gate must name the "automated-review" '
            'step as a signal source'
        )
        assert 'manage-status' in body and 'read' in body, (
            'Dispatcher Signal Gate must read the automated-review '
            'step outcome via manage-status read'
        )

    def test_script_failure_clusters_signal_named(self) -> None:
        """Signal 3 — script-failure clusters via
        ``manage-logging read --type work`` scanning ``[FAILED]``."""
        body = _read_dispatcher()
        assert 'manage-logging' in body and '--type work' in body, (
            'Dispatcher Signal Gate must read the work log via '
            'manage-logging read --type work'
        )
        assert '[FAILED]' in body, (
            'Dispatcher Signal Gate must scan for "[FAILED]" markers '
            'in the work log to identify script-failure clusters'
        )


class TestRemediatedInRunSignalsNamed:
    """Each of the three signals MUST count remediated-in-run evidence,
    not only outstanding / loud-failure evidence. These assertions verify
    the reworked prose names the resolved-in-run source/field/marker per
    signal so the gate does NOT short-circuit to ``skipped`` on a run that
    detected-and-remediated a defect (the highest-value lesson class)."""

    def test_signal_2_names_resolution_fixed_pr_comment(self) -> None:
        """Signal 2 (automated-review) MUST count fixed-in-run review-bot
        findings via ``manage-findings list --type pr-comment
        --resolution fixed``."""
        body = _read_dispatcher()
        assert 'manage-findings' in body and 'list' in body, (
            'Signal-2 prose must name a manage-findings list invocation '
            'to count fixed-in-run review-bot findings'
        )
        assert '--type pr-comment' in body, (
            'Signal-2 prose must name the pr-comment finding type token'
        )
        assert '--resolution fixed' in body, (
            'Signal-2 prose must name "--resolution fixed" so the '
            'remediated-in-run review-bot findings fire the signal'
        )

    def test_signal_3_names_all_three_marker_classes(self) -> None:
        """Signal 3 (script-failures) MUST bucket all three marker classes
        — ``[FAILED]``, ``[ERROR] ... script_failure``, and
        ``voluntary_checkpoint → error`` — by distinct failing notation."""
        body = _read_dispatcher()
        assert '[FAILED]' in body, (
            'Signal-3 prose must preserve the "[FAILED]" marker class'
        )
        assert 'script_failure' in body, (
            'Signal-3 prose must name the "[ERROR] ... script_failure" '
            'marker class so argparse-rejection / internal-error lines '
            'are counted'
        )
        assert 'voluntary_checkpoint' in body and 'error' in body, (
            'Signal-3 prose must name the "voluntary_checkpoint → error" '
            'reclassification marker class (dispatch-boundary no-progress)'
        )
        assert 'distinct' in body and 'notation' in body, (
            'Signal-3 prose must state the three marker classes are '
            'bucketed by distinct failing notation into signal_3_count'
        )


class TestDispatcherSkipBranch:
    """The dispatcher's all-zero skip branch MUST emit the canonical
    ``mark-step-done`` call directly so the phase_steps_complete
    invariant is satisfied even when no LLM dispatch fires."""

    _EXPECTED_DETAIL = 'no lesson-bearing signals'

    def test_skip_branch_uses_skipped_outcome(self) -> None:
        """The dispatcher MUST mark lessons-capture with
        ``--outcome skipped`` on the three-zero branch."""
        body = _read_dispatcher()
        assert '--outcome skipped' in body, (
            'Dispatcher Signal Gate skip branch must invoke '
            'mark-step-done with "--outcome skipped"'
        )

    def test_skip_branch_uses_canonical_display_detail(self) -> None:
        """The skip branch MUST carry the exact display-detail string
        ``"no lesson-bearing signals"`` — downstream consumers may grep
        for this token to identify a dispatcher-level Signal Gate
        short-circuit."""
        body = _read_dispatcher()
        token = f'--display-detail "{self._EXPECTED_DETAIL}"'
        assert token in body, (
            'Dispatcher Signal Gate skip branch must carry the '
            'canonical display-detail string ' + repr(self._EXPECTED_DETAIL)
        )

    def test_skip_branch_logs_decision(self) -> None:
        """The skip branch MUST log a decision-level entry naming all
        three signal-count values for forensic reconstruction."""
        body = _read_dispatcher()
        marker = '(plan-marshall:phase-6-finalize:lessons-capture)'
        assert marker in body, (
            'Dispatcher Signal Gate skip branch must emit a decision '
            'log line under the caller prefix ' + repr(marker)
        )


class TestDispatcherForwardsGateCounts:
    """When at least one signal is non-zero, the dispatcher MUST forward
    the three observed counts on the prompt body so the LLM workflow
    never re-issues the signal queries."""

    def test_forwarded_count_field_names_present(self) -> None:
        """The dispatcher MUST name the three runtime-input fields the
        body consumes."""
        body = _read_dispatcher()
        for field in (
            'signal_qgate_pending_count',
            'signal_automated_review_count',
            'signal_script_failure_clusters_count',
        ):
            assert field in body, (
                f'Dispatcher Signal Gate must forward the runtime-input '
                f'field {field!r} when dispatching the workflow body'
            )


class TestBodyNoLongerCarriesGate:
    """The workflow body MUST NOT carry the Signal Gate section (the
    early-return guard, the three signal-source queries, the skip branch
    mark-step-done call). That responsibility now sits in the dispatcher."""

    def test_body_does_not_declare_signal_gate_section(self) -> None:
        """The workflow body MUST NOT declare a top-level Signal Gate
        section — the dispatcher owns the gate."""
        body = _read_workflow()
        assert '### Signal Gate' not in body, (
            'lessons-capture.md must NOT declare a "### Signal Gate" '
            'section — the gate was moved into the dispatcher (B4)'
        )

    def test_body_does_not_carry_signal_query_calls(self) -> None:
        """The body MUST NOT re-issue the three signal-source queries
        the dispatcher has already evaluated. Catch this by asserting
        the body does NOT carry a bash invocation of ``qgate list`` or
        ``--type work``. Narrative mentions (e.g. "the body MUST NOT
        re-issue X, Y, Z") are permitted and expected."""
        body = _read_workflow()
        for line in body.splitlines():
            if 'execute-script.py' in line and 'qgate list' in line:
                msg = (
                    'lessons-capture.md must NOT carry a bash '
                    'invocation of "manage-findings qgate list" — the '
                    f'dispatcher already paid that cost (offending '
                    f'line: {line!r})'
                )
                raise AssertionError(msg)
            if 'execute-script.py' in line and '--type work' in line:
                msg = (
                    'lessons-capture.md must NOT carry a bash '
                    'invocation of "manage-logging read --type work" — '
                    f'the dispatcher already paid that cost (offending '
                    f'line: {line!r})'
                )
                raise AssertionError(msg)

    def test_body_does_not_emit_skip_outcome_directly(self) -> None:
        """The body MUST NOT emit the ``--outcome skipped`` shape
        itself — Branch C of Mark Step Complete now states it is
        emitted by the dispatcher and NOT by this body."""
        body = _read_workflow()
        # The body MAY mention the skip outcome in narrative prose (to
        # explain WHY this body never emits it) but MUST NOT carry an
        # actual bash invocation of mark-step-done with --outcome skipped.
        # Detect bash invocations by looking for the canonical script
        # prefix on the same line as the flag.
        for line in body.splitlines():
            if '--outcome skipped' in line and 'mark-step-done' in line:
                # This indicates a bash invocation, which is forbidden.
                # Narrative mentions (where mark-step-done is in a
                # separate sentence or as inline code) are allowed.
                if 'execute-script.py' in line:
                    msg = (
                        'lessons-capture.md must NOT carry a bash '
                        'invocation of "mark-step-done --outcome skipped" — '
                        f'the skipped recording is now the dispatcher\'s '
                        f'responsibility (offending line: {line!r})'
                    )
                    raise AssertionError(msg)
        # Also assert Branch C explicitly explains the delegation.
        assert 'NOT emitted by this body' in body, (
            'lessons-capture.md Branch C must explicitly state "NOT '
            'emitted by this body" so future readers know the skipped '
            'outcome is the dispatcher\'s responsibility'
        )


class TestBodyIntroNamesDispatcherMove:
    """The body's intro prose MUST explicitly name the B4 dispatcher-level
    Signal Gate move and document the three runtime-input fields."""

    def test_intro_names_dispatcher_level_precondition(self) -> None:
        """The intro MUST reference the dispatcher-level precondition so
        future readers know where the gate lives."""
        body = _read_workflow()
        assert 'Dispatcher-level Signal Gate precondition' in body or (
            'Dispatcher' in body and 'Signal Gate' in body
        ), (
            'lessons-capture.md intro must reference the '
            'dispatcher-level Signal Gate precondition (B4)'
        )

    def test_intro_names_runtime_input_fields(self) -> None:
        """The body MUST document the three runtime-input field names
        it consumes from the dispatcher."""
        body = _read_workflow()
        for field in (
            'signal_qgate_pending_count',
            'signal_automated_review_count',
            'signal_script_failure_clusters_count',
        ):
            assert field in body, (
                f'lessons-capture.md intro must document the runtime '
                f'input field {field!r}'
            )

    def test_signal_automated_review_field_documents_remediated_trigger(self) -> None:
        """The ``signal_automated_review_count`` field description MUST
        document the remediated-in-run trigger (resolution=fixed
        pr-comment findings), not only the outstanding-state triggers."""
        body = _read_workflow()
        assert '--resolution fixed' in body or 'resolution=fixed' in body, (
            'lessons-capture.md signal_automated_review_count field '
            'description must document the remediated-in-run trigger '
            '(review-bot findings with resolution=fixed)'
        )
        assert 'remediated' in body, (
            'lessons-capture.md signal_automated_review_count field '
            'description must state the field fires on remediated-in-run '
            'review-bot findings'
        )
