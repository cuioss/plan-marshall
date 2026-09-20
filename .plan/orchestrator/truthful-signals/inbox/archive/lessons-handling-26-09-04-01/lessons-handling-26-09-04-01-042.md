envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T13:33:51Z

component=plan-marshall:phase-6-finalize
category=bug

# CORRECTION to `lessons-handling-26-09-04-01-025.md` — its stated resolution is now FALSE, and the real resolution went the other way

⛔ **This corrects a correction I filed here, which has since been overtaken by events in Token-Sheriff.
Please read it against `-025` and `-023` together.**

## What `-025` claimed, and why it is now wrong

`-023` reported that `pre-push-quality-gate` declares `mutates_source: false` while Token-Sheriff's
`-Ppre-commit` command mutates the tree, so the dispatcher skips commit instrumentation and any diff the
step produces has no owner.

`-025` then told you the **observed instance was resolved**: Token-Sheriff PLAN-12 (PR #720) had unbound
both inherited mutating executions to `<phase>none</phase>`, so `-Ppre-commit` was genuinely non-mutating
and `mutates_source: false` had become a **correct** declaration for that project.

⛔ **That is no longer true.** Two subsequent commits reversed the approach entirely:

- **#728 `chore: realign -Ppre-commit with the org norm (auto-fix)`** — removed PLAN-12's `<phase>none</phase>`
  unbindings **and** the two assertions (`assert-license-headers-unchanged`, `assert-no-rewrite-changes`)
  that PR #713 had added. The profile is an **auto-fixer again, and it mutates.**
- **#729 `chore: declare the pre-commit profile as source-mutating`** — added to that project's
  `marshal.json`: `"extension_defaults": { "build.maven.profiles.mutating": "pre-commit" }`.

## The resolution inverted, and the inversion is the interesting part

`-025` said reality was corrected to match the declaration. **The opposite happened: the declaration was
corrected to match reality.** The project stopped fighting the org norm's auto-fixer, kept the mutation,
and told the harness the truth so the dispatcher can instrument and own the diff.

⚠ **Both routes close `-023`'s concrete failure** — a mutating step whose diff nobody owns — but they
imply different things about the harness:

- Under `-025`'s (now void) route, nothing in the harness needed to change.
- Under the actual route, the harness's behaviour is **load-bearing**: it must read
  `build.maven.profiles.mutating`, conclude the step mutates, and instrument the commit. If that path is
  wrong or unread, the diff is unowned again — with no local signal, because the project has now done
  everything correctly on its side.

⛔ **So `-023`'s mechanism question is not closed and should not be closed on `-025`'s reasoning.** What I
withdrew in `-025` was the evidence; what I am withdrawing now is the withdrawal's justification. The
right reading is: *a project can declare a mutating gate truthfully, and whether that declaration is
honoured is entirely on the harness side.*

## One further consequence worth your attention

The assertions PR #713 added — the ones whose ordering defect `-023`'s sibling reports described — are
**no longer in that project's tree at all**. Whether the org norm supplies equivalents is a question for
that project, not for you. It is noted here only so a reader of `-023`/`-025` does not go looking for a
gate configuration that no longer exists.
