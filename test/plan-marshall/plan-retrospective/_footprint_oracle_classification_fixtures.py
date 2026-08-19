# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``footprint oracle classification`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import json
import sys
from pathlib import Path

from _plan_retrospective_fixtures import build_happy_plan_dir  # noqa: E402

from conftest import MARKETPLACE_ROOT  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))


MANIFEST_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-manifest-consistency.py'
)


ROUTING_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-routing-decisions.py'
)


# The project-local skill tree this project's own build map routes as production
# (``.claude/skills/*.py`` on the Claude target — a single ``*`` spans ``/`` under
# fnmatch, so the glob covers the nested ``{skill}/scripts/`` layout).
PROJECT_LOCAL_PRODUCTION = [
    '.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py',
    '.claude/skills/sync-plugin-cache/scripts/sync.py',
    '.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py',
    '.claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py',
    '.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py',
]


def _write_marshal(base: Path) -> None:
    """Stage a marshal.json whose ``build.map`` mirrors this project's real routes."""
    (base / 'marshal.json').write_text(
        json.dumps(
            {
                'build': {
                    'map': {
                        'python': [
                            {'glob': '.claude/skills/*.py', 'role': 'production', 'build_class': 'prod_compile'},
                            {'glob': 'marketplace/bundles/*.py', 'role': 'production', 'build_class': 'prod_compile'},
                            {'glob': 'test/*.py', 'role': 'test', 'build_class': 'test_run'},
                            {'glob': 'pyproject.toml', 'role': 'config', 'build_class': 'build_config_full'},
                        ]
                    }
                }
            }
        ),
        encoding='utf-8',
    )


def _serialize(body: dict) -> str:
    from toon_parser import serialize_toon

    return serialize_toon(body) + '\n'


def _setup(tmp_path, monkeypatch, manifest: dict, *, plan_id: str = 'oracle-plan') -> tuple[str, Path]:
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)
    (plan_dir / 'execution.toon').write_text(_serialize(manifest), encoding='utf-8')
    _write_marshal(base)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


def _write_diff(directory: Path, files: list[str], name: str = 'diff.txt') -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text('\n'.join(files) + ('\n' if files else ''), encoding='utf-8')
    return path


def _check(checks: list, name: str) -> dict:
    for entry in checks:
        if entry.get('name') == name:
            return entry
    raise AssertionError(f'check {name!r} absent from {[c.get("name") for c in checks]}')
