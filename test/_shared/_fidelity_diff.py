# SPDX-License-Identifier: FSL-1.1-ALv2
"""Two-ref fidelity diff: what a refactor LOST, as a set difference.

A split or a move is faithful when nothing disappears. The tempting way to check
that is to compare counts at each end — same number of tests before and after,
so nothing was lost. That check is wrong in the direction that matters: a
refactor that drops one test and adds another reports a zero delta while having
silently lost a behaviour.

This instrument therefore compares **multisets**, not counts. Each facet is
collected as a `Counter` at both refs and differenced in both directions, so the
report names the comments, code lines and `Class::test` identities that vanished
and the ones that appeared. A loss is an element the difference names, never a
number that failed to match.

⛔ **The instrument computes BOTH sides itself.** It takes two refs and reads
each side out of git; it accepts no pre-computed figure and no baseline for one
end. That constraint is the reason it exists: a check handed one side as a
number is a check that trusts the very measurement it is supposed to verify.

It also **prints its own definition** — the facets it counted, how it normalised
each, and the paths it covered — because two instruments silently applying two
different definitions of "the same thing" is how a campaign produces two
irreconcilable figures for one question.

The module exposes importable functions plus a `main()` CLI. The two-ref git
access below is public and is shared by the sibling campaign instruments
(`_definition_duplication.py`, `_banner_attribution.py`) so all three read a ref
the same way.
"""

from __future__ import annotations

import argparse
import ast
import io
import subprocess
import tokenize
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

#: The facets this instrument compares, with the normalisation applied to each.
#: Printed verbatim in every report — see the module docstring on why a stated
#: definition is part of the output rather than a comment in the source.
FACET_DEFINITIONS: dict[str, str] = {
    'comments': 'every `#` comment token, leading marker and surrounding whitespace stripped',
    'code_lines': 'every non-blank line that is not comment-only, whitespace-stripped',
    'test_identities': "each test as `Class::name` (or `::name` at module level), from the AST",
}


# ---------------------------------------------------------------------------
# Two-ref git access (shared by the three campaign instruments)
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Run one git command in ``repo`` and return the completed process.

    An argv list is passed rather than a shell string, so a path carrying a
    shell metacharacter cannot be re-interpreted as a command.
    """
    return subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def list_python_files_at_ref(ref: str, prefixes: list[str], repo: Path) -> list[str]:
    """Return every ``*.py`` path under ``prefixes`` as it exists at ``ref``.

    The listing comes from the ref's own tree, never from the working copy, so a
    file that exists only at one end is present on exactly that side.
    """
    result = _git(repo, 'ls-tree', '-r', '--name-only', ref, '--', *prefixes)
    if result.returncode != 0:
        raise RuntimeError(f'git ls-tree failed for ref {ref!r}: {result.stderr.strip()}')
    return sorted(line for line in result.stdout.splitlines() if line.endswith('.py'))


def read_file_at_ref(ref: str, path: str, repo: Path) -> str | None:
    """Return the content of ``path`` at ``ref``, or None when it is absent there."""
    result = _git(repo, 'show', f'{ref}:{path}')
    if result.returncode != 0:
        return None
    return result.stdout


# ---------------------------------------------------------------------------
# Facet collection
# ---------------------------------------------------------------------------


@dataclass
class Facets:
    """The three multisets this instrument compares, plus its coverage."""

    comments: Counter = field(default_factory=Counter)
    code_lines: Counter = field(default_factory=Counter)
    test_identities: Counter = field(default_factory=Counter)
    paths: list[str] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)

    def facet(self, name: str) -> Counter:
        return getattr(self, name)


def collect_comments(source: str) -> Counter:
    """Return the multiset of comment texts, `#` marker and whitespace stripped."""
    found: Counter = Counter()
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                found[token.string.lstrip('#').strip()] += 1
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return found
    return found


def collect_code_lines(source: str) -> Counter:
    """Return the multiset of non-blank, non-comment-only lines, whitespace-stripped."""
    found: Counter = Counter()
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            found[stripped] += 1
    return found


def collect_test_identities(source: str, path: str) -> tuple[Counter, bool]:
    """Return ``(multiset of Class::test identities, parsed_ok)``.

    A module that does not parse yields an empty multiset and ``False`` — the
    caller records it as unparsed rather than as a module carrying no tests,
    because those two are different claims.
    """
    found: Counter = Counter()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return found, False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith('test'):
            found[f'{path}::{node.name}'] += 1
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) and child.name.startswith('test'):
                    found[f'{path}::{node.name}::{child.name}'] += 1
    return found, True


def collect_facets_at_ref(ref: str, prefixes: list[str], repo: Path) -> Facets:
    """Collect every facet across ``prefixes`` as they exist at ``ref``."""
    facets = Facets()
    for path in list_python_files_at_ref(ref, prefixes, repo):
        source = read_file_at_ref(ref, path, repo)
        if source is None:
            continue
        facets.paths.append(path)
        facets.comments.update(collect_comments(source))
        facets.code_lines.update(collect_code_lines(source))
        identities, parsed_ok = collect_test_identities(source, path)
        facets.test_identities.update(identities)
        if not parsed_ok:
            facets.unparsed.append(path)
    return facets


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def diff_facets(before: Facets, after: Facets) -> dict[str, dict]:
    """Return the per-facet multiset difference in BOTH directions.

    ``lost`` is ``before - after`` and ``gained`` is ``after - before``. Both are
    reported because a refactor that drops one element and adds another has a
    zero net delta and is exactly the loss this instrument exists to name.
    """
    report: dict[str, dict] = {}
    for name in FACET_DEFINITIONS:
        left, right = before.facet(name), after.facet(name)
        lost = left - right
        gained = right - left
        report[name] = {
            'definition': FACET_DEFINITIONS[name],
            'before_total': sum(left.values()),
            'after_total': sum(right.values()),
            'lost': sorted(lost.elements()),
            'gained': sorted(gained.elements()),
        }
    return report


def compare_refs(before_ref: str, after_ref: str, prefixes: list[str], repo: Path) -> dict:
    """Compare two refs over ``prefixes`` and return the full report structure."""
    before = collect_facets_at_ref(before_ref, prefixes, repo)
    after = collect_facets_at_ref(after_ref, prefixes, repo)
    return {
        'before_ref': before_ref,
        'after_ref': after_ref,
        'prefixes': list(prefixes),
        'before_paths': before.paths,
        'after_paths': after.paths,
        'unparsed': sorted(set(before.unparsed) | set(after.unparsed)),
        'facets': diff_facets(before, after),
    }


def format_report(report: dict) -> str:
    """Render the report, leading with the definition the instrument applied."""
    out: list[str] = []
    out.append('fidelity-diff: multiset comparison of two refs')
    out.append(f"  before_ref: {report['before_ref']}")
    out.append(f"  after_ref:  {report['after_ref']}")
    out.append(f"  paths covered: {', '.join(report['prefixes'])}")
    out.append(f"  modules read: {len(report['before_paths'])} before, {len(report['after_paths'])} after")
    if report['unparsed']:
        out.append(f"  unparsed (identities not collected): {', '.join(report['unparsed'])}")
    out.append('  definition applied per facet:')
    for name, definition in FACET_DEFINITIONS.items():
        out.append(f'    {name}: {definition}')
    out.append('')
    for name, facet in report['facets'].items():
        out.append(f"{name}: {facet['before_total']} before, {facet['after_total']} after")
        out.append(f"  lost ({len(facet['lost'])}):")
        for item in facet['lost']:
            out.append(f'    - {item}')
        out.append(f"  gained ({len(facet['gained'])}):")
        for item in facet['gained']:
            out.append(f'    + {item}')
    return '\n'.join(out)


def has_loss(report: dict) -> bool:
    """Return True when any facet lost an element."""
    return any(facet['lost'] for facet in report['facets'].values())


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Exits non-zero when any facet lost an element."""
    parser = argparse.ArgumentParser(
        prog='_fidelity_diff',
        description='Compare two refs by multiset and report what was lost.',
        allow_abbrev=False,
    )
    parser.add_argument('--before-ref', required=True, help='the ref the refactor started from')
    parser.add_argument('--after-ref', required=True, help='the ref the refactor produced')
    parser.add_argument('--paths', required=True, help='comma-separated path prefixes to cover')
    parser.add_argument('--repo', default='.', help='repository root (default: cwd)')
    args = parser.parse_args(argv)

    prefixes = [p.strip() for p in args.paths.split(',') if p.strip()]
    report = compare_refs(args.before_ref, args.after_ref, prefixes, Path(args.repo))
    print(format_report(report))
    return 1 if has_loss(report) else 0


if __name__ == '__main__':
    raise SystemExit(main())
