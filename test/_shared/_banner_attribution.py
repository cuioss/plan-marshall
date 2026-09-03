# SPDX-License-Identifier: FSL-1.1-ALv2
"""Two-ref banner-attribution check: a construct filed under the wrong heading.

A module organised into banner-delimited sections makes a promise to its reader:
everything under a heading belongs to it. A split or a move breaks that promise
quietly — the construct lands under whichever banner happened to precede the
insertion point, the file still parses, every test still passes, and the next
reader looking under the right heading does not find it.

This instrument reports a top-level construct sitting under a banner that
introduces a **different** section. The discriminator is deliberately narrow, so
"unrelated to its heading" is not enough on its own:

1. the enclosing banner names at least one subject token, AND
2. the construct's own name shares NO token with that banner, AND
3. the construct shares a **distinctive** token with exactly one other banner in
   the same module — distinctive meaning the token appears in that banner and no
   other.

Condition 3 is what makes the finding a *misattribution* rather than a vague
mismatch: the construct has a heading it evidently belongs under, and it is not
the one it sits beneath. Without it every helper whose name happens not to echo
its section would be reported.

**The distinctiveness requirement is the load-bearing half of condition 3**, and
dropping it makes the instrument unusable rather than merely noisier. Section
headings share a large structural vocabulary — "public entry point", "file
scanner", "data classes", "helpers" — so a construct matching a heading on a word
that several headings also carry has been attributed by nothing. Measured over
one real analyzer tree, matching on any shared token reported 72 constructs;
requiring the shared token to be unique to one heading brings that to 32.

⛔ **32 is a standing BASELINE, not 32 defects, and the verdict is the DELTA.**
The residue is real: a module whose sections are organised by *layer* rather
than by *subject* — constants in one section, the checkers that consume them in
another — legitimately has a checker named after a section it does not sit in.
Name-vs-heading similarity cannot separate that from a genuine misfiling, so
this instrument does not claim it can. What a campaign actually asks is *"did my
split introduce a misattribution?"*, and that question is answered by comparing
the two refs: `introduced` is the set present at the after-ref and absent at the
before-ref, and it is what `main()` exits non-zero on. A pre-existing finding is
reported for the reader and gates nothing.

⛔ **The instrument computes BOTH sides itself** from two refs; it accepts no
pre-computed figure and no baseline for one end. It also **prints its own
definition** — what it recognises as a banner, how it tokenises a name, and the
paths it covered.

The two-ref git access is imported from `_fidelity_diff`, the sibling campaign
instrument that owns it, so all three read a ref the same way.
"""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path

from _fidelity_diff import list_python_files_at_ref, read_file_at_ref

#: The definition this instrument applies, printed verbatim in every report.
DEFINITION = (
    'a BANNER is a comment line carrying section-heading punctuation (a `---`/`===` '
    'rule, or a comment framed by such a rule); a construct is MISATTRIBUTED when its '
    'enclosing banner names subject tokens it shares none of, while it shares a '
    'DISTINCTIVE token (one carried by that heading and no other in the module) with '
    'exactly one other banner'
)

#: A comment that is only rule punctuation — the frame around a heading, not the
#: heading itself. Recognised so the heading text is read from the framed line.
_RULE_ONLY = re.compile(r'^#\s*[-=~_*]{4,}\s*$')

#: A comment carrying heading text plus rule punctuation on the same line, e.g.
#: ``# --- Rule 4 ---------------``.
_INLINE_HEADING = re.compile(r'^#\s*[-=~_*]{2,}\s*(?P<text>.*?)\s*[-=~_*]*\s*$')

#: Tokens too generic to attribute anything by. A banner whose only tokens are
#: these names no subject, and a construct matching only on one of them would
#: match nearly every heading.
_STOPWORDS = frozenset({
    'and', 'the', 'for', 'not', 'with', 'from', 'into', 'this', 'that', 'rule', 'rules',
    'helper', 'helpers', 'shared', 'common', 'util', 'utils', 'test', 'tests', 'main',
    # Structural section vocabulary. Nearly every module carries several of
    # these across several headings, so they attribute nothing on their own —
    # and leaving them in is what turns the check into a false-positive machine.
    'entry', 'point', 'points', 'public', 'private', 'internal', 'scanner', 'scan',
    'parsing', 'parser', 'derivation', 'detection', 'data', 'class', 'classes',
    'form', 'file', 'files', 'source', 'population', 'finding', 'findings',
    'construction', 'pattern', 'patterns', 'check', 'checks', 'side', 'state',
    'states', 'line', 'lines', 'per', 'model', 'output', 'input', 'result',
    'results', 'config', 'configuration', 'module', 'modules',
})


@dataclass(frozen=True)
class Banner:
    """One section heading and the line it sits on."""

    text: str
    lineno: int
    tokens: frozenset[str]


@dataclass(frozen=True)
class Misattribution:
    """A construct filed under a banner that introduces a different section."""

    path: str
    construct: str
    lineno: int
    under_banner: str
    belongs_under: str


def tokenise(text: str) -> frozenset[str]:
    """Split ``text`` into lowercase subject tokens.

    Splits on non-alphanumerics and on camelCase boundaries, lowercases, then
    drops stopwords and tokens shorter than three characters — a two-letter
    fragment matches too much to attribute anything by.
    """
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', text)
    parts = re.split(r'[^A-Za-z0-9]+', spaced)
    return frozenset(part.lower() for part in parts if len(part) >= 3 and part.lower() not in _STOPWORDS)


def collect_banners(source: str) -> list[Banner]:
    """Return every section banner in ``source``, in line order.

    Both shapes are recognised: a heading framed by rule-only comment lines, and
    a heading carrying its rule punctuation inline.

    ⛔ A framed block is consumed WHOLE — its opening rule, its heading, every
    continuation line, and its closing rule. Without that the closing rule reads
    as the opening of a new banner and adopts whatever comment follows it, so an
    ordinary prose sentence inside the next comment block becomes a "heading"
    and attributes constructs by the words it happens to contain. Only the FIRST
    line of a framed block is the heading; the rest is its explanation.
    """
    lines = source.splitlines()
    banners: list[Banner] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped.startswith('#'):
            index += 1
            continue
        if _RULE_ONLY.match(stripped):
            index += 1
            heading: str | None = None
            heading_lineno = index
            while index < len(lines):
                current = lines[index].strip()
                if not current.startswith('#'):
                    break
                if _RULE_ONLY.match(current):
                    index += 1
                    break
                if heading is None:
                    text = current.lstrip('#').strip()
                    if text:
                        heading = text
                        heading_lineno = index + 1
                index += 1
            if heading:
                banners.append(Banner(text=heading, lineno=heading_lineno, tokens=tokenise(heading)))
            continue
        inline = _INLINE_HEADING.match(stripped)
        if inline:
            text = inline.group('text').strip()
            if text:
                banners.append(Banner(text=text, lineno=index + 1, tokens=tokenise(text)))
        index += 1
    return banners


def _enclosing_banner(banners: list[Banner], lineno: int) -> Banner | None:
    """Return the nearest banner at or above ``lineno``."""
    candidate: Banner | None = None
    for banner in banners:
        if banner.lineno <= lineno:
            candidate = banner
        else:
            break
    return candidate


def distinctive_tokens(banners: list[Banner]) -> dict[str, Banner]:
    """Return the tokens carried by exactly ONE banner, mapped to that banner.

    A token several headings share cannot say which section a construct belongs
    to, so only a token unique to one heading is allowed to attribute anything.
    """
    owners: dict[str, list[Banner]] = {}
    for banner in banners:
        for token in banner.tokens:
            owners.setdefault(token, []).append(banner)
    return {token: found[0] for token, found in owners.items() if len(found) == 1}


def scan_module(source: str, path: str) -> list[Misattribution]:
    """Return every misattributed top-level construct in ``source``."""
    banners = collect_banners(source)
    if len(banners) < 2:
        # With fewer than two sections there is no other heading a construct
        # could belong under, so condition 3 can never hold.
        return []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return []

    distinctive = distinctive_tokens(banners)
    findings: list[Misattribution] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        enclosing = _enclosing_banner(banners, node.lineno)
        if enclosing is None or not enclosing.tokens:
            continue
        own = tokenise(node.name)
        if not own or own & enclosing.tokens:
            continue
        owners = {distinctive[token] for token in own if token in distinctive}
        owners.discard(enclosing)
        # Exactly one other heading must claim it. Two claimants attribute no
        # better than none, so an ambiguous construct is left alone.
        if len(owners) == 1:
            findings.append(
                Misattribution(
                    path=path,
                    construct=node.name,
                    lineno=node.lineno,
                    under_banner=enclosing.text,
                    belongs_under=owners.pop().text,
                )
            )
    return findings


def scan_at_ref(ref: str, prefixes: list[str], repo: Path) -> tuple[list[Misattribution], list[str]]:
    """Return ``(misattributions, paths covered)`` for ``prefixes`` at ``ref``."""
    findings: list[Misattribution] = []
    paths: list[str] = []
    for path in list_python_files_at_ref(ref, prefixes, repo):
        source = read_file_at_ref(ref, path, repo)
        if source is None:
            continue
        paths.append(path)
        findings.extend(scan_module(source, path))
    return findings, paths


def _identity(finding: Misattribution) -> tuple[str, str, str]:
    """Return the comparison key: path, construct and the heading it sits under.

    The line number is deliberately excluded — a construct that merely moved
    down the file with its section is not a newly introduced misattribution.
    """
    return (finding.path, finding.construct, finding.under_banner)


def compare_refs(before_ref: str, after_ref: str, prefixes: list[str], repo: Path) -> dict:
    """Scan BOTH refs and return the full report structure.

    ``introduced`` is the after-ref findings absent from the before-ref — the
    only set that says something about the change rather than about the tree.
    """
    before, before_paths = scan_at_ref(before_ref, prefixes, repo)
    after, after_paths = scan_at_ref(after_ref, prefixes, repo)
    baseline = {_identity(finding) for finding in before}
    introduced = [finding for finding in after if _identity(finding) not in baseline]
    return {
        'definition': DEFINITION,
        'prefixes': list(prefixes),
        'before': {'ref': before_ref, 'paths': before_paths, 'findings': before},
        'after': {'ref': after_ref, 'paths': after_paths, 'findings': after},
        'introduced': introduced,
    }


def _format_side(side: dict) -> list[str]:
    out = [f"  ref {side['ref']}: {len(side['findings'])} misattributed across {len(side['paths'])} modules"]
    for finding in side['findings']:
        out.append(
            f'    {finding.path}:{finding.lineno} {finding.construct} '
            f'sits under "{finding.under_banner}" but belongs under "{finding.belongs_under}"'
        )
    return out


def format_report(report: dict) -> str:
    """Render the report, leading with the definition the instrument applied."""
    out = ['banner-attribution: two-ref check of section membership']
    out.append(f"  paths covered: {', '.join(report['prefixes'])}")
    out.append(f"  definition applied: {report['definition']}")
    out.append('')
    out.extend(_format_side(report['before']))
    out.append('')
    out.extend(_format_side(report['after']))
    out.append('')
    introduced = report['introduced']
    out.append(f'INTRODUCED by the change ({len(introduced)}) — the verdict; a pre-existing finding gates nothing:')
    for finding in introduced:
        out.append(
            f'    {finding.path}:{finding.lineno} {finding.construct} '
            f'sits under "{finding.under_banner}" but belongs under "{finding.belongs_under}"'
        )
    return '\n'.join(out)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Exits non-zero when the change INTRODUCED a misattribution."""
    parser = argparse.ArgumentParser(
        prog='_banner_attribution',
        description='Report constructs filed under the wrong section banner at two refs.',
        allow_abbrev=False,
    )
    parser.add_argument('--before-ref', required=True, help='the ref the work started from')
    parser.add_argument('--after-ref', required=True, help='the ref to compare against')
    parser.add_argument('--paths', required=True, help='comma-separated path prefixes to cover')
    parser.add_argument('--repo', default='.', help='repository root (default: cwd)')
    args = parser.parse_args(argv)

    prefixes = [p.strip() for p in args.paths.split(',') if p.strip()]
    report = compare_refs(args.before_ref, args.after_ref, prefixes, Path(args.repo))
    print(format_report(report))
    return 1 if report['introduced'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
