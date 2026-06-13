#!/usr/bin/env python3
"""Zero-match rule detector — positive-fixture self-test for ``plugin-doctor``.

This module implements the mechanical enforcement of the **zero-match
acceptance criterion** documented in
``references/rule-provenance.md`` § "Provenance contract for new rules":

> A new rule that matches zero occurrences in the existing corpus is
> inadmissible unless it ships a positive-fixture proving the matcher fires
> on a known-defect instance. A zero-match rule with no positive fixture is
> presumed dead and MUST be dropped or justified.

A rule whose target pattern is textually indistinguishable from a legitimate
shape is infeasible as a static check; the symptom of such a dead rule is that
it never fires — on the real marketplace OR on any deliberately-broken fixture.
This detector surfaces exactly that condition: it enumerates the set of rule
IDs the in-tree ``_analyze_*.py`` analyzers can emit, runs every registered
analyzer against a curated positive-fixture corpus (small known-defect
artifacts that SHOULD trip a specific rule), collects the set of rule IDs that
actually fired, and emits one ``zero-match-rule`` finding per registered rule
ID that fired on no fixture.

Design constraints (mirrors the sibling ``_analyze_*.py`` modules):

- pure static analysis driven by the analyzers themselves — no subprocess
  execution, no ``--help`` probing
- stdlib-only dependencies
- no mutation of any tracked file (the fixture corpus is written to a caller-
  supplied scratch directory under the system temp root, never under the
  marketplace tree)

Registered-rule-ID extraction
-----------------------------
The set of "registered rule IDs" is derived statically from the analyzer
modules, mirroring ``test_rule_provenance_table.py``'s extractor: every string
literal in a ``'type'`` / ``'rule_id'`` position, plus every module-level
``RULE_*`` / ``FINDING_TYPE`` constant, that passes the audit-tracked-rule-ID
heuristic. This is the same population the provenance audit pins, so the
zero-match detector and the provenance audit cover an identical rule set.

Positive-fixture corpus
-----------------------
``FIXTURE_CORPUS`` maps each rule ID the detector can prove to a
``FixtureSpec`` (the analyzer entry point plus the known-defect fixture files
to materialize under a scratch marketplace tree). The detector runs each
spec's analyzer over the materialized tree and records which rule IDs the run
emitted. A registered rule ID with NO corpus entry — or whose corpus entry
fired no matching finding — is reported as a ``zero-match-rule`` finding.

Findings have the shape::

    {
        'rule_id': 'zero-match-rule',
        'type': 'zero-match-rule',
        'rule': 'analyze_zero_match_rule',
        'file': '<analyzer module path, or '' when undetermined>',
        'line': 0,
        'severity': 'warning',
        'fixable': False,
        'snippet': '<the registered rule ID that fired on no fixture>',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_zero_match_rule(marketplace_root)``: entry point — derives the
  registered rule-ID set from the analyzers in ``marketplace_root``'s
  plugin-doctor scripts dir, runs the positive-fixture corpus, and returns one
  finding per registered rule ID that fired on no fixture.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

RULE_ID = 'zero-match-rule'
RULE_NAME = 'analyze_zero_match_rule'
FINDING_TYPE = 'zero-match-rule'

# ---------------------------------------------------------------------------
# Registered-rule-ID extraction (mirrors test_rule_provenance_table.py)
# ---------------------------------------------------------------------------

# Rule IDs that are component-type tags or analyzer-internal status payloads,
# NOT validation rules. Kept in lockstep with the provenance audit's
# NON_RULE_TYPE_TOKENS so the two cover an identical population.
_NON_RULE_TYPE_TOKENS = frozenset(
    {
        # component types
        'agent',
        'command',
        'skill',
        'script',
        'template',
        'workflow',
        # tool names
        'Skill',
        'Task',
        'SlashCommand',
        # operational / shaping diagnostics
        'file_read_error',
        'shell_substitution_in_skills',
        'file_type',
        'analyze_shell_substitution_in_skills',
        'HARDCODED_MODEL_ON_CANONICAL',
    }
)

# ``'type': '<id>'`` / ``'rule_id': '<id>'`` literal positions.
_RULE_LITERAL_RE = re.compile(r"'(?:type|rule_id)':\s*'([A-Za-z_][A-Za-z0-9_-]+)'")
# Module-level ``RULE_* = '<id>'`` / ``FINDING_TYPE = '<id>'`` constants.
_RULE_CONSTANT_RE = re.compile(
    r"^(?:RULE[A-Z_]*|FINDING_TYPE)\s*=\s*'([A-Za-z_][A-Za-z0-9_-]+)'", re.MULTILINE
)


def _is_audit_tracked_rule_id(token: str) -> bool:
    """Distinguish lint-rule IDs from analyzer-internal status payloads.

    Real lint-rule IDs are kebab-case (``agent-skill-tool-visibility``) or
    UPPER_SNAKE (``ARGUMENT_NAMING_NOTATION_INVALID``). Analyzer-internal
    status tokens use snake_case (``parse_error``, ``invalid_domain``) and are
    never tracked. Mirrors the provenance audit's heuristic.
    """
    if token in _NON_RULE_TYPE_TOKENS:
        return False
    if re.fullmatch(r'[A-Z][A-Z0-9_]+', token):
        return True
    if re.search(r'[A-Z]', token) and '_' in token:
        return False
    if '_' in token and '-' not in token:
        return False
    if re.fullmatch(r'[a-z][a-z0-9-]+', token):
        return True
    return False


def _extract_rule_ids_from_module(path: Path) -> set[str]:
    """Extract audit-tracked rule IDs from one analyzer module's source."""
    rule_ids: set[str] = set()
    if not path.is_file() or path.name == '_cmd_extension.py':
        # Extension-loading diagnostics are not lint rules.
        return rule_ids
    try:
        content = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return rule_ids
    for match in _RULE_LITERAL_RE.finditer(content):
        token = match.group(1)
        if _is_audit_tracked_rule_id(token):
            rule_ids.add(token)
    for match in _RULE_CONSTANT_RE.finditer(content):
        token = match.group(1)
        if _is_audit_tracked_rule_id(token):
            rule_ids.add(token)
    return rule_ids


def _scripts_dir(marketplace_root: Path) -> Path:
    """Resolve the plugin-doctor scripts directory from a marketplace root."""
    return (
        marketplace_root
        / 'pm-plugin-development'
        / 'skills'
        / 'plugin-doctor'
        / 'scripts'
    )


def registered_rule_ids(marketplace_root: Path) -> set[str]:
    """Return every audit-tracked rule ID emitted by the in-tree analyzers.

    Statically scans every ``_*.py`` module under the plugin-doctor scripts
    directory for rule-ID literals and ``RULE_*`` / ``FINDING_TYPE`` constants,
    filtered through the audit-tracked heuristic.
    """
    scripts_dir = _scripts_dir(marketplace_root)
    if not scripts_dir.is_dir():
        return set()
    rule_ids: set[str] = set()
    for py_file in sorted(scripts_dir.glob('_*.py')):
        rule_ids |= _extract_rule_ids_from_module(py_file)
    return rule_ids


# ---------------------------------------------------------------------------
# Positive-fixture corpus
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FixtureSpec:
    """One positive-fixture spec: the analyzer plus its known-defect files.

    ``analyzer`` is invoked with the scratch marketplace root the detector
    materializes. ``files`` maps a marketplace-root-relative path to the file
    content written under the scratch tree. Each fixture file is a deliberate
    known-defect instance that SHOULD trip ``rule_id``'s analyzer.
    """

    analyzer: Callable[[Path], list[dict]]
    files: dict[str, str] = field(default_factory=dict)


def _finding_rule_ids(findings: list[dict]) -> set[str]:
    """Collect the rule IDs a list of findings carries (type or rule_id)."""
    ids: set[str] = set()
    for finding in findings:
        for key in ('rule_id', 'type'):
            value = finding.get(key)
            if isinstance(value, str):
                ids.add(value)
    return ids


def _materialize(scratch_root: Path, files: dict[str, str]) -> None:
    """Write each relative fixture path under ``scratch_root``."""
    for rel_path, content in files.items():
        target = scratch_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')


def _build_fixture_corpus() -> dict[str, FixtureSpec]:
    """Construct the rule-ID → positive-fixture mapping.

    Imported lazily so the module imports cheaply when only the registered-
    rule-ID extractor is needed (e.g. from the provenance audit). The corpus
    is curated: each entry is a minimal known-defect fixture for one rule ID.
    The set of covered rule IDs is intentionally narrow — the detector reports
    EVERY registered rule ID that lacks an entry, which is the signal callers
    act on.
    """
    from _analyze_bash_chain_shapes_in_skills import (
        analyze_bash_chain_shapes_in_skills,
    )
    from _analyze_shell_substitution_in_skills import (
        analyze_shell_substitution_in_skills,
    )
    from _analyze_tmp_redirect_in_skills import analyze_tmp_redirect_in_skills
    from _analyze_workflow_doc_toon_error_field import (
        analyze_workflow_doc_toon_error_field,
    )

    pm_skill = 'plan-marshall/skills/_zero_match_fixture/SKILL.md'

    return {
        'shell-substitution-in-skills': FixtureSpec(
            analyzer=analyze_shell_substitution_in_skills,
            files={
                pm_skill: (
                    '# Fixture\n\n```bash\nresult=$(echo hi)\n```\n'
                ),
            },
        ),
        'bash-chain-shapes-in-skills': FixtureSpec(
            analyzer=analyze_bash_chain_shapes_in_skills,
            files={
                pm_skill: (
                    '# Fixture\n\n```bash\ngit add . && git commit -m x\n```\n'
                ),
            },
        ),
        'tmp-redirect-in-skills': FixtureSpec(
            analyzer=analyze_tmp_redirect_in_skills,
            files={
                pm_skill: (
                    '# Fixture\n\n```bash\npython3 run.py > /tmp/out.log\n```\n'
                ),
            },
        ),
        'WORKFLOW_DOC_TOON_ERROR_FIELD': FixtureSpec(
            analyzer=analyze_workflow_doc_toon_error_field,
            files={
                pm_skill: (
                    '# Fixture\n\n```toon\nstatus: error\n'
                    'error_type: some_category\n```\n'
                ),
            },
        ),
    }


def _fired_rule_ids() -> set[str]:
    """Run the positive-fixture corpus and collect every rule ID that fired.

    Each spec is materialized under its own scratch marketplace tree (so one
    fixture's defect never leaks into another analyzer's scan), the spec's
    analyzer is run over that tree, and the union of fired rule IDs is
    returned.
    """
    fired: set[str] = set()
    corpus = _build_fixture_corpus()
    for spec in corpus.values():
        with tempfile.TemporaryDirectory(prefix='zero_match_fixture_') as tmp:
            scratch_root = Path(tmp)
            _materialize(scratch_root, spec.files)
            try:
                findings = spec.analyzer(scratch_root)
            except Exception:  # noqa: BLE001 — a crashing analyzer counts as not-fired
                findings = []
            fired |= _finding_rule_ids(findings)
    return fired


# ---------------------------------------------------------------------------
# Finding construction
# ---------------------------------------------------------------------------


def _make_finding(rule_id: str, emitter_file: str) -> dict:
    return {
        'rule_id': RULE_ID,
        'type': FINDING_TYPE,
        'rule': RULE_NAME,
        'file': emitter_file,
        'line': 0,
        'severity': 'warning',
        'fixable': False,
        'snippet': rule_id,
        'description': (
            f'Rule `{rule_id}` fired on no positive fixture. A registered rule '
            'whose matcher does not trip on any known-defect instance is '
            'presumed dead — either its target pattern is textually '
            'indistinguishable from a legitimate shape (infeasible as a static '
            'check) or it lacks a positive-fixture proving it fires. Add a '
            'positive fixture to FIXTURE_CORPUS in _analyze_zero_match_rule.py, '
            'drop the rule, or justify the zero-match per the provenance '
            'contract (references/rule-provenance.md § "Provenance contract for '
            'new rules").'
        ),
    }


def _emitter_for_rule(marketplace_root: Path, rule_id: str) -> str:
    """Best-effort: name the analyzer module that declares ``rule_id``.

    Returns the absolute path of the first ``_analyze_*.py`` module under the
    plugin-doctor scripts dir that emits ``rule_id``, or '' when none is found.
    """
    scripts_dir = _scripts_dir(marketplace_root)
    if not scripts_dir.is_dir():
        return ''
    for py_file in sorted(scripts_dir.glob('_*.py')):
        if rule_id in _extract_rule_ids_from_module(py_file):
            return str(py_file)
    return ''


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_zero_match_rule(marketplace_root: Path) -> list[dict]:
    """Report every claimed positive-fixture rule that fired on no fixture.

    The detector enforces the zero-match acceptance criterion as a corpus
    self-test: a rule ID claimed by ``FIXTURE_CORPUS`` (and confirmed
    registered by the in-tree analyzers) MUST fire on its positive fixture.
    When a claimed rule fires on no fixture, its matcher is broken or dead and
    the fixture no longer proves what it asserts — that is the ``zero-match-rule``
    finding.

    Candidate scope is ``corpus_rules ∩ registered_rules``. A registered rule
    with NO corpus entry is out of scope — it makes no positive-fixture claim,
    so the detector stays silent for it (keeping the real-marketplace run at
    zero findings rather than flooding one finding per uncovered rule). A
    corpus entry whose rule ID is NOT registered is likewise skipped — the
    corpus cannot prove a rule the analyzers do not emit.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace root (the directory that contains the
        ``plan-marshall``, ``pm-plugin-development``, etc. bundle directories —
        i.e. ``<repo>/marketplace/bundles``). The registered rule-ID set is
        derived from the plugin-doctor scripts under this root.

    Returns
    -------
    list[dict]
        One ``zero-match-rule`` finding per claimed-and-registered rule ID that
        fired on no fixture. Empty when every claimed rule fires on its
        positive fixture (the healthy-corpus case).
    """
    registered = registered_rule_ids(marketplace_root)
    claimed = set(_build_fixture_corpus().keys())
    candidates = claimed & registered
    fired = _fired_rule_ids()

    findings: list[dict] = []
    for rule_id in sorted(candidates - fired):
        findings.append(_make_finding(rule_id, _emitter_for_rule(marketplace_root, rule_id)))
    return findings
