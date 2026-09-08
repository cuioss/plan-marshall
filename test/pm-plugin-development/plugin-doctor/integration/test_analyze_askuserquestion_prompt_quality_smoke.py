#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-tree regression smoke for the askuserquestion-prompt-quality analyzer.

COLLECTED in the default ``module-tests`` run. The per-check / per-obligation
coverage lives in the in-process unit suite
(``../test_analyze_askuserquestion_prompt_quality.py``) against synthetic
prompt blocks; this module adds the one property no synthetic fixture can
carry — that the prompts this repository actually SHIPS are clean, and stay
clean as new ones are written.

Two assertions, and the second is what keeps the first honest:

* **The corpus is clean** — scanning the shipped ``marketplace/bundles`` tree
  produces an empty finding list. A prompt that reintroduces a workflow step
  number, a tool-API type name, an internal-mechanics noun, or an option that
  never states its consequence fails this test at the commit that adds it.
* **The corpus was actually examined** — the recognizer saw a non-zero number
  of ``AskUserQuestion:`` invocation blocks. An empty finding list on its own
  is not evidence of a clean corpus: a recognizer that stopped matching, or a
  walk that reached no files, produces exactly the same empty list. Without
  this second assertion the first would go on passing as a vacuous green while
  covering nothing.

Why the population is derived rather than read off a finding
------------------------------------------------------------
The analyzer publishes ``population_size`` on each finding it emits, so on a
clean tree — the state this test exists to lock — there is no finding to read
it from. The population is therefore re-derived here through the analyzer's
OWN walk (``_markdown_targets`` + ``_scan_file``), which is the recognizer the
assertion is about: a recognizer that stops matching invocation blocks drives
this number to zero exactly as it drives ``population_size`` to zero.

The assertion is a FLOOR (``> 0``), deliberately not a pinned count. The
number moves with every prompt added to or removed from the shipped bundles,
so pinning it would turn ordinary authoring into a failing build while proving
nothing this floor does not already prove: that the tree was reached and the
recognizer still recognizes.
"""

from __future__ import annotations

from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

# Called with literals rather than through a wrapper so the loader-collision
# guard in test_conftest_loader_contract.py can resolve this call site
# statically — a wrapped call is invisible to it.
_aapq = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_askuserquestion_prompt_quality.py',
    '_analyze_askuserquestion_prompt_quality',
)

analyze_askuserquestion_prompt_quality = _aapq.analyze_askuserquestion_prompt_quality
_markdown_targets = _aapq._markdown_targets
_scan_file = _aapq._scan_file


def _examined_block_population(marketplace_root: Path) -> int:
    """Return how many ``AskUserQuestion:`` invocation blocks the walk examines.

    Sums the per-file block count the analyzer's own file scanner reports over
    the analyzer's own target walk, so this number is the same one the
    analyzer would publish as ``population_size`` had any violation been found.
    """
    population = 0
    for md_path in _markdown_targets(marketplace_root):
        _violations, blocks, _read_errors = _scan_file(md_path)
        population += blocks
    return population


class TestShippedPromptCorpusStaysClean:
    """The prompts this repository ships must keep passing the analyzer."""

    def test_shipped_marketplace_prompts_produce_no_findings(self) -> None:
        findings = analyze_askuserquestion_prompt_quality(MARKETPLACE_ROOT)
        assert findings == [], (
            f'{len(findings)} askuserquestion-prompt-quality finding(s) in the shipped '
            f'bundles under {MARKETPLACE_ROOT}. Each names the obligation it violates '
            f'and the file:line that carries it:\n'
            + '\n'.join(
                f'  {finding["file"]}:{finding["line"]}: {finding["description"]}'
                for finding in findings
            )
        )

    def test_the_shipped_corpus_was_actually_examined(self) -> None:
        population = _examined_block_population(MARKETPLACE_ROOT)
        assert population > 0, (
            f'The analyzer examined {population} AskUserQuestion invocation block(s) under '
            f'{MARKETPLACE_ROOT}, so the clean result above certifies nothing. Either the '
            f'invocation-block recognizer stopped matching the shipped prompt form, or the '
            f'markdown walk reached no files.'
        )
