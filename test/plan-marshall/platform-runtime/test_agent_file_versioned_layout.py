#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The agent-file lookup resolves the versioned deployed bundle-cache layout.

The Claude plugin cache deploys ``{root}/{bundle}/{version}/agents/{name}.md``,
one version directory per sync. The seam used to glob only the source-tree
shape — ``{root}/{bundle}/agents/{name}.md``, one level — so an installed
``execution-context-level-{N}`` variant, which exists ONLY in that deployed
layout and never in the source tree, was unresolvable and every dispatch of it
answered ``prompt_not_found``.

The fixture below is that deployed layout, carrying the frontmatter shape a real
agent does (a block-scalar description and a ``tools:`` list). It drives the
shared lookup ``runtime_base._find_agent_file`` directly and through the three
runtimes that consume it: Claude through ``claude_runtime._find_agent_file`` on
its dispatch path — the one runtime that supplies a deployed root — and
OpenCode and Antigravity through the shared ``_unmapped_agent_tools``
tool-mapping check their dispatches run, which supplies none.
"""

from pathlib import Path

import claude_runtime
import platform_runtime
import pytest
import runtime_base
from claude_runtime import ClaudeRuntime
from toon_parser import parse_toon

from conftest import MARKETPLACE_ROOT

#: The variant-suffixed name the seam could not resolve. Generated per target by
#: the variant emitter, so it exists only in a deployed tree.
VARIANT = 'execution-context-level-3'

#: The bare name, which also exists in the source tree and must keep resolving.
BARE = 'execution-context'

OLD_VERSION = '0.1.2135'
NEW_VERSION = '0.1.2139'

_AGENT_BODY = """---
name: {name}
description: |
  Dispatches one envelope into a focused subagent. The deployed variant keeps
  this description, so anything that renders it must not render the marker.

  Examples:
  - Input: name=push, plan_id=EXAMPLE
  - Output: TOON with status and the workflow's return fields
tools: Read, Grep
---

Run {name}.
"""


def _parsed(raw: str) -> dict:
    """Parse a TOON string and assert it is a non-empty dict."""
    result = parse_toon(raw)
    assert isinstance(result, dict), f'parse_toon returned non-dict: {raw!r}'
    return result


def _write_agent(version_dir: Path, name: str) -> Path:
    """Create ``{version_dir}/agents/{name}.md`` and return the file path."""
    agents_dir = version_dir / 'agents'
    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agents_dir / f'{name}.md'
    agent_file.write_text(_AGENT_BODY.format(name=name), encoding='utf-8')
    return agent_file


@pytest.fixture()
def deployed_cache(tmp_path: Path) -> Path:
    """A Claude plugin-cache root holding two installed versions of the bundle.

    Shape: ``{root}/plan-marshall/{version}/agents/execution-context-level-3.md``.
    The newer version dir is the live one for that agent.
    """
    root = tmp_path / 'cache' / 'plan-marshall'
    for version in (OLD_VERSION, NEW_VERSION):
        _write_agent(root / 'plan-marshall' / version, VARIANT)
    return root


@pytest.fixture()
def empty_cache(tmp_path: Path) -> Path:
    """A cache root with no bundle and therefore no agent file under it."""
    root = tmp_path / 'empty-cache' / 'plan-marshall'
    root.mkdir(parents=True)
    return root


# =============================================================================
# 1. The shared lookup — deployed layout, flat layout, source tree, miss
# =============================================================================


def test_shared_lookup_resolves_the_versioned_layout(deployed_cache: Path) -> None:
    """The deployed ``{bundle}/{version}/agents/`` shape resolves the variant.

    Two version dirs carry the agent, so this also pins newest-eligible-wins:
    an older or lexically-last choice would answer a different path.
    """
    resolved = runtime_base._find_agent_file(VARIANT, (deployed_cache,))
    assert resolved == deployed_cache / 'plan-marshall' / NEW_VERSION / 'agents' / f'{VARIANT}.md'


def test_shared_lookup_falls_back_to_the_only_version_that_carries_the_agent(deployed_cache: Path) -> None:
    """Eligibility, not recency alone: the newest dir WITHOUT the agent is skipped."""
    newest = deployed_cache / 'plan-marshall' / '0.1.9999'
    (newest / 'agents').mkdir(parents=True)
    resolved = runtime_base._find_agent_file(VARIANT, (deployed_cache,))
    assert resolved == deployed_cache / 'plan-marshall' / NEW_VERSION / 'agents' / f'{VARIANT}.md'


def test_shared_lookup_keeps_the_flat_layout_first(tmp_path: Path) -> None:
    """A root carrying both shapes answers its flat one."""
    root = tmp_path / 'both-shapes'
    flat = _write_agent(root / 'plan-marshall', VARIANT)
    _write_agent(root / 'plan-marshall' / NEW_VERSION, VARIANT)
    assert runtime_base._find_agent_file(VARIANT, (root,)) == flat


def test_a_flat_hit_in_a_later_root_beats_a_versioned_hit_in_an_earlier_one(tmp_path: Path) -> None:
    """The flat shape is probed across all roots before the versioned shape starts.

    That is what keeps a bare name resolving from the source tree in a checkout,
    where the deployed cache carries the same name one level deeper.
    """
    deployed = tmp_path / 'deployed'
    source = tmp_path / 'source'
    versioned = _write_agent(deployed / 'plan-marshall' / NEW_VERSION, BARE)
    flat = _write_agent(source / 'plan-marshall', BARE)
    assert versioned != flat
    assert runtime_base._find_agent_file(BARE, (deployed, source)) == flat


def test_bare_name_still_resolves_from_the_source_tree() -> None:
    """The source-tree walk is unchanged: the bare name resolves with no extra root."""
    resolved = runtime_base._find_agent_file(BARE)
    assert resolved is not None
    assert resolved.name == f'{BARE}.md'
    assert resolved.parent.name == 'agents'
    assert resolved.parent.parent.name == 'plan-marshall'


def test_missing_agent_returns_no_file(deployed_cache: Path) -> None:
    """An agent no root carries is still a miss, not a neighbouring file."""
    assert runtime_base._find_agent_file('no-such-agent', (deployed_cache,)) is None


def test_a_path_shaped_name_cannot_escape_the_root(deployed_cache: Path) -> None:
    """``--agent`` is a file stem, and a name that escapes resolves to nothing.

    The escape is planted, so the assertion is load-bearing: without the guard
    the versioned pass joins ``../../outside-execution-context.md`` under
    ``{bundle}/{version}/agents/`` and lands on exactly this file.
    """
    planted = deployed_cache / 'plan-marshall' / 'outside-execution-context.md'
    planted.write_text(_AGENT_BODY.format(name='outside-execution-context'), encoding='utf-8')

    assert runtime_base._find_agent_file('../../outside-execution-context', (deployed_cache,)) is None
    # Control: the same root DOES resolve a plain stem, so the guard is what
    # refused the escaped name rather than an unreachable fixture.
    assert runtime_base._find_agent_file(VARIANT, (deployed_cache,)) is not None


def test_a_glob_shaped_name_selects_no_agent(tmp_path: Path) -> None:
    """``--agent '*'`` resolves nothing: the name is a stem, never a pattern.

    The root carries a FLAT agent file, which is the shape the flat pass globs,
    so without the character guard ``*`` selects it and the caller dispatches an
    agent it never named. (The deployed root cannot prove this: its agents sit
    one level deeper than the flat glob reaches.)
    """
    root = tmp_path / 'flat-cache'
    _write_agent(root / 'plan-marshall', BARE)

    assert runtime_base._find_agent_file('*', (root,)) is None
    assert runtime_base._find_agent_file(f'{BARE}*', (root,)) is None
    # Control: the plain stem resolves from this very root.
    assert runtime_base._find_agent_file(BARE, (root,)) is not None


def test_search_roots_are_the_ones_probed(deployed_cache: Path) -> None:
    """The reported roots are the deployed root first, then the source tree."""
    roots = runtime_base._agent_search_roots((deployed_cache,))
    assert roots[0] == deployed_cache
    assert any(root.name == 'bundles' for root in roots[1:]), 'the source-tree root is not reported'


def test_the_versioned_pass_walks_every_bundle_under_a_root(tmp_path: Path) -> None:
    """A cache holding several bundles resolves an agent from any of them."""
    root = tmp_path / 'multi-bundle'
    _write_agent(root / 'other-bundle' / NEW_VERSION, 'other-agent')
    expected = _write_agent(root / 'plan-marshall' / NEW_VERSION, VARIANT)
    assert runtime_base._find_agent_file(VARIANT, (root,)) == expected


def test_an_unreadable_root_is_a_miss(tmp_path: Path) -> None:
    """A root that is not a directory cannot be listed, and is a miss, not a raise."""
    not_a_directory = tmp_path / 'not-a-directory'
    not_a_directory.write_text('x', encoding='utf-8')
    assert runtime_base._find_agent_file(VARIANT, (not_a_directory,)) is None


# =============================================================================
# 2. Claude — the dispatch path that answered prompt_not_found
# =============================================================================


def test_claude_dispatch_resolves_the_variant_from_the_cache(
    deployed_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--agent execution-context-level-3`` succeeds when the cache holds the file.

    Also pins the description the contract's Claude example shows: it is the
    agent frontmatter's own text, truncated to five words. A block-scalar
    description read as a plain ``key: value`` pair renders the ``|`` marker
    instead, which is what the example used to claim was a sentence. The fixture
    carries the paragraph break and the example list a real agent does, so the
    truncation is exercised over a block that spans them.
    """
    monkeypatch.setattr(claude_runtime, '_claude_bundle_cache_root', lambda: deployed_cache)

    result = _parsed(ClaudeRuntime().subagent_dispatch(VARIANT, None, None))

    assert result['status'] == 'success'
    assert result['invocation']['subagent_type'] == VARIANT
    assert result['invocation']['description'] == 'Dispatches one envelope into a'


def test_claude_dispatch_miss_names_the_roots_it_searched(empty_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An agent-file miss reports the roots, not just the name."""
    monkeypatch.setattr(claude_runtime, '_claude_bundle_cache_root', lambda: empty_cache)

    result = _parsed(ClaudeRuntime().subagent_dispatch(VARIANT, None, None))

    assert result['status'] == 'error'
    assert result['error'] == 'prompt_not_found'
    message = result['message']
    assert str(empty_cache) in message, 'the searched cache root is not named'
    for root in runtime_base._agent_search_roots():
        assert str(root) in message, f'the searched root {root} is not named'


# =============================================================================
# 3. Every runtime that consumes the shared lookup
# =============================================================================

#: The admitted runtimes, derived live from the router's registry — a target
#: added there must not be silently excluded from these tests.
_RUNTIMES = tuple(platform_runtime._REGISTRY.items())

assert _RUNTIMES, 'the runtime population derived from the router registry is empty'

_RUNTIME_TARGETS = frozenset(name for name, _ in _RUNTIMES)


def test_the_registry_admits_every_target_this_seam_serves() -> None:
    """The derived population is the three targets the seam serves today.

    A TEST rather than an import-time assertion: a registry change then reddens
    one test with a message instead of breaking collection for the whole module,
    which is what a hard-coded equality pin at module scope would do. A new
    target still has to be checked against this seam and named here deliberately.
    """
    assert _RUNTIME_TARGETS == {'antigravity', 'claude', 'opencode'}


def _versioned_agent_path(cache_root: Path) -> Path:
    """The path the deployed layout gives the variant under *cache_root*."""
    return cache_root / 'plan-marshall' / NEW_VERSION / 'agents' / f'{VARIANT}.md'


@pytest.mark.parametrize('target, runtime_cls', _RUNTIMES)
def test_every_runtime_resolves_the_variant_from_the_deployed_layout(
    target: str,
    runtime_cls: type,
    deployed_cache: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The versioned layout resolves for each runtime that shares the lookup.

    Claude is driven through the surface it uses in production: its
    deployment-root wrapper, which is its dispatch path.

    OpenCode and Antigravity supply no deployed root (see
    ``test_opencode_and_antigravity_supply_no_deployed_root``), so their leg
    injects one through the shared root computation to prove the lookup they
    call resolves the versioned shape. ``[]`` from ``_unmapped_agent_tools`` is
    the MEASURED "the agent file was read and every declared tool maps";
    ``None`` would be the vacuous "unresolvable".
    """
    if target == 'claude':
        monkeypatch.setattr(claude_runtime, '_claude_bundle_cache_root', lambda: deployed_cache)
        assert claude_runtime._find_agent_file(VARIANT) == _versioned_agent_path(deployed_cache)
    else:
        monkeypatch.setattr(runtime_base, '_agent_search_roots', lambda _extra=(): [deployed_cache])
        assert runtime_base._unmapped_agent_tools(VARIANT, target) == []

    assert _parsed(runtime_cls().subagent_dispatch(VARIANT, None, None))['status'] == 'success'


@pytest.mark.parametrize('target, runtime_cls', _RUNTIMES)
def test_every_runtime_treats_an_absent_agent_as_unmeasured(
    target: str,
    runtime_cls: type,
    empty_cache: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no agent file anywhere, the lookup reports a miss and nothing resolves."""
    if target == 'claude':
        monkeypatch.setattr(claude_runtime, '_claude_bundle_cache_root', lambda: empty_cache)
        result = _parsed(runtime_cls().subagent_dispatch(VARIANT, None, None))
        assert result['status'] == 'error'
        assert result['error'] == 'prompt_not_found'
    else:
        monkeypatch.setattr(runtime_base, '_agent_search_roots', lambda _extra=(): [empty_cache])
        assert runtime_base._unmapped_agent_tools(VARIANT, target) is None


@pytest.mark.parametrize('target', ('opencode', 'antigravity'))
def test_opencode_and_antigravity_supply_no_deployed_root(target: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool-mapping check reaches the shared lookup with no extra root.

    Pins the production wiring the test above compensates for: those two
    runtimes never pass a deployed bundle cache, so their check sees the
    script-relative source tree alone. If either starts supplying a root, this
    assertion goes red and the paragraph in ``contract.md`` that states this
    must be updated with it.
    """
    calls: list[tuple] = []
    real_find = runtime_base._find_agent_file

    def _spy(agent_name: str, extra_roots=()):
        calls.append((agent_name, tuple(extra_roots)))
        return real_find(agent_name, extra_roots)

    monkeypatch.setattr(runtime_base, '_find_agent_file', _spy)

    runtime_base._unmapped_agent_tools(BARE, target)

    assert calls, 'the tool-mapping check did not consult the shared lookup'
    assert calls[0][1] == (), f'{target} supplied a deployed root: {calls[0][1]!r}'


# =============================================================================
# 4. The agent frontmatter reader the resolution feeds
# =============================================================================


def _write_frontmatter(tmp_path: Path, frontmatter: str) -> Path:
    """Write an agent file with the given frontmatter body and return its path."""
    agent_file = tmp_path / 'agent.md'
    agent_file.write_text(f'---\n{frontmatter}\n---\n\nBody.\n', encoding='utf-8')
    return agent_file


@pytest.mark.parametrize('marker', ('|', '|-', '|+', '>', '>-', '|2'))
def test_a_block_scalar_description_never_renders_the_marker(marker: str, tmp_path: Path) -> None:
    """Every block-scalar header form resolves to the block's text."""
    agent_file = _write_frontmatter(
        tmp_path,
        f'name: agent\ndescription: {marker}\n  First line of the description.\n  Second line.\ntools: Read',
    )

    parsed = runtime_base._parse_agent_frontmatter(agent_file)

    assert parsed['description'] == 'First line of the description. Second line.'
    assert parsed['tools'] == ['Read']


def test_a_block_scalar_ends_at_the_next_top_level_key(tmp_path: Path) -> None:
    """A key after the block is not swallowed into the description."""
    agent_file = _write_frontmatter(
        tmp_path,
        'name: agent\ndescription: |\n  Only the description.\ntools: Read, Grep',
    )

    parsed = runtime_base._parse_agent_frontmatter(agent_file)

    assert parsed['description'] == 'Only the description.'
    assert parsed['name'] == 'agent'
    assert parsed['tools'] == ['Read', 'Grep']


def test_a_blank_line_inside_a_block_scalar_does_not_end_it(tmp_path: Path) -> None:
    """A paragraph break inside the block is skipped, not treated as the end.

    The canonical agent's description is two paragraphs separated by a blank
    line; ending the block there would truncate it to its first paragraph.
    """
    agent_file = _write_frontmatter(
        tmp_path,
        'name: agent\ndescription: |\n  First paragraph.\n\n  Second paragraph.\ntools: Read',
    )

    parsed = runtime_base._parse_agent_frontmatter(agent_file)

    assert parsed['description'] == 'First paragraph. Second paragraph.'
    assert parsed['tools'] == ['Read']


def test_an_empty_block_scalar_description_is_empty(tmp_path: Path) -> None:
    """A block with no indented lines is the empty description, not the marker."""
    agent_file = _write_frontmatter(tmp_path, 'name: agent\ndescription: |\ntools: Read')

    assert runtime_base._parse_agent_frontmatter(agent_file)['description'] == ''


def test_key_shaped_text_inside_a_block_scalar_is_not_a_key(tmp_path: Path) -> None:
    """Body text that looks like a key never overwrites a real frontmatter key.

    A block scalar is free text: a description that quotes YAML, or names
    ``tools:`` in prose, must not be re-read as a key line.
    """
    agent_file = _write_frontmatter(
        tmp_path,
        'name: agent\ndescription: |\n  description: Example\n  tools: Write\n  More detail.\ntools: Read',
    )

    parsed = runtime_base._parse_agent_frontmatter(agent_file)

    assert parsed['description'] == 'description: Example tools: Write More detail.'
    assert parsed['name'] == 'agent'
    assert parsed['tools'] == ['Read']


def test_a_tools_list_after_a_block_scalar_is_still_collected(tmp_path: Path) -> None:
    """The ``- item`` form below ``tools:`` keeps working beside a block scalar."""
    agent_file = _write_frontmatter(
        tmp_path,
        'name: agent\ndescription: |\n  A description.\ntools:\n- Read\n- Grep',
    )

    assert runtime_base._parse_agent_frontmatter(agent_file)['tools'] == ['Read', 'Grep']


def test_a_miss_with_no_searchable_root_says_so(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A machine with no root at all reports that, rather than an empty list."""
    monkeypatch.setattr(claude_runtime, '_find_agent_file', lambda _name: None)
    monkeypatch.setattr(claude_runtime, '_agent_search_roots', lambda: [])

    result = _parsed(ClaudeRuntime().subagent_dispatch(VARIANT, None, None))

    assert result['status'] == 'error'
    assert result['error'] == 'prompt_not_found'
    assert '(no searchable root)' in result['message']


def test_an_unreadable_agent_file_names_the_path_it_resolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A resolved-but-unreadable agent reports the path and the read failure."""
    unreadable = tmp_path / 'a-directory-not-a-file'
    unreadable.mkdir()
    monkeypatch.setattr(claude_runtime, '_find_agent_file', lambda _name: unreadable)

    result = _parsed(ClaudeRuntime().subagent_dispatch(BARE, None, None))

    assert result['status'] == 'error'
    assert result['error'] == 'prompt_not_found'
    assert str(unreadable) in result['message']
    assert 'could not be read' in result['message']


# =============================================================================
# 5. The ``{bundle}:{name}`` notation — a diagnosis, never a second lookup
# =============================================================================

#: The phrase every carrier of the new message has to state, so a reader of the
#: contract, the skill and the runtime miss all read the same sentence.
_STEM_PHRASE = 'takes an agent file stem'

PLATFORM_RUNTIME_SKILL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'platform-runtime'


def test_a_bundle_qualified_agent_answers_the_stem_naming_miss(
    empty_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``{bundle}:{name}`` value answers a miss that says why and names the stem.

    ``--agent`` takes a file stem, never the notation a ``Task:`` call uses, and
    the colon is not in the stem character set. The miss therefore reports the form
    error and the stem the caller meant instead of listing search roots as if a
    lookup had run — the reading that sent a real caller after a wrong name.
    """
    monkeypatch.setattr(claude_runtime, '_claude_bundle_cache_root', lambda: empty_cache)

    result = _parsed(ClaudeRuntime().subagent_dispatch(f'plan-marshall:{VARIANT}', None, None))

    assert result['status'] == 'error'
    assert result['error'] == 'prompt_not_found'
    message = result['message']
    assert _STEM_PHRASE in message, message
    assert VARIANT in message, f'the stem the value would have meant is not named: {message}'
    assert f'plan-marshall:{VARIANT}' in message, message
    assert 'part after the colon' in message, message
    # The form error replaces the root listing: there was never a lookup to report.
    assert 'not found; searched' not in message, message


@pytest.mark.parametrize(
    'agent_name',
    [
        pytest.param(f'../outside:{VARIANT}', id='path-in-bundle-half'),
        pytest.param(f'plan-marshall:../{VARIANT}', id='path-in-name-half'),
        pytest.param(f'*:{VARIANT}', id='glob-in-bundle-half'),
        pytest.param(f'plan-marshall:{VARIANT}*', id='glob-in-name-half'),
        pytest.param('plan-marshall:a:b', id='two-colons'),
    ],
)
def test_a_path_or_glob_half_is_not_the_notation(
    agent_name: str, empty_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path or a glob in either half is a plain miss, never the stem diagnosis.

    The guard refuses such a value because it is not a file stem; calling it "the
    notation" would send its reader to a lookup form that does not exist.
    """
    monkeypatch.setattr(claude_runtime, '_claude_bundle_cache_root', lambda: empty_cache)

    assert runtime_base._qualified_agent_stem(agent_name) is None, agent_name
    assert runtime_base._find_agent_file(agent_name) is None, agent_name

    result = _parsed(ClaudeRuntime().subagent_dispatch(agent_name, None, None))

    assert result['status'] == 'error'
    assert result['error'] == 'prompt_not_found'
    assert _STEM_PHRASE not in result['message'], result['message']


def test_the_diagnosis_changes_no_name_that_resolves(deployed_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every name that resolved before still resolves to the same file.

    The bare stem keeps resolving from the deployed versioned cache and from the
    source tree, and the diagnosis answers ``None`` for both — it reads no
    filesystem and adds no lookup form.
    """
    monkeypatch.setattr(claude_runtime, '_claude_bundle_cache_root', lambda: deployed_cache)

    assert claude_runtime._find_agent_file(VARIANT) == _versioned_agent_path(deployed_cache)
    assert runtime_base._qualified_agent_stem(VARIANT) is None

    from_source = runtime_base._find_agent_file(BARE)
    assert from_source is not None, 'the source-tree shape stopped resolving the bare name'
    assert from_source.name == f'{BARE}.md'
    assert runtime_base._qualified_agent_stem(BARE) is None


@pytest.mark.parametrize('document', ['standards/contract.md', 'SKILL.md'])
def test_the_governing_documents_carry_the_message(document: str) -> None:
    """The contract and the skill state the message the runtime answers."""
    text = (PLATFORM_RUNTIME_SKILL / document).read_text(encoding='utf-8')

    assert _STEM_PHRASE in text, f'{document} does not state what --agent takes'
    assert 'part after the colon' in text, f'{document} does not name the stem the value would have meant'
