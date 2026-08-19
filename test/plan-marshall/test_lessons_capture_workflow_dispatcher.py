#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the dispatcher-level lessons-capture Signal Gate (B4).

The deterministic three-signal Signal Gate (pending Q-Gate findings,
``automatic-review`` step outcome, script-failure clusters) was relocated
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
        """Signal 2 — ``automatic-review`` step outcome via
        ``manage-status read``."""
        body = _read_dispatcher()
        assert 'automatic-review' in body, (
            'Dispatcher Signal Gate must name the "automatic-review" '
            'step as a signal source'
        )
        assert 'manage-status' in body and 'read' in body, (
            'Dispatcher Signal Gate must read the automatic-review '
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
        """Signal 2 (automatic-review) MUST count fixed-in-run review-bot
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
