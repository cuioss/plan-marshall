#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the shared ``argparse_surface`` accept-set derivation.

The module derives one script's argparse surface by running that script's own
``--help`` and recursing into each discovered verb. Two consumers read it —
plugin-doctor's edit-time rules and the executor generator's pre-spawn
rejection — so a defect here is either a false rejection of a valid call or a
silent hole in both guards at once.

Three layers of coverage, each pinning a different property:

1. **Positive controls** — the shapes the replaced static AST walk could not
   reach: a script declaring ``aliases=`` (alias AND canonical both accepted),
   a script whose parser is assembled in an IMPORTED module (the
   ``tools-integration-ci:ci`` / ``ci_base.py`` shape), a nested verb tree
   resolving past the first level, and a flag declared in a CUSTOM argument
   group (the asymmetric-error rule's load-bearing case).

2. **Matched negative controls** — one per uncertainty path, each asserting an
   explicit :class:`NotDerivable` rather than an empty-but-confident surface.
   The distinction is the whole point: an empty surface reads as "this script
   accepts nothing" and would reject every call.

3. **Live-tree characterization** — every notation the real executor registers
   resolves to either a confident surface or an explicit not-derivable result,
   with the per-bucket counts published in the assertion message so a collapse
   in coverage is visible as a NUMBER rather than inferred from a green run.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT

import argparse_surface as surf

# ---------------------------------------------------------------------------
# Synthetic executor — mirrors the real ``.plan/execute-script.py`` dispatch
# ---------------------------------------------------------------------------

# The shim reads a notation -> script-path map and dispatches the resolved
# script with the remaining argv, so ``--help`` flows through to the target's
# own argparse instance and produces the real published surface. Dispatch is
# in-process via ``runpy.run_path`` under redirected stdout/stderr: the
# derivation already spawns the shim as a subprocess, so an inner spawn would
# double the interpreter cold-start cost of every probe.
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

# A notation triple shaped like a real one so the derivation's own
# ``bundle:skill:script`` split accepts it.
SYN_NOTATION = 'plan-marshall:manage-syn:manage-syn'

# The synthetic scripts live under ``tmp_path`` rather than the marketplace
# tree, so ``script_path_for_notation`` finds nothing and the derivation takes
# its no-content-hash branch: live probe, executor-keyed memo, NO disk cache.
# That is what keeps each test's fixture from poisoning the next one's, and it
# is why every test here can vary the script behind one shared notation.
NO_CACHE = surf.DerivationConfig(use_disk_cache=False)


def _make_executor(tmp_path: Path, mapping: dict[str, Path]) -> Path:
    """Write a synthetic executor + notation map and return the executor path."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    executor = plan_dir / 'execute-script.py'
    executor.write_text(_EXECUTOR_SHIM, encoding='utf-8')
    (plan_dir / 'notation_map.json').write_text(
        json.dumps({k: str(v) for k, v in mapping.items()}), encoding='utf-8'
    )
    return executor


def _derive(
    tmp_path: Path,
    source: str,
    *,
    filename: str = 'syn.py',
    config: surf.DerivationConfig = NO_CACHE,
    extra_files: dict[str, str] | None = None,
) -> surf.ScriptSurface | surf.NotDerivable:
    """Write ``source`` (plus any ``extra_files``) and derive its surface."""
    for name, body in (extra_files or {}).items():
        (tmp_path / name).write_text(body, encoding='utf-8')
    script = tmp_path / filename
    script.write_text(source, encoding='utf-8')
    executor = _make_executor(tmp_path, {SYN_NOTATION: script})
    surf.clear_memo()
    return surf.derive_surface(SYN_NOTATION, executor, config=config)


# ---------------------------------------------------------------------------
# Synthetic script sources
# ---------------------------------------------------------------------------


def _alias_source() -> str:
    """A script declaring ``aliases=`` — the shape the AST walk was blind to.

    Mirrors the three real scripts that declare aliases (``manage-status get``,
    ``manage-tasks get``, ``manage-lessons read``). ``help=`` is supplied so
    argparse also renders the ``read (get)`` grouping line, exercising the
    optional alias-enrichment anchor alongside the flat choice list.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser(prog='syn')
            subparsers = parser.add_subparsers(dest='cmd')
            read_p = subparsers.add_parser('read', aliases=['get'], help='Read a record')
            read_p.add_argument('--plan-id', required=True)
            subparsers.add_parser('list', help='List records')
            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _imported_parser_module() -> str:
    """A sibling module that OWNS the parser construction."""
    return textwrap.dedent('''
        import argparse

        def build_parser():
            parser = argparse.ArgumentParser(prog='syn')
            subparsers = parser.add_subparsers(dest='cmd')
            for name in ('pr', 'checks', 'issue', 'branch', 'repo'):
                sub = subparsers.add_parser(name)
                sub.add_argument('--plan-id')
            return parser
    ''').lstrip()


def _imported_parser_source() -> str:
    """The ``tools-integration-ci:ci`` shape — parser built in an imported module.

    A static walk of THIS file sees no ``add_parser`` call at all, so the
    replaced AST derivation contributed zero surface for one of the most
    heavily dispatched notations in the tree. ``--help`` renders the fully
    assembled parser regardless of which module built it.
    """
    return textwrap.dedent('''
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))
        from syn_parser_lib import build_parser

        def main():
            build_parser().parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _nested_source() -> str:
    """A three-level verb tree — ``plan {phase} {get,set}``."""
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser(prog='syn')
            subparsers = parser.add_subparsers(dest='cmd')
            plan = subparsers.add_parser('plan')
            phases = plan.add_subparsers(dest='phase')
            for phase in ('phase-3-outline', 'phase-5-execute'):
                node = phases.add_parser(phase)
                ops = node.add_subparsers(dest='op')
                get_p = ops.add_parser('get')
                get_p.add_argument('--field', required=True)
                set_p = ops.add_parser('set')
                set_p.add_argument('--field', required=True)
                set_p.add_argument('--value', required=True)
            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _custom_group_source() -> str:
    """A flag declared in a CUSTOM argument group.

    argparse renders such a flag under the group's own title, NOT under
    ``options:``. A section-scoped flag scan omits it and then rejects a valid
    call — which is exactly why the asymmetric-error rule harvests every
    ``--long-token`` anywhere in the output.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser(prog='syn')
            subparsers = parser.add_subparsers(dest='cmd')
            run = subparsers.add_parser('run')
            group = run.add_argument_group('routing options')
            group.add_argument('--project-dir')
            run.add_argument('--flag')
            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


def _nonzero_exit_source() -> str:
    """``--help`` exits non-zero — an import-time failure, a crashing main."""
    return textwrap.dedent('''
        import sys

        sys.stderr.write('boom\\n')
        sys.exit(3)
    ''').lstrip()


def _silent_source() -> str:
    """Exits cleanly and prints nothing at all."""
    return 'pass\n'


def _slow_source() -> str:
    """Sleeps well past any sane per-invocation timeout."""
    return textwrap.dedent('''
        import time

        time.sleep(30)
    ''').lstrip()


def _no_structure_source() -> str:
    """Prints a ``usage:`` line but NO argparse section header.

    This is the case the confidence rule exists for: enough surface syntax to
    look parseable, none of the structure the parsers actually need. Treating
    it as "an argparse parser declaring nothing" would mint an
    empty-but-confident surface.
    """
    return textwrap.dedent('''
        print('usage: syn [options]')
        print('This is a hand-rolled CLI, not argparse.')
    ''').lstrip()


def _suppressed_choices_source() -> str:
    """``add_subparsers(metavar=...)`` suppresses the choice list.

    With a metavar and no ``help=`` on any child, argparse renders neither the
    ``{a,b}`` group nor the per-verb grouping lines, so the acceptance oracle
    has nothing to read. The node must report an unconfident child listing
    rather than "declares no subcommands".
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser(prog='syn')
            subparsers = parser.add_subparsers(dest='cmd', metavar='COMMAND')
            subparsers.add_parser('alpha')
            subparsers.add_parser('beta')
            parser.parse_args()

        if __name__ == '__main__':
            main()
    ''').lstrip()


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


class TestPositiveControls:
    def test_alias_and_canonical_are_both_accepted(self, tmp_path: Path):
        result = _derive(tmp_path, _alias_source())
        assert surf.is_derivable(result), result
        accepted = result.known_subcommands()
        assert 'read' in accepted
        assert 'get' in accepted, (
            'alias spelling missing from the accept-set — the choice list is '
            'the acceptance oracle and argparse renders aliases flat in it'
        )
        assert 'list' in accepted

    def test_alias_grouping_maps_alias_to_canonical(self, tmp_path: Path):
        """The ``read (get)`` line is recovered — enrichment, never acceptance."""
        result = _derive(tmp_path, _alias_source())
        assert surf.is_derivable(result)
        assert result.root.canonical_spelling('get') == 'read'
        assert result.root.canonical_spelling('read') == 'read'
        assert result.root.alias_group('read') == ['get']

    def test_alias_node_carries_the_canonical_flag_surface(self, tmp_path: Path):
        """Both spellings resolve to a node declaring the canonical's flags."""
        result = _derive(tmp_path, _alias_source())
        assert surf.is_derivable(result)
        for spelling in ('read', 'get'):
            node = result.root.children[spelling]
            assert 'plan-id' in node.flags, spelling

    def test_parser_built_in_an_imported_module_is_confident(self, tmp_path: Path):
        """The ``ci_base.py`` shape — no ``add_parser`` call in the entry file."""
        result = _derive(
            tmp_path,
            _imported_parser_source(),
            extra_files={'syn_parser_lib.py': _imported_parser_module()},
        )
        assert surf.is_derivable(result), result
        assert result.root.children_confident
        assert result.known_subcommands() == {'pr', 'checks', 'issue', 'branch', 'repo'}

    def test_nested_verb_tree_resolves_past_the_first_level(self, tmp_path: Path):
        result = _derive(tmp_path, _nested_source())
        assert surf.is_derivable(result)
        node, unknown, chain = result.resolve_path(['plan', 'phase-5-execute', 'set'])
        assert unknown is None
        assert chain == ['plan', 'phase-5-execute', 'set']
        assert node is not None
        assert {'field', 'value'} <= node.flags
        assert node.required_flags == {'field', 'value'}

    def test_unregistered_sub_verb_reports_the_failing_token(self, tmp_path: Path):
        result = _derive(tmp_path, _nested_source())
        assert surf.is_derivable(result)
        node, unknown, chain = result.resolve_path(['plan', 'phase-9-nope'])
        assert node is None
        assert unknown == 'phase-9-nope'
        assert chain == ['plan']

    def test_custom_argument_group_flag_is_in_the_flag_set(self, tmp_path: Path):
        """Asymmetric-error control: a group-declared flag must not be lost."""
        result = _derive(tmp_path, _custom_group_source())
        assert surf.is_derivable(result)
        run = result.root.children['run']
        assert 'project-dir' in run.flags, (
            'flag declared in a custom argument group was dropped — a '
            'section-scoped scan would reject a valid call'
        )
        assert 'flag' in run.flags


# ---------------------------------------------------------------------------
# Matched negative controls — each asserts NOT-DERIVABLE, never empty
# ---------------------------------------------------------------------------


class TestNegativeControls:
    """Every uncertainty path yields an explicit marker, not an empty surface.

    Each case pairs with a positive control above. The shared assertion is the
    load-bearing one: ``is_derivable`` is False. A test that only checked
    ``known_subcommands() == set()`` would pass just as happily on the
    empty-but-confident surface these controls exist to forbid.
    """

    def test_nonzero_help_exit_is_not_derivable(self, tmp_path: Path):
        result = _derive(tmp_path, _nonzero_exit_source())
        assert isinstance(result, surf.NotDerivable)
        assert result.reason == surf.REASON_HELP_FAILED

    def test_empty_help_output_is_not_derivable(self, tmp_path: Path):
        result = _derive(tmp_path, _silent_source())
        assert isinstance(result, surf.NotDerivable)
        assert result.reason == surf.REASON_HELP_FAILED

    def test_timeout_is_not_derivable(self, tmp_path: Path):
        config = surf.DerivationConfig(use_disk_cache=False, timeout_seconds=1.0)
        result = _derive(tmp_path, _slow_source(), config=config)
        assert isinstance(result, surf.NotDerivable)
        assert result.reason == surf.REASON_HELP_FAILED

    def test_output_without_argparse_structure_is_not_derivable(self, tmp_path: Path):
        result = _derive(tmp_path, _no_structure_source())
        assert isinstance(result, surf.NotDerivable)
        assert result.reason == surf.REASON_NO_STRUCTURE, (
            'help with a usage: line but no section header must be rejected as '
            'unstructured, not read as a parser that declares nothing'
        )

    def test_exhausted_node_budget_is_not_derivable(self, tmp_path: Path):
        """A budget too small for even the root probe abandons the whole script."""
        config = surf.DerivationConfig(use_disk_cache=False, max_nodes=0)
        result = _derive(tmp_path, _alias_source(), config=config)
        assert isinstance(result, surf.NotDerivable)
        assert result.reason == surf.REASON_BUDGET_EXHAUSTED

    def test_suppressed_choice_list_yields_unconfident_children(self, tmp_path: Path):
        """``metavar=`` with no grouping lines: the child listing is UNKNOWN.

        Granular uncertainty — the root's own flag surface was read fine, so
        only the child listing is marked unconfident. ``resolve_path`` then
        stops at the node instead of reporting an unknown sub-verb, which is
        what keeps a valid ``syn alpha`` call from being rejected.
        """
        result = _derive(tmp_path, _suppressed_choices_source())
        assert surf.is_derivable(result)
        assert result.known_subcommands() == set()
        node, unknown, chain = result.resolve_path(['alpha'])
        assert unknown is None, (
            'a node with no readable child listing must not report an unknown '
            'sub-verb — it has no basis to call the token wrong'
        )
        assert node is result.root
        assert chain == []


# ---------------------------------------------------------------------------
# Depth / budget bounds
# ---------------------------------------------------------------------------


class TestBounds:
    def test_depth_cap_marks_the_boundary_node_unconfident(self, tmp_path: Path):
        """A tree deeper than ``max_depth`` stops WITHOUT claiming completeness."""
        config = surf.DerivationConfig(use_disk_cache=False, max_depth=1)
        result = _derive(tmp_path, _nested_source(), config=config)
        assert surf.is_derivable(result)
        plan = result.root.children['plan']
        assert plan.children == {}
        assert not plan.children_confident, (
            'depth-capped node must not read as "declares no children"'
        )
        node, unknown, _chain = result.resolve_path(['plan', 'phase-5-execute'])
        assert unknown is None
        assert node is plan


# ---------------------------------------------------------------------------
# Pure-parser units (no subprocess)
# ---------------------------------------------------------------------------


class TestPureParsers:
    def test_choices_without_the_dispatch_marker_are_not_children(self):
        """A plain ``choices=`` positional must NOT become a subparser listing.

        Detection stays on the usage line's trailing ``...``. Widening this
        decision would give the node children it does not have, and every valid
        call would then look like an unknown sub-verb.
        """
        help_text = textwrap.dedent('''
            usage: syn [-h] {alpha,beta}

            positional arguments:
              {alpha,beta}   the mode

            options:
              -h, --help     show this help message and exit
        ''').lstrip()
        assert surf.parse_choice_list(help_text) == []

    def test_dispatch_marker_admits_names_from_the_positional_section(self):
        """Once dispatch is confirmed, the section widens the NAME set."""
        help_text = textwrap.dedent('''
            usage: syn [-h] {alpha,beta} ...

            positional arguments:
              {alpha,beta,gamma}

            options:
              -h, --help  show this help message and exit
        ''').lstrip()
        assert set(surf.parse_choice_list(help_text)) == {'alpha', 'beta', 'gamma'}

    def test_required_flags_exclude_mutually_exclusive_group_members(self):
        """``(--set K=V | --get F)`` makes NO individual member required."""
        usage = 'usage: syn metadata [-h] --plan-id P (--set KV | --get F | --list)'
        assert surf.parse_required_flags(usage) == {'plan-id'}

    def test_unstructured_output_has_no_argparse_structure(self):
        assert not surf.has_argparse_structure('usage: syn [options]\nhand rolled\n')
        assert surf.has_argparse_structure('usage: syn\n\noptions:\n  -h, --help\n')

    def test_ansi_escapes_are_stripped_before_parsing(self):
        colored = '\x1b[36musage:\x1b[0m syn [-h] \x1b[36m{a,b}\x1b[0m ...\n\noptions:\n'
        assert surf.strip_ansi(colored).startswith('usage:')
        assert surf.parse_choice_list(surf.strip_ansi(colored)) == ['a', 'b']


# ---------------------------------------------------------------------------
# Live-tree characterization
# ---------------------------------------------------------------------------

# The known-hard cases: notations whose surface the replaced static AST walk
# could NOT derive, and whose confidence is therefore the direct evidence that
# the promotion delivered what it claimed. Kept small and derived with their
# own budget so a slow unrelated script can never starve them.
_KNOWN_HARD_NOTATIONS = (
    'plan-marshall:tools-integration-ci:ci',
    'plan-marshall:manage-tasks:manage-tasks',
    'plan-marshall:manage-status:manage-status',
    'plan-marshall:manage-lessons:manage-lessons',
)


def _live_executor() -> Path:
    executor = surf.resolve_executor(PROJECT_ROOT)
    if executor is None:
        pytest.fail(
            f'no .plan/execute-script.py under {PROJECT_ROOT} — the root '
            'conftest bootstraps it, so its absence is a real failure rather '
            'than a reason to skip this characterization'
        )
    return executor


class TestLiveTreeCharacterization:
    """Every registered notation lands in exactly one of two named buckets.

    The population is read from the live executor's own ``SCRIPTS`` registry
    rather than hand-listed, so the test cannot quietly shrink: if the registry
    is empty the test fails instead of vacuously passing over zero notations.
    """

    def test_known_hard_notations_yield_confident_surfaces(self):
        executor = _live_executor()
        index = surf.build_surface_index(list(_KNOWN_HARD_NOTATIONS), executor)
        unconfident = {
            notation: result.reason
            for notation, result in index.items()
            if not surf.is_derivable(result)
        }
        assert not unconfident, (
            'the promotion exists to cover these shapes — a parser assembled '
            f'in an imported module and alias-declaring scripts: {unconfident}'
        )
        ci = index['plan-marshall:tools-integration-ci:ci']
        assert {'pr', 'checks', 'issue', 'branch'} <= ci.known_subcommands()

    def test_alias_declaring_scripts_accept_both_spellings(self):
        """The three documented read-verb aliases resolve as accepted spellings."""
        executor = _live_executor()
        expected = {
            'plan-marshall:manage-tasks:manage-tasks': ('read', 'get'),
            'plan-marshall:manage-status:manage-status': ('read', 'get'),
            'plan-marshall:manage-lessons:manage-lessons': ('get', 'read'),
        }
        index = surf.build_surface_index(list(expected), executor)
        for notation, (canonical, alias) in expected.items():
            result = index[notation]
            assert surf.is_derivable(result), (notation, result)
            accepted = result.known_subcommands()
            assert canonical in accepted, (notation, canonical, sorted(accepted))
            assert alias in accepted, (
                f'{notation}: documented alias {alias!r} is not an accepted '
                f'spelling — this is the false rejection the promotion removes'
            )

    def test_every_registered_notation_is_confident_or_explicitly_not_derivable(self):
        executor = _live_executor()
        notations = sorted(_registered_notations(executor))
        assert notations, (
            f'the executor at {executor} registers no notations — the '
            'population this characterization grades is empty, so a pass here '
            'would certify nothing'
        )

        config = surf.DerivationConfig(total_budget_seconds=240.0)
        index = surf.build_surface_index(notations, executor, config=config)

        confident = [n for n, r in index.items() if surf.is_derivable(r)]
        not_derivable = {
            n: r.reason for n, r in index.items() if not surf.is_derivable(r)
        }
        assert len(index) == len(notations)

        # The invariant: no third bucket. A result is a usable surface or an
        # explicit marker naming why it is not — never an empty surface that
        # reads as "accepts nothing".
        for notation, result in index.items():
            assert surf.is_derivable(result) or isinstance(result, surf.NotDerivable), (
                f'{notation} landed outside both buckets: {result!r}'
            )
            if surf.is_derivable(result) and not result.root.children:
                assert not result.root.children_confident or result.root.flags, (
                    f'{notation} derived an empty-but-confident surface — the '
                    'shape that would reject every call'
                )

        # Published counts. Stated in the message so a coverage collapse is a
        # visible number, and floored so it cannot silently drift to zero.
        summary = (
            f'population={len(notations)} confident={len(confident)} '
            f'not_derivable={len(not_derivable)} reasons={sorted(set(not_derivable.values()))}'
        )
        assert len(confident) >= len(notations) // 2, (
            f'fewer than half the registered notations yielded a confident '
            f'surface — {summary}'
        )


def _registered_notations(executor: Path) -> set[str]:
    """Read the notation keys out of the live executor's ``SCRIPTS`` literal.

    Parsed from the generated file rather than imported: the executor is a
    script, not a module, and importing it would run its bootstrap.
    """
    import re

    text = executor.read_text(encoding='utf-8')
    key_re = re.compile(
        r'^\s*"(?P<notation>[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+)":'
    )
    notations: set[str] = set()
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if not in_block:
            if stripped.startswith('SCRIPTS') and '=' in stripped and '{' in stripped:
                in_block = True
            continue
        if stripped == '}':
            break
        match = key_re.match(line)
        if match:
            notations.add(match.group('notation'))
    return notations
