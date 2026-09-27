# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_compose_execution_tier_fixtures import (
    Path,
    SimpleNamespace,
    _clear_arch_resolve_cache,
    _mem,
)


class TestInvokeArchitectureResolveCaching:
    """``_invoke_architecture_resolve`` memoizes per ``(argv_extra, plan_id)`` within one compose.

    The same ``default:verify:arch-gate`` canonical is probed twice in one compose —
    once by ``_apply_domain_seeded_step_resolvability`` and again by
    ``_resolve_step_execution_tier`` when the step survives — so a repeated identical
    resolve must reuse the first result instead of re-spawning the subprocess. Distinct
    keys still each spawn their own subprocess.
    """

    _SUCCESS_TOON = 'status: success\nexecution_tier: per_task\n'

    @staticmethod
    def _patch_counting_run(monkeypatch) -> list[list[str]]:
        calls: list[list[str]] = []

        def _counting_run(argv, *a, **k):
            calls.append(argv)
            return SimpleNamespace(
                returncode=0,
                stdout=TestInvokeArchitectureResolveCaching._SUCCESS_TOON,
            )

        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        monkeypatch.setattr(_mem.subprocess, 'run', _counting_run)
        return calls

    def test_repeated_identical_resolve_spawns_subprocess_once(self, monkeypatch):
        calls = self._patch_counting_run(monkeypatch)

        first = _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')
        second = _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')

        assert first == second == {'status': 'success', 'execution_tier': 'per_task'}
        # The second identical resolve is served from the memo — no re-spawn.
        assert len(calls) == 1

    def test_distinct_keys_each_spawn_subprocess(self, monkeypatch):
        calls = self._patch_counting_run(monkeypatch)

        _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')
        _mem._invoke_architecture_resolve(['--command', 'quality-gate'], 'PLAN')
        _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'OTHER')

        # Distinct canonical or distinct plan_id → distinct cache key → distinct spawn.
        assert len(calls) == 3

    def test_cache_clear_forces_re_resolution(self, monkeypatch):
        calls = self._patch_counting_run(monkeypatch)

        _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')
        _mem._invoke_architecture_resolve_cached.cache_clear()
        _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')

        # cache_clear (as cmd_compose runs per compose) drops the memo → a re-spawn.
        assert len(calls) == 2
