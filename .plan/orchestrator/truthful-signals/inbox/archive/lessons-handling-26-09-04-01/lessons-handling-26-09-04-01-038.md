envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T07:59:31Z

component=plan-marshall:manage-architecture
category=bug

# diff-modules --pre reports every module as changed over a byte-identical baseline, so the architecture-refresh Tier-1 gate fires on a false positive

⛔ **RELOCATED FROM THE WRONG STORE — this is a MOVE, not a new report.** It was filed as lesson
`2026-09-08-16-001` in **Token-Sheriff's** lessons store, whose repo does not own the `plan-marshall` bundle.
It is written here first and removed there second (integrate-then-remove), so exactly one copy
exists at every point and none exists in two places.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`. Original id `2026-09-08-16-001`, created 2026-09-08, lifecycle `active` at the time of the move.
⚠ Nine such lessons accumulated because a plan overrode the `wrong_store` guard rather than
routing the lesson to the repo that owns the bundle — the mechanism is reported separately as
`lessons-handling-26-09-04-01-032`. Body reproduced verbatim below.

---

## Context

Observed in TokenSheriff plan `refresh-2a-coverage-priorities`, 2026-09-08, at the
`default:architecture-refresh` finalize step (Tier 0).

Followed the standard exactly: extracted `origin/main`'s committed
`.plan/project-architecture/` via `git archive`, ran `architecture discover --force`, then
`architecture diff-modules --pre {baseline_dir}`.

**The verb reported all 18 modules as `changed` — `added[0]`, `removed[0]`, `changed[18]` — over
input that is byte-identical.** Verified three independent ways:

- `git status --porcelain .plan/project-architecture` → empty. `discover --force` rewrote the
  descriptor to exactly what was already committed.
- `git diff origin/main...HEAD -- .plan/project-architecture` → empty. The branch never touched it.
- `diff -rq {baseline_dir} .plan/project-architecture` → **no output, exit 0**, with 18
  `enriched.json` files on each side and `_project.json` identical at 7311 bytes.

So regenerated == committed == `origin/main`, and the diff still reported total change.

## Impact

The `changed[]` list is not decorative — the standard feeds it to Tier 1, which in `prompt` mode
asks the operator to re-enrich the affected modules via an LLM pass. A false \"all 18 changed\"
therefore proposes a **whole-project re-enrichment for a plan that shifted no descriptor at all**:
maximum cost, zero information. Under `tier_1: auto` it would presumably run that pass unattended.

The failure direction matters. A diff that under-reports hides drift; this one over-reports, so it
cannot cause a stale descriptor — but it makes the signal worthless in the opposite way. A verb that
says \"everything changed\" on every run says nothing on any run, and an operator who sees it twice
learns to skip it, which is how a real 18-module drift would later go unread.

## Directive

Fix `diff-modules` so byte-identical descriptor trees compare equal. The likely cause is comparing a
freshly-discovered in-memory structure against parsed baseline files with a field that is
regeneration-sensitive (a timestamp, an absolute path, or dict/list ordering) rather than comparing
the persisted forms; note that `discover --force` itself writes deterministically here, since it
reproduced the committed bytes exactly.

Add a regression test asserting `changed == []` when the baseline directory is a copy of the current
descriptor tree — the exact condition this run hit.

Until it is fixed, do NOT read a `changed[]` list from this verb as evidence of drift without
corroborating it (`git status` on the descriptor path, or a recursive file diff against the
baseline). In this run the corroboration is what stopped a pointless whole-project re-enrichment.
