# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_compose_execution_tier.py: stamp."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_compose_execution_tier_fixtures import (
    Any,
    Path,
    SimpleNamespace,
    _arch_build,
    _clear_arch_resolve_cache,
    _core,
    _fake_resolver,
    _mem,
    _stamp,
    run_config,
)


class TestStampTotalityAndOrdering:
    """The record list is total over ``verification_steps`` and preserves order."""

    def test_one_record_per_step_in_order(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        steps = ['verify:quality-gate', 'verify:module-tests', 'verify:coverage']
        records = _stamp('X', steps)
        assert [r['step_id'] for r in records] == steps
        assert len(records) == len(steps)

    def test_every_record_has_step_id_and_tier(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        records = _stamp('X', ['verify:quality-gate', 'verify:module-tests'])
        for rec in records:
            assert set(rec.keys()) == {'step_id', 'tier'}
            assert rec['tier'] in ('per_task', 'orchestrator')

    def test_empty_verification_steps_yields_empty_list(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        assert _stamp('X', []) == []


class TestStampTotalityInvariantLock:
    """Regression lock: the stamp is TOTAL over ``verification_steps``.

    Totality is a property of ONE compose: the stamp is composed over the full
    step list in a single pass, so the persisted record list has no gaps — every
    phase-5 dispatch that reads that manifest sees a resolved tier for every step,
    never an un-stamped entry.

    Totality is NOT a durability claim. It does not assert that the recorded tier
    still describes execute-time reality: the tier derives from the adaptive
    learned build duration, so a ceiling-adjacent step's true tier moves between
    compose and execute (see ``TestStampReflectsALiveResolvedCeilingVerdict`` and
    ``TestStampIsASnapshotNotADurableFact``). What keeps a long build off a leaf
    is the leaf's LIVE re-resolve before running each step, not the completeness of
    this record list. The guarantees locked here, over a list mixing
    canonical-verify steps and an external ``project:`` / ``bundle:skill`` step:

    * exactly one record per input step, in input order (totality + ordering);
    * every record carries a resolved, non-empty tier (``per_task`` |
      ``orchestrator``) — never absent/empty;
    * an orchestrator-tier canonical (``verify:module-tests`` / ``verify:coverage``)
      is stamped ``orchestrator``;
    * an external / unresolvable step defaults to ``per_task``.
    """

    _MIXED_STEPS = [
        'default:verify:quality-gate',
        'verify:module-tests',
        'verify:coverage',
        'project:finalize-step-plugin-doctor',
        'my-bundle:my-verify-step',
    ]

    def test_stamp_is_total_over_mixed_step_list(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)

        records = _stamp('mixed-plan', self._MIXED_STEPS)

        # Totality + ordering: one record per input step, in list order.
        assert [r['step_id'] for r in records] == self._MIXED_STEPS
        assert len(records) == len(self._MIXED_STEPS)
        # Every record carries a resolved, non-empty tier.
        for rec in records:
            assert set(rec.keys()) == {'step_id', 'tier'}
            assert rec['tier'] in ('per_task', 'orchestrator')
            assert rec['tier']  # non-empty
        # Orchestrator-tier canonicals stamp orchestrator; external/unresolvable
        # steps default to per_task.
        tier_by_id = {r['step_id']: r['tier'] for r in records}
        assert tier_by_id['default:verify:quality-gate'] == 'per_task'
        assert tier_by_id['verify:module-tests'] == 'orchestrator'
        assert tier_by_id['verify:coverage'] == 'orchestrator'
        assert tier_by_id['project:finalize-step-plugin-doctor'] == 'per_task'
        assert tier_by_id['my-bundle:my-verify-step'] == 'per_task'

    def test_stamp_is_dispatch_invariant_composed_once_over_full_list(self, monkeypatch):
        """The stamp is a pure function of (step list, resolver) — re-running it with
        the SAME resolver yields a byte-identical total record list, so nothing in the
        stamping pass itself introduces per-dispatch asymmetry. Purity over a fixed
        resolver is all this pins; when the underlying resolve verdict changes the
        stamp changes with it, which is exactly what
        ``TestStampIsASnapshotNotADurableFact`` asserts."""
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)

        first = _stamp('mixed-plan', self._MIXED_STEPS)
        second = _stamp('mixed-plan', self._MIXED_STEPS)

        assert first == second
        # No step is left without a tier across either read.
        assert all(r['tier'] for r in first)
        assert all(r['tier'] for r in second)


class TestStampReflectsALiveResolvedCeilingVerdict:
    """The ceiling boundary, driven end-to-end by the PRODUCTION resolve producers.

    The regression this class exists for: a whole-tree step that resolves
    ``orchestrator`` / ``exceeds_bash_ceiling`` MUST NOT be stamped ``per_task`` in a
    form the leaf is instructed to trust inline. Every asserted field is produced by
    ``manage-architecture``'s real ``_classify_build_executable`` /
    ``_lookup_bash_timeout`` / ``_compute_execution_tier_fields``, and the resolve
    TOON the composer parses is serialized from those fields with the production
    ``serialize_toon`` — no hand-authored resolve-shaped dict literal appears
    anywhere in this class, so the four-field contract cannot drift away from its
    consumer without failing here.
    """

    # The literal shape ``architecture resolve --command coverage`` emits for this
    # repo's whole-tree coverage canonical. Fed to the production classifier rather
    # than being decomposed by hand.
    _RESOLVED_EXECUTABLE = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "coverage"'
    )

    # A MAVEN executable for the crossing test below. The engine is incidental
    # now that the tier follows the measurement rather than the floor — the
    # crossing is seeded on a MEASURED low value and re-seeded on a MEASURED
    # high one, which is the honest crossing and works for any engine.
    _MAVEN_RESOLVED_EXECUTABLE = (
        'python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "test -pl core"'
    )

    # A cheap learned duration whose buffered bound stays well inside the
    # ceiling — the pre-crossing seed.
    _WELL_BELOW_CEILING_SECONDS = 60

    # A learned duration far above the ceiling — the seed for the crossing test.
    # Its exact value is never asserted; only which side of the ceiling the
    # production arithmetic lands on.
    _WELL_ABOVE_CEILING_SECONDS = 3600

    @staticmethod
    def _production_lookup() -> tuple[int, bool]:
        """Run the production classify → lookup legs for the whole-tree coverage canonical."""
        classified = _arch_build._classify_build_executable(
            TestStampReflectsALiveResolvedCeilingVerdict._RESOLVED_EXECUTABLE
        )
        assert classified is not None, 'production classifier rejected a real resolved executable'
        tool_name, command_args = classified
        lookup = _arch_build._lookup_bash_timeout(tool_name, command_args, '.')
        assert lookup is not None, 'production timeout lookup returned nothing'
        bash_timeout, measured = lookup
        assert isinstance(bash_timeout, int), 'production timeout lookup returned no int'
        assert isinstance(measured, bool), 'production timeout lookup returned no measured-ness'
        return bash_timeout, measured

    @staticmethod
    def _production_tier_fields() -> dict[str, Any]:
        """Run the full production producer chain for the whole-tree coverage canonical."""
        bash_timeout, measured = TestStampReflectsALiveResolvedCeilingVerdict._production_lookup()
        fields: dict[str, Any] = _arch_build._compute_execution_tier_fields(bash_timeout, measured)
        return fields

    @staticmethod
    def _resolve_toon_for(fields: dict[str, Any]) -> str:
        """Serialize a status-success resolve TOON carrying the production fields."""
        toon: str = _core.serialize_toon({'status': 'success', **fields})
        return toon

    @staticmethod
    def _patch_resolve_with(monkeypatch, toon: str) -> None:
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        monkeypatch.setattr(_mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon))

    def test_production_producers_emit_the_four_field_envelope(self):
        """The producer chain yields exactly the four fields the composer consumes.

        The derived fields are asserted against the MEASURED-vs-UNMEASURED
        contract, not against the ceiling alone: ``exceeds_bash_ceiling`` is a
        pure ceiling comparison, while ``execution_tier`` is ``per_task`` only
        when the key is measured AND the stamp fits. Re-deriving both from the
        same ``(stamp, measured)`` pair the production lookup returned is what
        keeps this case from re-pinning the floor-driven derivation.
        """
        bash_timeout, measured = self._production_lookup()
        fields = _arch_build._compute_execution_tier_fields(bash_timeout, measured)

        assert set(fields) == {
            'bash_timeout_seconds',
            'exceeds_bash_ceiling',
            'execution_tier',
            'hint',
        }
        assert isinstance(fields['bash_timeout_seconds'], int)
        assert fields['execution_tier'] in ('per_task', 'orchestrator')
        expected_exceeds = fields['bash_timeout_seconds'] > _arch_build.HARNESS_BASH_CEILING_SECONDS
        assert fields['exceeds_bash_ceiling'] is expected_exceeds
        assert fields['execution_tier'] == ('per_task' if (measured and not expected_exceeds) else 'orchestrator')

    def test_ceiling_boundary_is_strictly_above(self):
        """At the ceiling → per_task; one second above it → orchestrator.

        Both envelopes come from the production ``_compute_execution_tier_fields``
        and the production ``HARNESS_BASH_CEILING_SECONDS`` constant, so a threshold
        change moves this assertion with it instead of silently invalidating it.
        Both are seeded ``measured=True`` — the ceiling boundary is only OBSERVABLE
        on the measured branch, since an unmeasured command is ``orchestrator``
        on both sides of it.
        """
        ceiling = _arch_build.HARNESS_BASH_CEILING_SECONDS

        at_ceiling = _arch_build._compute_execution_tier_fields(ceiling, True)
        above_ceiling = _arch_build._compute_execution_tier_fields(ceiling + 1, True)

        assert at_ceiling['exceeds_bash_ceiling'] is False
        assert at_ceiling['execution_tier'] == 'per_task'
        assert above_ceiling['exceeds_bash_ceiling'] is True
        assert above_ceiling['execution_tier'] == 'orchestrator'

    def test_unmeasured_is_orchestrator_on_both_sides_of_the_ceiling(self):
        """The fail-closed branch is ceiling-insensitive — that is the whole point.

        Complements the boundary case above: with ``measured=False`` the tier is
        ``orchestrator`` at AND below the ceiling, while ``exceeds_bash_ceiling``
        keeps reporting the literal comparison. This is the one branch where the
        two fields deliberately decouple, and pinning it here is what stops a
        future refactor from re-coupling them.
        """
        ceiling = _arch_build.HARNESS_BASH_CEILING_SECONDS

        below = _arch_build._compute_execution_tier_fields(ceiling - 100, False)
        above = _arch_build._compute_execution_tier_fields(ceiling + 1, False)

        assert below['exceeds_bash_ceiling'] is False
        assert below['execution_tier'] == 'orchestrator'
        assert below['hint'] == _arch_build._HINT_UNMEASURED
        assert above['exceeds_bash_ceiling'] is True
        assert above['execution_tier'] == 'orchestrator'
        assert above['hint'] == _arch_build._HINT_ORCHESTRATOR

    def test_above_ceiling_resolve_is_never_stamped_per_task(self, monkeypatch):
        """THE regression: an orchestrator-tier resolve stamps orchestrator, never per_task."""
        fields = _arch_build._compute_execution_tier_fields(_arch_build.HARNESS_BASH_CEILING_SECONDS + 1, True)
        assert fields['execution_tier'] == 'orchestrator'
        self._patch_resolve_with(monkeypatch, self._resolve_toon_for(fields))

        records = _stamp('plan-39-above-ceiling-stamp', ['verify:coverage'])

        assert records == [{'step_id': 'verify:coverage', 'tier': 'orchestrator'}]

    def test_at_ceiling_resolve_stamps_per_task(self, monkeypatch):
        """The other side of the boundary, through the same production envelope."""
        fields = _arch_build._compute_execution_tier_fields(_arch_build.HARNESS_BASH_CEILING_SECONDS, True)
        assert fields['execution_tier'] == 'per_task'
        self._patch_resolve_with(monkeypatch, self._resolve_toon_for(fields))

        records = _stamp('plan-39-at-ceiling-stamp', ['verify:coverage'])

        assert records == [{'step_id': 'verify:coverage', 'tier': 'per_task'}]

    def test_learned_duration_crossing_the_ceiling_flips_the_resolved_tier(self):
        """The volatility that makes the stamp advisory, pinned against production code.

        Seeds a MEASURED cheap duration for a build command, reads the production
        tier, then records an observed duration far above the ceiling through the
        production ``run_config.timeout_set`` writer and reads the tier again. The
        verdict flips ``per_task`` → ``orchestrator`` with no code change — exactly
        the compose-vs-execute divergence this plan diagnosed. The autouse
        ``_plan_base_dir_sandbox`` fixture redirects the run-config store into a
        per-test tmp sandbox, so neither seed touches the real learned durations.

        BOTH legs are measured. That is the substantive change: the crossing is now
        a duration crossing on the measured branch, which is the honest one and
        works for ANY engine — the pre-fix version had to be seeded specifically
        against Maven because the floor decided the tier and no pyproject command
        could ever start ``per_task``. Anchoring the pre-crossing leg on the
        unmeasured default would now assert ``orchestrator → orchestrator``, i.e.
        nothing about a crossing at all.
        """
        classified = _arch_build._classify_build_executable(self._MAVEN_RESOLVED_EXECUTABLE)
        assert classified is not None
        tool_name, command_args = classified
        config = _arch_build._load_build_config(tool_name)
        assert config is not None, 'production build config did not load'
        from _build_execute_factory import compute_command_key

        command_key = compute_command_key(config, command_args)

        run_config.timeout_set(command_key, self._WELL_BELOW_CEILING_SECONDS)
        stamp, measured = _arch_build._lookup_bash_timeout(tool_name, command_args, '.')
        assert measured is True, 'the cheap seed must make the key read as measured'
        before = _arch_build._compute_execution_tier_fields(stamp, measured)
        assert before['execution_tier'] == 'per_task', (
            'a cheap MEASURED command must start inside the Bash ceiling so the crossing stays observable'
        )

        run_config.timeout_set(command_key, self._WELL_ABOVE_CEILING_SECONDS)

        stamp, measured = _arch_build._lookup_bash_timeout(tool_name, command_args, '.')
        assert measured is True
        after = _arch_build._compute_execution_tier_fields(stamp, measured)
        assert after['execution_tier'] == 'orchestrator'
        assert after['bash_timeout_seconds'] > before['bash_timeout_seconds']
