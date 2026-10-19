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

``--spec`` must name a staged spec, i.e. a file below
``.plan/orchestrator/{slug}/plans/``. Anything else is refused: the lane exists
to run a staged orchestrator plan, and a path outside that tree names something
else. ``--project-dir`` defaults to the current directory and anchors every
project-scoped read (marshal.json, the project architecture, the guard marker).

**Fail closed.** An empty ``required_bots`` list, a missing automatic-review
step, an unreadable ``marshal.json`` and an unresolvable build command are all
errors carrying a specific code. There is never a fall-back to a default
reviewer list or a default build: a lane that quietly reviews with nobody, or
builds with the wrong tool, would report a green run over work nobody checked.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from file_ops import output_toon, output_toon_error

#: The step whose ``required_bots`` / ``optional_bots`` the lane drives.
_REVIEW_STEP_ID = 'plan-marshall:automatic-review'

#: The build canonical the lane resolves to learn the project's build tool, and
#: the command set the lane runs. ``verify`` is the resolved probe; the other
#: three are the lane's own canonical arguments, passed to whichever build
#: wrapper the architecture resolved. ``test-compile`` is part of ``verify``'s
#: split form and is not advertised as a resolvable canonical for every build
#: system, so it is composed from the SAME notation ``verify`` resolved rather
#: than resolved on its own.
_BUILD_PROBE = 'verify'
_BUILD_CANONICALS = ('quality-gate', 'module-tests', 'verify')
_SPLIT_FORM = ('quality-gate', 'test-compile', 'module-tests')

#: A staged spec, ANCHORED to the project root: ``.plan/orchestrator/{slug}/plans/PLAN-*.md``.
#: Matched with ``fullmatch`` against the project-relative path, so a same-shaped
#: file nested under another directory (an archive, a fixture tree) does not
#: satisfy it — the lane runs a spec at the root of the orchestrator tree, not any
#: file that happens to end the same way.
_SPEC_RE = re.compile(r'\.plan/orchestrator/(?P<slug>[^/]+)/plans/(?P<name>PLAN-[^/]+)\.md')

#: Lifts the executor prefix and the build notation out of a resolved
#: executable, so the lane composes the rest of its command set from the build
#: system the architecture resolved rather than from a hard-coded build skill.
_NOTATION_RE = re.compile(r'^(?P<prefix>.*?execute-script\.py)\s+(?P<notation>[^\s]+)\s+run\b')

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


def _resolve_spec(spec_value: str, project_dir: Path) -> tuple[Path, str, str]:
    """Validate ``--spec`` and return ``(spec, slug, plan_id)``.

    A RELATIVE spec is resolved against ``--project-dir``, not against the
    process's working directory: the flag names the project the whole resolution
    is about, so a caller that passes both must get the spec file it named. The
    project-relative path is then matched as a WHOLE against :data:`_SPEC_RE`, so
    only a spec at the root of the orchestrator tree qualifies.

    Raised as ``ValueError`` carrying the refusal code so the caller can emit a
    structured error rather than a traceback.
    """
    spec = Path(spec_value)
    if not spec.is_absolute():
        spec = project_dir / spec
    if not spec.is_file():
        raise ValueError('invalid_spec')
    try:
        rel = spec.resolve().relative_to(project_dir.resolve())
    except ValueError:
        raise ValueError('spec_outside_orchestrator') from None
    match = _SPEC_RE.fullmatch(rel.as_posix())
    if match is None:
        raise ValueError('spec_outside_orchestrator')
    return spec, match.group('slug'), _plan_id_from_spec(spec)


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


def _split_bots(value: Any) -> list[str]:
    """Split a CSV bot list, dropping blanks, preserving declared order."""
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
        from marketplace_bundles import resolve_bundle_path, resolve_bundles_root

        bundles_root: Path | None = resolve_bundles_root(Path(__file__))
    except Exception:
        bundles_root = None
    if bundles_root is not None:
        nested = resolve_bundle_path(bundles_root, bundle, subpath)
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

    required = _split_bots(step.get('required_bots'))
    if not required:
        raise ValueError('required_bots_empty')
    return _rows(required), _rows(_split_bots(step.get('optional_bots')))


def _resolve_build(project_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve the lane's build commands for this project's build system.

    The build system is read from the project architecture through the same
    resolution seam ``architecture resolve`` uses — never from a hard-coded
    build skill. ``verify`` is the probe; the remaining canons are passed to the
    notation it resolved.

    Returns ``(build, probed)``: the build command map, and the architecture's own
    resolved ``verify`` record, so the caller can read the timeout stamp off the
    same resolution instead of re-deriving the build system.
    """
    from _cmd_client_query import resolve_command

    try:
        probed = resolve_command(_BUILD_PROBE, None, str(project_dir))
    except Exception as exc:
        raise ValueError('build_command_unresolvable') from exc

    executable = probed.get('executable')
    if not isinstance(executable, str):
        raise ValueError('build_command_unresolvable')
    match = _NOTATION_RE.match(executable)
    if match is None:
        raise ValueError('build_command_unresolvable')
    prefix, notation = match.group('prefix'), match.group('notation')

    build: dict[str, Any] = {canon: f'{prefix} {notation} run --command-args "{canon}"' for canon in _BUILD_CANONICALS}
    # The split form exists because ``verify`` may outlive the shell budget; its
    # parts are the lane's own arguments on the SAME resolved build system.
    build['test-compile'] = f'{prefix} {notation} run --command-args "test-compile"'
    build['split'] = list(_SPLIT_FORM)
    return build, probed


def _augment_resolved(probed: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    """Return the architecture's augmented resolve record for *probed*.

    A thin seam over ``manage-architecture``'s augmentation, so the timeout
    resolution reads the architecture's own stamp without this module importing
    the architecture client at load time. It is also the seam a test can replace
    to pin a stamp the fixture architecture cannot express.
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
    from _cmd_manage import _gitignore_pattern_to_regex

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
        except ImportError as exc:
            # The shared glob translator is unavailable (a partial install).
            # Build everything and name the cause: a broken translator must never
            # be read as "no path matches", which for a skip rule would skip.
            rows = [{'path': path, 'kind': 'buildable'} for path in paths]
            reason = f'glob helper unavailable: {type(exc).__name__}'
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


def cmd_resolve(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve every project-specific value the runbook lane needs."""
    project_dir = Path(getattr(args, 'project_dir', '.') or '.').resolve()

    try:
        spec, slug, plan_id = _resolve_spec(args.spec, project_dir)
    except ValueError as exc:
        return {'status': 'error', 'error': str(exc), 'spec': args.spec}
    try:
        marshal = _read_marshal(project_dir)
        required, optional = _resolve_bots(marshal)
        build, probed = _resolve_build(project_dir)
        build_timeout_seconds = _resolve_build_timeout(probed, project_dir)
        base_branch = _resolve_base_branch(marshal)
        deliverable_state = _resolve_deliverable_skills(spec)
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

    worktree = f'.plan/local/worktrees/{plan_id}'
    progress_file = f'.plan/temp/rb-{plan_id}/progress.md'
    sender_id = f'rb-{plan_id}'
    landing_file = f'.plan/temp/landing-{plan_id}.md'
    inbox_write_command = (
        'python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox write '
        f'--slug {slug} --sender-type plan --sender-id {sender_id} --kind landing --payload-file {landing_file}'
    )

    resolved: dict[str, Any] = {
        'status': 'success',
        'operation': 'resolve',
        'spec': spec.as_posix(),
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
        'guard': guard,
        'guard_log': '/'.join(_GUARD_LOG_PARTS),
        'skills_note': deliverable_state['skills_note'],
    }
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

    classify_parser = subparsers.add_parser(
        'build-classify', help='Classify changed paths as docs-only or buildable', allow_abbrev=False
    )
    classify_parser.add_argument('--paths', required=True, help='Comma-separated changed paths')
    classify_parser.add_argument('--project-dir', default='.', help='Project root (default: current directory)')

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
    if args.command == 'build-classify':
        data = cmd_build_classify(args)
        if data.get('status') == 'error':
            output_toon_error(data['error'], data.get('message', data['error']))
            return 0
        output_toon(data)
        return 0
    parser.print_help()
    return 2


if __name__ == '__main__':
    main()
