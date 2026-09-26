# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_compose_execution_tier_fixtures import (
    Path,
    _clear_arch_resolve_cache,
    _mem,
    json,
)


class TestBuildPhaseCanonicalCarveOut:
    """Orchestrator-tier ``compile`` / ``test-compile`` are KEPT with the task, not routed.

    ``derive-verification`` legitimately emits ``compile`` and ``test-compile``
    (canonical build commands with NO phase-5 verify gate). When such a command
    resolves ``orchestrator`` tier (the fail-closed default for any unmeasured
    command), the OLD routing generalized it to ``verify:compile`` /
    ``verify:test-compile`` and appended it to ``phase_5.verification_steps`` — an
    unresolvable step that failed the WHOLE compose with ``unresolvable_step``.

    The carve-out keeps such a command with the task (the per_task fallback the
    leaf re-resolves live) instead of routing it to a nonexistent gate. The
    resolvability probe is REAL (``_verify_canonicals_universe`` over the tree) —
    only ``_resolve_command_tier`` / ``get_plan_dir`` / ``_emit_decision_log`` are
    patched — so the test exercises the same gate the composer uses.

    Matched-pair control (D4): the routable half (``module-tests`` via the fast
    path; a resolvable gate canonical via the generalization) and the custom-verb
    half (``perf-suite`` still routes and fails loud) guard the carve-out from
    being over-broad.
    """

    _COMPILE_CMD = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        "run --command-args 'compile plan-marshall'"
    )
    _TEST_COMPILE_CMD = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        "run --command-args 'test-compile plan-marshall'"
    )
    _MODULE_TESTS_CMD = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        "run --command-args 'module-tests plan-marshall'"
    )
    _CUSTOM_VERB_CMD = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        "run --command-args 'perf-suite plan-marshall'"
    )

    @staticmethod
    def _write_task(tasks_dir: Path, number: int, commands: list) -> Path:
        tasks_dir.mkdir(parents=True, exist_ok=True)
        task_path = tasks_dir / f'TASK-{number:03d}.json'
        task_path.write_text(
            json.dumps({'number': number, 'verification': {'commands': commands}}),
            encoding='utf-8',
        )
        return task_path

    @staticmethod
    def _patch_routing(monkeypatch, tmp_path: Path) -> list[str]:
        """All commands classify ``orchestrator``; real ``_check_step_resolvable`` runs."""
        captured: list[str] = []
        monkeypatch.setattr(_mem, 'get_plan_dir', lambda pid: tmp_path)
        monkeypatch.setattr(_mem, '_resolve_command_tier', lambda cmd, pid: {'execution_tier': 'orchestrator'})
        monkeypatch.setattr(_mem, '_emit_decision_log', lambda pid, msg: captured.append(msg))
        return captured

    def test_compile_kept_with_task_not_routed(self, monkeypatch, tmp_path):
        """An orchestrator-tier ``compile`` command stays in the task; no phase-5 step."""
        task_path = self._write_task(tmp_path / 'tasks', 1, [self._COMPILE_CMD])
        captured = self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)
        _mem._persist_task_rewrites(pending)

        assert mutated == 0
        assert pending == []
        assert body['phase_5']['verification_steps'] == []
        kept = json.loads(task_path.read_text(encoding='utf-8'))
        assert kept['verification']['commands'] == [self._COMPILE_CMD]
        # Provenance: the keep decision names the verb and the absent gate.
        assert any("'compile'" in msg and 'no phase-5 verify gate' in msg for msg in captured)

    def test_test_compile_kept_with_task_not_routed(self, monkeypatch, tmp_path):
        """An orchestrator-tier ``test-compile`` command stays in the task; no phase-5 step."""
        task_path = self._write_task(tmp_path / 'tasks', 1, [self._TEST_COMPILE_CMD])
        captured = self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)
        _mem._persist_task_rewrites(pending)

        assert mutated == 0
        assert body['phase_5']['verification_steps'] == []
        kept = json.loads(task_path.read_text(encoding='utf-8'))
        assert kept['verification']['commands'] == [self._TEST_COMPILE_CMD]
        assert any("'test-compile'" in msg and 'no phase-5 verify gate' in msg for msg in captured)

    def test_module_tests_still_routes(self, monkeypatch, tmp_path):
        """Routable control: ``module-tests`` still hoists to ``verify:module-tests``."""
        self._write_task(tmp_path / 'tasks', 1, [self._MODULE_TESTS_CMD])
        self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)
        _mem._persist_task_rewrites(pending)

        assert mutated == 1
        assert body['phase_5']['verification_steps'] == ['verify:module-tests']

    def test_custom_verb_still_routes_and_fails_loud(self, monkeypatch, tmp_path):
        """Control: a non-canonical custom verb still routes to ``verify:{verb}``.

        The carve-out is restricted to KNOWN canonical commands, so ``perf-suite``
        (not in the vocabulary registry) keeps the pre-existing generalize-and-drop
        behaviour rather than being swept up as "kept with the task".
        """
        task_path = self._write_task(tmp_path / 'tasks', 1, [self._CUSTOM_VERB_CMD])
        self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)
        _mem._persist_task_rewrites(pending)

        assert mutated == 1
        assert body['phase_5']['verification_steps'] == ['verify:perf-suite']
        rewritten = json.loads(task_path.read_text(encoding='utf-8'))
        assert rewritten['verification']['commands'] == []

    def test_mixed_task_composes_without_unresolvable_step(self, monkeypatch, tmp_path):
        """A task carrying both ``compile`` and ``module-tests`` composes cleanly.

        ``module-tests`` hoists to ``verify:module-tests`` while ``compile`` is kept
        with the task; the resulting phase-5 list resolves, so the compose-time
        resolution gate returns None (pre-fix it appended ``verify:compile`` and the
        gate failed the whole compose with ``unresolvable_step``)."""
        self._write_task(tmp_path / 'tasks', 1, [self._COMPILE_CMD, self._MODULE_TESTS_CMD])
        self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        _mem._route_task_verification_commands('X', body)

        phase_5_steps = body['phase_5']['verification_steps']
        assert phase_5_steps == ['verify:module-tests']
        # The FINAL emitted phase-5 list resolves — no unresolvable_step.
        assert _mem.check_emitted_steps_resolvable(phase_5_steps, [], {}, None) is None
