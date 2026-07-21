#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Settle-band scanner for the ``mutates-source-step-post-merge-order`` rule.

A finalize step that edits tracked source declares ``mutates_source: true`` in
its frontmatter. Such a step MUST run before the merge gate
(``default:branch-cleanup``): finalize runs on the plan's feature branch, so a
source edit is pushable — and CI-covered, and reviewed with the rest of the
change — only while that branch is still open. Once the branch is merged the
feature branch is gone, so a later edit cannot ride the PR, cannot be squashed
into the landed commit, and can only reach the base branch through a separate
follow-up PR. The enforcement-critical ordering contract lives in the central
standard: see ``marketplace/bundles/plan-marshall/skills/phase-6-finalize/
standards/source-edit-pushability.md`` and its § "Mutation-settling stage"
counterpart in ``phase-6-finalize/SKILL.md``; this analyzer is the structural
backstop that makes a re-divergence fail the build instead of surfacing as a
stuck PR.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_role_field.py`` and
``_analyze_finalize_step_token.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- frontmatter parsing driven by the file text alone
- stdlib-only dependencies
- no mutation of any file

Scan roots
----------
Every finalize-step doc across the three addressing surfaces owned by
``ext-point-finalize-step``:

1. **Built-in step docs** — ``phase-6-finalize/workflow/*.md`` and
   ``phase-6-finalize/standards/*.md``.
2. **Bundle steps** — every bundle's ``skills/*/SKILL.md``.
3. **Project-local steps** — ``<repo>/.claude/skills/finalize-step-*/SKILL.md``.

Membership is DECLARED, not inferred: a doc is a finalize step iff its
frontmatter carries ``implements: ...ext-point-finalize-step`` (scalar or
block-sequence form). Docs without that declaration are never inspected.

Detection
---------
The merge-gate order is resolved DYNAMICALLY from the discovered
``default:branch-cleanup`` record — never a hardcoded literal — so moving the
merge gate moves the rule's threshold with it. A finding is emitted for each
discovered step whose ``mutates_source`` is truthy AND whose ``order`` is
greater than or equal to the merge-gate order, anchored at the step's
``order:`` line.

A step doc that declares no ``mutates_source`` key is silently skipped (it
makes no source-mutation claim, so it is out of scope and produces no false
positive). When the merge-gate step is not discoverable — a synthetic
``tmp_path`` marketplace with no phase-6-finalize tree — the scan returns no
findings rather than guessing a threshold.

Findings have the shape::

    {
        'rule_id': 'mutates-source-step-post-merge-order',
        'type': 'mutates_source_step_post_merge_order',
        'rule': 'analyze_mutates_source_order',
        'file': '<absolute step-doc path>',
        'line': <int, 1-based line of the order: key>,
        'severity': 'error',
        'fixable': False,
        'details': {
            'step_name': '<declared step id>',
            'step_order': <int>,
            'merge_gate_order': <int>,
        },
    }

Public API
----------
- ``analyze_mutates_source_order(marketplace_root)``: entry point.
"""

from __future__ import annotations

from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'mutates-source-step-post-merge-order'
RULE_NAME = 'analyze_mutates_source_order'
FINDING_TYPE = 'mutates_source_step_post_merge_order'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='corpus-relational',
)

# Canonical ``implements:`` value identifying a finalize-step doc. Membership is
# declared on each step doc via this ext-point; the contract lives in the central
# standard marketplace/bundles/plan-marshall/skills/extension-api/standards/
# ext-point-finalize-step.md. This constant is the discovery key only.
_FINALIZE_STEP_EXT_POINT = (
    'plan-marshall:extension-api/standards/ext-point-finalize-step'
)

# The merge gate whose order is the settle-band boundary. Its ORDER is resolved
# dynamically from the discovered record; only the step's identity is a literal.
_MERGE_GATE_STEP_NAME = 'default:branch-cleanup'

_TRUTHY = frozenset({'true', 'yes', 'on', '1'})


class _StepDoc:
    """One discovered finalize-step doc and the fields the rule reads."""

    __slots__ = ('path', 'name', 'order', 'mutates_source', 'order_line')

    def __init__(
        self,
        path: Path,
        name: str,
        order: int | None,
        mutates_source: str | None,
        order_line: int,
    ) -> None:
        self.path = path
        self.name = name
        self.order = order
        self.mutates_source = mutates_source
        self.order_line = order_line


def _frontmatter_lines(text: str) -> list[tuple[int, str]] | None:
    """Return ``(1-based line number, line)`` pairs inside the frontmatter block.

    Returns ``None`` when the file does not open with a ``---`` fence or the
    block is never closed — in both cases the doc carries no frontmatter
    contract and is out of scope.
    """
    if not text.startswith('---'):
        return None
    lines = text.splitlines()
    collected: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if index == 0:
            if line.strip() != '---':
                return None
            continue
        if line.strip() == '---':
            return collected
        collected.append((index + 1, line))
    return None


def _parse_step_doc(path: Path) -> _StepDoc | None:
    """Parse one candidate doc into a ``_StepDoc``, or ``None`` when out of scope.

    Out of scope means: unreadable, no frontmatter block, or a frontmatter block
    that does not declare the finalize-step ext-point. The ext-point check is a
    membership test over the raw block text so both the scalar
    (``implements: <value>``) and the block-sequence (``implements:`` then
    ``  - <value>``) declaration forms are recognised. Comment lines are excluded
    from that membership test — matching the key-parsing loop below — so a doc
    that comments out its ``implements:`` declaration stays out of scope.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None

    block = _frontmatter_lines(text)
    if block is None:
        return None
    uncommented = '\n'.join(
        line for _, line in block if not line.strip().startswith('#')
    )
    if _FINALIZE_STEP_EXT_POINT not in uncommented:
        return None

    name = ''
    order: int | None = None
    order_line = 1
    mutates_source: str | None = None

    for line_number, raw_line in block:
        # Top-level keys only — an indented line belongs to a nested mapping
        # (e.g. the ``lane:`` block) and never carries these three fields.
        if not raw_line or raw_line[0].isspace():
            continue
        stripped = raw_line.strip()
        if stripped.startswith('#') or ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key == 'name':
            name = value
        elif key == 'order':
            order_line = line_number
            try:
                order = int(value)
            except ValueError:
                order = None
        elif key == 'mutates_source':
            mutates_source = value

    return _StepDoc(path, name, order, mutates_source, order_line)


def _candidate_paths(marketplace_root: Path) -> list[Path]:
    """Enumerate every candidate doc across the three addressing surfaces."""
    candidates: list[Path] = []

    phase_6 = marketplace_root / 'plan-marshall' / 'skills' / 'phase-6-finalize'
    for sub in ('workflow', 'standards'):
        sub_dir = phase_6 / sub
        if sub_dir.is_dir():
            candidates.extend(sorted(sub_dir.glob('*.md')))

    if marketplace_root.is_dir():
        for bundle_dir in sorted(marketplace_root.iterdir()):
            skills_dir = bundle_dir / 'skills'
            if not skills_dir.is_dir():
                continue
            candidates.extend(sorted(skills_dir.glob('*/SKILL.md')))

    project_skills = marketplace_root.parent.parent / '.claude' / 'skills'
    if project_skills.is_dir():
        candidates.extend(sorted(project_skills.glob('finalize-step-*/SKILL.md')))

    return candidates


def _merge_gate_order(steps: list[_StepDoc]) -> int | None:
    """Resolve the merge-gate order from the discovered ``branch-cleanup`` record."""
    for step in steps:
        if step.name == _MERGE_GATE_STEP_NAME and step.order is not None:
            return step.order
    return None


def analyze_mutates_source_order(marketplace_root: Path) -> list[dict]:
    """Flag every source-mutating finalize step ordered at or after the merge gate.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles root (the directory that contains the
        ``plan-marshall``, ``pm-plugin-development``, etc. bundle directories —
        i.e. ``<repo>/marketplace/bundles``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree, and empty when the
        merge-gate step is not discoverable).
    """
    marketplace_root = Path(marketplace_root)

    steps: list[_StepDoc] = []
    for path in _candidate_paths(marketplace_root):
        step = _parse_step_doc(path)
        if step is not None:
            steps.append(step)

    merge_order = _merge_gate_order(steps)
    if merge_order is None:
        return []

    findings: list[Finding] = []
    for step in steps:
        if step.mutates_source is None:
            # No source-mutation claim — out of scope, never a false positive.
            continue
        if step.mutates_source.lower() not in _TRUTHY:
            continue
        if step.order is None or step.order < merge_order:
            continue
        findings.append(
            Finding(
                type=FINDING_TYPE,
                file=str(step.path),
                line=step.order_line,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                details={
                    'step_name': step.name,
                    'step_order': step.order,
                    'merge_gate_order': merge_order,
                },
                extra={
                    'rule': RULE_NAME,
                    'message': (
                        f'Finalize step `{step.name}` declares '
                        f'mutates_source: true but is ordered {step.order}, at or '
                        f'after the merge gate `{_MERGE_GATE_STEP_NAME}` '
                        f'(order {merge_order}). Its source edits are unpushable: '
                        f'the feature branch is already merged, so the edit cannot '
                        f'ride the PR. Move the step into the settle band (before '
                        f'the merge gate) or drop the source mutation. See '
                        f'phase-6-finalize/standards/source-edit-pushability.md.'
                    ),
                },
            )
        )
    return [f.to_dict() for f in findings]
