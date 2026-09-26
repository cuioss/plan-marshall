# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_compose_execution_tier_fixtures import (
    Path,
    _clear_arch_resolve_cache,
    _mem,
    json,
)


class TestRouteUnmappedOrchestratorVerbs:
    """Orchestrator-tier commands with a NON-canonical, UNKNOWN verb route to ``verify:{verb}``.

    The canonical map (``_VERB_TO_PHASE_5_STEP``) is only the fast path: an
    orchestrator-tier build command whose parseable verb is unmapped AND is not a
    known build-phase canonical (e.g. a custom target like ``perf-suite``)
    generalizes to the bare ``verify:{verb}`` step ID and is REMOVED from the task.

    Two OTHER kinds of orchestrator-tier command survive per-task instead of
    routing, and are covered elsewhere, not here: an unparseable (raw-shell /
    non-``plan-marshall:build-``) command, and a known canonical build verb with
    no phase-5 verify gate (``compile`` / ``test-compile`` — see
    ``TestBuildPhaseCanonicalCarveOut``).
    """

    _CUSTOM_VERB_CMD = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        "run --command-args 'perf-suite plan-marshall'"
    )
    # A raw shell command: not a ``plan-marshall:build-*`` executor invocation, so the
    # classifier cannot parse a verb out of it. The specific program is incidental —
    # what the fixture stands for is "unparseable verb".
    _RAW_SHELL_CMD = 'make perf-suite'

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
        """Point the routing pass at ``tmp_path`` with an all-orchestrator classifier."""
        captured: list[str] = []
        monkeypatch.setattr(_mem, 'get_plan_dir', lambda pid: tmp_path)
        monkeypatch.setattr(_mem, '_resolve_command_tier', lambda cmd, pid: {'execution_tier': 'orchestrator'})
        monkeypatch.setattr(_mem, '_emit_decision_log', lambda pid, msg: captured.append(msg))
        return captured

    def test_unmapped_verb_routes_to_verify_verb_and_leaves_no_inline_command(self, monkeypatch, tmp_path):
        """(i) The custom-verb command lands as ``verify:{verb}`` and is dropped per-task."""
        task_path = self._write_task(tmp_path / 'tasks', 1, [self._CUSTOM_VERB_CMD])
        captured = self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)
        # The routing pass STAGES the task rewrite; persistence is deferred to the
        # caller after the compose-time resolution gate. Commit the staged writes
        # so the on-disk assertion below observes the routed state.
        _mem._persist_task_rewrites(pending)

        assert mutated == 1
        assert body['phase_5']['verification_steps'] == ['verify:perf-suite']
        rewritten = json.loads(task_path.read_text(encoding='utf-8'))
        assert rewritten['verification']['commands'] == []
        # Diagnostic-mute fix: the routed non-canonical verb is named in decision.log.
        assert any("'perf-suite'" in msg and "'verify:perf-suite'" in msg for msg in captured)

    def test_recompose_is_idempotent_appends_nothing(self, monkeypatch, tmp_path):
        """(ii) A second routing pass over the routed state appends and mutates nothing."""
        self._write_task(tmp_path / 'tasks', 1, [self._CUSTOM_VERB_CMD])
        self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        first, first_pending = _mem._route_task_verification_commands('X', body)
        assert first == 1
        # Persist between passes to model a real re-compose: the second compose
        # reads the persisted (already-routed) task files from disk.
        _mem._persist_task_rewrites(first_pending)
        second, second_pending = _mem._route_task_verification_commands('X', body)
        assert second == 0
        assert second_pending == []
        assert body['phase_5']['verification_steps'] == ['verify:perf-suite']

    def test_same_verb_across_tasks_dedups_through_seen_steps(self, monkeypatch, tmp_path):
        """Two tasks carrying the same custom verb produce ONE routed step."""
        self._write_task(tmp_path / 'tasks', 1, [self._CUSTOM_VERB_CMD])
        self._write_task(tmp_path / 'tasks', 2, [self._CUSTOM_VERB_CMD])
        self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)

        assert mutated == 2
        assert len(pending) == 2
        assert body['phase_5']['verification_steps'] == ['verify:perf-suite']

    def test_raw_shell_command_stays_per_task_untouched(self, monkeypatch, tmp_path):
        """(iii) An orchestrator-classified raw-shell command (unparseable verb) is kept."""
        task_path = self._write_task(tmp_path / 'tasks', 1, [self._RAW_SHELL_CMD])
        self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)

        assert mutated == 0
        assert pending == []
        assert body['phase_5']['verification_steps'] == []
        unchanged = json.loads(task_path.read_text(encoding='utf-8'))
        assert unchanged['verification']['commands'] == [self._RAW_SHELL_CMD]

    def test_canonical_verb_still_uses_fast_path_map(self, monkeypatch, tmp_path):
        """A canonical verb routes through ``_VERB_TO_PHASE_5_STEP``, not the generalization."""
        cmd = (
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
            "run --command-args 'module-tests plan-marshall'"
        )
        self._write_task(tmp_path / 'tasks', 1, [cmd])
        captured = self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)

        assert mutated == 1
        assert len(pending) == 1
        assert body['phase_5']['verification_steps'] == ['verify:module-tests']
        # The canonical fast path emits NO per-verb non-canonical routing line.
        assert not any('non-canonical' in msg for msg in captured)
