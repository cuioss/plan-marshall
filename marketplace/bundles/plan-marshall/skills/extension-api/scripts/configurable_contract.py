#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Configurable step-param contract parser.

Single source of truth for the step-owned ``configurable`` frontmatter
declaration. Each param-owning finalize step declares its params in the
``---``-fenced YAML frontmatter of its own body doc (SKILL.md for ``project:``
steps; the canonical workflow/standards doc for built-in ``default:`` steps):

```yaml
---
name: sonar-roundtrip
order: 80
configurable:
  - key: touched_file_cleanup
    default: new_code_only
    description: Which surface the Sonar roundtrip success criterion covers.
  - key: do_transition
    default: false
    description: Gate the server-side SonarCloud dismissal path.
---
```

The parser is a thin, fail-loud reader consumed by ``manage-config`` and
``manage-execution-manifest`` as the canonical default/description source for
step-owned params. Each declaration entry MUST carry exactly the three mandatory
sub-fields ``key`` (str), ``default`` (any JSON scalar), and ``description``
(non-empty str). Every malformed-declaration case raises ``ValueError`` with a
precise message; there is no silent fallback.

Addressing scheme: a param is addressed as ``{step_id}.{param_key}`` (e.g.
``default:sonar-roundtrip.touched_file_cleanup``).

Stdlib-only. Does NOT import any target script (no import of
``manage-config`` / ``manage-execution-manifest``); path resolution mirrors
``manage-execution-manifest._resolve_standards_path`` but is re-derived here so
the parser stays a leaf dependency.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

# Direct import - executor sets up PYTHONPATH for cross-skill imports.
from marketplace_bundles import resolve_bundles_root, resolve_skills_root  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# The three mandatory sub-fields every ``configurable`` entry MUST declare.
_REQUIRED_SUBFIELDS: tuple[str, ...] = ('key', 'default', 'description')


# =============================================================================
# Step-doc path resolution (mirrors manage-execution-manifest._resolve_standards_path)
# =============================================================================

def _phase_6_skill_dir() -> Path:
    """Return the ``phase-6-finalize`` skill directory in the owning bundle."""
    return resolve_skills_root(Path(__file__)) / 'phase-6-finalize'


def _repo_root() -> Path:
    """Return the repository root anchor (grandparent of ``marketplace/bundles``)."""
    return resolve_bundles_root(Path(__file__)).parent.parent


def _strip_default_prefix(step_id: str) -> str:
    """Strip a leading ``default:`` prefix from a built-in step id."""
    prefix = 'default:'
    return step_id[len(prefix):] if step_id.startswith(prefix) else step_id


def _guard_within(candidate: Path, parent_dir: Path, step_id: str) -> Path:
    """Return ``candidate`` only if it stays within ``parent_dir``.

    ``step_id`` is externally controlled, so a value such as
    ``project:../../etc/passwd`` would escape the intended parent directory via
    simple string concatenation. After resolving both paths, this guard verifies
    the candidate is contained by ``parent_dir`` and fails loud otherwise — there
    is no silent fallback.

    Args:
        candidate: The constructed body-doc path (not yet existence-checked).
        parent_dir: The intended containing directory the candidate must not
            escape.
        step_id: The originating step identifier, surfaced in the error message.

    Returns:
        The resolved candidate path when it is contained by ``parent_dir``.

    Raises:
        ValueError: When the resolved candidate escapes ``parent_dir`` (path
            traversal detected).
    """
    resolved_candidate = candidate.resolve()
    resolved_parent = parent_dir.resolve()
    if not resolved_candidate.is_relative_to(resolved_parent):
        raise ValueError(
            f"configurable contract: step id {step_id!r} resolves to "
            f"{resolved_candidate} which escapes the intended parent directory "
            f"{resolved_parent} (path traversal rejected)"
        )
    return resolved_candidate


def resolve_step_doc_path(step_id: str) -> Path:
    """Resolve the body-doc path that declares ``step_id``'s configurable block.

    Resolution rules (mirroring manage-execution-manifest):

    - ``project:``-prefixed steps resolve to
      ``.claude/skills/{bare-name}/SKILL.md`` relative to the repo root.
    - Built-in steps (bare or ``default:``-prefixed) resolve to the
      ``phase-6-finalize`` body doc, searching ``workflow/`` first then
      ``standards/``. When neither exists the ``workflow/`` path is returned so
      the caller's missing-file error names the preferred location.

    Args:
        step_id: The step identifier (``default:branch-cleanup``,
            ``project:finalize-step-pre-submission-self-review``, …).

    Returns:
        The resolved body-doc path (may not exist on disk).

    Raises:
        ValueError: When the externally-controlled ``step_id`` resolves to a
            path that escapes its intended parent directory (path traversal).
    """
    if step_id.startswith('project:'):
        bare = step_id[len('project:'):]
        skills_root = _repo_root() / '.claude' / 'skills'
        candidate = skills_root / bare / 'SKILL.md'
        return _guard_within(candidate, skills_root, step_id)

    skill_dir = _phase_6_skill_dir()
    bare = _strip_default_prefix(step_id)
    workflow_path = _guard_within(skill_dir / 'workflow' / f'{bare}.md', skill_dir, step_id)
    if workflow_path.is_file():
        return workflow_path
    standards_path = _guard_within(skill_dir / 'standards' / f'{bare}.md', skill_dir, step_id)
    if standards_path.is_file():
        return standards_path
    return workflow_path


# =============================================================================
# Frontmatter extraction
# =============================================================================

def _extract_frontmatter_lines(text: str) -> list[str] | None:
    """Return the lines inside the leading ``---``-fenced frontmatter block.

    Returns ``None`` when the file does not open with a ``---`` fence or the
    closing fence is never reached.
    """
    if not text.startswith('---'):
        return None
    lines = text.splitlines()
    # lines[0] is the opening '---'. Collect until the next standalone '---'.
    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == '---':
            return body
        body.append(line)
    return None


def _coerce_scalar(raw: str) -> Any:
    """Coerce a YAML scalar string to a Python JSON-scalar value.

    Handles quoted strings, booleans (``true``/``false``), ``null``/``~``,
    integers, and floats. Anything else is returned as the stripped string.
    An empty/absent value coerces to the empty string (the description
    non-empty check then rejects it where required).
    """
    value = raw.strip()
    if not value:
        return ''
    if (value[0] == value[-1]) and value[0] in ('"', "'") and len(value) >= 2:
        return value[1:-1]
    lowered = value.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    if lowered in ('null', '~'):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _parse_configurable_entries(fm_lines: list[str]) -> list[dict[str, Any]] | None:
    """Parse the ``configurable:`` list block from frontmatter lines.

    Recognises the YAML block-sequence shape:

    ```yaml
    configurable:
      - key: foo
        default: bar
        description: ...
    ```

    Returns the list of per-entry sub-field maps, or ``None`` when no
    ``configurable:`` key is present. An empty list is returned when the key is
    present but declares no entries.
    """
    entries: list[dict[str, Any]] | None = None
    current: dict[str, Any] | None = None
    in_block = False
    block_indent = 0

    for line in fm_lines:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if not in_block:
            if stripped == 'configurable:' or stripped.startswith('configurable:'):
                in_block = True
                block_indent = indent
                entries = []
            continue

        # Inside the configurable block. A top-level key at or below the block
        # indent terminates the block.
        if indent <= block_indent and not stripped.startswith('-'):
            break

        if stripped.startswith('- '):
            # New entry. The text after '- ' is the first sub-field.
            current = {}
            entries.append(current)  # type: ignore[union-attr]
            item = stripped[2:].strip()
            if item and ':' in item:
                key, _, val = item.partition(':')
                current[key.strip()] = _coerce_scalar(val)
        elif stripped == '-':
            current = {}
            entries.append(current)  # type: ignore[union-attr]
        else:
            # Continuation sub-field of the current entry.
            if current is None or ':' not in stripped:
                continue
            key, _, val = stripped.partition(':')
            current[key.strip()] = _coerce_scalar(val)

    return entries


# =============================================================================
# Public API
# =============================================================================

def parse_configurable(step_doc_path: str | Path) -> dict[str, dict[str, Any]]:
    """Parse a step body doc's ``configurable`` declaration.

    Args:
        step_doc_path: Path to the step's body doc (the ``---``-fenced
            frontmatter source).

    Returns:
        A mapping ``{param_key: {"default": <scalar>, "description": <str>}}``
        for every declared param entry.

    Raises:
        ValueError: On any malformed-declaration case —
            - the file does not exist;
            - the file has no ``---``-fenced frontmatter block;
            - no ``configurable:`` block is present;
            - the ``configurable:`` block declares no entries;
            - an entry is missing any of ``key`` / ``default`` / ``description``;
            - an entry declares any sub-field outside ``key`` / ``default`` /
              ``description``;
            - ``key`` or ``description`` is not a string;
            - ``description`` is empty;
            - a ``key`` is declared more than once.
    """
    path = Path(step_doc_path)
    if not path.is_file():
        raise ValueError(
            f"configurable contract: step body doc not found: {path}"
        )
    text = path.read_text(encoding='utf-8')
    fm_lines = _extract_frontmatter_lines(text)
    if fm_lines is None:
        raise ValueError(
            f"configurable contract: {path} has no '---'-fenced frontmatter block"
        )
    entries = _parse_configurable_entries(fm_lines)
    if entries is None:
        raise ValueError(
            f"configurable contract: {path} declares no 'configurable:' "
            f"frontmatter block (a param-owning step MUST declare one)"
        )
    if not entries:
        raise ValueError(
            f"configurable contract: {path} 'configurable:' block is empty "
            f"(declare at least one param entry)"
        )

    result: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        for subfield in _REQUIRED_SUBFIELDS:
            if subfield not in entry:
                raise ValueError(
                    f"configurable contract: {path} entry #{index + 1} is "
                    f"missing required sub-field '{subfield}' "
                    f"(every entry needs key, default, description)"
                )
        extra_keys = set(entry) - set(_REQUIRED_SUBFIELDS)
        if extra_keys:
            raise ValueError(
                f"configurable contract: {path} entry #{index + 1} declares "
                f"unexpected sub-field(s) {sorted(extra_keys)} "
                f"(every entry MUST carry exactly key, default, description)"
            )
        key = entry['key']
        description = entry['description']
        if not isinstance(key, str):
            raise ValueError(
                f"configurable contract: {path} entry #{index + 1} 'key' must "
                f"be a string, got {type(key).__name__}: {key!r}"
            )
        if not isinstance(description, str):
            raise ValueError(
                f"configurable contract: {path} entry '{key}' 'description' "
                f"must be a string, got {type(description).__name__}: "
                f"{description!r}"
            )
        if not description.strip():
            raise ValueError(
                f"configurable contract: {path} entry '{key}' has an empty "
                f"'description' (descriptions MUST be non-empty)"
            )
        if key in result:
            raise ValueError(
                f"configurable contract: {path} declares duplicate key '{key}'"
            )
        result[key] = {
            'default': entry['default'],
            'description': description,
        }
    return result


def resolve_step_defaults(step_id: str) -> dict[str, Any]:
    """Resolve a step's param defaults from its declared ``configurable`` block.

    Resolves ``step_id`` to its body-doc path (see :func:`resolve_step_doc_path`)
    then parses the declaration and projects each entry to its default.

    Args:
        step_id: The step identifier (``default:sonar-roundtrip``,
            ``project:finalize-step-pre-submission-self-review``, …).

    Returns:
        A mapping ``{param_key: <default value>}`` for every declared param.

    Raises:
        ValueError: On any malformed-declaration case (see
            :func:`parse_configurable`).
    """
    path = resolve_step_doc_path(step_id)
    schema = parse_configurable(path)
    return {key: spec['default'] for key, spec in schema.items()}


def resolve_step_defaults_optional(step_id: str) -> dict[str, Any] | None:
    """Resolve a step's param defaults, or ``None`` when it owns no params.

    Distinguishes the *ownerless* case (the step's body doc has no
    ``configurable:`` block — a legitimate, expected state for a built-in
    finalize step that owns no params) from the *malformed* case (the block
    is present but ill-formed). The former returns ``None``; the latter
    propagates the :class:`ValueError` raised by :func:`parse_configurable`.

    This is the seed-side companion to :func:`resolve_step_defaults`: the
    ``manage-config`` finalize-step defaults seed maps every built-in step id
    through this resolver, folding param-owning steps to their default map and
    ownerless steps to ``None`` (serialized as ``null`` on disk).

    Args:
        step_id: The step identifier (``default:sonar-roundtrip``,
            ``default:commit-push``, …).

    Returns:
        A mapping ``{param_key: <default value>}`` when the step declares a
        ``configurable:`` block, or ``None`` when it declares none.

    Raises:
        ValueError: On a malformed (present-but-ill-formed) ``configurable:``
            block, or when the step body doc does not exist (see
            :func:`parse_configurable`).
    """
    path = resolve_step_doc_path(step_id)
    if not path.is_file():
        raise ValueError(
            f"configurable contract: step body doc not found: {path}"
        )
    text = path.read_text(encoding='utf-8')
    fm_lines = _extract_frontmatter_lines(text)
    if fm_lines is None:
        # No frontmatter at all → the step owns no configurable params.
        return None
    if _parse_configurable_entries(fm_lines) is None:
        # Frontmatter present but no ``configurable:`` key → ownerless.
        return None
    # A ``configurable:`` block IS present — parse it fully (fail loud on
    # malformed) and project to defaults.
    schema = parse_configurable(path)
    return {key: spec['default'] for key, spec in schema.items()}


# =============================================================================
# CLI (diagnostic surface)
# =============================================================================

def _cmd_parse(args: argparse.Namespace) -> int:
    """Parse a step doc's configurable block and emit the schema as TOON."""
    schema = parse_configurable(args.path)
    rows = [
        {'key': key, 'default': spec['default'], 'description': spec['description']}
        for key, spec in schema.items()
    ]
    print(serialize_toon({'status': 'success', 'path': str(args.path), 'params': rows}))
    return 0


def _cmd_resolve(args: argparse.Namespace) -> int:
    """Resolve a step id's param defaults and emit them as TOON."""
    defaults = resolve_step_defaults(args.step_id)
    print(serialize_toon({'status': 'success', 'step_id': args.step_id, 'defaults': defaults}))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point — fail-loud diagnostic access to the contract parser."""
    parser = argparse.ArgumentParser(
        description='Configurable step-param contract parser.',
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_parse = sub.add_parser('parse', help='Parse a step doc configurable block', allow_abbrev=False)
    p_parse.add_argument('--path', required=True, help='Path to the step body doc')
    p_parse.set_defaults(func=_cmd_parse)

    p_resolve = sub.add_parser('resolve', help='Resolve a step id param defaults', allow_abbrev=False)
    p_resolve.add_argument('--step-id', required=True, help='Step identifier')
    p_resolve.set_defaults(func=_cmd_resolve)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(serialize_toon({'status': 'error', 'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
