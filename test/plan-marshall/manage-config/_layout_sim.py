#!/usr/bin/env python3
"""Shared layout-simulation helpers for manage-config step-discovery tests.

Several manage-config test modules build a fake ``plan-marshall`` bundle tree
on disk so the built-in verify / finalize step discovery can resolve each
step's ``order`` frontmatter. Two on-disk shapes are exercised:

* **source layout** — ``<base>/plan-marshall/skills/<phase>/standards/<step>.md``
  (the marketplace-source shape).
* **versioned plugin-cache layout** —
  ``<base>/plan-marshall/<version>/skills/<phase>/standards/<step>.md``
  (the installed-plugin-cache shape).

This module is the single source of truth for those builders; consumers import
``bare``, ``write_phase_standards`` and ``build_phase_layout`` from it via the
sibling-import convention (``from _layout_sim import ...``) used elsewhere under
``test/plan-marshall/``.
"""

from __future__ import annotations

from pathlib import Path


def bare(step_name: str) -> str:
    """Strip the ``default:`` (or any ``prefix:``) marker from a built-in step name."""
    return step_name.split(':', 1)[1] if ':' in step_name else step_name


def write_phase_standards(skill_root: Path, step_names: list[str]) -> None:
    """Create the ``standards/*.md`` docs production discovery reads for ``step_names``.

    Each ``default:verify:{canonical}`` step resolves to the single
    ``canonical_verify.md`` doc (frontmatter ``name: default:verify``,
    ``order: 10``) — every parameterized canonical-verify step shares that one
    backing doc. Any non-canonical ``default:{name}`` step is written to its own
    ``standards/{bare}.md`` with monotonically increasing ``order`` frontmatter
    (``(index + 1) * 10``) so its discovered ordering is deterministic.
    """
    standards_dir = skill_root / 'standards'
    standards_dir.mkdir(parents=True, exist_ok=True)
    wrote_canonical_verify = False
    for offset, step_name in enumerate(step_names):
        bare_name = bare(step_name)
        if bare_name.startswith('verify:'):
            # All parameterized canonical-verify steps share canonical_verify.md.
            if not wrote_canonical_verify:
                (standards_dir / 'canonical_verify.md').write_text(
                    '---\nname: default:verify\ndescription: canonical verify step\norder: 10\n---\n\n# default:verify\n'
                )
                wrote_canonical_verify = True
            continue
        order = (offset + 1) * 10
        (standards_dir / f'{bare_name}.md').write_text(
            f'---\nname: {bare_name}\ndescription: {bare_name} step\norder: {order}\n---\n\n# {bare_name}\n'
        )


def build_phase_layout(
    base: Path,
    phase: str,
    step_names: list[str],
    *,
    cache_layout: bool,
    version: str = '0.1-BETA',
) -> Path:
    """Build a ``<phase>`` standards tree under ``base`` in the requested layout.

    Args:
        base: Root directory the bundle tree is written beneath.
        phase: Phase skill directory name (e.g. ``'phase-5-execute'``).
        step_names: Built-in step names to materialize as standards docs.
        cache_layout: When True, use the versioned plugin-cache shape
            (``<base>/plan-marshall/<version>/skills/<phase>``); otherwise the
            source shape (``<base>/plan-marshall/skills/<phase>``).
        version: Version segment for the cache layout (ignored for source).

    Returns:
        ``base`` (unchanged), for call-site convenience.
    """
    inner = (base / 'plan-marshall' / version) if cache_layout else (base / 'plan-marshall')
    write_phase_standards(inner / 'skills' / phase, step_names)
    return base
