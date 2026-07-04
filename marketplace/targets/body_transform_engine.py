# SPDX-License-Identifier: FSL-1.1-ALv2
"""Target-shared body-transform engine — data-driven line-level body rewrites.

This module is the target-neutral engine that applies the line-level body
transforms documented in each target's ``transforms.md``. It owns the
**matchers** (the "Claude source vocabulary" — how each source idiom is found)
and the **appliers**; every per-target *rewrite template* is supplied as data
from that target's ``mapping.json``. A new target therefore supplies only data
— no transform code — which is the [07 target-extensibility] cost-to-add
contract.

The three transforms, all rule-data-driven:

* **Transform 1: ``Skill:`` directive rewrite** — Claude Code intercepts a
  full-line ``Skill: {bundle}:{skill}`` directive at runtime; a non-verbatim
  target rewrites it into its own skill-load form. The rewrite *template* lives
  in ``mapping.json::directive_rewrites['skill_directive'].template`` with
  ``{bundle}`` / ``{skill}`` placeholders. The engine owns the full-line
  matcher (:data:`SKILL_DIRECTIVE_RE`), anchored so inline backtick references
  like `` `Skill: foo:bar` `` in prose are unaffected.

* **Transform 2: Slash-command rewrite** — Claude Code skills with
  ``user-invocable: true`` are invoked as ``/skill-name``; a dual-emit target
  invokes them under a namespaced id. The rewrite *template* lives in
  ``mapping.json::slash_rewrites['slash_command'].template`` with a ``{name}``
  placeholder resolved from the marketplace scan
  (:func:`build_user_invocable_lookup`).

* **Transform 3: Registered-idiom rewrite** — Claude-native tool idioms
  (``AskUserQuestion``, ``Task:``, ``Skill: <entry>``) are registered as
  per-target rewrite data in ``mapping.json::body_idiom_rewrites``. Each idiom
  carries a *disposition* the engine honours:

    - ``rewrite_inline_code`` — rewrite backtick-wrapped tool references
      (e.g. `` `AskUserQuestion` `` → `` `question` ``) to the target tool
      name. Bare prose mentions of the concept are left alone.
    - ``preserve`` — a deliberate, leaf-aware non-rewrite (e.g. ``Task:`` —
      the dispatcher's leaf-constraint prose must NOT be blanket-rewritten).
    - ``source_fix`` — the divergence is fixed in the source, not at emit time
      (e.g. ``Skill: <entry>`` placeholder prose).

**Fail-closed discipline.** Two guards fail the build rather than emit an
un-dispositioned idiom:

* :func:`assert_dispositions_known` — any ``body_idiom_rewrites`` entry carrying
  an *unknown* disposition raises :class:`UnmappedIdiomError`.
* :func:`assert_source_vocabulary_mapped` — a *non-verbatim* target (one that
  declares any rewrite category) that leaves a structural source idiom
  (``skill_directive`` / ``slash_command``) without a template raises
  :class:`UnmappedIdiomError`. A *verbatim* target (the canonical Claude target,
  which declares no rewrites) skips every transform, so its output stays
  byte-identical to source and independently equality-validatable.

All transforms are idempotent — running them on already-transformed text is a
no-op.

The factory :func:`make_body_transformer` composes the three transforms into a
callable matching the ``BodyTransformer`` signature consumed by each target's
emitter::

    rules = load_transform_rules(config_dir / 'mapping.json')
    lookup = build_user_invocable_lookup(marketplace_dir)
    transformer = make_body_transformer(lookup, rules)
    emit_bundles(marketplace_dir, output_dir, config_dir, body_transformer=transformer)
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The set of dispositions the engine knows how to honour. A registered idiom
# carrying any other disposition is a build-time error (fail-closed).
_KNOWN_DISPOSITIONS = frozenset({'rewrite_inline_code', 'preserve', 'source_fix'})

# The structural "Claude source vocabulary": source idioms a non-verbatim target
# MUST supply a rewrite template for, keyed to the ``mapping.json`` category that
# carries the template. The engine owns each idiom's *matcher*; the target owns
# only the replacement *template* (data). Adding a source idiom here forces every
# non-verbatim target to map it or the build fails closed — the same discipline
# as ``UnmappedToolError`` for frontmatter tools.
STRUCTURAL_VOCABULARY: dict[str, str] = {
    'skill_directive': 'directive_rewrites',
    'slash_command': 'slash_rewrites',
}


class UnmappedIdiomError(ValueError):
    """A registered Claude source idiom is left unmapped (fail-closed build).

    Raised either when a ``body_idiom_rewrites`` entry carries an unknown
    disposition, or when a non-verbatim target omits a template for a structural
    source idiom in :data:`STRUCTURAL_VOCABULARY`.
    """


# Match a full-line ``Skill: bundle:skill`` directive. The leading and trailing
# anchors are ``MULTILINE`` so the regex applies per-line in a multi-line body.
# The bundle/skill names are kebab-case identifiers.
_NAME_RE = r'[A-Za-z0-9][A-Za-z0-9_-]*'
SKILL_DIRECTIVE_RE = re.compile(
    rf'^Skill:\s+(?P<bundle>{_NAME_RE}):(?P<skill>{_NAME_RE})\s*$',
    re.MULTILINE,
)


BodyTransformer = Callable[[str, str, str], str]
"""Signature: ``(body, bundle, kind) -> rewritten body``. ``kind`` is one of
``'skill'``, ``'agent'``, or ``'command'``."""


@dataclass(frozen=True)
class TransformRules:
    """Per-target body-transform rule data, loaded from ``mapping.json``.

    Each field mirrors a ``mapping.json`` top-level category:

    * ``directive_rewrites`` — Transform 1 templates, keyed by structural idiom
      name (``skill_directive``). Each record carries a ``template`` with
      ``{bundle}`` / ``{skill}`` placeholders.
    * ``slash_rewrites`` — Transform 2 templates, keyed by structural idiom name
      (``slash_command``). Each record carries a ``template`` with a ``{name}``
      placeholder.
    * ``body_idiom_rewrites`` — Transform 3 registered-idiom dispositions.

    A target that declares *none* of the three is **verbatim** — the engine
    applies no transform and the emitted body is byte-identical to source.
    """

    directive_rewrites: dict[str, dict[str, Any]] = field(default_factory=dict)
    slash_rewrites: dict[str, dict[str, Any]] = field(default_factory=dict)
    body_idiom_rewrites: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def is_verbatim(self) -> bool:
        """True when the target declares no rewrite category (verbatim output)."""
        return not (
            self.directive_rewrites or self.slash_rewrites or self.body_idiom_rewrites
        )


def load_transform_rules(mapping_path: Path) -> TransformRules:
    """Load and fail-closed-validate the body-transform rules from ``mapping.json``.

    Reads the ``directive_rewrites``, ``slash_rewrites`` and
    ``body_idiom_rewrites`` categories. Returns an all-empty (verbatim)
    :class:`TransformRules` when the file is missing or unreadable — a target
    with no ``mapping.json`` is verbatim by construction.

    Fails closed via :func:`assert_dispositions_known` (Transform 3) and
    :func:`assert_source_vocabulary_mapped` (Transforms 1/2): a malformed or
    incomplete non-verbatim rule set raises :class:`UnmappedIdiomError` at load
    time, before any body is emitted.
    """
    try:
        data = json.loads(mapping_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return TransformRules()
    if not isinstance(data, dict):
        return TransformRules()

    rules = TransformRules(
        directive_rewrites=_as_dict(data.get('directive_rewrites')),
        slash_rewrites=_as_dict(data.get('slash_rewrites')),
        body_idiom_rewrites=_as_dict(data.get('body_idiom_rewrites')),
    )
    assert_dispositions_known(rules.body_idiom_rewrites)
    assert_source_vocabulary_mapped(rules)
    return rules


def _as_dict(value: Any) -> dict[str, dict[str, Any]]:
    return value if isinstance(value, dict) else {}


def assert_dispositions_known(registry: dict[str, dict[str, Any]]) -> None:
    """Fail closed: every registered idiom must carry a known disposition.

    Raises :class:`UnmappedIdiomError` when any ``body_idiom_rewrites`` entry's
    ``disposition`` is missing or not one of :data:`_KNOWN_DISPOSITIONS`. This is
    the structural guard that a NEW Claude idiom cannot be added to the registry
    (or emitted) without an explicit, engine-handled disposition.
    """
    for idiom, record in registry.items():
        disposition = record.get('disposition') if isinstance(record, dict) else None
        if disposition not in _KNOWN_DISPOSITIONS:
            raise UnmappedIdiomError(
                f'Registered idiom {idiom!r} has unknown disposition {disposition!r}; '
                f'known dispositions: {sorted(_KNOWN_DISPOSITIONS)}'
            )


def assert_source_vocabulary_mapped(rules: TransformRules) -> None:
    """Fail closed: a non-verbatim target must map every structural source idiom.

    A verbatim target (declares no rewrite category) is exempt — it emits source
    bytes unchanged. A non-verbatim target must supply a non-empty ``template``
    for each idiom in :data:`STRUCTURAL_VOCABULARY`; a missing template raises
    :class:`UnmappedIdiomError`, so a target cannot partially opt into rewriting
    and silently leave a known Claude source idiom un-rewritten.
    """
    if rules.is_verbatim:
        return
    for idiom, category_key in STRUCTURAL_VOCABULARY.items():
        category = getattr(rules, category_key)
        record = category.get(idiom) if isinstance(category, dict) else None
        template = record.get('template') if isinstance(record, dict) else None
        if not template:
            raise UnmappedIdiomError(
                f'Non-verbatim target leaves source idiom {idiom!r} unmapped; '
                f'expected a non-empty {category_key}[{idiom!r}].template'
            )


def rewrite_skill_directives(body: str, template: str) -> str:
    """Apply Transform 1: full-line ``Skill:`` directive rewrite.

    ``template`` is the target's rewrite string with ``{bundle}`` / ``{skill}``
    placeholders (from ``mapping.json::directive_rewrites``). Placeholders are
    substituted literally — the template itself is emitted verbatim aside from
    those two tokens — so a template containing ``{ name: ... }`` braces is safe.

    Idempotent: the rewritten line no longer matches :data:`SKILL_DIRECTIVE_RE`,
    so re-running is a no-op.
    """

    def replace(match: re.Match[str]) -> str:
        bundle = match.group('bundle')
        skill = match.group('skill')
        return template.replace('{bundle}', bundle).replace('{skill}', skill)

    return SKILL_DIRECTIVE_RE.sub(replace, body)


def build_slash_command_re(known_names: list[str]) -> re.Pattern[str] | None:
    """Build the slash-command regex for the supplied skill names.

    Returns ``None`` when ``known_names`` is empty (the resulting regex would
    match nothing useful and would still raise on compile).
    """
    if not known_names:
        return None
    # Sort by length descending so longer names match before shorter prefixes
    # (avoids partial matches when one skill name is a prefix of another).
    alternatives = sorted({n for n in known_names if n}, key=lambda n: (-len(n), n))
    pattern = (
        r'(?<![\w-])/(?P<name>'
        + '|'.join(re.escape(n) for n in alternatives)
        + r')(?=\s|$|=)'
    )
    return re.compile(pattern, re.MULTILINE)


def rewrite_slash_commands(body: str, lookup: dict[str, str], template: str) -> str:
    """Apply Transform 2: rewrite ``/skill-name`` to the namespaced form.

    ``lookup`` maps bare skill names to their namespaced form
    (``{bundle}-{skill}``); ``template`` is the target's rewrite string with a
    ``{name}`` placeholder (from ``mapping.json::slash_rewrites``). Names already
    in namespaced form pass through unchanged because the regex only matches the
    bare names listed in ``lookup``.

    Idempotent: rewritten names are namespaced and not in the ``lookup`` keys,
    so a second pass does not re-match.
    """
    pattern = build_slash_command_re(list(lookup))
    if pattern is None:
        return body

    def replace(match: re.Match[str]) -> str:
        name = match.group('name')
        target = lookup.get(name)
        if target is None or target == name:
            return match.group(0)
        return template.replace('{name}', target)

    return pattern.sub(replace, body)


def rewrite_registered_idioms(body: str, registry: dict[str, dict[str, Any]]) -> str:
    """Apply Transform 3: data-driven registered-idiom rewrites.

    Iterates the registry (fail-closed-validated by
    :func:`assert_dispositions_known`) and applies each idiom's disposition:

    - ``rewrite_inline_code`` — rewrite backtick-wrapped `` `{idiom}` `` to the
      target tool name (`` `{opencode_tool}` ``). Bare prose mentions are left.
    - ``preserve`` / ``source_fix`` — no body change (deliberate non-rewrite /
      source-side fix).

    Idempotent: a ``rewrite_inline_code`` whose replacement is already present
    does not re-match (the source idiom name no longer appears in that backtick
    span).
    """
    for idiom, record in registry.items():
        disposition = record.get('disposition')
        if disposition != 'rewrite_inline_code':
            continue
        target_tool = record.get('opencode_tool')
        if not target_tool:
            continue
        # Rewrite only the backtick-wrapped tool reference, never bare prose.
        body = body.replace(f'`{idiom}`', f'`{target_tool}`')
    return body


def make_body_transformer(
    lookup: dict[str, str],
    rules: TransformRules,
) -> BodyTransformer:
    """Compose Transforms 1 + 2 + 3 into a ``BodyTransformer``.

    The returned callable matches the emitter's ``BodyTransformer`` signature:
    ``(body, bundle, kind) -> rewritten body``. The bundle and kind arguments are
    reserved for future per-context behavior; the current transforms apply
    uniformly to skill, agent, and command bodies.

    Each transform runs only when ``rules`` declares its category, so a verbatim
    target (empty ``rules``) returns bodies unchanged. ``rules`` is expected to
    have passed the fail-closed validation in :func:`load_transform_rules`.
    """
    directive_template = _structural_template(rules.directive_rewrites, 'skill_directive')
    slash_template = _structural_template(rules.slash_rewrites, 'slash_command')

    def transform(body: str, _bundle: str, _kind: str) -> str:
        if directive_template:
            body = rewrite_skill_directives(body, directive_template)
        if slash_template:
            body = rewrite_slash_commands(body, lookup, slash_template)
        if rules.body_idiom_rewrites:
            body = rewrite_registered_idioms(body, rules.body_idiom_rewrites)
        return body

    return transform


def _structural_template(category: dict[str, dict[str, Any]], idiom: str) -> str:
    record = category.get(idiom) if isinstance(category, dict) else None
    template = record.get('template') if isinstance(record, dict) else None
    return template if isinstance(template, str) else ''


def _frontmatter_field(content: str, field_name: str) -> str:
    """Read a single scalar frontmatter field without a full YAML parse.

    Returns the trimmed value of the first ``{field_name}:`` line inside the
    leading ``---`` frontmatter block, or ``''`` when absent. Deliberately
    minimal so the engine stays target-neutral (no dependency on any target's
    frontmatter parser) — the user-invocable scan only needs one scalar field.
    """
    if not content.startswith('---'):
        return ''
    end = content.find('\n---', 3)
    if end == -1:
        return ''
    block = content[3:end]
    prefix = f'{field_name}:'
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix):].strip()
    return ''


def _is_user_invocable(value: str) -> bool:
    return value.strip().lower() in {'true', 'yes', '1'}


def build_user_invocable_lookup(marketplace_dir: Path) -> dict[str, str]:
    """Scan ``marketplace_dir`` for ``user-invocable: true`` skills.

    Returns a dict mapping the bare skill name to the namespaced
    ``{bundle}-{skill}`` id — the resolved ``{name}`` values a Transform 2
    template substitutes. The scan is non-destructive — it only reads SKILL.md
    frontmatter for skills under ``{bundle}/skills/{skill}/``.
    """
    lookup: dict[str, str] = {}
    if not marketplace_dir.is_dir():
        return lookup

    for bundle_dir in sorted(marketplace_dir.iterdir()):
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / 'SKILL.md'
            if not skill_md.is_file():
                continue
            try:
                content = skill_md.read_text(encoding='utf-8')
            except OSError:
                continue
            if _is_user_invocable(_frontmatter_field(content, 'user-invocable')):
                lookup[skill_dir.name] = f'{bundle_dir.name}-{skill_dir.name}'
    return lookup


__all__ = [
    'BodyTransformer',
    'STRUCTURAL_VOCABULARY',
    'SKILL_DIRECTIVE_RE',
    'TransformRules',
    'UnmappedIdiomError',
    'assert_dispositions_known',
    'assert_source_vocabulary_mapped',
    'build_slash_command_re',
    'build_user_invocable_lookup',
    'load_transform_rules',
    'make_body_transformer',
    'rewrite_registered_idioms',
    'rewrite_skill_directives',
    'rewrite_slash_commands',
]
