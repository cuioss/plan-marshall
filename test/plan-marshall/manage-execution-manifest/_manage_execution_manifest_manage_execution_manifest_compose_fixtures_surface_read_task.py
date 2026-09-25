#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import Callable, _mem


def _make_tier_stub(
    orchestrator_verbs: set[str] | None = None,
    per_task_timeout: int = 360,
) -> Callable[[str, str], dict | None]:
    """Build a fake ``_resolve_command_tier`` that branches by verb.

    Commands whose verb appears in ``orchestrator_verbs`` resolve to the
    ``orchestrator`` tier; every other build verb resolves to ``per_task``
    with the supplied ``bash_timeout_seconds`` (default 360s — comfortably
    under the 600s ceiling). Non-build commands (the helper's parse
    returns ``None``) resolve to ``None`` so the composer leaves them
    untouched.
    """
    orch = set(orchestrator_verbs or ())

    def _stub(cmd: str, plan_id: str) -> dict | None:
        parsed = _mem._parse_verification_command(cmd)
        if parsed is None:
            return None
        verb, _ = parsed
        if verb in orch:
            return {
                'status': 'success',
                'bash_timeout_seconds': 900,
                'exceeds_bash_ceiling': True,
                'execution_tier': 'orchestrator',
                'hint': 'Exceeds Bash ceiling; orchestrator-tier only',
            }
        return {
            'status': 'success',
            'bash_timeout_seconds': per_task_timeout,
            'exceeds_bash_ceiling': False,
            'execution_tier': 'per_task',
            'hint': f'Bash timeout={per_task_timeout * 1000}ms',
        }

    return _stub
