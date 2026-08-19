#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The suspect-zero census — the class guard.

A detector that has never produced a positive is indistinguishable, from its
output alone, from one that CANNOT produce one. The census makes every zero
SUSPECT rather than silently clean, and classifies what KIND of zero it is:

* ``structural`` — the check declared it could not measure. Not evidence.
* ``starved`` — the corpus supplied no plans. Not evidence either, for a
  different reason, and with a different remedy.
* ``disciplinary`` — a non-empty corpus was examined and nothing was genuine.
  Evidence about the corpus; never proof the check is able to fire.

The distinction is the deliverable. A census that lumped the three together
would report the same thing for a check whose predicate cannot fire and a check
that is doing its job over a clean corpus.
"""


import re
from pathlib import Path

from _audit_fixtures import audit

#: The scalars a check may declare its EXAMINED population under — bound to the
#: production set rather than restated.
#:
#: A second hand-maintained copy is the very shape this guard exists to detect,
#: and it drifted once already: this list named `plans_with_merge_events` while
#: `_examined_population` did not read it, and no fixture reached the state where
#: the disagreement showed. `TestPopulationKeyCoverage` keeps the set honest from
#: the other side, asserting every `plans_*` scalar any emitter publishes is
#: classified as a denominator or as a documented non-denominator.
_EXAMINED_POPULATION_KEYS = audit._EXAMINED_POPULATION_KEYS


_EMPTY_POPULATION_RE = re.compile(
    rf"^(?:{'|'.join(_EXAMINED_POPULATION_KEYS)}):\s*0\s*$", re.MULTILINE
)


def _declares_empty_population(block: str) -> bool:
    """Does this block state, under ANY of its own names, that it examined nothing?

    Reads the block DIRECTLY rather than calling `audit._examined_population`, and
    that is the point. `_examined_population` applies precedence and falls back to
    the corpus size when it finds no declaration, so an expectation derived from it
    judges a block with an unread population key to have a FULL population — the
    same verdict the census reaches — and the contradiction (block says zero,
    census says "a non-empty examined population") is invisible to both sides. An
    earlier version of this helper did exactly that and passed against the broken
    code.

    The KEY SET is shared with production deliberately; the READING is not. Sharing
    the keys is what stops the two lists drifting apart, and reading independently
    is what stops the assertion becoming a restatement of the implementation.
    """
    return bool(_EMPTY_POPULATION_RE.search(block))


def _shipping_corpus(repo_root: Path) -> list:
    """A one-plan corpus whose plan SHIPS but carries no exploration counters.

    `minimal_corpus`'s plan records no `modified_files`, so it fails
    `_plan_shipped` and every delivery-cost check excludes it — which starves
    those checks by the shipping route and masks the `plans_in_corpus` axis. A
    non-empty `modified_files` makes the plan ship, so the shipping exclusion is
    zero and a check that still reports `plans_in_corpus: 0` did so by its OWN
    narrowing.
    """
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "shipping-plan"
    plan_dir.mkdir(parents=True)
    (plan_dir / "references.json").write_text(
        '{"scope_estimate": "surgical", "modified_files": ["src/a.py"]}',
        encoding="utf-8",
    )
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    return [audit.collect_inputs(plan_dir)]


_UNMEASURED_BLOCK = (
    "check: merge-window-accounting\nstatus: unmeasured\nunmeasured_reason: no substrate\n"
)


_MEASURED_ZERO_BLOCK = (
    "check: dispatch-topology\nstatus: success\ngenuine_signal_count: 0\nrows[3]{a}:\n"
)


_FIRED_BLOCK = (
    "check: dispatch-topology\nstatus: success\ngenuine_signal_count: 2\nrows[3]{a}:\n"
)


def _audit_source() -> str:
    return Path(audit.__file__).read_text(encoding="utf-8")
