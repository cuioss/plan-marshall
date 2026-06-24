# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Shared firing-fixture corpus for the plugin-doctor test-layer suite-coverage check.

This module is the test-layer replacement for the deleted runtime
``_analyze_zero_match_rule.py`` corpus. Its job is to DERIVE the set of
plugin-doctor rule IDs that "fire" — exactly as the suite-coverage meta-test
(``test_zero_match_suite_coverage.py``) needs them — by running each registered
analyzer over a minimal known-defect positive fixture and collecting the rule
IDs the run emitted.

The contract the meta-test enforces is::

    registered_rule_ids(MARKETPLACE_ROOT) - fired_rule_ids() - EXEMPT_RULE_IDS == ∅

where:

- ``registered_rule_ids(root)`` — the audit-tracked rule-ID population, scanned
  statically from every ``_*.py`` analyzer module (relocated here verbatim from
  the deleted analyzer; the same extractor ``test_rule_provenance_table.py``
  uses).
- ``fired_rule_ids()`` — the union of rule IDs every spec in ``FIXTURE_CORPUS``
  emits when run over its own scratch tree (this module's value proposition).
  "Fired against its positive fixture" is the operative definition of "fired in
  the suite".
- ``EXEMPT_RULE_IDS`` — the shrunken, per-entry-justified frozenset of rules
  that structurally cannot fire on any fixture.

Design constraints (mirror the deleted analyzer and the sibling tests):

- pure static analysis driven by the analyzers themselves — no subprocess,
  no ``--help`` probing.
- stdlib-only.
- no mutation of any tracked file — every fixture is materialized under a
  per-spec ``tempfile.TemporaryDirectory`` scratch root, never under the
  marketplace tree.

Two fixture shapes are supported by ``FixtureSpec``:

- ``analyzer`` set: a marketplace-wide analyzer ``fn(marketplace_root) ->
  list[dict]`` is run over a scratch root materialized from ``files``.
- ``component`` set: a per-component rule run through
  ``analyze_component(component_dict)`` — ``files`` materializes the component
  artifact(s) and ``component`` is a callable ``fn(scratch_root) -> dict``
  building the component dict ``analyze_component`` consumes.

Cross-file rules (``duplication`` / ``extraction`` / ``terminology``) are NOT
static-detection findings — they are emitted only by ``verify_findings`` on a
verified LLM claim. They are covered by ``test_analyze_crossfile.py`` (a
verifier-echo test) which feeds its emitted finding types into ``record_fired``
so the suite-coverage meta-test counts them. ``fired_rule_ids()`` below unions
that recorded set in via the ``_EXTRA_FIRED`` registry.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

# Source text of the real configurable-contract parser, materialized into the
# step-configurable-contract fixture's scratch tree so the analyzer's dynamic
# import (``_load_contract_parser``) resolves. The parser imports
# ``marketplace_bundles`` / ``toon_parser`` at module top, both on the test
# PYTHONPATH, and neither is called during a ``parse_configurable(path)`` scan.
_CONFIGURABLE_CONTRACT_SRC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'extension-api'
    / 'scripts'
    / 'configurable_contract.py'
).read_text(encoding='utf-8')

# ---------------------------------------------------------------------------
# Analyzer module loading — load every analyzer entry point once via the shared
# loader so intra-bundle ``from _analyze_* import ...`` references resolve.
# ---------------------------------------------------------------------------


def _load(filename: str, name: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_da = _load('_doctor_analysis.py', '_doctor_analysis_fixtures')
analyze_component = _da.analyze_component

_atrs = _load('_analyze_tmp_redirect_in_skills.py', '_atrs_fixtures')
_asrtp = _load('_analyze_skill_relative_temp_path.py', '_asrtp_fixtures')
_assub = _load('_analyze_shell_substitution_in_skills.py', '_assub_fixtures')
_abcs = _load('_analyze_bash_chain_shapes_in_skills.py', '_abcs_fixtures')
_awdtef = _load('_analyze_workflow_doc_toon_error_field.py', '_awdtef_fixtures')
_ahps = _load('_analyze_historical_prose_in_skills.py', '_ahps_fixtures')
_alis = _load('_analyze_lesson_id_in_skill_prose.py', '_alis_fixtures')
_aatd = _load('_analyze_allowed_tools_drift.py', '_aatd_fixtures')
_asdrc = _load('_analyze_self_declared_rule_compliance.py', '_asdrc_fixtures')
_afst = _load('_analyze_finalize_step_token.py', '_afst_fixtures')
_ascc = _load('_analyze_step_configurable_contract.py', '_ascc_fixtures')
_aroe = _load('_analyze_role_field.py', '_aroe_fixtures')
_advd = _load('_analyze_declared_vs_disk.py', '_advd_fixtures')
_apmt = _load('_analyze_provides_method_table.py', '_apmt_fixtures')
_alc = _load('_analyze_literal_count.py', '_alc_fixtures')
_apj = _load('_analyze_plugin_json.py', '_apj_fixtures')
_asn = _load('_analyze_skill_notation.py', '_asn_fixtures')
_afm = _load('_analyze_frontmatter.py', '_afm_fixtures')
_armc = _load('_analyze_resolver_matrix_coverage.py', '_armc_fixtures')
_aan = _load('_analyze_argument_naming.py', '_aan_fixtures')
_asimp = _load('_analyze_simplicity.py', '_asimp_fixtures')
_acra = _load('_analyze_cmd_root_anchoring.py', '_acra_fixtures')
_aepp = _load('_analyze_executor_path_in_production.py', '_aepp_fixtures')
_apps = _load('_analyze_plan_path_in_scripts.py', '_apps_fixtures')
_afcgr = _load('_analyze_fail_closed_gate_reads.py', '_afcgr_fixtures')
_amfv = _load('_analyze_metadata_field_validity.py', '_amfv_fixtures')
_arbm = _load('_analyze_resolution_branch_markers.py', '_arbm_fixtures')
_asat = _load('_analyze_shell_active_tokens.py', '_asat_fixtures')
_aoaf = _load('_analyze_orphan_argparse_flags.py', '_aoaf_fixtures')
_ap2r = _load('_analyze_phase2_refine_contract.py', '_ap2r_fixtures')
_ans = _load('_analyze_notation_staleness.py', '_ans_fixtures')
_amfi = _load('_analyze_manage_findings_invocation.py', '_amfi_fixtures')
_ami = _load('_analyze_manage_invocation.py', '_ami_fixtures')
_avc = _load('_analyze_verb_chains.py', '_avc_fixtures')
_atc = _load('_analyze_test_conventions.py', '_atc_fixtures')
_ascd = _load('_analyze_script_call_drift.py', '_ascd_fixtures')
_accf = _load('_cmd_cross_file.py', '_accf_fixtures')
verify_findings = _accf.verify_findings
_abfic = _load('_analyze_bash_fence_inline_code_exemption.py', '_abfic_fixtures')
_asm = _load('_analyze_skill_mode.py', '_asm_fixtures')
_appu = _load('_analyze_persona_profile_uniqueness.py', '_appu_fixtures')
_apbr = _load('_analyze_persona_binding_resolves.py', '_apbr_fixtures')

# ---------------------------------------------------------------------------
# Registered-rule-ID extraction (relocated verbatim from the deleted
# _analyze_zero_match_rule.py; identical to test_rule_provenance_table.py's
# extractor so the two cover an identical population).
# ---------------------------------------------------------------------------

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

_RULE_LITERAL_RE = re.compile(r"'(?:type|rule_id)':\s*'([A-Za-z_][A-Za-z0-9_-]+)'")
_RULE_CONSTANT_RE = re.compile(
    r"^(?:RULE[A-Z_]*|FINDING_TYPE)\s*=\s*'([A-Za-z_][A-Za-z0-9_-]+)'", re.MULTILINE
)


def _is_audit_tracked_rule_id(token: str) -> bool:
    """Distinguish lint-rule IDs from analyzer-internal status payloads."""
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
    """Return every audit-tracked rule ID emitted by the in-tree analyzers."""
    scripts_dir = _scripts_dir(marketplace_root)
    if not scripts_dir.is_dir():
        return set()
    rule_ids: set[str] = set()
    for py_file in sorted(scripts_dir.glob('_*.py')):
        rule_ids |= _extract_rule_ids_from_module(py_file)
    return rule_ids


# ---------------------------------------------------------------------------
# Fixture-spec model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FixtureSpec:
    """One positive-fixture spec for a registered rule.

    Exactly one of ``analyzer`` / ``component`` drives the spec:

    - ``analyzer``: a marketplace-wide analyzer ``fn(marketplace_root) ->
      list[dict]`` run over a scratch root materialized from ``files``.
    - ``component``: a callable ``fn(scratch_root) -> dict`` building the
      component dict fed to ``analyze_component`` after ``files`` is
      materialized.

    ``files`` maps a scratch-root-relative path to the file content written
    under the scratch tree. Each fixture file is a deliberate known-defect
    instance that SHOULD trip the spec's rule.
    """

    files: dict[str, str] = field(default_factory=dict)
    analyzer: Callable[[Path], list[dict]] | None = None
    component: Callable[[Path], dict] | None = None


def _materialize(scratch_root: Path, files: dict[str, str]) -> None:
    """Write each relative fixture path under ``scratch_root``."""
    for rel_path, content in files.items():
        target = scratch_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')


def _finding_rule_ids(findings: list[dict]) -> set[str]:
    """Collect the rule IDs a list of findings carries (type or rule_id)."""
    ids: set[str] = set()
    for finding in findings:
        for key in ('rule_id', 'type'):
            value = finding.get(key)
            if isinstance(value, str):
                ids.add(value)
    return ids


# ---------------------------------------------------------------------------
# Component fixture builders — materialize a component artifact and return the
# component dict analyze_component consumes.
# ---------------------------------------------------------------------------

# Frontmatter and bodies are crafted minimal known-defect instances. Each
# builder writes its artifact under the scratch root and returns the matching
# component dict.


def _skill_component(scratch_root: Path, skill_name: str, skill_md: str) -> dict:
    skill_dir = scratch_root / 'b' / 'skills' / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(skill_md, encoding='utf-8')
    return {
        'name': skill_name,
        'path': str(skill_dir),
        'skill_md_path': str(md),
        'type': 'skill',
    }


def _agent_component(scratch_root: Path, agent_name: str, agent_md: str) -> dict:
    agents_dir = scratch_root / 'b' / 'agents'
    agents_dir.mkdir(parents=True, exist_ok=True)
    md = agents_dir / f'{agent_name}.md'
    md.write_text(agent_md, encoding='utf-8')
    return {'name': agent_name, 'path': str(md), 'type': 'agent'}


def _command_component(scratch_root: Path, cmd_name: str, cmd_md: str) -> dict:
    cmds_dir = scratch_root / 'b' / 'commands'
    cmds_dir.mkdir(parents=True, exist_ok=True)
    md = cmds_dir / f'{cmd_name}.md'
    md.write_text(cmd_md, encoding='utf-8')
    return {'name': cmd_name, 'path': str(md), 'type': 'command'}


def _skill_with_subdoc(
    scratch_root: Path, skill_name: str, subdoc_rel: str, subdoc_body: str
) -> dict:
    """Materialize a clean skill plus one known-defect sub-document.

    ``subdoc_rel`` is a skill-root-relative path like ``standards/x.md``. The
    SKILL.md itself is clean (good frontmatter, short body) so only the subdoc
    rule under test fires.
    """
    skill_dir = scratch_root / 'b' / 'skills' / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(_GOOD_SKILL_FM + '\n# Fixture\n', encoding='utf-8')
    subdoc = skill_dir / subdoc_rel
    subdoc.parent.mkdir(parents=True, exist_ok=True)
    subdoc.write_text(subdoc_body, encoding='utf-8')
    return {
        'name': skill_name,
        'path': str(skill_dir),
        'skill_md_path': str(md),
        'type': 'skill',
    }


# Reusable known-defect bodies ------------------------------------------------

# A skill SKILL.md with a forbidden ## Version section in a subdoc and various
# defects; bodies are layered per rule below.

_GOOD_SKILL_FM = (
    '---\n'
    'name: fixture-skill\n'
    'description: A fixture skill\n'
    'user-invocable: false\n'
    '---\n'
)


# ---------------------------------------------------------------------------
# Fixture corpus
# ---------------------------------------------------------------------------

# Path of a plan-marshall skill markdown used by the marketplace-wide skill
# scanners (they walk <root>/plan-marshall/skills/<skill>/SKILL.md).
_PM_SKILL = 'plan-marshall/skills/fixture-skill/SKILL.md'
_PM_STANDARD = 'plan-marshall/skills/fixture-skill/standards/x.md'


def build_fixture_corpus() -> dict[str, FixtureSpec]:
    """Construct the rule-ID → positive-fixture mapping for every fixturable rule.

    Imported analyzers are bound at module import (above). Each entry is a
    minimal known-defect fixture for one rule ID. A rule that cannot be made to
    fire on any fixture belongs in ``EXEMPT_RULE_IDS`` (with a justification),
    not here.
    """
    corpus: dict[str, FixtureSpec] = {}

    # --- Marketplace-wide skill-markdown regex scanners ---------------------

    corpus['tmp-redirect-in-skills'] = FixtureSpec(
        analyzer=_atrs.analyze_tmp_redirect_in_skills,
        files={_PM_SKILL: '# F\n\n```bash\npython3 r.py > /tmp/out.log\n```\n'},
    )
    # A relative ``.plan/temp`` path consumed by ``git -C ... commit -F`` inside a
    # bash fence — the harness Write/git -C resolution mismatch the rule catches.
    corpus['skill-relative-temp-path-git-c'] = FixtureSpec(
        analyzer=_asrtp.analyze_skill_relative_temp_path,
        files={
            _PM_SKILL: (
                '# F\n\n```bash\n'
                'git -C {worktree_path} commit -F .plan/temp/{plan_id}-commit-msg.txt\n'
                '```\n'
            )
        },
    )
    corpus['shell-substitution-in-skills'] = FixtureSpec(
        analyzer=_assub.analyze_shell_substitution_in_skills,
        files={_PM_SKILL: '# F\n\n```bash\nresult=$(echo hi)\n```\n'},
    )
    corpus['bash-chain-shapes-in-skills'] = FixtureSpec(
        analyzer=_abcs.analyze_bash_chain_shapes_in_skills,
        files={_PM_SKILL: '# F\n\n```bash\ngit add . && git commit -m x\n```\n'},
    )
    corpus['WORKFLOW_DOC_TOON_ERROR_FIELD'] = FixtureSpec(
        analyzer=_awdtef.analyze_workflow_doc_toon_error_field,
        files={_PM_SKILL: '# F\n\n```toon\nstatus: error\nerror_type: cat\n```\n'},
    )
    # A SKILL.md with valid frontmatter but no ``mode:`` key fires skill-missing-mode
    # (reason: mode_missing) and nothing else — _GOOD_SKILL_FM omits the key.
    corpus['skill-missing-mode'] = FixtureSpec(
        analyzer=_asm.analyze_skill_mode,
        files={_PM_SKILL: _GOOD_SKILL_FM + '\n# F\n'},
    )
    # persona-profile-uniqueness: two persona SKILL.md files declaring the same
    # first ``profiles:`` entry triggers a primary-profile collision finding.
    corpus['persona-profile-uniqueness'] = FixtureSpec(
        analyzer=_appu.analyze_persona_profile_uniqueness,
        files={
            'plan-marshall/skills/persona-alpha/SKILL.md': (
                '---\n'
                'name: persona-alpha\n'
                'description: Alpha persona\n'
                'implements: persona\n'
                'profiles:\n'
                '  - implementation\n'
                '---\n\n# Alpha\n'
            ),
            'plan-marshall/skills/persona-beta/SKILL.md': (
                '---\n'
                'name: persona-beta\n'
                'description: Beta persona\n'
                'implements: persona\n'
                'profiles:\n'
                '  - implementation\n'
                '---\n\n# Beta\n'
            ),
        },
    )
    # persona-binding-resolves: a persona SKILL.md with ``profiles:`` set whose
    # ``composes:`` references a non-existent persona triggers the
    # composed_persona_not_found discriminator.
    corpus['persona-binding-resolves'] = FixtureSpec(
        analyzer=_apbr.analyze_persona_binding_resolves,
        files={
            'plan-marshall/skills/persona-broken/SKILL.md': (
                '---\n'
                'name: persona-broken\n'
                'description: Broken persona\n'
                'implements: persona\n'
                'profiles:\n'
                '  - implementation\n'
                'composes:\n'
                '  - plan-marshall:persona-nonexistent\n'
                '---\n\n# Broken\n'
            ),
        },
    )
    corpus['no-historical-prose-in-skills'] = FixtureSpec(
        analyzer=_ahps.analyze_historical_prose_in_skills,
        files={
            _PM_SKILL: (
                '# F\n\n- Driving lesson: `2026-01-01-12-001` (some past event)\n'
            )
        },
    )
    corpus['no-lesson-id-in-skill-prose'] = FixtureSpec(
        analyzer=_alis.analyze_lesson_id_in_skill_prose,
        files={_PM_SKILL: '# F\n\nSee lesson `2026-01-01-12-001` for context.\n'},
    )
    corpus['skill-self-declared-rule-violation'] = FixtureSpec(
        analyzer=_asdrc.analyze_self_declared_rule_compliance,
        files={
            _PM_SKILL: (
                '# F\n\nThis skill uses flat-numbering for all steps.\n\n'
                '### Step 1a\n\nbody\n'
            )
        },
    )
    corpus['phase-5-step-missing-role-field'] = FixtureSpec(
        analyzer=_aroe.analyze_role_field,
        files={
            'plan-marshall/skills/phase-5-execute/standards/x.md': (
                '---\n'
                'name: default:quality_check\n'
                'description: Run quality-gate\n'
                'order: 10\n'
                '---\n\n# X\n'
            )
        },
    )
    corpus['finalize-step-token-mismatch'] = FixtureSpec(
        analyzer=lambda root: _afst.scan_finalize_step_token(root / 'marketplace' / 'bundles'),
        files={
            'marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py': (
                "OPTIONAL_BUNDLE_FINALIZE_STEPS = ['plan-marshall:plan-retrospective']\n"
            ),
            'marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md': (
                '# F\n\n```bash\n'
                'python3 .plan/execute-script.py '
                'plan-marshall:manage-status:manage-status mark-step-done \\\n'
                '  --plan-id PLAN_ID --phase 6-finalize --step plan-retrospective\n'
                '```\n'
            ),
        },
    )
    # step-configurable-contract: a built-in phase-6-finalize body doc whose
    # ``configurable:`` block is present but malformed (an entry missing its
    # required ``description`` sub-field) fires. The scratch tree carries the
    # real contract parser so the analyzer's dynamic import resolves; the
    # scratch root IS the bundles root the scanner walks.
    corpus['step-configurable-contract'] = FixtureSpec(
        analyzer=_ascc.scan_step_configurable_contract,
        files={
            'plan-marshall/skills/extension-api/scripts/configurable_contract.py': (
                _CONFIGURABLE_CONTRACT_SRC
            ),
            'plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md': (
                '---\n'
                'name: sonar-roundtrip\n'
                'order: 80\n'
                'configurable:\n'
                '  - key: touched_file_cleanup\n'
                '    default: new_code_only\n'  # missing required description
                '---\n\n# Sonar Roundtrip\n'
            ),
        },
    )
    # The Bash: directive must be a body line OUTSIDE any fence (fenced lines
    # are command substitutions, not tool directives) and must start at line
    # start so _TOOL_DIRECTIVE_RE matches.
    corpus['allowed-tools-body-drift'] = FixtureSpec(
        analyzer=_aatd.analyze_allowed_tools_drift,
        files={
            _PM_SKILL: (
                '---\n'
                'name: f\n'
                'description: d\n'
                'allowed-tools: Read\n'
                '---\n\n'
                '# F\n\n'
                'Bash: run the command here\n'
            )
        },
    )

    # --- Reference-resolution cluster (plugin.json / Skill: / recipe) -------

    corpus['declared-component-vs-disk'] = FixtureSpec(
        analyzer=_advd.analyze_declared_vs_disk,
        files={
            'b/.claude-plugin/plugin.json': (
                '{"name": "b", "skills": ["./skills/ghost-skill"]}\n'
            ),
        },
    )
    # An Extension subclass with no real overrides, paired with a SKILL.md whose
    # Extension API table lists ``provides_triage()`` — a phantom mirror row.
    corpus['provides-method-table-drift'] = FixtureSpec(
        analyzer=_apmt.analyze_provides_method_table,
        files={
            'b/skills/plan-marshall-plugin/extension.py': (
                'from plan_marshall.script_shared import ExtensionBase\n'
                '\n\n'
                'class Extension(ExtensionBase):\n'
                '    pass\n'
            ),
            'b/skills/plan-marshall-plugin/SKILL.md': (
                '# plan-marshall-plugin\n\n'
                '## Extension API\n\n'
                '| Hook | Description |\n'
                '|------|-------------|\n'
                '| `provides_triage()` | Triage skill reference |\n'
            ),
        },
    )
    # An extension-api SKILL.md whose Extension Points table claims 1
    # implementation of ``provides_triage()`` while no bundle extension.py
    # overrides it — a stale count mirror (stated 1, actual 0).
    corpus['literal-count-drift'] = FixtureSpec(
        analyzer=_alc.analyze_literal_count,
        files={
            'plan-marshall/skills/extension-api/SKILL.md': (
                '# Extension API\n\n'
                '## Extension Points\n\n'
                '| Extension Point | Hook Method | Contract | Implementations |\n'
                '|-----------------|-------------|----------|-----------------|\n'
                '| Triage | `provides_triage()` | [doc](standards/x.md) | 1 |\n'
            ),
        },
    )
    # A component SKILL.md carrying a relative link to a file that does not
    # exist under the scratch tree — a broken-relative-link.
    corpus['broken-relative-link'] = FixtureSpec(
        analyzer=_da.analyze_markdown_mirror_rules,
        files={
            'b/skills/fixture-skill/SKILL.md': (
                '# Fixture\n\nSee [the standard](standards/missing.md) for details.\n'
            ),
        },
    )
    # A component SKILL.md whose fenced block opens without a language
    # info-string — a fenced-code-no-language defect.
    corpus['fenced-code-no-language'] = FixtureSpec(
        analyzer=_da.analyze_markdown_mirror_rules,
        files={
            'b/skills/fixture-skill/SKILL.md': '# Fixture\n\n```\nbare code block\n```\n',
        },
    )
    corpus['plugin-json-orphan-component'] = FixtureSpec(
        analyzer=_apj.analyze_plugin_json_orphans,
        files={
            'b/.claude-plugin/plugin.json': '{"name": "b", "agents": []}\n',
            'b/agents/ghost-agent.md': '---\nname: ghost\n---\n\n# Ghost\n',
        },
    )
    corpus['skill-notation-unresolved'] = FixtureSpec(
        analyzer=_asn.analyze_skill_notation,
        files={
            'b/.claude-plugin/plugin.json': '{"name": "b"}\n',
            'b/skills/real-skill/SKILL.md': (
                '# F\n\nLoad it:\n\n```\nSkill: b:ghost-skill\n```\n'
            ),
        },
    )
    corpus['recipe-missing-implements'] = FixtureSpec(
        analyzer=_afm.analyze_frontmatter,
        files={
            'b/skills/recipe-fixture/SKILL.md': (
                '---\nname: recipe-fixture\ndescription: A recipe\n---\n\n# Recipe\n'
            ),
        },
    )
    corpus['resolver-matrix-coverage'] = FixtureSpec(
        analyzer=_armc.analyze_resolver_matrix_coverage,
        files={
            'b/skills/s/scripts/_resolver.py': (
                'def resolve(a, b, c):\n'
                '    if a:\n'
                '        return 1\n'
                '    if b:\n'
                '        return 2\n'
                '    if c:\n'
                '        return 3\n'
                '    return 0\n'
            ),
        },
    )

    # --- SIMPLICITY_* cluster (scan_simplicity expects a marketplace/ root) --
    # One script triggering all five detectors. scan_simplicity globs
    # ``{root}/bundles/*/skills/*/scripts/**/*.py``.
    _simplicity_script = (
        'import os  # backward compat\n'
        '\n'
        '\n'
        'def discard(x):\n'
        '    del x\n'
        '    return 1\n'
        '\n'
        '\n'
        'def swallow():\n'
        '    try:\n'
        '        risky()\n'
        '    except Exception:  # defensive only\n'
        '        return None\n'
        '    return 0\n'
        '\n'
        '\n'
        'def passthrough(a, b):\n'
        '    return helper(a, b)\n'
        '\n'
        '\n'
        'def documented(a, b):\n'
        '    """Args:\n'
        '\n'
        '    Returns:\n'
        '    """\n'
        '    return a + b\n'
    )
    _simplicity_files = {'bundles/b/skills/s/scripts/_simp.py': _simplicity_script}
    for _rule in (
        'SIMPLICITY_UNUSED_PARAMETER',
        'SIMPLICITY_BACKWARD_COMPAT_REEXPORT',
        'SIMPLICITY_DEFENSIVE_CATCHALL',
        'SIMPLICITY_THIN_WRAPPER',
        'SIMPLICITY_SIGNATURE_DOCSTRING',
    ):
        corpus[_rule] = FixtureSpec(
            analyzer=_asimp.scan_simplicity,
            files=_simplicity_files,
        )

    # --- Production-script literal scanners (marketplace/ root with bundles/)-

    corpus['executor-path-in-production'] = FixtureSpec(
        analyzer=_aepp.analyze_executor_path_in_production,
        files={
            'bundles/b/skills/s/scripts/x.py': (
                "RUNNER = '.plan/execute-script.py'\n"
            ),
        },
    )
    corpus['plan-path-in-scripts'] = FixtureSpec(
        analyzer=_apps.analyze_plan_path_in_scripts,
        files={
            'bundles/b/skills/s/scripts/y.py': (
                "PLAN_DIR = '.plan/plans/' + 'x'\n"
            ),
        },
    )
    corpus['fail-closed-gate-read'] = FixtureSpec(
        analyzer=_afcgr.analyze_fail_closed_gate_reads,
        files={
            'bundles/b/skills/s/scripts/gate.py': (
                'from pathlib import Path\n'
                '\n'
                'def cmd_check(args):\n'
                '    p = Path(args.path)\n'
                '    if p.exists():\n'
                '        content = p.read_text(encoding="utf-8")\n'
                '    return content\n'
            ),
        },
    )
    corpus['redundant-contract-typed-isinstance'] = FixtureSpec(
        analyzer=_afcgr.analyze_fail_closed_gate_reads,
        files={
            'bundles/b/skills/s/scripts/guard.py': (
                'def merge(metadata: dict) -> dict:\n'
                '    if isinstance(metadata, dict):\n'
                '        return metadata\n'
                '    return {}\n'
            ),
        },
    )

    # --- Per-file AST analyzers (take a single script_path) -----------------

    corpus['cmd-root-anchoring-missing'] = FixtureSpec(
        analyzer=lambda root: _acra.analyze_cmd_root_anchoring(root / 'd.py'),
        files={
            'd.py': (
                'import argparse\n'
                'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
                'subparsers = parser.add_subparsers()\n'
                "p_run = subparsers.add_parser('run', allow_abbrev=False)\n"
                "p_run.add_argument('--name')\n"
                'p_run.set_defaults(func=cmd_run)\n'
                '\n'
                'def cmd_run(args):\n'
                '    return 0\n'
            ),
        },
    )
    corpus['orphan-argparse-flag'] = FixtureSpec(
        analyzer=lambda root: _aoaf.analyze_orphan_argparse_flags(root / 'd.py'),
        files={
            'd.py': (
                'import argparse\n'
                'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
                'subparsers = parser.add_subparsers()\n'
                "p_run = subparsers.add_parser('run', allow_abbrev=False)\n"
                "p_run.add_argument('--verbose', action='store_true')\n"
                'p_run.set_defaults(func=cmd_run)\n'
                '\n'
                'def cmd_run(args):\n'
                '    print("running")\n'
            ),
        },
    )

    # --- Per-skill-dir markdown scanners ------------------------------------

    corpus['shell-active-tokens'] = FixtureSpec(
        analyzer=lambda root: _asat.analyze_shell_active_tokens(root / 's'),
        files={
            's/standards/x.md': (
                '# F\n\nRun: `--detail "value `tok` end"`\n'
            ),
        },
    )
    corpus['resolution-branch-side-effect-undocumented'] = FixtureSpec(
        analyzer=lambda root: _arbm.analyze_resolution_branch_markers(root / 's'),
        files={
            's/standards/x.md': (
                '# F\n\n## Resolution\n\n### Hold\n\n'
                'The user keeps both surfaces and continues.\n'
            ),
        },
    )

    # --- Marketplace-wide metadata-field scanner (marketplace/ root) --------

    corpus['metadata-field-undefined'] = FixtureSpec(
        analyzer=_amfv.analyze_metadata_field_validity,
        files={
            'bundles/b/skills/s/SKILL.md': (
                '# F\n\nThe metadata write stores `bogus_undefined_field` here.\n'
            ),
        },
    )

    # --- phase-2-refine contract (paths list, self-filters to phase-2-refine)-

    corpus['refine-contract-violation'] = FixtureSpec(
        analyzer=lambda root: _ap2r.analyze_phase2_refine_contract([root]),
        files={
            'phase-2-refine/workflow/x.md': (
                '# F\n\nWrite("marketplace/bundles/foo/SKILL.md")\n'
            ),
        },
    )

    # --- Test-conventions rules (operate on a test/ tree) -------------------

    corpus['unique-fixture-basenames'] = FixtureSpec(
        analyzer=lambda root: _atc.analyze_unique_fixture_basenames(root / 'test'),
        files={'test/plan-marshall/foo/_fixtures.py': '# generic basename\n'},
    )
    corpus['subprocess-pythonpath'] = FixtureSpec(
        analyzer=lambda root: _atc.analyze_subprocess_pythonpath(root / 'test'),
        files={
            'test/foo/test_thing.py': (
                'import subprocess\n'
                'import sys\n'
                '\n'
                'def test_runs():\n'
                "    subprocess.run([sys.executable, '-c', 'print(1)'], check=True)\n"
            ),
        },
    )
    # identifier-validator-corpus fires deterministically via the error path: a
    # registry entry whose validator_path does not exist emits a
    # validator_not_found finding (no subprocess / list_command needed).
    corpus['identifier-validator-corpus'] = FixtureSpec(
        analyzer=lambda root: _atc.analyze_validator_regex_vs_corpus(
            [
                {
                    'validator_path': 'does-not-exist.py',
                    'regex_constant': 'PATTERN',
                    'list_command': 'true',
                }
            ],
            project_root=root,
        ),
        files={},
    )

    # --- Component cluster (analyze_component over a crafted component) ------
    # Agent-frontmatter / agent-rule fixtures.

    corpus['missing-frontmatter'] = FixtureSpec(
        component=lambda root: _agent_component(root, 'a', '# No frontmatter\n')
    )
    corpus['invalid-yaml'] = FixtureSpec(
        component=lambda root: _agent_component(
            root, 'a', '---\nnot valid yaml here no colon\n---\n\n# A\n'
        )
    )
    corpus['missing-name-field'] = FixtureSpec(
        component=lambda root: _agent_component(
            root, 'a', '---\ndescription: d\ntools: Read\n---\n\n# A\n'
        )
    )
    corpus['missing-description-field'] = FixtureSpec(
        component=lambda root: _agent_component(
            root, 'a', '---\nname: a\ntools: Read\n---\n\n# A\n'
        )
    )
    corpus['missing-tools-field'] = FixtureSpec(
        component=lambda root: _agent_component(
            root, 'a', '---\nname: a\ndescription: d\n---\n\n# A\n'
        )
    )
    corpus['agent-task-tool-prohibited'] = FixtureSpec(
        component=lambda root: _agent_component(
            root, 'a', '---\nname: a\ndescription: d\ntools: Read, Task\n---\n\n# A\n'
        )
    )
    corpus['agent-skill-tool-visibility'] = FixtureSpec(
        component=lambda root: _agent_component(
            root, 'a', '---\nname: a\ndescription: d\ntools: Read, Edit\n---\n\n# A\n'
        )
    )
    corpus['agent-maven-restricted'] = FixtureSpec(
        component=lambda root: _agent_component(
            root,
            'a',
            '---\nname: a\ndescription: d\ntools: Read, Skill\n---\n\n'
            '# A\n\n```\nBash: mvn clean install\n```\n',
        )
    )
    corpus['workflow-hardcoded-script-path'] = FixtureSpec(
        component=lambda root: _agent_component(
            root,
            'a',
            '---\nname: a\ndescription: d\ntools: Read, Skill\n---\n\n'
            '# A\n\nRun: python3 marketplace/bundles/x/scripts/foo.py\n',
        )
    )
    corpus['agent-glob-resolver-workaround'] = FixtureSpec(
        component=lambda root: _agent_component(
            root,
            'a',
            '---\nname: a\ndescription: d\ntools: Read, Glob, Skill\n---\n\n# A\n',
        )
    )
    corpus['agent-lessons-via-skill'] = FixtureSpec(
        component=lambda root: _agent_component(
            root,
            'a',
            '---\nname: a\ndescription: d\ntools: Read, Skill\n---\n\n'
            '# A\n\nCONTINUOUS IMPROVEMENT RULE: run /plugin-update-agent.\n',
        )
    )
    corpus['backup-pattern'] = FixtureSpec(
        component=lambda root: _agent_component(
            root,
            'a',
            '---\nname: a\ndescription: d\ntools: Read, Skill\n---\n\n'
            '# A\n\nKeep a `config.py.bak` backup copy.\n',
        )
    )

    # Skill-cluster fixtures.

    corpus['skill-naming-noun-suffix'] = FixtureSpec(
        component=lambda root: _skill_component(
            root, 'fixture-runner', _GOOD_SKILL_FM + '\n# Fixture\n'
        )
    )
    corpus['missing-user-invocable'] = FixtureSpec(
        component=lambda root: _skill_component(
            root, 's', '---\nname: s\ndescription: d\n---\n\n# S\n'
        )
    )
    corpus['misspelled-user-invocable'] = FixtureSpec(
        component=lambda root: _skill_component(
            root, 's', '---\nname: s\ndescription: d\nuser-invokable: false\n---\n\n# S\n'
        )
    )
    corpus['skill-invokable-mismatch'] = FixtureSpec(
        component=lambda root: _skill_component(
            root,
            's',
            '---\nname: s\ndescription: d\nuser-invocable: true\n---\n\n'
            '# S\n\n**REFERENCE MODE**: reference content.\n',
        )
    )
    corpus['file-bloat'] = FixtureSpec(
        component=lambda root: _skill_component(
            root, 's', _GOOD_SKILL_FM + '\n# S\n' + ('\nline\n' * 1300)
        )
    )
    corpus['checklist-pattern'] = FixtureSpec(
        component=lambda root: _skill_component(
            root, 's', _GOOD_SKILL_FM + '\n# S\n\n## Tasks\n\n- [ ] do a thing\n'
        )
    )

    # Subdoc-cluster fixtures — a skill whose subdoc trips each subdoc rule.

    corpus['subdoc-bloat'] = FixtureSpec(
        component=lambda root: _skill_with_subdoc(
            root, 's', 'standards/big.md', '# Big\n' + ('\nline\n' * 850)
        )
    )
    corpus['subdoc-forbidden-metadata'] = FixtureSpec(
        component=lambda root: _skill_with_subdoc(
            root, 's', 'standards/x.md', '# X\n\n## Version History\n\nv1.\n'
        )
    )
    corpus['subdoc-hardcoded-script-path'] = FixtureSpec(
        component=lambda root: _skill_with_subdoc(
            root,
            's',
            'standards/x.md',
            '# X\n\nRun: python3 marketplace/bundles/x/scripts/foo.py\n',
        )
    )
    corpus['subdoc-checklist-pattern'] = FixtureSpec(
        component=lambda root: _skill_with_subdoc(
            root, 's', 'standards/x.md', '# X\n\n## Steps\n\n- [ ] do a thing\n'
        )
    )
    corpus['skill-resolver-gap'] = FixtureSpec(
        component=lambda root: _skill_with_subdoc(
            root,
            's',
            'standards/x.md',
            '# X\n\nUse Glob: `**/*.md` to discover files.\n\nThen process them.\n',
        )
    )
    corpus['workflow-prose-parameter-inconsistency'] = FixtureSpec(
        component=lambda root: _skill_component(
            root,
            's',
            _GOOD_SKILL_FM
            + '\n# S\n\n## Step\n\n```bash\n'
            + 'python3 .plan/execute-script.py '
            + 'plan-marshall:manage-plan-documents:manage-plan-documents '
            + 'read --section context\n```\n\n'
            + 'If absent, fall back to the body section.\n',
        )
    )

    # --- Pure-static markdown / AST analyzers not run via analyze_component --

    corpus['manage-findings-invocation-invalid'] = FixtureSpec(
        analyzer=lambda _root: _amfi.analyze_manage_findings_invocation(
            'python3 .plan/execute-script.py '
            'plan-marshall:manage-findings:manage_findings list --plan-id p\n',
            'x.md',
        ),
        files={},
    )
    corpus['prose-verb-chain-consistency'] = FixtureSpec(
        analyzer=lambda root: _avc.analyze_verb_chains(
            root / 'marketplace' / 'bundles' / 'b' / 'skills' / 's'
        ),
        files={
            'marketplace/bundles/b/skills/s/scripts/x.py': (
                'import argparse\n'
                'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
                'subparsers = parser.add_subparsers()\n'
                "p_run = subparsers.add_parser('run', allow_abbrev=False)\n"
            ),
            'marketplace/bundles/b/skills/s/SKILL.md': (
                '# F\n\n```bash\n'
                'python3 .plan/execute-script.py b:s:x bogusverb --flag\n'
                '```\n'
            ),
        },
    )
    corpus['notation-staleness'] = FixtureSpec(
        analyzer=lambda root: _ans.analyze_notation_staleness(
            [root / 'marketplace' / 'bundles' / 'b' / 'skills' / 's']
        ),
        files={
            'marketplace/bundles/b/.claude-plugin/plugin.json': '{"name": "b"}\n',
            'marketplace/bundles/b/skills/s/scripts/real.py': '# real script\n',
            'marketplace/bundles/b/skills/s/SKILL.md': (
                '# F\n\n```bash\n'
                'python3 .plan/execute-script.py b:s:ghost-script run\n'
                '```\n'
            ),
        },
    )

    # bash-fence-inline-code-exemption: a script defining BOTH the bash-fence
    # marker and an inline-code exemption helper (reintroduction guard).
    corpus['bash-fence-inline-code-exemption'] = FixtureSpec(
        analyzer=_abfic.analyze_bash_fence_inline_code_exemption,
        files={
            'bundles/b/skills/s/scripts/_bad.py': (
                "_BASH_FENCE_INFO_STRINGS = ('bash', 'sh')\n"
                "_INLINE_CODE_RE = None  # inline-code exemption (must not co-exist)\n"
            ),
        },
    )

    # ARGUMENT_NAMING_* cluster — each sub-rule is pure-static and is fired by
    # calling its sub-function directly with a constructed registry / index,
    # avoiding the load_registered_notations executor dependency.
    _ScriptEntry = _aan._ScriptEntry
    corpus['ARGUMENT_NAMING_NOTATION_INVALID'] = FixtureSpec(
        analyzer=lambda root: _aan.scan_notation(
            root, {'b:s:registered'}
        ),
        files={
            'bundles/b/skills/s/SKILL.md': (
                '# F\n\n```bash\n'
                'python3 .plan/execute-script.py b:s:unregistered-script run\n'
                '```\n'
            ),
        },
    )
    corpus['ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN'] = FixtureSpec(
        analyzer=lambda root: _aan.scan_subcommand(
            root, {'b:s:x': _ScriptEntry(subcommands={'run': set()}, root_flags=set())}
        ),
        files={
            'bundles/b/skills/s/SKILL.md': (
                '# F\n\n```bash\n'
                'python3 .plan/execute-script.py b:s:x bogusverb\n'
                '```\n'
            ),
        },
    )
    corpus['ARGUMENT_NAMING_FLAG_UNKNOWN'] = FixtureSpec(
        analyzer=lambda root: _aan.scan_flag(
            root, {'b:s:x': _ScriptEntry(subcommands={}, root_flags={'name'})}
        ),
        files={
            'bundles/b/skills/s/SKILL.md': (
                '# F\n\n```bash\n'
                'python3 .plan/execute-script.py b:s:x --bogus-flag value\n'
                '```\n'
            ),
        },
    )
    corpus['ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT'] = FixtureSpec(
        analyzer=lambda root: _aan.scan_canonical_forms(root, {}),
        files={
            'bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md': (
                '## Canonical Forms\n\n'
                '| Script | Operation | Canonical form |\n'
                '| --- | --- | --- |\n'
                '| `ghost` | read | `ghost-unresolvable read --plan-id {id}` |\n'
            ),
        },
    )

    return corpus


# ---------------------------------------------------------------------------
# Fired-rule-ID derivation
# ---------------------------------------------------------------------------

# Extra rule IDs recorded by tests that cannot be driven by a static analyzer
# fixture (e.g. the cross-file verifier-echo test in test_analyze_crossfile.py
# feeds its emitted finding types here). Tests call ``record_fired(...)`` to
# populate this; ``fired_rule_ids`` unions it in.
_EXTRA_FIRED: set[str] = set()


def record_fired(findings_or_ids) -> None:
    """Record rule IDs that fired in a test that the static corpus cannot drive.

    Accepts either an iterable of finding dicts (rule IDs extracted from
    ``type``/``rule_id``) or an iterable of rule-ID strings.
    """
    for item in findings_or_ids:
        if isinstance(item, dict):
            for key in ('rule_id', 'type'):
                value = item.get(key)
                if isinstance(value, str):
                    _EXTRA_FIRED.add(value)
        elif isinstance(item, str):
            _EXTRA_FIRED.add(item)


def crossfile_verified_findings() -> list[dict]:
    """Return verified cross-file findings carrying the duplication / extraction /
    terminology rule types.

    The static ``analyze_cross_file`` analyzer emits only raw analysis
    structures; the ``type: duplication/extraction/terminology`` FINDINGS are
    emitted solely by ``verify_findings`` on a VERIFIED LLM claim. This builder
    crafts an ``analysis`` dict plus a matching ``llm_findings`` dict so each
    rule type lands in ``verified``. Both the suite-coverage meta-test (via
    ``fired_rule_ids``) and ``test_analyze_crossfile.py`` (the verifier-echo
    test) consume this single builder so the firing inputs are authored once.
    """
    analysis = {
        'skill_path': '/fake/skill',
        'content_blocks': [
            {'file': 'a.md', 'section': 'Intro', 'lines': '1-10'},
            {'file': 'b.md', 'section': 'Intro', 'lines': '1-10'},
            {'file': 'c.md', 'section': 'Setup', 'lines': '1-20'},
        ],
        # An exact duplicate pair so a true_duplicate claim confirms.
        'exact_duplicates': [
            {
                'hash': 'abc',
                'occurrences': [
                    {'file': 'a.md', 'section': 'Intro', 'lines': '1-10'},
                    {'file': 'b.md', 'section': 'Intro', 'lines': '1-10'},
                ],
            }
        ],
        'similarity_candidates': [],
        # An extraction candidate so an extraction claim confirms (same type).
        'extraction_candidates': [
            {
                'type': 'template',
                'pattern': 'placeholder_structure',
                'file': 'c.md',
                'section': 'Setup',
                'lines': '1-20',
            }
        ],
        # A terminology variant so a standardize claim confirms.
        'terminology_variants': [
            {
                'concept': 'workflow',
                'variants': [
                    {'term': 'workflow', 'files': ['a.md'], 'count': 3},
                    {'term': 'process', 'files': ['b.md'], 'count': 1},
                ],
                'recommendation': "standardize on 'workflow'",
            }
        ],
    }
    llm_findings = {
        'duplications': [
            {
                'source': {'file': 'a.md', 'section': 'Intro'},
                'target': {'file': 'b.md', 'section': 'Intro'},
                'classification': 'true_duplicate',
            }
        ],
        'extractions': [
            {
                'file': 'c.md',
                'section': 'Setup',
                'type': 'template',
                'recommendation': 'extract_to_templates',
            }
        ],
        'terminology': [
            {
                'concept': 'workflow',
                'standardized_term': 'workflow',
                'action': 'standardize',
            }
        ],
    }
    result = verify_findings(analysis, llm_findings)
    return list(result.get('verified', []))


def _run_spec(spec: FixtureSpec) -> set[str]:
    """Materialize one spec under a scratch tree and return its fired rule IDs."""
    with tempfile.TemporaryDirectory(prefix='zm_fixture_') as tmp:
        scratch_root = Path(tmp)
        _materialize(scratch_root, spec.files)
        if spec.analyzer is not None:
            findings = spec.analyzer(scratch_root)
        else:
            component = spec.component(scratch_root)
            result = analyze_component(component)
            findings = result.get('issues', [])
    return _finding_rule_ids(findings)


def fired_rule_ids() -> set[str]:
    """Return the union of every rule ID the fixture corpus fires.

    Each spec is materialized under its own scratch tree (so one fixture's
    defect never leaks into another analyzer's scan), the spec's analyzer or
    component path is run, and the union of fired rule IDs is returned. The
    ``_EXTRA_FIRED`` registry (populated by ``record_fired`` from tests that
    cannot be driven by a static fixture) is unioned in.
    """
    fired: set[str] = set(_EXTRA_FIRED)
    for spec in build_fixture_corpus().values():
        fired |= _run_spec(spec)
    # Cross-file rules (duplication / extraction / terminology) are emitted only
    # by verify_findings on a verified LLM claim — derived here from the shared
    # crafted-claim builder so the meta-test never depends on test ordering.
    fired |= _finding_rule_ids(crossfile_verified_findings())
    return fired
