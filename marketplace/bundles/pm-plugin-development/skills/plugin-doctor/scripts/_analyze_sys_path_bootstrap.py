#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``sys.path`` bootstrap guard for the ``sys-path-bootstrap`` rule.

Deterministic AST-based static analyzer that flags every
``sys.path.insert(...)`` / ``sys.path.append(...)`` call in a marketplace skill
script whose file is not on an explicit allowlist of sanctioned sites.

Why this rule exists
--------------------
Marketplace scripts run through the executor, which injects a ``PYTHONPATH``
covering every skill ``scripts/`` directory (and its nested subdirectories)
before it dispatches; tests mirror the same set onto ``sys.path`` via
``conftest`` and mypy via ``MYPYPATH``. A per-script ``sys.path`` bootstrap that
walks ancestors to find a shared module — or re-inserts a script's own directory
for sibling imports — is therefore dead weight in every real context (a same-dir
insert is a no-op because Python already puts a script's own directory on
``sys.path[0]``). Such bootstraps also drift silently: mypy resolves imports via
``MYPYPATH`` independently of the runtime insert, so a broken or redundant
bootstrap is invisible to static analysis and only fails at runtime.

Enforcement model
-----------------
The rule is an allowlist gate, not a heuristic. Any ``sys.path`` mutation call in
a NON-allowlisted skill script is a finding. Adding a genuinely load-bearing site
(a script that runs before the executor exists, or a functional lazy-import that
must add a directory on demand and degrade gracefully) is a conscious, reviewed
act: the file is added to :data:`_ALLOWLIST` with its justification. This mirrors
the ``warn_unused_ignores`` guard that keeps the import-not-found silencing
comments from creeping back.

Allowlist categories
--------------------
1. **Pre-executor entry points** — scripts invoked before
   ``.plan/execute-script.py`` exists (the executor generator, the
   marshall-steward wizard scripts, the permission-fix wizard step and the
   permission chain it imports, the platform-runtime router and its Claude
   runtime). These have no executor-provided ``PYTHONPATH`` to rely on.
2. **Functional lazy-imports** — functions that add a specific skill's scripts
   directory on demand to import an optional cross-skill module, degrading
   gracefully when it is absent (build-parser loading, build-map derivation,
   dynamic build-config resolution, file-path subprocess dependency wiring).
3. **Dynamic-introspection tools** — the plugin-discovery loader and the two
   plugin-doctor analyzers that import an arbitrary target script's directory to
   introspect it.

Findings have the shape::

    {
        'rule_id': 'sys-path-bootstrap',
        'type': 'sys_path_bootstrap',
        'rule': 'analyze_sys_path_bootstrap',
        'file': '<absolute script path>',
        'line': <int, 1-based>,
        'severity': 'error',
        'fixable': False,
        'call': 'sys.path.insert' | 'sys.path.append',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_sys_path_bootstrap(marketplace_root)``: entry point — scans every
  ``*/skills/*/scripts/**/*.py`` under ``marketplace_root``.
"""

from __future__ import annotations

import ast
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'sys-path-bootstrap'
RULE_NAME = 'analyze_sys_path_bootstrap'
FINDING_TYPE = 'sys_path_bootstrap'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='file-local',
)

# Sanctioned ``sys.path`` mutation sites, keyed by their path relative to the
# marketplace-bundles root. Each entry is load-bearing — see the module docstring
# for the three category definitions. A NEW sys.path bootstrap must be justified
# and added here, or (preferably) removed in favour of the executor-injected
# PYTHONPATH.
_ALLOWLIST: frozenset[str] = frozenset(
    {
        # 1. Pre-executor entry points (run before .plan/execute-script.py exists)
        'plan-marshall/skills/tools-script-executor/scripts/generate_executor.py',
        'plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py',
        'plan-marshall/skills/marshall-steward/scripts/determine_mode.py',
        'plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py',
        'plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py',
        'plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py',
        'plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py',
        'plan-marshall/skills/platform-runtime/scripts/platform_runtime.py',
        'plan-marshall/skills/platform-runtime/scripts/claude_runtime.py',
        # 2. Functional lazy-imports (add a directory on demand, degrade gracefully)
        'plan-marshall/skills/script-shared/scripts/marketplace_paths.py',
        'plan-marshall/skills/manage-architecture/scripts/_architecture_core.py',
        'plan-marshall/skills/manage-architecture/scripts/_cmd_client_build.py',
        'plan-marshall/skills/tools-integration-ci/scripts/_ci_log_filter.py',
        'plan-marshall/skills/script-shared/scripts/build/_build_queue_slot.py',
        # 3. Dynamic-introspection tools (import an arbitrary target dir to load it)
        'pm-plugin-development/skills/plan-marshall-plugin/scripts/plugin_discover.py',
        'pm-plugin-development/skills/plugin-doctor/scripts/_analyze_finalize_step_token.py',
        'pm-plugin-development/skills/plugin-doctor/scripts/_analyze_step_configurable_contract.py',
    }
)


def _is_sys_path_mutation(node: ast.AST) -> str | None:
    """Return ``'sys.path.insert'`` / ``'sys.path.append'`` for a matching call.

    Matches ``sys.path.insert(...)`` and ``sys.path.append(...)`` by AST shape so
    the same tokens appearing inside a string literal, comment, or regex (as they
    do in the analyzer modules that detect this pattern) are never mistaken for a
    real mutation. Returns ``None`` for any other node.
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in ('insert', 'append'):
        return None
    value = func.value
    if (
        isinstance(value, ast.Attribute)
        and value.attr == 'path'
        and isinstance(value.value, ast.Name)
        and value.value.id == 'sys'
    ):
        return f'sys.path.{func.attr}'
    return None


def _make_finding(path: Path, line_no: int, call: str) -> dict:
    return Finding(
        type=FINDING_TYPE,
        file=str(path),
        line=line_no,
        severity='error',
        fixable=False,
        rule_id=RULE_ID,
        description=(
            f'``{call}`` in a marketplace skill script is a per-script sys.path '
            'bootstrap. The executor injects a PYTHONPATH covering every skill '
            'scripts/ directory before it dispatches (tests mirror it via conftest, '
            'mypy via MYPYPATH), so cross-skill imports resolve without it — write '
            'the import plainly. If this site is genuinely load-bearing (runs before '
            'the executor exists, or is a functional lazy-import that degrades '
            'gracefully), add its path to _ALLOWLIST in _analyze_sys_path_bootstrap.py '
            'with a justification.'
        ),
        extra={'rule': RULE_NAME, 'call': call},
    ).to_dict()


def _scan_file(path: Path, rel: str) -> list[dict]:
    """Scan one script for non-allowlisted ``sys.path`` mutations."""
    try:
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text)
    except (OSError, UnicodeDecodeError, SyntaxError):
        # A file the doctor cannot read or parse is surfaced by other rules;
        # this rule stays silent rather than emitting a spurious finding.
        return []

    findings: list[dict] = []
    for node in ast.walk(tree):
        call = _is_sys_path_mutation(node)
        if call is not None:
            findings.append(_make_finding(path, getattr(node, 'lineno', 0), call))
    return findings


def _script_targets(marketplace_root: Path) -> list[Path]:
    """Return every ``*.py`` under any bundle's ``skills/*/scripts/`` tree."""
    return sorted(
        p for p in marketplace_root.glob('*/skills/*/scripts/**/*.py') if p.is_file()
    )


def analyze_sys_path_bootstrap(marketplace_root: Path) -> list[dict]:
    """Flag ``sys.path`` mutations in non-allowlisted marketplace skill scripts.

    Walks ``marketplace_root/*/skills/*/scripts/**/*.py`` and reports every
    ``sys.path.insert`` / ``sys.path.append`` call whose file is not on
    :data:`_ALLOWLIST`.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace-bundles root (the directory that contains the
        ``plan-marshall``, ``pm-plugin-development``, … bundle directories).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree).
    """
    findings: list[dict] = []
    for script in _script_targets(marketplace_root):
        rel = script.relative_to(marketplace_root).as_posix()
        if rel in _ALLOWLIST:
            continue
        findings.extend(_scan_file(script, rel))
    return findings
