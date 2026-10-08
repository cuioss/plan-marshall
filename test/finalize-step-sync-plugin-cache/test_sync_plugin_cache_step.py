#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Contract tests for the project-local ``project:finalize-step-sync-plugin-cache`` skill.

The skill is a markdown executor playbook backed by the unified sync engine
at ``marketplace/targets/sync.py``, which it runs with no ``--target`` so one
call syncs every harness install. These tests pin the contract from three
angles:

1. **Frontmatter and ordering** — ``order: 85`` so it sits post-merge
   immediately after ``project:finalize-step-deploy-target`` (81) and
   before ``default:record-metrics`` (990); inside the step, sync, executor
   regeneration, daemon reconcile and repin run in that order.
2. **Project-local registration** — the skill lives at
   ``.claude/skills/finalize-step-sync-plugin-cache/SKILL.md`` (NOT in
   any marketplace bundle, NOT in ``BUILT_IN_FINALIZE_STEPS``).
3. **Outcome and display-detail decision branches** — a re-implementation
   of the skill's decision over the engine's aggregate document and the
   final registry verdict, plus a length check that composes both
   ``display_detail`` forms from the tokens the step text documents.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from _documented_example_scan import BARE_PYTHON_TARGETS_PREFIX, iter_fenced_blocks, scan_shell_prescriptions

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module
from marketplace.targets.sync import SYNC_TARGETS

cd = load_script_module('plan-marshall', 'manage-config', '_config_defaults.py')

_SKILL_MD = PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-sync-plugin-cache' / 'SKILL.md'
_DEPLOY_TARGET_SKILL_MD = PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-deploy-target' / 'SKILL.md'

#: The engine call the step prescribes: no ``--target``, so one call syncs every
#: harness. Built from the shared prefix constant so this module never opens a
#: line with the invocation itself.
_ENGINE_INVOCATION = f'{BARE_PYTHON_TARGETS_PREFIX}sync.py'
_RECONCILE_INVOCATION = f'{BARE_PYTHON_TARGETS_PREFIX}claude/reconcile_daemon.py'
_REPORT_INVOCATION = f'{BARE_PYTHON_TARGETS_PREFIX}claude/registry_pin.py'
_REPIN_INVOCATION = f'{_REPORT_INVOCATION} --apply'

#: The step's headings, in the order the step runs them.
_STEP_HEADINGS: tuple[str, ...] = (
    '### 1. Invoke the unified sync engine',
    '### 2. Parse the result',
    '### 3. Regenerate the on-main executor (when the Claude cache synced)',
    '### 3b. Reconcile the build daemon (when the Claude cache synced)',
    '### 3c. Repin or report the plugin registry (when the Claude cache synced)',
    '### 4. Mark step complete',
)

#: The three steps that run only once the Claude cache has synced.
_GATED_HEADINGS: tuple[str, ...] = _STEP_HEADINGS[2:5]
# A slice yields fewer elements, down to none, when the tuple it reads is
# shortened or reordered — and an empty one would let the gate test below
# collect no case and report nothing.
assert len(_GATED_HEADINGS) == 3, f'the gated-step slice resolved {len(_GATED_HEADINGS)} heading(s), not three'

#: A gate on the Claude row's own ``status`` rather than on ``cache_status``.
_BARE_STATUS_GATE = re.compile(r'(?<!cache_)status: success')

#: The ``display_detail`` limit, owned by the external-step contract.
_DETAIL_LIMIT = 80

#: The largest count the documented length bound covers.
_SEVEN_DIGITS = '9999999'


def _text() -> str:
    return _SKILL_MD.read_text(encoding='utf-8')


def _flat(text: str) -> str:
    return re.sub(r'\s+', ' ', text)


def _parse_frontmatter(path: Path) -> dict[str, str]:
    match = re.match(r'^---\n(.*?)\n---\n', path.read_text(encoding='utf-8'), re.DOTALL)
    assert match is not None, f'frontmatter not found in {path}'
    pairs = (line.split(':', 1) for line in match.group(1).splitlines() if ':' in line)
    return {key.strip(): value.strip() for key, value in pairs}


def _section(heading: str) -> str:
    """The body under ``heading``, up to the next heading of the same depth or higher."""
    text = _text()
    start = text.index(heading)
    following = re.search(r'^#{2,3} ', text[start + len(heading) :], re.MULTILINE)
    return text[start : start + len(heading) + following.start()] if following else text[start:]


def _documented_tokens(prefix: str) -> list[str]:
    """Every backticked ``{prefix} {word}`` token the step text documents, as the word."""
    return sorted(set(re.findall(rf'`{prefix} (\w+)`', _text())))


def _pin_tokens() -> list[str]:
    """The first-column tokens of the step's pin-token table."""
    table = _text().split('| Pin token |', 1)[1].split('\n\n', 1)[0]
    return re.findall(r'^\| `(\w+)` \|', table, re.MULTILINE)


def _form(opening: str) -> str:
    """The ``display_detail`` template whose fenced line starts with ``opening``."""
    lines = [block.body.strip() for block in iter_fenced_blocks(_text()) if block.body.strip().startswith(opening)]
    assert len(lines) == 1, f'expected one fenced template opening with {opening!r}, found {len(lines)}'
    return lines[0]


def _longest(tokens: list[str]) -> str:
    assert tokens, 'no documented token resolved — the composition below would measure nothing'
    return max(tokens, key=len)


# ---------------------------------------------------------------------------
# 1) Frontmatter and ordering
# ---------------------------------------------------------------------------


def test_skill_frontmatter_canonical_fields():
    assert _SKILL_MD.is_file(), f'project-local finalize-step skill missing: {_SKILL_MD}'
    fm = _parse_frontmatter(_SKILL_MD)
    assert fm.get('name') == 'finalize-step-sync-plugin-cache'
    assert fm.get('description'), 'description must be non-empty'
    assert fm.get('order') == '85', (
        'finalize-step-sync-plugin-cache order must be 85 (post-merge: immediately after '
        'finalize-step-deploy-target=81, before record-metrics=990)'
    )


def test_order_after_deploy_target_post_merge():
    """Post-merge, the sync step immediately follows deploy-target, both after create-pr."""
    create_pr_md = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'create-pr.md'
    orders = [int(_parse_frontmatter(path)['order']) for path in (create_pr_md, _DEPLOY_TARGET_SKILL_MD, _SKILL_MD)]

    assert orders == sorted(orders) and len(set(orders)) == len(orders)


def test_skill_body_documents_inline_and_engine_call():
    """The step is inline-only and its one sync call is the unified engine, run without ``--target``.

    Matching every prescribed line that names a ``sync.py`` — rather than only
    looking for the engine line — is what catches a second sync script or a
    ``--target`` narrowing the finalize-time sync to one harness.
    """
    prescriptions, _ = scan_shell_prescriptions(_text())
    flat = _flat(_text().lower())

    assert 'inline-only' in flat or 'inline only' in flat
    assert [line for line in prescriptions if 'sync.py' in line] == [_ENGINE_INVOCATION]


def test_step_headings_and_commands_run_in_the_documented_order():
    """Sync, executor regeneration, daemon reconcile, repin and the completion record, in that order."""
    text = _text()
    prescriptions, examined = scan_shell_prescriptions(text)
    assert examined, 'no fenced line resolved from the step — nothing was examined'
    commands = (
        _ENGINE_INVOCATION,
        'tools-script-executor:generate_executor generate',
        _RECONCILE_INVOCATION,
        'run_config registry-repin get',
        _REPIN_INVOCATION,
        'mark-step-done',
    )

    heading_positions = [text.index(heading) for heading in _STEP_HEADINGS]
    command_positions = [
        next(index for index, line in enumerate(prescriptions) if command in line) for command in commands
    ]

    assert heading_positions == sorted(heading_positions)
    assert command_positions == sorted(command_positions)
    assert 'repin or report (3c) → parity verdict' in _flat(text)


@pytest.mark.parametrize('heading', _GATED_HEADINGS)
def test_claude_follow_up_steps_gate_on_cache_status(heading: str):
    """Steps 3, 3b and 3c gate on the Claude ``cache_status``, never on the ``claude`` row's ``status``."""
    section = _flat(_section(heading))

    assert 'cache_status: success' in section
    assert not _BARE_STATUS_GATE.search(section), f'{heading} gates on the claude row status'


def test_repin_step_reads_the_opt_in_and_applies_only_when_enabled():
    """Step 3c reads ``registry-repin get``, prescribes both script forms and logs its own line."""
    section = _section(_STEP_HEADINGS[4])
    prescriptions, _ = scan_shell_prescriptions(section)

    assert 'plan-marshall:manage-run-config:run_config registry-repin get' in ' '.join(prescriptions)
    assert _REPIN_INVOCATION in prescriptions and _REPORT_INVOCATION in prescriptions
    assert section.index('`value: enabled`') < section.index(_REPIN_INVOCATION) < section.index('`value: disabled`')
    assert 'Registry repin: mode {mode}, verdict {registry_parity}' in section
    assert '`in_parity`, `behind`, `ahead` or `unreadable`' in _flat(section)


def test_outcome_table_fails_on_an_unsynced_install_or_a_behind_verdict():
    """Three conditions record ``failed``; only their absence records ``done``."""
    rows = re.findall(r'^\| (.+?) \| `outcome=(\w+)` \|$', _section(_STEP_HEADINGS[1]), re.MULTILINE)

    assert [outcome for _, outcome in rows] == ['failed', 'failed', 'failed', 'done']
    assert 'OpenCode or Antigravity' in rows[0][0]
    assert '`cache_status`' in rows[1][0]
    assert '`behind`' in rows[2][0]


def test_display_detail_forms_carry_a_pin_token():
    """Both forms end with the pin token, and the token table names all five."""
    assert _form('cl ').endswith('; pin {pin}')
    assert _form('failed: ').endswith('[; claude synced[; pin {pin}]]')
    assert _pin_tokens() == ['ok', 'repinned', 'behind', 'ahead', 'unreadable']


def test_display_detail_forms_stay_within_the_limit_at_their_longest():
    """Each form, composed from the longest documented token of every segment, is ASCII and fits.

    The tokens are read from the step text, so a token added there that
    overflows the limit fails here rather than at finalize time.
    """
    pin = _longest(_pin_tokens())
    form_1 = (
        _form('cl ')
        .replace('{synced_count}', _SEVEN_DIGITS)
        .replace('{deployed_count}', _SEVEN_DIGITS)
        .replace('{regen}', _longest(_documented_tokens('regen')))
        .replace('{daemon}', _longest(_documented_tokens('daemon')))
        .replace('{pin}', pin)
    )
    form_2 = _form('failed: ').replace('{pin}', pin)
    harnesses = [name for name in SYNC_TARGETS if name != 'claude']
    compositions = [
        form_1.replace('[', '').replace(']', ''),
        form_2.replace('{targets}', ', '.join(harnesses)).replace('[', '').replace(']', ''),
        form_2.split('[', 1)[0].replace('{targets}', ', '.join(SYNC_TARGETS)),
    ]

    for composed in compositions:
        assert '{' not in composed, f'an unresolved placeholder remains: {composed}'
        assert composed.isascii(), f'not ASCII: {composed}'
        assert len(composed) <= _DETAIL_LIMIT, f'{len(composed)} characters: {composed}'
    assert all(f'`{composed}`' in _flat(_text()) for composed in compositions[:2]), (
        'the step text should state the longest rendering of each form verbatim'
    )


# ---------------------------------------------------------------------------
# 2) NOT a built-in default — meta-project-only project step
# ---------------------------------------------------------------------------


def test_sync_plugin_cache_is_not_a_built_in_default():
    """The sync step is discovered as ``project:{dir}``, never as a ``default:`` built-in."""
    from extension_discovery import find_implementors

    discovered_names = {rec['name'] for rec in find_implementors(cd.FINALIZE_STEP_EXT_POINT) if rec.get('name')}
    assert 'default:sync-plugin-cache' not in discovered_names
    assert 'project:finalize-step-sync-plugin-cache' in discovered_names
    # DEFAULT_PLAN_FINALIZE['steps'] is a lazy None placeholder; the seeded map is
    # built by _seed_finalize_steps() (the discovered default-on built-in set).
    assert 'default:sync-plugin-cache' not in cd._seed_finalize_steps()


@pytest.mark.parametrize(
    'relative',
    ['phase-6-finalize/standards/sync-plugin-cache.md', 'sync-harnesses'],
    ids=['standards-doc', 'sync-command-skill'],
)
def test_nothing_in_the_bundle_ships_the_sync_step_or_command(relative: str):
    """The step and the ``sync-harnesses`` command are project-local; the bundle ships neither."""
    bundled = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / relative

    assert not bundled.exists(), f'unexpected bundled copy: {bundled}'


# ---------------------------------------------------------------------------
# 3) Outcome and display-detail decision branches
# ---------------------------------------------------------------------------


def _aggregate(
    *, cache_status: str = 'success', opencode: str = 'success', antigravity: str = 'success'
) -> dict[str, Any]:
    """The per-harness results of an all-targets run, in the engine's shape."""
    return {
        'claude': {'cache_status': cache_status, 'synced_count': 10},
        'opencode': {'status': opencode, 'deployed_count': 164},
        'antigravity': {'status': antigravity, 'deployed_count': 170},
    }


def _resolve_step(
    document: dict[str, Any], *, verdict: str = 'in_parity', repinned: bool = False, daemon: str | None = None
) -> tuple[str, str, bool]:
    """Mirror the skill's Steps 2-4 decision.

    ``verdict`` and ``repinned`` are Step 3c's result and are read only when the
    Claude cache synced. Returns ``(outcome, display_detail, follow_ups_run)``.
    """
    cache_synced = document['claude']['cache_status'] == 'success'
    unsynced = [] if cache_synced else ['claude']
    unsynced += [name for name in ('opencode', 'antigravity') if document[name]['status'] != 'success']
    pin = {'in_parity': 'repinned' if repinned else 'ok'}.get(verdict, verdict)
    outcome = 'failed' if unsynced or (cache_synced and verdict == 'behind') else 'done'
    if unsynced:
        detail = f'failed: {", ".join(unsynced)} (see work log)'
        return outcome, detail + (f'; claude synced; pin {pin}' if cache_synced else ''), cache_synced
    counts = (
        f'cl {document["claude"]["synced_count"]} oc {document["opencode"]["deployed_count"]} '
        f'ag {document["antigravity"]["deployed_count"]}'
    )
    return outcome, f'{counts}; regen ok{f"; daemon {daemon}" if daemon else ""}; pin {pin}', cache_synced


@pytest.mark.parametrize(
    ('document', 'step_3c', 'expected'),
    [
        (_aggregate(), {}, ('done', 'cl 10 oc 164 ag 170; regen ok; pin ok', True)),
        (_aggregate(), {'repinned': True}, ('done', 'cl 10 oc 164 ag 170; regen ok; pin repinned', True)),
        (_aggregate(), {'verdict': 'behind'}, ('failed', 'cl 10 oc 164 ag 170; regen ok; pin behind', True)),
        (_aggregate(), {'verdict': 'ahead'}, ('done', 'cl 10 oc 164 ag 170; regen ok; pin ahead', True)),
        (
            _aggregate(),
            {'verdict': 'unreadable', 'daemon': 'defer'},
            ('done', 'cl 10 oc 164 ag 170; regen ok; daemon defer; pin unreadable', True),
        ),
        (
            _aggregate(opencode='error'),
            {'repinned': True},
            ('failed', 'failed: opencode (see work log); claude synced; pin repinned', True),
        ),
        (_aggregate(cache_status='error'), {}, ('failed', 'failed: claude (see work log)', False)),
        (_aggregate(cache_status='partial'), {'verdict': 'behind'}, ('failed', 'failed: claude (see work log)', False)),
        (
            _aggregate(cache_status='error', opencode='error', antigravity='error'),
            {},
            ('failed', 'failed: claude, opencode, antigravity (see work log)', False),
        ),
    ],
    ids=[
        'all-synced-in-parity',
        'all-synced-repinned',
        'all-synced-behind',
        'all-synced-ahead',
        'all-synced-unreadable-daemon-deferred',
        'opencode-failed-claude-synced',
        'claude-guard-refused',
        'claude-bundles-failed',
        'none-synced',
    ],
)
def test_step_resolution(document: dict[str, Any], step_3c: dict[str, Any], expected: tuple[str, str, bool]):
    """Each run resolves to its outcome, its detail and whether the Claude follow-ups ran.

    The discriminating cases are the ones the aggregate status cannot tell
    apart: a registry that is behind fails a run whose every install synced,
    a repin that closed the gap does not, and a Claude cache that did not sync
    records no pin token because Step 3c never ran.
    """
    assert _resolve_step(document, **step_3c) == expected
    assert len(expected[1]) <= _DETAIL_LIMIT
