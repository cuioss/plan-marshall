# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared derivation of the merge-shaped ``ci pr`` verb population.

The designated single source for the merge-shaped verb-set derivation, following
the single-source discipline :mod:`_dispatch_roster` applies to the
phase-6-finalize roster sections — a suite that reasons about this population
imports the derivation here rather than maintaining its own copy that can
silently drift out of step.

**The authority is BEHAVIOUR, not a verb name.** A registry key is merge-shaped
when the handler it binds *reaches the platform queue/train surface in its own
executable code* — see :func:`first_queue_symbol`. :data:`MERGE_SHAPED_VERBS` is
a MIRROR of that derivation, not its filter: it exists so a reader has a name for
the population and so drift between the two can be asserted, and it must never be
used to narrow the derived set. Filtering the registry through a hand-listed
vocabulary is what made "population-complete" mean "complete over four pre-named
verbs": a merge-shaped handler registered under any other name was dropped before
any guard saw it, with nothing reported about the condition that dropped it.

**Three states, none of them silent.** :func:`derive_population` classifies EVERY
``('pr', verb)`` registry key into exactly one of ``members`` (reaches the
queue/train surface), ``inert`` (resolved, reaches nothing) and ``unresolved``
(the bound handler's source could not be located at all). The third bucket is the
one that must never be folded into the second: a handler this module cannot read
is a member it cannot classify, and reporting it as "not merge-shaped" would be a
derivation asserting an absence it never established.

**Membership comes from the registry literal**, not from a ``def cmd_`` scan or a
search for handlers that shell out to the CLI. The registry is the closed
population; a call-site scan is a sample, and sampling is what under-counted this
population twice (each provider's ``cmd_pr_auto_merge`` missed in turn).

**Handler bodies are located by parse, not by slicing.** :func:`handler_source`
resolves a bound symbol to its own top-level statement through :mod:`ast`. A
regex that finds ``\\ndef name(`` and slices to the next top-level ``def``
over-reads: it swallows every module-level constant that happens to sit between
two functions, so a handler is credited with vocabulary it never references.
Parsing also resolves the factory-bound handlers (``cmd_pr_close``,
``cmd_pr_ready``, both assigned from ``make_pr_number_handler``), which have no
``def`` line and which a ``def``-anchored search cannot see at all.

These functions are **pure**: each takes provider module source *text* and
returns a derivation over it. Path resolution (which module file, via
``conftest.MARKETPLACE_ROOT``) is the caller's job, exactly as
:mod:`_dispatch_roster` takes the document text rather than resolving it. That
keeps this module importable from ``test/_shared`` with no dependency on
pytest's ``conftest`` resolution order.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from typing import NamedTuple

#: The merge-shaped ``pr`` sub-verbs as currently derived — a MIRROR of the
#: behaviour derivation, never its filter. Consumers assert this against
#: :func:`derive_population` via :func:`mirror_drift`; nothing narrows a derived
#: population through it.
MERGE_SHAPED_VERBS: frozenset[str] = frozenset({'merge', 'auto-merge', 'safe-merge', 'merge-queue'})

#: The two CI provider keys whose registries carry the merge-shaped verbs. Named
#: here so a consumer iterates a derived provider set rather than a literal it
#: re-types.
PROVIDERS: tuple[str, ...] = ('github', 'gitlab')

#: One provider ``handlers: HandlerMap`` registry literal, matched up to its
#: ``\n    }`` close brace.
_HANDLER_MAP_RE = re.compile(r'handlers:\s*HandlerMap\s*=\s*\{(.*?)\n    \}', re.DOTALL)

#: One registry row: a ``('group', 'verb'[, 'sub'])`` key.
_HANDLER_ROW_RE = re.compile(r"\(\s*('[^']+'(?:\s*,\s*'[^']+')*)\s*\)\s*:")

#: A symbol that touches the platform queue / train state. Derived per provider
#: from the module's own vocabulary rather than listed, so a guard renamed or a
#: new probe helper added is picked up without editing this file.
#:
#: Matched ONLY against IDENTIFIER tokens of the handler under test (see
#: :func:`first_queue_symbol`), never against its raw source text. Against raw
#: text the pattern is satisfied by the handler's own DOCSTRING — every
#: merge-shaped handler documents the queue/train surface it guards — so the
#: predicate would report a hit for a handler that merely talks about the queue
#: and never probes it.
#:
#: Deliberately UNANCHORED — no leading ``\b``. Identifiers carry the vocabulary
#: mid-token (``skip_merge_queue_preflight``, ``_refuse_on_required_merge_queue``,
#: ``_probe_merge_train_state``, ``_MERGE_TRAIN_INELIGIBLE_HINT``), and ``_`` is
#: a word character, so a word-boundary anchor matches only the identifiers that
#: BEGIN with the vocabulary. Against prose the anchor is invisible — every prose
#: mention has real boundaries — which is why it survives a raw-text match and
#: silently under-matches the moment the predicate is bound to code.
QUEUE_VOCAB_RE = re.compile(r'(?i)merge[_-]?(?:queue|train)')


class ProviderSources(NamedTuple):
    """One provider's derivation inputs, as text.

    Attributes:
        registry_text: The module text carrying the ``handlers: HandlerMap``
            literal — the closed population.
        handler_texts: The module texts the bound handler symbols are defined in,
            searched in order. GitHub splits its PR handlers into a submodule;
            GitLab defines them alongside its registry.
    """

    registry_text: str
    handler_texts: tuple[str, ...]


class Population(NamedTuple):
    """The total classification of every ``('pr', verb)`` registry key.

    Every key lands in exactly one bucket, so ``members + inert + unresolved``
    is the whole registered ``pr`` surface. Each entry is a
    ``(provider, verb, handler_symbol)`` triple, ordered by provider then by the
    registry's own key order, so the derivation is stable and reviewable.

    Attributes:
        members: Handlers that reach the platform queue/train surface in their
            executable code. This is the merge-shaped population.
        inert: Handlers whose source was located and references no queue/train
            symbol.
        unresolved: Keys whose bound handler symbol could not be located in any
            supplied handler text. NOT an absence of queue behaviour — an absence
            of evidence, which consumers must fail on rather than absorb.
    """

    members: list[tuple[str, str, str]]
    inert: list[tuple[str, str, str]]
    unresolved: list[tuple[str, str, str]]


class Drift(NamedTuple):
    """Divergence between the behaviour derivation and the vocabulary mirror.

    Attributes:
        unnamed: Behaviour-shaped members whose verb is absent from
            :data:`MERGE_SHAPED_VERBS` — the silent-filter defect. Under the old
            vocabulary-filtered derivation these were dropped from the population
            with nothing reported.
        stale: Registered verbs present in :data:`MERGE_SHAPED_VERBS` whose
            handler reaches no queue/train symbol — the stale-mirror defect. The
            vocabulary claims a guard the handler does not perform.
    """

    unnamed: list[tuple[str, str, str]]
    stale: list[tuple[str, str, str]]


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


def _bound_name(node: ast.stmt) -> str | None:
    """The module-level name ``node`` binds, or ``None`` if it binds none.

    Covers both shapes a handler is registered under: a ``def`` and a plain
    assignment from a factory (``cmd_pr_close = make_pr_number_handler(...)``).
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        return target.id if isinstance(target, ast.Name) else None
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def handler_source(symbol: str, handler_texts: tuple[str, ...]) -> str:
    """The source text of the top-level statement binding ``symbol``.

    Searches ``handler_texts`` in order and returns the first match's own source
    segment — exactly the statement, with nothing that follows it. Returns the
    empty string when no supplied text binds the symbol; callers must treat that
    as unresolved rather than as "references nothing".
    """
    for text in handler_texts:
        for node in ast.parse(text).body:
            if _bound_name(node) == symbol:
                return ast.get_source_segment(text, node) or ''
    return ''


def line_starts(source: str) -> list[int]:
    """Absolute character offset at which each 1-based source line begins.

    Lets a ``(row, col)`` token position be converted back to the absolute
    offset an ordering assertion compares on, so every position reported is an
    offset into the ORIGINAL handler text.
    """
    starts = [0, 0]
    position = 0
    for line in source.splitlines(keepends=True):
        position += len(line)
        starts.append(position)
    return starts


def source_tokens(source: str) -> list[tokenize.TokenInfo]:
    """Tokenize one handler fragment.

    Deliberately un-guarded: a fragment that cannot be tokenized is a handler
    the caller cannot reason about, and a loud error is the honest outcome —
    swallowing it would silently downgrade every derivation over it to "no hits
    found", which is indistinguishable from a passing check.
    """
    return list(tokenize.generate_tokens(io.StringIO(source).readline))


def first_queue_symbol(source: str, own_symbol: str) -> tuple[int, str] | None:
    """First ``(offset, identifier)`` in ``source`` naming the queue/train surface.

    The behaviour predicate, and it is deliberately narrow in two ways — each
    closing a way a check over it could pass without the property holding:

    * **Identifiers only.** Docstrings, comments and string literals are excluded
      by construction, because only ``NAME`` tokens are considered. A handler
      that merely *describes* the queue in prose therefore yields ``None``. This
      is the load-bearing narrowing: matching raw text makes the predicate
      satisfiable by the handler docstrings, every one of which documents the
      queue/train surface, and makes an ordering arm over it structurally
      incapable of failing, because a docstring necessarily precedes every
      executable literal.
    * **Not the handler's own name.** ``cmd_pr_merge_queue`` carries the
      vocabulary in its own identifier, so an unfiltered scan would match the
      binding line of exactly the two verbs whose guard matters most — again at
      an offset preceding every literal, so again unfalsifiable.

    Returns ``None`` when the handler references no queue/train symbol.
    """
    starts = line_starts(source)
    for token in source_tokens(source):
        if token.type != tokenize.NAME or token.string == own_symbol:
            continue
        if QUEUE_VOCAB_RE.search(token.string):
            row, col = token.start
            return starts[row] + col, token.string
    return None


def derive_population(provider_sources: dict[str, ProviderSources]) -> Population:
    """Classify every registered ``('pr', verb)`` key of every supplied provider.

    Args:
        provider_sources: Maps each provider key (e.g. ``'github'``) to that
            provider's registry text and handler module texts.

    Returns:
        The total three-bucket classification. See :class:`Population`.
    """
    members: list[tuple[str, str, str]] = []
    inert: list[tuple[str, str, str]] = []
    unresolved: list[tuple[str, str, str]] = []

    for provider in sorted(provider_sources):
        sources = provider_sources[provider]
        names = registry_handler_names(sources.registry_text)
        for key in registry_keys(sources.registry_text):
            if len(key) != 2 or key[0] != 'pr':
                continue
            symbol = names[key]
            entry = (provider, key[1], symbol)
            body = handler_source(symbol, sources.handler_texts)
            if not body:
                unresolved.append(entry)
            elif first_queue_symbol(body, symbol) is not None:
                members.append(entry)
            else:
                inert.append(entry)
    return Population(members=members, inert=inert, unresolved=unresolved)


def mirror_drift(population: Population) -> Drift:
    """Compare the behaviour derivation against the :data:`MERGE_SHAPED_VERBS` mirror.

    Bidirectional by construction: reading only one direction catches a
    vocabulary that lost a verb the handlers still guard, or a vocabulary that
    kept one they no longer do, but never both.
    """
    return Drift(
        unnamed=[entry for entry in population.members if entry[1] not in MERGE_SHAPED_VERBS],
        stale=[entry for entry in population.inert if entry[1] in MERGE_SHAPED_VERBS],
    )
