# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared derivation of the merge-shaped ``ci pr`` verb population.

The single implementation of the merge-shaped verb-set derivation, so every
suite that reasons about that population reads an **identical** set rather than
each maintaining its own copy that can silently drift out of step — the same
single-source discipline :mod:`_dispatch_roster` applies to the phase-6-finalize
roster sections.

The population is the closed set the plan
``060-a-prose-routing-table-is-not-an-enforcement-boundary`` derived: the
``('pr', verb)`` keys of each CI provider's ``handlers: HandlerMap`` registry
literal whose verb is one of the merge-shaped vocabulary. Deriving from the
registry literal — NOT from a ``def cmd_`` scan or a search for handlers that
shell out to the CLI — is what stops the sample-read-as-enumeration failure that
under-counted this population twice (each provider's ``cmd_pr_auto_merge`` missed
in turn). The registry is the closed population; a call-site scan is a sample.

These functions are **pure**: each takes the provider module source *text* and
returns a derivation over it. Path resolution (which module file, via
``conftest.MARKETPLACE_ROOT``) is the caller's job, exactly as
:mod:`_dispatch_roster` takes the document text rather than resolving it. That
keeps this module importable from ``test/_shared`` with no dependency on
pytest's ``conftest`` resolution order.
"""

from __future__ import annotations

import re

#: The candidate merge-shaped ``pr`` sub-verbs. This is the VOCABULARY the
#: derivation filters against — not a membership claim. WHICH of these each
#: provider actually registers is derived from that provider's registry literal.
MERGE_SHAPED_VERBS: frozenset[str] = frozenset({'merge', 'auto-merge', 'safe-merge', 'merge-queue'})

#: The two CI provider keys whose registries carry the merge-shaped verbs. Named
#: here so a consumer iterates a derived provider set rather than a literal it
#: re-types.
PROVIDERS: tuple[str, ...] = ('github', 'gitlab')

#: One provider ``handlers: HandlerMap`` registry literal, matched up to its
#: ``\n    }`` close brace. Identical to the regex the first-instance source-guard
#: (``test_branch_cleanup_merge_queue_routing.py``) uses, so the two suites derive
#: the SAME registry population from the SAME literal.
_HANDLER_MAP_RE = re.compile(r'handlers:\s*HandlerMap\s*=\s*\{(.*?)\n    \}', re.DOTALL)

#: One registry row: a ``('group', 'verb'[, 'sub'])`` key.
_HANDLER_ROW_RE = re.compile(r"\(\s*('[^']+'(?:\s*,\s*'[^']+')*)\s*\)\s*:")


def _handler_map_body(module_text: str) -> str:
    """Return the inside of a provider's ``handlers: HandlerMap = { ... }`` literal.

    Raises ``AssertionError`` when no such literal is found: the registry IS the
    population, so a miss must fail loudly rather than silently yield an empty
    derivation that every downstream assertion then passes vacuously over.
    """
    match = _HANDLER_MAP_RE.search(module_text)
    assert match is not None, (
        'No `handlers: HandlerMap = {...}` literal was found in the provider module '
        'text. The registry IS the merge-shaped population; without it every '
        'derivation over it is vacuous.'
    )
    return match.group(1)


def registry_keys(module_text: str) -> list[tuple[str, ...]]:
    """Every ``(group, verb[, sub])`` key in a provider's ``HandlerMap`` literal."""
    keys: list[tuple[str, ...]] = []
    for raw in _HANDLER_ROW_RE.findall(_handler_map_body(module_text)):
        keys.append(tuple(part.strip().strip("'") for part in raw.split(',')))
    return keys


def registry_handler_names(module_text: str) -> dict[tuple[str, ...], str]:
    """Map each registry key to the handler symbol it is bound to."""
    bindings: dict[tuple[str, ...], str] = {}
    for line in _handler_map_body(module_text).splitlines():
        row = _HANDLER_ROW_RE.search(line)
        if row is None:
            continue
        key = tuple(part.strip().strip("'") for part in row.group(1).split(','))
        _, _, handler = line.partition('):')
        bindings[key] = handler.strip().rstrip(',').strip()
    return bindings


def merge_shaped_keys(module_text: str) -> list[tuple[str, ...]]:
    """The merge-shaped subset of a provider's registry — derived, not listed.

    A key is merge-shaped iff it is a two-element ``('pr', verb)`` whose ``verb``
    is in :data:`MERGE_SHAPED_VERBS`.
    """
    return [
        key
        for key in registry_keys(module_text)
        if len(key) == 2 and key[0] == 'pr' and key[1] in MERGE_SHAPED_VERBS
    ]


def merge_shaped_members(provider_texts: dict[str, str]) -> list[tuple[str, str, str]]:
    """Derive ``(provider, verb, handler_name)`` for every merge-shaped member.

    Args:
        provider_texts: Maps each provider key (e.g. ``'github'``) to that
            provider's ``*_ops.py`` module source text.

    Returns:
        One ``(provider, verb, handler_name)`` per merge-shaped registry member,
        ordered by provider then by the registry's own key order, so the derived
        population is stable and reviewable.
    """
    members: list[tuple[str, str, str]] = []
    for provider in sorted(provider_texts):
        text = provider_texts[provider]
        names = registry_handler_names(text)
        for key in merge_shaped_keys(text):
            members.append((provider, key[1], names[key]))
    return members
