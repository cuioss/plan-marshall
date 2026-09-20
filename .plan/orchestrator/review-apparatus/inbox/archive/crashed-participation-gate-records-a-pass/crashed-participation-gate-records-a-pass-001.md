envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=landing
created=2026-08-01T19:05:08Z

## What landed — PR #1070

`fix(automatic-review): stop crashed review_completeness from passing` — 6 commits, verify green (14196 passed, 2 skipped), merging now.

- **Seven list flags relaxed to `nargs='?'` / `const=''`** across two parsers: `review_completeness.py check` (x5) and `github_pr.py fetch_findings` (x2).
- **All four documented call sites quoted.**
- **An UNKNOWN verdict branch** added to `automatic-review/SKILL.md` and `branch-cleanup.md`: a non-zero exit OR a return missing the field is UNKNOWN, never a pass, and the force-done hatch is withdrawn from it.
- **A normative prohibition** in `bot-participation-contract.md`: a check conclusion is neither participation evidence nor a findings-handled record.
- **Tests whose flag populations derive from the live argparse surfaces**, with vacuity guards.

## Mechanism correction — the most important item in this landing

The spec's root-cause story was WRONG, and the epic must carry the correction, not the spec.

The crash is **not** caused by the unquoted placeholder. The generated executor strips every empty-string argument before argparse ever runs:

```python
script_args = [a for a in script_args if a]   # .plan/execute-script.py:989
```

so `--flag ""` and a bare `--flag` are indistinguishable downstream. **Quoting would never have fixed it.** The `nargs='?'` relaxation is the whole fix.

This plan's own first-pass callouts repeated the wrong story and framed quoting and the parser as complementary defences — corrected in commit `5d10ad536`. This matters because an author trusting the old text could add a list flag, quote it, skip `nargs`, and reintroduce the crash.

## Population scope — UNMEASURED, handed back to the epic

The executor strip is **global**, so ANY marketplace script with an optional flag lacking `nargs='?'` that is reachable with an empty value is exposed identically. Whether other such sites exist was **NOT measured**, and this plan claims nothing about it.

Deriving that population — argparse surfaces across all marketplace scripts, filtered to optional-without-`nargs`, crossed with invocation sites that interpolate a possibly-empty placeholder — is a **separate plan**.

Field evidence that it bites: API-Sheriff PR #138 hit exit-2 on 4 `review_completeness` invocations while `automatic-review` still recorded `done`.

## Residue explicitly NOT fixed here

The spec forbids consolidating PR-013 / PR-008 work into this plan. Each item below rides as its own `candidate-lesson` message in this same drain:

1. `classify_bot` participation-precedence launders a live refusal (PLAN-PR-013 wrong-commit class) — observed live on coderabbit this run.
2. `github_re_review` returned `matched:true` AND `refusal_detected:true` in one envelope; the matched signal was CodeRabbit's "does not re-review already reviewed commits" ACK (PLAN-PR-008).
3. Trigger-B self-contradiction: a required bot can become structurally untriggerable, so the loop-back can never clear (PLAN-PR-008).
4. CodeRabbit's auto-generated ACK carried the documented ignore-pattern marker and still survived the noise pre-filter into the findings ledger.
5. Two latent literal-semicolon defects in prescribed `manage-logging` message text — as written, those records can never be emitted in this repo.
6. The unmeasured empty-flag population above.
7. The wrong-mechanism correction itself, as a durable rule.

## Merge caveat the epic must record

Merged on a **KNOWN-PARTIAL review at operator direction**:

- **pr-agent** (the sole required bot) reviewed through `5d10ad536` and **never saw `3e33e54a3`**.
- **coderabbit** was rate-limited and gave no substantive review of the last four commits.
- **sourcery** was `participated_but_empty`.

**Owes a post-merge comment sweep.**
