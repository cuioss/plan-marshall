# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Claude target equality-check engine.

The engine compares ``build_plugin_json(bundle_dir)`` (regenerated from
the source bundle's frontmatter scan) against the emitted artifact at
``target/claude/{bundle}/.claude-plugin/plugin.json``. The source
bundle's committed ``plugin.json`` is no longer the source of truth.
"""

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.emitter import iter_bundle_dirs
from marketplace.targets.claude.equality_check import check_bundle, run_equality_check


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _emitted(target_dir: Path, bundle_name: str, plugin_doc: dict) -> None:
    """Helper: write an emitted plugin.json into target_dir."""
    _write(
        target_dir / bundle_name / '.claude-plugin' / 'plugin.json',
        json.dumps(plugin_doc, indent=2) + '\n',
    )


def _write_source_marketplace(root: Path, plugin_names: list[str]) -> None:
    """Write a minimal source marketplace.json under ``root/.claude-plugin/``."""
    manifest = {
        'name': 'demo-marketplace',
        'plugins': [
            {'name': name, 'description': name, 'source': f'./bundles/{name}'}
            for name in plugin_names
        ],
    }
    _write(root / '.claude-plugin' / 'marketplace.json', json.dumps(manifest, indent=2) + '\n')


@pytest.fixture()
def clean_marketplace(tmp_path: Path) -> tuple[Path, Path]:
    """Source bundle + matching emitted artifact under target/claude/.

    The source bundle's committed plugin.json may still declare a ``skills``
    array (informational metadata), but the regenerator emits ``skills: []``
    so the runtime's default ``skills/`` folder scan owns skill discovery
    without double-loading. The emitted artifact mirrors what the build
    target produces, not the source's metadata view.
    """
    marketplace_root = tmp_path
    marketplace = marketplace_root / 'bundles'
    target = tmp_path / 'target' / 'claude'
    bundle = marketplace / 'demo'

    # Source plugin.json keeps the legacy skills metadata for top-level
    # passthrough; the emitted artifact uses the new empty-skills convention.
    source_plugin_doc = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'agents': ['./agents/demo-agent.md'],
        'commands': [],
        'skills': ['./skills/alpha-skill', './skills/zeta-skill'],
    }
    emitted_plugin_doc = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'agents': ['./agents/demo-agent.md'],
        'commands': [],
        'skills': [],
    }
    _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps(source_plugin_doc, indent=2) + '\n')
    _write(bundle / 'agents' / 'demo-agent.md', '---\nname: demo-agent\n---\nbody\n')
    _write(bundle / 'skills' / 'alpha-skill' / 'SKILL.md', '---\nname: alpha-skill\ndescription: a\n---\n')
    _write(bundle / 'skills' / 'zeta-skill' / 'SKILL.md', '---\nname: zeta-skill\ndescription: z\n---\n')
    _emitted(target, 'demo', emitted_plugin_doc)

    # The equality engine now also diffs the top-level marketplace.json.
    # Write both source and emitted manifests so the clean fixture passes.
    _write_source_marketplace(marketplace_root, ['demo'])
    _write(
        target / '.claude-plugin' / 'marketplace.json',
        json.dumps(
            {
                'name': 'demo-marketplace',
                'plugins': [{'name': 'demo', 'description': 'demo', 'source': './demo'}],
            },
            indent=2,
        )
        + '\n',
    )
    return marketplace, target


def test_clean_tree_passes(clean_marketplace: tuple[Path, Path]):
    marketplace, target = clean_marketplace
    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is True
    assert result.diffs == []
    assert 'passed' in result.summary


def test_added_agent_without_target_update_drift(clean_marketplace: tuple[Path, Path]):
    """New source agent without re-emit: surfaces as `only_in_generated`."""
    marketplace, target = clean_marketplace
    new_agent = marketplace / 'demo' / 'agents' / 'second-agent.md'
    _write(new_agent, '---\nname: second-agent\n---\nbody\n')
    diffs = check_bundle(marketplace / 'demo', target)
    agents_diff = next((d for d in diffs if d.field == 'agents'), None)
    assert agents_diff is not None
    assert './agents/second-agent.md' in agents_diff.only_in_generated
    assert './agents/second-agent.md' not in (agents_diff.only_in_committed or [])


def test_orphan_target_entry_drift(clean_marketplace: tuple[Path, Path]):
    """Stale entry only in the emitted target: surfaces as `only_in_committed`."""
    marketplace, target = clean_marketplace
    plugin_path = target / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_doc = json.loads(plugin_path.read_text(encoding='utf-8'))
    plugin_doc['agents'].append('./agents/ghost-agent.md')  # not on disk in source
    plugin_doc['agents'].sort()
    plugin_path.write_text(json.dumps(plugin_doc, indent=2) + '\n', encoding='utf-8')

    diffs = check_bundle(marketplace / 'demo', target)
    agents_diff = next((d for d in diffs if d.field == 'agents'), None)
    assert agents_diff is not None
    assert './agents/ghost-agent.md' in agents_diff.only_in_committed


def test_skills_field_never_drifts_regardless_of_disk_state(clean_marketplace: tuple[Path, Path]):
    """``skills`` is always ``[]`` in the regenerated artifact — adding or
    removing skill dirs on disk must NOT produce drift in the skills field.
    The runtime owns skill discovery via its default ``skills/`` folder scan.
    """
    marketplace, target = clean_marketplace
    _write(
        marketplace / 'demo' / 'skills' / 'new-skill' / 'SKILL.md',
        '---\nname: new-skill\ndescription: n\n---\n',
    )
    diffs = check_bundle(marketplace / 'demo', target)
    assert not any(d.field == 'skills' for d in diffs)


def test_marketplace_json_drift_surfaces(clean_marketplace: tuple[Path, Path]):
    """If the emitted marketplace.json differs from a fresh regeneration,
    the equality check fails with ``marketplace_json_drift=True``.
    """
    marketplace, target = clean_marketplace
    # Mutate the emitted marketplace.json to introduce drift.
    emitted = target / '.claude-plugin' / 'marketplace.json'
    doc = json.loads(emitted.read_text(encoding='utf-8'))
    doc['plugins'][0]['source'] = './stale-name'
    emitted.write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is False
    assert result.marketplace_json_drift is True
    assert 'marketplace.json' in result.summary


def test_missing_top_level_marketplace_json_surfaces(clean_marketplace: tuple[Path, Path]):
    """If target/claude/.claude-plugin/marketplace.json is missing entirely,
    the equality check fails and the summary names the missing artifact.
    """
    marketplace, target = clean_marketplace
    (target / '.claude-plugin' / 'marketplace.json').unlink()
    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is False
    assert result.marketplace_json_drift is True
    assert 'marketplace.json' in result.summary


def test_orphan_agent_file_in_target_surfaces_drift(clean_marketplace: tuple[Path, Path]):
    """An ``agents/*.md`` file physically present in target/claude/{bundle}/
    that is NOT declared in the emitted plugin.json must surface as drift.
    This catches stale leftovers from a previous emit run (e.g. variants for
    a source canonical that has since been deleted) which the manifest-only
    check cannot see.
    """
    marketplace, target = clean_marketplace
    orphan = target / 'demo' / 'agents' / 'ghost-agent.md'
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text('---\nname: ghost-agent\n---\nstale body\n', encoding='utf-8')

    diffs = check_bundle(marketplace / 'demo', target)
    orphan_diff = next((d for d in diffs if d.field == 'agents-orphans'), None)
    assert orphan_diff is not None
    assert orphan_diff.only_in_committed == ['./agents/ghost-agent.md']


def test_orphan_command_file_in_target_surfaces_drift(clean_marketplace: tuple[Path, Path]):
    """Same invariant for the ``commands/`` directory: a file on disk that
    is not declared in the emitted plugin.json surfaces as drift.
    """
    marketplace, target = clean_marketplace
    orphan = target / 'demo' / 'commands' / 'ghost-command.md'
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text('---\nname: ghost-command\n---\nstale\n', encoding='utf-8')

    diffs = check_bundle(marketplace / 'demo', target)
    orphan_diff = next((d for d in diffs if d.field == 'commands-orphans'), None)
    assert orphan_diff is not None
    assert orphan_diff.only_in_committed == ['./commands/ghost-command.md']


def test_clean_target_has_no_orphan_drift(clean_marketplace: tuple[Path, Path]):
    """Sanity check: when every on-disk agent/command file IS declared in
    the emitted plugin.json, no orphan drift is reported.
    """
    marketplace, target = clean_marketplace
    # The fixture emits exactly the declared agent file (./agents/demo-agent.md)
    # — write it on disk so the orphan check has something to match against.
    declared_agent = target / 'demo' / 'agents' / 'demo-agent.md'
    declared_agent.parent.mkdir(parents=True, exist_ok=True)
    declared_agent.write_text('---\nname: demo-agent\n---\nbody\n', encoding='utf-8')

    diffs = check_bundle(marketplace / 'demo', target)
    assert not any(d.field.endswith('-orphans') for d in diffs)


def test_run_equality_check_summary_mentions_bundles(clean_marketplace: tuple[Path, Path]):
    marketplace, target = clean_marketplace
    new_agent = marketplace / 'demo' / 'agents' / 'second-agent.md'
    _write(new_agent, '---\nname: second-agent\n---\nbody\n')

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is False
    assert 'demo' in result.summary
    assert 'failed' in result.summary


def test_missing_target_dir_returns_diagnostic(clean_marketplace: tuple[Path, Path]):
    """Absent target/claude/ root produces a structured diagnostic, not a crash."""
    marketplace, _target = clean_marketplace
    nowhere = marketplace.parent / 'target' / 'does-not-exist'
    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(nowhere, bundles)
    assert result.passed is False
    assert 'not generated' in result.summary
    assert 'generate.py --target claude' in result.summary
    assert result.unusable_target_bundles == ['demo']


def test_missing_per_bundle_target_returns_diagnostic(clean_marketplace: tuple[Path, Path]):
    """target/claude exists but a specific bundle's plugin.json is missing."""
    marketplace, target = clean_marketplace
    # Wipe the demo bundle's emitted plugin.json
    (target / 'demo' / '.claude-plugin' / 'plugin.json').unlink()
    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)
    assert result.passed is False
    assert 'demo' in result.summary
    assert 'missing' in result.summary
    assert result.unusable_target_bundles == ['demo']


def test_corrupt_emitted_plugin_json_returns_diagnostic(clean_marketplace: tuple[Path, Path]):
    """A corrupt (invalid JSON) emitted plugin.json returns the documented
    're-run emit' diagnostic instead of crashing the equality CLI with a
    traceback — mirroring the adjacent, already-guarded marketplace.json read.
    """
    marketplace, target = clean_marketplace
    plugin_path = target / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_path.write_text('{ not valid json ', encoding='utf-8')

    bundles = list(iter_bundle_dirs(marketplace, None))
    # Must return a structured result, NOT raise json.JSONDecodeError.
    result = run_equality_check(target, bundles)
    assert result.passed is False
    assert 'demo' in result.summary
    assert 'generate.py --target claude' in result.summary
    assert 'demo' in result.unusable_target_bundles


#: Valid JSON documents that are NOT objects. Each parses without a
#: ``JSONDecodeError``, so a decode-only guard passes them straight through to
#: readers that call ``.get(...)`` on them.
_VALID_JSON_NON_OBJECTS = ['[]', '"x"', 'null', '3']


@pytest.mark.parametrize('payload', _VALID_JSON_NON_OBJECTS, ids=['array', 'string', 'null', 'number'])
def test_valid_json_that_is_not_an_object_returns_the_diagnostic(
    clean_marketplace: tuple[Path, Path], payload: str
):
    """A parseable non-object is unusable too, and must not escape as a traceback.

    A guard keyed on ``JSONDecodeError`` alone covers only half of "unusable":
    each payload here decodes cleanly, then fails several frames away when the
    diff calls ``.get('agents')`` on a list, a string, ``None`` or an int. The
    documented contract is a structured re-run-emit result for every emitted
    artifact the engine cannot compare — not for the subset that happens to be
    syntactically broken.
    """
    marketplace, target = clean_marketplace
    plugin_path = target / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_path.write_text(payload, encoding='utf-8')

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)

    assert result.passed is False
    assert 'demo' in result.unusable_target_bundles
    assert 'generate.py --target claude' in result.summary


def test_an_unreadable_emitted_plugin_json_returns_the_diagnostic(
    clean_marketplace: tuple[Path, Path]
):
    """A path that exists but cannot be READ is unusable in the same way.

    ``read_text`` raises ``OSError`` when the path is a directory or permissions
    deny it. ``OSError`` is not ``JSONDecodeError``, so it was never converted
    into ``CorruptEmittedPluginJsonError`` and escaped the caller's ``except``,
    terminating the whole equality check instead of producing the documented
    re-emit diagnostic for one bundle.
    """
    marketplace, target = clean_marketplace
    plugin_path = target / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_path.unlink()
    plugin_path.mkdir()

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)

    assert result.passed is False
    assert result.unusable_target_bundles == ['demo']
    assert 'generate.py --target claude' in result.summary


def test_undecodable_bytes_in_an_emitted_plugin_json_return_the_diagnostic(
    clean_marketplace: tuple[Path, Path]
):
    """Bytes that are not valid UTF-8 raise ``UnicodeDecodeError``, not a decode error.

    ``UnicodeDecodeError`` derives from ``ValueError`` and is raised by
    ``read_text`` BEFORE ``json.loads`` is ever reached, so the
    ``JSONDecodeError`` guard cannot see it.
    """
    marketplace, target = clean_marketplace
    plugin_path = target / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_path.write_bytes(b'{"name": "\xff"}')

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)

    assert result.passed is False
    assert result.unusable_target_bundles == ['demo']


@pytest.mark.parametrize('field_name', ['agents', 'commands', 'skills'])
def test_a_non_list_array_field_returns_the_diagnostic(
    clean_marketplace: tuple[Path, Path], field_name: str
):
    """``isinstance(parsed, dict)`` is not the whole of "usable".

    The diff calls ``list()`` on every array field and ``set()`` on two of them,
    so an object declaring one as a scalar passes the object check and then
    raises ``TypeError`` from inside ``check_bundle`` — again escaping the
    caller's ``except``, which catches only ``CorruptEmittedPluginJsonError``.
    """
    marketplace, target = clean_marketplace
    doc: dict = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'agents': ['./agents/demo-agent.md'],
        'commands': [],
        'skills': [],
    }
    doc[field_name] = 3
    _emitted(target, 'demo', doc)

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)

    assert result.passed is False
    assert result.unusable_target_bundles == ['demo']


@pytest.mark.parametrize('field_name', ['agents', 'commands', 'skills'])
@pytest.mark.parametrize(
    'element',
    [{'path': './agents/demo-agent.md'}, 3],
    ids=['unhashable-object', 'hashable-non-string'],
)
def test_a_list_holding_a_non_string_element_returns_the_diagnostic(
    clean_marketplace: tuple[Path, Path], field_name: str, element: object
):
    """Validating the CONTAINER is not validating the contract.

    The guard above proves the value is a ``list``; the caller's contract is a
    list OF STRINGS. ``check_bundle`` builds a ``set`` from each array, so an
    unhashable element (an object) raises ``TypeError`` several frames away and
    escapes the caller's ``except`` — terminating the whole equality check
    instead of reporting this one bundle as needing a re-emit, which is exactly
    the outcome this guard exists to prevent. A hashable non-string (an int)
    does not even crash: it compares unequal to every generated entry and is
    reported as ordinary manifest drift, so the artifact's corruption is
    misdiagnosed as a re-emittable difference. Both are refused HERE.
    """
    marketplace, target = clean_marketplace
    doc: dict = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'agents': ['./agents/demo-agent.md'],
        'commands': [],
        'skills': [],
    }
    doc[field_name] = [element]
    _emitted(target, 'demo', doc)

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)

    assert result.passed is False
    assert result.unusable_target_bundles == ['demo']


def test_a_list_of_strings_is_still_accepted(clean_marketplace: tuple[Path, Path]):
    """Matched control: element validation must not refuse the ordinary artifact.

    A guard that rejected every populated array would satisfy the case above
    while failing every real bundle, so the well-formed shape — a populated
    ``agents`` list of strings alongside two empty lists — is pinned as
    accepted, with the equality verdict clean.
    """
    marketplace, target = clean_marketplace

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)

    emitted = json.loads(
        (target / 'demo' / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8')
    )
    assert emitted['agents'] == ['./agents/demo-agent.md'], 'fixture precondition'
    assert result.passed is True
    assert result.unusable_target_bundles == []


def test_the_unusable_list_is_named_for_the_outcome_not_one_of_its_causes(
    clean_marketplace: tuple[Path, Path]
):
    """A present-but-corrupt bundle is reported as unusable, never as missing.

    The field carries both causes, so naming it ``missing`` told its reader the
    artifact was absent when in fact it was present and unreadable — a
    different repair. The rename is a clean break: the old name must be gone,
    not aliased, or a caller reading it would keep getting the wrong story.
    """
    marketplace, target = clean_marketplace
    (target / 'demo' / '.claude-plugin' / 'plugin.json').write_text('[]', encoding='utf-8')

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)

    assert result.unusable_target_bundles == ['demo']
    assert not hasattr(result, 'missing_target_bundles'), (
        'the old field name must not survive as an alias — compatibility for '
        'this plan is "breaking", and an alias would let a caller keep reading '
        'a corrupt bundle as a missing one'
    )


def test_the_unusable_list_is_sorted_across_both_causes(clean_marketplace: tuple[Path, Path]):
    """One sort over the union, not two sorted halves concatenated.

    Sorting each cause separately and joining them yields a list that is
    ordered only within each half. The names here are chosen so the two forms
    disagree: the missing bundle sorts AFTER the corrupt one, so a concatenated
    ``sorted(missing) + sorted(corrupt)`` returns them in the wrong order while
    still looking sorted at a glance.
    """
    marketplace, target = clean_marketplace
    # A second source bundle whose emitted artifact is present but unusable.
    _write(
        marketplace / 'aaa' / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': 'aaa', 'version': '0.0.1', 'description': 'a'}, indent=2) + '\n',
    )
    _write(target / 'aaa' / '.claude-plugin' / 'plugin.json', '[]')
    # ...and the first bundle's artifact is absent.
    (target / 'demo' / '.claude-plugin' / 'plugin.json').unlink()

    bundles = list(iter_bundle_dirs(marketplace, None))
    result = run_equality_check(target, bundles)

    assert result.unusable_target_bundles == ['aaa', 'demo']
