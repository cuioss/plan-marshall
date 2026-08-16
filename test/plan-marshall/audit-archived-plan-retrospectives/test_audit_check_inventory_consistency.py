#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``billing-composition`` registration, and the index surfaces that must agree
with the check registry.

The inventory is stated in four places and each must match: the module
docstring's enumeration, the source's count prose, ``SKILL.md``'s
available-checks table, and ``SKILL.md``'s count prose. The docstring guard is
itself pinned red against a docstring missing an entry, so it cannot pass
vacuously.
"""

import re

from _audit_fixtures import (
    AUDIT_SCRIPTS_DIR,
    audit,
    minimal_corpus,
)

_AUDIT_SOURCE = AUDIT_SCRIPTS_DIR / "audit.py"
_SKILL_DIR = AUDIT_SCRIPTS_DIR.parent
_SKILL_MD = _SKILL_DIR / "SKILL.md"
_CHECKS_DIR = _SKILL_DIR / "checks"

# Number words for the count-prose claims. This is a SPELLING table, not a pinned
# count: the expected word is looked up from ``len(CHECK_NAMES)`` on every run, so
# adding a check moves the expectation automatically instead of freezing today's
# number. A count outside the covered range fails loudly (KeyError) rather than
# silently skipping the assertion.
_COUNT_WORDS = {
    20: "twenty",
    21: "twenty-one",
    22: "twenty-two",
    23: "twenty-three",
    24: "twenty-four",
    25: "twenty-five",
    26: "twenty-six",
    27: "twenty-seven",
    28: "twenty-eight",
    29: "twenty-nine",
    30: "thirty",
}

# A per-check bullet HEAD in the module docstring's enumeration: a backticked
# check name at column 0. Continuation lines are indented and sub-bullets are
# nested, so only the enumeration's own entries match — a prose mention of a check
# name inside another bullet's body (which is exactly how
# ``architecture-lookup-ratio`` hid for so long) is NOT counted as a bullet.
_DOCSTRING_BULLET_RE = re.compile(r"^- `([a-z0-9-]+)`", re.MULTILINE)


def _docstring_bullet_checks(docstring: str) -> list[str]:
    """Return the check names the docstring's per-check bullet enumeration names."""
    return _DOCSTRING_BULLET_RE.findall(docstring)


def _drop_bullet(docstring: str, name: str) -> str:
    """Return *docstring* with the ``- `name`` bullet and its continuation removed.

    Used to reconstruct the PRE-FIX docstring so the index-completeness guard can
    be shown to go red for the right reason.
    """
    out: list[str] = []
    dropping = False
    for line in docstring.splitlines(keepends=True):
        if line.startswith("- `"):
            dropping = line.startswith(f"- `{name}`")
        elif dropping and line.strip() and not line.startswith("  "):
            dropping = False
        if not dropping:
            out.append(line)
    return "".join(out)


def test_billing_composition_registered_and_ordered_before_synthesis():
    # Registered in every table, and inserted BEFORE the facet-completeness critic
    # so the "synthesis runs last" invariant survives the addition.
    assert "billing-composition" in audit.CHECK_NAMES
    assert "billing-composition" in audit.CROSS_PLAN_CHECKS
    assert "billing-composition" in audit.CHECK_ERA
    # Its figures are cost-composition ratios, so a non-shipping plan must not
    # dilute them — it belongs to the delivery-cost partition.
    assert "billing-composition" in audit.DELIVERY_COST_CHECKS
    assert "billing-composition" not in audit.FULL_CORPUS_CHECKS
    assert audit.CHECK_NAMES[-1] == "cross-check-synthesis"
    assert audit.CHECK_NAMES.index("billing-composition") < audit.CHECK_NAMES.index(
        "cross-check-synthesis"
    )


def test_billing_composition_carries_this_plan_pr_boundary():
    # The check is introduced by this plan, and the same plan widens the per-phase
    # key set its byte-composition figures read, so its era boundary is this plan's
    # own PR — RESOLVED to #1086. It was seeded as the PR-PENDING sentinel and
    # filled by project:finalize-step-era-stamp-fill once create-pr allocated the
    # number. This is the co-changing mirror of the audit.py CHECK_ERA constant;
    # the pair is rewritten in lock-step by that step, so this assertion is the
    # designated acceptance for era-fill firing from a composed manifest.
    assert audit.CHECK_ERA["billing-composition"] == "#1086"


def test_full_sweep_emits_billing_composition_block(tmp_path):
    # The full sweep emits the block, era-stamped, ahead of cross-check-synthesis.
    inputs = minimal_corpus(tmp_path)

    output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

    assert (
        "check: billing-composition\nstatus: success\n"
        f"fixed_since: {audit.CHECK_ERA['billing-composition']}" in output
    )
    assert output.index("check: billing-composition") < output.index(
        "check: cross-check-synthesis"
    )


def test_module_docstring_enumerates_every_registered_check():
    # INDEX-COMPLETENESS GUARD (population-derived). The expected set is derived
    # from CHECK_NAMES rather than restated as a second literal list, which is what
    # makes this guard fail on the NEXT check added too instead of pinning today's
    # number. Both directions are asserted: no registered check lacks a bullet, and
    # no bullet names something that is not a registered check.
    bullets = _docstring_bullet_checks(audit.__doc__ or "")

    assert set(bullets) == set(audit.CHECK_NAMES), (
        f"docstring bullets vs CHECK_NAMES differ: "
        f"missing={sorted(set(audit.CHECK_NAMES) - set(bullets))}, "
        f"unexpected={sorted(set(bullets) - set(audit.CHECK_NAMES))}"
    )
    # Cardinality is asserted separately from set equality so a DUPLICATE bullet
    # (which set equality cannot see) is caught too.
    assert len(bullets) == len(audit.CHECK_NAMES), bullets


def test_docstring_index_guard_is_red_against_the_pre_fix_docstring():
    # MATCHED POSITIVE CONTROL for the guard above. `architecture-lookup-ratio` was
    # the pre-existing gap: it is a registered check whose only appearance was
    # inside the `exploration-share` bullet's PROSE, with no bullet of its own.
    # Reconstructing that pre-fix state must drive the guard red — otherwise the
    # guard is vacuous and would pass over any future omission just as silently.
    full = audit.__doc__ or ""
    assert "architecture-lookup-ratio" in _docstring_bullet_checks(full), (
        "the repaired architecture-lookup-ratio bullet is missing"
    )

    pruned = _drop_bullet(full, "architecture-lookup-ratio")
    pruned_bullets = _docstring_bullet_checks(pruned)

    # The name still appears in the pruned text (as prose inside another bullet),
    # which is precisely why a substring search would NOT have caught the gap — the
    # bullet-head parse is what makes the guard honest.
    assert "architecture-lookup-ratio" in pruned
    assert "architecture-lookup-ratio" not in pruned_bullets
    assert set(pruned_bullets) != set(audit.CHECK_NAMES)
    assert len(pruned_bullets) == len(audit.CHECK_NAMES) - 1


def test_audit_source_count_prose_matches_the_registry():
    # The module docstring and the argparse `description` carry the SAME count
    # sentence, so both must agree with len(CHECK_NAMES) and no stale spelling may
    # survive anywhere in the file.
    source = _AUDIT_SOURCE.read_text(encoding="utf-8")
    expected = _COUNT_WORDS[len(audit.CHECK_NAMES)]

    assert source.count(f"across {expected} retrospective checks") == 2, (
        "both the module docstring and the argparse description must carry the "
        "current count"
    )
    for count, word in _COUNT_WORDS.items():
        if count == len(audit.CHECK_NAMES):
            continue
        assert f"across {word} retrospective checks" not in source, word


def test_skill_md_available_checks_table_names_every_registered_check():
    # The SECOND index surface over the check set (the docstring enumeration is the
    # first). Population-derived from CHECK_NAMES, and it asserts two things that
    # can fail independently: the table links the sub-document, and that
    # sub-document actually exists on disk.
    text = _SKILL_MD.read_text(encoding="utf-8")
    for check in audit.CHECK_NAMES:
        assert f"checks/{check}.md" in text, f"{check} missing from the Available checks table"
        assert (_CHECKS_DIR / f"{check}.md").is_file(), f"{check} sub-document missing on disk"
        assert f"`{check}`" in text, f"{check} missing from the --check valid-names list"


def test_skill_md_count_prose_matches_the_registry():
    # Both SKILL.md count claims — the frontmatter `description` and the body's
    # "N-check retrospective auditor" line — agree with len(CHECK_NAMES), and no
    # stale spelling survives.
    text = _SKILL_MD.read_text(encoding="utf-8")
    expected = _COUNT_WORDS[len(audit.CHECK_NAMES)]

    assert f"across {expected} retrospective checks" in text
    assert f"{expected.capitalize()}-check retrospective auditor" in text
    for count, word in _COUNT_WORDS.items():
        if count == len(audit.CHECK_NAMES):
            continue
        assert f"across {word} retrospective checks" not in text, word
        assert f"{word.capitalize()}-check retrospective auditor" not in text, word
