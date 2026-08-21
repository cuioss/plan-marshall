# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``check-artifact-consistency.py``.

Scope: the step ordering that decides whether absent metrics are a failure or merely
inconclusive — read from real discovery, and inconclusive rather than fail whenever
the ordering cannot be resolved.
"""


from __future__ import annotations

from pathlib import Path

from _check_artifact_consistency_fixtures import _check_mod


class TestMetricsGeneratedOrderingDerivedVerdict:
    """``metrics_generated``'s absence verdict is derived from step ORDERING.

    An absent ``metrics.md`` only substantiates "the producing step did not run"
    once that step has had its turn. ``default:record-metrics`` is ordered after
    ``plan-marshall:plan-retrospective``, so the historical
    ``fail`` — "metrics.md missing — record-metrics step did not run" — was a
    causal claim about a step that had not yet been reached, and was structurally
    guaranteed to be wrong on a correctly-functioning run rather than
    occasionally wrong.

    The two verdicts are pinned as a MATCHED positive/negative control pair over
    the same input (no ``metrics.md`` on disk), differing ONLY in the resolved
    ordering: producer-later must be ``inconclusive`` and producer-earlier must
    be ``fail``. Without the negative half, the repair could be satisfied by
    making the check unconditionally inconclusive.

    The orders are injected by stubbing the discovery seam the production code
    queries, so the branches are driven through the SAME resolution path the real
    run uses. ``test_orders_are_read_from_real_discovery`` keeps that stubbing
    honest: it asserts the unstubbed resolver answers from the live registry, so
    a resolver that silently returned ``None`` everywhere could not make the
    stubbed branches read as green.
    """

    #: Read from the module under test rather than restated as literals, so
    #: renaming a finalize step id moves the production check and this test
    #: together. A restated literal would leave
    #: ``test_orders_are_read_from_real_discovery`` asserting the OLD id and
    #: failing while naming the wrong cause.
    _PRODUCER = _check_mod._METRICS_PRODUCER_STEP
    _CONSUMER = _check_mod._METRICS_CONSUMER_STEP

    def _plan_dir_without_metrics(self, tmp_path: Path) -> Path:
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        return plan_dir

    def _stub_orders(self, monkeypatch, *, producer, consumer) -> list[str]:
        """Stub discovery with the given orders; return the ext-points queried.

        ``None`` for either order omits that step from the discovered records —
        the not-discoverable case, which is distinct from a discovered step whose
        order happens to be low.
        """
        queried: list[str] = []
        records = []
        if producer is not None:
            records.append({'name': self._PRODUCER, 'order': producer})
        if consumer is not None:
            records.append({'name': self._CONSUMER, 'order': consumer})

        def _fake_find_implementors(ext_point):
            queried.append(ext_point)
            return records

        monkeypatch.setattr(_check_mod, 'find_implementors', _fake_find_implementors)
        return queried

    def test_producer_ordered_later_is_inconclusive_naming_the_ordering(
        self, tmp_path, monkeypatch
    ):
        """Positive half: producer after consumer → ``inconclusive``, ordering named."""
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        queried = self._stub_orders(monkeypatch, producer=998, consumer=995)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'inconclusive', (
            'A producer ordered after the consuming retrospective has not had its '
            f'turn, so its artifact\'s absence is unmeasurable. Got: {status} — {message}'
        )
        assert self._PRODUCER in message
        assert self._CONSUMER in message
        assert '998' in message and '995' in message, (
            'The message must NAME the ordering it derived the verdict from, so a '
            f'reader can tell it apart from a genuine miss: {message}'
        )
        assert 'did not run' not in message, (
            'The retired causal claim must not survive on the inconclusive branch.'
        )
        assert queried == [_check_mod._FINALIZE_STEP_EXT_POINT] * 2, (
            'Both orders must be resolved from the finalize-step ext-point '
            f'registry the pipeline itself orders by, got {queried}'
        )

    def test_producer_ordered_earlier_is_fail(self, tmp_path, monkeypatch):
        """Negative half: producer before consumer → ``fail`` on the SAME input.

        Identical plan directory, identical absent artifact — only the resolved
        ordering differs. This is what stops the repair from being satisfied by
        an unconditionally-inconclusive check.
        """
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        self._stub_orders(monkeypatch, producer=10, consumer=995)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'fail', (
            'A producer ordered BEFORE the consumer has already had its turn, so a '
            f'missing artifact is a genuine miss. Got: {status} — {message}'
        )
        assert '10' in message and '995' in message

    def test_equal_orders_are_fail(self, tmp_path, monkeypatch):
        """Boundary: equal orders give no guarantee the producer runs later.

        Only a STRICTLY later producer substantiates "has not had its turn". At
        equal order the run sequence is unconstrained, so the check must not
        excuse the absence — it falls to the measured branch.
        """
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        self._stub_orders(monkeypatch, producer=995, consumer=995)

        status, _ = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'fail'

    def test_unresolvable_ordering_is_inconclusive_not_fail(self, tmp_path, monkeypatch):
        """An ordering that cannot be resolved is itself an unmeasurable input."""
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        self._stub_orders(monkeypatch, producer=None, consumer=995)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'inconclusive', (
            'Whether the producer has had its turn is unknown when its order does '
            f'not resolve — a fail would be a confident claim from no input: {message}'
        )
        assert 'could not be resolved' in message

    def test_discovery_failure_is_inconclusive_not_a_crash(self, tmp_path, monkeypatch):
        """A raising registry degrades to unmeasurable, never an uncaught error.

        The consistency gate is fail-closed throughout: a discovery blow-up must
        surface as a structured verdict, not abort every remaining check.
        """
        plan_dir = self._plan_dir_without_metrics(tmp_path)

        def _boom(ext_point):
            raise RuntimeError('registry unavailable')

        monkeypatch.setattr(_check_mod, 'find_implementors', _boom)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'inconclusive'
        assert 'could not be resolved' in message

    def test_present_metrics_passes_whatever_the_ordering(self, tmp_path, monkeypatch):
        """Control: ordering only governs the ABSENCE branch, never presence."""
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        self._stub_orders(monkeypatch, producer=998, consumer=995)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'pass'
        assert message == 'metrics.md present'

    def test_orders_are_read_from_real_discovery(self):
        """Non-vacuity: the UNSTUBBED resolver answers from the live registry.

        Every branch above stubs the seam, so all of them would still read as
        green against a resolver that always returned ``None``. This asserts the
        real one resolves both steps to integers off the discovered records —
        which is also what makes the production verdict ordering-derived rather
        than literal-derived.
        """
        producer_order = _check_mod._resolve_step_order(self._PRODUCER)
        consumer_order = _check_mod._resolve_step_order(self._CONSUMER)

        assert isinstance(producer_order, int), (
            f'{self._PRODUCER} must be discoverable with an integer order; '
            'an unresolvable producer would make every stubbed branch above vacuous.'
        )
        assert isinstance(consumer_order, int), (
            f'{self._CONSUMER} must be discoverable with an integer order.'
        )

    def test_unknown_step_resolves_to_none(self):
        """The resolver reports not-discoverable rather than inventing a position."""
        assert _check_mod._resolve_step_order('default:no-such-finalize-step') is None
