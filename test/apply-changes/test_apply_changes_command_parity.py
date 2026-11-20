#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``apply-changes`` command is one sequence behind three harness-local entry points.

Each harness reads its commands from its own project-local location, so the
command exists as three files: a Claude skill, an OpenCode command and an
Antigravity skill. They carry one ordered sequence — regenerate the three
targets, run the sync engine, regenerate the executor, reconcile the build
daemon, write the registry pin — and end with the restart the command cannot
perform itself.

Three copies of one sequence drift unless something holds them together. These
tests pin the parts that must stay identical and correctly ordered: the command
name and its permission entries, the seven prescribed commands and their order,
the bare engine call, the registry write as its own last step, the
``cache_status`` gate on the three follow-up steps, and the byte-identical
post-run block that names the restart.

**Every pin has a matched control.** Each detector is a pure function over
document text, so its control plants the violation in a temporary tree and reads
it back through the same code path — then asserts the detector is silent on the
unmodified entry points. A detector that fired on everything, or on nothing,
fails its control.

The entry points live under ``.claude/``, ``.opencode/`` and ``.agents/``, which
lie outside the architecture inventory, so they are read by explicit path.
"""

from __future__ import annotations

import json
from pathlib import Path

from _documented_example_scan import BARE_PYTHON_TARGETS_PREFIX
from _harness_entry_point_scan import (
    BARE_STATUS_GATE,
    DIRECT_WRAPPER_CALL,
    collapsed,
    frontmatter,
    post_run_block,
    prescribed_commands,
    replace_nth,
    step_blocks,
    swap_lines,
)

from conftest import PROJECT_ROOT
from marketplace.targets.sync import CLAUDE_TARGET, SYNC_TARGETS

_COMMAND_NAME = 'apply-changes'

#: The repository-relative entry point of each harness, keyed by harness name.
#: The mapping is explicit because each harness reads commands from its own
#: location; which harnesses must HAVE an entry point is derived below.
_ENTRY_POINT_PATHS: dict[str, str] = {
    'claude': f'.claude/skills/{_COMMAND_NAME}/SKILL.md',
    'opencode': f'.opencode/commands/{_COMMAND_NAME}.md',
    'antigravity': f'.agents/skills/{_COMMAND_NAME}/SKILL.md',
}

#: ``(harness, repository-relative entry point)`` for every harness the engine
#: syncs, derived from the engine's own ``SYNC_TARGETS`` so a harness added there
#: without an entry point fails here instead of falling outside every check. An
#: undeclared harness keeps a sentinel path, which no existence check can pass.
_ENTRY_POINTS: tuple[tuple[str, str], ...] = tuple(
    (harness, _ENTRY_POINT_PATHS.get(harness, f'<no entry point declared for {harness}>')) for harness in SYNC_TARGETS
)
assert _ENTRY_POINTS, 'SYNC_TARGETS resolved no harness, so every entry-point check would be vacuous'

#: The entry points that are skills. A skill declares its name in frontmatter; an
#: OpenCode command is named by its file alone. Derived from the declared paths,
#: so a harness added as a skill is checked as one without a second list to edit.
_SKILL_HARNESSES: tuple[str, ...] = tuple(
    harness for harness, relative in _ENTRY_POINTS if relative.endswith('/SKILL.md')
)
assert _SKILL_HARNESSES, 'no entry point is a skill, so the frontmatter checks would be vacuous'

#: The permission entries the Claude settings must allow for the skill to be
#: invocable by name and by argument.
_SKILL_PERMISSIONS: tuple[str, ...] = (f'Skill({_COMMAND_NAME})', f'Skill({_COMMAND_NAME}:*)')

#: The three invocations below are built from the shared prefix constant so this
#: module never opens a line with a bare host-interpreter targets call, which the
#: generator-prescription sweep reports as a prescription.
_ENGINE_CALL = f'{BARE_PYTHON_TARGETS_PREFIX}sync.py'
_RECONCILE_CALL = f'{BARE_PYTHON_TARGETS_PREFIX}claude/reconcile_daemon.py'
_REPIN_CALL = f'{BARE_PYTHON_TARGETS_PREFIX}claude/registry_pin.py --apply'
_REGENERATE_CALL = 'python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate'

#: The generation targets are the engine's own sync population, in its own order,
#: so a harness added to `SYNC_TARGETS` is demanded of the entry points here rather
#: than silently left ungenerated.
_GENERATE_CALLS: tuple[str, ...] = tuple(
    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
    f'--command-args "generate-{target}"'
    for target in SYNC_TARGETS
)

#: The whole prescribed sequence, in order: the three regenerations, the sync, the
#: executor regeneration, the daemon reconcile and the registry write.
_PRESCRIBED_SEQUENCE: tuple[str, ...] = (
    *_GENERATE_CALLS,
    _ENGINE_CALL,
    _REGENERATE_CALL,
    _RECONCILE_CALL,
    _REPIN_CALL,
)

#: The follow-up steps, with the script each must prescribe.
_GATED_STEPS: tuple[tuple[int, str], ...] = (
    (3, 'generate_executor'),
    (4, 'reconcile_daemon.py'),
    (5, 'registry_pin.py --apply'),
)

#: The plugin-reload command the post-run block must name and nowhere else.
_RELOAD_PLUGINS = '/reload-plugins'

#: The one sentence that keeps a restart and a reload apart.
_RELOAD_SENTENCE = f'`{_RELOAD_PLUGINS}` alone is not sufficient'

#: The markers that would tie a description to one harness's install location.
_HARNESS_LOCATION_MARKERS: tuple[str, ...] = ('plugin cache', '~/.claude', '.config/opencode', '.gemini')

#: The restrictive conditions that BIND a follow-up step to its gate. A step that
#: carries the gate literal without one of these runs unconditionally, which is the
#: defect the gate pin exists to prevent.
_RESTRICTIVE_MARKERS: tuple[str, ...] = ('only when', 'under the same')

#: The frontmatter key that withholds a command or skill from model invocation. One
#: harness publishes it; the other two publish no such key, and the gap is recorded
#: in the entry point beside the sequence rather than in a PR body.
_OPERATOR_ONLY_KEY = 'disable-model-invocation'

#: What a harness without the key must say instead: that it publishes no key that
#: withholds the command, and what keeps a model from invoking it there.
_GAP_CLAUSE = 'no key that withholds'

#: The tag every entry point must carry on the operator-only claim — the key's own
#: effect is not shown by reading, and saying so is what keeps the claim honest.
_UNCONFIRMED_CLAUSE = 'not shown by reading'

#: The target metadata each gap-claiming harness cites, so the claim can be checked
#: against the data instead of only against its own prose. A rules file that ever
#: gains the withholding key makes the gap statement false, and this map is what
#: turns that into a red test rather than a stale paragraph.
#:
#: The PATH is explicit data: `sync.py` publishes no rules-file path and defines no
#: directory-naming convention for one, so it cannot be derived from the target
#: name. The KEY SET is not a second manifest — it is derived from the engine's own
#: synced harnesses, minus the one harness that publishes the key.
_RULES_FILE_PATHS: dict[str, str] = {
    'opencode': 'marketplace/targets/opencode/frontmatter-rules.json',
    'antigravity': 'marketplace/targets/antigravity/frontmatter-rules.json',
}
_GAP_HARNESSES: tuple[str, ...] = tuple(harness for harness in SYNC_TARGETS if harness != CLAUDE_TARGET)
_HARNESS_RULES_FILES: dict[str, str] = {harness: _RULES_FILE_PATHS[harness] for harness in _GAP_HARNESSES}
assert _HARNESS_RULES_FILES, 'the engine syncs no non-Claude harness, so the gap-claim checks would be vacuous'


def _read(root: Path, relative: str) -> str:
    """``relative`` read from ``root``, failing when the path is absent."""
    path = root / relative
    assert path.is_file(), f'the entry point {relative} should exist under {root}'
    return path.read_text(encoding='utf-8')


def _entry_texts(root: Path = PROJECT_ROOT) -> dict[str, str]:
    """Every entry point's text, keyed by harness, read from ``root``."""
    return {harness: _read(root, relative) for harness, relative in _ENTRY_POINTS}


def _missing_entry_points(root: Path = PROJECT_ROOT) -> list[str]:
    """The declared entry points absent from ``root``, or not named for the command."""
    missing = [relative for _harness, relative in _ENTRY_POINTS if not (root / relative).is_file()]
    misnamed = [
        relative
        for _harness, relative in _ENTRY_POINTS
        if not relative.removesuffix('/SKILL.md').removesuffix('.md').endswith(f'/{_COMMAND_NAME}')
    ]
    return missing + misnamed


def _harness_coverage_violations(paths: dict[str, str]) -> list[str]:
    """The harnesses the engine syncs that carry no declared entry point."""
    return sorted(set(SYNC_TARGETS) - set(paths))


def _frontmatter_violations(texts: dict[str, str]) -> list[str]:
    """Problems with the declared name: skills name the command, OpenCode does not."""
    problems: list[str] = []
    for harness in _SKILL_HARNESSES:
        declared = frontmatter(texts[harness]).get('name')
        if declared != _COMMAND_NAME:
            problems.append(f'the {harness} skill should declare name {_COMMAND_NAME}, got {declared!r}')
    for harness, text in texts.items():
        if harness in _SKILL_HARNESSES:
            continue
        if 'name' in frontmatter(text):
            problems.append(f'the {harness} entry point is named by its file and should declare no name')
    return problems


def _description_violations(texts: dict[str, str]) -> list[str]:
    """Descriptions that tie the command to one harness's install location."""
    problems: list[str] = []
    for harness, text in texts.items():
        description = frontmatter(text).get('description', '')
        if not description:
            problems.append(f'the {harness} entry point should carry a description')
            continue
        offenders = [marker for marker in _HARNESS_LOCATION_MARKERS if marker in description.casefold()]
        if offenders:
            problems.append(f'the {harness} description names a harness location: {offenders}')
    return problems


def _settings_violations(allow: list[str]) -> list[str]:
    """The skill permission entries absent from an allow list."""
    return [entry for entry in _SKILL_PERMISSIONS if entry not in allow]


def _sequence_violations(text: str) -> list[str]:
    """Problems with the prescribed sequence: a missing, extra or reordered command."""
    commands = prescribed_commands(text)
    if commands == list(_PRESCRIBED_SEQUENCE):
        return []
    return [
        f'prescribed commands should be {_PRESCRIBED_SEQUENCE!r}, got {commands!r}',
        f'unexpected: {[command for command in commands if command not in _PRESCRIBED_SEQUENCE]!r}',
        f'missing: {[command for command in _PRESCRIBED_SEQUENCE if command not in commands]!r}',
    ]


def _engine_and_repin_violations(text: str) -> list[str]:
    """Problems with the engine call and the registry write.

    The engine call is bare — one run syncing every harness, with no argument
    choosing a target and no registry write folded into it. The registry write is
    its own step, names ``--apply``, and comes last; no ``--repin`` appears at all.
    """
    problems: list[str] = []
    commands = prescribed_commands(text)
    sync_calls = [command for command in commands if 'sync.py' in command]
    if sync_calls != [_ENGINE_CALL]:
        problems.append(f'the sync call should be the bare engine call {_ENGINE_CALL!r}, got {sync_calls!r}')
    repin_calls = [command for command in commands if 'registry_pin.py' in command]
    if repin_calls != [_REPIN_CALL]:
        problems.append(f'the registry write should be its own {_REPIN_CALL!r} step, got {repin_calls!r}')
    if commands and commands[-1] != _REPIN_CALL:
        problems.append(f'the registry write should be the last prescribed command, got {commands[-1]!r}')
    if '--repin' in text:
        problems.append('a --repin flag appears: the registry write is its own step, never an engine argument')
    return problems


def _gate_violations(text: str) -> list[str]:
    """Problems with the ``cache_status`` gate.

    Steps 3 to 5 each run only when the Claude result reports
    ``cache_status: success`` and each prescribes its own script; no step states a
    gate on the Claude target's own ``status``, which a ``behind`` registry lowers
    to ``partial`` while the cache install is complete.
    """
    problems: list[str] = []
    blocks = step_blocks(text)
    for number, step_text in sorted(blocks.items()):
        if BARE_STATUS_GATE.search(step_text):
            problems.append(f'step {number} states a gate on the Claude target status')
    for number, script in _GATED_STEPS:
        gated = blocks.get(number)
        if gated is None:
            problems.append(f'step {number} was not found')
            continue
        if script not in gated:
            problems.append(f'step {number} should prescribe {script}')
        if 'cache_status: success' not in gated:
            problems.append(f'step {number} should gate on cache_status: success')
        lowered = gated.casefold()
        if not any(marker in lowered for marker in _RESTRICTIVE_MARKERS):
            problems.append(f'step {number} states the gate without a restrictive condition')
    return problems


def _direct_wrapper_violations(text: str) -> list[str]:
    """The prescribed commands that run ``./pw`` directly."""
    prescribed = prescribed_commands(text)
    if not prescribed:
        return ['no prescribed command resolved']
    return [command for command in prescribed if DIRECT_WRAPPER_CALL.search(command)]


def _mirror_violations(texts: dict[str, str]) -> list[str]:
    """Divergence between the entry points, and the post-run block's own contract."""
    problems: list[str] = []
    prescribed = {harness: prescribed_commands(text) for harness, text in texts.items()}
    blocks = {harness: post_run_block(text) for harness, text in texts.items()}
    reference_commands = prescribed.get('claude', [])
    reference_block = blocks.get('claude', '')
    if not reference_commands:
        problems.append('no prescribed command resolved from the claude entry point')
    if not reference_block:
        problems.append('no post-run block resolved from the claude entry point')
    for harness in texts:
        if prescribed[harness] != reference_commands:
            problems.append(f'the {harness} entry point prescribes a different command list')
        if blocks[harness] != reference_block:
            problems.append(f'the {harness} post-run block differs from the claude one')
    for harness, text in texts.items():
        outside_block = '\n'.join(line for line in text.splitlines() if not line.startswith('>'))
        if _RELOAD_PLUGINS in outside_block:
            problems.append(f'the {harness} entry point names {_RELOAD_PLUGINS} outside the post-run block')
    if 'restart' not in reference_block.casefold():
        problems.append('the post-run block should name the restart')
    if _RELOAD_SENTENCE not in collapsed(reference_block):
        problems.append(f'the post-run block should state that {_RELOAD_PLUGINS} alone is not sufficient')
    return problems


def _settings_allow(root: Path = PROJECT_ROOT) -> list[str]:
    """The ``permissions.allow`` list of the project's Claude settings."""
    payload = json.loads((root / '.claude' / 'settings.json').read_text(encoding='utf-8'))
    return list(payload['permissions']['allow'])


def _rules_fields(root: Path, harness: str) -> set[str]:
    """The frontmatter fields a harness's own target metadata admits."""
    rules = json.loads((root / _HARNESS_RULES_FILES[harness]).read_text(encoding='utf-8'))
    return set(rules.get('required_fields', [])) | set(rules.get('optional_fields', []))


def _gap_claim_contradicted(root: Path, harness: str) -> bool:
    """Whether the harness's own metadata now carries the withholding key.

    The entry point says its harness publishes no key that withholds the command
    from model invocation. Reading the file it cites is what keeps that sentence
    from outliving the data: the day the key appears, the gap is gone and the
    entry point must carry the key instead. A ``root`` with no such file (a planted
    fixture) states nothing to contradict; the shipped tree's own files are pinned
    present by their own test, so the silence cannot be the whole guard.
    """
    if not (root / _HARNESS_RULES_FILES[harness]).is_file():
        return False
    return _OPERATOR_ONLY_KEY in _rules_fields(root, harness)


def _operator_only_violations(texts: dict[str, str], root: Path = PROJECT_ROOT) -> list[str]:
    """Problems with the operator-only pin, per harness.

    The Claude entry point carries the key. A harness that publishes no such key
    declares the gap and what keeps a model from invoking the command there. Every
    entry point tags the claim as unconfirmed, because whether either harness
    honours its frontmatter is a runtime behaviour this repository only cites.
    """
    problems: list[str] = []
    claude = texts.get('claude')
    if claude is None:
        return ['no claude entry point was read, so the operator-only key cannot be pinned']
    if frontmatter(claude).get(_OPERATOR_ONLY_KEY, '').casefold() != 'true':
        problems.append(f'the claude entry point should declare {_OPERATOR_ONLY_KEY}: true')
    if _UNCONFIRMED_CLAUSE not in collapsed(claude).casefold():
        problems.append(f"the claude entry point should record that the key's effect is {_UNCONFIRMED_CLAUSE}")

    for harness, text in texts.items():
        if harness == 'claude':
            continue
        body = collapsed(text).casefold()
        # The uncertainty tag is checked BEFORE the key branch: an entry point that
        # has acquired the key still owes the statement that its effect is unproven,
        # and a `continue` here would let exactly that case through unmarked.
        if _UNCONFIRMED_CLAUSE not in body:
            problems.append(f'the {harness} entry point should mark the operator-only claim as {_UNCONFIRMED_CLAUSE}')
        if frontmatter(text).get(_OPERATOR_ONLY_KEY, '').casefold() == 'true':
            continue
        if _GAP_CLAUSE not in body:
            problems.append(
                f'the {harness} entry point should record that its harness publishes {_GAP_CLAUSE} the command'
            )
        if harness in _HARNESS_RULES_FILES and _gap_claim_contradicted(root, harness):
            problems.append(
                f'the {harness} gap statement is now false: {_HARNESS_RULES_FILES[harness]} carries '
                f'{_OPERATOR_ONLY_KEY}'
            )
    return problems


def _plant(root: Path, overrides: dict[str, str]) -> None:
    """Write every entry point under ``root``, replacing the harnesses in ``overrides``."""
    for harness, relative in _ENTRY_POINTS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = overrides[harness] if harness in overrides else _read(PROJECT_ROOT, relative)
        target.write_text(text, encoding='utf-8')


def test_the_declared_entry_points_exist_for_every_synced_harness():
    """Every harness the engine syncs carries an ``apply-changes`` entry point."""
    assert _harness_coverage_violations(_ENTRY_POINT_PATHS) == [], (
        f'entry points {sorted(_ENTRY_POINT_PATHS)} should match the engine targets {sorted(SYNC_TARGETS)}'
    )
    assert _missing_entry_points() == []


def test_the_entry_points_declare_their_names_and_neutral_descriptions():
    """Skills name the command in frontmatter; the OpenCode file is named by its path."""
    texts = _entry_texts()

    assert _frontmatter_violations(texts) == []
    assert _description_violations(texts) == []


def test_the_claude_settings_allow_the_skill_and_its_wildcard():
    """The skill is invocable by name, so the allow list carries both entries."""
    assert _settings_violations(_settings_allow()) == []


def test_every_entry_point_prescribes_the_seven_commands_in_order():
    """One sequence, in one order: the three regenerations, sync, executor, reconcile, repin."""
    for harness, relative in _ENTRY_POINTS:
        assert _sequence_violations(_read(PROJECT_ROOT, relative)) == [], (
            f'the {harness} entry point should prescribe the seven commands in order'
        )


def test_the_sync_call_is_bare_and_the_registry_write_is_its_own_last_step():
    """The engine runs with no argument, and the registry is written by its own step."""
    for harness, relative in _ENTRY_POINTS:
        assert _engine_and_repin_violations(_read(PROJECT_ROOT, relative)) == [], (
            f'the {harness} entry point should run the bare engine and repin as its own step'
        )


def test_steps_three_to_five_gate_on_cache_status():
    """The three follow-up steps gate on ``cache_status``, never on the target's status."""
    for harness, relative in _ENTRY_POINTS:
        assert _gate_violations(_read(PROJECT_ROOT, relative)) == [], (
            f'the {harness} entry point should gate its follow-up steps on cache_status: success'
        )


def test_no_entry_point_prescribes_a_direct_wrapper_call():
    """No prescribed command runs ``./pw`` directly.

    The regeneration goes through the build executor, which is the only form the
    enforcement hook admits inside a plan worktree.
    """
    for harness, relative in _ENTRY_POINTS:
        assert _direct_wrapper_violations(_read(PROJECT_ROOT, relative)) == [], (
            f'the {harness} entry point prescribes a direct ./pw call'
        )


def test_the_three_entry_points_are_mirrors_and_carry_the_post_run_block():
    """Equal command lists, one byte-identical post-run block, and the reload named only there."""
    assert _mirror_violations(_entry_texts()) == []


def test_the_command_is_operator_only_on_every_harness():
    """The key where the harness publishes one, the recorded gap where it does not."""
    assert _operator_only_violations(_entry_texts()) == []


def test_each_gap_claiming_harness_has_its_rules_file_to_check_against():
    """Non-vacuity: the contradiction guard reads a real file in the shipped tree.

    The map's key set is DERIVED from the engine's synced harnesses, so it cannot
    fall behind them; what is left to verify is that each cited path exists and that
    the shipped metadata still contradicts nothing.
    """
    for harness, relative in _HARNESS_RULES_FILES.items():
        assert (PROJECT_ROOT / relative).is_file(), f'the {harness} gap claim cites a file that does not exist'
        assert not _gap_claim_contradicted(PROJECT_ROOT, harness), (
            f'{relative} carries {_OPERATOR_ONLY_KEY}, so the {harness} gap statement is false'
        )


def test_operator_only_controls(tmp_path: Path):
    """Matched control: a missing key, a missing gap clause and a missing tag all fire.

    Each fixture is a STUB entry point rather than a substitution into the real
    text: a phrase-level replace would silently do nothing (and pass) if the doc
    re-wrapped the phrase across a line, and a control that cannot fire is the
    shape this file exists against.
    """
    stub = '---\nname: apply-changes\ndescription: A stub entry point.\n---\n\nRuns the sequence.\n'

    _plant(tmp_path, {'claude': stub})
    reported = _operator_only_violations(_entry_texts(tmp_path))
    assert any(_OPERATOR_ONLY_KEY in problem for problem in reported), (
        f'a claude entry point with no operator-only key must be reported, got {reported}'
    )

    _plant(tmp_path, {})
    assert _operator_only_violations(_entry_texts(tmp_path)) == [], 'the unmodified entry points must stay clean'

    # The stub carries the uncertainty clause and omits only the gap statement, so
    # the gap diagnostic is the ONLY OpenCode problem — a regression in the gap
    # check then reddens this control instead of hiding behind the uncertainty one.
    _plant(
        tmp_path,
        {
            'opencode': (
                '---\ndescription: A stub command.\n---\n\nThe effect is **not shown by reading** in this repository.\n'
            )
        },
    )
    reported = _operator_only_violations(_entry_texts(tmp_path))
    assert any('opencode' in problem and _GAP_CLAUSE in problem for problem in reported), (
        f'a harness without the key and without the recorded gap must be reported by its gap diagnostic, got {reported}'
    )

    keyed_only = (
        '---\nname: apply-changes\ndescription: A stub entry point.\n'
        f'{_OPERATOR_ONLY_KEY}: true\n---\n\nRuns the sequence.\n'
    )
    _plant(tmp_path, {'claude': keyed_only})
    reported = _operator_only_violations(_entry_texts(tmp_path))
    assert any(_UNCONFIRMED_CLAUSE in problem for problem in reported), (
        f'an unconfirmed claim relabelled as confirmed must be reported, got {reported}'
    )

    keyed_opencode = (
        f'---\ndescription: A stub command.\n{_OPERATOR_ONLY_KEY}: true\n---\n\nNothing is recorded here.\n'
    )
    _plant(tmp_path, {'opencode': keyed_opencode})
    reported = _operator_only_violations(_entry_texts(tmp_path))
    assert any('opencode' in problem and _UNCONFIRMED_CLAUSE in problem for problem in reported), (
        f'a keyed non-Claude entry point that omits the uncertainty tag must still be reported, got {reported}'
    )


def test_missing_entry_point_control(tmp_path: Path):
    """Matched control: a harness with no entry point is reported, and the real tree is not."""
    claude_only = tmp_path / _ENTRY_POINT_PATHS['claude']
    claude_only.parent.mkdir(parents=True)
    claude_only.write_text(_read(PROJECT_ROOT, _ENTRY_POINT_PATHS['claude']), encoding='utf-8')

    assert _missing_entry_points(tmp_path), 'an absent entry point must be reported'
    assert _missing_entry_points() == [], 'the real tree carries all three'
    assert _harness_coverage_violations({'claude': _ENTRY_POINT_PATHS['claude']}), (
        'an undeclared harness must be reported'
    )
    assert _harness_coverage_violations(_ENTRY_POINT_PATHS) == [], 'the real mapping covers every harness'


def test_name_and_description_controls(tmp_path: Path):
    """Matched control: a wrong name, a declared OpenCode name and a located description all fire."""
    claude = _read(PROJECT_ROOT, _ENTRY_POINT_PATHS['claude'])
    opencode = _read(PROJECT_ROOT, _ENTRY_POINT_PATHS['opencode'])

    _plant(tmp_path, {'claude': claude.replace(f'name: {_COMMAND_NAME}', 'name: sync-harnesses', 1)})
    assert _frontmatter_violations(_entry_texts(tmp_path)), 'a wrong skill name must be reported'

    _plant(tmp_path, {'opencode': opencode.replace('---\n', f'---\nname: {_COMMAND_NAME}\n', 1)})
    assert _frontmatter_violations(_entry_texts(tmp_path)), 'a name on an OpenCode command must be reported'

    _plant(tmp_path, {})
    assert _frontmatter_violations(_entry_texts(tmp_path)) == [], 'the unmodified entry points must stay clean'

    _plant(
        tmp_path,
        {'claude': claude.replace('description: Carry', 'description: Write the plugin cache, Carry', 1)},
    )
    assert _description_violations(_entry_texts(tmp_path)), 'a harness-located description must be reported'
    assert _description_violations(_entry_texts()) == [], 'the shipped descriptions are harness-neutral'


def test_settings_permission_control(tmp_path: Path):
    """Matched control: settings without the two entries are reported, the real file is not."""
    planted = tmp_path / '.claude'
    planted.mkdir()
    (planted / 'settings.json').write_text(
        json.dumps({'permissions': {'allow': ['Skill(sync-harnesses)', 'Skill(sync-harnesses:*)']}}),
        encoding='utf-8',
    )

    assert _settings_violations(_settings_allow(tmp_path)) == list(_SKILL_PERMISSIONS), (
        'absent entries must be reported'
    )
    assert _settings_violations(_settings_allow()) == [], 'the real settings allow both entries'


def test_a_harness_that_gains_the_withholding_key_is_detected(tmp_path: Path):
    """Matched control: the gap statement is checked against the file it cites.

    A prose-only guard would stay green the day a harness publishes the key. The
    planted rules file carries it, and the entry point's gap sentence must then be
    reported as false.
    """
    _plant(tmp_path, {})
    rules_path = tmp_path / _HARNESS_RULES_FILES['opencode']
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text(
        json.dumps({'required_fields': ['description'], 'optional_fields': [_OPERATOR_ONLY_KEY]}),
        encoding='utf-8',
    )

    assert _gap_claim_contradicted(tmp_path, 'opencode'), 'a rules file carrying the key must be detected'
    assert not _gap_claim_contradicted(PROJECT_ROOT, 'opencode'), 'the shipped opencode rules carry no such key'
    reported = _operator_only_violations(_entry_texts(tmp_path), tmp_path)
    assert any('gap statement is now false' in problem for problem in reported), (
        f'a gap claim the harness metadata contradicts must be reported, got {reported}'
    )


def test_reordered_step_control(tmp_path: Path):
    """Matched control: an exchanged step is reported, and the unmodified entry point is not."""
    claude = _read(PROJECT_ROOT, _ENTRY_POINT_PATHS['claude'])
    _plant(tmp_path, {'claude': swap_lines(claude, _ENGINE_CALL, _REGENERATE_CALL)})

    assert _sequence_violations(_entry_texts(tmp_path)['claude']), 'a reordered step must be reported'
    assert _sequence_violations(claude) == [], 'the unmodified entry point must stay clean'


def test_engine_repin_control(tmp_path: Path):
    """Matched control: a ``--repin`` on the engine call is reported, and the bare call is not."""
    claude = _read(PROJECT_ROOT, _ENTRY_POINT_PATHS['claude'])
    _plant(tmp_path, {'claude': claude.replace(_ENGINE_CALL, f'{_ENGINE_CALL} --repin')})

    assert _engine_and_repin_violations(_entry_texts(tmp_path)['claude']), 'a --repin on the engine must be reported'
    assert _engine_and_repin_violations(claude) == [], 'the bare engine call must stay clean'


def test_ungated_step_controls(tmp_path: Path):
    """Matched control: each follow-up step's gate is checked, one step at a time."""
    claude = _read(PROJECT_ROOT, _ENTRY_POINT_PATHS['claude'])

    for occurrence in range(1, len(_GATED_STEPS) + 1):
        _plant(tmp_path, {'claude': replace_nth(claude, 'cache_status: success', 'the sync outcome', occurrence)})
        reported = _gate_violations(_entry_texts(tmp_path)['claude'])
        assert f'step {occurrence + 2} should gate on cache_status: success' in reported, (
            f'stripping the gate from step {occurrence + 2} must be reported, got {reported}'
        )

    _plant(tmp_path, {'claude': claude.replace('only when', 'regardless of whether', 1)})
    assert 'step 3 states the gate without a restrictive condition' in _gate_violations(
        _entry_texts(tmp_path)['claude']
    ), 'a gate literal that no longer restricts its step must be reported'

    assert _gate_violations(claude) == [], 'the gated entry point must stay clean'


def test_direct_wrapper_control(tmp_path: Path):
    """Matched control: a direct ``./pw`` call is reported, and the executor form is not."""
    claude = _read(PROJECT_ROOT, _ENTRY_POINT_PATHS['claude'])
    _plant(tmp_path, {'claude': claude.replace(_GENERATE_CALLS[0], './pw generate-claude')})

    assert _direct_wrapper_violations(_entry_texts(tmp_path)['claude']), 'a direct ./pw call must be reported'
    assert _direct_wrapper_violations(claude) == [], 'the executor form must stay clean'


def test_diverged_mirror_control(tmp_path: Path):
    """Matched control: a diverged post-run block is reported, and the identical ones are not."""
    antigravity = _read(PROJECT_ROOT, _ENTRY_POINT_PATHS['antigravity'])
    _plant(tmp_path, {'antigravity': f'{antigravity}\n> 4. **Extra** — a line no other entry point carries.\n'})

    assert _mirror_violations(_entry_texts(tmp_path)), 'a diverged post-run block must be reported'
    assert _mirror_violations(_entry_texts()) == [], 'the identical entry points must stay clean'


def test_reload_and_restart_controls(tmp_path: Path):
    """Matched control: a reload outside the block and a block without the restart both fire."""
    claude = _read(PROJECT_ROOT, _ENTRY_POINT_PATHS['claude'])

    _plant(tmp_path, {'claude': f'{claude}\nRun {_RELOAD_PLUGINS} when the agents look stale.\n'})
    assert _mirror_violations(_entry_texts(tmp_path)), f'{_RELOAD_PLUGINS} outside the block must be reported'

    clean = _entry_texts()
    _plant(tmp_path, {harness: text.replace('restart', 'relaunch') for harness, text in clean.items()})
    assert 'the post-run block should name the restart' in _mirror_violations(_entry_texts(tmp_path)), (
        'a block that never names the restart must be reported by its own check'
    )

    _plant(
        tmp_path,
        {harness: text.replace(_RELOAD_SENTENCE, 'a reload is usually enough') for harness, text in clean.items()},
    )
    assert f'the post-run block should state that {_RELOAD_PLUGINS} alone is not sufficient' in _mirror_violations(
        _entry_texts(tmp_path)
    ), 'a block without the reload sentence must be reported by its own check'

    assert _mirror_violations(_entry_texts()) == [], 'the entry points name it only inside the block'


def test_step_block_splitter_reads_both_numbering_styles():
    """Matched control for the step reader: both styles resolve, and a missing step stays missing."""
    claude_style = '### Step 3: Regenerate\n\ncache_status: success\n\n### Step 4: Reconcile\n'
    opencode_style = '3. Regenerate\n\n   cache_status: success\n\n4. Reconcile\n'

    assert sorted(step_blocks(claude_style)) == [3, 4]
    assert 'cache_status: success' in step_blocks(claude_style)[3]
    assert sorted(step_blocks(opencode_style)) == [3, 4]
    assert step_blocks('no steps here') == {}
