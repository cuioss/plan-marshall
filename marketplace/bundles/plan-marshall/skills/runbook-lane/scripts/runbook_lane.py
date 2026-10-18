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


def _resolve_build(project_dir: Path) -> dict[str, Any]:
    """Resolve the lane's build commands for this project's build system.

    The build system is read from the project architecture through the same
    resolution seam ``architecture resolve`` uses — never from a hard-coded
    build skill. ``verify`` is the probe; the remaining canons are passed to the
    notation it resolved.
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
    return build


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
        build = _resolve_build(project_dir)
    except ValueError as exc:
        return {'status': 'error', 'error': str(exc), 'spec': args.spec, 'plan': plan_id}
    except Exception as exc:
        return {'status': 'error', 'error': 'resolve_failed', 'message': str(exc), 'plan': plan_id}

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

    return {
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
        'required_bots': required,
        'optional_bots': optional,
        'commit_trailer': trailer,
        'harness': harness,
        'guard': guard,
    }


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
    parser.print_help()
    return 2


if __name__ == '__main__':
    main()
