# SPDX-License-Identifier: FSL-1.1-ALv2
"""Two-ref duplication survey: which definitions have a home, and which do not.

A name appearing in several modules is not automatically a duplicate. There are
two populations behind that one observation, and conflating them is how a
de-duplication pass merges two behaviours into one:

- **A duplicate with a home** — one name whose body is IDENTICAL everywhere it
  appears. Hoisting it into a shared module removes real repetition.
- **A name carrying more than one body** — the same identifier implementing
  different behaviour in different modules. These are same-named local helpers,
  not duplicates, and hoisting one would silently rebind the others.

The instrument reports the two separately and never merges them, because the
second population is usually the larger one and reads as duplication only if
bodies are left uncompared.

Bodies are compared by a **normalised** form (docstring dropped, comments
dropped, blank lines dropped, each line whitespace-collapsed), so a reflowed
comment does not read as a behavioural difference and a genuinely different body
is never absorbed by formatting noise.

⛔ **The instrument computes BOTH sides itself** from two refs; it accepts no
pre-computed figure and no baseline for one end. It also **prints its own
definition** — what it treats as a definition, how it normalises a body, and the
directories it covered.

The two-ref git access is imported from `_fidelity_diff`, the sibling campaign
instrument that owns it, so all three read a ref the same way rather than
carrying three copies that could drift.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from _fidelity_diff import list_python_files_at_ref, read_file_at_ref

#: The three node kinds this instrument treats as a definition. Bound once and
#: used both as the annotation and as the ``isinstance`` filter, so the type the
#: normaliser accepts and the nodes the collector hands it cannot drift apart.
Definition = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef

#: The definition this instrument applies, printed verbatim in every report.
DEFINITION = (
    'a MODULE-LEVEL `def`/`async def`/`class` is a definition; two occurrences are '
    'the same body when their normalised source matches (docstring, comments and '
    'blank lines dropped, each remaining line whitespace-collapsed)'
)


@dataclass(frozen=True)
class Occurrence:
    """One module-level definition found at one path."""

    name: str
    path: str
    body_hash: str
    lineno: int


def _normalise_body(node: Definition, source_lines: list[str]) -> str:
    """Return the definition's body with formatting and prose removed.

    Docstrings and comments are dropped because a reworded explanation is not a
    behavioural difference; whitespace is collapsed because re-indentation is
    not either. What survives is the code the definition actually runs.
    """
    start = node.lineno - 1
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    body = source_lines[start:end]
    docstring_spans: set[int] = set()
    first = node.body[0] if node.body else None
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
        and first.end_lineno is not None
    ):
        docstring_spans = set(range(first.lineno - 1, first.end_lineno))
    kept: list[str] = []
    for offset, line in enumerate(body):
        if start + offset in docstring_spans:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        kept.append(' '.join(stripped.split()))
    return '\n'.join(kept)


def collect_definitions(source: str, path: str) -> list[Occurrence]:
    """Return every module-level definition in ``source``.

    Only module-level definitions are collected: a method inside a class is
    scoped by that class and is not a candidate for hoisting on its own.
    """
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return []
    lines = source.splitlines()
    found: list[Occurrence] = []
    for node in tree.body:
        if not isinstance(node, Definition):
            continue
        digest = hashlib.sha256(_normalise_body(node, lines).encode('utf-8')).hexdigest()
        found.append(Occurrence(name=node.name, path=path, body_hash=digest, lineno=node.lineno))
    return found


def collect_at_ref(ref: str, prefixes: list[str], repo: Path) -> tuple[list[Occurrence], list[str]]:
    """Return ``(occurrences, paths covered)`` for ``prefixes`` at ``ref``."""
    occurrences: list[Occurrence] = []
    paths: list[str] = []
    for path in list_python_files_at_ref(ref, prefixes, repo):
        source = read_file_at_ref(ref, path, repo)
        if source is None:
            continue
        paths.append(path)
        occurrences.extend(collect_definitions(source, path))
    return occurrences, paths


def partition(occurrences: list[Occurrence]) -> dict[str, list[dict]]:
    """Split names appearing more than once into the two populations.

    ``duplicates_with_a_home`` carries one body everywhere; ``multiple_bodies``
    carries more than one. A name occurring once is neither and is omitted.
    """
    by_name: dict[str, list[Occurrence]] = defaultdict(list)
    for occurrence in occurrences:
        by_name[occurrence.name].append(occurrence)

    homed: list[dict] = []
    multi: list[dict] = []
    for name, group in sorted(by_name.items()):
        if len(group) < 2:
            continue
        bodies = {occurrence.body_hash for occurrence in group}
        entry = {
            'name': name,
            'occurrences': len(group),
            'distinct_bodies': len(bodies),
            'paths': sorted(occurrence.path for occurrence in group),
        }
        (homed if len(bodies) == 1 else multi).append(entry)
    return {'duplicates_with_a_home': homed, 'multiple_bodies': multi}


def survey_refs(before_ref: str, after_ref: str, prefixes: list[str], repo: Path) -> dict:
    """Survey duplication at BOTH refs and return the full report structure."""
    before, before_paths = collect_at_ref(before_ref, prefixes, repo)
    after, after_paths = collect_at_ref(after_ref, prefixes, repo)
    return {
        'definition': DEFINITION,
        'prefixes': list(prefixes),
        'before': {
            'ref': before_ref,
            'paths': before_paths,
            'definitions': len(before),
            **partition(before),
        },
        'after': {
            'ref': after_ref,
            'paths': after_paths,
            'definitions': len(after),
            **partition(after),
        },
    }


def _format_side(side: dict) -> list[str]:
    out = [
        f"  ref {side['ref']}: {side['definitions']} module-level definitions "
        f"across {len(side['paths'])} modules"
    ]
    homed = side['duplicates_with_a_home']
    multi = side['multiple_bodies']
    out.append(f'    duplicates with a home ({len(homed)}) — one body everywhere, safe to hoist:')
    for entry in homed:
        out.append(f"      {entry['name']} x{entry['occurrences']}: {', '.join(entry['paths'])}")
    out.append(f'    names carrying more than one body ({len(multi)}) — NOT duplicates:')
    for entry in multi:
        out.append(
            f"      {entry['name']} x{entry['occurrences']} "
            f"in {entry['distinct_bodies']} bodies: {', '.join(entry['paths'])}"
        )
    return out


def format_report(report: dict) -> str:
    """Render the survey, leading with the definition the instrument applied."""
    out = ['definition-duplication: two-ref survey of module-level definitions']
    out.append(f"  paths covered: {', '.join(report['prefixes'])}")
    out.append(f"  definition applied: {report['definition']}")
    out.append('')
    out.extend(_format_side(report['before']))
    out.append('')
    out.extend(_format_side(report['after']))
    return '\n'.join(out)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Always exits 0 — this instrument surveys, it does not gate."""
    parser = argparse.ArgumentParser(
        prog='_definition_duplication',
        description='Survey module-level definition duplication at two refs.',
        allow_abbrev=False,
    )
    parser.add_argument('--before-ref', required=True, help='the ref the work started from')
    parser.add_argument('--after-ref', required=True, help='the ref to compare against')
    parser.add_argument('--paths', required=True, help='comma-separated directory prefixes to survey')
    parser.add_argument('--repo', default='.', help='repository root (default: cwd)')
    args = parser.parse_args(argv)

    prefixes = [p.strip() for p in args.paths.split(',') if p.strip()]
    print(format_report(survey_refs(args.before_ref, args.after_ref, prefixes, Path(args.repo))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
