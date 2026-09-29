# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every documented retrospective fragment capture writes and registers under ``{fragment_dir}``.

A capture site is a line in a marketplace markdown document that registers a
fragment with ``collect-fragments`` (``--fragment-file <path>``, or
``--item <aspect>=<path>`` naming a ``fragment-*.toon`` file), redirects a
script's stdout into a
``fragment-*.toon`` file, or instructs the ``Write`` tool to write one. The
written and the registered path must both begin with ``{fragment_dir}/`` — the
directory of the ``bundle_path`` that ``collect-fragments init`` returns. A
cwd-relative capture lands under whatever directory the caller runs from while
``collect-fragments`` anchors a relative path to the bundle root (the plan
directory in live mode, a synthetic tmp root in archived mode), so the
registered file is not the written one.

The population is derived by scanning every markdown document under the
marketplace bundles, across all bundles; a line that only names a fragment file
without writing or registering it is excluded by the predicate, and an argparse
metavar in a canonical-invocation signature is not a capture path.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from conftest import MARKETPLACE_ROOT

_ANCHOR = '{fragment_dir}/'
_FRAGMENT_BASENAME = re.compile(r'^fragment-[\w{}.-]*\.toon$')
_FRAGMENT_TOKEN = re.compile(r'fragment-[\w{}.-]*\.toon')
_FRAGMENT_FILE_FLAG = re.compile(r'--fragment-file(?:\s+|=)(\S+)')
_ITEM_FLAG = re.compile(r'--item(?:\s+|=)(\S+)')
_REDIRECT = re.compile(r'>\s*(\S+)')
_BACKTICKED = re.compile(r'`([^`]+)`')
_WRITE_TOOL = re.compile(r'`Write`|\bWrite tool\b')
_METAVAR = re.compile(r'^[A-Z][A-Z0-9_]*$')
_TRAILING_PUNCTUATION = '`.,;:)'


class CaptureSite(NamedTuple):
    line: int
    kind: str
    path: str


def _clean(token: str) -> str:
    return token.rstrip(_TRAILING_PUNCTUATION).lstrip('`')


def _is_fragment_path(token: str) -> bool:
    return bool(_FRAGMENT_BASENAME.match(token.rsplit('/', 1)[-1]))


def capture_sites(text: str) -> list[CaptureSite]:
    """Return every fragment write or registration a document instructs, with its path."""
    sites: list[CaptureSite] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in _FRAGMENT_FILE_FLAG.finditer(line):
            path = _clean(match.group(1))
            if not _METAVAR.match(path):
                sites.append(CaptureSite(number, 'registration', path))
        for match in _ITEM_FLAG.finditer(line):
            _aspect, separator, raw_path = match.group(1).partition('=')
            path = _clean(raw_path)
            if separator and _is_fragment_path(path):
                sites.append(CaptureSite(number, 'registration', path))
        for match in _REDIRECT.finditer(line):
            path = _clean(match.group(1))
            if _is_fragment_path(path):
                sites.append(CaptureSite(number, 'redirect', path))
        if _WRITE_TOOL.search(line):
            for match in _BACKTICKED.finditer(line):
                path = match.group(1).strip()
                if _is_fragment_path(path):
                    sites.append(CaptureSite(number, 'write', path))
    return sites


def unanchored(sites: list[CaptureSite]) -> list[CaptureSite]:
    """Return the capture sites whose path does not begin with ``{fragment_dir}/``."""
    return [site for site in sites if not site.path.startswith(_ANCHOR)]


def _mentions_capture_keywords(text: str) -> bool:
    return 'collect-fragments' in text and bool(_FRAGMENT_TOKEN.search(text))


def _derive_population() -> dict[Path, list[CaptureSite]]:
    population: dict[Path, list[CaptureSite]] = {}
    for document in sorted(MARKETPLACE_ROOT.rglob('*.md')):
        sites = capture_sites(document.read_text(encoding='utf-8'))
        if sites:
            population[document] = sites
    return population


class TestCaptureSitesAreAnchored:
    """Every capture site in the marketplace writes and registers under ``{fragment_dir}``."""

    def test_no_capture_site_writes_or_registers_a_relative_path(self):
        population = _derive_population()

        violations = [
            f'{document.relative_to(MARKETPLACE_ROOT)}:{site.line} ({site.kind}) {site.path}'
            for document, sites in population.items()
            for site in unanchored(sites)
        ]

        assert population, 'no fragment capture site found under the marketplace bundles'
        assert not violations, 'fragment captures not anchored at {fragment_dir}/:\n' + '\n'.join(violations)

    def test_every_capture_keyword_document_yields_a_parsed_site(self):
        population = _derive_population()
        keyword_documents = {
            document
            for document in MARKETPLACE_ROOT.rglob('*.md')
            if _mentions_capture_keywords(document.read_text(encoding='utf-8'))
        }

        unparsed = sorted(
            str(document.relative_to(MARKETPLACE_ROOT)) for document in keyword_documents - set(population)
        )

        assert keyword_documents, 'no marketplace document names collect-fragments beside a fragment file'
        assert not unparsed, 'documents naming a fragment capture yielded no parsed site:\n' + '\n'.join(unparsed)


class TestCaptureSitePredicate:
    """The predicate flags cwd-relative captures and ignores reader-only mentions."""

    def test_cwd_relative_redirect_and_registration_are_both_flagged(self):
        text = (
            'python3 .plan/execute-script.py x:y:z run > work/fragment-x.toon\n'
            'python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add '
            '--plan-id p --aspect x --fragment-file work/fragment-x.toon\n'
        )

        flagged = unanchored(capture_sites(text))

        assert [(site.line, site.kind) for site in flagged] == [(1, 'redirect'), (2, 'registration')]

    def test_cwd_relative_write_instruction_and_batch_item_are_flagged(self):
        text = (
            'write the fragment to `work/fragment-x.toon` via the `Write` tool\n'
            'collect-fragments register --item x=work/fragment-x.toon\n'
        )

        flagged = unanchored(capture_sites(text))

        assert [(site.line, site.kind) for site in flagged] == [(1, 'write'), (2, 'registration')]

    def test_equals_form_registrations_are_flagged(self):
        text = (
            'collect-fragments add --aspect x --fragment-file=work/fragment-x.toon\n'
            'collect-fragments register --item=x=work/fragment-x.toon\n'
        )

        flagged = unanchored(capture_sites(text))

        assert [(site.line, site.kind, site.path) for site in flagged] == [
            (1, 'registration', 'work/fragment-x.toon'),
            (2, 'registration', 'work/fragment-x.toon'),
        ]

    def test_anchored_equals_form_registrations_are_not_flagged(self):
        text = 'add --fragment-file={fragment_dir}/fragment-x.toon\nregister --item=x={fragment_dir}/fragment-x.toon\n'

        sites = capture_sites(text)

        assert len(sites) == 2
        assert unanchored(sites) == []

    def test_anchored_captures_are_not_flagged(self):
        text = (
            'run > {fragment_dir}/fragment-x.toon\n'
            'add --fragment-file {fragment_dir}/fragment-x.toon\n'
            'writes to `{fragment_dir}/fragment-x.toon` via the `Write` tool\n'
        )

        sites = capture_sites(text)

        assert len(sites) == 3
        assert unanchored(sites) == []

    def test_reader_mention_and_signature_metavar_are_not_capture_sites(self):
        text = (
            'reads the forwarded block of `work/fragment-artifact-consistency.toon`\n'
            'add --plan-id PLAN_ID --aspect ASPECT --fragment-file FRAGMENT_FILE\n'
            'register --plan-id PLAN_ID --item ASPECT=FRAGMENT_FILE\n'
        )

        assert capture_sites(text) == []
