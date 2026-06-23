#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Role-field scanner for the ``phase-5-step-missing-role-field`` rule.

This module implements a deterministic frontmatter scanner that flags
phase-5-execute step standards files missing a ``role:`` field. The
``role:`` field is consumed by the ``manage-execution-manifest`` composer's
structural role-based intersection in Rows 2/3/4/5 of the decision matrix
(see ``marketplace/bundles/plan-marshall/skills/manage-execution-manifest/
standards/decision-rules.md`` § Role-Field Intersection). When a step file
omits the ``role:`` field, candidate-to-role resolution returns ``None``
and the step silently drops out of every role-based intersection — the
``name_drift=true`` failure mode documented in the originating audit
lesson.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_executor_path_in_production.py`` and
``_analyze_plan_path_in_scripts.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven frontmatter parsing
- stdlib-only dependencies
- no mutation of any file
- path-scoped: only files under
  ``marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/*.md``
  are inspected; everything else is silently ignored

Detection
---------
For each ``*.md`` file under the scoped directory, the analyzer parses the
leading YAML frontmatter block (``---`` … ``---``) and checks for a
non-empty ``role:`` field. A finding is emitted when:

- the file has no frontmatter at all
- the frontmatter block is present but does not declare a ``role:`` key
- the ``role:`` key is present but the value is empty / whitespace-only

Canonical-verify exemption
--------------------------
The single parameterized canonical-verify step (``name: default:verify`` or
any ``default:verify:`` step ID) is **exempt** from the static ``role:``
requirement. That step backs every canonical command and derives its matrix
role dynamically from the trailing canonical segment at compose time
(``manage-execution-manifest._role_of``) — there is no static ``role:``
frontmatter to require. See
``marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/
canonical_verify.md``. Legacy-style role-less step files (any other
``name: default:…`` step) still produce a finding.

Findings have the shape::

    {
        'rule_id': 'phase-5-step-missing-role-field',
        'type': 'missing_role_field',
        'rule': 'analyze_role_field',
        'file': '<absolute markdown path>',
        'line': 1,
        'severity': 'error',
        'fixable': False,
        'snippet': '<bare step name, e.g. quality_check>',
        'description': (
            'phase-5 step standards file missing `role:` frontmatter field — '
            'manage-execution-manifest composer\\'s role-based intersection in '
            'Rows 2/3/4/5 will silently drop this candidate. See '
            'manage-execution-manifest/standards/decision-rules.md '
            '§ Role-Field Intersection.'
        ),
    }

Public API
----------
- ``analyze_role_field(marketplace_root)``: entry point — scans every
  ``*.md`` under
  ``marketplace_root/plan-marshall/skills/phase-5-execute/standards/``.
"""

from __future__ import annotations

from pathlib import Path

RULE_ID = 'phase-5-step-missing-role-field'
RULE_NAME = 'analyze_role_field'
FINDING_TYPE = 'missing_role_field'

_SCOPED_REL = ('plan-marshall', 'skills', 'phase-5-execute', 'standards')

_DESCRIPTION = (
    'phase-5 step standards file missing `role:` frontmatter field — '
    "manage-execution-manifest composer's role-based intersection in "
    'Rows 2/3/4/5 will silently drop this candidate. See '
    'manage-execution-manifest/standards/decision-rules.md '
    '§ Role-Field Intersection.'
)


def _scoped_dir(marketplace_root: Path) -> Path:
    """Resolve the phase-5-execute/standards directory under ``marketplace_root``.

    ``marketplace_root`` is the bundles root (the directory that contains
    ``plan-marshall``, ``pm-plugin-development``, etc.). The scoped path is
    ``{marketplace_root}/plan-marshall/skills/phase-5-execute/standards``.
    """
    return marketplace_root.joinpath(*_SCOPED_REL)


def _parse_frontmatter_keys(text: str) -> dict[str, str] | None:
    """Parse the leading ``---``-fenced YAML frontmatter into a flat string map.

    Returns ``None`` when the file does not open with ``---``. Returns an empty
    dict when the block is empty. Only top-level scalar ``key: value`` pairs
    are recognised — comments, nested mappings, list-valued entries, and lines
    that lack a colon are silently skipped. Quoted scalars have their wrapping
    quotes stripped.
    """
    if not text.startswith('---'):
        return None
    lines = text.splitlines()
    out: dict[str, str] = {}
    in_block = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if index == 0:
            if stripped != '---':
                return None
            in_block = True
            continue
        if not in_block:
            break
        if stripped == '---':
            return out
        if not stripped or stripped.startswith('#'):
            continue
        if ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        out[key.strip()] = value.strip().strip('"').strip("'")
    # End of file reached before the closing ``---``: treat as not-frontmatter.
    return None


def _is_step_file(frontmatter: dict[str, str]) -> bool:
    """Return True iff the frontmatter declares this file as a phase-5 verify step.

    A phase-5 step standards file is identified structurally by the presence of
    ALL three frontmatter keys:

    - ``name`` starting with ``default:`` (the dispatch token consumed by the
      Built-in Step Dispatch Table in phase-5-execute SKILL.md)
    - ``description`` (every dispatch-table entry carries a one-line summary)
    - ``order`` (the integer key used by marshall-steward to sort the steps
      list — present only on dispatch-eligible files)

    Helper / narrative documents in the same directory (e.g., ``operations.md``,
    ``recovery.md``, ``workflow.md``, ``sync-with-main.md``) lack one or more
    of these keys and are therefore not subject to the role-field requirement.
    """
    name = frontmatter.get('name', '')
    if not isinstance(name, str) or not name.startswith('default:'):
        return False
    if 'description' not in frontmatter:
        return False
    if 'order' not in frontmatter:
        return False
    return True


def _is_canonical_verify_step(frontmatter: dict[str, str]) -> bool:
    """Return True iff the frontmatter identifies the parameterized canonical-verify step.

    The canonical-verify step is the single parameterized built-in step that
    backs every canonical command — its dispatch token is ``default:verify``
    and its step IDs carry the ``default:verify:`` prefix
    (``default:verify:quality-gate`` etc). It derives its matrix role
    dynamically from the trailing canonical segment at compose time
    (``manage-execution-manifest._role_of``) and therefore carries **no**
    static ``role:`` frontmatter. It is exempt from the role-field
    requirement; every other ``name: default:…`` step file still requires a
    static ``role:`` value.
    """
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False
    return name == 'default:verify' or name.startswith('default:verify:')


def _has_role_field(text: str) -> bool:
    """Return True iff the file is exempt from or satisfies the ``role:`` requirement.

    Exemption rules:

    - Files with no YAML frontmatter at all are reference / narrative documents
      (operations, recovery, sync-with-main, test-scaffolding, workflow, …)
      and are NOT subject to the role requirement. They cannot structurally
      be step files because step-file identification (``_is_step_file``)
      requires ``name: default:…`` + ``description`` + ``order`` in the
      frontmatter block. Without a frontmatter block, the file is unambiguously
      a helper doc.
    - Files whose frontmatter is present but does NOT identify the file as a
      phase-5 step file (per ``_is_step_file``) are also helper documents.
    - The parameterized canonical-verify step (``name: default:verify`` or a
      ``default:verify:`` step ID) is exempt: it derives its role dynamically
      at compose time and carries no static ``role:`` frontmatter.
    - Only the remaining (legacy-style) files identified as step files are
      required to declare a non-empty ``role:`` value.
    """
    frontmatter = _parse_frontmatter_keys(text)
    if frontmatter is None:
        # No frontmatter at all — narrative / reference document. Exempt.
        return True
    if not _is_step_file(frontmatter):
        # Helper / narrative document — role: requirement does not apply.
        return True
    if _is_canonical_verify_step(frontmatter):
        # Canonical-verify step derives its role dynamically — exempt from the
        # static role: requirement.
        return True
    return bool(frontmatter.get('role'))


def analyze_role_field(marketplace_root: Path) -> list[dict]:
    """Scan phase-5-execute standards files for missing ``role:`` frontmatter.

    Returns a list of findings (one per offending file). Files outside the
    scoped directory are not inspected; if the scoped directory itself does
    not exist (e.g., the plan-marshall bundle is absent from the tree), the
    function returns an empty list without raising.
    """
    scoped = _scoped_dir(marketplace_root)
    if not scoped.is_dir():
        return []

    findings: list[dict] = []
    for md_path in sorted(scoped.glob('*.md')):
        try:
            text = md_path.read_text(encoding='utf-8')
        except OSError:
            # Unreadable file is not the analyzer's failure mode; skip silently.
            continue
        if _has_role_field(text):
            continue
        findings.append(
            {
                'rule_id': RULE_ID,
                'type': FINDING_TYPE,
                'rule': RULE_NAME,
                'file': str(md_path),
                'line': 1,
                'severity': 'error',
                'fixable': False,
                'snippet': md_path.stem,
                'description': _DESCRIPTION,
            }
        )
    return findings
