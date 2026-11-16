#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The agent-file lookup resolves the versioned deployed bundle-cache layout.

The Claude plugin cache deploys ``{root}/{bundle}/{version}/agents/{name}.md``,
one version directory per sync. The seam used to glob only ``{root}/agents/``
and ``{root}/{bundle}/agents/``, so an installed ``execution-context-level-{N}``
variant — which exists ONLY in that deployed layout, never in the source tree —
was unresolvable and every dispatch of it answered ``prompt_not_found``.

The fixture below is that deployed layout. It drives the shared lookup
``runtime_base._find_agent_file`` directly and through the three runtimes that
consume it: Claude through ``claude_runtime._find_agent_file`` on its dispatch
path, OpenCode and Antigravity through the shared ``_unmapped_agent_tools``
tool-mapping check their dispatches run.
"""

from pathlib import Path

import claude_runtime
import pytest
import runtime_base
from antigravity_runtime import AntigravityRuntime
from claude_runtime import ClaudeRuntime
from opencode_runtime import OpenCodeRuntime
from toon_parser import parse_toon

#: The variant-suffixed name the seam could not resolve. Generated per target by
#: the variant emitter, so it exists only in a deployed tree.
VARIANT = 'execution-context-level-3'

#: The bare name, which also exists in the source tree and must keep resolving.
BARE = 'execution-context'

OLD_VERSION = '0.1.2135'
NEW_VERSION = '0.1.2139'

_AGENT_BODY = '---\nname: {name}\ndescription: Dispatches one envelope\n---\n\nRun {name}.\n'


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
    """The deployed ``{bundle}/{version}/agents/`` shape resolves the variant."""
    resolved = runtime_base._find_agent_file(VARIANT, (deployed_cache,))
    assert resolved == deployed_cache / 'plan-marshall' / NEW_VERSION / 'agents' / f'{VARIANT}.md'


def test_shared_lookup_picks_the_newest_eligible_version_dir(deployed_cache: Path) -> None:
    """Two version dirs carrying the agent reduce to the numerically-newest one."""
    (deployed_cache / 'plan-marshall' / '0.1.2100').mkdir(parents=True)
    resolved = runtime_base._find_agent_file(VARIANT, (deployed_cache,))
    assert resolved is not None
    assert resolved.parent.parent.name == NEW_VERSION, 'an older or empty version dir won the selection'


def test_shared_lookup_falls_back_to_the_only_version_that_carries_the_agent(deployed_cache: Path) -> None:
    """Eligibility, not recency alone: the newest dir WITHOUT the agent is skipped."""
    newest = deployed_cache / 'plan-marshall' / '0.1.9999'
    (newest / 'agents').mkdir(parents=True)
    resolved = runtime_base._find_agent_file(VARIANT, (deployed_cache,))
    assert resolved == deployed_cache / 'plan-marshall' / NEW_VERSION / 'agents' / f'{VARIANT}.md'


def test_shared_lookup_keeps_the_flat_layout_first(tmp_path: Path) -> None:
    """A root carrying both shapes answers the flat one, as before the change."""
    root = tmp_path / 'both-shapes'
    flat = _write_agent(root / 'plan-marshall', VARIANT)
    _write_agent(root / 'plan-marshall' / NEW_VERSION, VARIANT)
    assert runtime_base._find_agent_file(VARIANT, (root,)) == flat


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


def test_search_roots_are_the_ones_probed(deployed_cache: Path) -> None:
    """The reported roots are the deployed root first, then the source tree."""
    roots = runtime_base._agent_search_roots((deployed_cache,))
    assert roots[0] == deployed_cache
    assert any(root.name == 'bundles' for root in roots[1:]), 'the source-tree root is not reported'


# =============================================================================
# 2. Claude — the dispatch path that answered prompt_not_found
# =============================================================================


def test_claude_dispatch_resolves_the_variant_from_the_cache(
    deployed_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--agent execution-context-level-3`` succeeds when the cache holds the file."""
    monkeypatch.setattr(claude_runtime, '_claude_bundle_cache_root', lambda: deployed_cache)

    result = _parsed(ClaudeRuntime().subagent_dispatch(VARIANT, None, None))

    assert result['status'] == 'success'
    assert result['invocation']['subagent_type'] == VARIANT


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

_RUNTIMES = (
    ('claude', ClaudeRuntime),
    ('opencode', OpenCodeRuntime),
    ('antigravity', AntigravityRuntime),
)


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

    Each runtime is driven through the surface it actually uses: Claude through
    its deployment-root wrapper, which is its dispatch path; OpenCode and
    Antigravity through the shared ``_unmapped_agent_tools`` tool-mapping check
    their dispatches run, where ``[]`` is the MEASURED "the agent file was read
    and every declared tool maps" and ``None`` the vacuous "unresolvable".
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
