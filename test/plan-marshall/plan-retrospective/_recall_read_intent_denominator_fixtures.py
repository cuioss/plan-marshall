# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``recall read intent denominator`` test module.

Holds the module-level loads, constants and helpers it uses, so
the module itself carries the import and not the preamble.
"""


from __future__ import annotations

import json
from pathlib import Path

from conftest import load_script_module

_cac = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-artifact-consistency.py', 'cac_read_intent_mod'
)


#: The check passes at or above this recall. Restated from the module under test
#: so a threshold change surfaces here as a failure rather than silently
#: re-tuning what these fixtures prove.
_THRESHOLD = 0.70


_ONE_DELIVERABLE = [{'number': '1', 'title': 'Deliverable 1'}]


def _outline(entries: list[tuple[str, str | None]], *, backticked: bool = True) -> str:
    """Build a one-deliverable outline whose bullets carry per-file intents.

    ``entries`` is ``(path, intent)``; an intent of ``None`` emits the
    unannotated bullet form. ``backticked`` selects the canonical
    ``- `path` (intent)`` form or the bare ``- path (intent)`` form.
    """
    bullets = []
    for path, intent in entries:
        rendered = f'`{path}`' if backticked else path
        suffix = f' ({intent})' if intent else ''
        bullets.append(f'- {rendered}{suffix}')
    return (
        '# Solution: Intent\n\n'
        '## Summary\n\nFixture.\n\n'
        '## Overview\n\nOverview.\n\n'
        '## Deliverables\n\n'
        '### 1. Deliverable 1\n\n'
        '**Affected files:**\n' + '\n'.join(bullets) + '\n'
    )


def _plan_dir(tmp_path: Path, footprint: list[str]) -> Path:
    """Seed a plan dir whose footprint resolves from the tier-2 capture.

    Using ``realized_footprint`` keeps the fixture deterministic: the resolver
    answers from the file, so no worktree or git history is involved.
    """
    plan_dir = tmp_path / 'plan'
    plan_dir.mkdir()
    (plan_dir / 'references.json').write_text(
        json.dumps({'realized_footprint': footprint}), encoding='utf-8'
    )
    return plan_dir
