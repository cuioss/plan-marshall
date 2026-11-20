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

    runbook_lane resolve --spec PATH [--project-dir DIR]
    runbook_lane executor-skew [--executor PATH] [--lane-dir DIR]
    runbook_lane build-routing --worktree PATH
    runbook_lane build-classify --paths P1,P2 [--project-dir DIR]
    runbook_lane sonar-stale-delta --state STATE [--count-status STATUS]
                             [--analysis-revision SHA] [--head-revision SHA] [--worktree DIR]
    runbook_lane sonar-gate --state STATE [--count-status STATUS] [--open-count N]
                             [--open-keys K1,K2] [--operator-selected-keys K1,K2]
                             [--carried-forward --carried-forward-analysis-revision SHA
                              --carried-forward-head-revision SHA]
    runbook_lane sonar-facts --state STATE [--count-status STATUS] [--open-count N] [--rules R1,R2]
                             [--gate-status STATUS]
                             [--carried-forward --analysed-revision SHA --carried-forward-head-revision SHA]
    runbook_lane review-gate --pr-number N [--project-dir DIR] [--disposition TEXT ...]

``--spec`` must name a staged spec, i.e. a file below
``.plan/orchestrator/{slug}/plans/``. Anything else is refused: the lane exists
to run a staged orchestrator plan, and a path outside that tree names something
else. ``--project-dir`` defaults to the current directory and anchors every
project-scoped read (marshal.json, the project architecture, the guard marker).

``--spec`` names that staged spec LOGICALLY: the read is worktree-first by
default. The shared ledger worktree's copy —
``{epic_dir}/plans/{spec name}``, where ``epic_dir`` follows the store seam the
orchestrator publishes — wins when it exists, and the main checkout's copy is the
fallback when the worktree holds none. Every spec edit lives only in that worktree
until a ledger land, so this default is what lets an emitted command carry no flag
and need no land. With ``orchestrator.use_worktree`` off there is no second copy
and the one copy is read without error. ``--spec-from-ledger`` is accepted as a
documented no-op: it names the read the default makes, so a command line that
carries it behaves exactly as one that does not. ``resolve`` always reports which
copy it read (``spec_source``: ``ledger_worktree`` | ``main_checkout``) and, when
both copies exist and differ, ``spec_differ: true`` — "the copy NOT read says
something else", which is the main checkout's copy when the worktree's was read,
and the marker a read of the older copy would otherwise leave out.

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
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, NamedTuple

import orchestrator_worktree
import spec_skills
from file_ops import output_toon, output_toon_error
from marketplace_paths import PLAN_DIR_NAME, base_dir_override_active, main_checkout_root

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

#: The landing's required Sonar count key. One spelling for one measurement: the
#: schema, the gate's read and this renderer all name the same field, so a
#: landing cannot carry the figure under a second name the check does not require.
_SONAR_OPEN_ISSUES_FACT = 'sonar_open_new_issues'

#: The landing's OPTIONAL Sonar rules fact, on the per-step typed-fact channel the
#: lifecycle's ``sonar-roundtrip`` step already uses.
_SONAR_FACT_STEP = 'sonar-roundtrip'

#: The landing's OPTIONAL quality-gate fact. A Sonar quality gate can fail on a
#: new-code METRIC (coverage, duplication, maintainability) that is neither an
#: open finding nor an unreviewed hotspot, so such a failure is not a finding for
#: the open-findings rule — but it is reported, because a landing that says the
#: merge head was clean and stays silent about a failing gate would be stating
#: half the read.
_SONAR_QUALITY_GATE_FACT = f'step.{_SONAR_FACT_STEP}.quality_gate_status'

#: The four states the quality-gate read can answer with. ``not_computed`` is a
#: provider answer (no new-code analysis for the head), distinct from ``unknown``
#: (the read itself failed) — the same answered-absence / failed-read split the
#: count facts use.
SONAR_GATE_STATUSES = ('ok', 'error', 'not_computed', 'unknown')

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

#: The longest body slot the CI's own slot pattern accepts on the OLDEST executor this
#: lane may meet: 64 characters until the executor is regenerated.
_BODY_SLOT_MAX_LENGTH = 64


def _plan_id_from_spec(spec: Path) -> str:
    """Derive the lane plan id from a spec's basename, unfolded.

    ``PLAN-42-example-slug.md`` becomes ``42-example-slug``: the ``PLAN-`` marker is
    dropped and the rest is lower-cased, which is the same id the orchestrator's row
    and the inbox sender share. It is deliberately NOT folded further: the id names
    the worktree, the progress file, the sender and the inbox, so two staged plans
    whose names differ only in separators must keep distinct ids. The body slot is a
    different value with a different vocabulary — see :func:`_body_slot_from_plan_id`.
    """
    stem = spec.name
    if stem.endswith('.md'):
        stem = stem[:-3]
    if stem.startswith('PLAN-'):
        stem = stem[len('PLAN-') :]
    return stem.lower()


def _body_slot_from_plan_id(plan_id: str) -> str:
    """Derive the CI body slot from a plan id.

    The slot vocabulary is lowercase letters, digits and hyphens, starting with a
    letter or digit, at most 64 characters (the live executor's accepted bound until
    the executor is regenerated). A spec name with ``_``, ``.`` or a long stem would
    otherwise derive a slot the CI rejects and stall the lane at PR open.

    Folding is LOSSY, so any id the fold changes — separators, case, punctuation or
    truncation — carries a digest of the ORIGINAL id. Two plans whose ids differ only
    in separators therefore keep distinct slots instead of silently sharing one.
    """
    folded = re.sub(r'[^a-z0-9]+', '-', plan_id.lower()).strip('-') or 'plan'
    if folded == plan_id and len(folded) <= _BODY_SLOT_MAX_LENGTH:
        return folded
    digest = hashlib.sha1(plan_id.encode('utf-8')).hexdigest()[:8]
    return f'{folded[: _BODY_SLOT_MAX_LENGTH - len(digest) - 1]}-{digest}'


class _SpecChoice(NamedTuple):
    """The copy of a staged spec ``resolve`` will read, and what it must report.

    A ``NamedTuple`` rather than a dataclass on purpose: the suite loads this
    module with ``register=False``, and ``dataclasses`` resolves a class's own
    module through ``sys.modules`` — which is empty for that load — so a dataclass
    here raises ``AttributeError`` on import in every test that takes that path.
    """

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


def _staged_spec_shape(spec: Path, project_dir: Path) -> tuple[str, str]:
    """Return ``(slug, file name)`` for a spec path, or refuse it.

    The file name carries its ``.md`` extension, because the caller rebuilds both
    copies' paths from it — the regex group that matches it deliberately stops
    before the extension.

    The project-relative path is matched as a WHOLE against :data:`_SPEC_RE`, so a
    same-shaped file nested elsewhere (an archive, a fixture tree) never
    qualifies. A second spelling is accepted beside it: a path inside the ledger
    worktree's own store, which is exactly the form a caller reaches for when the
    worktree copy is the one it wants — accepted with no flag, because the
    worktree-first read is the default. Every other path is the
    ``spec_outside_orchestrator`` refusal.
    """
    try:
        relative = spec.resolve().relative_to(project_dir.resolve())
    except ValueError:
        relative = None
    if relative is not None:
        match = _SPEC_RE.fullmatch(relative.as_posix())
        if match is not None:
            return match.group('slug'), f'{match.group("name")}.md'
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


def _main_store_dir(project_dir: Path) -> Path:
    """The ``.plan`` directory of the checkout the fallback copy belongs to.

    The lane runs every command from the MAIN checkout, but ``--project-dir`` can
    name a plan worktree, where ``{project_dir}/.plan`` is that worktree's own
    config tier — NOT the copy a ``main_checkout`` answer claims to have read. The
    fallback therefore anchors on the main checkout the ledger worktree is a
    worktree OF (the git common dir), and stays on ``project_dir`` only where that
    anchor does not exist: outside a git checkout, or under a base-dir override
    that already stands in for main.
    """
    if not base_dir_override_active():
        try:
            return main_checkout_root() / PLAN_DIR_NAME
        except RuntimeError:
            pass
    return project_dir / PLAN_DIR_NAME


def _contained_file(path: Path, root: Path) -> bool:
    """Whether ``path`` is a file whose RESOLVED location stays under ``root``.

    A copy derived from the validated slug and name is not the caller's resolved
    path, and ``is_file`` follows symlinks — so a link planted at the derived
    location could otherwise hand the lane a file from outside the store while the
    result claims a store copy. Requiring the resolution to stay under the store
    root closes that without giving up the read.
    """
    if not path.is_file():
        return False
    try:
        return path.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def _named_copy_is_contained(spec: Path, main_store: Path, ledger_store: Path | None) -> bool:
    """Whether a directly named spec resolves under the main or the ledger store.

    The shape check proves the path LOOKS like a staged spec; this proves it IS one
    of the two copies the read order is about. A same-shaped file in a plan
    worktree's own ``.plan`` tier passes the first test and fails this one — it is
    neither copy — so the read is refused instead of being labelled
    ``main_checkout`` for a file the main checkout does not hold.
    """
    if _contained_file(spec, main_store):
        return True
    return ledger_store is not None and _contained_file(spec, ledger_store)


def _resolve_spec(spec_value: str, project_dir: Path) -> _SpecChoice:
    """Validate ``--spec`` and select the copy of it to read.

    A RELATIVE spec is resolved against ``--project-dir``, not against the
    process's working directory: the flag names the project the whole resolution
    is about, so a caller that passes both must get the spec file it named.

    The read is WORKTREE-FIRST: the ledger worktree's copy wins when it exists, so
    a spec that exists only in the worktree is readable by default, and the main
    checkout's copy is the fallback for a spec the worktree does not hold —
    ``invalid_spec`` when neither exists, and ``invalid_spec`` for a same-shaped
    file that resolves under neither store root. The choice is reported as
    ``source``, and ``differs`` says whether the copy NOT read would have answered
    differently (the main checkout's copy, when the worktree's was read).

    Raised as ``ValueError`` carrying the refusal code so the caller can emit a
    structured error rather than a traceback.
    """
    spec = Path(spec_value)
    if not spec.is_absolute():
        spec = project_dir / spec
    slug, name = _staged_spec_shape(spec, project_dir)

    main_store = _main_store_dir(project_dir)
    main_copy = main_store / 'orchestrator' / slug / 'plans' / name
    # Both copies are resolved on every path: which one is READ is the default
    # order's decision, while the differ marker exists to report a read that left
    # the other copy unread.
    ledger_copy: Path | None = None
    store = _ledger_store_dir()
    if store is not None:
        candidate = store / 'orchestrator' / slug / 'plans' / name
        if _contained_file(candidate, store):
            ledger_copy = candidate

    if ledger_copy is not None:
        chosen, source = ledger_copy, 'ledger_worktree'
    elif _contained_file(main_copy, main_store):
        chosen, source = main_copy, 'main_checkout'
    elif spec.is_file() and _named_copy_is_contained(spec, main_store, store):
        # The caller named the copy directly. It survived the shape check, and it
        # must ALSO resolve under one of the two store roots: a same-shaped file in
        # a plan worktree's own ``.plan`` tier is not a store copy, and reading it
        # while reporting `main_checkout` would mislabel the source. The LABEL comes
        # from where the file actually resolves, never from the order alone.
        chosen = spec.resolve()
        source = 'ledger_worktree' if store is not None and _contained_file(chosen, store) else 'main_checkout'
    else:
        raise ValueError('invalid_spec')

    differs = (
        ledger_copy is not None and _contained_file(main_copy, main_store) and _copies_differ(ledger_copy, main_copy)
    )
    return _SpecChoice(chosen, slug, _plan_id_from_spec(chosen), source, differs)


def _copies_differ(first: Path, second: Path) -> bool:
    """Whether two spec copies hold different bytes.

    An unreadable pair answers ``False``: the marker says "the copy you did not
    read says something else", and it must never be raised on a read it could not
    make — the refusal path is the spec READ, not this comparison, so a permission
    or I/O fault here degrades the marker instead of turning a usable spec into a
    traceback.
    """
    try:
        return first.read_bytes() != second.read_bytes()
    except OSError:
        return False


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


# --- the per-deliverable declaration: ONE reader, owned by script-shared -------
#
# The orchestrator's ``corpus spec-skills`` verb reads the same ``Skills:`` /
# ``Persona:`` lines this lane loads, so the grammar, the declaration resolution
# and the existence probe live in ``script-shared``'s ``spec_skills`` module. These
# wrappers keep the lane's call sites — and its tests — on the lane's own surface
# rather than turning the lane into a second reader.
#
# The lane's own bundle is what a BARE skill name resolves in, and it is the
# shared module's answer for the install this lane ships in.


def _lane_skill_dir() -> Path:
    """The lane's own skill directory, ``{root}/{bundle}-{skill}`` or ``{bundle}/skills/{skill}``."""
    return Path(__file__).resolve().parents[1]


def _lane_skills_root() -> Path:
    """The ``skills/`` directory the lane itself ships in."""
    return Path(__file__).resolve().parents[2]


def _lane_bundle() -> str | None:
    """The bundle the lane ships in, used to resolve a bare skill name.

    Delegates to the shared reader, whose anchor is its own install — the same
    bundle and the same ``skills/`` root this lane ships beside. ``None`` means a
    flat deployment records no identity, so the caller refuses a bare name rather
    than probing a bundle that does not exist.
    """
    return spec_skills.installed_bundle(_lane_skill_dir())


def _skill_probe_paths(notation: str, lane_bundle: str) -> list[Path]:
    """Return every path the lane probes for *notation*, in probe order."""
    return spec_skills.skill_probe_paths(notation, lane_bundle, skills_root=_lane_skills_root(), anchor=Path(__file__))


def _skill_exists(notation: str, lane_bundle: str) -> bool:
    """Whether *notation* names a skill installed in any deployed layout."""
    return spec_skills.skill_exists(notation, lane_bundle, skills_root=_lane_skills_root(), anchor=Path(__file__))


_EXECUTOR_SKEW_MATCH = 'match'
_EXECUTOR_SKEW_SKEW = 'skew'
_EXECUTOR_SKEW_UNCHECKED = 'could_not_check'
#: The comparison cannot change the outcome, so it is not made — a source
#: checkout, where the executor dispatches the checkout's own scripts and the
#: lane text is that same checkout's text. Distinct from ``match``: nothing
#: agreed, because nothing was compared.
_EXECUTOR_SKEW_NOT_APPLICABLE = 'not_applicable'

#: Which leg of :func:`_lane_version_probe` answered — or failed to. The layout
#: decides which path the ``could_not_check`` reason names, so the operator's
#: remedy (no install stamp? no version directory? a broken executor?) follows
#: from the verdict instead of from a guess.
_LANE_LAYOUT_VERSIONED = 'versioned'
_LANE_LAYOUT_FLAT = 'flat'
_LANE_LAYOUT_NESTED = 'nested'
_LANE_LAYOUT_SOURCE_CHECKOUT = 'source_checkout'
_LANE_LAYOUT_UNRESOLVED = 'unresolved'


class _LaneTextVersion(NamedTuple):
    """The lane-text version probe: the version read, and where it looked.

    ``version`` is ``None`` when the comparison is UNMAKEABLE. ``probe`` is the
    path the answering leg read: the live version directory, the install stamp a
    flat install carries, the version-less bundle directory, or ``None`` when no
    install was found at all.
    """

    version: str | None
    layout: str
    probe: Path | None


def _lane_version_probe(skill_dir: Path | None = None) -> _LaneTextVersion:
    """Read the lane text's version, naming the leg that answered.

    The version comes from the LIVE install, never from the executing script's
    own path: a stale executor runs an older ``runbook_lane.py`` from its
    embedded path, so reading ``__file__``'s version would compare that stale
    version with itself and report ``match``.

    Which leg answers depends on the layout the harness deploys:

    * a versioned plugin cache supplies it from the newest eligible
      ``{bundle}/{version}/skills/{skill}`` directory
      (``select_live_version_dir`` — the shared selector the harness's own
      resolution follows);
    * a flat install (``{root}/skills/{bundle}-{skill}/``) carries no version
      directory, so it supplies the ``version`` of the sync's install stamp at
      the deploy root that contains its skill root, where the target's sync
      publishes one;
    * a source checkout carries neither, so its comparison stays UNMAKEABLE —
      and unnecessary: the executor dispatches that checkout's own scripts (see
      :func:`_is_source_checkout_bundle`), which is why the verdict for it is
      ``not_applicable`` rather than an answered comparison.

    The legs run in that order, and a leg that finds nothing leaves the probe to
    the next one. A flat install whose stamp is absent, unreadable or carries no
    version is UNMAKEABLE too — never "no skew". So is a stamp whose version the
    comparison cannot parse into a version key: a word such as ``unknown`` yields
    no key at all, so every executor would read as ``match`` — the fail-open
    direction this check exists to close.

    The stamp is written ONCE PER SYNC, so it witnesses what the sync deployed,
    not a lane text edited in place afterwards. That is the accepted trade: a
    flat install has no pin or registry, so what was deployed is what is loaded,
    and a per-skill version stamp or a content hash would be the only witnesses
    that also catch an in-place edit.
    """
    from deployed_layout import DIST_MANIFEST_NAME, flat_deploy_root, read_deploy_stamp_version
    from marketplace_bundles import resolve_bundles_root, select_live_version_dir
    from plugin_registry import version_key

    root = (skill_dir or _lane_skill_dir()).resolve()
    bundle = _lane_bundle()
    bundle_dir: Path | None = None
    if bundle:
        try:
            bundles_root: Path | None = resolve_bundles_root(root / 'SKILL.md')
        except Exception:
            bundles_root = None
        if bundles_root is not None and (bundles_root / bundle).is_dir():
            bundle_dir = bundles_root / bundle
            live = select_live_version_dir(
                bundle_dir, lambda version_dir: (version_dir / 'skills' / root.name / 'SKILL.md').is_file()
            )
            if live is not None:
                return _LaneTextVersion(live.name, _LANE_LAYOUT_VERSIONED, live)
    deploy_root = flat_deploy_root(root)
    if deploy_root is not None:
        stamped = read_deploy_stamp_version(deploy_root)
        comparable = stamped if stamped is not None and version_key(stamped) else None
        return _LaneTextVersion(comparable, _LANE_LAYOUT_FLAT, deploy_root / DIST_MANIFEST_NAME)
    if bundle_dir is not None:
        if _is_source_checkout_bundle(bundle_dir):
            return _LaneTextVersion(None, _LANE_LAYOUT_SOURCE_CHECKOUT, bundle_dir)
        return _LaneTextVersion(None, _LANE_LAYOUT_NESTED, bundle_dir)
    return _LaneTextVersion(None, _LANE_LAYOUT_UNRESOLVED, None)


def _is_source_checkout_bundle(bundle_dir: Path) -> bool:
    """Whether *bundle_dir* is a source checkout's bundle rather than a cache entry.

    The shape ``resolve_bundles_root`` already probes: a SOURCE checkout carries
    ``.claude-plugin/plugin.json`` DIRECTLY under the bundle
    (``marketplace/bundles/plan-marshall``), while a plugin cache carries it under
    ``{bundle}/{version}/`` and holds none directly.

    Reaching this check already means the versioned leg found no version
    directory carrying THIS skill, so ``resolve_bundle_path`` resolves the
    executor's mapping for it to the unversioned copy
    (``marketplace_bundles.resolve_bundle_path`` falls back to
    ``{bundle}/{subpath}``) — the checkout's own script. A cache-shaped bundle
    whose live version directory DOES carry the skill never reaches here: the
    versioned leg returns first.
    """
    return (bundle_dir / '.claude-plugin' / 'plugin.json').is_file()


def _lane_text_version(skill_dir: Path | None = None) -> str | None:
    """Return the version of the lane text a harness would load, or ``None``.

    ``None`` means the comparison is UNMAKEABLE, never that the versions agree.
    See :func:`_lane_version_probe` for which leg supplies the version on each
    layout and what a failed probe leaves behind.
    """
    return _lane_version_probe(skill_dir).version


def _unreadable_lane_text_reason(skill_dir: Path | None = None) -> str:
    """Name the thing a ``could_not_check`` could not read on the lane-text side.

    The cases name different remedies — a missing install stamp, a version
    directory whose name carries no version, a version-less nested install, and a
    directory that is neither — so the reason says which path was probed instead
    of one generic sentence.
    """
    probe = _lane_version_probe(skill_dir)
    if probe.layout == _LANE_LAYOUT_FLAT:
        return f'lane text version unknown: no usable version in the install stamp {probe.probe}'
    if probe.layout == _LANE_LAYOUT_VERSIONED:
        return f'lane text version unknown: the version directory {probe.probe} names no version key'
    if probe.layout == _LANE_LAYOUT_NESTED:
        return f'lane text version unknown: no version directory under {probe.probe}'
    if probe.layout == _LANE_LAYOUT_SOURCE_CHECKOUT:
        # The verdict is withheld, not the layout: this run executes a different
        # checkout, so its mapped script may lack a verb the probed text names.
        return (
            f'lane text version unknown: the probed source checkout {probe.probe} is not the checkout this run executes'
        )
    return 'lane text version unknown: no versioned install and no flat install stamp above the lane text'


def _probe_is_running_lane_tree(skill_dir: Path | None) -> bool:
    """Whether the probed lane skill directory IS the one this script runs from.

    This is the mapping check the ``not_applicable`` verdict rests on: the
    executor dispatches this notation to a file, and that file IS this script, so
    the executor's mapping is the probed checkout's own copy exactly when the
    probed skill directory is the script's own. Bundle containment is not enough —
    another skill in the same bundle is unrelated text this run does not execute,
    and excusing it would report a comparison nobody made. So is a source checkout
    probed from a different tree: its lane text may name a verb this run's mapped
    script lacks.
    """
    probed = skill_dir or _lane_skill_dir()
    try:
        return probed.resolve() == _lane_skill_dir()
    except OSError:
        return False


def _source_checkout_reason(skill_dir: Path | None = None) -> str:
    """Say why a source checkout needs no comparison, naming the tree that makes it true.

    The statement is about the MAPPING a source checkout produces, not about
    versions agreeing: the executor resolves this skill to the checkout's own
    script, so the lane text cannot name a verb its mapped script lacks.
    """
    probe = _lane_version_probe(skill_dir)
    return (
        'comparison not applicable: the lane text lives in a source checkout '
        f"({probe.probe}), where the executor maps the checkout's own scripts, "
        'so the lane text cannot name a verb those scripts lack'
    )


def _executor_skew(executor: Path, lane_skill_dir: Path | None = None, target: str | None = None) -> str:
    """Compare the executor's version with the lane text's version.

    The version is read through ``plugin_registry``'s shared executor reader,
    never by parsing the executor here. ``target`` names the harness the
    comparison is made FOR: a harness-independent executor carries a version per
    harness, so the verdict must be the one the RUNNING harness would reach — the
    same read that reports ``executor_version`` — or the reported fields and the
    verdict can disagree. Returns ``match`` when the executor is
    the same version or newer, ``skew`` when it is OLDER than the text this run
    read — the dangerous direction, where the text names verbs the executor's
    mapped script does not have — and ``could_not_check`` when either version
    cannot be read. ``could_not_check`` is deliberately not ``match``: a failed
    read must never be reported as agreement. A version the comparison cannot
    parse into a version key is such a failed read on either side: it would
    otherwise compare as the empty tuple and claim ``skew`` (or ``match``) for a
    comparison that was never made.

    A source checkout answers ``not_applicable`` instead of any of the three when
    there is no version to compare against: the executor maps that checkout's own
    scripts, so the lane text cannot name a verb the mapped script lacks, and the
    comparison would change nothing. That verdict needs a READABLE executor
    version first — an unreadable one is still ``could_not_check``, because the
    reason the lane must act on is then the executor's, not the layout's.
    """
    from plugin_registry import EXECUTOR_VERSION_FOUND, read_executor_version, version_key

    state, executor_version = read_executor_version(executor, target=target)
    if state != EXECUTOR_VERSION_FOUND or executor_version is None:
        return _EXECUTOR_SKEW_UNCHECKED
    if not version_key(executor_version):
        return _EXECUTOR_SKEW_UNCHECKED
    lane_version = _lane_text_version(lane_skill_dir)
    if lane_version is not None and version_key(lane_version):
        if version_key(executor_version) < version_key(lane_version):
            return _EXECUTOR_SKEW_SKEW
        return _EXECUTOR_SKEW_MATCH
    # No version to compare against. A source checkout is the one layout where
    # that is not a failed read but an unnecessary comparison — but only for the
    # tree this run actually executes, because only then is the executor's mapping
    # its own copy (see _probe_is_running_lane_tree). Every other unmakeable case
    # keeps the fail-closed verdict.
    if lane_version is None:
        probe = _lane_version_probe(lane_skill_dir)
        if probe.layout == _LANE_LAYOUT_SOURCE_CHECKOUT and _probe_is_running_lane_tree(lane_skill_dir):
            return _EXECUTOR_SKEW_NOT_APPLICABLE
    return _EXECUTOR_SKEW_UNCHECKED


def cmd_executor_skew(args: argparse.Namespace) -> dict[str, Any]:
    """Decide whether the executor may run the lane text this run read.

    Reports the verdict and both versions, so a ``skew`` can name them and the
    remedy. A comparison that cannot be made is ``could_not_check`` with its
    reason; the lane reports it and asks the operator instead of reading it as
    no skew. A source checkout answers ``not_applicable`` with the reason the
    comparison would change nothing, and the lane proceeds on it.
    """
    from plugin_registry import (
        EXECUTOR_VERSION_EMPTY,
        EXECUTOR_VERSION_FOUND,
        EXECUTOR_VERSION_NOT_FOUND,
        read_executor_version,
        version_key,
    )

    executor = Path(getattr(args, 'executor', None) or '.plan/execute-script.py')
    lane_skill_dir = Path(getattr(args, 'lane_dir', None) or _lane_skill_dir())
    # Ask as the RUNNING harness: a harness-independent executor carries a
    # version per harness, and the question here is whether THIS harness's run
    # would dispatch pre-fix code — not which harness wrote the file.
    runtime_harness = None
    try:
        from target_context import detect_target_from_env

        runtime_harness = detect_target_from_env()
    except Exception:
        runtime_harness = None
    state, executor_version = read_executor_version(executor, target=runtime_harness)
    lane_version = _lane_text_version(lane_skill_dir)
    verdict = _executor_skew(executor, lane_skill_dir, target=runtime_harness)
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
    elif verdict == _EXECUTOR_SKEW_NOT_APPLICABLE:
        result['reason'] = _source_checkout_reason(lane_skill_dir)
    elif verdict == _EXECUTOR_SKEW_UNCHECKED:
        # Name WHICH side could not be read: a file that was read but carries no
        # usable version is a different fact from an unreadable file, and the
        # operator's remedy differs. A readable but key-less executor version is
        # the executor's failure, so it must not be blamed on the lane text.
        if state != EXECUTOR_VERSION_FOUND:
            if state in (EXECUTOR_VERSION_EMPTY, EXECUTOR_VERSION_NOT_FOUND):
                result['reason'] = 'executor version missing or empty'
            else:
                result['reason'] = 'executor version unreadable'
        elif executor_version is None or not version_key(executor_version):
            result['reason'] = 'executor version names no version key'
        else:
            result['reason'] = _unreadable_lane_text_reason(lane_skill_dir)
    return result


def _resolve_deliverable_skills(spec: Path) -> dict[str, Any]:
    """Resolve every deliverable's named skills and persona, and verify each exists.

    Delegates to the shared reader with the lane's own bundle and ``skills/``
    anchor. A name that does not resolve to an installed skill is reported as
    missing so the run can stop and ask, rather than silently working without the
    standard it was told to apply.
    """
    return spec_skills.resolve_deliverable_skills(
        spec, _lane_bundle(), skills_root=_lane_skills_root(), anchor=Path(__file__), skill_dir=_lane_skill_dir()
    )


def _resolve_sonar(marshal: dict[str, Any]) -> dict[str, Any]:
    """Resolve the project's Sonar state from its own configuration.

    Returns ``{'state': 'configured', 'project_key': ...}`` for a project that
    analyses its pull requests with Sonar, and ``{'state': 'not_configured'}``
    for one that does not — the state in which the lane skips the open-finding read
    and nothing blocks. Read from ``credentials_config.{provider}``, the
    non-secret block ``manage-providers credentials edit --extra`` writes, so the
    resolve stays offline: no REST call, no credential-file read.

    Fails closed on a configuration it cannot read: a ``credentials_config``
    section or provider block that is not an object is ``sonar_config_unreadable``,
    and a provider block that carries no usable ``project_key`` is
    ``sonar_config_incomplete`` — never a silent ``not_configured``. A corrupt or
    half-written Sonar block must not drain as "this project does not use Sonar",
    which is the one state in which the open-finding read is skipped.
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

    The row carries ``review_complete_after_handling`` beside it, from the same
    record, so the lane reads one source for both: a flagged reviewer is done once
    its qualifying review is handled, with no re-trigger, wait or currency demand.
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
                'review_complete_after_handling': bot_registry.review_complete_after_handling(bot),
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

#: The whole CI configuration tree. The ignored-input guard reads this, not only the
#: workflow directory: a reusable workflow, an action definition or a config file
#: anywhere under it can carry the rule the delta is classified by.
_CI_CONFIG_DIR = ('.github',)

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

    A SYMLINK is never this checkout's rule. Containment in the checkout proves
    nothing about the verified commit — a tracked link can point at a file the head
    does not carry, or at an ignored path — so following it would decide the delta by
    bytes the graded tree never contained. Every link is skipped; the caller reports
    a discovery that found only links as an unreadable rule rather than as "no rule".
    """
    directory = project_dir.joinpath(*_CI_WORKFLOW_DIR)
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return []
    discovered: list[Path] = []
    for entry in entries:
        if entry.is_symlink():
            continue
        if not entry.is_file() or entry.suffix.lower() not in _WORKFLOW_SUFFIXES:
            continue
        discovered.append(entry)
    return discovered


def _workflow_discovery_problem(project_dir: Path, discovered: list[Path]) -> str | None:
    """Why workflow discovery could not read the project's rule, or ``None``.

    A directory that holds workflow-named entries while discovery returned none is a
    rule the lane could not read — every candidate was a symlink. Reporting it as
    "no CI rule" would hand the decision to the architecture fallback, which is a
    different rule from the one the project's CI applies. A project with no workflow
    at all is ``None``: that genuinely has no CI footprint rule.
    """
    directory = project_dir.joinpath(*_CI_WORKFLOW_DIR)
    try:
        entries = sorted(entry for entry in directory.iterdir() if entry.suffix.lower() in _WORKFLOW_SUFFIXES)
    except OSError:
        return None
    if discovered or not entries:
        return None
    names = ', '.join(entry.name for entry in entries)
    return f'every workflow in this checkout is a symlink, so its rule cannot be read: {names}'


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
    workflows = _iter_workflow_files(project_dir)
    problem = _workflow_discovery_problem(project_dir, workflows)
    if problem is not None:
        return [], None, problem
    for workflow in workflows:
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
    builds, even when the architecture files a documentation module over it. A
    path in NEITHER class is buildable — the gate's own direction, since its
    opt-in names what to SKIP, not what to build.

    Under a CI that DELEGATES the rule to a reusable workflow (``source`` is
    ``ci-workflow`` and ``skip`` is ``None``) this function is not reached: the
    rule the CI applied is not in this checkout, so no architecture-derived
    substitute may stand in for it, and the caller builds every path with the
    delegation named. ``module_prefixes`` and the architecture fallback therefore
    apply only to a project whose CI has no footprint rule at all.
    """
    if any(_matches_glob(path, pattern) for pattern in extra):
        return 'buildable'
    if source == 'ci-workflow':
        return 'docs-only' if any(_matches_glob(path, pattern) for pattern in skip or []) else 'buildable'
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


def _classify_paths(project_dir: Path, paths: list[str]) -> tuple[list[dict[str, Any]], str, str]:
    """Classify *paths* with the PROJECT's own footprint rule.

    Returns ``(rows, source, reason)``. ``source`` is ``ci-workflow`` when the
    checkout holds the rule and ``architecture`` when it does not. A non-empty
    ``reason`` means the rule could not be read at all: every path is then
    ``buildable`` (skip nothing) and the caller reports why, so an unreadable rule
    costs a local build rather than a skipped CI one.

    One seam for both consumers of the rule — the build gate and the stale-analysis
    carry-forward — because two copies of it would let one skip what the other
    builds.
    """
    extra, skip, reason = _read_footprint_rule(project_dir)
    if extra is not None:
        source = 'ci-workflow'
        module_prefixes: list[str] = []
    else:
        source = 'architecture'
        module_prefixes = _architecture_module_prefixes(project_dir) or ['']
    doc_surfaces = _architecture_documentation_surfaces(project_dir)

    if reason:
        return [{'path': path, 'kind': 'buildable'} for path in paths], source, reason
    if source == 'ci-workflow' and skip is None:
        # The workflow opts in but holds no rule: it DELEGATES the footprint rule to a
        # reusable workflow this checkout does not hold. Substituting the architecture's
        # documentation surfaces would decide the delta by a rule the CI never applied,
        # and a wrong docs-only answer SKIPS a build the CI runs — the one direction this
        # gate must never take. Every path builds, and the delegation is named.
        return (
            [{'path': path, 'kind': 'buildable'} for path in paths],
            source,
            'the CI delegates its footprint rule to a reusable workflow this checkout does not hold',
        )
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
        return (
            [{'path': path, 'kind': 'buildable'} for path in paths],
            source,
            f'glob helper unavailable: {exc}',
        )
    return rows, source, ''


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

    rows, source, reason = _classify_paths(project_dir, paths)
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


# =============================================================================
# sonar-stale-delta — a stale analysis whose delta the project does not build
# =============================================================================

#: The name a carried-forward read's verdict carries: the delta between the
#: analysed head and the head was positively classified as a path set the project
#: does not build, so the enumeration of the analysed head stands in for this
#: head's. A distinct name, so a carried-forward figure never reads like a
#: measurement of the current head.
_CARRY_FORWARD_UNBUILT = 'carried_forward_unbuilt_delta'

#: The prefix the READ gives its own ``count_status_reason`` when the figure was carried
#: forward. It is the token that binds the gate and the facts to the read: a reason with
#: this prefix and no marking is refused, so a carried-forward figure cannot be reported
#: as this head's measurement.
_CARRY_FORWARD_REASON_PREFIX = 'carried_forward'


def _git_in(worktree: Path, *args: str) -> tuple[bool, str]:
    """Run one git command against *worktree*; return ``(ok, stdout)``.

    ``ok`` is ``False`` for a non-zero exit AND for a command that could not be
    started at all, so a caller never reads absent output as an empty answer.
    """
    import subprocess

    try:
        completed = subprocess.run(
            ['git', '-C', str(worktree), *args],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False, ''
    if completed.returncode != 0:
        return False, ''
    return True, completed.stdout


def _resolve_commit(worktree: Path, revision: str) -> str:
    """Return the commit *revision* names in *worktree*, or ``''``.

    An unresolvable revision — one the checkout does not hold, a branch that was
    force-pushed away — is the empty string, which the caller reads as "cannot
    decide" and never as "nothing changed".
    """
    if not revision.strip():
        return ''
    ok, out = _git_in(worktree, 'rev-parse', '--verify', '--quiet', f'{revision}^{{commit}}')
    return out.strip() if ok else ''


def _checkout_revision(worktree: Path) -> str:
    """Return the commit *worktree* has checked out, or ``''``.

    The footprint rule is read from the worktree's FILES, so the commit it holds
    is part of that read: a rule from another commit is not the head's rule.
    """
    ok, out = _git_in(worktree, 'rev-parse', 'HEAD')
    return out.strip() if ok else ''


def _worktree_is_clean(worktree: Path) -> bool | None:
    """Whether *worktree* carries no change the head does not; ``None`` if unreadable.

    The footprint rule is read from the worktree's FILES, so a modified or untracked
    file is a rule the head does not carry — a checkout on the right commit with a
    rewritten workflow would otherwise decide the delta under a rule nothing
    committed. Two shapes hide from a bare ``git status``: an ``assume-unchanged`` or
    ``skip-worktree`` entry (git reports it clean whatever its content), and an
    untracked file when ``status.showUntrackedFiles`` is ``no``. Both are read
    explicitly, because either would let a local edit present a rule the head lacks.
    """
    ok, out = _git_in(worktree, 'status', '--porcelain', '--untracked-files=normal')
    if not ok:
        return None
    if out.strip():
        return False
    ok, tags = _git_in(worktree, 'ls-files', '-v')
    if not ok:
        return None
    return not any(_entry_hides_its_change(line) for line in tags.splitlines())


def _entry_hides_its_change(line: str) -> bool:
    """Whether an ``ls-files -v`` line marks an entry git will not report as changed.

    ``ls-files -v`` prefixes each path with a tag: a LOWERCASE tag means
    assume-unchanged, and ``S`` means skip-worktree. Either makes ``git status``
    silent about a modified file, so the file can carry a rule the head does not.
    """
    tag = line[:1]
    return bool(tag) and (tag.islower() or tag == 'S')


def _ignored_workflow_inputs(worktree: Path) -> list[str] | None:
    """Return ignored-untracked files under the CI config tree, or ``None``.

    ``git status --porcelain`` omits ignored paths, but the footprint rule is read
    from the DIRECTORY, so an ignored CI file is a rule the head does not carry. The
    guard covers the whole ``.github`` tree, not only ``workflows``: a reusable
    workflow or an action definition there supplies the same rule. ``None`` says the
    read itself failed, which is not "none found".
    """
    ok, out = _git_in(
        worktree,
        'ls-files',
        '--others',
        '--ignored',
        '--exclude-standard',
        '--',
        '/'.join(_CI_CONFIG_DIR),
    )
    if not ok:
        return None
    return [line.strip() for line in out.splitlines() if line.strip()]


def _delta_paths(worktree: Path, base: str, head: str) -> list[str] | None:
    """Return the paths that changed from *base* to *head*, or ``None``.

    ``None`` is the load-bearing answer: it says the change could not be listed,
    which is never read as an empty change. Renames are not followed, so a rename
    reports both its source and its destination. ``-z`` is what keeps a path Git
    would otherwise quote (a non-ASCII or control character in it) intact: the
    quoted form would not match a module prefix, and the veto would then miss a
    change inside a built module.
    """
    ok, out = _git_in(worktree, 'diff', '--name-only', '--no-renames', '-z', base, head)
    if not ok:
        return None
    return [path for path in out.split('\0') if path]


# =============================================================================
# Stale-delta refusals a project's own rule cannot decide are NOT carried
# =============================================================================


def _stale_delta_revisions(worktree: Path, analysis_revision: str, head_revision: str) -> tuple[str, str, str | None]:
    """Resolve both revisions and verify the checkout presents the HEAD's own rule.

    Returns ``(analysed, head, detail)``. ``detail`` names why the decision cannot be
    made; when it is ``None`` both commits are the resolved OBJECT NAMES, so two
    spellings of one commit compare equal and a worktree carrying another commit's
    rule, a dirty tree, or an ignored CI input is refused before any classification.
    """
    if not worktree.is_dir():
        return '', '', f'worktree_unreadable: {worktree} is not a directory'
    analysed = _resolve_commit(worktree, analysis_revision)
    if not analysed:
        return (
            '',
            '',
            (f'revision_unresolvable: the analysed revision {analysis_revision} is not present in the routed checkout'),
        )
    head = _resolve_commit(worktree, head_revision)
    if not head:
        return (
            '',
            '',
            (f'revision_unresolvable: the head revision {head_revision} is not present in the routed checkout'),
        )
    if analysed == head:
        # The same commit on both sides is not a stale analysis at all, so the
        # carried-forward sentence would assert a difference that does not exist.
        return (
            analysed,
            head,
            (f'revisions_equal: analysed {analysis_revision} and head {head_revision} are the same commit'),
        )
    checkout = _checkout_revision(worktree)
    if checkout != head:
        # The rule that decides this delta is read from the worktree's files, so a
        # worktree on another commit carries another rule — and a rule from the
        # wrong commit can call a path unbuilt that the head builds.
        return (
            analysed,
            head,
            (
                f'worktree_not_at_head: the checkout is at {checkout or "an unreadable commit"} and the '
                f"head revision resolves to {head}; the footprint rule it carries is not the head's rule"
            ),
        )
    clean = _worktree_is_clean(worktree)
    if clean is None:
        return analysed, head, 'worktree_unreadable: the checkout status could not be read'
    if not clean:
        # A modified or untracked workflow file is a rule the head does not carry,
        # so the same fail-closed answer as a checkout on another commit.
        return (
            analysed,
            head,
            (
                'worktree_dirty: the checkout carries changed or untracked paths, so the rule it presents '
                'is not the rule at the head'
            ),
        )
    ignored = _ignored_workflow_inputs(worktree)
    if ignored is None:
        return analysed, head, 'worktree_unreadable: the ignored-path read of the workflow directory failed'
    if ignored:
        return (
            analysed,
            head,
            (
                'worktree_ignored_inputs: the CI configuration carries ignored files the head does not '
                f'carry ({", ".join(ignored)}), and the rule is read from the directory'
            ),
        )
    return analysed, head, None


def _sonar_stale_delta_verdict(
    state: str,
    count_status: str | None,
    analysis_revision: str,
    head_revision: str,
    worktree: Path,
) -> dict[str, Any]:
    """Decide whether a stale analysis is the read for this head.

    The case this exists for: a head the project's CI deliberately never analyses
    (``skip-on-docs-only``), where the pull-request analysis stays on an earlier
    head forever. Retrying that read can never succeed, so the lane decides it
    from the analysed head instead.

    Fail-closed is the whole design: the delta must be one the project does not
    build, and the project's own rule is the only thing that can say so. Every
    changed path is classified with that rule (its CI workflow's skip globs, or its
    architecture's documentation surfaces), and one ``buildable`` path refuses the
    carry-forward. A project whose CI delegates its build to a reusable workflow
    holds no such rule, so the delegated case is not decided here. An unresolvable
    revision, an unlistable diff, an unreadable rule and a single buildable path all
    answer ``carry_forward: false`` with the lane's own ``undecidable_read``, which is
    the state the merge gate already refuses.
    """
    verdict: dict[str, Any] = {
        'status': 'success',
        'operation': 'sonar-stale-delta',
        'state': state,
        'count_status': count_status or '',
        'carry_forward': False,
        'reason': 'undecidable_read',
        'analysis_revision': analysis_revision,
        'head_revision': head_revision,
    }
    if state == 'not_configured':
        verdict['reason'] = 'not_configured'
        return verdict
    if count_status != 'undecidable':
        # A confirmed or unconfigured read is not the case this decides; only a
        # stale analysis is carried forward, never a settled one.
        verdict['reason'] = 'count_status_not_stale'
        return verdict
    if not analysis_revision or not head_revision:
        verdict['detail'] = 'revision_missing: both revisions must be reported to decide a carried-forward read'
        return verdict

    analysed, head, detail = _stale_delta_revisions(worktree, analysis_revision, head_revision)
    if detail is not None:
        verdict['detail'] = detail
        return verdict

    paths = _delta_paths(worktree, analysed, head)
    if paths is None:
        verdict['detail'] = f'diff_failed: the change from {analysis_revision} to {head_revision} could not be listed'
        return verdict
    verdict['changed_paths'] = paths
    rule_paths = [path for path in paths if path == _CI_CONFIG_DIR[0] or path.startswith(f'{_CI_CONFIG_DIR[0]}/')]
    if rule_paths:
        # A head that edits the CI rule can widen its own paths-ignore, so the rule read
        # from THAT head is not the rule that would have judged the source change it
        # carries — carrying it forward would excuse a change by a rule it wrote itself.
        verdict['detail'] = (
            'rule_changed: the delta changes the CI configuration the footprint rule is read from '
            f'({", ".join(rule_paths)}), so the change cannot be carried forward'
        )
        return verdict
    if not paths:
        verdict['carry_forward'] = True
        verdict['source'] = 'none'
        verdict['reason'] = (
            f'{_CARRY_FORWARD_UNBUILT}: analysed {analysis_revision} != head {head_revision}; '
            'the delta since the analysed head is empty'
        )
        return verdict

    rows, source, rule_reason = _classify_paths(worktree, paths)
    verdict['source'] = source
    if rule_reason:
        # A rule that could not be read is not a rule that skips nothing: every
        # path is buildable, so the read stays undecidable rather than carried.
        verdict['detail'] = f'rule_unreadable: {rule_reason}'
        return verdict
    buildable = [row['path'] for row in rows if row['kind'] == 'buildable']
    if buildable:
        verdict['buildable_paths'] = buildable
        verdict['detail'] = (
            f'delta_buildable: {len(buildable)} of {len(paths)} changed path(s) are paths the project builds'
        )
        return verdict

    verdict['carry_forward'] = True
    verdict['reason'] = (
        f'{_CARRY_FORWARD_UNBUILT}: analysed {analysis_revision} != head {head_revision}; '
        'the delta since the analysed head is not built'
    )
    return verdict


def cmd_sonar_stale_delta(args: argparse.Namespace) -> dict[str, Any]:
    """Report whether a stale Sonar analysis may stand as this head's read."""
    state = getattr(args, 'state', None)
    if state not in _SONAR_STATES:
        return {
            'status': 'error',
            'error': 'invalid_sonar_state',
            'message': f'--state must be one of {", ".join(_SONAR_STATES)}; got {state!r}',
        }
    count_status = getattr(args, 'count_status', None)
    if state == 'configured':
        if count_status not in _SONAR_COUNT_STATUSES:
            return {
                'status': 'error',
                'error': 'invalid_count_status',
                'message': (
                    f'--count-status must be one of {", ".join(_SONAR_COUNT_STATUSES)} '
                    f'when --state configured; got {count_status!r}'
                ),
            }
    elif count_status is not None:
        return {
            'status': 'error',
            'error': 'state_contradicts_read',
            'message': 'a not_configured state carries no read; drop --count-status',
        }
    elif getattr(args, 'analysis_revision', None) is not None or getattr(args, 'head_revision', None) is not None:
        # Symmetric with the other two Sonar verbs: a project with no Sonar has no
        # read, so revisions beside `not_configured` are a contradiction rather
        # than an input the verb silently ignores.
        return {
            'status': 'error',
            'error': 'state_contradicts_read',
            'message': (
                'a not_configured state carries no read; drop --count-status, --analysis-revision and --head-revision'
            ),
        }
    worktree = Path(getattr(args, 'worktree', None) or '.').resolve()
    return _sonar_stale_delta_verdict(
        state,
        count_status,
        (getattr(args, 'analysis_revision', '') or '').strip(),
        (getattr(args, 'head_revision', '') or '').strip(),
        worktree,
    )


def _operator_selection_records(progress_file: Path) -> set[str] | None:
    """Return the finding keys the progress file records as OPERATOR-selected.

    The lane writes one line per selection, ``operator-selected: {key}: {reason}``
    (section 6 step 4). Reading them back is what turns "the lane passed a key" into
    "the run recorded the operator's answer naming that key": a key the lane types
    into ``--operator-selected-keys`` without that record is refused. The record is
    still lane-written, so this makes a violation VISIBLE in the audit trail rather
    than impossible; the spec's own dismissal rule is an operator answer, and this is
    the strongest witness a plan-less lane has.

    ``None`` when the file cannot be read — a caller that named no file makes no
    cross-check, and a caller that named one it cannot read gets the strict answer
    (no key is recorded) rather than a silent pass.
    """
    try:
        text = progress_file.read_text(encoding='utf-8')
    except OSError:
        return set()
    recorded: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(_OPERATOR_SELECTION_PREFIX):
            continue
        tail = stripped[len(_OPERATOR_SELECTION_PREFIX) :].strip()
        key = tail.split(':', 1)[0].strip()
        if key:
            recorded.add(key)
    return recorded


#: A revision is a hexadecimal OBJECT NAME — the thing the gate's pair and the facts'
#: marking stand on. A ref expression (``HEAD~1``), a branch name or a date is not a
#: revision, so it is refused rather than compared as one.
_REVISION_RE = re.compile(r'[0-9a-fA-F]{7,64}')

#: The shortest prefix this lane treats as naming a commit on its own.
_MIN_REVISION_PREFIX = 7


def _same_revision(one: str, other: str) -> bool:
    """Whether two spellings name ONE commit: identical, or one a hex prefix of the other.

    A short SHA and the full object name of the same commit are one revision, so a
    string comparison would report a carried-forward pair that does not exist.
    """
    if not one or not other:
        return False
    left, right = one.strip().lower(), other.strip().lower()
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    return (
        len(shorter) >= _MIN_REVISION_PREFIX
        and longer.startswith(shorter)
        and re.fullmatch(r'[0-9a-f]+', shorter) is not None
    )


def _carried_forward_revisions(
    args: argparse.Namespace,
) -> tuple[tuple[str, str] | None, dict[str, Any] | None]:
    """Read the carried-forward marking and its revision pair, or refuse them.

    A carried-forward read is licensed by THREE facts that only make sense
    together: the read's own ``carried_forward`` marker, the analysed revision the
    enumeration was measured at, and the head it stands in for. The marker is
    caller-asserted, and what it closes is one direction only: the revision pair
    ALONE no longer renames a verdict, so a caller following the documented chain
    cannot pass a carried-forward rename without saying so. It does not prove the
    read was carried forward — a caller that invents all three still gets the
    rename — and it does not stop a plain figure being reported plainly. One
    revision alone describes no read either, so it is refused rather than
    half-recorded, and the pair is refused on any read that is not a confirmed
    enumeration — the carry-forward renames a measured figure, never a failed one.
    """
    marked = bool(getattr(args, 'carried_forward', False))
    analysed = (getattr(args, 'carried_forward_analysis_revision', None) or '').strip()
    head = (getattr(args, 'carried_forward_head_revision', None) or '').strip()
    if not marked and not analysed and not head:
        return None, None
    if not marked:
        return None, {
            'status': 'error',
            'error': 'carried_forward_unmarked',
            'message': (
                "a carried-forward figure carries the read's own `carried_forward: true` marker: pass "
                '--carried-forward beside --carried-forward-analysis-revision and '
                '--carried-forward-head-revision, never the revision pair alone'
            ),
        }
    if not analysed:
        return None, {
            'status': 'error',
            'error': 'carried_forward_incomplete',
            'message': (
                'a carried-forward read names both revisions: '
                '--carried-forward-analysis-revision and --carried-forward-head-revision'
            ),
        }
    if getattr(args, 'count_status', None) != 'confirmed':
        return None, {
            'status': 'error',
            'error': 'carried_forward_requires_confirmed',
            'message': (
                'a carried-forward read is a confirmed enumeration of the analysed head; '
                f'--count-status is {getattr(args, "count_status", None)!r}'
            ),
        }
    if not head:
        return None, {
            'status': 'error',
            'error': 'carried_forward_incomplete',
            'message': (
                'a carried-forward read names both revisions: '
                '--carried-forward-analysis-revision and --carried-forward-head-revision'
            ),
        }
    for value in (analysed, head):
        if _REVISION_RE.fullmatch(value) is None:
            return None, {
                'status': 'error',
                'error': 'revision_format_invalid',
                'message': (f'a carried-forward revision is a hexadecimal object name: {value!r} is not one'),
            }
    if _same_revision(analysed, head):
        # Two spellings of ONE commit describe a settled read, not a carried-forward one:
        # the verdict would assert a difference that does not exist.
        return None, {
            'status': 'error',
            'error': 'carried_forward_revisions_equal',
            'message': (
                'the carried-forward analysed revision and head revision are the same commit; '
                'a carried-forward read names the head an earlier analysis is standing in for'
            ),
        }
    return (analysed, head), None


def _carried_forward(
    verdict: dict[str, Any],
    carried_forward: tuple[str, str] | None,
    reason: str = '',
) -> dict[str, Any]:
    """Re-name an ADMITTING verdict as a carried-forward read.

    A carried-forward figure is a measured figure of an EARLIER head, so a verdict
    that admitted it on ``no_open_issues`` would read like a measurement of this
    one. The distinct name carries both revisions and the fact that the delta was
    not built, so the landing and the operator see which head was counted. When the
    read's OWN ``count_status_reason`` is supplied it is used instead of the default
    sentence, so an empty delta is not described as one the project does not build.
    """
    if carried_forward is None or not verdict.get('merge_allowed'):
        return verdict
    analysed, head = carried_forward
    verdict['reason'] = reason.strip() or (
        f'{_CARRY_FORWARD_UNBUILT}: analysed {analysed} != head {head}; the delta since the analysed head is not built'
    )
    verdict['carried_forward'] = True
    verdict['analysis_revision'] = analysed
    verdict['head_revision'] = head
    return verdict


def _sonar_gate_verdict(
    state: str,
    count_status: str | None,
    open_count: int | None,
    open_keys: list[str],
    selected_keys: list[str],
    recorded_keys: set[str] | None = None,
    hotspot_keys: list[str] | None = None,
    carried_forward: tuple[str, str] | None = None,
    carried_forward_reason: str = '',
) -> dict[str, Any]:
    """Decide whether the Sonar read admits the merge (section 7's condition).

    The verdict is a pure function of the read and of the OPERATOR'S selection,
    so the lane's merge condition is a decision a script makes rather than a
    judgement a reader re-derives:

    - ``not_configured`` — the project does not analyse with Sonar, so there is
      no open-finding condition to satisfy.
    - ``undecidable`` — the read never settled. This is a BLOCKER, never a ``0``:
      no count and no key set were observed, so "no open findings" is unknowable.
    - ``unconfigured`` — resolve said ``configured`` and the read could not
      authenticate. Also a blocker: the credentials the project claims are not
      usable, which is a defect nobody would otherwise see.
    - ``confirmed`` — admitted when the count is ``0``, or when every open key
      the read enumerated is one the OPERATOR selected for dismissal. The lane
      never records a dismissal itself: a finding stays open unless the operator
      named its key, so a gate that accepted the lane's own list would let the
      run dismiss its own findings. A count with no enumerated key set cannot be
      verified key by key, so it is refused rather than passed on the count
      alone.
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
        return _carried_forward(
            {
                'status': 'success',
                'operation': 'sonar-gate',
                'merge_allowed': True,
                'reason': 'no_open_issues',
                'open_issue_count': 0,
            },
            carried_forward,
            carried_forward_reason,
        )
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
    selected = set(selected_keys)
    unselected = [key for key in open_keys if key not in selected]
    if unselected:
        return {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': False,
            'reason': 'open_issues_not_operator_selected',
            'open_issue_count': count,
            'unselected_keys': unselected,
        }
    undismissable = [key for key in (hotspot_keys or []) if key in selected]
    if undismissable:
        # A security hotspot has no transition verb, so a "dismissal" of one would
        # be recorded and never transmitted. The lane's rule is that a hotspot is
        # FIXED or reported as a blocker, and this is the gate saying so.
        return {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': False,
            'reason': 'hotspot_not_dismissable',
            'open_issue_count': count,
            'hotspot_keys': undismissable,
        }
    if recorded_keys is not None:
        unrecorded = [key for key in open_keys if key not in recorded_keys]
        if unrecorded:
            # The keys are supplied, but the run never recorded the operator's
            # answer naming them. The gate cannot tell a selection from a list the
            # lane invented, so it admits only what the progress file witnesses.
            return {
                'status': 'success',
                'operation': 'sonar-gate',
                'merge_allowed': False,
                'reason': 'selection_not_recorded',
                'open_issue_count': count,
                'unrecorded_keys': unrecorded,
            }
    return _carried_forward(
        {
            'status': 'success',
            'operation': 'sonar-gate',
            'merge_allowed': True,
            'reason': 'all_open_issues_operator_selected',
            'open_issue_count': count,
            'selected_count': len(selected),
        },
        carried_forward,
        carried_forward_reason,
    )


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
    if getattr(args, 'dismissed_keys', None) is not None:
        # The tombstone for the retired surface: a lane-recorded dismissal is no
        # longer an input at all, and refusing it by name says WHY rather than
        # letting argparse report an unknown flag.
        return {
            'status': 'error',
            'error': 'lane_dismissal_not_accepted',
            'message': (
                "a dismissal needs the operator's selection: pass the keys the operator named with "
                '--operator-selected-keys, never a list the lane recorded itself'
            ),
        }
    if state == 'not_configured':
        # A read state supplied beside `not_configured` is a contradiction: a
        # project with no Sonar has no read to report. Refuse it rather than let a
        # stale count ride an "allowed" verdict. Every read flag is checked, not
        # only the two count flags: `--open-keys` and `--operator-selected-keys`
        # describe the same read, so dropping one silently would report
        # `merge_allowed: true` for a project whose findings nobody looked at.
        if (
            count_status is not None
            or open_count is not None
            or getattr(args, 'open_keys', None) is not None
            or getattr(args, 'operator_selected_keys', None) is not None
            or getattr(args, 'hotspot_keys', None) is not None
            or getattr(args, 'carried_forward', None)
            or getattr(args, 'carried_forward_analysis_revision', None) is not None
            or getattr(args, 'carried_forward_head_revision', None) is not None
            or getattr(args, 'count_status_reason', None) is not None
        ):
            return {
                'status': 'error',
                'error': 'state_contradicts_read',
                'message': (
                    'a not_configured state carries no read; drop --count-status, --open-count, '
                    '--open-keys, --operator-selected-keys, --hotspot-keys, --carried-forward, the '
                    '--carried-forward-* revisions and --count-status-reason'
                ),
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
    carried_forward_revisions, carried_forward_error = _carried_forward_revisions(args)
    if carried_forward_error is not None:
        return carried_forward_error
    count_status_reason = (getattr(args, 'count_status_reason', None) or '').strip()
    if count_status_reason.startswith(_CARRY_FORWARD_REASON_PREFIX) and carried_forward_revisions is None:
        # The read's OWN output says it was carried forward, so a figure reported
        # without the marking would read as a measurement of this head.
        return {
            'status': 'error',
            'error': 'carried_forward_unmarked',
            'message': (
                "the read's count_status_reason names a carry-forward: pass --carried-forward beside "
                '--carried-forward-analysis-revision and --carried-forward-head-revision, so the '
                'verdict cannot state a figure of another head as this head'
            ),
        }
    if getattr(args, 'operator_selected_keys', None) and not getattr(args, 'progress_file', None):
        # A selection with no record behind it is exactly the self-attested
        # dismissal this gate exists to remove. The flag alone is the lane's word;
        # the progress file is the witness, so it is not optional when a key is
        # claimed.
        return {
            'status': 'error',
            'error': 'progress_file_required',
            'message': (
                '--operator-selected-keys needs --progress-file: the key must be recorded as an '
                'operator-selected line in the run, or the gate cannot tell a selection from a list '
                'the lane invented'
            ),
        }
    if (
        count_status == 'confirmed'
        and isinstance(open_count, int)
        and open_count > 0
        and _split_csv(getattr(args, 'operator_selected_keys', None))
        and getattr(args, 'hotspot_keys', None) is None
    ):
        # Without the hotspot set the gate cannot tell a selected hotspot from a
        # selected issue, so omitting the flag would let a hotspot through. An
        # EMPTY value is the answer for a read that found none — required means
        # stated, not non-empty.
        return {
            'status': 'error',
            'error': 'hotspot_keys_required',
            'message': (
                "--hotspot-keys is required when selecting open findings: pass the read's hotspot "
                'keys, or an explicit empty value when it reported none'
            ),
        }
    return _sonar_gate_verdict(
        state,
        count_status,
        open_count,
        _split_csv(getattr(args, 'open_keys', None)),
        _split_csv(getattr(args, 'operator_selected_keys', None)),
        _progress_selection(getattr(args, 'progress_file', None)),
        _split_csv(getattr(args, 'hotspot_keys', None)),
        carried_forward_revisions,
        count_status_reason,
    )


def _progress_selection(value: str | None) -> set[str] | None:
    """Resolve ``--progress-file`` to the recorded operator selections, or ``None``.

    ``None`` means the caller named no file, so no cross-check is made. A file that
    was named is READ; one that cannot be read answers the empty set, which refuses
    every selection rather than waving it through.
    """
    if not value:
        return None
    return _operator_selection_records(Path(value))


def cmd_sonar_facts(args: argparse.Namespace) -> dict[str, Any]:
    """Render the landing's Sonar facts from the read taken at the merge head.

    The COUNT is the landing's required ``sonar_open_new_issues`` key — one
    spelling for one measurement, so the gate, the facts and the schema cannot
    drift apart — and the RULES it left open ride the OPTIONAL per-step channel
    (``step.sonar-roundtrip.open_issue_rules``) beside it.

    The two sentinels are the point of the verb. A confirmed read carries the
    MEASURED count. An ``undecidable`` read carries ``unknown`` — a failed read
    asserts that nothing was observed and never collapses into ``0``, which is a
    claim the run did not earn. A project without Sonar carries ``n/a``, the
    answered absence, which is a legal value for the required count.

    ``--rules`` is required above zero because a count with no rule beside it
    renders as "3 open findings, no rule left open" — a figure whose other half is
    missing. A security hotspot carries no rule, so a read whose only open findings
    are hotspots passes the literal ``hotspot`` and the fact states exactly that.
    """
    state = getattr(args, 'state', None)
    if state not in _SONAR_STATES:
        return {
            'status': 'error',
            'error': 'invalid_sonar_state',
            'message': f'--state must be one of {", ".join(_SONAR_STATES)}; got {state!r}',
        }

    # Assigned on both branches so the analysed-revision guard below can read it
    # without a branch-dependent rebind.
    count_status = None
    if state == 'not_configured':
        # Symmetric with the gate: a read supplied beside `not_configured` is a
        # contradiction, and rendering `n/a` over it would hide that the caller
        # read one project's issues and reported another project's state.
        if any(
            getattr(args, name, None) is not None
            for name in (
                'count_status',
                'count_status_reason',
                'open_count',
                'rules',
                'gate_status',
                'analysed_revision',
                'carried_forward_head_revision',
            )
        ) or getattr(args, 'carried_forward', False):
            return {
                'status': 'error',
                'error': 'state_contradicts_read',
                'message': (
                    'a not_configured state carries no read; drop --count-status, --count-status-reason, '
                    '--open-count, --rules, --gate-status, --carried-forward and the carried-forward revisions'
                ),
            }
        count, rules = 'n/a', 'n/a'
        gate_status = None
    else:
        count_status = getattr(args, 'count_status', None)
        gate_status = getattr(args, 'gate_status', None)
        if count_status not in _SONAR_COUNT_STATUSES:
            return {
                'status': 'error',
                'error': 'invalid_count_status',
                'message': (
                    f'--count-status must be one of {", ".join(_SONAR_COUNT_STATUSES)} when --state configured; '
                    f'got {count_status!r}'
                ),
            }
        if gate_status is not None and gate_status not in SONAR_GATE_STATUSES:
            return {
                'status': 'error',
                'error': 'invalid_gate_status',
                'message': (f'--gate-status must be one of {", ".join(SONAR_GATE_STATUSES)}; got {gate_status!r}'),
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

    fact_lines = [f'{_SONAR_OPEN_ISSUES_FACT}={count}', f'step.{_SONAR_FACT_STEP}.open_issue_rules={rules}']
    # A carried-forward figure is a figure of an EARLIER head, so the fact must say
    # three things together: that it is carried forward, which head was analysed and
    # which head it stands in for. The read's own marker is required — a figure
    # measured elsewhere must never render as this head's measurement.
    marked = bool(getattr(args, 'carried_forward', False))
    analysed_revision = (getattr(args, 'analysed_revision', None) or '').strip()
    carried_forward_head = (getattr(args, 'carried_forward_head_revision', None) or '').strip()
    count_status_reason = (getattr(args, 'count_status_reason', None) or '').strip()
    if count_status_reason.startswith(_CARRY_FORWARD_REASON_PREFIX) and not marked:
        # The read's own output names the carry-forward, so a figure rendered without the
        # marking would state another head's measurement as this head's.
        return {
            'status': 'error',
            'error': 'carried_forward_unmarked',
            'message': (
                "the read's count_status_reason names a carry-forward: pass --carried-forward beside "
                '--analysed-revision and --carried-forward-head-revision'
            ),
        }
    for value in (analysed_revision, carried_forward_head):
        if value and _REVISION_RE.fullmatch(value) is None:
            return {
                'status': 'error',
                'error': 'revision_format_invalid',
                'message': f'a carried-forward revision is a hexadecimal object name: {value!r} is not one',
            }
    if not marked and (analysed_revision or carried_forward_head):
        return {
            'status': 'error',
            'error': 'carried_forward_unmarked',
            'message': (
                "a carried-forward figure carries the read's own `carried_forward: true` marker: pass "
                '--carried-forward beside --analysed-revision and --carried-forward-head-revision'
            ),
        }
    if marked and not analysed_revision:
        return {
            'status': 'error',
            'error': 'carried_forward_incomplete',
            'message': (
                '--carried-forward names both revisions: --analysed-revision (measured at) and '
                '--carried-forward-head-revision (standing in for)'
            ),
        }
    if analysed_revision and count_status != 'confirmed':
        return {
            'status': 'error',
            'error': 'analysed_revision_requires_confirmed',
            'message': (
                '--analysed-revision names the head a confirmed figure was measured at; '
                f'--count-status is {count_status!r}, which measured nothing'
            ),
        }
    if marked and not carried_forward_head:
        return {
            'status': 'error',
            'error': 'carried_forward_incomplete',
            'message': (
                '--carried-forward names both revisions: --analysed-revision (measured at) and '
                '--carried-forward-head-revision (standing in for)'
            ),
        }
    if analysed_revision and _same_revision(analysed_revision, carried_forward_head):
        # Two equal revisions describe a settled read, not a carried-forward one;
        # the fact would assert a difference that does not exist. The gate compares the
        # same way, so a short and a full SHA of one commit cannot pass here and be
        # refused there.
        return {
            'status': 'error',
            'error': 'carried_forward_revisions_equal',
            'message': (
                'the carried-forward analysed revision and head revision are the same commit; a '
                'carried-forward figure names the head an older analysis is standing in for'
            ),
        }
    if analysed_revision:
        fact_lines.append(f'step.{_SONAR_FACT_STEP}.analysed_revision={analysed_revision}')
        fact_lines.append(f'step.{_SONAR_FACT_STEP}.carried_forward_head_revision={carried_forward_head}')
        fact_lines.append(f'step.{_SONAR_FACT_STEP}.carried_forward=true')
    # The quality-gate fact is OPTIONAL and rides only when the caller read one:
    # a line asserting a state nothing observed would be worse than its absence.
    if gate_status is not None:
        fact_lines.append(f'{_SONAR_QUALITY_GATE_FACT}={gate_status}')

    return {
        'status': 'success',
        'operation': 'sonar-facts',
        'open_issue_count': count,
        'open_issue_rules': rules,
        'quality_gate_status': gate_status if gate_status is not None else 'not_read',
        'fact_lines': fact_lines,
    }


# =============================================================================
# review-gate — the review half of the merge gate
# =============================================================================

#: The review-body sections the gate reads out of a reviewer's review body.
#:
#: Each row is ``(label prefix, canonical section)``, and the label is matched as
#: a case-insensitive PREFIX of the ``<summary>`` title the reviewer's own markup
#: puts above the block. The trailing decoration a reviewer adds — a leading
#: emoji, a ``(N)`` count — is stripped before the match, so one label covers
#: every rendering of that heading.
#:
#: ``inline`` is listed beside the three body-only sections on purpose: the
#: reviewer states its inline findings in the body as a count line even though
#: they also arrive as threads, and a finding it declares belongs in the
#: disposition ledger whichever surface carries it.
_REVIEW_BODY_SECTIONS = (
    ('actionable comments', 'inline'),
    ('inline comments', 'inline'),
    ('duplicate comments', 'duplicate'),
    ('outside diff range comments', 'outside-diff'),
    ('outside-diff comments', 'outside-diff'),
    ('nitpick comments', 'nitpick'),
    ('nitpicks', 'nitpick'),
    ('follow-ups', 'followup'),
    ('followups', 'followup'),
    ('additional comments', 'additional'),
    # REPORTED (not captured here) from a consumer repository's review body as a
    # `<picture>`-prefixed counted title (`Minor comments: 25`): one finding row per item,
    # so the block holds findings and its declared count is theirs. It is NOT boilerplate,
    # and reading it as such is what left that pull request unmergeable.
    ('minor comments', 'minor'),
)

#: The ``<summary>`` titles a reviewer posts that COUNT their block while the block
#: is not a findings section — the boilerplate a reviewer renders beside its
#: findings. Matched as a case-insensitive PREFIX of the normalised title, like the
#: section table.
#:
#: Every entry is grounded: ``review info``, ``run configuration``, ``commits`` and
#: ``files selected for processing`` are OBSERVED as titles in the review body of
#: ``cuioss/plan-marshall#1940`` (review ``PRR_kwDOQ3xasM8AAAABWsFY6g``) — the file
#: list is the one that carries a declared count there (``: 19``), and the other
#: three carry none; ``review details`` is the block the automatic-review fixtures
#: render; ``files ignored due to path filters`` is the spec-named sibling of
#: the observed file list. A counted title that is none of these is COUNTED as
#: ``unclassified`` findings rather than declared away — and ``Additional comments (N)``
#: is deliberately NOT here: the capture does not carry it, the spec names the shape, and
#: a counted title that cannot be shown to be boilerplate is COUNTED as findings so a block
#: is never a false pass.
_NON_FINDING_SECTION_LABELS = (
    'files selected for processing',
    'files ignored due to path filters',
    # OBSERVED on ``cuioss/plan-marshall#1952`` in an INCREMENTAL review: the files the
    # reviewer skipped because they are unchanged since its previous review, posted as a
    # counted ``<details>`` block with a ``<picture>`` icon wrapper. It is a diagnostic
    # about what was NOT re-read, so it is neither a findings section nor a stop.
    'files skipped from review as they are similar to previous changes',
    # OBSERVED on ``cuioss/plan-marshall#1971`` in an INCREMENTAL review: the files that
    # carried no reviewable change in that pass, again a counted ``<details>`` block with
    # a ``<picture>`` icon wrapper and one file row per entry. A file list that names
    # nothing to review is not a findings section, so allowing it mints no ``unclassified``
    # findings — and, because it is a boundary, it cannot be absorbed into the section above.
    'files with no reviewable changes',
    'review details',
    'review info',
    'run configuration',
    'commits',
)

#: The markers that make a resolved thread's last BOT-authored comment an answer that
#: the concern REMAINS. A reviewer that closes a thread with an acknowledgement
#: ("Addressed in commit …", "verified", "fixed") matches none of these, so the
#: thread counts as handled; one that restates THIS thread's defect matches, so a
#: thread resolved to silence it is refused.
#:
#: Every marker names the thread's own defect in the present tense. A generic
#: "a separate concern remains" is deliberately NOT one: a reviewer that confirms a
#: fix and opens a NEW concern elsewhere in the same breath would otherwise leave a
#: resolved thread refused forever, and the new concern has its own thread.
_CONCERN_REMAINS_MARKERS = (
    'still applies',
    'still present',
    'still an issue',
    'still unresolved',
    'still not addressed',
    'not addressed',
    'remains unresolved',
)

_SUMMARY_RE = re.compile(r'<summary>(?P<title>.*?)</summary>', re.IGNORECASE | re.DOTALL)
#: The count a reviewer declares at the end of a ``<summary>`` title, in either
#: OBSERVED spelling: a parenthesised ``(N)`` (``Nitpick comments (2)``) or a
#: trailing ``: N`` (``Nitpick comments: 1``, and the per-file ``path: 1``). The
#: colon form needs whitespace after it, so a bare location (``src/a.py:12``) is not
#: a count.
_COUNT_SUFFIX_RE = re.compile(r'(?:\((?P<paren>\d+)\)|:\s+(?P<colon>\d+))\s*$')

#: What a count read does not need: markup and decoration AROUND the declared count.
#: The colon and the parentheses survive, because both spellings are counts.
_COUNT_TITLE_NOISE_RE = re.compile(r'[^a-z0-9\- ():]+')

#: The per-row finding marker the reviewer puts in a section's rows, OBSERVED on
#: ``cuioss/plan-marshall#1940`` (``<!-- cr-comment:v1:…``). A section that declares
#: no count states its findings one per marker, so the markers are its count.
_ROW_MARKER_RE = re.compile(r'<!--\s*cr-comment:v1:')

#: A ``<details>`` open or close tag, used to find the container a ``<summary>``
#: sits in.
_DETAILS_TOKEN_RE = re.compile(r'</?details\b[^>]*>', re.IGNORECASE)

#: The section an unrecognised COUNTED title's findings are minted under. A title this
#: parser cannot place is not a stop: a block the reviewer filled and counted holds
#: statements about this change, so its count is findings that must be disposed of
#: exactly like every other section's.
_UNCLASSIFIED_SECTION = 'unclassified'

#: A BOLD marker, and the span pairing this parser derives from the marker positions. A
#: reviewer writes a section heading in a second shape — OBSERVED on ``cuioss/plan-marshall#1983``
#: and ``#1984``, where ``**⚠️ Outside diff range comments (1)**`` heads a ``[!CAUTION]`` block
#: whose finding rides a ``<summary>`` row that declares no count of its own.
#:
#: Pairing is by MARKER ROLE, never a non-overlapping ``finditer`` over the whole body: one
#: stray ``**`` earlier in the body (``x **kwargs y **⚠️ Outside diff range comments (1)**``)
#: would spend a real heading's opening marker as the closing marker of the pair before it, and
#: the heading would never be read — an UNDER-count, the one direction this gate must never
#: take. An opener is the next CLOSING marker's partner (``_bold_spans``), so the heading is
#: read whatever an unpaired marker did earlier.
_BOLD_MARKER_RE = re.compile(r'\*\*')

#: The elements whose text is PROSE, never a heading: a finding's own row body (``<dd>``)
#: and an inline code sample (``<code>``). A reviewer quotes section headings inside them,
#: and reading such a quote as a heading would cut the enclosing section's span short — an
#: UNDER-count, the one direction this gate must never take. A region that is never closed
#: runs to the end of the BLOCK it sits in, which is the fail-safe direction.
_PROSE_TAG_RE = re.compile(r'<(?P<close>/?)(?P<name>dd|code)\b[^>]*>', re.IGNORECASE)

#: The count a normalised bold heading still carries after normalisation — removed before
#: the label comparison so a heading matches its label whichever spelling declared it.
_HEADING_TRAILING_COUNT_RE = re.compile(r'\s*(?:\(\d+\)|\d+)\s*$')

#: A BOLD span inside a Markdown code span is a QUOTE of the heading, not a heading: a
#: reviewer writes `` `**Outside diff range comments (1)**` `` when it discusses the rule.
#: Only a code span holding the heading and nothing else is read as that quotation, and the
#: spans are paired by RUN LENGTH (CommonMark's rule): a stray single backtick cannot close
#: on the first character of a doubled fence and leave the heading's own backticks paired
#: around it, which would hide a real heading (see ``_code_span_contents``).
_BACKTICK_RUN_RE = re.compile(r'`+')

#: A fenced code block's fence marker (``` or ~~~, three or more). A reviewer QUOTES
#: markup inside these fences — a suggested fix, a shell script, an HTML example —
#: and those bytes are prose about the change, never structure of the review. The
#: marker is matched anywhere rather than at a line start: the gate parses the
#: FLATTENED display form, where the newlines a fence opens on are already gone.
_FENCE_LINE_RE = re.compile(r'```+|~~~+')


def _mask_fenced_code(body: str) -> str:
    """Blank out fenced code blocks, keeping every offset in place.

    A `<details><summary>…</summary>` quoted inside a fence is an EXAMPLE: reading it
    as a real block minted phantom findings, and after the wrapper content check was
    narrowed it stopped the gate on CodeRabbit's own quoted snippet. Masking with
    spaces (never deleting) keeps every other offset — and therefore every span the
    callers compute — valid.
    """
    characters = list(body)
    open_at: int | None = None
    for fence in _FENCE_LINE_RE.finditer(body):
        if open_at is None:
            open_at = fence.start()
            continue
        for index in range(open_at, fence.end()):
            if characters[index] != '\n':
                characters[index] = ' '
        open_at = None
    return ''.join(characters)


#: The severity words a review ROW opens with, and the location marker it carries. A block
#: whose summary is a counted title continues a bold heading's ownership only when it looks
#: like a ROW; a bare counted title (`Potential issues (2)`) is a section of its own.
_ROW_SEVERITY_RE = re.compile(r'^(?:🟠|🟡|🔴|⚪|🟢)?\s*(?:major|minor|critical|trivial|info)\b', re.IGNORECASE)
_ROW_LOCATION_RE = re.compile(r'\b[\w./-]+\.[A-Za-z0-9]+\s*:\s*\d+')

#: The most findings the gate will enumerate for one section. A reviewer's declared count
#: is its own claim; a count above this is a body the gate refuses to materialize rather
#: than one it trusts, because enumerating it would exhaust the process before any verdict.
_MAX_ENUMERATED_FINDINGS = 1000


def _owned_blocks(body: str, heading_end: int) -> list[tuple[int, int]]:
    """Return the blocks a BOLD heading owns, as ``(open_offset, close_offset)`` spans.

    Ownership is an IDENTITY scoped to the heading's own depth AND to what sits between
    the heading and the block. Three mistakes are excluded, and each one is an under-count
    — the direction this gate must never take:

    - a bold span that merely MENTIONS a heading in prose (``**Outside diff range comments
      (1)** is empty this time.``) is not a heading over the block that follows, so the gap
      between the heading and the opener must carry no prose word;
    - a block whose own opening ``<summary>`` names a findings section belongs to that
      section, not to the bold line above it;
    - a bold label line that closes the block it sits in owns nothing that follows, and a
      block with no matching close owns nothing at all — running either to the end of the
      body would swallow every section after it.

    Sibling blocks at the heading's level are claimed as a RUN, so an undeclared heading
    whose findings ride two consecutive blocks counts both.
    """
    tokens = list(_DETAILS_TOKEN_RE.finditer(body))
    depth_at_heading = 0
    for token in tokens:
        if token.start() >= heading_end:
            break
        depth_at_heading += -1 if token.group(0).startswith('</') else 1

    spans: list[tuple[int, int]] = []
    boundary = heading_end
    depth = depth_at_heading
    # Start AT the heading: a block that merely precedes it belongs to whatever came before.
    index = next((position for position, token in enumerate(tokens) if token.start() >= heading_end), len(tokens))
    while index < len(tokens):
        token = tokens[index]
        if token.group(0).startswith('</'):
            depth -= 1
            if depth < depth_at_heading:
                return spans
            index += 1
            continue
        close = _block_close(body, token.start())
        if close is None or depth != depth_at_heading:
            return spans
        if not _adjacent_to_heading(body, boundary, token.start()):
            return spans
        if _block_opens_a_section_or_a_bare_counted_title(body, token.start()):
            return spans
        if _block_opens_a_non_finding_list(body, token.start()):
            return spans
        spans.append((token.start(), close))
        closing_token = _DETAILS_TOKEN_RE.match(body, close)
        boundary = closing_token.end() if closing_token is not None else close
        depth += 1
        index = next((later for later, token_ in enumerate(tokens) if token_.start() >= close), len(tokens))
    return spans


def _adjacent_to_heading(body: str, boundary: int, opener: int) -> bool:
    """Whether only markup and whitespace separate a heading from the block it may own.

    The gap carries blockquote markers, list bullets, ``<br>`` tags and other markup in the
    real bodies; a LETTER or DIGIT left after the markup is removed means prose, and a
    heading mentioned in prose owns no block.
    """
    gap = re.sub(r'<[^>]+>', ' ', body[boundary:opener])
    return re.search(r'[A-Za-z0-9]', gap) is None


def _block_opens_a_non_finding_list(body: str, opener: int) -> bool:
    """Whether the block at ``opener`` opens with a declared NON-FINDING block's title.

    A ``Files selected for processing: 15`` list is a boundary, and a heading must not own
    it: the count it declares would be read as the heading's findings.
    """
    title = _block_summary_title(body, opener)
    return title is not None and _is_non_finding_title(title)


def _block_opens_a_section(body: str, opener: int) -> bool:
    """Whether the block at ``opener`` opens with a ``<summary>`` naming a FINDINGS section."""
    title = _block_summary_title(body, opener)
    return title is not None and _section_for_title(title)[0] is not None


def _block_opens_a_section_or_a_bare_counted_title(body: str, opener: int) -> bool:
    """Whether the block at ``opener`` is a SECTION of its own rather than a bold heading's row.

    A block whose summary names a findings section is a section. So is a block whose summary
    is a counted title that looks like neither a row's severity line nor a row's
    ``file:line`` location: `Potential issues (2)` is a section, while `Major · src/a.py (2)`
    is the row of the bold heading above it.
    """
    title = _block_summary_title(body, opener)
    if title is None:
        return False
    if _section_for_title(title)[0] is not None:
        return True
    if _declared_count(title) is None:
        return False
    plain = re.sub(r'<[^>]+>', ' ', title).strip()
    return _ROW_SEVERITY_RE.match(plain) is None and _ROW_LOCATION_RE.search(plain) is None


def _block_summary_title(body: str, opener: int) -> str | None:
    """Return the title of the ``<summary>`` that OPENS the block at ``opener``, or ``None``.

    Only the summary before the block's first NESTED ``<details>`` opens this block. A
    summary further inside belongs to a block the reviewer nested here — reading it as this
    block's title let a nested ``Files selected for processing: 15`` list title a
    summary-less block and silence the counted heading it held.
    """
    closing = _block_close(body, opener)
    boundary = closing if closing is not None else len(body)
    opening = _DETAILS_TOKEN_RE.match(body, opener)
    if opening is None:
        return None
    nested = _DETAILS_TOKEN_RE.search(body, opening.end(), boundary)
    limit = nested.start() if nested is not None else boundary
    summary = _SUMMARY_RE.search(body, opening.end(), limit)
    return None if summary is None else summary.group('title')


def _block_close(body: str, opener: int) -> int | None:
    """Return the offset of the ``</details>`` closing the block opened at ``opener``.

    ``None`` when the block is never closed, so its caller can treat an unbalanced block
    as owning nothing rather than as owning the rest of the body.
    """
    depth = 0
    for token in _DETAILS_TOKEN_RE.finditer(body, opener):
        depth += -1 if token.group(0).startswith('</') else 1
        if depth == 0:
            return token.start()
    return None


def _adjacent_unclosed_block(body: str, heading_end: int) -> bool:
    """Whether an ADJACENT block after the heading is never closed.

    A standalone findings heading followed by a block that cannot be closed is a body whose
    findings nobody can enumerate — the block's rows would be invisible and the gate could
    answer `all_handled`. That is a stop, never a silent skip.
    """
    for token in _DETAILS_TOKEN_RE.finditer(body, heading_end):
        if token.group(0).startswith('</'):
            return False
        if not _adjacent_to_heading(body, heading_end, token.start()):
            return False
        return _block_close(body, token.start()) is None
    return False


def _enclosing_block_close(body: str, offset: int) -> int | None:
    """Return the close offset of the innermost block OPEN at ``offset``, or ``None``."""
    stack: list[int] = []
    for token in _DETAILS_TOKEN_RE.finditer(body):
        if token.start() >= offset:
            break
        if token.group(0).startswith('</'):
            if stack:
                stack.pop()
        else:
            stack.append(token.start())
    return _block_close(body, stack[-1]) if stack else None


def _inside_prose(body: str, offset: int) -> bool:
    """Whether ``offset`` sits inside a finding's row body (``<dd>``) or a code sample.

    A heading-shaped BOLD span inside one of these is a QUOTE of a heading, never a heading:
    a reviewer quotes section titles inside a finding's row and inside a code sample, and
    reading one as a heading would end the enclosing section's span there and lose every
    finding after it.

    Prose scopes are per BLOCK, at every depth. A ``<dd>`` or ``<code>`` opened in a block is
    prose for the rest of that block and ends when the block does — so an unterminated
    ``<code>`` in one block cannot hide a heading in a later sibling block, and a ``<dd>`` that
    legitimately spans a nested block keeps its own scope instead of being cut at that block.
    A tag in a block that has since closed is never counted, whichever depth it sat at. The
    scopes INHERIT: a tag left open in a parent block is still prose for a heading inside that
    parent's nested blocks, because the parent's text still contains the heading.
    """
    scopes: list[dict[str, int]] = [{}]
    # A close sorts BEFORE an open at the same offset, so an empty block cannot leave its
    # opener on the stack.
    events: list[tuple[int, int, str, str, bool]] = []
    for block in _DETAILS_TOKEN_RE.finditer(body, 0, offset):
        closing = block.group(0).startswith('</')
        events.append((block.start(), 0 if closing else 1, 'block', '', closing))
    for prose in _PROSE_TAG_RE.finditer(body, 0, offset):
        closing = bool(prose.group('close'))
        events.append((prose.start(), 0 if closing else 1, 'prose', prose.group('name').lower(), closing))
    for _position, _order, kind, name, closing in sorted(events):
        if kind == 'block':
            if closing:
                if len(scopes) > 1:
                    scopes.pop()
                    if len(scopes) == 1:
                        # A prose tag opened in the TOP-LEVEL text ends with the top-level
                        # block that follows it. The block is the region such a tag runs
                        # into; letting it survive the block keeps a heading BELOW the
                        # closed block in a prose scope, which drops its findings.
                        scopes[0] = {}
            else:
                scopes.append({})
            continue
        depth = scopes[-1]
        depth[name] = max(0, depth.get(name, 0) + (-1 if closing else 1))
    return any(level > 0 for scope in scopes for level in scope.values())


#: The ASCII punctuation CommonMark counts as punctuation for its flanking rule — a class the
#: Unicode categories do not match (``<`` is a math symbol, not a ``P*`` code point).
_ASCII_PUNCTUATION = frozenset('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')


def _is_punctuation(character: str) -> bool:
    """Whether ``character`` is punctuation in Markdown's flanking rule.

    Markdown's rule names Unicode punctuation; a SYMBOL is punctuation too as far as this
    parser is concerned, because a reviewer decorates a heading with it: reading ``**…(1)**🎯``
    as "the closer is followed by something that could open a word" turned the closing marker
    into an opener and lost the heading.
    """
    if not character:
        return False
    if character in _ASCII_PUNCTUATION:
        return True
    return unicodedata.category(character).startswith(('P', 'S'))


def _bold_spans(body: str) -> list[tuple[int, int, str]]:
    """Every ``(start, end, title)`` BOLD span, paired by OPENING and CLOSING markers.

    ``finditer`` over a single-span pattern pairs markers NON-OVERLAPPINGLY, so one stray
    ``**`` earlier in the body spends a real heading's opening marker as the closing marker of
    the pair before it and the heading is never read — an under-count.

    A marker's role is Markdown's own flanking rule: it can OPEN when text does not attach on
    its left (or punctuation does, while the marker itself is followed by non-punctuation), and
    it can CLOSE when text attaches on its left and nothing that could start a word sits on its
    right. A marker that could do both closes only when a heading is already open, so
    ``text**Heading**`` still reads as one span while ``>**⚠️ Heading**`` (an opener glued to
    punctuation) does not spend itself as a closer. That single rule does everything this parser
    needs: the heading after a stray ``**kwargs`` is still read (two markers with words to their
    right are two openers), the prose BETWEEN two bold runs is not read as a heading of its own
    (``**Major** Nitpick comments (2) **Quick win**`` states one severity label and one win),
    ``**A****B**`` is two spans, and a title ending in an emoji or a quotation mark closes.
    """
    spans: list[tuple[int, int, str]] = []
    opener: int | None = None
    for marker in _BOLD_MARKER_RE.finditer(body):
        before = body[marker.start() - 1] if marker.start() else ''
        after = body[marker.end() : marker.end() + 1]
        can_open = (
            bool(after)
            and not after.isspace()
            and (not _is_punctuation(after) or not before or before.isspace() or _is_punctuation(before))
        )
        can_close = (
            bool(before)
            and not before.isspace()
            and (not _is_punctuation(before) or not after or after.isspace() or _is_punctuation(after))
        )
        if not (can_close and not (can_open and opener is None)):
            opener = marker.start()
            continue
        if can_open and opener is not None:
            pending = body[opener + len('**') : marker.start()].strip('*')
            if _bold_heading_section(pending)[0] is None:
                # The span from the pending opener to here is not a heading, and this marker
                # could OPEN one: a stray ``**`` earlier in the body must not spend the
                # opening marker of a counted heading glued to a letter
                # (``**stray x**Outside diff range comments (1)**``). A pending span that IS
                # a heading is never spent this way, so a closer followed by an emoji
                # (``**…(1)**🎯``) still closes.
                opener = marker.start()
                continue
        if opener is not None:
            # A delimiter RUN can carry three markers (`***Heading***`), so the run's inner
            # asterisks belong to the delimiter, not to the title: stripping them keeps a
            # triple-emphasis heading readable while a title with an asterisk INSIDE it still is
            # not a span.
            title = body[opener + len('**') : marker.start()].strip('*')
            if title and '*' not in title:
                spans.append((opener, marker.end(), title))
        opener = None
    return spans


def _code_span_contents(body: str) -> list[tuple[int, int]]:
    """Return the ``(content_start, content_end)`` of every code span, paired by run length.

    A backtick run of N opens a span that only a later run of EXACTLY N closes; a run of
    another length is literal text inside it. Pairing every second backtick instead lets a
    stray single run close on the first character of a doubled fence, after which the
    doubled fence's other character pairs with the heading's own backticks and the heading
    reads as a quotation.

    A run with NO later equal-length partner is literal text and is SKIPPED, never left
    pending: a pending unmatched run used to suppress every later span, so one stray
    double-backtick run hid the single-backtick quotation that followed it and the heading
    inside it was counted as a finding.
    """
    runs = [(run.start(), run.end() - run.start()) for run in _BACKTICK_RUN_RE.finditer(body)]
    contents: list[tuple[int, int]] = []
    index = 0
    while index < len(runs):
        start, length = runs[index]
        closer = next((later for later in range(index + 1, len(runs)) if runs[later][1] == length), None)
        if closer is None:
            index += 1
            continue
        contents.append((start + length, runs[closer][0]))
        index = closer + 1
    return contents


def _quoted_in_a_code_span(body: str, start: int, end: int) -> bool:
    """Whether the bold span at ``start``–``end`` is the WHOLE content of a code span.

    A reviewer quotes a heading as a code span (`` `**Outside diff range comments (1)**` ``).
    A code span that holds the heading plus other text is not that quotation: a stray run
    earlier in the body pairs with a later one and spans prose on both sides of a real
    heading, and reading it as a quotation would drop the heading's findings — the
    direction this gate must never take.
    """
    heading = body[start:end].strip()
    return any(
        content_start <= start and end <= content_end and body[content_start:content_end].strip() == heading
        for content_start, content_end in _code_span_contents(body)
    )


#: What separates a bold heading from the text after it in the flattened display form a
#: review body arrives in: the blockquote markers and line markup the flatten inserts.
_FLATTENED_BREAK_RE = re.compile(r'^(?:[\s>]|<br\s*/?>)*', re.IGNORECASE)


def _heading_is_mentioned_in_prose(body: str, offset: int) -> bool:
    """Whether a SENTENCE runs on past the bold heading ending at ``offset``.

    ``**Outside diff range comments (1)** is empty this time.`` is a heading QUOTED in prose:
    the sentence continues past the closing marker, so the span is not a heading over what
    follows, and minting a finding for it would be a phantom. A list row (``- `src/a.py:12`
    …``), a table, a tag or a block is not a sentence, so a counted heading above any of those
    is a heading — the shape where the drop rule read a declaration as zero findings.

    The test keys on a LETTER continuing the sentence. A continuation led by punctuation
    (``**: none this round.``) is therefore read as a heading — over-counting rather than
    dropping a row, which is the direction this gate permits. The residual is a prose ROW that
    happens to start with a letter, which is the same text as a mention in the flattened form
    (a surviving newline is treated as a space here) and is named in :func:`_body_findings`.
    """
    rest = body[offset:]
    if not rest.strip():
        return False
    break_match = _FLATTENED_BREAK_RE.match(rest)
    remainder = rest[break_match.end() :] if break_match is not None else rest
    return bool(remainder) and remainder[0].isalpha()


def _enclosing_block_span(body: str, offset: int) -> tuple[int, int]:
    """Return the ``(open, close)`` offsets of the innermost block OPEN at ``offset``.

    The offsets are the ``<details>`` opener's and its matching closer's. A block that is never
    closed runs to the end of the body — the fail-safe direction for a caller measuring what a
    block contains.
    """
    stack: list[int] = []
    for token in _DETAILS_TOKEN_RE.finditer(body):
        if token.start() >= offset:
            break
        if token.group(0).startswith('</'):
            if stack:
                stack.pop()
        else:
            stack.append(token.start())
    if not stack:
        return offset, offset
    closing = _block_close(body, stack[-1])
    return stack[-1], len(body) if closing is None else closing


def _inside_non_finding_block(body: str, offset: int) -> bool:
    """Whether ``offset`` sits inside a block titled as a declared NON-FINDING block.

    A bold label inside a ``Review info`` block is a label on boilerplate, not a section over
    the body: the block states nothing about this change, so the label's count is not a
    finding's.
    """
    opener, _close = _enclosing_block_span(body, offset)
    if opener == offset:
        # No block is open here: the sentinel is the offset itself.
        return False
    title = _block_summary_title(body, opener)
    return title is not None and _is_non_finding_title(title)


def _enclosing_sections(
    body: str,
    matches: list[re.Match[str]],
    heading_at: dict[int, str | None],
) -> dict[int, int | None]:
    """Map each ``<summary>`` to the heading that encloses it.

    THE nesting rule this parser depends on: a reviewer nests a per-FILE grouping
    inside a section block, so ``<details><summary>Nitpick comments (2)</summary>
    … <details><summary>src/comments.py (2)</summary>`` has one section summary and
    one file summary inside it. A summary nested inside a HEADING is content — a file
    path that happens to contain ``comment`` or ``nitpick`` must not be minted as a
    separate ``unclassified`` heading, and neither must a per-file count that would then
    be counted twice: once as the enclosing heading's declared count and once as its own.

    Depth alone is not the rule, because a reviewer may wrap a whole body in one
    outer block: every real section then sits one level deeper, and a bare depth
    test would drop its findings silently — the "cannot read means pass" failure
    this gate exists to close. Nesting inside a block that is NOT a heading
    (a walkthrough, the AI-prompt block) is therefore not containment: such a
    summary stays a section candidate at any depth.
    """
    containers: dict[int, int | None] = {}
    stack: list[int | None] = []
    events: list[tuple[int, str, int | None]] = [
        (match.start(), 'summary', index) for index, match in enumerate(matches)
    ]
    events.extend(
        (token.start(), 'close' if token.group(0).startswith('</') else 'open', None)
        for token in _DETAILS_TOKEN_RE.finditer(body)
    )
    # A close sorts before an open at the same offset, so an empty block cannot
    # leave its opener on the stack.
    events.sort(key=lambda event: (event[0], 0 if event[1] == 'close' else 1))
    for _position, kind, index in events:
        if kind == 'open':
            stack.append(None)
        elif kind == 'close':
            if stack:
                stack.pop()
        elif index is not None:
            # The nearest HEADING, not merely the nearest open block: a non-heading
            # group can sit between a section and a deeper summary, and that deeper
            # summary is still the section's content.
            containers[index] = next(
                (holder for holder in reversed(stack) if holder is not None and heading_at.get(holder) is not None),
                None,
            )
            if stack and stack[-1] is None:
                stack[-1] = index
    return containers


#: The depth at or above which a ``<summary>`` is a reviewer's SECTION heading. A
#: section block opens one ``<details>``, so its summary sits at depth 1; a deeper
#: summary is the per-file grouping inside a section, and is content.
_SECTION_DEPTH = 1

#: The record kinds the review-surface read publishes. A record of any OTHER kind
#: is a surface this verb cannot read, so it stops the gate rather than being
#: filtered away as "no findings".
_RECORD_KINDS = ('inline', 'review_body', 'issue_comment')

#: The progress line that records the OPERATOR's dismissal selection, and the
#: separator after which the key sits. Read back by ``sonar-gate --progress-file``
#: so a supplied selection is checked against the run's own record.
_OPERATOR_SELECTION_PREFIX = 'operator-selected:'

#: The reviewer-neutral evidence field of one disposition line, and the progress
#: template's own separator.
_DISPOSITION_SEPARATOR = '—'
_DISPOSITION_RE = re.compile(
    r'^(?P<reviewer>\S+)\s+(?P<section>\S+)\s+(?P<id>\S+)\s*' + _DISPOSITION_SEPARATOR + r'\s*(?P<evidence>\S.*)$'
)

#: The evidence values that name neither a commit nor a reason — the shape a line has
#: when nothing was decided. Compared as one punctuation-stripped, case-folded token, so
#: ``TBD.``, ``N/A`` and ``—`` reduce to ``tbd``, ``na`` and the empty entry.
_DISPOSITION_PLACEHOLDER_EVIDENCE = frozenset({'', 'tbd', 'todo', 'na', 'none', 'later', 'wip', 'pending'})

#: A hex commit id is evidence on its own, with no other token needed.
_COMMIT_SHA_RE = re.compile(r'[0-9a-f]{7,40}')

#: Everything a placeholder comparison does not need: punctuation, markup and symbols.
_PLACEHOLDER_PUNCTUATION_RE = re.compile(r'[^a-z0-9]+')


def _disposition_evidence_is_real(evidence: str) -> bool:
    """Whether a disposition's evidence names a commit or a stated reason.

    A hex commit id is evidence on its own. Any other text is a stated reason unless it
    reduces to a placeholder once case and punctuation are stripped — a placeholder is
    what a line says when nothing was decided, so counting it as disposed is the pass
    this gate exists to remove.
    """
    token = _PLACEHOLDER_PUNCTUATION_RE.sub('', evidence.strip().lower())
    if _COMMIT_SHA_RE.fullmatch(token):
        return True
    return token not in _DISPOSITION_PLACEHOLDER_EVIDENCE


def _normalise_section_title(title: str) -> str:
    """Return a ``<summary>`` title reduced to lowercase words for LABEL matching.

    A reviewer decorates its headings with markup, emoji, bold markers and
    punctuation. The markup is dropped first (a ``<picture>``/``<strong>`` wrapper
    carries no words of the heading), then everything that is not a letter, a digit,
    a hyphen, a space or a parenthesised group is dropped, so ``🧹 Nitpick comments
    (2)`` and ``**Nitpick comments (2)**`` reduce to the same ``nitpick comments
    (2)`` the label table is written against. The parentheses survive on purpose:
    they let a normalised title keep the shape it declares, though the COUNT itself is
    read off the raw title by ``_declared_count`` — normalisation drops the colon
    spelling the reviewer uses.
    """
    text = re.sub(r'<[^>]+>', ' ', title)
    return ' '.join(re.sub(r'[^a-z0-9\- ()]+', ' ', text.lower()).split())


def _parse_declared_count(digits: str) -> int:
    """Read a declared count, never raising on a digit run no ``int()`` can take.

    A run longer than nine digits is already far above :data:`_MAX_ENUMERATED_FINDINGS`, so
    it answers the first count above the cap: the caller then stops with the same named
    reason as any other implausible declaration, instead of ``int()`` raising ``ValueError``
    on CPython's integer-string conversion limit and replacing the verdict with a traceback.
    Leading zeros are stripped first: ``0000000001`` declares ONE finding, and measuring the
    padded spelling would refuse it as over the cap.
    """
    significant = digits.lstrip('0') or '0'
    if len(significant) > 9:
        return _MAX_ENUMERATED_FINDINGS + 1
    return int(significant)


def _declared_count(title: str) -> int | None:
    """Return the count a ``<summary>`` title declares, or ``None``.

    The count is read off the RAW title, because the colon spelling does not survive
    ``_normalise_section_title`` — and it is the spelling the reviewer really posts
    (OBSERVED: ``Nitpick comments: 1`` on #1940). Markup and decoration AROUND the
    count are dropped first, so ``**Nitpick comments (3)**`` and ``Nitpick comments:
    3 🧹`` still declare three; both spellings name the same statement about the block.
    """
    text = re.sub(r'<[^>]+>', ' ', title)
    plain = ' '.join(_COUNT_TITLE_NOISE_RE.sub(' ', text.lower()).split())
    declared = _COUNT_SUFFIX_RE.search(plain)
    if declared is None:
        return None
    return _parse_declared_count(declared.group('paren') or declared.group('colon'))


def _is_non_finding_title(title: str) -> bool:
    """Whether a counted title is a declared non-finding block (a file list, review info)."""
    normalised = _normalise_section_title(title)
    return any(normalised.startswith(label) for label in _NON_FINDING_SECTION_LABELS)


def _section_for_title(title: str) -> tuple[str | None, int | None]:
    """Return ``(canonical section, declared count)`` for one ``<summary>`` title.

    ``(None, None)`` when the title is not a finding section at all (a
    walkthrough, a "Review details" block, the AI-prompt block). The count is the
    one the reviewer declares — ``(N)`` or ``: N`` — or ``None`` when it declares
    none; the caller then counts the section's row markers or nested per-file blocks.
    """
    normalised = _normalise_section_title(title)
    for label, section in sorted(_REVIEW_BODY_SECTIONS, key=lambda row: -len(row[0])):
        if normalised.startswith(label):
            return section, _declared_count(title)
    return None, None


def _heading_section(title: str) -> tuple[str | None, int | None]:
    """Return the section a ``<summary>`` title states, or ``(None, None)``.

    A title naming a findings section returns that section. A title that declares a count
    while matching neither a findings section nor a declared non-finding label is
    ``unclassified``: its count is findings whose disposition the gate demands — refusing
    the whole body instead stopped every re-run on a body that never changes, and reading
    it as zero admitted the merge over findings nobody read.
    """
    section, declared = _section_for_title(title)
    if section is not None:
        return section, declared
    counted = _declared_count(title)
    if counted is not None and not _is_non_finding_title(title):
        return _UNCLASSIFIED_SECTION, counted
    return None, None


def _bold_heading_section(title: str) -> tuple[str | None, int | None]:
    """Return ``(canonical section, declared count)`` when a BOLD line heads a section.

    A reviewer writes a section heading in one of two shapes: a ``<summary>`` title, or a
    BOLD line of its own — OBSERVED on ``cuioss/plan-marshall#1983`` and ``#1984``, where
    ``**⚠️ Outside diff range comments (1)**`` heads the ``<details>`` carrying the finding
    while no ``<summary>`` states that heading. Without this read those findings are
    invisible, so a review whose findings all ride such a block answered ``all_handled``.

    Only a bold span saying NOTHING but a findings-section label (and, optionally, the count
    it declares) is a heading. That is what separates a heading from the bold decoration a
    body carries elsewhere: ``**Major**`` and ``**Quick win**`` label one finding's severity,
    and ``**Actionable comments posted: 4**`` is the status line the inline-count reader
    owns — turning any of those into a section would mint findings nobody wrote.
    """
    normalised = _normalise_section_title(title)
    declared = _declared_count(title)
    label_text = normalised if declared is None else _HEADING_TRAILING_COUNT_RE.sub('', normalised)
    for label, section in sorted(_REVIEW_BODY_SECTIONS, key=lambda row: -len(row[0])):
        if label_text == label:
            return section, declared
    return None, None


def _count_section_findings(
    span: str,
    declared: int | None,
    excluded_offsets: frozenset[int] = frozenset(),
    span_start: int = 0,
) -> int:
    """Return the number of findings the reviewer declares inside one section.

    The declared count wins: it is the reviewer's own statement about the block, and
    reading it is what keeps one disposition from clearing several findings. Without
    one, the section's own rows state it — one ``<!-- cr-comment:v1:`` marker per
    finding — and its nested per-file blocks state it as ``file: n`` or ``file (n)``.
    The two are taken at their larger value, because a disagreement between them is a
    block that under-states its findings, and an under-count clears several with one
    disposition. A block carrying neither, but prose of its own, states one finding; an
    empty block states none.

    A nested summary that is ITSELF a section heading (its absolute offset is in
    ``excluded_offsets``) contributes nothing here: it is counted as a section of its own,
    and adding its count would report the same statements twice.
    """
    if declared is not None:
        return declared
    rows = len(_ROW_MARKER_RE.findall(span))
    nested = 0
    for match in _SUMMARY_RE.finditer(span):
        if span_start + match.start() in excluded_offsets:
            continue
        counted = _declared_count(match.group('title'))
        if counted is not None:
            nested += counted
    if rows or nested:
        return max(rows, nested)
    return 1 if re.sub(r'<[^>]+>', ' ', span).strip() else 0


def _body_sources(body: str) -> dict[str, Any]:
    """Return the ``<summary>`` headings of one review body and how they nest."""
    matches = list(_SUMMARY_RE.finditer(body))
    starts = list(enumerate(matches))
    heading_at = {index: _heading_section(match.group('title'))[0] for index, match in starts}
    return {
        'matches': matches,
        'starts': starts,
        'heading_at': heading_at,
        'offset_of': {index: match.start() for index, match in starts},
        'end_of': {index: match.end() for index, match in starts},
        'containers': _enclosing_sections(body, matches, heading_at),
        'starts_by_index': {index: match.group('title') for index, match in starts},
    }


def _direct_child_blocks(body: str, start: int, end: int) -> list[tuple[int, int]]:
    """Return the spans of the blocks opened DIRECTLY inside ``body[start:end]``."""
    spans: list[tuple[int, int]] = []
    depth = 0
    for token in _DETAILS_TOKEN_RE.finditer(body, start, end):
        if token.group(0).startswith('</'):
            depth -= 1
            continue
        if depth == 0:
            close = _block_close(body, token.start())
            spans.append((token.start(), close if close is not None else end))
        depth += 1
    return spans


def _transparent_wrappers(body: str, sources: dict[str, Any]) -> tuple[dict[int, list[int]], str | None]:
    """Map each counted WRAPPER to the recognised sections it encloses, or name a stop.

    A counted title this parser does not know can be a wrapper: a group whose content is a
    recognised section (``<summary>Review (1)</summary><details><summary>Nitpick comments
    (10)</summary>…``). Reading the wrapper's own count as its findings made the outer 1 win
    over the inner 10 — the under-count this rule closes — so such a wrapper is read THROUGH
    and the section inside it is a section of its own. Three shapes stop instead, because
    reading through would drop something the body states: an enclosed section that owns no
    CLOSED block (nothing beside it can be attributed), content of the wrapper's own beside
    that section, and a wrapper declaring MORE findings than the sections it encloses
    account for.
    """
    starts_by_index = sources['starts_by_index']
    containers = sources['containers']
    heading_at = sources['heading_at']
    offset_of = sources['offset_of']
    end_of = sources['end_of']
    transparent: dict[int, list[int]] = {}
    for index, title in starts_by_index.items():
        holder = containers.get(index)
        if holder is None or heading_at.get(holder) != _UNCLASSIFIED_SECTION:
            continue
        if _section_for_title(title)[0] is not None:
            transparent.setdefault(holder, []).append(index)
    for index, children in transparent.items():
        _open, wrapper_close = _enclosing_block_span(body, offset_of[index])
        for child in children:
            child_open, _child_close = _enclosing_block_span(body, offset_of[child])
            if child_open < end_of[index] or _block_close(body, child_open) is None:
                return {}, (
                    f'the counted wrapper {starts_by_index[index]!r} encloses a section without a '
                    f'closed block of its own, so its findings cannot be read'
                )
        gap = body[end_of[index] : wrapper_close]
        masks: list[tuple[int, int]] = []
        for child_open, child_close in _direct_child_blocks(body, end_of[index], wrapper_close):
            if not any(child_open <= offset_of[child] < child_close for child in children):
                continue
            # Mask only the group's own SUMMARY element — its structural title — and the
            # recognised section's own block. The rest of the group stays visible, so a
            # prose row written beside the section is content the wrapper must account
            # for; masking the whole group hid exactly that row and required a
            # disposition only for the section. The summary search is bounded to the
            # group's OWN head: an unbounded search found the nested section's summary
            # when the group carries none, and that removed a finding written above it.
            first_nested = next(
                (
                    token.start()
                    for token in _DETAILS_TOKEN_RE.finditer(body, child_open + 1, child_close)
                    if not token.group(0).startswith('</')
                ),
                child_close,
            )
            summary_match = _SUMMARY_RE.search(body, child_open, first_nested)
            masks.append((child_open, summary_match.end() if summary_match is not None else child_open))
            for child in children:
                if child_open <= offset_of[child] < child_close:
                    section_open, section_close = _enclosing_block_span(body, offset_of[child])
                    masks.append((section_open, section_close if section_close is not None else wrapper_close))
        for start_at, end_at in masks:
            first = max(start_at, end_of[index]) - end_of[index]
            last = min(end_at, wrapper_close) - end_of[index]
            if first < last:
                gap = gap[:first] + ' ' * (last - first) + gap[last:]
        # ANY non-whitespace text is the wrapper's own content: a letter-or-digit test would
        # pass a non-ASCII sentence and a symbol-only note, and reading through would drop both.
        if re.sub(r'<[^>]+>', ' ', gap).strip():
            return {}, (
                f'the counted wrapper {starts_by_index[index]!r} carries content beside the '
                f'section it encloses, so its findings cannot be read'
            )
        declared = _declared_count(starts_by_index[index]) or 0
        enclosed = 0
        for child in children:
            # The SAME count the section enumeration will use: an undeclared child's
            # rows are its findings, so assuming one per undeclared child rejected a
            # wrapper that declared the two rows its child actually carries.
            child_open, child_close = _enclosing_block_span(body, offset_of[child])
            child_span = body[child_open : child_close if child_close is not None else len(body)]
            enclosed += _count_section_findings(
                child_span,
                _declared_count(starts_by_index[child]),
                frozenset(),
                child_open,
            )
        if declared > enclosed:
            return {}, (
                f'the counted wrapper {starts_by_index[index]!r} declares {declared} findings and '
                f'encloses only {enclosed}, so its findings cannot be read'
            )
    return transparent, None


def _heading_is_a_mention(body: str, start: int, end: int, raw_body: str | None) -> bool:
    """Whether a bold heading is quoted in a sentence, not one over the rows below it.

    The flattened display form cannot tell a heading over a prose ROW from one inside a
    sentence: both carry a letter after the closing marker. The RAW body can — a row sits on
    its own line — so a continuation only makes a mention when it shares the heading's line.
    Without the raw text the flattened rule stands.
    """
    if not _heading_is_mentioned_in_prose(body, end):
        return False
    if raw_body is None:
        return True
    title = body[start + len('**') : end - len('**')].strip('*')
    needle = '**' + title + '**'
    # The display form has NEWLINES replaced by spaces, so a title split across two raw
    # lines appears as one line here. Matching token-by-token with a whitespace run
    # between them finds that raw occurrence; and a title the raw body cannot locate is
    # NOT called a mention — dropping a heading because its spelling could not be
    # re-found is the under-count this gate must never take.
    needle_re = re.compile(r'\s+'.join(re.escape(token) for token in needle.split()))
    occurrence = max(len(needle_re.findall(body[:start])), 0)
    matches = list(needle_re.finditer(raw_body))
    if occurrence >= len(matches):
        return False
    tail = raw_body[matches[occurrence].end() :].split('\n', 1)[0]
    remainder = _FLATTENED_BREAK_RE.match(tail)
    tail = tail[remainder.end() :] if remainder is not None else tail
    return bool(tail) and tail[0].isalpha()


def _body_bold_headings(
    body: str,
    summary_spans: list[tuple[int, int]],
    raw_body: str | None,
) -> tuple[
    list[tuple[int, int, str, int | None]],
    list[tuple[int, int, str, int | None]],
    dict[int, list[tuple[int, int]]],
    list[tuple[int, int, int]],
    frozenset[int],
    str | None,
]:
    """Return the BOLD-line headings of one review body, and what each owns.

    They are boundaries and sections at once: a bold heading ends the span of the summary
    section above it and owns the span below. A bold span inside a ``<summary>`` is that
    summary's own decoration, one inside a finding's row body or a code sample is a QUOTE of
    a heading, and one a sentence runs on from is a heading MENTIONED in prose — none of
    those mints a finding.
    """

    def _lies_within(offset: int, spans: list[tuple[int, int]]) -> bool:
        return any(start <= offset < end for start, end in spans)

    bold_candidates = [
        (start, end, section, declared)
        for start, end, title in _bold_spans(body)
        if not _lies_within(start, summary_spans) and not _inside_prose(body, start)
        if not _quoted_in_a_code_span(body, start, end)
        for section, declared in (_bold_heading_section(title),)
        if section is not None
    ]
    # A heading that names a section, sits beside a row block, and cannot see that block's end
    # is a body whose findings cannot be enumerated: stop rather than drop them silently.
    for candidate in bold_candidates:
        if not _owned_blocks(body, candidate[1]) and _adjacent_unclosed_block(body, candidate[1]):
            return (
                [],
                [],
                {},
                [],
                frozenset(),
                (f'the block under {candidate[2]!r} is never closed, so its findings cannot be read'),
            )
    # The blocks each bold heading OWNS, and the span it therefore covers. Ownership is that
    # identity, never mere precedence — a section summary inside any other block is a section
    # of its own, and treating it as the bold heading's row would drop its findings.
    owned_blocks = {
        start: _owned_blocks(body, heading_end) for start, heading_end, _section, _declared in bold_candidates
    }
    # An unclosed SECOND sibling is the same stop as an unclosed first one: the heading owns the
    # blocks before it, and the remaining rows of the broken one would be silently unread.
    for start, _heading_end, section, _declared in bold_candidates:
        spans = owned_blocks.get(start) or []
        if not spans:
            continue
        closing_token = _DETAILS_TOKEN_RE.match(body, spans[-1][1])
        boundary = closing_token.end() if closing_token is not None else spans[-1][1]
        if _adjacent_unclosed_block(body, boundary):
            return (
                [],
                [],
                {},
                [],
                frozenset(),
                (f'the block under {section!r} is never closed, so its findings cannot be read'),
            )
    bold_headings = [candidate for candidate in bold_candidates if owned_blocks.get(candidate[0])]
    # A counted heading that owns no `<details>` block is still a heading: the reviewer DECLARED
    # the findings, and dropping the declaration is the under-count this rule closes. Two
    # shapes are not that heading — a bold span a SENTENCE runs on from (a heading mentioned in
    # prose), and a label inside a declared NON-FINDING block (boilerplate's own title).
    declared_headings = [
        candidate
        for candidate in bold_candidates
        if not owned_blocks.get(candidate[0])
        and candidate[3]
        and not _heading_is_a_mention(body, candidate[0], candidate[1], raw_body)
        and not _inside_non_finding_block(body, candidate[0])
    ]
    owned_spans = [
        (open_offset, close_offset, start)
        for start, _end, _section, _declared in bold_headings
        for open_offset, close_offset in owned_blocks.get(start, [])
    ]
    # A bold heading nested in another heading's span does not END that span: its own interval
    # is blanked out of the count instead, so the rows on both sides of it are read by their
    # own section. That is as true of a counted heading with no block as of one that owns one.
    nested_starts = frozenset(
        [start for start, _end, _section, _declared in bold_headings]
        + [start for start, _end, _section, _declared in declared_headings]
    )
    return bold_headings, declared_headings, owned_blocks, owned_spans, nested_starts, None


def _body_summary_headings(
    body: str,
    sources: dict[str, Any],
    transparent: dict[int, list[int]],
    owned_spans: list[tuple[int, int, int]],
) -> tuple[list[tuple[int, int, str, int | None]], list[int]]:
    """Return the ``<summary>`` findings sections, and the offsets that end a span."""
    starts = sources['starts']
    heading_at = sources['heading_at']
    offset_of = sources['offset_of']
    end_of = sources['end_of']
    containers = sources['containers']
    starts_by_index = sources['starts_by_index']
    transparent_children = frozenset(child for children in transparent.values() for child in children)

    def _is_content(index: int) -> bool:
        """Whether this summary sits inside a HEADING — a per-file grouping, not a heading."""
        return index not in transparent_children and containers.get(index) is not None

    def _is_section(index: int) -> bool:
        """Whether this summary is a section heading."""
        return not _is_content(index) and heading_at[index] is not None

    def _is_span_boundary(index: int) -> bool:
        """Whether this summary ENDS the span of the section before it.

        A finding section's content runs to the next section heading — and also to a DECLARED
        NON-FINDING block, which is a boundary even though it contributes no findings: a
        counted ``Files selected for processing: 1`` list copied inside a section's span would
        be counted as one more finding of that section. An ``unclassified`` heading is a
        heading like any other, so it is a boundary too.
        """
        if _is_content(index):
            return False
        if heading_at[index] is not None:
            return True
        title = starts_by_index[index]
        return _declared_count(title) is not None and _is_non_finding_title(title)

    headings: list[tuple[int, int, str, int | None]] = []
    for index, _match in starts:
        if index in transparent:
            continue
        if not _is_section(index):
            continue
        title = starts_by_index[index]
        owned = any(open_offset < offset_of[index] < close_offset for open_offset, close_offset, _owner in owned_spans)
        if owned and _section_for_title(title)[0] is None:
            # A summary inside a block a bold heading owns is that block's row. A summary that
            # NAMES a findings section is not: it is a section of its own, and the outer count
            # leaves its span out, so neither reading loses it nor counts it twice.
            continue
        section, declared = _heading_section(title)
        if section is None:
            continue
        headings.append((offset_of[index], end_of[index], section, declared))
    boundaries = [match.start() for index, match in starts if _is_span_boundary(index)]
    return headings, boundaries


def _heading_span_end(
    body: str,
    start: int,
    owned_blocks: dict[int, list[tuple[int, int]]],
    boundary_starts: list[int],
    nested_starts: frozenset[int],
) -> int:
    """The offset at which the heading at ``start`` stops owning the body."""
    blocks = owned_blocks.get(start) or []
    if blocks:
        # A bold heading's span is the blocks it owns. The summary that OPENS such a block is
        # a boundary for every other heading, but cutting the block's own span at it would
        # leave an undeclared bold heading counting an empty span.
        return blocks[-1][1]
    # A section's span is bounded by the next SECTION boundary — never by a bold heading nested
    # inside its own block (owning one or not), whose interval is excluded from the count
    # instead, so the rows on either side of it are both read.
    boundary = next(
        (bound_ for bound_ in boundary_starts if bound_ > start and bound_ not in nested_starts),
        len(body),
    )
    enclosing = _enclosing_block_close(body, start)
    return boundary if enclosing is None else min(boundary, enclosing)


def _count_body_headings(
    body: str,
    headings: list[tuple[int, int, str, int | None]],
    owned_blocks: dict[int, list[tuple[int, int]]],
    owned_spans: list[tuple[int, int, int]],
    boundary_starts: list[int],
    nested_starts: frozenset[int],
    heading_offsets: frozenset[int],
    reviewer: str,
    counters: dict[str, int],
) -> tuple[list[dict[str, str]], int, str | None]:
    """Count every heading's findings, naming a stop when one asks for too many."""
    findings: list[dict[str, str]] = []
    inline_from_sections = 0
    for start, end, section, declared in headings:
        span_end = _heading_span_end(body, start, owned_blocks, boundary_starts, nested_starts)
        span = body[end:span_end]
        # A NESTED bold heading's own interval is counted by that heading, so it is blanked here
        # — same length, so every offset stays where it was. This heading's own blocks are left
        # intact: they are the span it counts. ONLY owning headings blank an interval.
        for open_offset, close_offset, owner_start in owned_spans:
            if owner_start != start and end < open_offset and close_offset < span_end:
                span = span[: open_offset - end] + ' ' * (close_offset - open_offset) + span[close_offset - end :]
        count = _count_section_findings(
            span,
            declared,
            excluded_offsets=heading_offsets,
            span_start=end,
        )
        if count > _MAX_ENUMERATED_FINDINGS:
            return (
                [],
                0,
                (
                    f'{count} findings declared for section {section!r}, above the '
                    f'{_MAX_ENUMERATED_FINDINGS} this gate will enumerate'
                ),
            )
        findings.extend(_numbered_findings(reviewer, section, count, counters))
        if section == 'inline':
            inline_from_sections += count
    if len(findings) > _MAX_ENUMERATED_FINDINGS:
        # The per-heading cap is not a cap on the BODY: many headings each just under it would
        # still enumerate more rows than the gate will materialize.
        return (
            [],
            0,
            (f'{len(findings)} findings in one body, above the {_MAX_ENUMERATED_FINDINGS} this gate will enumerate'),
        )
    return findings, inline_from_sections, None


def _body_findings(
    reviewer: str,
    body: str,
    bot_kind: str,
    counters: dict[str, int] | None = None,
    raw_body: str | None = None,
) -> tuple[list[dict[str, str]], str | None]:
    """Parse one review body into its findings, or name what makes it unreadable.

    Every recognised section contributes ``{section}-{n}`` findings under
    ``reviewer``. ``counters`` carries the per-(reviewer, section) numbering
    ACROSS this reviewer's bodies, so two review bodies do not both mint
    ``nitpick-1``: a disposition naming ``nitpick-1`` then discharges exactly one
    finding rather than one per body, which is what a stale finding riding a
    fresh sha looks like.

    An inline count the reviewer states only as its status line (the registry's
    ``review_body_summary_patterns`` literal) is read as the ``inline`` section too. The status
    line and an inline section are two statements about the same findings, so the LARGER of the
    two is the count — a body whose second statement is bigger never reads fewer findings than
    it declares, and one whose statements agree mints nothing twice.

    A section heading is read in THREE shapes, so no block a reviewer filled goes
    unread: a ``<summary>`` title naming a findings section, a BOLD line that states
    nothing but such a label, and a ``<summary>`` title that declares a count while
    naming nothing this parser knows — whose declared count is minted as
    ``unclassified`` findings, because a titled, counted block holds statements that
    must be disposed of. A title that declares no count and names no findings section is
    never a heading: inside a heading it is that heading's content (the per-file grouping),
    and with no enclosing heading it is ignored, exactly as it was before this parser read
    more than one heading shape.

    A counted BOLD heading is read even when it owns no ``<details>`` block: its declared
    count is a statement about the rows below it, and dropping it is the under-count this
    gate forbids. Only a heading a SENTENCE runs on from (a mention in prose) or a label
    inside a declared non-finding block mints nothing. The raw body separates the two
    shapes the flattened form merges: a heading over a prose ROW ends its line, while a
    mention continues on the same line as the closing marker.

    A counted title this parser does not know that ENCLOSES a recognised section is a
    wrapper, not a section: it reads through, so the section inside it keeps its own
    findings. A wrapper stops with a named cause when it encloses a section with no closed
    block of its own, says anything of its own beside that section, or declares MORE
    findings than the sections it encloses account for. A wrapper holding a BOLD heading
    counts both, which errs toward more findings — the direction this gate permits.

    A count larger than :data:`_MAX_ENUMERATED_FINDINGS` — per heading, for the inline
    supplement, or for the body's total — is a stop: a body that declares it would
    enumerate that many rows, so the gate names it rather than allocating them.
    """
    counters = counters if counters is not None else {}
    # Quoted markup inside a fence is prose (see `_mask_fenced_code`): mask it before
    # any structural read, so an example can neither mint findings nor stop the gate.
    body = _mask_fenced_code(body)
    sources = _body_sources(body)
    transparent, stop = _transparent_wrappers(body, sources)
    if stop is not None:
        return [], stop

    # The BOLD-line headings, in body order: a bold heading ends the span of the summary
    # section above it and owns the span below it.
    summary_spans = [(match.start(), match.end()) for _index, match in sources['starts']]
    bold_headings, declared_headings, owned_blocks, owned_spans, nested_starts, stop = _body_bold_headings(
        body, summary_spans, raw_body
    )
    if stop is not None:
        return [], stop
    summary_headings, boundary_starts = _body_summary_headings(body, sources, transparent, owned_spans)
    boundary_starts = sorted(
        boundary_starts
        + [start for start, _end, _section, _declared in bold_headings]
        + [start for start, _end, _section, _declared in declared_headings]
    )
    headings = sorted(
        summary_headings + bold_headings + declared_headings,
        key=lambda heading: heading[0],
    )

    heading_offsets = frozenset(start for start, _end, _section, _declared in headings)
    findings, inline_from_sections, stop = _count_body_headings(
        body,
        headings,
        owned_blocks,
        owned_spans,
        boundary_starts,
        nested_starts,
        heading_offsets,
        reviewer,
        counters,
    )
    if stop is not None:
        return [], stop

    # The reviewer's status line and any inline section are two statements about the SAME
    # inline findings, so the larger one is the count — the same rule the sections themselves
    # follow. Reading the status line only when no inline section exists let a blockless
    # ``**Inline comments (2)**`` heading suppress a status line declaring four, which would
    # read fewer findings than the body states; the shortfall is minted instead, and a body
    # whose two statements agree mints nothing twice. The shortfall is capped like every other
    # count, so a hostile status line cannot allocate the process to death.
    supplement = max(0, _inline_status_count(body, bot_kind) - inline_from_sections)
    if supplement > _MAX_ENUMERATED_FINDINGS:
        return [], (
            f'{supplement} inline findings declared by the status line, above the '
            f'{_MAX_ENUMERATED_FINDINGS} this gate will enumerate'
        )
    findings.extend(_numbered_findings(reviewer, 'inline', supplement, counters))
    if len(findings) > _MAX_ENUMERATED_FINDINGS:
        return [], (
            f'{len(findings)} findings in one body, above the {_MAX_ENUMERATED_FINDINGS} this gate will enumerate'
        )
    return findings, None


def _numbered_findings(
    reviewer: str,
    section: str,
    count: int,
    counters: dict[str, int],
) -> list[dict[str, str]]:
    """Mint ``count`` findings for one section, continuing this reviewer's numbering."""
    rows = []
    for _ in range(count):
        counters[section] = counters.get(section, 0) + 1
        rows.append({'reviewer': reviewer, 'section': section, 'id': f'{section}-{counters[section]}'})
    return rows


def _inline_status_count(body: str, bot_kind: str) -> int:
    """Read the reviewer's inline count off its declared status line, or ``0``.

    The literal comes from the registry (``review_body_summary_patterns``), never
    from this module: the bot standard remains the one place the phrase lives.

    The number is matched IMMEDIATELY after the literal, never as the first
    digit run anywhere in the rest of the body: the CI read the lane uses is the display
    path, which flattens a body to one line, so a "first digit in the tail" read
    would turn any later ``(N)`` into a phantom inline count. Matching forward
    from the literal is the same read on a flattened and on a structured body.
    """
    if not bot_kind:
        return 0
    import bot_registry

    for pattern in bot_registry.review_body_summary_patterns(bot_kind):
        index = body.find(pattern)
        if index < 0:
            continue
        declared = re.match(r'\s*(\d+)', body[index + len(pattern) :])
        if declared is None:
            continue
        return _parse_declared_count(declared.group(1))
    return 0


def _bot_of(comment: dict[str, Any]) -> str:
    """Return the registered bot a comment is attributed to (``''`` for anyone else)."""
    import bot_registry

    return bot_registry.bot_kind_for_login(comment.get('author'))


def _reviewer_of(comment: dict[str, Any]) -> str:
    """Return the reviewer identity a comment is attributed to (``''`` when nameless).

    A registered bot resolves to its ``bot_kind``, so the disposition ledger names
    the reviewer the same way the reviewer's own standard does. Anyone else is a
    HUMAN reviewer, and is named by its login: the gate covers every reviewer's
    review body, not only the registered bots' — a human's sectioned review is a
    finding source like any other, and silently dropping it would be the pass this
    verb exists to remove.
    """
    import bot_registry

    kind = bot_registry.bot_kind_for_login(comment.get('author'))
    if kind:
        return kind
    return str(comment.get('author') or '').strip().lower()


def _threads(comments: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group the inline comments by thread id, in the order the provider returned them."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for comment in comments:
        if comment.get('kind') != 'inline':
            continue
        thread_id = str(comment.get('thread_id') or '')
        if not thread_id:
            continue
        grouped.setdefault(thread_id, []).append(comment)
    return grouped


def _thread_concern_remains(thread: list[dict[str, Any]]) -> bool:
    """Whether a RESOLVED thread's last BOT comment says the concern remains.

    The last BOT-authored comment is the finding's last word: a reviewer that
    restates the defect and is then answered by the lane (or a human) still has an
    open concern, and a lane reply can itself carry the marker vocabulary, so the
    comments after the bot's are never tested. A later bot comment WITHOUT a marker
    (the bot's own acknowledgement, "Addressed in commit …") is the discharge; a
    thread with no bot comment at all carries no reviewer concern.
    """
    last = next((comment for comment in reversed(thread) if _bot_of(comment)), None)
    if last is None:
        return False
    body = str(last.get('body') or '').lower()
    return any(marker in body for marker in _CONCERN_REMAINS_MARKERS)


def _review_thread_rows(threads: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split the threads into ``(unresolved, concern-remains)`` rows carrying ``path:line``."""
    unresolved: list[dict[str, Any]] = []
    remains: list[dict[str, Any]] = []
    for thread_id, thread in threads.items():
        opening = thread[0]
        row = {
            'thread_id': thread_id,
            'path': str(opening.get('path') or ''),
            'line': opening.get('line') or 0,
            'location': f'{opening.get("path") or "?"}:{opening.get("line") or 0}',
        }
        if not all(bool(comment.get('resolved')) for comment in thread):
            unresolved.append(row)
        elif _thread_concern_remains(thread):
            remains.append(row)
    return unresolved, remains


def _parse_dispositions(values: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    """Parse the ``--disposition`` values into rows, naming any that do not parse.

    One row per progress line, in the progress template's own wording:
    ``finding: {reviewer} {section} {id} — {sha|reason}``. The evidence token is
    what makes the disposition a disposition: a line with none, or with a placeholder
    (``TBD``, ``-``, ``n/a``, …), answers nothing about the finding, so it is refused
    by name rather than counted.
    """
    rows: list[dict[str, str]] = []
    refused: list[str] = []
    for value in values:
        match = _DISPOSITION_RE.match(value.strip())
        if match is None or not _disposition_evidence_is_real(match.group('evidence')):
            refused.append(value)
            continue
        rows.append({key: match.group(key) for key in ('reviewer', 'section', 'id', 'evidence')})
    return rows, refused


_REVIEW_READ_EXCEPTIONS = (OSError, RuntimeError, ValueError, TypeError, AttributeError, ImportError)
"""What the review read — its imports, its repo lookup and its fetch — may raise.

The read classifies these as a failed read; the flatten of the same snapshot
classifies the same set, so both halves of one verdict answer ``undecidable_read``
rather than letting one of them escape as a traceback.
"""


def _read_review_surfaces(pr_number: int, project_dir: Path) -> dict[str, Any]:
    """Read a pull request's comment surfaces ONCE, raw, in-process.

    One fetch is the point. The findings parser reads the DISPLAY form (every body
    flattened to one line, which is what ``ci pr comments`` prints) and the
    required-reviewer check reads the RAW form (a coverage-marker opener is the bot's
    own claim only at the start of a line), and two fetches could show the two halves
    different moments: a review or a thread landing between them would be credited by
    one and unseen by the other, so the gate could answer ``all_handled`` over findings
    it never read. The provider data is therefore fetched here, once, and the verdict
    flattens its own copy (:func:`_display_read`).

    The read is the data fetch the producer and the post chokepoint ask, imported
    through ``github_re_review`` (the import-order-safe entry into ``github_ops``) and
    routed to ``project_dir`` so ``gh`` resolves the same repository the lane is
    gating. It is GitHub's read, so the project must ROUTE to GitHub
    (:func:`ci_base.resolve_ci_provider`) before a comment is read at all: waiting for
    ``gh`` to fail instead would leave a project configured for another provider
    readable through a GitHub-resolvable checkout, and an empty GitHub set would answer
    ``all_handled`` over comments that project never publishes. A mismatch, and an
    unresolvable provider alike, answer ``status: error`` — which the gate reports as
    ``undecidable_read``, never as a missing review.

    Every failure is CLASSIFIED, never a traceback. The imports, the repo lookup
    (:func:`github_ops.get_repo_info` dereferences its own JSON, so a malformed reply
    raises ``AttributeError``) and the fetch itself all sit inside the guard, because a
    crash is the one shape this verb cannot classify — and a read nobody can classify
    is a stop, not a verdict.
    """
    try:
        from ci_base import resolve_ci_provider, set_default_cwd
        from github_re_review import fetch_pr_comments_data

        provider = resolve_ci_provider(project_dir)
        if provider != 'github':
            # The read is GitHub's, so the project must ROUTE to GitHub before a comment
            # is read at all. Waiting for ``gh`` to fail instead would leave a project
            # configured for another provider readable through a GitHub-resolvable
            # checkout: an empty GitHub set would answer ``all_handled`` over comments
            # the project's own CI never publishes.
            return {
                'status': 'error',
                'error': f'the review gate reads GitHub comment data; this project routes to {provider or "no resolvable CI provider"}',
            }
        set_default_cwd(str(project_dir))
        return fetch_pr_comments_data(pr_number)
    except _REVIEW_READ_EXCEPTIONS as exc:
        return {'status': 'error', 'error': f'the review read could not run: {exc}'}


def _display_read(read: dict[str, Any]) -> dict[str, Any]:
    """The DISPLAY form of ``read`` — every body flattened — for the findings parser.

    The parser counts sections off the flattened text the printed table carries, so the
    flattening happens here, over the same snapshot the required-reviewer check reads.
    A non-success envelope is returned unchanged, which keeps a failed read a failed
    read for every consumer.
    """
    import github_ops

    return github_ops.flatten_comment_bodies(read)


def _required_reviewers_without_a_review(comments: list[dict[str, Any]], required_reviewers: list[str]) -> list[str]:
    """Return the required reviewers that hold no qualifying review on this read.

    The done rule's precondition, checked where the merge is decided. A qualifying
    review is the producer's finished-review test — the ONE predicate
    (``_github_pr.is_finished_review``) the producer, the post chokepoint and this
    check all ask, so none of the three can answer a formal review differently.
    Nothing here decides what to do with the review — only that a review exists to be
    done.

    ``comments`` are the provider's RAW records (:func:`_read_review_surfaces`), never
    the display-flattened copy: the predicate places a coverage marker by its line
    position, so the text it reads must still HAVE those lines. Nothing here strips,
    re-splits or otherwise rebuilds the body.
    """
    # `github_re_review` owns the import-order-safe entry into `_github_pr` (it
    # imports `github_ops` first, which breaks that module's import cycle) and
    # re-exports the one finished-review reader, so the lane never imports the cycle
    # itself.
    from github_re_review import is_finished_review

    present: set[str] = set()
    for comment in comments:
        bot = _bot_of(comment)
        if not bot or bot not in required_reviewers:
            continue
        if is_finished_review(comment, bot):
            present.add(bot)
    return sorted(set(required_reviewers) - present)


def _review_gate_verdict(
    pr_number: int,
    read: dict[str, Any],
    dispositions: list[dict[str, str]],
    refused: list[str],
    required_reviewers: list[str] | None = None,
) -> dict[str, Any]:
    """Decide whether the review surfaces admit the merge (section 7's condition).

    The verdict is a pure function of the ONE raw read and of the run's recorded
    dispositions, so the merge condition is a decision a script makes:

    - an unreadable or truncated read is ``undecidable_read`` — a stop, never a
      pass, because "no findings" is unknowable from a surface nobody read whole, and
      so is a comment entry the display flatten cannot read;
    - a disposition line that names no commit and no stated reason is
      ``disposition_unparsable``;
    - an unresolved thread is ``unresolved_review_threads``;
    - a body finding with no disposition naming a commit or a stated reason is
      ``body_findings_undisposed``;
    - a resolved thread whose last BOT-authored comment states that the concern
      remains is ``thread_concern_remains`` — resolution is not silence, and a lane
      reply below the bot's restatement never discharges it;
    - a required reviewer holding no qualifying review is
      ``required_review_missing``;
    - otherwise ``all_handled``.
    """
    base: dict[str, Any] = {'status': 'success', 'operation': 'review-gate', 'pr_number': pr_number}
    if refused:
        return {
            **base,
            'merge_allowed': False,
            'reason': 'disposition_unparsable',
            'refused': refused,
        }
    if read.get('status') != 'success':
        return {
            **base,
            'merge_allowed': False,
            'reason': 'undecidable_read',
            'detail': str(read.get('error') or 'the review surface read failed'),
        }
    if 'complete' not in read:
        # A read that publishes no coverage signal at all is not the same failure as one
        # that reported itself incomplete: naming truncation would state a cause that did
        # not happen and send the reader looking for a drained connection that was never
        # opened. Both stop the gate; the detail says which one it was.
        return {
            **base,
            'merge_allowed': False,
            'reason': 'undecidable_read',
            'detail': (
                'the review surface read published no completeness signal: '
                'whether every connection was drained is unknown'
            ),
        }
    if read.get('complete') is not True:
        return {
            **base,
            'merge_allowed': False,
            'reason': 'undecidable_read',
            'detail': 'the review surface read was truncated: not every connection was drained',
        }

    # The findings parser reads the DISPLAY form, derived here from the one snapshot
    # this verdict decides on: the required-reviewer check below reads the same
    # snapshot's raw bodies. One fetch, two views, no window between them. The flatten
    # reads every entry before the dict filter below reaches one, so an entry that is
    # not a mapping raises here; the guard classifies that as a stop, because a crash
    # states no verdict at all.
    try:
        display = _display_read(read)
    except _REVIEW_READ_EXCEPTIONS as exc:
        return {
            **base,
            'merge_allowed': False,
            'reason': 'undecidable_read',
            'detail': f'the review read could not be flattened into its display form: {exc}',
        }
    comments = [comment for comment in (display.get('comments') or []) if isinstance(comment, dict)]
    unrecognised = sorted({str(comment.get('kind')) for comment in comments} - set(_RECORD_KINDS))
    if unrecognised:
        # A record shape this verb does not know is a surface it cannot read. The
        # alternative — filtering to the shapes it knows and reporting the rest as
        # no findings — is the "cannot read means pass" failure once more, and it is
        # silent: a provider that renamed ``kind`` would drain as a clean merge.
        return {
            **base,
            'merge_allowed': False,
            'reason': 'undecidable_read',
            'detail': f'unrecognised review-surface record kind(s): {", ".join(unrecognised)}',
        }
    threads = _threads(comments)
    unresolved, remains = _review_thread_rows(threads)

    findings: list[dict[str, str]] = []
    counters: dict[str, dict[str, int]] = {}
    # The parser reads the DISPLAY form for its structure, and the RAW body for the one fact
    # the flatten destroys: whether text continues on the heading's own LINE. Both views come
    # from the same snapshot, keyed by the record id.
    raw_bodies = {
        str(entry.get('id')): str(entry.get('body') or '')
        for entry in read.get('comments') or []
        if isinstance(entry, dict)
    }
    for comment in comments:
        if comment.get('kind') != 'review_body':
            continue
        reviewer = _reviewer_of(comment)
        if not reviewer:
            # A review body with no attributable author cannot be disposed by name,
            # so its findings would vanish — the pass this verb exists to remove.
            return {
                **base,
                'merge_allowed': False,
                'reason': 'undecidable_read',
                'detail': 'a review body carries no attributable author',
            }
        body_findings, undecidable = _body_findings(
            reviewer,
            str(comment.get('body') or ''),
            _bot_of(comment),
            counters.setdefault(reviewer, {}),
            raw_body=raw_bodies.get(str(comment.get('id')), str(comment.get('body') or '')),
        )
        if undecidable is not None:
            return {**base, 'merge_allowed': False, 'reason': 'undecidable_read', 'detail': undecidable}
        findings.extend(body_findings)

    disposed = {(row['reviewer'], row['section'], row['id']) for row in dispositions}
    undisposed = [
        finding for finding in findings if (finding['reviewer'], finding['section'], finding['id']) not in disposed
    ]

    verdict: dict[str, Any] = {
        **base,
        'unresolved_review_threads': len(unresolved),
        'review_body_findings_total': len(findings),
        'review_body_findings_handled': len(findings) - len(undisposed),
        'unresolved_threads': unresolved,
    }
    missing_reviews: list[str] = []
    if required_reviewers:
        verdict['required_reviewers'] = list(required_reviewers)
        missing_reviews = _required_reviewers_without_a_review(
            [comment for comment in read.get('comments') or [] if isinstance(comment, dict)],
            list(required_reviewers),
        )
    if missing_reviews:
        # The done rule is "one handled review IS the review", never "the flag is
        # enough": a required reviewer the run names must actually hold a qualifying
        # review before its currency demand can be waived.
        return {
            **verdict,
            'merge_allowed': False,
            'reason': 'required_review_missing',
            'missing_required_reviews': missing_reviews,
        }
    if unresolved:
        return {**verdict, 'merge_allowed': False, 'reason': 'unresolved_review_threads'}
    if undisposed:
        return {**verdict, 'merge_allowed': False, 'reason': 'body_findings_undisposed', 'undisposed': undisposed}
    if remains:
        return {**verdict, 'merge_allowed': False, 'reason': 'thread_concern_remains', 'threads': remains}
    return {**verdict, 'merge_allowed': True, 'reason': 'all_handled'}


def cmd_review_gate(args: argparse.Namespace) -> dict[str, Any]:
    """Report whether the pull request's review surfaces admit the merge."""
    pr_number = getattr(args, 'pr_number', None)
    if not isinstance(pr_number, int) or pr_number <= 0:
        return {
            'status': 'error',
            'error': 'invalid_pr_number',
            'message': f'--pr-number must be a positive integer; got {pr_number!r}',
        }
    project_dir = Path(getattr(args, 'project_dir', None) or '.')
    dispositions, refused = _parse_dispositions(list(getattr(args, 'disposition', None) or []))
    required_reviewers = [
        str(bot).strip() for bot in (getattr(args, 'required_reviewer', None) or []) if str(bot).strip()
    ]
    read = _read_review_surfaces(pr_number, project_dir)
    return _review_gate_verdict(pr_number, read, dispositions, refused, required_reviewers)


def cmd_resolve(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve every project-specific value the runbook lane needs."""
    project_dir = Path(getattr(args, 'project_dir', '.') or '.').resolve()

    try:
        choice = _resolve_spec(args.spec, project_dir)
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
    # The READ half of the same channel: the orchestrator delivers a plan's mail to
    # ``inbox/to/{plan_id}/``, so the lane reads its own mailbox through the verb
    # that resolves that address — never by opening a path under the epic tree.
    inbox_read_command = (
        'python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox read '
        f'--slug {slug} --plan-id {plan_id}'
    )

    resolved: dict[str, Any] = {
        'status': 'success',
        'operation': 'resolve',
        'spec': spec.as_posix(),
        'spec_source': choice.source,
        'slug': slug,
        'plan': plan_id,
        'body_slot': _body_slot_from_plan_id(plan_id),
        'worktree': worktree,
        'progress_file': progress_file,
        'landing_file': landing_file,
        'sender_id': sender_id,
        'inbox_write_command': inbox_write_command,
        'inbox_read_command': inbox_read_command,
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
        help=(
            'Accepted for compatibility and now a no-op: reading the spec from the shared ledger '
            'worktree first, then the main checkout, is the default'
        ),
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

    stale_parser = subparsers.add_parser(
        'sonar-stale-delta',
        help="Decide whether a stale Sonar analysis may stand as this head's read",
        allow_abbrev=False,
    )
    stale_parser.add_argument(
        '--state',
        required=True,
        help='The state resolve reported: configured, or not_configured',
    )
    stale_parser.add_argument(
        '--count-status',
        dest='count_status',
        default=None,
        help="The read's count_status (only undecidable can be carried forward)",
    )
    stale_parser.add_argument(
        '--analysis-revision',
        dest='analysis_revision',
        default=None,
        help='The revision the read reported as analysed',
    )
    stale_parser.add_argument(
        '--head-revision',
        dest='head_revision',
        default=None,
        help='The revision the read reported as the head',
    )
    stale_parser.add_argument(
        '--worktree',
        default='.',
        help='The routed checkout the analysed revision and the delta are resolved in',
    )

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
        '--operator-selected-keys',
        dest='operator_selected_keys',
        default=None,
        help='Comma-separated finding keys the OPERATOR selected for dismissal',
    )
    gate_parser.add_argument(
        '--progress-file',
        dest='progress_file',
        default=None,
        help='The run progress file; a selected key must be recorded there as an operator selection',
    )
    gate_parser.add_argument(
        '--hotspot-keys',
        dest='hotspot_keys',
        default=None,
        help='Comma-separated SECURITY HOTSPOT keys among the open ones; a hotspot is never dismissable',
    )
    gate_parser.add_argument(
        '--dismissed-keys',
        dest='dismissed_keys',
        default=None,
        help='Retired: a lane-recorded dismissal is refused (lane_dismissal_not_accepted)',
    )
    gate_parser.add_argument(
        '--carried-forward',
        dest='carried_forward',
        action='store_true',
        help="The read's own carried_forward marker; it must accompany the revision pair",
    )
    gate_parser.add_argument(
        '--carried-forward-analysis-revision',
        dest='carried_forward_analysis_revision',
        default=None,
        help='The analysed revision a carried-forward read was measured at (name both this and the head)',
    )
    gate_parser.add_argument(
        '--carried-forward-head-revision',
        dest='carried_forward_head_revision',
        default=None,
        help='The head a carried-forward read stands in for (name both this and the analysed revision)',
    )
    gate_parser.add_argument(
        '--count-status-reason',
        dest='count_status_reason',
        default=None,
        help="The read's own count_status_reason; a carry-forward reason requires the marking",
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
    facts_parser.add_argument(
        '--gate-status',
        dest='gate_status',
        default=None,
        help='The new-code quality-gate status read at the merge head: ok, error, not_computed or unknown',
    )
    facts_parser.add_argument(
        '--carried-forward',
        dest='carried_forward',
        action='store_true',
        help="The read's own carried_forward marker; a carried-forward figure must carry it",
    )
    facts_parser.add_argument(
        '--analysed-revision',
        dest='analysed_revision',
        default=None,
        help='The analysed revision a carried-forward confirmed figure was measured at',
    )
    facts_parser.add_argument(
        '--carried-forward-analysis-revision',
        dest='analysed_revision',
        default=None,
        help=argparse.SUPPRESS,
    )
    facts_parser.add_argument(
        '--carried-forward-head-revision',
        dest='carried_forward_head_revision',
        default=None,
        help='The head a carried-forward figure stands in for',
    )
    facts_parser.add_argument(
        '--count-status-reason',
        dest='count_status_reason',
        default=None,
        help="The read's own count_status_reason; a carry-forward reason requires the marking",
    )

    review_parser = subparsers.add_parser(
        'review-gate',
        help='Decide whether the pull request review surfaces admit the merge',
        allow_abbrev=False,
    )
    review_parser.add_argument('--pr-number', dest='pr_number', type=int, required=True, help='Pull request number')
    review_parser.add_argument('--project-dir', default='.', help='Project root (default: current directory)')
    review_parser.add_argument(
        '--disposition',
        action='append',
        default=None,
        help=('One progress-file disposition line, repeatable: "{reviewer} {section} {id} — {sha|reason}"'),
    )
    review_parser.add_argument(
        '--required-reviewer',
        dest='required_reviewer',
        action='append',
        default=None,
        help=(
            'A REQUIRED reviewer bot kind, repeatable. When named, the gate also requires '
            'that reviewer to hold a qualifying review on record (a formal review record, or '
            'a summary marker that is readable, kind=reviewed and names a commit); one '
            'without it answers merge_allowed: false, required_review_missing.'
        ),
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
    if args.command == 'sonar-stale-delta':
        data = cmd_sonar_stale_delta(args)
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
    if args.command == 'review-gate':
        data = cmd_review_gate(args)
        if data.get('status') == 'error':
            output_toon_error(data['error'], data.get('message', data['error']))
            return 0
        output_toon(data)
        return 0
    parser.print_help()
    return 2


if __name__ == '__main__':
    main()
