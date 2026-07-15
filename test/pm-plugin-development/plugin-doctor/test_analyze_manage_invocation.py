#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``_analyze_manage_invocation.py`` plugin-doctor analyzer.

The analyzer ships two rules over markdown invocations of every
script-bearing skill in the marketplace (the in-scope set is auto-derived
from the bundle tree by ``discover_in_scope_scripts``):

  * ``manage-invocation-invalid`` (severity: error) — emitted for each of
    four mismatch modes against the script's canonical argparse surface:

      - unknown top-level subcommand
      - unknown sub-verb (under a subcommand declaring its own subparsers)
      - unknown long flag under the resolved leaf parser
      - missing required long flag declared by the leaf parser

  * ``missing-canonical-block`` (severity: warning, build-failing under
    quality-gate) — emitted for an in-scope SKILL.md that lacks a
    ``## Canonical invocations`` section.

Surface derivation is from the script's live ``--help`` interface, NOT from
an AST walk. The tests therefore build a *synthetic executor*: a small
``.plan/execute-script.py`` shim that maps ``{notation}`` to a synthetic
argparse script under ``tmp_path`` and dispatches the trailing args
(including ``--help``) to it, exactly as the real executor does. This lets
the tests exercise the three registration styles that defeated the old
AST extractor:

  - loop-registered subcommands (``manage-logging`` registers ``work`` /
    ``decision`` through a ``for`` loop — invisible to literal-``add_parser``
    AST extraction, visible to ``--help``);
  - a many-subcommand script (``manage-status`` shape, ~20 subcommands);
  - subcommands sharing a flag (``--plan-id`` declared on every subcommand
    via a shared parent / common helper).

Each negative finding type has at least one dedicated case; payload shape
(rule_id, severity, line, file, canonical_hint) is verified against the
documented schema. A dedicated layer exercises the in-scope derivation
(argparse detection, underscore skip, excluded skills, ``manage-findings``
exclusion). A dedicated layer runs the corrected analyzer against the REAL
plan-marshall bundle and asserts zero false positives for the
correctly-authored canonical calls in the shipped docs.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from conftest import load_script_module

# ---------------------------------------------------------------------------
# Module loader — load the analyzer directly from the marketplace scripts dir.
# Underscore-prefixed analyzers are not importable through the executor, so we
# spec-load the module by file path the same way the doctor harness does.
# ---------------------------------------------------------------------------


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_ami = _load_module('_analyze_manage_invocation', '_analyze_manage_invocation.py')

analyze_manage_invocation_markdown = _ami.analyze_manage_invocation_markdown
scan_skill_for_manage_invocation = _ami.scan_skill_for_manage_invocation
scan_manage_invocation = _ami.scan_manage_invocation
check_missing_canonical_blocks = _ami.check_missing_canonical_blocks
discover_in_scope_scripts = _ami.discover_in_scope_scripts
derive_script_tree = _ami.derive_script_tree
build_script_index = _ami.build_script_index
RULE_MANAGE_INVOCATION_INVALID = _ami.RULE_MANAGE_INVOCATION_INVALID
RULE_MISSING_CANONICAL_BLOCK = _ami.RULE_MISSING_CANONICAL_BLOCK
_positional_region_is_templated = _ami._positional_region_is_templated


# ---------------------------------------------------------------------------
# Synthetic argparse scripts exercising real registration styles.
# ---------------------------------------------------------------------------

# Synthetic notation used across the per-shape unit tests. Mirrors the shape
# of a manage-* notation triple so the regex extractor accepts it.
_SYN_NOTATION = 'plan-marshall:manage-syn:manage-syn'


def _flat_script_source() -> str:
    """Two flat subcommands and one root-level flag.

    - ``foo`` subcommand has ``--alpha`` (required) and ``--beta``.
    - ``bar`` subcommand has ``--gamma``.
    - Root parser has ``--debug``.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser()
            parser.add_argument('--debug', action='store_true')
            subparsers = parser.add_subparsers(dest='cmd')

            foo = subparsers.add_parser('foo')
            foo.add_argument('--alpha', required=True)
            foo.add_argument('--beta')

            bar = subparsers.add_parser('bar')
            bar.add_argument('--gamma')

            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _nested_script_source() -> str:
    """One flat and one nested subcommand.

    - ``qgate`` subcommand declares its own subparsers:
        * ``add`` with ``--plan-id`` (required) and ``--phase`` (required)
        * ``query`` with ``--plan-id`` (required) and ``--phase``
    - ``other`` is a flat subcommand with ``--flag``.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest='cmd')

            qgate = subparsers.add_parser('qgate')
            qgate_subs = qgate.add_subparsers(dest='sub')

            add_p = qgate_subs.add_parser('add')
            add_p.add_argument('--plan-id', required=True)
            add_p.add_argument('--phase', required=True)

            query_p = qgate_subs.add_parser('query')
            query_p.add_argument('--plan-id', required=True)
            query_p.add_argument('--phase')

            other = subparsers.add_parser('other')
            other.add_argument('--flag')

            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _minimal_argparse_source() -> str:
    """Minimal argparse script — single ``run`` subcommand with one flag."""
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest='cmd')
            run = subparsers.add_parser('run')
            run.add_argument('--flag')
            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _loop_registered_source() -> str:
    """``manage-logging`` shape — subcommands registered through a ``for`` loop.

    The old AST extractor only saw literal ``subparsers.add_parser('name')``
    calls, so subcommands registered by iterating a list were INVISIBLE,
    producing false ``subcommand_unknown`` findings for genuinely-valid
    invocations like ``manage-logging work`` / ``manage-logging decision``.
    ``--help`` derivation sees them because argparse renders the real
    registered choices regardless of how the parsers were built.
    """
    return textwrap.dedent('''
        import argparse

        _SUBCOMMANDS = ['script', 'work', 'decision', 'separator', 'read']

        def main():
            parser = argparse.ArgumentParser(description='Unified logging operations')
            subparsers = parser.add_subparsers(dest='cmd')
            for name in _SUBCOMMANDS:
                sub = subparsers.add_parser(name)
                sub.add_argument('--plan-id')
                sub.add_argument('--level')
                sub.add_argument('--message')
            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _many_subcommand_source() -> str:
    """``manage-status`` shape — many subcommands, several loop-registered.

    Demonstrates the many-subcommand surface (~20) that the AST extractor
    under-counted. A subset is registered via a literal list comprehension /
    loop, the rest by helper calls, so a literal-only AST walk would miss
    most of them.
    """
    return textwrap.dedent('''
        import argparse

        _VERBS = [
            'create', 'read', 'set-phase', 'update-phase', 'progress',
            'metadata', 'get-context', 'get-worktree-path', 'list',
            'list-orphans', 'transition', 'archive', 'route',
            'get-routing-context', 'delete-plan', 'mark-step-done',
            'change-type-heuristic', 'aggregate-confidence', 'merge-lock',
            'self-test',
        ]

        def _register(subparsers, name):
            p = subparsers.add_parser(name)
            p.add_argument('--plan-id')
            return p

        def main():
            parser = argparse.ArgumentParser(
                description='Manage status.json files'
            )
            subparsers = parser.add_subparsers(dest='cmd')
            for verb in _VERBS:
                _register(subparsers, verb)
            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _shared_flag_source() -> str:
    """Subcommands that all share ``--plan-id`` and ``--task-number``.

    The shared flags are added to every subcommand through a common helper —
    the AST extractor dropped them because they were not declared as literal
    per-subcommand ``add_argument`` calls on the named parser variable.
    ``--help`` renders the real per-leaf flag surface including the shared
    flags, so the analyzer no longer falsely flags ``--plan-id`` as unknown.
    """
    return textwrap.dedent('''
        import argparse

        def _add_common(p):
            p.add_argument('--plan-id', required=True)
            p.add_argument('--task-number', required=True)

        def main():
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest='cmd')

            for name in ('update', 'finalize-step'):
                sub = subparsers.add_parser(name)
                _add_common(sub)
                sub.add_argument('--status')

            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _ansi_colored_script_source() -> str:
    """A ``_flat_script_source`` clone whose ``--help`` emits ANSI SGR codes.

    Mirrors the flat shape exactly (root ``--debug``, subcommands ``foo``
    [required ``--alpha``, optional ``--beta``] and ``bar`` [``--gamma``]) but
    overrides ``format_help`` to wrap SGR color escapes around the ``usage:``
    marker, the subcommand choices, and the ``--flag`` tokens — reproducing
    Python 3.14's colorized ``argparse --help``. The escapes flow through the
    executor shim exactly as a real colorized subprocess would emit them.

    The analyzer must strip these escapes to recover the surface: pre-fix, the
    colored ``usage:`` line defeats ``line.startswith('usage:')`` and the
    colored option flags defeat ``_OPTION_FLAG_RE``, yielding an EMPTY surface
    (the ~865-false-finding bug). The ``format_help`` override colorizes the
    root and every subparser (``add_subparsers`` defaults ``parser_class`` to
    the root's class), so ``foo``/``bar`` ``--help`` are colored too.
    """
    return textwrap.dedent('''
        import argparse

        _COLOR_TOKENS = (
            'usage:', '--debug', '--alpha', '--beta', '--gamma', 'foo', 'bar',
        )

        def _colorize(text):
            for tok in _COLOR_TOKENS:
                text = text.replace(tok, '\\x1b[36m' + tok + '\\x1b[0m')
            return text

        class _ColorParser(argparse.ArgumentParser):
            def format_help(self):
                return _colorize(super().format_help())

        def main():
            parser = _ColorParser(prog='syn')
            parser.add_argument('--debug', action='store_true')
            subparsers = parser.add_subparsers(dest='cmd')

            foo = subparsers.add_parser('foo')
            foo.add_argument('--alpha', required=True)
            foo.add_argument('--beta')

            bar = subparsers.add_parser('bar')
            bar.add_argument('--gamma')

            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


# ---------------------------------------------------------------------------
# Synthetic executor — maps {notation} to a synthetic script and dispatches.
# ---------------------------------------------------------------------------

# The shim mirrors the real ``.plan/execute-script.py`` executor: it reads a
# notation -> script-path mapping and dispatches the resolved script with the
# remaining argv, forwarding its stdout/stderr/returncode. ``--help`` therefore
# flows through to the target's argparse instance, producing the real published
# surface.
#
# Dispatch is IN-PROCESS via ``runpy.run_path`` under redirected stdout/stderr
# rather than a child ``subprocess``: the analyzer's own ``_run_help`` already
# spawns the shim as a subprocess, so an additional inner spawn (shim -> target)
# doubled the interpreter cold-start cost for every fixture-backed probe. The
# shim drives ``runpy.run_path`` itself, catching the ``SystemExit`` that
# argparse raises on ``--help`` and explicitly flushing the captured stdout/
# stderr before exiting. Because the shim owns the flush deterministically (it
# is the only writer to the real fds at exit), the help text is stable across
# repeated probes — the interpreter-shutdown flush race that motivated the old
# subprocess design only manifested when ``runpy`` + ``SystemExit`` raced the
# PARENT's ``capture_output`` teardown, which no longer applies here.
_EXECUTOR_SHIM = textwrap.dedent('''
    #!/usr/bin/env python3
    import contextlib
    import io
    import json
    import runpy
    import sys
    from pathlib import Path

    _MAP = json.loads((Path(__file__).parent / 'notation_map.json').read_text())

    def main():
        if len(sys.argv) < 2:
            sys.exit(2)
        notation = sys.argv[1]
        target = _MAP.get(notation)
        if target is None:
            sys.stderr.write(f'Unknown notation: {notation}\\n')
            sys.exit(2)

        out_buf = io.StringIO()
        err_buf = io.StringIO()
        rc = 0
        saved_argv = sys.argv
        sys.argv = [target, *sys.argv[2:]]
        try:
            with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
                runpy.run_path(target, run_name='__main__')
        except SystemExit as exc:
            code = exc.code
            if code is None:
                rc = 0
            elif isinstance(code, int):
                rc = code
            else:
                err_buf.write(f'{code}\\n')
                rc = 1
        finally:
            sys.argv = saved_argv

        sys.stdout.write(out_buf.getvalue())
        sys.stderr.write(err_buf.getvalue())
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(rc)

    if __name__ == '__main__':
        main()
''').lstrip()


def _make_executor(tmp_path: Path, mapping: dict[str, Path]) -> Path:
    """Write a synthetic executor + notation map and return the executor path.

    The executor lives at ``{root}/.plan/execute-script.py``, matching the
    real layout that ``_resolve_executor`` discovers.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    executor = plan_dir / 'execute-script.py'
    executor.write_text(_EXECUTOR_SHIM, encoding='utf-8')
    import json

    (plan_dir / 'notation_map.json').write_text(
        json.dumps({k: str(v) for k, v in mapping.items()}), encoding='utf-8'
    )
    return executor


@pytest.fixture
def flat_index(tmp_path: Path) -> dict:
    script = tmp_path / 'syn_flat.py'
    script.write_text(_flat_script_source(), encoding='utf-8')
    executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
    tree = derive_script_tree(_SYN_NOTATION, executor)
    assert tree is not None
    return {_SYN_NOTATION: tree}


@pytest.fixture
def nested_index(tmp_path: Path) -> dict:
    script = tmp_path / 'syn_nested.py'
    script.write_text(_nested_script_source(), encoding='utf-8')
    executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
    tree = derive_script_tree(_SYN_NOTATION, executor)
    assert tree is not None
    return {_SYN_NOTATION: tree}


# ---------------------------------------------------------------------------
# Router-level verb allowlist (``_ROUTER_VERBS``).
# ---------------------------------------------------------------------------

# The real notation the ``_ROUTER_VERBS`` map keys on. ``ci barrier`` is
# intercepted in ``ci.py::main()`` BEFORE provider argparse dispatch, so it
# never appears in the ``--help`` choices group — the analyzer must accept it
# via the router-verb allowlist rather than flag it as an unknown subcommand.
_CI_NOTATION = 'plan-marshall:tools-integration-ci:ci'


def _ci_router_source() -> str:
    """CI-router shape — provider subcommands only.

    Mirrors the ``ci`` surface as ``--help`` renders it: the provider verbs
    (``branch`` / ``checks`` / ``pr``) are registered subparsers, but the
    provider-agnostic ``barrier`` verb is intercepted in ``main()`` ahead of
    argparse dispatch and is therefore ABSENT from this synthetic surface —
    exactly as it is absent from the real ``ci --help``.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest='cmd')
            for name in ('branch', 'checks', 'pr'):
                p = subparsers.add_parser(name)
                p.add_argument('--flag')
            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


@pytest.fixture
def ci_router_index(tmp_path: Path) -> dict:
    script = tmp_path / 'syn_ci.py'
    script.write_text(_ci_router_source(), encoding='utf-8')
    executor = _make_executor(tmp_path, {_CI_NOTATION: script})
    tree = derive_script_tree(_CI_NOTATION, executor)
    assert tree is not None
    # Guard: the synthetic surface must NOT contain ``barrier`` — the whole
    # point is that the allowlist, not the ``--help`` surface, admits it.
    assert 'barrier' not in tree.known_subcommands()
    return {_CI_NOTATION: tree}


def test_router_verb_barrier_accepted(ci_router_index: dict) -> None:
    """A router-level verb absent from ``--help`` is accepted via the allowlist.

    ``ci barrier`` is intercepted before argparse dispatch, so it is not in the
    derived surface; ``_ROUTER_VERBS`` admits it and the concrete documented
    invocation produces no finding.
    """
    content = (
        'python3 .plan/execute-script.py '
        'plan-marshall:tools-integration-ci:ci barrier '
        '--settled-head SHA --signal ci:pending'
    )
    findings = analyze_manage_invocation_markdown(
        content, 'SKILL.md', ci_router_index
    )
    assert findings == []


def test_non_router_unknown_subcommand_still_flagged(ci_router_index: dict) -> None:
    """The router-verb allowlist does not blanket-accept unknown subcommands.

    A genuinely-unregistered subcommand on the same notation is still flagged —
    only names listed in ``_ROUTER_VERBS`` for the notation are admitted.
    """
    content = (
        'python3 .plan/execute-script.py '
        'plan-marshall:tools-integration-ci:ci bogus --flag x'
    )
    findings = analyze_manage_invocation_markdown(
        content, 'SKILL.md', ci_router_index
    )
    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'subcommand_unknown'


def test_router_verb_unknown_flag_is_flagged(ci_router_index: dict) -> None:
    """A router verb's flags ARE validated — a misspelled/unknown flag is caught.

    ``ci barrier`` is admitted as a valid verb, but its flag surface is modeled
    in ``_ROUTER_VERBS`` and validated with the standard machinery, so a bogus
    flag is reported rather than accepted wholesale (the finding daae30 fix).
    """
    content = (
        'python3 .plan/execute-script.py '
        'plan-marshall:tools-integration-ci:ci barrier '
        '--settled-head SHA --signal ci:pending --bogus x'
    )
    findings = analyze_manage_invocation_markdown(
        content, 'SKILL.md', ci_router_index
    )
    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'flag_unknown'
    assert findings[0]['details']['flag'] == 'bogus'
    assert findings[0]['details']['subcommand'] == 'barrier'


def test_router_verb_missing_required_flag_is_flagged(ci_router_index: dict) -> None:
    """A router verb's required flags are validated — omitting one is flagged."""
    content = (
        'python3 .plan/execute-script.py '
        'plan-marshall:tools-integration-ci:ci barrier --settled-head SHA'
    )
    findings = analyze_manage_invocation_markdown(
        content, 'SKILL.md', ci_router_index
    )
    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'required_flag_missing'
    assert findings[0]['details']['missing'] == ['signal']


def test_router_verb_injected_routing_flags_accepted(ci_router_index: dict) -> None:
    """Executor/router-injected flags (--plan-id) are accepted on a router verb."""
    content = (
        'python3 .plan/execute-script.py '
        'plan-marshall:tools-integration-ci:ci --plan-id p barrier '
        '--settled-head SHA --signal ci:pending'
    )
    findings = analyze_manage_invocation_markdown(
        content, 'SKILL.md', ci_router_index
    )
    assert findings == []


# ---------------------------------------------------------------------------
# Synthetic-marketplace builder — drives the in-scope derivation directly.
# ---------------------------------------------------------------------------


def _write_skill_script(
    bundles_dir: Path,
    bundle: str,
    skill: str,
    script_filename: str,
    *,
    source: str,
    canonical_block: bool = False,
) -> Path:
    """Create a ``{bundle}/skills/{skill}/scripts/{script}`` entry-point.

    Returns the skill directory. When ``canonical_block`` is True the
    SKILL.md carries a ``## Canonical invocations`` section.
    """
    skill_dir = bundles_dir / bundle / 'skills' / skill
    (skill_dir / 'scripts').mkdir(parents=True, exist_ok=True)
    (skill_dir / 'scripts' / script_filename).write_text(source, encoding='utf-8')
    body = '# Skill\n\nDescription.\n'
    if canonical_block:
        body += '\n## Canonical invocations\n\n### run\n\n```bash\nrun --flag x\n```\n'
    (skill_dir / 'SKILL.md').write_text(body, encoding='utf-8')
    return skill_dir


def _build_synthetic_marketplace(tmp_path: Path) -> Path:
    """Create a synthetic marketplace with a representative in-scope set.

    Includes:
      - two script-bearing skills with the canonical block present,
      - two script-bearing skills missing the block,
      - one skill whose entry-point filename differs from the skill name,
      - excluded helper skills and ``manage-findings`` (must NOT be in-scope),
      - a ``_``-prefixed helper module (must NOT be in-scope),
      - a non-argparse script (must NOT be in-scope).
    """
    marketplace_root = tmp_path / 'mp'
    bundles_dir = marketplace_root / 'marketplace' / 'bundles'
    bundles_dir.mkdir(parents=True)

    # In-scope, canonical block present.
    _write_skill_script(
        bundles_dir, 'plan-marshall', 'manage-status', 'manage-status.py',
        source=_minimal_argparse_source(), canonical_block=True,
    )
    _write_skill_script(
        bundles_dir, 'plan-marshall', 'manage-tasks', 'manage-tasks.py',
        source=_minimal_argparse_source(), canonical_block=True,
    )
    # In-scope, canonical block MISSING.
    _write_skill_script(
        bundles_dir, 'plan-marshall', 'manage-config', 'manage-config.py',
        source=_minimal_argparse_source(), canonical_block=False,
    )
    # In-scope, entry-point filename differs from skill name, block missing.
    _write_skill_script(
        bundles_dir, 'plan-marshall', 'plan-doctor', 'plan_doctor.py',
        source=_minimal_argparse_source(), canonical_block=False,
    )

    # Excluded: shared-only helper skill.
    _write_skill_script(
        bundles_dir, 'plan-marshall', 'script-shared', 'helpers.py',
        source=_minimal_argparse_source(), canonical_block=False,
    )
    # Excluded: non-entry-point reference skill.
    _write_skill_script(
        bundles_dir, 'plan-marshall', 'ref-toon-format', 'toon.py',
        source=_minimal_argparse_source(), canonical_block=False,
    )
    # Excluded: manage-findings has its own dedicated analyzer.
    _write_skill_script(
        bundles_dir, 'plan-marshall', 'manage-findings', 'manage-findings.py',
        source=_minimal_argparse_source(), canonical_block=False,
    )

    # Not an entry point: underscore-prefixed helper alongside an entry point.
    logging_skill = bundles_dir / 'plan-marshall' / 'skills' / 'manage-logging'
    helper_scripts = logging_skill / 'scripts'
    helper_scripts.mkdir(parents=True, exist_ok=True)
    (helper_scripts / 'manage-logging.py').write_text(
        _minimal_argparse_source(), encoding='utf-8'
    )
    (helper_scripts / '_internal.py').write_text(
        _minimal_argparse_source(), encoding='utf-8'
    )
    (logging_skill / 'SKILL.md').write_text(
        '# Skill\n\n## Canonical invocations\n\n### run\n\n```bash\nrun --flag x\n```\n',
        encoding='utf-8',
    )

    # Not an entry point: a script that declares no ArgumentParser.
    no_arg_skill = bundles_dir / 'plan-marshall' / 'skills' / 'no-cli-skill' / 'scripts'
    no_arg_skill.mkdir(parents=True, exist_ok=True)
    (no_arg_skill / 'lib.py').write_text(
        'def helper():\n    return 1\n', encoding='utf-8'
    )
    (bundles_dir / 'plan-marshall' / 'skills' / 'no-cli-skill' / 'SKILL.md').write_text(
        '# Skill\n', encoding='utf-8'
    )

    return marketplace_root


def _attach_executor_to_synthetic_marketplace(marketplace_root: Path) -> Path:
    """Wire a synthetic executor mapping the synthetic in-scope notations.

    The executor lives at ``{marketplace_root}/.plan/execute-script.py`` so
    ``_resolve_executor`` discovers it directly under the synthetic root, and
    each in-scope notation resolves to its on-disk script. Returns the
    executor path.
    """
    descriptors = discover_in_scope_scripts(marketplace_root)
    mapping: dict[str, Path] = {}
    for desc in descriptors:
        script_abs = marketplace_root / 'marketplace' / desc.script_relpath
        if not script_abs.is_file():
            script_abs = marketplace_root / desc.script_relpath
        mapping[desc.notation] = script_abs
    return _make_executor(marketplace_root, mapping)


# Notations expected to be in-scope for the synthetic marketplace above.
_EXPECTED_IN_SCOPE = {
    'plan-marshall:manage-status:manage-status',
    'plan-marshall:manage-tasks:manage-tasks',
    'plan-marshall:manage-config:manage-config',
    'plan-marshall:plan-doctor:plan_doctor',
    'plan-marshall:manage-logging:manage-logging',
}
# Notations expected to be EXCLUDED.
_EXPECTED_EXCLUDED = {
    'plan-marshall:script-shared:helpers',
    'plan-marshall:ref-toon-format:toon',
    'plan-marshall:manage-findings:manage-findings',
    'plan-marshall:manage-logging:_internal',
    'plan-marshall:no-cli-skill:lib',
}


# ---------------------------------------------------------------------------
# Layer A — live ``--help`` surface derivation.
# ---------------------------------------------------------------------------


class TestDeriveScriptTree:
    """``derive_script_tree`` reconstructs the surface from live ``--help``."""

    def test_flat_subcommands_derived(self, tmp_path: Path) -> None:
        script = tmp_path / 'syn.py'
        script.write_text(_flat_script_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        assert tree.known_subcommands() == {'foo', 'bar'}

        foo_leaf = tree.get_leaf('foo', None)
        assert foo_leaf is not None
        assert foo_leaf.flags == {'alpha', 'beta'}
        assert foo_leaf.required_flags == {'alpha'}

        bar_leaf = tree.get_leaf('bar', None)
        assert bar_leaf is not None
        assert bar_leaf.flags == {'gamma'}
        assert bar_leaf.required_flags == set()

    def test_root_flags_derived(self, tmp_path: Path) -> None:
        script = tmp_path / 'syn.py'
        script.write_text(_flat_script_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        # ``--debug`` is action='store_true' on the root parser; ``--help``
        # renders it in the root options block.
        assert 'debug' in tree.root.flags

    def test_nested_subcommands_derived(self, tmp_path: Path) -> None:
        script = tmp_path / 'syn.py'
        script.write_text(_nested_script_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        assert tree.known_subcommands() == {'qgate', 'other'}

        # ``qgate`` resolves only with a sub_verb (it is a nested subparser).
        assert tree.get_leaf('qgate', None) is None
        add_leaf = tree.get_leaf('qgate', 'add')
        assert add_leaf is not None
        assert add_leaf.flags == {'plan-id', 'phase'}
        assert add_leaf.required_flags == {'plan-id', 'phase'}

        query_leaf = tree.get_leaf('qgate', 'query')
        assert query_leaf is not None
        assert query_leaf.flags == {'plan-id', 'phase'}
        assert query_leaf.required_flags == {'plan-id'}

        # ``other`` is flat.
        other_leaf = tree.get_leaf('other', None)
        assert other_leaf is not None
        assert other_leaf.flags == {'flag'}

    def test_unreachable_notation_returns_none(self, tmp_path: Path) -> None:
        # Executor maps no notations — ``--help`` produces no usable output.
        executor = _make_executor(tmp_path, {})
        tree = derive_script_tree('plan-marshall:absent:absent', executor)
        assert tree is None


class TestAnsiColoredHelp:
    """ANSI-colored ``--help`` output must yield the same surface as plain text.

    Regression guard for the color-corruption bug: Python 3.14 colorizes
    ``argparse --help``, and the SGR escapes around ``usage:``, the subcommand
    choices, and the ``--flag`` tokens defeat the plain-text surface regexes,
    so surface derivation collapsed to an EMPTY tree and the analyzer emitted
    ~865 false ``manage-invocation-invalid`` findings. The fix strips ANSI
    escapes (and runs the probe with a color-suppressed env) before parsing.
    This test fails against the pre-fix analyzer (colored ``--help`` -> empty
    surface) and passes against the fixed analyzer.
    """

    def test_colored_help_matches_plain_surface(self, tmp_path: Path) -> None:
        # Arrange — a plain flat script and an ANSI-colored clone of the same shape.
        plain_script = tmp_path / 'syn_plain.py'
        plain_script.write_text(_flat_script_source(), encoding='utf-8')
        colored_script = tmp_path / 'syn_colored.py'
        colored_script.write_text(_ansi_colored_script_source(), encoding='utf-8')
        plain_notation = 'plan-marshall:manage-plain:manage-plain'
        colored_notation = 'plan-marshall:manage-colored:manage-colored'
        executor = _make_executor(
            tmp_path,
            {plain_notation: plain_script, colored_notation: colored_script},
        )

        # Act — derive the surface from each script's live ``--help``.
        plain_tree = derive_script_tree(plain_notation, executor)
        colored_tree = derive_script_tree(colored_notation, executor)

        # Assert — the colored surface is non-empty and identical to the plain one.
        assert plain_tree is not None
        assert colored_tree is not None
        assert colored_tree.to_dict() == plain_tree.to_dict()

    def test_colored_help_resolves_full_flag_surface(self, tmp_path: Path) -> None:
        # Arrange — an ANSI-colored --help script with a known surface.
        colored_script = tmp_path / 'syn_colored.py'
        colored_script.write_text(_ansi_colored_script_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: colored_script})

        # Act — derive the surface (the ANSI-strip + clean-env path).
        tree = derive_script_tree(_SYN_NOTATION, executor)

        # Assert — subcommands and per-leaf flags survive the colored --help.
        assert tree is not None
        assert tree.known_subcommands() == {'foo', 'bar'}
        assert 'debug' in tree.root.flags

        foo_leaf = tree.get_leaf('foo', None)
        assert foo_leaf is not None
        assert foo_leaf.flags == {'alpha', 'beta'}
        assert foo_leaf.required_flags == {'alpha'}

        bar_leaf = tree.get_leaf('bar', None)
        assert bar_leaf is not None
        assert bar_leaf.flags == {'gamma'}


class TestLoopRegisteredSubcommands:
    """Subcommands registered through a ``for`` loop are visible via ``--help``.

    This is the catastrophic false-positive that AST extraction produced:
    ``manage-logging work`` / ``manage-logging decision`` are loop-registered,
    so the old extractor saw NO subcommands and flagged every valid
    invocation as ``subcommand_unknown``.
    """

    def test_all_loop_subcommands_derived(self, tmp_path: Path) -> None:
        script = tmp_path / 'mlog.py'
        script.write_text(_loop_registered_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        assert tree.known_subcommands() == {
            'script', 'work', 'decision', 'separator', 'read'
        }

    def test_loop_registered_invocation_is_not_flagged(self, tmp_path: Path) -> None:
        script = tmp_path / 'mlog.py'
        script.write_text(_loop_registered_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        index = {_SYN_NOTATION: tree}
        # The canonical ``work`` invocation must produce ZERO findings — it is
        # the exact false-positive shape the pivot fixes.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} work '
            f'--plan-id p --level INFO --message "[STATUS] hi"\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        assert findings == []

    def test_unknown_subcommand_still_flagged(self, tmp_path: Path) -> None:
        script = tmp_path / 'mlog.py'
        script.write_text(_loop_registered_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        index = {_SYN_NOTATION: tree}
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} not-a-verb --plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'subcommand_unknown'


class TestManySubcommandScript:
    """A many-subcommand script (manage-status shape) is fully enumerated."""

    def test_all_subcommands_derived(self, tmp_path: Path) -> None:
        script = tmp_path / 'mstat.py'
        script.write_text(_many_subcommand_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        subs = tree.known_subcommands()
        assert len(subs) == 20
        # Spot-check the verbs the AST extractor most commonly dropped.
        for verb in ('metadata', 'get-worktree-path', 'transition', 'self-test'):
            assert verb in subs

    def test_helper_registered_subcommand_invocation_clean(
        self, tmp_path: Path
    ) -> None:
        script = tmp_path / 'mstat.py'
        script.write_text(_many_subcommand_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        index = {_SYN_NOTATION: tree}
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} get-worktree-path '
            f'--plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        assert findings == []


class TestSharedFlagAcrossSubcommands:
    """A flag added to every subcommand via a helper is visible per-leaf."""

    def test_shared_flag_present_on_each_leaf(self, tmp_path: Path) -> None:
        script = tmp_path / 'shared.py'
        script.write_text(_shared_flag_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        for sub in ('update', 'finalize-step'):
            leaf = tree.get_leaf(sub, None)
            assert leaf is not None
            assert {'plan-id', 'task-number', 'status'} <= leaf.flags
            assert {'plan-id', 'task-number'} <= leaf.required_flags

    def test_shared_flag_invocation_not_flagged(self, tmp_path: Path) -> None:
        script = tmp_path / 'shared.py'
        script.write_text(_shared_flag_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        index = {_SYN_NOTATION: tree}
        # ``--plan-id`` / ``--task-number`` are shared — neither is unknown.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} finalize-step '
            f'--plan-id p --task-number 3 --status done\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        assert findings == []

    def test_missing_shared_required_flag_is_flagged(self, tmp_path: Path) -> None:
        script = tmp_path / 'shared.py'
        script.write_text(_shared_flag_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        index = {_SYN_NOTATION: tree}
        # Omit the required ``--task-number``.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} finalize-step '
            f'--plan-id p --status done\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'required_flag_missing'
        assert findings[0]['details']['missing'] == ['task-number']


# ---------------------------------------------------------------------------
# Layer B — positive cases (canonical invocations produce no findings).
# ---------------------------------------------------------------------------


class TestPositiveCanonicalInvocations:
    """Each script accepts a canonical invocation cleanly."""

    def test_flat_subcommand_canonical_clean(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --alpha v1 --beta v2\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_nested_subcommand_canonical_clean(self, nested_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate add --plan-id p1 --phase phase-5-execute\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert findings == []

    def test_unknown_notation_is_skipped(self, flat_index: dict) -> None:
        """Notations not in the script_index are silently passed over."""
        content = (
            'python3 .plan/execute-script.py some-bundle:some-skill:some-script anything --x y\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []


# ---------------------------------------------------------------------------
# Layer B2 — in-scope derivation (discover_in_scope_scripts).
# ---------------------------------------------------------------------------


class TestDiscoverInScopeScripts:
    """``discover_in_scope_scripts`` auto-derives coverage from the bundle tree."""

    def test_derives_expected_in_scope_set(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        descriptors = discover_in_scope_scripts(marketplace_root)
        notations = {d.notation for d in descriptors}
        assert notations == _EXPECTED_IN_SCOPE

    def test_excludes_shared_reference_findings_and_helpers(
        self, tmp_path: Path
    ) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        descriptors = discover_in_scope_scripts(marketplace_root)
        notations = {d.notation for d in descriptors}
        for excluded in _EXPECTED_EXCLUDED:
            assert excluded not in notations, f'{excluded} must be excluded'

    def test_underscore_prefixed_scripts_are_skipped(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        descriptors = discover_in_scope_scripts(marketplace_root)
        thirds = {d.notation.split(':')[-1] for d in descriptors}
        assert '_internal' not in thirds

    def test_non_argparse_scripts_are_skipped(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        descriptors = discover_in_scope_scripts(marketplace_root)
        notations = {d.notation for d in descriptors}
        assert 'plan-marshall:no-cli-skill:lib' not in notations

    def test_third_segment_is_script_stem_not_skill_name(
        self, tmp_path: Path
    ) -> None:
        """A skill whose entry-point filename differs from the skill name is
        keyed off the script stem, not a filename==skill assumption."""
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        descriptors = discover_in_scope_scripts(marketplace_root)
        by_notation = {d.notation: d for d in descriptors}
        assert 'plan-marshall:plan-doctor:plan_doctor' in by_notation

    def test_descriptor_relpaths_resolve(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        descriptors = discover_in_scope_scripts(marketplace_root)
        for desc in descriptors:
            assert desc.script_relpath.startswith('bundles/')
            assert desc.skill_dir_relpath.startswith('bundles/')
            script_abs = marketplace_root / 'marketplace' / desc.script_relpath
            assert script_abs.is_file()

    def test_results_are_sorted_by_notation(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        descriptors = discover_in_scope_scripts(marketplace_root)
        notations = [d.notation for d in descriptors]
        assert notations == sorted(notations)

    def test_missing_bundles_dir_returns_empty(self, tmp_path: Path) -> None:
        empty = tmp_path / 'empty'
        empty.mkdir()
        assert discover_in_scope_scripts(empty) == ()


# ---------------------------------------------------------------------------
# Layer C — negative cases (one per finding type).
# ---------------------------------------------------------------------------


class TestUnknownSubcommand:
    """An unregistered top-level subcommand produces one finding."""

    def test_unknown_subcommand_is_flagged(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} zzz --alpha v1\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        assert f['details']['reason'] == 'subcommand_unknown'
        assert f['details']['subcommand'] == 'zzz'
        assert set(f['details']['known_subcommands']) == {'foo', 'bar'}
        assert 'canonical_hint' in f['details']

    def test_subcommand_finding_short_circuits_flag_validation(
        self, flat_index: dict
    ) -> None:
        """When subcommand is unknown, no flag findings are emitted on the same line."""
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} zzz --not-a-real-flag\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'subcommand_unknown'


class TestUnknownSubVerb:
    """An unregistered sub-verb under a nested subparser produces one finding."""

    def test_unknown_sub_verb_is_flagged(self, nested_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate banana --plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'sub_verb_unknown'
        assert f['details']['subcommand'] == 'qgate'
        assert f['details']['sub_verb'] == 'banana'
        assert set(f['details']['known_sub_verbs']) == {'add', 'query'}
        # Lock down the documented severity and the canonical_hint payload on
        # the sub-verb path, matching the sibling unknown-subcommand test.
        assert f['severity'] == 'error'
        assert 'canonical_hint' in f['details']
        assert f['details']['canonical_hint']

    def test_missing_sub_verb_is_flagged(self, nested_index: dict) -> None:
        """``qgate`` without a sub-verb still produces a sub_verb_unknown finding."""
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate --plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'sub_verb_unknown'
        assert findings[0]['details']['sub_verb'] is None


class TestUnknownFlag:
    """An unregistered long flag under a resolved leaf parser is flagged."""

    def test_unknown_flag_on_flat_subcommand(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --alpha v --not-a-flag z\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        # One finding for the unknown flag. No missing-required finding because
        # --alpha is satisfied.
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'flag_unknown'
        assert f['details']['flag'] == 'not-a-flag'
        # ``known_flags`` reports the full set the analyzer validated against:
        # the leaf's own flags PLUS the ancestor union (root ``--debug``) PLUS
        # the universal executor-injected allowlist. The leaf flags are always
        # a subset; the genuinely-unknown flag must never appear.
        known = set(f['details']['known_flags'])
        assert {'alpha', 'beta'} <= known
        assert 'debug' in known  # root flag surfaced via the ancestor union
        assert 'not-a-flag' not in known

    def test_unknown_flag_on_nested_sub_verb(self, nested_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate add --plan-id p --phase ph --bogus z\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        # Required flags are satisfied — only the unknown-flag finding fires.
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'flag_unknown'
        assert findings[0]['details']['flag'] == 'bogus'


class TestMissingRequiredFlag:
    """A missing required flag produces one finding."""

    def test_missing_required_on_flat_subcommand(self, flat_index: dict) -> None:
        # ``foo`` requires --alpha; invocation omits it.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --beta v2\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'required_flag_missing'
        assert f['details']['missing'] == ['alpha']
        assert set(f['details']['required_flags']) == {'alpha'}

    def test_missing_required_on_nested_sub_verb(self, nested_index: dict) -> None:
        # ``qgate add`` requires both --plan-id and --phase; omit one.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate add --plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'required_flag_missing'
        assert f['details']['missing'] == ['phase']


# ---------------------------------------------------------------------------
# Layer D — missing-canonical-block rule (per in-scope SKILL.md).
# ---------------------------------------------------------------------------


class TestMissingCanonicalBlock:
    """SKILL.md without ``## Canonical invocations`` produces a finding."""

    def test_missing_block_flagged_only_for_skills_without_section(
        self, tmp_path: Path
    ) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        findings = check_missing_canonical_blocks(marketplace_root)
        flagged = {f['details']['notation'] for f in findings}
        # manage-config and plan-doctor lack the section; the rest of the
        # in-scope set carries it.
        assert flagged == {
            'plan-marshall:manage-config:manage-config',
            'plan-marshall:plan-doctor:plan_doctor',
        }
        for f in findings:
            assert f['rule_id'] == RULE_MISSING_CANONICAL_BLOCK
            assert f['severity'] == 'warning'
            assert f['details']['reason'] == 'missing_canonical_block'
            assert 'canonical_hint' in f['details']

    def test_present_block_is_not_flagged(self, tmp_path: Path) -> None:
        marketplace_root = tmp_path / 'mp'
        bundles_dir = marketplace_root / 'marketplace' / 'bundles'
        bundles_dir.mkdir(parents=True)
        _write_skill_script(
            bundles_dir, 'plan-marshall', 'manage-status', 'manage-status.py',
            source=_minimal_argparse_source(), canonical_block=True,
        )
        findings = check_missing_canonical_blocks(marketplace_root)
        assert findings == []

    def test_block_heading_is_case_insensitive(self, tmp_path: Path) -> None:
        marketplace_root = tmp_path / 'mp'
        bundles_dir = marketplace_root / 'marketplace' / 'bundles'
        bundles_dir.mkdir(parents=True)
        skill_dir = _write_skill_script(
            bundles_dir, 'plan-marshall', 'manage-status', 'manage-status.py',
            source=_minimal_argparse_source(), canonical_block=False,
        )
        (skill_dir / 'SKILL.md').write_text(
            '# Skill\n\n## canonical INVOCATIONS\n\n### run\n',
            encoding='utf-8',
        )
        findings = check_missing_canonical_blocks(marketplace_root)
        assert findings == []

    def test_excluded_skill_not_flagged_for_missing_block(
        self, tmp_path: Path
    ) -> None:
        """A shared-only skill without the section is NOT flagged (out of scope)."""
        marketplace_root = tmp_path / 'mp'
        bundles_dir = marketplace_root / 'marketplace' / 'bundles'
        bundles_dir.mkdir(parents=True)
        _write_skill_script(
            bundles_dir, 'plan-marshall', 'script-shared', 'helpers.py',
            source=_minimal_argparse_source(), canonical_block=False,
        )
        findings = check_missing_canonical_blocks(marketplace_root)
        assert findings == []


# ---------------------------------------------------------------------------
# Layer E — per-skill scanner end-to-end.
# ---------------------------------------------------------------------------


class TestSkillScanner:
    """``scan_skill_for_manage_invocation`` walks SKILL.md + standards/refs/etc."""

    def test_scanner_picks_up_skill_md_invocations(
        self, tmp_path: Path, flat_index: dict
    ) -> None:
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        (skill_dir / 'SKILL.md').write_text(
            f'# Skill\npython3 .plan/execute-script.py {_SYN_NOTATION} zzz --x y\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_manage_invocation(skill_dir, flat_index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'subcommand_unknown'
        assert findings[0]['file'].endswith('SKILL.md')

    def test_scanner_aggregates_subdoc_findings(
        self, tmp_path: Path, flat_index: dict
    ) -> None:
        skill_dir = tmp_path / 'my-skill'
        (skill_dir / 'standards').mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text('# clean\n', encoding='utf-8')
        (skill_dir / 'standards' / 'rules.md').write_text(
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --bogus z\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_manage_invocation(skill_dir, flat_index)
        # ``foo`` is registered (no subcommand finding), --alpha is missing
        # (required_flag_missing), and --bogus is unknown (flag_unknown).
        reasons = {f['details']['reason'] for f in findings}
        assert reasons == {'flag_unknown', 'required_flag_missing'}

    def test_scanner_returns_empty_for_clean_skill(
        self, tmp_path: Path, flat_index: dict
    ) -> None:
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        (skill_dir / 'SKILL.md').write_text(
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --alpha v\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_manage_invocation(skill_dir, flat_index)
        assert findings == []

    def test_scanner_handles_missing_directory(
        self, tmp_path: Path, flat_index: dict
    ) -> None:
        findings = scan_skill_for_manage_invocation(
            tmp_path / 'nonexistent', flat_index
        )
        assert findings == []


# ---------------------------------------------------------------------------
# Layer F — Finding payload shape (schema contract).
# ---------------------------------------------------------------------------


class TestFindingPayloadShape:
    """All findings carry the documented schema fields."""

    def test_payload_contains_required_keys_invocation_rule(
        self, flat_index: dict
    ) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} zzz --alpha v\n'
        )
        findings = analyze_manage_invocation_markdown(
            content, '/path/to/SKILL.md', flat_index
        )
        assert findings
        f = findings[0]
        for key in (
            'rule_id',
            'type',
            'file',
            'line',
            'severity',
            'fixable',
            'description',
            'details',
        ):
            assert key in f, f'missing required key {key}'
        assert f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        assert f['type'] == RULE_MANAGE_INVOCATION_INVALID
        assert f['file'] == '/path/to/SKILL.md'
        assert isinstance(f['line'], int) and f['line'] >= 1
        assert f['severity'] == 'error'
        assert f['fixable'] is False

    def test_payload_contains_required_keys_canonical_block_rule(
        self, tmp_path: Path
    ) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        findings = check_missing_canonical_blocks(marketplace_root)
        assert findings
        f = findings[0]
        for key in (
            'rule_id',
            'type',
            'file',
            'line',
            'severity',
            'fixable',
            'description',
            'details',
        ):
            assert key in f, f'missing required key {key}'
        assert f['rule_id'] == RULE_MISSING_CANONICAL_BLOCK
        assert f['severity'] == 'warning'
        assert f['line'] == 1

    def test_canonical_hint_present_in_details(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --bogus v\n'
        )
        findings = analyze_manage_invocation_markdown(
            content, '/fake/SKILL.md', flat_index
        )
        assert findings
        details = findings[0]['details']
        assert 'canonical_hint' in details
        assert _SYN_NOTATION in details['canonical_hint']

    def test_line_number_anchored(self, flat_index: dict) -> None:
        content = (
            '# Title\n'
            '\n'
            '\n'
            f'python3 .plan/execute-script.py {_SYN_NOTATION} zzz --alpha v\n'
        )
        findings = analyze_manage_invocation_markdown(
            content, '/fake/SKILL.md', flat_index
        )
        assert findings
        assert findings[0]['line'] == 4


# ---------------------------------------------------------------------------
# Layer G — Marketplace-wide aggregator + build_script_index resolution.
# ---------------------------------------------------------------------------


class TestMarketplaceAggregator:
    """``scan_manage_invocation`` combines markdown + canonical-block findings."""

    def test_index_resolves_in_scope_scripts(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        _attach_executor_to_synthetic_marketplace(marketplace_root)
        index = build_script_index(marketplace_root)
        assert set(index.keys()) == _EXPECTED_IN_SCOPE

    def test_index_empty_without_executor(self, tmp_path: Path) -> None:
        """Without an executor the surface cannot be probed — index is empty
        (no false positives)."""
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        index = build_script_index(marketplace_root)
        assert index == {}

    def test_aggregator_runs_both_rules(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        _attach_executor_to_synthetic_marketplace(marketplace_root)
        bundles_dir = marketplace_root / 'marketplace' / 'bundles'
        # Add one consumer bundle markdown with a bad invocation against an
        # in-scope notation (the synthetic script declares ``run``).
        consumer_md = (
            bundles_dir / 'consumer-bundle' / 'skills' / 'consumer-skill' / 'SKILL.md'
        )
        consumer_md.parent.mkdir(parents=True)
        consumer_md.write_text(
            'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status zzz --x y\n',
            encoding='utf-8',
        )

        findings = scan_manage_invocation(marketplace_root)
        rule_ids = {f['rule_id'] for f in findings}
        assert RULE_MANAGE_INVOCATION_INVALID in rule_ids
        assert RULE_MISSING_CANONICAL_BLOCK in rule_ids

    def test_aggregator_clean_marketplace_has_no_findings(self, tmp_path: Path) -> None:
        """A marketplace where every in-scope skill has the block and no doc
        carries a bad invocation produces zero findings."""
        marketplace_root = tmp_path / 'mp'
        bundles_dir = marketplace_root / 'marketplace' / 'bundles'
        bundles_dir.mkdir(parents=True)
        _write_skill_script(
            bundles_dir, 'plan-marshall', 'manage-status', 'manage-status.py',
            source=_minimal_argparse_source(), canonical_block=True,
        )
        _attach_executor_to_synthetic_marketplace(marketplace_root)
        findings = scan_manage_invocation(marketplace_root)
        assert findings == []


# ---------------------------------------------------------------------------
# Layer H — quality-gate wiring (direct cmd_quality_gate invocation).
# ---------------------------------------------------------------------------


def _load_doctor_marketplace():
    """Load ``doctor-marketplace.py`` for direct ``cmd_quality_gate`` calls.

    Uses the shared ``load_script_module`` helper (the loader convention this
    module standardized on) so no direct ``importlib`` / ``sys`` plumbing is
    needed here.
    """
    return _load_module('doctor_marketplace_for_invocation_test', 'doctor-marketplace.py')


class _Args:
    """Minimal argparse-namespace stand-in for direct cmd_* calls."""

    def __init__(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestTemplatedInvocationSkip:
    """Templated / usage-string invocations are skipped, not flagged.

    A concrete consumer call is the only thing the rule validates. Placeholder
    (``{...}`` / ``<...>``) and usage-syntax (``[...]`` / ``|`` / ``...``)
    tokens in the subcommand/sub-verb region mark a non-concrete invocation —
    a templated example or a ``## Canonical invocations`` usage string — which
    cannot be resolved against the canonical tree and must not produce
    spurious findings.
    """

    def test_predicate_detects_placeholders_in_positional_region(self) -> None:
        assert _positional_region_is_templated(' plan {phase} get')
        assert _positional_region_is_templated(' {command} {args}')
        assert _positional_region_is_templated(' foo <subcommand>')

    def test_predicate_detects_usage_syntax(self) -> None:
        assert _positional_region_is_templated(' [--project-dir | --plan-id] list')
        assert _positional_region_is_templated(' ...')
        assert _positional_region_is_templated(' qgate ...')

    def test_predicate_ignores_template_syntax_in_flag_values(self) -> None:
        # A placeholder AFTER the first flag (a flag value) is not a templated
        # positional region — the subcommand chain is still concrete.
        assert not _positional_region_is_templated(' metadata --set k={value}')
        assert not _positional_region_is_templated(' foo --alpha {x}')

    def test_predicate_passes_concrete_invocations(self) -> None:
        assert not _positional_region_is_templated(' foo --alpha v')
        assert not _positional_region_is_templated(' qgate add --plan-id p --phase ph')

    def test_placeholder_subverb_not_flagged(self, nested_index: dict) -> None:
        # ``qgate`` requires a sub-verb; a ``{sub}`` placeholder stands for a
        # real one — do not flag sub_verb_unknown.
        content = f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate {{sub}} --plan-id p\n'
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert findings == []

    def test_placeholder_subcommand_not_flagged(self, flat_index: dict) -> None:
        content = f'python3 .plan/execute-script.py {_SYN_NOTATION} {{cmd}} --alpha v\n'
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_usage_string_bracket_group_not_flagged(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} '
            f'[--debug] foo --alpha v\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_ellipsis_prose_mention_not_flagged(self, flat_index: dict) -> None:
        content = f'Run `python3 .plan/execute-script.py {_SYN_NOTATION} ...` exactly.\n'
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_flag_value_placeholder_still_validates_subcommand(self, nested_index: dict) -> None:
        # Placeholder only in a flag value — the concrete sub-verb chain is
        # still validated, so a genuinely-unknown flag is still caught.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate add '
            f'--plan-id {{pid}} --phase {{ph}} --nope z\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'flag_unknown'
        assert findings[0]['details']['flag'] == 'nope'


class TestQualityGateWiring:
    """``cmd_quality_gate`` runs the manage-invocation cluster as a build gate."""

    def test_quality_gate_imports_scan_manage_invocation(self) -> None:
        """The single-pass runner imports the manage-invocation scanner.

        The quality-gate dispatch (including the manage-invocation cluster) is
        driven by ``_runner.RuleRunner.run_quality_gate``, so the scanner import
        lives on the runner module rather than the doctor-marketplace CLI
        orchestrator.
        """
        runner = _load_module('_runner', '_runner.py')
        assert hasattr(runner, 'scan_manage_invocation')

    def test_quality_gate_runs_manage_invocation_cluster(self, tmp_path: Path) -> None:
        """cmd_quality_gate lists scan_manage_invocation in rules_run and
        surfaces its findings against a synthetic tree carrying a bad
        invocation."""
        dm = _load_doctor_marketplace()
        marketplace_root = _build_synthetic_marketplace(tmp_path)
        # The executor must live where ``_resolve_executor`` looks relative to
        # the inner root the gate passes — i.e. under the inner ``marketplace``
        # dir's parent. Attaching at the synthetic root covers the
        # ``marketplace_root.parent`` candidate.
        _attach_executor_to_synthetic_marketplace(marketplace_root)
        # Add a consumer doc with a bad invocation so the rule fires.
        bundles_dir = marketplace_root / 'marketplace' / 'bundles'
        consumer_md = (
            bundles_dir / 'consumer-bundle' / 'skills' / 'consumer-skill' / 'SKILL.md'
        )
        consumer_md.parent.mkdir(parents=True)
        consumer_md.write_text(
            'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status zzz --x y\n',
            encoding='utf-8',
        )
        # Point find_marketplace_root at the dir that directly contains bundles/.
        inner_root = marketplace_root / 'marketplace'
        args = _Args(marketplace_root=str(inner_root))
        result = dm.cmd_quality_gate(args)
        # The gate fails (the bad invocation plus minimal-fixture argparse
        # findings are present); the manage-invocation rule must be wired in.
        assert result['status'] == 'fail'
        rules_run = {r['rule'] for r in result['rules_run']}
        assert 'scan_manage_invocation' in rules_run
        rule_ids = {issue.get('rule_id') for issue in result['issues']}
        assert RULE_MANAGE_INVOCATION_INVALID in rule_ids

    def test_quality_gate_help_documents_rule(self) -> None:
        """The cmd_quality_gate docstring names the scan_manage_invocation rule."""
        dm = _load_doctor_marketplace()
        assert 'scan_manage_invocation' in (dm.cmd_quality_gate.__doc__ or '')

    def test_analyze_does_not_run_manage_invocation_cluster(self) -> None:
        """cmd_analyze must NOT run the live-``--help`` manage-invocation rule.

        The rule derives each script's surface from its ``--help`` output (one
        subprocess per parser node) and belongs only to the marketplace-wide
        ``cmd_quality_gate``. Running it on every per-component ``analyze`` pass
        cold-derives the whole marketplace surface and overruns the test
        harness's per-call subprocess budget (``test_analyze_returns_valid_toon``
        timed out at 30s under a cold CI cache). This guard fails if a future
        change re-wires the expensive rule back into the analyze path.
        """
        import inspect

        dm = _load_doctor_marketplace()
        src = inspect.getsource(dm.cmd_analyze)
        assert 'scan_manage_invocation' not in src, (
            'cmd_analyze must not invoke scan_manage_invocation — the live-help '
            'surface derivation is too slow for per-component analyze; it lives '
            'in cmd_quality_gate only'
        )


# ---------------------------------------------------------------------------
# Layer I — robustness fixes carried forward (PR #372 review feedback).
# ---------------------------------------------------------------------------


class TestMultiLineBackslashContinuation:
    """Backslash-continued invocations are joined before flag validation."""

    def test_flags_on_continuation_lines_are_recognized(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo \\\n'
            f'  --alpha v1 \\\n'
            f'  --beta v2\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_continuation_does_not_swallow_unknown_flag(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo \\\n'
            f'  --alpha v1 \\\n'
            f'  --nope v3\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'flag_unknown'
        assert f['details']['flag'] == 'nope'

    def test_finding_line_anchored_to_logical_start(self, flat_index: dict) -> None:
        content = (
            '# heading\n'  # line 1
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --alpha v \\\n'  # line 2
            '  --nope v\n'  # line 3 (physical-only)
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        assert findings[0]['line'] == 2
        assert findings[0]['details']['reason'] == 'flag_unknown'


class TestShellQuotingFalsePositives:
    """Flag-like text inside quoted argument values is not parsed as a flag."""

    def test_double_quoted_value_with_dashes_is_not_a_flag(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo '
            f'--alpha "release: --not-a-flag"\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_single_quoted_value_with_dashes_is_not_a_flag(self, flat_index: dict) -> None:
        content = (
            f"python3 .plan/execute-script.py {_SYN_NOTATION} foo "
            f"--alpha '--not-a-flag'\n"
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_unquoted_flag_still_validated(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo '
            f'--alpha "in quotes --safe" --nope unsafe\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'flag_unknown'
        assert findings[0]['details']['flag'] == 'nope'


class TestFlatSubcommandWithPositionalArgs:
    """A flat subcommand that accepts positional args still gets flag validation."""

    def test_positional_after_flat_subcommand_does_not_block_flag_check(
        self, tmp_path: Path
    ) -> None:
        script = tmp_path / 'syn.py'
        script.write_text(
            textwrap.dedent('''
                import argparse

                def main():
                    parser = argparse.ArgumentParser()
                    subparsers = parser.add_subparsers(dest='command')
                    path = subparsers.add_parser('path')
                    path.add_argument('source')
                    path.add_argument('target')
                    path.add_argument('--json', action='store_true')
                    parser.parse_args()

                if __name__ == '__main__':
                    main()
            ''').lstrip(),
            encoding='utf-8',
        )
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None

        index = {_SYN_NOTATION: tree}
        clean = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} path src dst --json\n'
        )
        findings = analyze_manage_invocation_markdown(clean, '/fake/SKILL.md', index)
        assert findings == []

        bad = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} path src dst --nope\n'
        )
        findings = analyze_manage_invocation_markdown(bad, '/fake/SKILL.md', index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'flag_unknown'
        assert findings[0]['details']['flag'] == 'nope'


class TestMutuallyExclusiveGroupSupport:
    """Flags declared on ``add_mutually_exclusive_group`` are honored.

    Group-level flags render in the leaf's ``--help`` options block exactly
    like any other flag, so ``--help`` derivation captures them with no
    special-casing.
    """

    def test_group_flags_attach_to_parent_leaf(self, tmp_path: Path) -> None:
        script = tmp_path / 'syn.py'
        script.write_text(
            textwrap.dedent('''
                import argparse

                def main():
                    parser = argparse.ArgumentParser()
                    subparsers = parser.add_subparsers(dest='command')
                    run = subparsers.add_parser('run')
                    group = run.add_mutually_exclusive_group(required=True)
                    group.add_argument('--by-id')
                    group.add_argument('--by-name')
                    run.add_argument('--debug', action='store_true')
                    parser.parse_args()

                if __name__ == '__main__':
                    main()
            ''').lstrip(),
            encoding='utf-8',
        )
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        leaf = tree.get_leaf('run', None)
        assert leaf is not None
        assert leaf.flags == {'by-id', 'by-name', 'debug'}

    def test_argument_group_flags_attach_to_parent_leaf(self, tmp_path: Path) -> None:
        script = tmp_path / 'syn.py'
        script.write_text(
            textwrap.dedent('''
                import argparse

                def main():
                    parser = argparse.ArgumentParser()
                    subparsers = parser.add_subparsers(dest='command')
                    run = subparsers.add_parser('run')
                    grp = run.add_argument_group('output')
                    grp.add_argument('--json', action='store_true')
                    grp.add_argument('--quiet', action='store_true')
                    parser.parse_args()

                if __name__ == '__main__':
                    main()
            ''').lstrip(),
            encoding='utf-8',
        )
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        leaf = tree.get_leaf('run', None)
        assert leaf is not None
        assert leaf.flags == {'json', 'quiet'}


# ---------------------------------------------------------------------------
# Layer I2 — parent-inherited flags, ancestor-union, and universal allowlist.
# ---------------------------------------------------------------------------


def _parents_inherited_source() -> str:
    """``parents=[...]`` shape — a common parent flag inherited by subcommands.

    A shared ``--plan-id`` is declared ONCE on a ``parents=[common]`` parser and
    inherited by every subcommand. argparse copies the parent's action into each
    child, so the flag is valid on ``run`` / ``check`` even though it is never
    declared directly on either subcommand. The analyzer must accept it — the
    AST extractor never modelled ``parents=`` at all, and per-leaf ``--help``
    validation mis-flags any flag argparse renders only on the parent.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            common = argparse.ArgumentParser(add_help=False)
            common.add_argument('--plan-id')

            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest='cmd')

            run = subparsers.add_parser('run', parents=[common])
            run.add_argument('--flag')

            check = subparsers.add_parser('check', parents=[common])
            check.add_argument('--strict', action='store_true')

            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _root_flag_source() -> str:
    """A flag declared on the ROOT parser, honored by every subcommand.

    ``--project-dir`` is added to the top-level parser before subparser
    dispatch. argparse accepts it on every subcommand, but renders it ONLY in
    the root ``--help`` options block — never in a subcommand's. The
    ancestor-union must accept it at the leaf; per-leaf validation alone would
    mis-flag it.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser()
            parser.add_argument('--project-dir')
            subparsers = parser.add_subparsers(dest='cmd')
            run = subparsers.add_parser('run')
            run.add_argument('--flag')
            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


class TestParentInheritedFlags:
    """Flags inherited via ``parents=[...]`` are accepted on each subcommand."""

    def test_parent_flag_accepted_on_each_subcommand(self, tmp_path: Path) -> None:
        script = tmp_path / 'syn.py'
        script.write_text(_parents_inherited_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        index = {_SYN_NOTATION: tree}
        # ``--plan-id`` is inherited from the ``parents=[common]`` parser; it
        # must NOT be flagged as unknown on either subcommand.
        for sub in ('run', 'check'):
            content = (
                f'python3 .plan/execute-script.py {_SYN_NOTATION} {sub} --plan-id p\n'
            )
            findings = analyze_manage_invocation_markdown(
                content, '/fake/SKILL.md', index
            )
            invalid = [
                f for f in findings
                if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
            ]
            assert invalid == [], f'parent-inherited --plan-id flagged on {sub}: {invalid}'

    def test_genuinely_unknown_flag_still_flagged_with_parents(
        self, tmp_path: Path
    ) -> None:
        script = tmp_path / 'syn.py'
        script.write_text(_parents_inherited_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        index = {_SYN_NOTATION: tree}
        # A flag neither inherited nor declared anywhere is still a real defect.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} run --plan-id p --bogus z\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        invalid = [
            f for f in findings if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        ]
        assert len(invalid) == 1
        assert invalid[0]['details']['reason'] == 'flag_unknown'
        assert invalid[0]['details']['flag'] == 'bogus'


class TestRootFlagAncestorUnion:
    """A root-declared flag is accepted on subcommands via the ancestor union."""

    def test_root_flag_accepted_on_subcommand(self, tmp_path: Path) -> None:
        script = tmp_path / 'syn.py'
        script.write_text(_root_flag_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        index = {_SYN_NOTATION: tree}
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} run '
            f'--flag v --project-dir /x\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        invalid = [
            f for f in findings if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        ]
        assert invalid == [], f'root-declared --project-dir flagged on subcommand: {invalid}'


class TestUniversalFlagAllowlist:
    """Executor-injected universal flags are accepted on any leaf.

    ``--audit-plan-id`` is stripped by the executor wrapper before the target
    script's argparse runs, so it appears in NO node's ``--help`` surface. The
    universal allowlist guarantees it is never flagged even when the
    ancestor-union does not contain it.
    """

    def test_audit_plan_id_never_flagged(self, flat_index: dict) -> None:
        # ``foo`` declares --alpha (required) / --beta; --audit-plan-id is in no
        # node's surface but is executor-injected and must be accepted.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo '
            f'--alpha v --audit-plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        invalid = [
            f for f in findings if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        ]
        assert invalid == [], f'executor-injected --audit-plan-id flagged: {invalid}'

    def test_universal_allowlist_does_not_mask_real_unknown_flag(
        self, flat_index: dict
    ) -> None:
        # --audit-plan-id is allowlisted; --bogus is still a real unknown flag.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo '
            f'--alpha v --audit-plan-id p --bogus z\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        invalid = [
            f for f in findings if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        ]
        assert len(invalid) == 1
        assert invalid[0]['details']['flag'] == 'bogus'


def _routing_flag_nested_source() -> str:
    """A top-level routing flag declared BEFORE the subcommand, plus a nested
    sub-verb chain — the real ``ci``/``sonar`` shape.

    ``--project-dir`` is a top-level routing/global flag consumed by the router
    argparse layer before the subcommand positional. ``pr`` is a nested
    subcommand whose ``prepare-comment`` sub-verb is the real command. A valid
    invocation places ``--project-dir X`` BEFORE ``pr prepare-comment`` — the
    parser must skip the routing flag and resolve the ``pr prepare-comment``
    chain, never mis-read it as a missing/unknown subcommand.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser()
            parser.add_argument('--project-dir')
            subparsers = parser.add_subparsers(dest='cmd')

            pr = subparsers.add_parser('pr')
            pr_subs = pr.add_subparsers(dest='sub')

            prepare = pr_subs.add_parser('prepare-comment')
            prepare.add_argument('--plan-id', required=True)
            prepare.add_argument('--pr-number', required=True)

            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


class TestLeadingRoutingFlagBeforeSubcommand:
    """A top-level routing flag placed BEFORE the subcommand is skipped, and the
    real subcommand/sub-verb chain is THEN resolved and validated.

    Reproduces the false-positive caught by the scoped finalize gate:
    ``ci --project-dir {WORKTREE} pr prepare-comment …`` was mis-parsed as a
    missing/unknown subcommand because the positional extractor stopped at the
    leading ``--project-dir`` flag and extracted zero positionals.
    """

    def _index(self, tmp_path: Path) -> dict:
        script = tmp_path / 'syn_routing.py'
        script.write_text(_routing_flag_nested_source(), encoding='utf-8')
        executor = _make_executor(tmp_path, {_SYN_NOTATION: script})
        tree = derive_script_tree(_SYN_NOTATION, executor)
        assert tree is not None
        return {_SYN_NOTATION: tree}

    def test_routing_flag_before_subcommand_validates_clean(
        self, tmp_path: Path
    ) -> None:
        index = self._index(tmp_path)
        # ``--project-dir {WORKTREE}`` is a leading routing flag; the real
        # subcommand chain is ``pr prepare-comment``. Mirrors triage.md.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} '
            f'--project-dir {{WORKTREE}} pr prepare-comment '
            f'--plan-id {{plan_id}} --pr-number {{pr_number}}\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        invalid = [
            f for f in findings if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        ]
        assert invalid == [], (
            f'leading --project-dir routing flag produced false positives: {invalid}'
        )

    def test_routing_flag_with_continuation_validates_clean(
        self, tmp_path: Path
    ) -> None:
        index = self._index(tmp_path)
        # The same shape spread across a backslash continuation, as authored.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} \\\n'
            f'  --project-dir {{WORKTREE}} pr prepare-comment \\\n'
            f'  --plan-id {{plan_id}} --pr-number {{pr_number}}\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        invalid = [
            f for f in findings if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        ]
        assert invalid == [], (
            f'continuation routing flag produced false positives: {invalid}'
        )

    def test_concrete_routing_flag_value_validates_clean(
        self, tmp_path: Path
    ) -> None:
        index = self._index(tmp_path)
        # Non-templated concrete value for the routing flag — the value token
        # must be consumed wholesale so ``pr`` is the first positional.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} '
            f'--project-dir /abs/path pr prepare-comment '
            f'--plan-id p --pr-number 7\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        invalid = [
            f for f in findings if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        ]
        assert invalid == [], (
            f'concrete routing-flag value produced false positives: {invalid}'
        )

    def test_wrong_sub_verb_after_routing_flag_still_flagged(
        self, tmp_path: Path
    ) -> None:
        index = self._index(tmp_path)
        # The fix must NOT blind the validator: a genuinely-wrong sub-verb after
        # the leading routing flag must still resolve the real ``pr`` subcommand
        # and report the bad sub-verb.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} '
            f'--project-dir /abs/path pr bogus-verb --plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', index)
        invalid = [
            f for f in findings if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        ]
        assert len(invalid) == 1, (
            f'wrong sub-verb after routing flag should still be flagged: {invalid}'
        )
        assert invalid[0]['details']['reason'] == 'sub_verb_unknown'
        assert invalid[0]['details']['sub_verb'] == 'bogus-verb'


# NOTE: The zero-false-positive smokes against the REAL plan-marshall bundle
# (``TestRealMarketplaceZeroFalsePositives``) probe the live
# ``.plan/execute-script.py`` executor and live in the integration suite
# (``integration/test_analyze_manage_invocation_smoke.py``, excluded from the
# default ``module-tests`` run via the root ``test/conftest.py`` collect_ignore
# list). This unit suite derives surfaces only from synthetic argparse scripts
# behind the in-process shim above.
