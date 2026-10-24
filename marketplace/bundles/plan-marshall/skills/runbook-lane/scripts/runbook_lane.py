#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic resolver for the runbook lane.

The runbook lane implements one staged orchestrator plan spec without the
``/plan-marshall`` lifecycle. Every value that used to be spelled into the lane's
contract by hand — the epic slug, the derived names, the build commands, the
required and optional reviewers with their trigger comments, the commit trailer
and the inbox command — is resolved here from the project's OWN configuration,
so the lane contract itself carries no project-specific literal.

Verb surface::

    runbook_lane resolve --spec PATH [--project-dir DIR] [--spec-from-ledger]
    runbook_lane executor-skew [--executor PATH] [--lane-dir DIR]
    runbook_lane build-routing --worktree PATH
    runbook_lane build-classify --paths P1,P2 [--project-dir DIR]
    runbook_lane sonar-gate --state STATE [--count-status STATUS] [--open-count N]
                             [--open-keys K1,K2] [--dismissed-keys K1,K2]
    runbook_lane sonar-facts --state STATE [--count-status STATUS] [--open-count N] [--rules R1,R2]

``--spec`` must name a staged spec, i.e. a file below
``.plan/orchestrator/{slug}/plans/``. Anything else is refused: the lane exists
to run a staged orchestrator plan, and a path outside that tree names something
else. ``--project-dir`` defaults to the current directory and anchors every
project-scoped read (marshal.json, the project architecture, the guard marker).

``--spec-from-ledger`` reads that same logical spec from the shared ledger
worktree first — ``{epic_dir}/plans/{spec name}``, where ``epic_dir`` follows the
store seam the orchestrator publishes — and falls back to the main checkout's copy
when the worktree holds none. The flag is set per emit, so a round of emits needs
no ledger land; with ``orchestrator.use_worktree`` off there is no second copy and
the flag is a no-op rather than an error. ``resolve`` always reports which copy it
read (``spec_source``: ``ledger_worktree`` | ``main_checkout``) and, when both
copies exist and differ, ``spec_differ: true`` — the marker a silent read of the
older copy would leave out.

**Fail closed.** An empty ``required_bots`` list, a missing automatic-review
step, an unreadable ``marshal.json``, an unreadable Sonar block
(``sonar_config_unreadable``) or one carrying no project key
(``sonar_config_incomplete``), and an unresolvable build command are all
errors carrying a specific code. There is never a fall-back to a default
reviewer list or a default build: a lane that
quietly reviews with nobody, or builds with the wrong tool, would report a green
run over work nobody checked.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orchestrator_worktree
from file_ops import output_toon, output_toon_error
from marketplace_paths import PLAN_DIR_NAME

#: The step whose ``required_bots`` / ``optional_bots`` the lane drives.
_REVIEW_STEP_ID = 'plan-marshall:automatic-review'

#: The provider block whose presence makes the project a Sonar project. The
#: non-secret ``credentials_config`` key is canonicalized to the prefix-stripped
#: form (``manage-providers``), so the bundle-prefixed spelling is accepted as a
#: fallback read.
_SONAR_CONFIG_KEY = 'workflow-integration-sonar'

#: The two states the lane resolves for Sonar, and the three the read can answer
#: with. ``unconfigured`` is a READ answer (the credential is missing at read
#: time), never a resolve state: a project that carries a project key but cannot
#: authenticate must block, not silently skip a check resolve said it needed.
_SONAR_STATES = ('configured', 'not_configured')
_SONAR_COUNT_STATUSES = ('confirmed', 'undecidable', 'unconfigured')

#: The landing's optional Sonar facts, on the per-step typed-fact channel the
#: lifecycle's ``sonar-roundtrip`` step already uses, so one measurement rides one
#: channel.
_SONAR_FACT_STEP = 'sonar-roundtrip'

#: The provider's own CE-readiness default, used when the active target imposes no
#: Bash ceiling (the seam answers ``no-op``).
_SONAR_CE_DEFAULT_SECONDS = 600

#: Margin kept below the harness's Bash ceiling. The plan-less read polls in-process
#: and returns its own typed ``undecidable`` when the budget expires; a budget at or
#: above the ceiling would have the harness kill the call first, leaving the lane a
#: tool timeout instead of a state it can classify.
_SONAR_CE_CEILING_MARGIN_SECONDS = 60

#: The build canons the lane runs, each resolved on its own through the
#: architecture: no composed ``--command-args "<canonical>"`` form exists, because
#: the canonical name is only meaningful to a wrapper that maps canonical names
#: and Maven's wrapper takes complete Maven arguments.
#:
#: The GATE canonicals: ``quality-gate`` is required for all modules and
#: ``verify`` for every non-pom module (extension-api's canonical-commands
#: contract, § Required Commands), but each build system publishes them
#: CONDITIONALLY — npm emits ``quality-gate`` only for a ``lint``/``check``
#: script and ``verify`` only for a ``test`` script — so at least ONE must
#: resolve for the lane to have a gate at all, and both must be absent before
#: ``resolve`` fails closed.
_GATE_CANONICALS = ('quality-gate', 'verify')

#: The test-conditional canonicals: ``module-tests`` only when the module has
#: test sources, ``test-compile`` only on a build system with a separate
#: test-compile step (Maven, Gradle — pyproject and npm publish none). Their
#: absence is the project's answer, not a resolution failure: a lane that
#: required them could not run in a pyproject or npm project at all.
_TEST_CONDITIONAL_CANONICALS = ('module-tests', 'test-compile')

#: The order the in-process fallback runs the gate's parts in. Filtered to the
#: canonicals the project actually resolved, so the fallback never asks for a
#: part the project does not publish.
_SPLIT_FORM = ('quality-gate', 'test-compile', 'module-tests')


#: A staged spec, ANCHORED to the project root: ``.plan/orchestrator/{slug}/plans/PLAN-*.md``.
#: Matched with ``fullmatch`` against the project-relative path, so a same-shaped
#: file nested under another directory (an archive, a fixture tree) does not
#: satisfy it — the lane runs a spec at the root of the orchestrator tree, not any
#: file that happens to end the same way.
_SPEC_RE = re.compile(r'\.plan/orchestrator/(?P<slug>[^/]+)/plans/(?P<name>PLAN-[^/]+)\.md')

#: Harness identifiers whose tool-call guard the lane can observe on disk.
_GUARD_NONE_HARNESSES = frozenset({'antigravity'})

#: The OpenCode guard's marker file, relative to the project root.
_OPENCODE_GUARD = ('.opencode', 'plugin', 'guard.js')

#: The settings files a Claude install registers a pre-tool-use hook in, relative
#: to the project root. ``settings.local.json`` is the machine-local one, so a
#: hook installed there counts exactly as a shared one does.
_CLAUDE_SETTINGS_FILES = (('.claude', 'settings.json'), ('.claude', 'settings.local.json'))

#: The tool-call guard's audit log, relative to the project root. Returned by
#: ``resolve`` so the lane reads the log at a path it was told, rather than
#: guessing one.
_GUARD_LOG_PARTS = ('.plan', 'temp', 'guard.log')

#: The build timeout the lane falls back to when the project's architecture can
#: stamp none. Scaled on purpose to survive a full project verification.
_DEFAULT_BUILD_TIMEOUT_SECONDS = 1800

#: The base branch a project falls back to when it never configured one. A
#: fallback, not the lane's answer: the lane always uses the resolved value.
_DEFAULT_BASE_BRANCH = 'main'


def _plan_id_from_spec(spec: Path) -> str:
    """Derive the lane plan id from a spec's basename.

    ``PLAN-42-example-slug.md`` becomes ``42-example-slug``: the ``PLAN-``
    marker is dropped and the rest is lower-cased, which is the same id the
    orchestrator's row and the inbox sender share.
    """
    stem = spec.name
    if stem.endswith('.md'):
        stem = stem[:-3]
    if stem.startswith('PLAN-'):
        stem = stem[len('PLAN-') :]
    return stem.lower()


@dataclass(frozen=True)
class _SpecChoice:
    """The copy of a staged spec ``resolve`` will read, and what it must report."""

    path: Path
    slug: str
    plan_id: str
    source: str
    differs: bool


def _ledger_store_dir() -> Path | None:
    """The shared ledger worktree's ``.plan`` directory, or ``None`` when there is none.

    COMPUTED from the same store seam the orchestrator publishes
    (``orchestrator_worktree``: the ``orchestrator.use_worktree`` knob plus the
    main-anchored worktree path), so the lane reads the tree the orchestrator
    reports rather than a second copy of the rule.

    Deliberately NOT the store resolver's ``ensure_...`` form: the lane only ever
    READS the spec, so a read must never create the ledger worktree as a side
    effect. An unresolvable anchor (no git checkout and no override) answers
    ``None``, which leaves the main checkout's copy as the only one — the knob-off
    behaviour, in the one situation where there is provably no second copy.
    """
    try:
        if not orchestrator_worktree.orchestrator_use_worktree():
            return None
        return orchestrator_worktree.orchestrator_worktree_path() / PLAN_DIR_NAME
    except (RuntimeError, OSError):
        return None


def _staged_spec_shape(spec: Path, project_dir: Path, *, from_ledger: bool) -> tuple[str, str]:
    """Return ``(slug, file name)`` for a spec path, or refuse it.

    The file name carries its ``.md`` extension, because the caller rebuilds both
    copies' paths from it — the regex group that matches it deliberately stops
    before the extension.

    The project-relative path is matched as a WHOLE against :data:`_SPEC_RE`, so a
    same-shaped file nested elsewhere (an archive, a fixture tree) never
    qualifies. Under the ledger flag one further spelling is accepted: a path
    inside the ledger worktree's own store, which is exactly the form a caller
    reaches for when the worktree copy is the one it wants. Every other path is
    the ``spec_outside_orchestrator`` refusal.
    """
    try:
        relative = spec.resolve().relative_to(project_dir.resolve())
    except ValueError:
        relative = None
    if relative is not None:
        match = _SPEC_RE.fullmatch(relative.as_posix())
        if match is not None:
            return match.group('slug'), f'{match.group("name")}.md'
    if from_ledger:
        store = _ledger_store_dir()
        if store is not None:
            try:
                inside = spec.resolve().relative_to(store.resolve())
            except ValueError:
                inside = None
            if inside is not None:
                match = _SPEC_RE.fullmatch(f'{PLAN_DIR_NAME}/{inside.as_posix()}')
                if match is not None:
                    return match.group('slug'), f'{match.group("name")}.md'
    raise ValueError('spec_outside_orchestrator')


def _resolve_spec(spec_value: str, project_dir: Path, *, from_ledger: bool = False) -> _SpecChoice:
    """Validate ``--spec`` and select the copy of it to read.

    A RELATIVE spec is resolved against ``--project-dir``, not against the
    process's working directory: the flag names the project the whole resolution
    is about, so a caller that passes both must get the spec file it named.

    Without the flag this is the unchanged read — the main checkout's copy, and
    ``invalid_spec`` when it holds none. With it the ledger worktree's copy wins
    when it exists and the main checkout's is the fallback, so a spec that exists
    only in the worktree is readable. The choice is reported as ``source``, and
    ``differs`` says whether the copy NOT read would have answered differently.

    Raised as ``ValueError`` carrying the refusal code so the caller can emit a
    structured error rather than a traceback.
    """
    spec = Path(spec_value)
    if not spec.is_absolute():
        spec = project_dir / spec
    slug, name = _staged_spec_shape(spec, project_dir, from_ledger=from_ledger)

    main_copy = project_dir / '.plan' / 'orchestrator' / slug / 'plans' / name
    # The ledger copy is resolved on BOTH paths: the flag decides whether it is
    # READ, while the differ marker exists precisely to report a default read that
    # left the newer copy unread.
    ledger_copy: Path | None = None
    store = _ledger_store_dir()
    if store is not None:
        candidate = store / 'orchestrator' / slug / 'plans' / name
        if candidate.is_file():
            ledger_copy = candidate

    if from_ledger and ledger_copy is not None:
        chosen, source = ledger_copy, 'ledger_worktree'
    elif main_copy.is_file():
        chosen, source = main_copy, 'main_checkout'
    elif spec.is_file():
        # The caller named the ONLY copy. It survived the shape check above, so it
        # is either the main checkout's own file or, under the flag, the ledger
        # worktree's.
        chosen, source = spec.resolve(), ('ledger_worktree' if from_ledger else 'main_checkout')
    else:
        raise ValueError('invalid_spec')

    differs = ledger_copy is not None and main_copy.is_file() and ledger_copy.read_bytes() != main_copy.read_bytes()
    return _SpecChoice(chosen, slug, _plan_id_from_spec(chosen), source, differs)


def _read_marshal(project_dir: Path) -> dict[str, Any]:
    """Read ``.plan/marshal.json`` for the project under resolution."""
    path = project_dir / '.plan' / 'marshal.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        raise ValueError('marshal_unreadable') from None
    if not isinstance(data, dict):
        raise ValueError('marshal_unreadable')
    return data


def _split_csv(value: Any) -> list[str]:
    """Split a comma-separated list, dropping blanks, preserving declared order."""
    if not isinstance(value, str):
        return []
    return [part.strip() for part in value.split(',') if part.strip()]


#: The heading that opens a staged spec's deliverable list.
_DELIVERABLES_HEADING = '## Deliverables'

#: A numbered deliverable at column 0. Nested numbering is INDENTED, so the
#: sub-conditions a deliverable states are never mistaken for further
#: deliverables — a rule this parser depends on and a spec's own format supplies.
_DELIVERABLE_HEAD_RE = re.compile(r'^(?P<number>\d+)\.\s+(?P<title>.+?)\s*$')

#: The two per-deliverable declarations. Both are OPTIONAL: a spec staged before
#: they existed carries neither, and the lane then falls back to the persona
#: table's per-kind defaults with no domain skills.
_SKILLS_DECL_RE = re.compile(r'^(?:\s*[-*]\s*)?Skills:\s*(?P<value>.+?)\s*$')
_PERSONA_DECL_RE = re.compile(r'^(?:\s*[-*]\s*)?Persona:\s*(?P<value>.+?)\s*$')


def _lane_skill_dir() -> Path:
    """The lane's own skill directory, ``{root}/{bundle}-{skill}`` or ``{bundle}/skills/{skill}``."""
    return Path(__file__).resolve().parents[1]


def _lane_skills_root() -> Path:
    """The ``skills/`` directory the lane itself ships in."""
    return Path(__file__).resolve().parents[2]


def _lane_bundle() -> str | None:
    """The bundle the lane ships in, used to resolve a bare skill name.

    In the source tree and the nested plugin cache the bundle is the lane's
    grandparent directory name. In a flat deployment the lane's own directory is
    the dash-joined ``{bundle}-{skill}``, which no separator position can split
    back into the pair, so the bundle is read from the identity the flat emitters
    record in the lane's ``SKILL.md``
    (:func:`deployed_layout.read_flat_skill_identity`).

    Returns ``None`` for a FLAT deployment whose ``SKILL.md`` records no
    identity: the directory name cannot attribute it to a bundle, so every bare
    name would silently miss. The caller turns that — for a spec that names a
    bare skill or persona, and only then — into a named refusal instead of
    probing a bundle that does not exist; a fully qualified name carries its own
    bundle and needs this one not at all.
    """
    from deployed_layout import is_flat_root, read_flat_skill_identity
    from marketplace_bundles import extract_bundle_name

    identity = read_flat_skill_identity(_lane_skill_dir())
    if identity is not None:
        return identity[0]
    if is_flat_root(_lane_skills_root()):
        return None
    return extract_bundle_name(_lane_skill_dir().parents[1])


def _skill_probe_paths(notation: str, lane_bundle: str) -> list[Path]:
    """Return every path the lane probes for *notation*, in probe order.

    A bare name is qualified with ``lane_bundle`` first, so the lane's own skills
    resolve beside it without the caller spelling a bundle. ONE enumeration feeds
    both the existence answer and the "every probed path" error: the flat
    ``{bundle}-{skill}`` candidates come from the same vocabulary
    :func:`deployed_layout.resolve_skill_path` uses internally
    (:func:`deployed_layout.skill_roots` plus
    :func:`deployed_layout.flat_skill_dir_name`), and the nested bundle tree —
    every version dir in it — through :func:`marketplace_bundles.resolve_bundle_path`.
    A second, redundant ``resolve_skill_path`` call beside this enumeration is
    what used to make the two disagree.
    """
    from deployed_layout import flat_skill_dir_name, skill_roots

    bundle, separator, skill = notation.partition(':')
    if not separator:
        bundle, skill = lane_bundle, notation
    subpath = f'skills/{skill}/SKILL.md'

    candidates: list[Path] = [
        root / flat_skill_dir_name(bundle, skill) / 'SKILL.md' for root in skill_roots(_lane_skills_root())
    ]
    try:
        from marketplace_bundles import resolve_bundle_path, resolve_bundles_root, select_live_version_dir

        bundles_root: Path | None = resolve_bundles_root(Path(__file__))
    except Exception:
        bundles_root = None
    if bundles_root is not None:
        # A VERSIONED bundle cache has one live version dir, and that is the
        # path a probe actually reads. Naming the unversioned
        # ``{bundle}/{subpath}`` fallback for such a cache reports a path that
        # cannot exist on that machine, hiding which version was probed.
        bundle_dir = bundles_root / bundle
        live_version: Path | None = None
        if bundle_dir.is_dir():
            live_version = select_live_version_dir(
                bundle_dir, lambda version_dir: (version_dir / '.claude-plugin' / 'plugin.json').is_file()
            )
        nested = (
            live_version / subpath if live_version is not None else resolve_bundle_path(bundles_root, bundle, subpath)
        )
        if nested not in candidates:
            candidates.append(nested)
    return candidates


def _skill_exists(notation: str, lane_bundle: str) -> bool:
    """Whether *notation* names a skill installed in any deployed layout.

    True when any :func:`_skill_probe_paths` candidate exists: the lane's own
    ``skills/`` root in either shape, or the nested bundle tree a cross-bundle
    name resolves through.
    """
    return any(path.is_file() for path in _skill_probe_paths(notation, lane_bundle))


_EXECUTOR_SKEW_MATCH = 'match'
_EXECUTOR_SKEW_SKEW = 'skew'
_EXECUTOR_SKEW_UNCHECKED = 'could_not_check'


def _lane_text_version(skill_dir: Path | None = None) -> str | None:
    """Return the version of the lane text a harness would load, or ``None``.

    The version is read from the LIVE installed bundle, never from the executing
    script's own path: a stale executor runs an older ``runbook_lane.py`` from
    its embedded path, so reading ``__file__``'s version would compare that stale
    version with itself and report ``match``. ``select_live_version_dir`` is the
    shared selector the harness's resolution follows, so the comparison names the
    text an agent actually reads.

    A deployed bundle lives under ``{bundle}/{version}/skills/{skill}``. The
    source tree and a flat install carry no version directory; either is an
    UNMAKEABLE comparison, never "no skew".
    """
    from marketplace_bundles import resolve_bundles_root, select_live_version_dir

    root = (skill_dir or _lane_skill_dir()).resolve()
    bundle = _lane_bundle()
    if not bundle:
        return None
    try:
        bundles_root = resolve_bundles_root(root / 'SKILL.md')
    except Exception:
        return None
    bundle_dir = bundles_root / bundle
    if not bundle_dir.is_dir():
        return None
    live = select_live_version_dir(
        bundle_dir, lambda version_dir: (version_dir / 'skills' / root.name / 'SKILL.md').is_file()
    )
    return live.name if live is not None else None


def _executor_skew(executor: Path, lane_skill_dir: Path | None = None) -> str:
    """Compare the executor's version with the lane text's version.

    The version is read through ``plugin_registry``'s shared executor reader,
    never by parsing the executor here. Returns ``match`` when the executor is
    the same version or newer, ``skew`` when it is OLDER than the text this run
    read — the dangerous direction, where the text names verbs the executor's
    mapped script does not have — and ``could_not_check`` when either version
    cannot be read. ``could_not_check`` is deliberately not ``match``: a failed
    read must never be reported as agreement.
    """
    from plugin_registry import EXECUTOR_VERSION_FOUND, read_executor_version, version_key

    state, executor_version = read_executor_version(executor)
    lane_version = _lane_text_version(lane_skill_dir)
    if state != EXECUTOR_VERSION_FOUND or executor_version is None or lane_version is None:
        return _EXECUTOR_SKEW_UNCHECKED
    if version_key(executor_version) < version_key(lane_version):
        return _EXECUTOR_SKEW_SKEW
    return _EXECUTOR_SKEW_MATCH


def cmd_executor_skew(args: argparse.Namespace) -> dict[str, Any]:
    """Decide whether the executor may run the lane text this run read.

    Reports the verdict and both versions, so a ``skew`` can name them and the
    remedy. A comparison that cannot be made is ``could_not_check`` with its
    reason; the lane reports it and asks the operator instead of reading it as
    no skew.
    """
    from plugin_registry import (
        EXECUTOR_VERSION_EMPTY,
        EXECUTOR_VERSION_FOUND,
        EXECUTOR_VERSION_NOT_FOUND,
        read_executor_version,
    )

    executor = Path(getattr(args, 'executor', None) or '.plan/execute-script.py')
    lane_skill_dir = Path(getattr(args, 'lane_dir', None) or _lane_skill_dir())
    state, executor_version = read_executor_version(executor)
    lane_version = _lane_text_version(lane_skill_dir)
    verdict = _executor_skew(executor, lane_skill_dir)
    result: dict[str, Any] = {
        'status': 'success',
        'operation': 'executor-skew',
        'verdict': verdict,
        'executor': executor.as_posix(),
        'executor_version': executor_version or 'unknown',
        'lane_version': lane_version or 'unknown',
    }
    if verdict == _EXECUTOR_SKEW_SKEW:
        result['remedy'] = 'regenerate the executor'
    elif verdict == _EXECUTOR_SKEW_UNCHECKED:
        # Name WHICH side could not be read: a file that was read but carries no
        # usable assignment is a different fact from an unreadable file, and the
        # operator's remedy differs.
        if state == EXECUTOR_VERSION_FOUND:
            result['reason'] = 'lane text version not derivable from its install path'
        elif state in (EXECUTOR_VERSION_EMPTY, EXECUTOR_VERSION_NOT_FOUND):
            result['reason'] = 'executor version missing or empty'
        else:
            result['reason'] = 'executor version unreadable'
    return result


def _spec_deliverables(spec: Path) -> list[dict[str, str]]:
    """Read a staged spec's ``## Deliverables`` section into per-deliverable rows.

    Each row carries its number, title, raw ``Skills:`` value and raw
    ``Persona:`` value. Only lines INSIDE the section and outside a fenced block
    are read, so a spec that quotes the declaration format in prose or in an
    example does not declare anything by it.
    """
    try:
        lines = spec.read_text(encoding='utf-8').splitlines()
    except OSError:
        return []
    start = next((i for i, line in enumerate(lines) if line.strip() == _DELIVERABLES_HEADING), None)
    if start is None:
        return []
    rows: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_fence = False
    for line in lines[start + 1 :]:
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith('## '):
            break
        head = _DELIVERABLE_HEAD_RE.match(line)
        if head:
            current = {
                'number': head.group('number'),
                'title': head.group('title').strip().strip('*').strip(),
                'skills': '',
                'persona': '',
            }
            rows.append(current)
            continue
        if current is None:
            continue
        skills = _SKILLS_DECL_RE.match(line)
        if skills:
            current['skills'] = skills.group('value')
            continue
        persona = _PERSONA_DECL_RE.match(line)
        if persona:
            current['persona'] = persona.group('value')
    return rows


def _declared_skills(value: str) -> list[str]:
    """Split a ``Skills:`` value into its ``bundle:skill`` notations."""
    return [part.strip().strip('`') for part in value.split(',') if part.strip().strip('`')]


def _declared_persona(value: str) -> str:
    """Normalise a ``Persona:`` value to a resolvable persona notation.

    ``implementer`` and ``plan-marshall:persona-implementer`` name the same
    skill. A KEEPS its bundle when it carries one — a persona in another bundle
    must resolve there, not in the lane's own — while a bare kind is prefixed
    with the canonical ``persona-`` marker and left bare, to be qualified with
    the lane's own bundle at probe time.
    """
    persona = value.strip().strip('`')
    if not persona:
        return ''
    bundle, separator, skill = persona.partition(':')
    if not separator:
        skill = persona
    if not skill.startswith('persona-'):
        skill = f'persona-{skill}'
    return f'{bundle}:{skill}' if separator else skill


def _resolve_deliverable_skills(spec: Path) -> dict[str, Any]:
    """Resolve every deliverable's named skills and persona, and verify each exists.

    The declaration is authored by the ORCHESTRATOR when the spec is staged; the
    lane only reads it. A name that does not resolve to an installed skill is
    reported as missing so the run can stop and ask, rather than silently working
    without the standard it was told to apply.
    """
    lane_bundle = _lane_bundle()
    rows = _spec_deliverables(spec)
    declared: list[str] = []
    personas: list[str] = []
    for row in rows:
        skills = _declared_skills(row['skills'])
        declared.extend(skills)
        row['skills'] = ', '.join(skills)
        row['persona'] = _declared_persona(row['persona'])
        if row['persona']:
            personas.append(row['persona'])
    names = [*declared, *personas]
    if lane_bundle is None:
        # A flat layout that records no identity cannot attribute its own
        # dash-joined directory to a bundle, so a BARE name has no bundle to
        # resolve in. Refuse by name; a silent miss on every bare name would
        # report the wrong cause. A qualified name carries its own bundle and
        # needs this one not at all.
        if any(':' not in name for name in names):
            raise ValueError('flat_skill_identity_missing')
        lane_bundle = ''
    missing: list[str] = []
    probed: list[str] = []
    for name in names:
        if _skill_exists(name, lane_bundle):
            continue
        missing.append(name)
        probed.extend(str(candidate) for candidate in _skill_probe_paths(name, lane_bundle))
    return {
        'deliverables': rows,
        'missing_skills': missing,
        'missing_probed': probed,
        'skills_note': 'declared' if declared or personas else 'none named',
    }


def _resolve_sonar(marshal: dict[str, Any]) -> dict[str, Any]:
    """Resolve the project's Sonar state from its own configuration.

    Returns ``{'state': 'configured', 'project_key': ...}`` for a project that
    analyses its pull requests with Sonar, and ``{'state': 'not_configured'}``
    for one that does not — the state in which the lane skips the open-issue read
    and nothing blocks. Read from ``credentials_config.{provider}``, the
    non-secret block ``manage-providers credentials edit --extra`` writes, so the
    resolve stays offline: no REST call, no credential-file read.

    Fails closed on a configuration it cannot read: a ``credentials_config``
    section or provider block that is not an object is ``sonar_config_unreadable``,
    and a provider block that carries no usable ``project_key`` is
    ``sonar_config_incomplete`` — never a silent ``not_configured``. A corrupt or
    half-written Sonar block must not drain as "this project does not use Sonar",
    which is the one state in which the open-issue read is skipped.
    """
    credentials = marshal.get('credentials_config')
    if credentials is None:
        credentials = {}
    if not isinstance(credentials, dict):
        raise ValueError('sonar_config_unreadable')
    block = credentials.get(_SONAR_CONFIG_KEY)
    if block is None:
        # A pre-normalization key carries the bundle prefix; reads accept either
        # spelling (``manage-providers`` canonicalizes on the next access).
        block = credentials.get(f'plan-marshall:{_SONAR_CONFIG_KEY}')
    if block is None:
        return {'state': 'not_configured'}
    if not isinstance(block, dict):
        raise ValueError('sonar_config_unreadable')
    project_key = block.get('project_key')
    if not isinstance(project_key, str) or not project_key.strip():
        # The block exists, so this project INTENDS to analyse with Sonar; a
        # missing project key is a configuration defect, and skipping the read on
        # it would silently disable the merge gate on exactly the project that
        # asked for it. Fail closed instead.
        raise ValueError('sonar_config_incomplete')
    return {'state': 'configured', 'project_key': project_key.strip()}


def _resolve_sonar_ce_wait(project_dir: Path) -> int:
    """Resolve a CE-readiness budget that returns inside the harness's Bash ceiling.

    The plan-less read polls in-process until the analysis settles, so its budget
    must expire BEFORE the harness's Bash timeout: a budget at or above the ceiling
    gets the call killed with no typed answer, and the lane has no state to
    classify. The ceiling comes from the platform-runtime ``harness
    bash-timeout-ceiling`` seam (per active target), and the margin below it leaves
    room for the enumeration and the process teardown.

    A target that imposes no ceiling answers ``no-op``; the provider's own 600s
    default then applies. A ceiling that could not be READ is a different state,
    and it fails closed (``sonar_ce_ceiling_unreadable``): falling back to 600s
    would hand a 120s harness a budget it kills before the read can answer, which
    is the failure this budget exists to prevent. Only a project that analyses
    with Sonar calls this, so a broken seam does not block a lane that has no Sonar
    read to make.
    """
    from platform_runtime import _runtime_for_target
    from toon_parser import parse_toon

    try:
        parsed = parse_toon(_runtime_for_target(str(project_dir)).harness_bash_timeout_ceiling())
    except Exception:
        raise ValueError('sonar_ce_ceiling_unreadable') from None
    if parsed.get('status') == 'no-op':
        return _SONAR_CE_DEFAULT_SECONDS
    try:
        ceiling = int(parsed['ceiling_seconds'])
    except (KeyError, TypeError, ValueError):
        raise ValueError('sonar_ce_ceiling_unreadable') from None
    return max(1, ceiling - _SONAR_CE_CEILING_MARGIN_SECONDS)


def _resolve_bots(marshal: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve the required and optional reviewers with their trigger comments.

    An absent empty ``required_bots`` fails closed: a lane with no required
    reviewer would merge without a review, so it is refused here rather than
    silently defaulted.

    Each row also carries the reviewer's ``quota_limited`` flag, read from the
    same per-bot standards record as its trigger comments. The merge gate uses it
    to decide whether an earlier qualifying review may stand in for "reviewed the
    current head"; see ``runbook-lane/SKILL.md`` § merge gate. Because the flag
    resolves ``False`` when a record declares nothing, the authorization stays off
    for every reviewer the project has not positively marked.
    """
    plan_block = marshal.get('plan')
    steps = plan_block.get('phase-6-finalize', {}).get('steps', {}) if isinstance(plan_block, dict) else {}
    step = steps.get(_REVIEW_STEP_ID) if isinstance(steps, dict) else None
    if not isinstance(step, dict):
        raise ValueError('review_step_missing')

    import bot_registry

    def _rows(names: list[str]) -> list[dict[str, Any]]:
        return [
            {
                'bot': bot,
                'trigger_comment': bot_registry.trigger_comment(bot),
                'escalated_trigger_comment': bot_registry.escalated_trigger_comment(bot),
                'quota_limited': bot_registry.quota_limited(bot),
            }
            for bot in names
        ]

    required = _split_csv(step.get('required_bots'))
    if not required:
        raise ValueError('required_bots_empty')
    return _rows(required), _rows(_split_csv(step.get('optional_bots')))


class _BuildCommandUnresolvable(Exception):
    """The gate canonicals the project's architecture resolves to no executable.

    The field is plural by construction: the gate fails closed only when NEITHER
    ``quality-gate`` nor ``verify`` resolves, so there is never a single
    canonical to name here.
    """

    def __init__(self, canonicals: tuple[str, ...]) -> None:
        super().__init__(','.join(canonicals))
        self.canonicals = canonicals


class _ArchitectureUnavailable(Exception):
    """The project's architecture is missing or unreadable.

    A DIFFERENT fact from "the architecture does not publish this canonical": it
    says nothing was resolved at all, so reporting it as
    ``build_command_unresolvable`` would name a project defect where the cause is
    an absent crawl.
    """


def _resolve_build(project_dir: Path) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Resolve the lane's build commands through the project architecture.

    Each canonical is resolved on its own through the same seam
    ``architecture resolve`` uses, so the lane receives the COMPLETE command the
    project's build wrapper accepts: ``verify -Ppre-commit`` on Maven, the
    canonical-name form on pyproject. A canonical name is never composed onto a
    probe, because the name is only meaningful to a wrapper that maps canonical
    names — Maven's takes complete Maven arguments.

    Resolution is scoped to the ROOT module on purpose: ``resolve`` runs at
    setup, before the worktree's change surface exists, and the lane's build gate
    verifies the whole project, so the root module's command is the only one that
    is both knowable then and sufficient for every module the run touches.

    Required and optional canonicals are separated by the architecture's own
    contract: the GATE canonicals (``quality-gate``, ``verify``) are the pair
    every gated module resolves, though each build system publishes them
    conditionally (npm publishes ``quality-gate`` only for a lint script and
    ``verify`` only for a test script), so at least one must resolve; the
    test-conditional canonicals (``module-tests``, ``test-compile``) are omitted
    when the project publishes none. An absent canonical is left out of the map
    and of the split order, and a project with NO gate canonical raises
    :class:`_BuildCommandUnresolvable`, naming the gate canonicals. There is no
    composed fall-back, no default build, and no synthesized part.

    Returns ``(build, probed, missing_gate)``: the build command map, the
    architecture's resolved ``verify`` record (so the caller can read the
    timeout stamp off the same resolution instead of re-deriving the build
    system), and the gate canonicals this project does NOT publish — named
    rather than silently absent.
    """
    from _architecture_core import DataNotFoundError, ModuleNotFoundInProjectError, load_project_meta
    from _cmd_client_query import resolve_command

    # The PERSISTED architecture is what ``resolve_command`` reads, so it is what
    # this check reads — through the owner's own loader rather than a hand-parse
    # of its filename and schema. A missing or unreadable project file answers
    # "architecture unavailable", never "this project publishes no gate": the
    # latter would name a build defect for a crawl that never ran.
    try:
        project_meta = load_project_meta(str(project_dir))
    except DataNotFoundError as exc:
        raise _ArchitectureUnavailable(str(exc)) from exc
    except Exception as exc:
        raise _ArchitectureUnavailable(f'{type(exc).__name__}: {exc}') from exc
    if not isinstance(project_meta, dict) or not project_meta.get('modules'):
        raise _ArchitectureUnavailable('the project architecture declares no modules')

    # The exceptions ``resolve_command`` uses for "this project does not publish
    # that canonical"; the same trio ``_cmd_client_handlers`` treats as absence.
    # Anything else is a real architecture failure and propagates (``resolve``
    # then reports ``resolve_failed``) instead of being read as "no such part".
    _absent = (ValueError, ModuleNotFoundInProjectError, DataNotFoundError)
    resolved: dict[str, dict[str, Any]] = {}

    def _lookup(canonical: str) -> dict[str, Any] | None:
        try:
            record = resolve_command(canonical, None, str(project_dir))
        except _absent:
            return None
        executable = record.get('executable')
        if not isinstance(executable, str) or not executable.strip():
            return None
        return record

    for canonical in (*_GATE_CANONICALS, *_TEST_CONDITIONAL_CANONICALS):
        record = _lookup(canonical)
        if record is not None:
            resolved[canonical] = record

    if not any(canonical in resolved for canonical in _GATE_CANONICALS):
        # No gate at all: the lane has nothing it could run, so it refuses by
        # name rather than building with a default. Both names travel, because
        # neither resolved.
        raise _BuildCommandUnresolvable(_GATE_CANONICALS)

    build: dict[str, Any] = {canonical: record['executable'] for canonical, record in resolved.items()}
    # The split form exists because ``verify`` may outlive the shell budget; its
    # parts are the architecture's own commands for the same build system, in a
    # fixed order, filtered to the ones this project publishes. When no
    # test-conditional part resolved, the "split" is the gate canonical alone —
    # Maven's ``quality-gate`` IS ``verify -Ppre-commit`` — so it cannot be
    # shorter than ``verify`` and is answered EMPTY rather than as a duplicate.
    split = [canonical for canonical in _SPLIT_FORM if canonical in resolved]
    if not any(canonical in resolved for canonical in _TEST_CONDITIONAL_CANONICALS):
        split = []
    build['split'] = split
    # ``verify`` when published, else the gate canonical the project has. The
    # caller reads the timeout stamp off it, so it must be a gate canonical.
    probed = resolved.get('verify') or resolved[_GATE_CANONICALS[0]]
    missing_gate = [canonical for canonical in _GATE_CANONICALS if canonical not in resolved]
    return build, probed, missing_gate


def _augment_resolved(probed: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    """Return the architecture's augmented resolve record for *probed*.

    A thin seam over ``manage-architecture``'s augmentation, so the timeout
    resolution reads the architecture's own stamp without this module importing
    the architecture client at load time. The REAL augmentation always runs; a
    test that needs a stamp the fixture architecture cannot express patches the
    LOOKUP it reads, never this function.
    """
    from _cmd_client import _augment_resolved as augment

    return augment(probed, str(project_dir))


def _resolve_build_timeout(probed: dict[str, Any], project_dir: Path) -> int:
    """Return the build timeout, in seconds, from the architecture's own stamp.

    The architecture augments a resolved build command with
    ``bash_timeout_seconds`` — the bound the next real run will measure against,
    derived from the project's persisted run configuration and the build system's
    own floor. Reading it here is what keeps the lane's ``--timeout`` tied to the
    project's build configuration rather than to a number spelled into the skill.

    Falls back, only when the stamp is unavailable, to the run configuration's
    generic value and finally to the lane's documented default — never to
    ``None``, since the lane has to hand a number to the build command.
    """
    try:
        stamped = _augment_resolved(probed, project_dir).get('bash_timeout_seconds')
        if isinstance(stamped, int) and stamped > 0:
            return stamped
    except Exception:
        pass
    try:
        import run_config

        return int(run_config.timeout_get('verify', _DEFAULT_BUILD_TIMEOUT_SECONDS, str(project_dir)))
    except Exception:
        return _DEFAULT_BUILD_TIMEOUT_SECONDS


def _resolve_base_branch(marshal: dict[str, Any]) -> str:
    """Return the project's base branch.

    Read from ``project.default_base_branch`` in the project's own configuration.
    The fallback is the value the configuration seeds when the key is absent, and
    it exists only so a project that never set the key still has one: the lane
    itself never spells a base branch.
    """
    project = marshal.get('project')
    if isinstance(project, dict):
        value = project.get('default_base_branch')
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _DEFAULT_BASE_BRANCH


#: The build-server preflight states ``resolve`` reports, in the client's own
#: vocabulary. ``disabled`` is an unenrolled project, not an error. Kept here
#: because the client exposes no state constant and this plan CONSUMES the client
#: without changing it; an unrecognised state is reported as ``down`` — the
#: fail-closed direction, since the lane then runs in-process rather than
#: claiming a daemon that may not be there.
_BUILD_SERVER_STATES = ('ready', 'disabled', 'down')


def _resolve_build_server(project_dir: Path) -> tuple[str, str | None]:
    """Return the build server's preflight state for *project_dir*, plus its reason.

    Read from the build-server client's own one-call preflight, so the lane does
    not guess from a socket path or a registry file: ``disabled`` when the
    project is not enrolled (no daemon probe — enrolment is an operator action
    and the lane runs in-process), ``ready`` when a verified handshake answers,
    and ``down`` with the client's named reason otherwise.

    A preflight that cannot run at all is reported as ``down`` with a named
    reason rather than omitted: the lane still builds (in-process), and the
    landing says why the daemon was not used.
    """
    from build_server import run_preflight

    try:
        result = run_preflight(argparse.Namespace(project_path=str(project_dir)))
    except Exception as exc:
        # The client's own message is kept beside the type: a client-side defect
        # (a signature change, say) must not read as a daemon outage.
        return 'down', f'preflight_failed: {type(exc).__name__}: {exc}'
    state = result.get('preflight')
    if state not in _BUILD_SERVER_STATES:
        return 'down', 'preflight_unreadable'
    if state == 'down':
        return state, str(result.get('reason') or 'unreachable')
    return state, None


def _claude_guard_installed(project_dir: Path) -> bool:
    """Whether a Claude install registers a REAL pre-tool-use hook.

    A settings file's existence proves nothing, and neither does the KEY: a
    ``hooks.PreToolUse`` holding an empty list is a declaration, not enforcement.
    The hook has to carry at least one entry whose inner hook list holds a
    command. Both settings files are read — the shared ``settings.json`` and the
    machine-local ``settings.local.json`` — and either one registering such a hook
    is enough, since a locally installed hook enforces exactly as a shared one
    does. An unreadable or unparseable file contributes nothing.
    """
    for parts in _CLAUDE_SETTINGS_FILES:
        try:
            text = project_dir.joinpath(*parts).read_text(encoding='utf-8')
        except OSError:
            continue
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(document, dict):
            continue
        hooks = document.get('hooks')
        entries = hooks.get('PreToolUse') if isinstance(hooks, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            inner = entry.get('hooks') if isinstance(entry, dict) else None
            if isinstance(inner, list) and any(isinstance(hook, dict) and hook.get('command') for hook in inner):
                return True
    return False


def _resolve_harness_guard(project_dir: Path) -> tuple[str, str]:
    """Resolve the active harness and whether a tool-call guard is INSTALLED.

    ``antigravity`` has no pre-tool-use hooks at all, so its guard is always
    absent. On the other harnesses the guard is observed for THIS project, and
    observed as an INSTALLED hook rather than as a directory or a key: an OpenCode
    guard is its plugin file, and a Claude guard is a non-empty ``PreToolUse``
    hook registered in either settings file (see
    :func:`_claude_guard_installed`).
    """
    import target_context

    harness = target_context.resolve_target(project_dir)['target']
    if harness in _GUARD_NONE_HARNESSES:
        return harness, 'none'
    if harness == 'opencode':
        return harness, 'present' if project_dir.joinpath(*_OPENCODE_GUARD).is_file() else 'none'
    return harness, 'present' if _claude_guard_installed(project_dir) else 'none'


#: The runtime-info vocabulary the landing's stamp is written in. ``unknown`` is
#: its could-not-read value; ``mixed`` is a session tree that ran more than one
#: model or variant, whose distinct labels ride ``models``.
_RUNTIME_UNKNOWN = 'unknown'
_RUNTIME_MIXED = 'mixed'


def _stamp_value(value: Any) -> str:
    """Return a runtime-stamp value, or ``unknown`` when nothing was read."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return _RUNTIME_UNKNOWN


def _render_model(info: dict[str, Any]) -> str:
    """Render the runtime ``model`` fact as its comma-separated list form.

    A mixed session tree already carries its distinct labels in ``models``; a
    single-model tree renders ``{model}/{variant}`` when a variant was measured
    and the bare model otherwise. Nothing is averaged, reduced to the root's
    value, or guessed: an unreadable model is ``unknown``.
    """
    model = _stamp_value(info.get('model'))
    if model == _RUNTIME_MIXED:
        labels = [label.strip() for label in str(info.get('models') or '').split(',') if label.strip()]
        return ','.join(labels) if labels else _RUNTIME_UNKNOWN
    if model == _RUNTIME_UNKNOWN:
        return model
    variant = info.get('variant')
    if isinstance(variant, str) and variant.strip():
        return f'{model}/{variant.strip()}'
    return model


def _collect_runtime_info(harness: str) -> dict[str, Any]:
    """Call the platform-runtime collector with the inputs its own target passes.

    On OpenCode the model is MEASURED from the session database for the session
    the run is under, and the environment is scoped to the variables that target
    may resolve — exactly as ``opencode_runtime``'s own collector call does, so
    a Claude-specific variable leaking into the environment can never be
    attributed to an OpenCode stamp. On the other harnesses the collector reads
    the script-accessible sources itself.

    A thin seam, so the wiring can be asserted without a live session database.
    """
    from runtime_info import OPENCODE_SESSION_ID_ENV, collect_runtime_info

    measurement: dict[str, Any] = {}
    if harness == 'opencode':
        from opencode_runtime import OpenCodeRuntime, _default_opencode_db_path

        measurement = {
            'env': {key: value for key, value in os.environ.items() if key in OpenCodeRuntime._OPENCODE_MODEL_ENV},
            'opencode_db_path': _default_opencode_db_path(),
            'opencode_session_id': os.environ.get(OPENCODE_SESSION_ID_ENV),
        }
    return collect_runtime_info(harness, **measurement)


def _unknown_stamp() -> dict[str, str]:
    """The stamp for a runtime fact nothing could read."""
    return {'model': _RUNTIME_UNKNOWN, 'effort': _RUNTIME_UNKNOWN, 'plugin_version': _RUNTIME_UNKNOWN}


def _resolve_runtime_stamp(harness: str) -> tuple[dict[str, str], str | None]:
    """Resolve the landing's runtime stamp from the platform-runtime seam.

    ``harness``, ``model``, ``effort`` and ``plugin_version`` are the four facts
    the landing's consumer requires; ``plugin_version`` is the BUNDLE version
    (``runtime-info``'s ``bundle_version``), and the executor's own version rides
    the OPTIONAL ``executor_version`` — present only when it was read. The lane
    re-runs this at landing time rather than reusing its setup-time answer, so a
    model or effort switch during the run is stamped.

    Values are MEASURED by the collector — on OpenCode from the session tree —
    and an attribute with no readable source is ``unknown`` rather than an
    estimate. A seam that fails outright degrades to the same ``unknown``
    vocabulary and returns a reason naming the failure: a landing field must
    never abort ``resolve`` at setup, and the degradation must not be silent.
    """
    try:
        info = _collect_runtime_info(harness)
    except Exception as exc:
        return _unknown_stamp(), f'runtime_info_unreadable: {type(exc).__name__}: {exc}'
    stamp = {
        'model': _render_model(info),
        'effort': _stamp_value(info.get('effort')),
        'plugin_version': _stamp_value(info.get('bundle_version')),
    }
    executor_version = info.get('executor_version')
    if isinstance(executor_version, str) and executor_version.strip():
        stamp['executor_version'] = executor_version.strip()
    # The collector's own omission reason travels beside the stamp: a fact it
    # could not measure (an OpenCode run with no session id) is `unknown` WITH a
    # reason, never a silent unknown. A self-reported model is not substituted —
    # only a measurement is a stamp.
    omission = info.get('model_omission_reason')
    reason = omission.strip() if isinstance(omission, str) and omission.strip() else None
    return stamp, reason


#: The CI directory a workflow lives under, relative to the project root. A
#: DIRECTORY, never a filename: the workflow that carries the opt-in is
#: discovered, so no workflow name appears in this module.
_CI_WORKFLOW_DIR = ('.github', 'workflows')

#: The extensions a workflow file may carry.
_WORKFLOW_SUFFIXES = ('.yml', '.yaml')

#: The workflow input that opts a project in to the footprint gate, the input
#: that lists the build overrides, and the trigger filter that names the paths
#: the project's CI does not build.
_FOOTPRINT_OPT_IN_KEY = 'skip-on-docs-only'
_EXTRA_BUILDABLE_KEY = 'extra-buildable'
_PATHS_IGNORE_KEY = 'paths-ignore'

#: The architecture file category whose extensions are the project's prose classes,
#: and the ``build_systems`` marker the documentation extension writes on a
#: prose-only module. Both are the architecture's own vocabulary: the lane reads
#: them rather than spelling a class list of its own.
_ARCHITECTURE_DOC_CATEGORY = 'doc'
_ARCHITECTURE_DOC_BUILD_SYSTEM = 'documentation'


def _iter_workflow_files(project_dir: Path) -> list[Path]:
    """Return the project's CI workflow files, sorted, or an empty list.

    Discovery, not a fixed name: a project's opt-in lives in whichever workflow
    carries it, so the lane never names one.
    """
    directory = project_dir.joinpath(*_CI_WORKFLOW_DIR)
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return []
    return [entry for entry in entries if entry.is_file() and entry.suffix.lower() in _WORKFLOW_SUFFIXES]


def _footprint_opt_in(lines: list[str]) -> bool:
    """Whether *lines* opt in to the footprint gate.

    Only a literal ``true`` opts in. A definition that merely NAMES the input
    (a reusable workflow's ``skip-on-docs-only:`` header, or a caller passing an
    expression) is not an opt-in and is skipped, so a project that hosts the
    reusable workflow is not mistaken for one that uses it.
    """
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f'{_FOOTPRINT_OPT_IN_KEY}:'):
            value = stripped.split(':', 1)[1].strip().strip('"\'').lower()
            return value == 'true'
    return False


def _scalar_tokens(text: str) -> list[str]:
    """Split one scalar line into glob tokens, dropping comments and wrapping quotes.

    A quoted scalar is unwrapped before it is split, because the quote characters
    are YAML syntax rather than part of the glob. A comment line contributes
    nothing.
    """
    text = text.strip()
    if not text or text.startswith('#'):
        return []
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1]
    return [part for part in text.split() if part]


def _extra_buildable_globs(lines: list[str]) -> list[str]:
    """Return the ``extra-buildable`` globs from a workflow body, in declared order.

    Handles both scalar styles a workflow may use: an inline value (optionally
    quoted), and a block scalar whose indicator is ``>`` (folded) or ``|``
    (literal). A block-scalar indicator is not a glob, so neither style is read
    as one.
    """
    extra: list[str] = []
    for index, line in enumerate(lines):
        if not line.strip().startswith(f'{_EXTRA_BUILDABLE_KEY}:'):
            continue
        base_indent = len(line) - len(line.lstrip(' '))
        inline = line.strip().split(':', 1)[1].strip()
        if inline and not inline.startswith(('>', '|')):
            extra.extend(_scalar_tokens(inline))
        for candidate in lines[index + 1 :]:
            if not candidate.strip():
                continue
            if len(candidate) - len(candidate.lstrip(' ')) <= base_indent:
                break
            extra.extend(_scalar_tokens(candidate))
        break
    return extra


def _read_footprint_rule(project_dir: Path) -> tuple[list[str] | None, list[str] | None, str]:
    """Return ``(extra_buildable, ci_skip_globs, reason)`` for the footprint rule.

    ``extra_buildable`` is ``None`` when no workflow opts in — the architecture
    then decides — and a list when one does. A workflow that cannot be decoded
    yields an EMPTY list and a non-empty ``reason``: the caller then builds every
    path, the fail-closed direction, because an unreadable rule must never become
    a skipped build.

    ``ci_skip_globs`` is the project's own non-building class when the checkout
    HOLDS it (a ``paths-ignore`` declaration in the opting-in workflow), and
    ``None`` when it does not — the rule then lives in a reusable workflow the
    repository does not hold, and the caller falls back to the architecture's
    narrowly-scoped prose class instead of guessing a skip set.
    """
    for workflow in _iter_workflow_files(project_dir):
        try:
            text = workflow.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError) as exc:
            return [], None, f'{workflow.name}: {type(exc).__name__}'
        lines = text.splitlines()
        if not _footprint_opt_in(lines):
            continue
        return _extra_buildable_globs(lines), _paths_ignore_globs(lines), ''
    return None, None, ''


#: The gitignore directory-prefix tail the reused helper appends to every
#: pattern. A CI path filter matches a FILE path as a whole, so the tail is
#: removed before use: leaving it in would let ``docs/*`` match ``docs/a/b.md``
#: and skip a build the CI runs.
_GITIGNORE_DIR_TAIL = '(?:/.*)?$'


def _paths_ignore_globs(lines: list[str]) -> list[str] | None:
    """Return the workflow's PR non-building globs, or ``None``.

    ``None`` is the load-bearing answer: it says the project's CI rule is NOT in
    this file — the usual cause being a ``uses:`` delegation to a reusable
    workflow the checkout does not hold — so the caller must fall back to the
    architecture's narrowly-scoped prose class rather than read "no globs here"
    as "nothing is skipped". An EMPTY list is a readable rule that names
    nothing, which correctly skips nothing.

    Only the block form (``paths-ignore:`` followed by ``- glob`` items) and a plain inline scalar
    are read. A YAML flow sequence is tokenized rather than parsed, so it degrades to tokens that
    match no path — the fail-closed direction. The block's enclosing key is consulted so a
    ``push``-only filter is not applied to a PR diff, and a leading ``!`` (a re-include, which has
    no meaning in ``paths-ignore``) is dropped rather than matched literally.
    """
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith(f'{_PATHS_IGNORE_KEY}:'):
            continue
        if _enclosing_event(lines, index) not in (None, 'pull_request'):
            continue
        base_indent = len(line) - len(line.lstrip(' '))
        inline = stripped.split(':', 1)[1].strip()
        globs: list[str] = []
        if inline and not inline.startswith(('>', '|')):
            globs.extend(token for token in _scalar_tokens(inline) if not token.startswith('!'))
        for candidate in lines[index + 1 :]:
            if not candidate.strip():
                continue
            if len(candidate) - len(candidate.lstrip(' ')) <= base_indent:
                break
            item = candidate.strip()
            if item.startswith('- '):
                item = item[2:].strip()
            globs.extend(token for token in _scalar_tokens(item) if not token.startswith('!'))
        return globs
    return None


def _enclosing_event(lines: list[str], index: int) -> str | None:
    """Return the shallower YAML key enclosing ``lines[index]``, or ``None``.

    The nearest preceding line that is LESS indented and ends with ``:`` is the
    mapping key the block lives under — on a workflow trigger that is the event
    name (``push``, ``pull_request``, ``merge_group``). A line-level reader has
    no YAML parser here; the indentation scan answers the only question the
    caller has, which is whether a filter belongs to the PR event.
    """
    base_indent = len(lines[index]) - len(lines[index].lstrip(' '))
    for candidate in reversed(lines[:index]):
        if not candidate.strip():
            continue
        indent = len(candidate) - len(candidate.lstrip(' '))
        if indent < base_indent and candidate.strip().endswith(':'):
            return candidate.strip()[:-1].strip()
    return None


def _architecture_documentation_surfaces(project_dir: Path) -> list[tuple[str, set[str]]]:
    """Return one ``(prefix, extensions)`` pair per documentation-surface module.

    A documentation-surface module is one whose architecture ``build_systems``
    carries the documentation marker the documentation extension writes on a
    prose-only module. Each surface keeps its OWN extensions: a suffix that
    module B files as ``doc`` must not license a skip inside module A's
    directory. An empty result means the architecture reports no such surface,
    and no path is then classified docs-only by it.
    """
    surfaces: list[tuple[str, set[str]]] = []
    try:
        from _architecture_core import iter_modules, load_module_derived

        for name in iter_modules(str(project_dir)):
            try:
                derived = load_module_derived(name, str(project_dir))
            except Exception:
                continue
            if _ARCHITECTURE_DOC_BUILD_SYSTEM not in (derived.get('build_systems') or []):
                continue
            module_path = str((derived.get('paths') or {}).get('module') or '').strip('/')
            if not module_path or module_path == '.':
                continue
            extensions: set[str] = set()
            for rel in (derived.get('files') or {}).get(_ARCHITECTURE_DOC_CATEGORY) or []:
                # Deliberately NOT lower-cased: a CI path filter matches a suffix
                # case-sensitively, so ``.MD`` is not ``.md``.
                suffix = Path(str(rel)).suffix
                if suffix:
                    extensions.add(suffix)
            surfaces.append((f'{module_path}/', extensions))
    except Exception:
        return []
    return surfaces


def _architecture_module_prefixes(project_dir: Path) -> list[str] | None:
    """Return the module directory prefixes the architecture reports, or ``None``.

    The fallback footprint source for a project with no CI opt-in: a changed path
    is buildable when it lies inside a module the architecture knows about, and
    docs-only when it lies outside every one. A root module (``paths.module`` of
    ``.``) covers the whole tree, so such a project simply builds.
    """
    try:
        from _architecture_core import iter_modules, load_module_derived

        prefixes: list[str] = []
        for name in iter_modules(str(project_dir)):
            derived = load_module_derived(name, str(project_dir))
            # A documentation-surface module is prose, not a building module: its
            # directory must not force a build before the prose check below runs.
            if _ARCHITECTURE_DOC_BUILD_SYSTEM in (derived.get('build_systems') or []):
                continue
            module_path = str((derived.get('paths') or {}).get('module') or '').strip('/')
            prefixes.append('' if module_path in ('', '.') else f'{module_path}/')
        return prefixes
    except Exception:
        return None


class _GlobHelperUnavailable(Exception):
    """The shared glob translator could not even be imported.

    Raised from the ONE import seam, so the classifier's fail-closed answer
    names a missing translator rather than any defect in classification itself.
    """


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile *pattern* as a ROOT-ANCHORED path glob.

    The translation is not re-spelled here: it is ``manage-architecture``'s
    ``_gitignore_pattern_to_regex``, which already implements ``**`` as a
    globstar over whole segments (``test/**/*.md`` matches a file directly under
    ``test/`` as well as one nested deeper — the ``fnmatch`` defect this gate
    replaced). The pattern is handed over with a leading ``/``, the helper's
    ANCHORED form, because a CI path filter matches a repository-relative path as
    a whole: ``*.md`` is root-only and ``**/*.md`` is any depth. The helper's
    unanchored form applies gitignore's "match at any depth" rule to a slash-less
    pattern, and over-matching is the fail-OPEN direction for a skip rule.

    The helper's trailing directory-prefix group is removed: it is gitignore
    semantics (a matched DIRECTORY covers its contents), and it would let
    ``docs/*`` match ``docs/a/b.md`` and skip a build the CI runs.
    """
    try:
        from _cmd_manage import _gitignore_pattern_to_regex
    except Exception as exc:
        # A partial install (ImportError) and a translator whose own import
        # raises something else are one fact for the caller: there is no
        # translator, so nothing may be read as "no path matches".
        raise _GlobHelperUnavailable(type(exc).__name__) from exc

    translated = _gitignore_pattern_to_regex(f'/{pattern}').pattern
    if translated.endswith(_GITIGNORE_DIR_TAIL):
        translated = translated[: -len(_GITIGNORE_DIR_TAIL)]
    return re.compile(f'{translated}$')


def _matches_glob(path: str, pattern: str) -> bool:
    """Whether *path* matches *pattern*, with ``**`` as a globstar."""
    return _glob_to_regex(pattern).match(path) is not None


def _is_project_doc(path: str, doc_surfaces: list[tuple[str, set[str]]]) -> bool:
    """Whether *path* belongs to one of the architecture's documentation surfaces.

    A path is prose only when it lies inside a documentation module's prefix AND
    carries a suffix THAT module files as ``doc``. The suffix comparison is
    CASE-SENSITIVE (``README.MD`` is not ``README.md`` to a CI path filter), and
    each surface keeps its own extensions, so one module's prose vocabulary
    never licenses a skip inside another's directory. This is the narrow, closed
    fallback for a project whose CI rule the checkout does not hold; every other
    path builds.
    """
    for prefix, extensions in doc_surfaces:
        if path.startswith(prefix) and Path(path).suffix in extensions:
            return True
    return False


def _classify_path(
    path: str,
    extra: list[str],
    skip: list[str] | None,
    module_prefixes: list[str],
    doc_surfaces: list[tuple[str, set[str]]],
    source: str,
) -> str:
    """Classify ONE changed path as ``buildable`` or ``docs-only``.

    ``extra-buildable`` is an OVERRIDE that forces a build, so it is tested first:
    this repository lists ``marketplace/**/*.md`` there precisely because those
    Markdown files are test input, and the skip classes would otherwise call
    them docs-only.

    Under a READABLE CI rule (``skip`` is a list) that rule IS the non-building
    class, and the architecture is only a hint: a path the rule does not name
    builds, even when the architecture files a documentation module over it.
    When the checkout does not hold the rule (``skip`` is ``None``) the narrow
    architecture fallback applies. A path in NEITHER class is buildable — the
    gate's own direction, since its opt-in names what to SKIP, not what to
    build; the architecture fallback keeps the same fail-closed bias, because
    the module list is not an inventory of everything that can affect a build.
    """
    if any(_matches_glob(path, pattern) for pattern in extra):
        return 'buildable'
    if source == 'ci-workflow':
        if skip is not None:
            return 'docs-only' if any(_matches_glob(path, pattern) for pattern in skip) else 'buildable'
        return 'docs-only' if _is_project_doc(path, doc_surfaces) else 'buildable'
    if any(path.startswith(prefix) for prefix in module_prefixes):
        return 'buildable'
    return 'docs-only' if _is_project_doc(path, doc_surfaces) else 'buildable'


def _worktree_executor_state(worktree_dir: Path) -> tuple[str, str | None]:
    """Report whether ``worktree_dir`` carries a usable executor, and why not.

    The rule is the one the PRODUCER applies when it fills the slot
    (``workflow-integration-git``'s ``_executor_slot.executor_landed``): a
    regular, non-symlink, non-empty file. A symlink is the retired layout, and an
    empty file is the "generation exited 0 and wrote nothing" shape — neither can
    dispatch a call, so both are ``absent``.

    Restated here rather than imported: the slot module lives in the PRODUCING
    skill, and a consumer that imported it would couple the lane to another
    skill's internals for a four-line predicate. The authority stays there; this
    is the read side of the same on-disk contract, and a divergence would show
    as the lane routing on a file the producer would not have called landed.

    The pair is the whole vocabulary — ``present`` carries no reason, and
    ``absent`` always names one: ``worktree_not_created`` when the directory does
    not exist yet (a resolve taken before setup), ``executor_absent_from_worktree``
    when it exists with no usable slot.
    """
    executor = worktree_dir / '.plan' / 'execute-script.py'
    try:
        present = executor.is_file() and not executor.is_symlink() and executor.stat().st_size > 0
    except OSError:
        present = False
    if present:
        return 'present', None
    if not worktree_dir.is_dir():
        return 'absent', 'worktree_not_created'
    return 'absent', 'executor_absent_from_worktree'


def cmd_build_routing(args: argparse.Namespace) -> dict[str, Any]:
    """Decide whether a routed build may be submitted or must run in-process.

    A routed job re-runs the WORKTREE's own ``.plan/execute-script.py``, and the
    routing submits without checking that it exists — so an absent executor ends
    the job terminal (exit 2) with no in-process fallback. ``worktree-create``
    now fills that slot, so the normal answer is ``auto``: submit, and the daemon
    re-runs the worktree's own executor.

    ``in_process`` is the DEGRADED answer, taken only when the slot is absent,
    and it carries the named reason the run records. ``executor_in_worktree``
    reports the read itself, so the mode and the state cannot disagree.
    """
    worktree = Path(getattr(args, 'worktree', None) or '.').resolve()
    state, reason = _worktree_executor_state(worktree)
    result: dict[str, Any] = {
        'status': 'success',
        'operation': 'build-routing',
        'worktree': worktree.as_posix(),
        'executor_in_worktree': state,
        'execution_mode': 'auto',
    }
    if state == 'absent':
        result['execution_mode'] = 'in_process'
        result['reason'] = reason
    return result


def cmd_build_classify(args: argparse.Namespace) -> dict[str, Any]:
    """Classify the changed paths so the build gate can skip a docs-only change.

    The rule's SOURCE is the project's own: its CI footprint opt-in when it has
    one, else the architecture's module directories. A project that declares
    neither yields ``buildable`` for every path — the fail-closed direction, since
    skipping a build the project would have run is the expensive mistake.
    """
    project_dir = Path(getattr(args, 'project_dir', '.') or '.').resolve()
    paths = [part.strip() for part in (args.paths or '').split(',') if part.strip()]
    if not paths:
        return {'status': 'error', 'error': 'no_paths', 'message': 'no changed paths to classify'}

    extra, skip, reason = _read_footprint_rule(project_dir)
    if extra is not None:
        source = 'ci-workflow'
        module_prefixes: list[str] = []
    else:
        source = 'architecture'
        module_prefixes = _architecture_module_prefixes(project_dir) or ['']
    doc_surfaces = _architecture_documentation_surfaces(project_dir)

    if reason:
        # The opt-in was found but its rule could not be read: skip nothing, so
        # the unknown rule costs a local build rather than a skipped CI one.
        rows = [{'path': path, 'kind': 'buildable'} for path in paths]
    else:
        try:
            rows = [
                {
                    'path': path,
                    'kind': _classify_path(path, extra or [], skip, module_prefixes, doc_surfaces, source),
                }
                for path in paths
            ]
        except _GlobHelperUnavailable as exc:
            # The shared glob translator is unavailable: absent from a partial
            # install, or raising something other than ImportError while it is
            # imported (a missing dependency of its own, a broken module body).
            # Build everything and name the cause: a broken translator must never
            # be read as "no path matches", which for a skip rule would skip, and
            # an uncaught non-ImportError must not abort the classifier.
            rows = [{'path': path, 'kind': 'buildable'} for path in paths]
            reason = f'glob helper unavailable: {exc}'
    buildable = any(row['kind'] == 'buildable' for row in rows)
    result: dict[str, Any] = {
        'status': 'success',
        'operation': 'build-classify',
        'source': source,
        'kind': 'buildable' if buildable else 'docs-only',
        'buildable': buildable,
        'paths': rows,
    }
    # A rule that could not be read is named, so the caller sees WHY every path
    # built rather than reading the outcome as a rule that simply matched nothing.
    if reason:
        result['reason'] = reason
    return result


def _sonar_gate_verdict(
    state: str,
    count_status: str | None,
    open_count: int | None,
    open_keys: list[str],
    dismissed_keys: list[str],
) -> dict[str, Any]:
    """Decide whether the Sonar read admits the merge (section 7's condition).

    The verdict is a pure function of the read and the run's recorded dismissals,
    so the lane's merge condition is a decision a script makes rather than a
    judgement a reader re-derives:

    - ``not_configured`` — the project does not analyse with Sonar, so there is
      no open-issue condition to satisfy.
    - ``undecidable`` — the read never settled. This is a BLOCKER, never a ``0``:
      no count and no key set were observed, so "no open issues" is unknowable.
    - ``unconfigured`` — resolve said ``configured`` and the read could not
      authenticate. Also a blocker: the credentials the project claims are not
      usable, which is a defect nobody would otherwise see.
    - ``confirmed`` — admitted when the count is ``0``, or when every open issue
      the read enumerated is covered by a recorded dismissal. A count with no
      enumerated key set cannot be verified key by key, so it is refused rather
      than passed on the count alone.
    """
    if state == 'not_configured':
        return {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': True,
            'reason': 'not_configured',
        }
    if count_status == 'undecidable':
        return {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': False,
            'reason': 'undecidable_read',
            'open_issue_count': None,
        }
    if count_status == 'unconfigured':
        return {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': False,
            'reason': 'unconfigured_read',
        }

    count = open_count if isinstance(open_count, int) and open_count >= 0 else None
    if count is None:
        return {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': False,
            'reason': 'confirmed_read_without_count',
            'open_issue_count': None,
        }
    if count == 0:
        if open_keys:
            # Mirror of the count guard above: a measured zero enumerates no key,
            # so keys beside it describe some other read.
            return {
                'status': 'success',
                'operation': 'sonar-gate',
                'merge_allowed': False,
                'reason': 'confirmed_zero_with_open_keys',
                'open_issue_count': 0,
            }
        return {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': True,
            'reason': 'no_open_issues',
            'open_issue_count': 0,
        }
    if len(set(open_keys)) < count:
        # Distinct keys, not list length: a repeated key enumerates one issue
        # twice, so `--open-count 2 --open-keys K1,K1` would otherwise pass a
        # check whose whole purpose is to refuse a count it cannot verify.
        return {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': False,
            'reason': 'open_issue_keys_missing',
            'open_issue_count': count,
        }
    dismissed = set(dismissed_keys)
    undismissed = [key for key in open_keys if key not in dismissed]
    if undismissed:
        return {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': False,
            'reason': 'open_issues_undismissed',
            'open_issue_count': count,
            'undismissed_keys': undismissed,
        }
    return {
        'status': 'success',
        'operation': 'sonar-gate',
        'merge_allowed': True,
        'reason': 'all_open_issues_dismissed',
        'open_issue_count': count,
        'dismissed_count': len(dismissed),
    }


def cmd_sonar_gate(args: argparse.Namespace) -> dict[str, Any]:
    """Report whether the pull request's Sonar state admits the merge."""
    state = getattr(args, 'state', None)
    count_status = getattr(args, 'count_status', None)
    open_count = getattr(args, 'open_count', None)
    if state not in _SONAR_STATES:
        return {
            'status': 'error',
            'error': 'invalid_sonar_state',
            'message': f'--state must be one of {", ".join(_SONAR_STATES)}; got {state!r}',
        }
    if state == 'not_configured':
        # A read state supplied beside `not_configured` is a contradiction: a
        # project with no Sonar has no read to report. Refuse it rather than let a
        # stale count ride an "allowed" verdict.
        if count_status is not None or open_count is not None:
            return {
                'status': 'error',
                'error': 'state_contradicts_read',
                'message': 'a not_configured state carries no read; drop --count-status and --open-count',
            }
        return _sonar_gate_verdict(state, None, None, [], [])
    if count_status not in _SONAR_COUNT_STATUSES:
        return {
            'status': 'error',
            'error': 'invalid_count_status',
            'message': (
                f'--count-status must be one of {", ".join(_SONAR_COUNT_STATUSES)} '
                f'when --state configured; got {count_status!r}'
            ),
        }
    return _sonar_gate_verdict(
        state,
        count_status,
        open_count,
        _split_csv(getattr(args, 'open_keys', None)),
        _split_csv(getattr(args, 'dismissed_keys', None)),
    )


def cmd_sonar_facts(args: argparse.Namespace) -> dict[str, Any]:
    """Render the landing's optional Sonar facts from the read taken at the merge head.

    Two facts on the per-step typed-fact channel the lifecycle's
    ``sonar-roundtrip`` step already uses — one measurement, one channel:
    ``step.sonar-roundtrip.open_issue_count`` and
    ``step.sonar-roundtrip.open_issue_rules``.

    The two sentinels are the point of the verb. A confirmed read carries the
    MEASURED count. An ``undecidable`` read carries ``unknown`` — a failed read
    asserts that nothing was observed and never collapses into ``0``, which is a
    claim the run did not earn. A project without Sonar carries ``n/a``, the
    answered absence. Both facts are OPTIONAL in the landing, so the required key
    set is untouched and no earlier landing becomes incomplete.
    """
    state = getattr(args, 'state', None)
    if state not in _SONAR_STATES:
        return {
            'status': 'error',
            'error': 'invalid_sonar_state',
            'message': f'--state must be one of {", ".join(_SONAR_STATES)}; got {state!r}',
        }

    if state == 'not_configured':
        # Symmetric with the gate: a read supplied beside `not_configured` is a
        # contradiction, and rendering `n/a` over it would hide that the caller
        # read one project's issues and reported another project's state.
        if any(getattr(args, name, None) is not None for name in ('count_status', 'open_count', 'rules')):
            return {
                'status': 'error',
                'error': 'state_contradicts_read',
                'message': 'a not_configured state carries no read; drop --count-status, --open-count and --rules',
            }
        count, rules = 'n/a', 'n/a'
    else:
        count_status = getattr(args, 'count_status', None)
        if count_status not in _SONAR_COUNT_STATUSES:
            return {
                'status': 'error',
                'error': 'invalid_count_status',
                'message': (
                    f'--count-status must be one of {", ".join(_SONAR_COUNT_STATUSES)} when --state configured; '
                    f'got {count_status!r}'
                ),
            }
        if count_status in ('undecidable', 'unconfigured'):
            # Both are failed reads: nothing was observed, so the figure is
            # `unknown` — never `0`, which is a measured clean answer.
            count, rules = 'unknown', 'unknown'
        else:
            open_count = getattr(args, 'open_count', None)
            if not isinstance(open_count, int) or open_count < 0:
                return {
                    'status': 'error',
                    'error': 'confirmed_read_without_count',
                    'message': '--open-count is required for a confirmed read',
                }
            count = str(open_count)
            declared = _split_csv(getattr(args, 'rules', None))
            if not declared and open_count > 0:
                # A non-zero count with no rules would render as "3 open issues,
                # no rule left open" — a figure whose other half is missing. The
                # read enumerates the rules, so the lane can always pass them.
                return {
                    'status': 'error',
                    'error': 'confirmed_read_without_rules',
                    'message': '--rules is required for a confirmed count above zero',
                }
            rules = ','.join(declared) if declared else 'none'
            if declared and open_count == 0:
                # The mirror of the guard above: a measured zero leaves no rule
                # open, so a rule beside it describes some other read.
                return {
                    'status': 'error',
                    'error': 'confirmed_zero_with_rules',
                    'message': 'a confirmed count of zero carries no rule left open',
                }

    return {
        'status': 'success',
        'operation': 'sonar-facts',
        'open_issue_count': count,
        'open_issue_rules': rules,
        'fact_lines': [
            f'step.{_SONAR_FACT_STEP}.open_issue_count={count}',
            f'step.{_SONAR_FACT_STEP}.open_issue_rules={rules}',
        ],
    }


def cmd_resolve(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve every project-specific value the runbook lane needs."""
    project_dir = Path(getattr(args, 'project_dir', '.') or '.').resolve()

    try:
        choice = _resolve_spec(args.spec, project_dir, from_ledger=args.spec_from_ledger)
    except ValueError as exc:
        return {'status': 'error', 'error': str(exc), 'spec': args.spec}
    spec, slug, plan_id = choice.path, choice.slug, choice.plan_id
    try:
        marshal = _read_marshal(project_dir)
        required, optional = _resolve_bots(marshal)
        build, probed, missing_gate = _resolve_build(project_dir)
        build_timeout_seconds = _resolve_build_timeout(probed, project_dir)
        base_branch = _resolve_base_branch(marshal)
        deliverable_state = _resolve_deliverable_skills(spec)
        sonar_state = _resolve_sonar(marshal)
        # The read's budget is resolved only for a project that will make the read:
        # a broken ceiling seam must not block a lane with no Sonar read to make.
        sonar_ce_wait = _resolve_sonar_ce_wait(project_dir) if sonar_state['state'] == 'configured' else None
    except _ArchitectureUnavailable as exc:
        # Nothing was resolved because the architecture itself is absent or
        # unreadable: naming that cause keeps it distinct from a project that
        # publishes no gate canonical.
        return {
            'status': 'error',
            'error': 'architecture_unavailable',
            'message': str(exc),
            'spec': args.spec,
            'plan': plan_id,
        }
    except _BuildCommandUnresolvable as exc:
        # Fail closed and name the gate canonicals that could not be resolved:
        # the lane never falls back to a composed string or to a default build.
        return {
            'status': 'error',
            'error': 'build_command_unresolvable',
            'canonicals': list(exc.canonicals),
            'spec': args.spec,
            'plan': plan_id,
        }
    except ValueError as exc:
        return {'status': 'error', 'error': str(exc), 'spec': args.spec, 'plan': plan_id}
    except Exception as exc:
        return {'status': 'error', 'error': 'resolve_failed', 'message': str(exc), 'plan': plan_id}

    if deliverable_state['missing_skills']:
        # Fail closed: a spec that names a skill which is not installed cannot be
        # run as written, and skipping it silently would drop a standard the
        # orchestrator deliberately attached to that deliverable.
        return {
            'status': 'error',
            'error': 'named_skill_not_found',
            'missing': ', '.join(deliverable_state['missing_skills']),
            'probed': ', '.join(deliverable_state['missing_probed']),
            'spec': args.spec,
            'plan': plan_id,
        }

    import run_config

    trailer = run_config.read_commit_trailer()['trailer']
    harness, guard = _resolve_harness_guard(project_dir)
    build_server, build_server_reason = _resolve_build_server(project_dir)
    runtime_stamp, runtime_stamp_reason = _resolve_runtime_stamp(harness)

    worktree = f'.plan/local/worktrees/{plan_id}'
    progress_file = f'.plan/temp/rb-{plan_id}/progress.md'
    sender_id = f'rb-{plan_id}'
    landing_file = f'.plan/temp/landing-{plan_id}.md'
    executor_state, executor_reason = _worktree_executor_state(project_dir / worktree)
    inbox_write_command = (
        'python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox write '
        f'--slug {slug} --sender-type plan --sender-id {sender_id} --kind landing --payload-file {landing_file}'
    )

    resolved: dict[str, Any] = {
        'status': 'success',
        'operation': 'resolve',
        'spec': spec.as_posix(),
        'spec_source': choice.source,
        'slug': slug,
        'plan': plan_id,
        'worktree': worktree,
        'progress_file': progress_file,
        'landing_file': landing_file,
        'sender_id': sender_id,
        'inbox_write_command': inbox_write_command,
        'build': build,
        'build_timeout_seconds': build_timeout_seconds,
        'base_branch': base_branch,
        'required_bots': required,
        'optional_bots': optional,
        'commit_trailer': trailer,
        'harness': harness,
        'model': runtime_stamp['model'],
        'effort': runtime_stamp['effort'],
        'plugin_version': runtime_stamp['plugin_version'],
        'guard': guard,
        'guard_log': '/'.join(_GUARD_LOG_PARTS),
        'build_server': build_server,
        'sonar': sonar_state['state'],
        'skills_note': deliverable_state['skills_note'],
        'executor_in_worktree': executor_state,
    }
    # A reason exists only for ``absent``: the present row carries no absence
    # explanation, which would read like a qualified success.
    if executor_reason is not None:
        resolved['executor_reason'] = executor_reason
    # The differ marker is PRESENCE-gated rather than always-false: it exists to
    # say "the copy you did not read says something else", and a `false` row would
    # invite a consumer to treat "no marker" and "no second copy" as one state.
    if choice.differs:
        resolved['spec_differ'] = True
    # A project can publish only one gate canonical (npm publishes each
    # conditionally), so the missing one is NAMED rather than silently dropped.
    # Presence-gated: an empty population would read like a parsed-but-empty
    # answer on every fully-populated project.
    if missing_gate:
        resolved['build_missing_canonicals'] = list(missing_gate)
    # The read's budget rides only when there is a read to make: an empty row
    # would read like a parsed-but-empty answer on a project without Sonar.
    if sonar_ce_wait is not None:
        resolved['sonar_ce_wait_timeout_seconds'] = sonar_ce_wait
    # The project key rides only when there is one: an empty row would read like a
    # parsed-but-empty answer on a project that does not use Sonar at all.
    if 'project_key' in sonar_state:
        resolved['sonar_project_key'] = sonar_state['project_key']
    # The executor version is OPTIONAL in the landing, so it is present only when
    # the seam actually read one — never an `unknown` line the template must drop.
    if 'executor_version' in runtime_stamp:
        resolved['executor_version'] = runtime_stamp['executor_version']
    # A reason only exists for ``down``: the other two states are their own
    # explanation, and an empty row would read like a parsed-but-empty answer.
    if build_server_reason is not None:
        resolved['build_server_reason'] = build_server_reason
    # Likewise for a runtime seam that failed: the stamp degrades to ``unknown``
    # so setup is never aborted, and the reason keeps that from being silent.
    if runtime_stamp_reason is not None:
        resolved['runtime_stamp_reason'] = runtime_stamp_reason
    # Presence-gated: an empty population would render an empty row set that reads
    # like a parsed-but-empty answer, when the truth is that no spec declares one.
    if deliverable_state['deliverables']:
        resolved['deliverables'] = deliverable_state['deliverables']
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description='Runbook-lane resolver', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True, help='Resolver verb')

    resolve_parser = subparsers.add_parser(
        'resolve', help='Resolve the project-specific lane values', allow_abbrev=False
    )
    resolve_parser.add_argument(
        '--spec', required=True, help='Staged spec path: .plan/orchestrator/{slug}/plans/PLAN-*.md'
    )
    resolve_parser.add_argument('--project-dir', default='.', help='Project root (default: current directory)')
    resolve_parser.add_argument(
        '--spec-from-ledger',
        dest='spec_from_ledger',
        action='store_true',
        help='Read the spec from the shared ledger worktree first, falling back to the main checkout',
    )

    skew_parser = subparsers.add_parser(
        'executor-skew',
        help='Compare the executor version with the lane text version',
        allow_abbrev=False,
    )
    skew_parser.add_argument(
        '--executor',
        default=None,
        help='Executor to read (default: .plan/execute-script.py)',
    )
    skew_parser.add_argument(
        '--lane-dir',
        dest='lane_dir',
        default=None,
        help="The lane skill's own directory (default: this script's skill dir)",
    )

    routing_parser = subparsers.add_parser(
        'build-routing',
        help='Decide whether a routed build may be submitted or must run in-process',
        allow_abbrev=False,
    )
    routing_parser.add_argument(
        '--worktree',
        required=True,
        help='The worktree the build will run against',
    )

    classify_parser = subparsers.add_parser(
        'build-classify', help='Classify changed paths as docs-only or buildable', allow_abbrev=False
    )
    classify_parser.add_argument('--paths', required=True, help='Comma-separated changed paths')
    classify_parser.add_argument('--project-dir', default='.', help='Project root (default: current directory)')

    gate_parser = subparsers.add_parser(
        'sonar-gate', help="Decide whether the pull request's Sonar state admits the merge", allow_abbrev=False
    )
    gate_parser.add_argument(
        '--state',
        required=True,
        help='The state resolve reported: configured, or not_configured',
    )
    gate_parser.add_argument(
        '--count-status',
        dest='count_status',
        default=None,
        help="The read's count_status: confirmed, undecidable, or unconfigured (required when configured)",
    )
    gate_parser.add_argument(
        '--open-count',
        dest='open_count',
        type=int,
        default=None,
        help="The read's confirmed open-issue count",
    )
    gate_parser.add_argument(
        '--open-keys',
        dest='open_keys',
        default=None,
        help='Comma-separated issue keys the read enumerated',
    )
    gate_parser.add_argument(
        '--dismissed-keys',
        dest='dismissed_keys',
        default=None,
        help='Comma-separated issue keys this run dismissed with a stated reason',
    )

    facts_parser = subparsers.add_parser(
        'sonar-facts',
        help="Render the landing's optional Sonar facts from the merge-head read",
        allow_abbrev=False,
    )
    facts_parser.add_argument(
        '--state',
        required=True,
        help='The state resolve reported: configured, or not_configured',
    )
    facts_parser.add_argument(
        '--count-status',
        dest='count_status',
        default=None,
        help="The read's count_status: confirmed, undecidable, or unconfigured (required when configured)",
    )
    facts_parser.add_argument(
        '--open-count',
        dest='open_count',
        type=int,
        default=None,
        help="The read's confirmed open-issue count",
    )
    facts_parser.add_argument(
        '--rules',
        default=None,
        help='Comma-separated rules of the issues left open at the merge head',
    )

    args = parser.parse_args()
    if args.command == 'resolve':
        data = cmd_resolve(args)
        if data.get('status') == 'error':
            output_toon_error(
                data['error'],
                data.get('message', data['error']),
                **{k: v for k, v in data.items() if k not in ('status', 'error', 'message')},
            )
            return 0
        output_toon(data)
        return 0
    if args.command == 'executor-skew':
        output_toon(cmd_executor_skew(args))
        return 0
    if args.command == 'build-routing':
        output_toon(cmd_build_routing(args))
        return 0
    if args.command == 'build-classify':
        data = cmd_build_classify(args)
        if data.get('status') == 'error':
            output_toon_error(data['error'], data.get('message', data['error']))
            return 0
        output_toon(data)
        return 0
    if args.command == 'sonar-gate':
        data = cmd_sonar_gate(args)
        if data.get('status') == 'error':
            output_toon_error(data['error'], data.get('message', data['error']))
            return 0
        output_toon(data)
        return 0
    if args.command == 'sonar-facts':
        data = cmd_sonar_facts(args)
        if data.get('status') == 'error':
            output_toon_error(data['error'], data.get('message', data['error']))
            return 0
        output_toon(data)
        return 0
    parser.print_help()
    return 2


if __name__ == '__main__':
    main()
