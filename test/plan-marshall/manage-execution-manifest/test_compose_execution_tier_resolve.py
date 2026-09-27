# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_compose_execution_tier_fixtures import (
    Path,
    SimpleNamespace,
    _clear_arch_resolve_cache,
    _mem,
    _resolve_step_execution_tier,
)


class TestResolveStepExecutionTierDefaultsPerTask:
    """``_resolve_step_execution_tier`` falls back to per_task on every failure path.

    ``per_task`` is the PERMISSIVE default, NOT a safe floor: it is the value that
    would put a long build inline, where the host platform auto-backgrounds it past
    the Bash ceiling and a dispatched leaf cannot reap it. The fallback is
    acceptable only because the stamp is advisory — ``phase-5-execute`` re-resolves
    the tier live before running each step and routes on that verdict, so a
    permissive compose-time default cannot by itself send a long build inline.

    The assertions below therefore pin the composer's obligation to emit SOME
    resolved tier on every failure path (never an absent or unresolved value), not a
    claim that ``per_task`` is the conservative choice.
    """

    def test_unresolvable_executor_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: None)
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_nonzero_exit_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        monkeypatch.setattr(_mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=1, stdout=''))
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_subprocess_error_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))

        def _boom(*a, **k):
            raise OSError('boom')

        monkeypatch.setattr(_mem.subprocess, 'run', _boom)
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_non_success_status_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: error\nexecution_tier: orchestrator\n'
        monkeypatch.setattr(_mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon))
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_unknown_tier_value_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: success\nexecution_tier: something-else\n'
        monkeypatch.setattr(_mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon))
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_absent_tier_field_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: success\nmodule: default\n'
        monkeypatch.setattr(_mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon))
        assert _resolve_step_execution_tier('quality-gate', 'X') == 'per_task'

    def test_orchestrator_tier_is_read_from_resolve_toon(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: success\nexecution_tier: orchestrator\nbash_timeout_seconds: 2065\n'
        monkeypatch.setattr(_mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon))
        assert _resolve_step_execution_tier('verify', 'X') == 'orchestrator'

    def test_per_task_tier_is_read_from_resolve_toon(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: success\nexecution_tier: per_task\nbash_timeout_seconds: 150\n'
        monkeypatch.setattr(_mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon))
        assert _resolve_step_execution_tier('quality-gate', 'X') == 'per_task'
