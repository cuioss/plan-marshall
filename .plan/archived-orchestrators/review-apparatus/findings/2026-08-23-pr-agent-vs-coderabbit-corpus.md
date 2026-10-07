# Corpus analysis — pr-agent vs CodeRabbit review quality

A population-backed comparison, replacing the per-PR anecdotes (n=1..3) that every prior
comparison in this epic rested on. Read-only; nothing in the repository was changed.

## The question, and why the existing instrument cannot answer it

`review_retrospective.py` reports pr-agent's `actionable_count` as **0 on every PR it has
ever reviewed**. That is not a quality measurement — it is a bucketing artefact. pr-agent
posts exactly ONE `issue_comment` per PR (the `## PR Reviewer Guide 🔍` table, updated in
place on re-review); the aggregator maps `issue_comment` → meta unconditionally. So the
authoritative table scores pr-agent zero regardless of what the comment contains.

Any comparison that reads that table answers a question about comment *shape*, not review
*quality*. This analysis therefore re-counts from the raw `pr-comment.jsonl` substrate and
opens pr-agent's comment bodies, which is the only unit comparable to a CodeRabbit inline
comment.

## Population — and what was excluded, by name

| Figure | Value |
|---|---:|
| `pr-comment.jsonl` stores walked | 1912 |
| excluded as pytest scratch | 1689 |
| stores included | 223 |
| records read | 1383 |
| records unparseable | 0 |
| records dropped (no `pr_number`) | 1 |
| duplicate records collapsed | 29 |
| **unique records** | **1353** |
| distinct PRs | 224 |

**The exclusion is stated, not silent.** 1689 stores sit under `.plan/local/worktrees/**`
and `.plan/temp/pytest-basetemp/**` — pytest scratch inside the five live worktrees, carrying
synthetic authors (`alice`, `bob`, `octocat`, `carol`, `dave`, `randombot[bot]`,
`some-retired-bot`, `human-reviewer`, …). An aggregate that swallowed them would have
reported 2368 records and 273 PRs, roughly three-quarters of it fixture data.

**Coverage boundary.** pr-agent's records span PR **#1013 – #1134**. Nothing after #1134 is
in this corpus — including all thirteen cloud-wave PRs (#1141–#1241) and everything since —
because a `doc/plans/` lane run never writes `.plan/`. This measures one era, not all time,
and the blind spot is the same one PLAN-PR-031 exists to close.

## Volume — and why volume is the wrong axis

Era-matched (PRs ≥ #1013, the first pr-agent appearance), on the **33 PRs where both bots
filed**:

| Reviewer | Records | Records/PR | inline | review_body | issue_comment |
|---|---:|---:|---:|---:|---:|
| CodeRabbit | 212 | 6.42 | 136 | 45 | 31 |
| pr-agent | 34 | 1.03 | **0** | **0** | 34 |

pr-agent's 1.03 records/PR is its posting convention, not its output. Opening the 51 guide
bodies gives the real count:

| pr-agent body-level | Value |
|---|---:|
| PR Reviewer Guides parsed | 51 |
| focus-area findings, total | **17** |
| mean per guide | 0.33 |
| guides with **zero** findings | **36 / 51 (70.6%)** |
| guides carrying a security concern | **1 / 51** |

The zero-finding body is a canned 242-byte table: *"No security concerns identified / No major
issues detected"*. The security cell is **absent** on 51 of 52 bodies — pr-agent has flagged a
security concern exactly once (#1113, a TOCTOU symlink hazard), despite a charter that is
explicitly security-weighted.

## The measurement that matters: paired recall on the same diff

Restricted to the 33 PRs where **both** bots filed, so neither bot's absence is being read as
a clean review (a refused reviewer and a clean one are represented identically — the known
defect owned by PLAN-PR-026).

- pr-agent returned **"no major issues"** on **22 of 33** PRs.
- On **20 of those 22**, CodeRabbit had at least one finding that was subsequently **repaired**.
- Total CodeRabbit `fixed` findings inside pr-agent's clean verdicts: **68**.

### Controlling for the trigger confound

pr-agent has no `synchronize` push trigger (#1048 shipped, reverted #1053), so it sees the
opening commit plus explicit loopback re-reviews, while CodeRabbit sees every round. A finding
on a commit pr-agent never saw is not a recall miss. Splitting the 68 by
`reviewed_commit_sha`:

| Bucket | Count |
|---|---:|
| on a commit **pr-agent did review** — genuine recall miss | **47** |
| on a commit pr-agent never saw — trigger confound | 21 |
| indeterminate (sha missing on one side) | 0 |

**Of 22 clean bills of health, 17 were contradicted at the exact commit pr-agent examined.**
Three more (#1043, #1067, #1074) are fully explained by the trigger gap. Two (#1024, #1056)
are genuine agreement — CodeRabbit found nothing repairable either.

**Field validation.** `reviewed_commit_sha` was checked against the commit pr-agent's own body
names (*"Review updated until commit …"*). Six bodies carry that marker; the field agreed with
all six and contradicted none. n=6 is a small witness set — the field is corroborated, not
proven. The residual risk is one-directional: dedupe keeps the first-seen sha for a re-fetched
comment, which would push a same-commit miss into the `diff` bucket. The bias **deflates** the
47, so the recall gap is a floor, not a ceiling.

### Severity of the 47

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | **15** |
| Minor | 26 |
| Trivial | 6 |

Not nitpicks. Fifteen Major-severity defects were repaired on commits pr-agent had just
declared free of major issues — spanning `manage-config.py`, `_cmd_classification_validate.py`,
`branch-cleanup.md`, `arch-gate-java/SKILL.md`, and four test modules.

## Precision — the axis where pr-agent is not better either

Rejection (triage-assigned false positive) on the paired subset:

| Reviewer | Rejected | Records | Rate |
|---|---:|---:|---:|
| CodeRabbit | 13 | 212 | 6.1% |
| pr-agent | 4 | 33 | 12.1% |

Read per *finding* rather than per record, pr-agent produced 17 focus findings of which 5
records were rejected — a materially worse hit rate than CodeRabbit's, on a small n.

## What pr-agent does deliver

The operator decision making pr-agent the sole required bot was taken on **reliability**, and
that ground is intact:

- Era presence: pr-agent **51 of 62** PRs (82.3%); CodeRabbit **42 of 62** (67.7%). pr-agent has
  neither a per-account quota nor a diff-size refusal.
- On **18 era PRs pr-agent filed and CodeRabbit did not.** Four carried findings; **two were
  repaired** — #1041 (`Inconsistent Schema`) and #1047 (`False Positive Q-Gate Failure`).
  #1041 is the decisive case: CodeRabbit and Sourcery both *refused*, and pr-agent was the only
  bot that actually reviewed the 48-file diff.

⛔ That 18 is **not** evidence CodeRabbit failed there — absence of a record conflates refusal
with silence. It is evidence only that pr-agent showed up.

## Verdict

**On finding defects, the two are not comparable — CodeRabbit is the reviewer and pr-agent is
a smoke alarm that has fired 17 times in 51 PRs.** 70.6% of pr-agent's reviews say nothing at
all, and 77.3% of its clean verdicts were false at the commit it examined, by 47 repaired
defects of which 15 were Major.

**On availability, pr-agent is the better instrument**, and that is why it is required.

⛔ **RETRACTED, same day:** an earlier revision of this document closed with *"the reason it never
refuses is the same reason it says little"*. That asserted a shared cause which was never measured,
and it is wrong. The two properties have separate, independently addressable causes: it never refuses
because it carries no per-account quota and no diff-size refusal (it **clips** instead); it says
little because of the `/review` tool's prompt schema. Nothing forces the second to follow from the
first — the framing implied an inherent trade-off where there is a fixable defect. See § The lever
that was already pulled.

The failure mode this creates is specific and dangerous: **a required bot whose default output
is a clean bill of health, wired to a gate that cannot distinguish "reviewed and clean" from
"reviewed and blind".** A green required check currently carries almost no information about
whether the diff was actually scrutinised.

## What this implies for the staged queue

- **PLAN-PR-026** (*"nobody reviewed" and "reviewed clean" are still one signal*) is the
  load-bearing plan, and this analysis sizes it: the collapsed state is the **majority** case
  for the required bot, not an edge case.
- **PLAN-PR-030** (*the instrument can report our gates perfect*) is confirmed from a second
  direction — `actionable_count: 0` for pr-agent on 100% of PRs is the same class of defect as
  `structural_share: 100.0` at `reviewer_coverage: 1/1`.
- **PLAN-PR-034** (*a refusal nobody recognises*) gains a measured denominator: pr-agent
  declares zero `refusal_patterns`, and this corpus shows its non-refusal is structural.
- **PLAN-PR-031** (*the record of what we did is itself unverified*) — the corpus stops dead at
  #1134. Every PR since is unmeasured because the lane never wrote `.plan/`.

## What this does NOT establish

1. **Ground truth is triage disposition, not adjudication.** `fixed` means the team repaired
   something. It is a strong proxy for a true positive, not an independent verdict — and
   PLAN-PR-037 documents that `resolve_finding` never reconciles the bucket against
   `resolution_detail`, so a bucket can contradict its own text.
2. **One era only** (#1013–#1134). Model versions, `path_instructions`, and the settings ladder
   all moved during and after it. This is not a claim about pr-agent's current configuration.
3. **The 22-PR paired cell is small.** The direction is unambiguous and the effect is large, but
   a 22-PR sample supports a verdict, not a precise rate.
4. **Nothing here was re-derived from the live PRs.** It is the findings store as our own
   pipeline recorded it. Where the pipeline drops comments (PLAN-PR-029 D1's unanchored
   `ignore.low` regexes destroying whole findings), this corpus inherits the loss — which, again,
   would understate CodeRabbit's volume, not overstate it.

---

## The lever that was already pulled — and did not work

Added after the first revision, because the corpus window **straddles** material changes to
`cuioss/pr-agent-settings`. A single blended rate mixes two regimes, so the comparison above was
re-cut on the merge dates of the config commits that touch review depth.

| Epoch | Boundary | Config state |
|---|---|---|
| A | `< 2026-07-28T09:07Z` | original charter (three stacked suppressors, six AppSec bullets), `max_model_tokens` 32000, `num_max_findings` 5, `temperature` 0.2 |
| B | `07-28T09:07Z – 07-29T12:07Z` | charter fix (#5), ceiling 256000 (#6), temperature 1.0 (#7), description 2000 (#9), intent-as-claim (#10) |
| C | `>= 2026-07-29T12:07Z` | charter contests the empty-list permission, `num_max_findings = 12` (#13) |

| Epoch | PRs | findings | findings/PR | silent | silent % | security |
|---|---:|---:|---:|---:|---:|---:|
| A | 4 | 3 | 0.75 | 1 | 25.0% | 0 |
| B | 17 | 4 | 0.24 | 13 | 76.5% | 0 |
| C | 30 | 10 | 0.33 | 22 | **73.3%** | 1 |

Paired recall, per epoch (both bots filed):

| Epoch | paired PRs | pr-agent silent | same-commit CodeRabbit `fixed` inside those |
|---|---:|---:|---:|
| A | 4 | 1 | 1 |
| B | 9 | 8 | 12 |
| C | 20 | 13 | **34** |

Epoch A's n=4 is too small to carry weight and its higher rate is noise. The load-bearing row is
**C: thirty PRs under the strongest charter this org has written, ten findings against a ceiling of
twelve, and 73.3% of reviews carrying nothing.** The charter rewrite that was designed specifically
to contest the empty-list permission moved the silent rate by **3.2 points**.

⭐ **This closes the charter lane by measurement, not by argument.** `.pr_agent.toml` records the
model lane as already closed the same way — a controlled run across `3.5-flash` / `2.5-pro` /
`3.6-flash` produced byte-identical 242-byte output. Neither knob reachable from central config is
the binding constraint.

The constraint is the `/review` tool's own output schema. `key_issues_to_review`'s field description
in the pinned image (`pr_reviewer_prompts.toml:150`) grants explicit permission to return an empty
list, and `extra_instructions` is appended as a *separate block* — it argues alongside that
description rather than replacing it. The config's own comments predicted this; the epoch data is
the confirmation.

⛔ **Do not spend another round on charter text.** Two rounds bought three points. A third is not a
different experiment.

**Date basis caveat.** Epochs are assigned from the finding record's ingestion `timestamp` (filed
during the plan's finalize), which is a proxy for review time, not review time. Records land *after*
the review, so the boundary can only push a record later than its true epoch — the bias understates
A and flatters C. The direction of the C result survives it.

## The surface that has never been tried

`/improve` (`[pr_code_suggestions]`) is a **different tool with a different prompt and no empty-list
clause**. It is fully tuned centrally as of `pr-agent-settings#14` (2026-08-09):
`commitable_code_suggestions = true`, a charter carrying the same substantiation bar, a stated
ceiling of 12.

**It has never run on a real pull request in this corpus — zero inline records across 223 stores and
224 PRs.** (An earlier count of 7 inline records was pytest fixture data and does not survive the
scratch exclusion.) The reason is gating, not capability: `reusable-pr-agent-review.yml` declares
`auto-improve` defaulting to **false**, with a per-PR `pr-agent-improve` label as the ordinary
opt-in, and this repository's caller passes no input at all. The capability has been configured and
unused.

## Action taken — 2026-08-23

**PR #1334** (`feature/pr-agent-improve-pilot`) enables `auto-improve: true` on this repository's
caller. Repository-scoped, one line, reversible. Operator-chosen scope: pilot here first rather than
an org-wide fan-out, so the first production observations of `/improve` are bought before 21
consumer repos are committed to it.

⚠ **The pilot ships a known unguarded surface, recorded so it is not later mistaken for a
measurement.** The reusable workflow's fail-closed gate keys on the `review` output and is
deliberately not extended to `/improve`, which writes the separate `improve` key. An empty suggestion
set is therefore indistinguishable from a run that never happened — **this epic's own PLAN-PR-026
defect, reproduced on a new surface.** Closing it needs an oracle in the org workflow. Until then an
absent suggestion set reads **UNKNOWN**, never clean.

## Remaining levers, ranked

1. **`/improve` as the finding surface** — in flight as #1334. The only untried lever with no
   measurement against it.
2. **The `synchronize` trigger** — recovers the 21 of 68 misses that sat on commits pr-agent never
   saw (~31% of the gap). Needs `handle_push_trigger` + `push_commands` **and** a narrowed
   fail-closed gate, because the runner legitimately no-ops on merge commits, bot commits, and
   unchanged SHAs. Org-workflow work, 21-repo fan-out. Not a one-liner — see #1048/#1053.
3. **An `/improve` oracle in the org workflow** — turns lever 1 from a hope into a measurement, and
   is the same work PLAN-PR-026 scopes locally.
4. ⛔ **Not reachable by configuration at all.** CodeRabbit executes verification scripts against the
   tree before asserting — `ast-grep`, `rg`, `fd` and python probes appear in its comment bodies
   (`#1113`, `Length of output: 29579`). PR-Agent has no such facility, and no tool switch, charter,
   or model supplies one. Independence from CodeRabbit cannot be bought entirely from this bot; the
   remainder has to come from in-house deterministic gates, which is `PLAN-PR-030`'s territory.

---

## ⛔ QUALIFICATION added same day — the corpus measures a configuration that no longer exists

Two facts found while scoping the fix, both of which bound every number above:

**1. pr-agent's last measured PR is #1129.** The domain-routed charter landed at **#1130**
(`f5493b437`, 2026-08-09 — this epic's own shipped PLAN-PR-022, *"a generic charter cannot see a
language-specific defect"*), refined at #1313. Checked directly: `cuioss-review-bot` has **zero**
records at or after #1130. Epoch C's thirty PRs all sit in #1055–#1129. So **not one measured PR ran
under the charter this repository uses today**, and #1334 has since added `/improve` on top.

**2. "Do not spend another round on charter text" is OVERSTATED as written.** It is established for
*exhortation* — that is what `pr-agent-settings` #5 and #13 were, and B→C moved silence 3.2 points.
It does **not** extend to **concrete domain rules**, which are a different intervention: the
repo-local pack carries ~15 python/plugin rules that each name a mechanism (`shell=True`,
`pickle.loads`, `os.environ` → `Path`, the `untrusted-ingestion` gate). That species has prior
evidence *for* it — `path_instructions` produced 4 valid findings of 5 on #1042. **#1130 is
untested, not refuted.** The blanket instruction is corrected to: do not spend another round on
charter *exhortation*; concrete mechanism-naming rules are a live and unmeasured lever.

⇒ The next measurement is **not** a fresh whole-corpus pass. It is the corpus restricted to
**PRs ≥ #1130**, which currently has a pr-agent population of **zero**.
