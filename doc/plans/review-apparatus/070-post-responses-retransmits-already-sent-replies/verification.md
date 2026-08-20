# Verification — 070-post-responses-retransmits-already-sent-replies

**Landed as:** PR #1187, squash commit `c89bfc53`
**Verdict:** verified-with-gaps

The plan's four deliverables all landed, the fix is real, and every test the report names exists and
passes in the current tree. Three substantive defects survive: one genuine duplicate-transmit path the
fix does not close (and which additionally reports a transmitted disposition as `untransmitted`), and
four stale prose restatements of the pre-fix skip taxonomy — in the two workflow documents that
*invoke* the verb (one of them twenty-two lines above the corrected paragraph in the same document),
in the Sonar skill and its own inline comment, and in `_findings_core.py`'s new reader enumeration;
see § Completeness review for the four sites. Beyond
those, the D0 consumer enumeration is incomplete in its record (its "sole production invoker" claim is
refutable from the bundle) without that incompleteness changing any behaviour.

## Method

Read in full: `plan.md`, `report-01.md`.

Diff read: `git show --stat -M c89bfc53`; `git show c89bfc53 -- <path>` for `github_pr.py`,
`_findings_core.py`, `verification-feedback.md`, `workflow-integration-github/SKILL.md`.

Ground truth is the current tree. Every source read below was taken at `61a43e53`; sibling verification
sessions have since advanced HEAD with `doc/plans/`-only commits, and
`git diff --stat 61a43e53 HEAD -- marketplace/ test/ .claude/` is empty, so the source ground truth is
unchanged. Later commits touching the same files were enumerated with
`git log --oneline c89bfc53..HEAD -- <paths>` → `d3ba81fd`, `9e9e9880`, `38548923`, `66a5d66b`,
`b19ef4a6`.

Current-tree reads: `github_pr.py` §`cmd_post_responses` (lines 1483–1699), `_findings_core.py`
§`resolve_finding` / §`resolve_findings_by_type` / §`mark_finding_responded` (lines 440–575),
`gitlab_pr.py` §`cmd_post_responses` (lines 346–447), `sonar.py` §`cmd_post_responses` (lines 704–780),
`verification-feedback.md` §Step 8 (lines 237–266), `workflow-integration-github/SKILL.md` §Workflow 2
step 4 (lines 152–175), `workflow-pr-doctor/standards/automated-review-lifecycle.md` §Step 4.5 (lines
133–160), `manage-findings/standards/jsonl-format.md`, `manage-findings/SKILL.md`,
`.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`,
`test/_shared/_dispatch_roster.py`.

Searches run (all from the repository root):

- `grep -rn "count_responded" --include=*.md --include=*.py --include=*.toon --include=*.json .` excluding
  `doc/plans/` and `.git/` — the exact D0 method, re-run.
- `grep -rn "'responded'|\"responded\"|responded_at" marketplace/bundles/plan-marshall/skills/ --include=*.py`
- `grep -rn "responded" marketplace/bundles/ --include=*.md` — eleven hits; four are the marker
  (`workflow-integration-github/SKILL.md:162,169`, `workflow-integration-gitlab/SKILL.md:74`,
  `workflow-integration-sonar/SKILL.md:148`), one is the corrected Step 8 paragraph
  (`verification-feedback.md:265`), and the rest are the ordinary English word in
  `automatic-review` participation prose — the same-name trap the plan warned about.
- `grep -rn "responded" marketplace/bundles/plan-marshall/skills/manage-findings/` (hits in `.py` only)
- `grep -rn "resolve_finding|resolve_findings_by_type|update_jsonl_in_dir|update_jsonl\(" marketplace/bundles/ --include=*.py`
  — the complete set of record-mutation entry points.
- `grep -rn "no_resolution_detail|Only a finding with no|nothing to transmit" marketplace/bundles/ --include=*.md`
- `grep -rn "post_responses|RESPOND" marketplace/bundles/ --include=*.md`, plus
  `grep -rn "post_responses --pr-number|github_pr \\\\" marketplace/bundles/ --include=*.md` to separate
  *executable invocation blocks* from mere references.
- `grep -n "^def test_post_responses" test/plan-marshall/workflow-integration-github/test_github_pr.py`
- `grep -rn "responded" test/plan-marshall/workflow-integration-sonar/*.py`
- `grep -rn "threads_resolved" marketplace/ test/ .claude/`
- `grep -rn "'reason':" .../github_pr.py` — the complete skip/untransmitted reason vocabulary.

Tests run (no repository file modified; probes written to the session scratchpad only):

- `.venv/bin/python -m pytest test/plan-marshall/workflow-integration-github/test_github_pr.py -o addopts="" -q -k post_responses`
  → **14 passed**.
- `.venv/bin/python -m pytest test/plan-marshall/manage-findings/test_findings_store.py -o addopts="" -q -k responded`
  → **3 passed**.
- Two scratchpad probes (importing the real modules through `test/conftest.py`'s `load_script_module`
  and a `PLAN_BASE_DIR` sandbox equivalent to the `plan_context` fixture) to settle two behavioural
  questions the existing suite does not cover — the resolve-thread-failure path and the
  resolution-only-change path. Both reproduced; outputs quoted below.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | "the consumer set is published with its size and derivation method" | Consumer set derived by literal-name grep + invoker trace; **size 0 in production**; retrospective refuted as a reader; GATE passes | Method and size published in `report-01.md` § D0. Re-running the grep reproduces the hit set exactly, and the "no production reader of `count_responded`" conclusion is correct. The claim "**sole** production invoker" is refutable: `automated-review-lifecycle.md` § Step 4.5 is a second documented invocation site, and its `threads_resolved: {N}` (line 157) is a respond-loop count with no documented source anywhere in the bundle | **met with a gap** (G4) |
| D1 | "a second round over unchanged dispositions transmits nothing, and a changed disposition still transmits, both proven by tests" | Marker imported, skip added, stamped in the same unit of work; `resolve_finding` clears on change | Present and correct at `github_pr.py:1549,1606-1607,1662,1679` and `_findings_core.py:476-481,529-533`. Both tests exist and pass. **Not** met on one branch: reply-sent-then-resolve-failed leaves no marker, so the reply is re-sent next round (probe-confirmed) | **met on the happy path, gap on the failure path** (G1) |
| D2 | "every consumer D0 found reads a field whose name matches its content, and the migration (or the decision not to migrate) is stated per consumer" | `count_responded` narrowed to this round's transmits; already-satisfied land in `skipped[]`; no consumer to migrate | `github_pr.py:1693` counts `len(responded)`, which now excludes marker-skipped findings. Per-consumer statement given in the D0 table for the three rows it found. The invocation site D0 missed (G4) was therefore not stated | **met for the derived set** |
| D3 | "(a) 4+3 transmits 3 and reports 3; (b) a changed disposition re-transmits; (c) the consumer population is non-empty-asserted first and every member covered; each proven discriminating by mutation" | Three tests + four more in the follow-up commit, RED values 7 / 1 / 6 | All seven named tests exist and pass (see § Report-claim audit). (a) and (b) are genuinely discriminating. (c)'s "derived population" is a hard-coded two-key literal, so the non-empty assert cannot fail | **(a)(b) met; (c) met in letter, weak in substance** (G10) |

### D0 — consumer derivation

The derivation method is published (`report-01.md` § D0: "grep the whole repository tree (excluding
`doc/plans/`) for the literal field name `count_responded`; then trace (a) the sole production invoker …
and (b) the plan-named suspect"). Re-running that grep on the current tree returns exactly three
producers (`github_pr.py:1693`, `gitlab_pr.py:441`, `sonar.py:774`), the doc mentions, and test
assertions — no production reader. **The retrospective refutation is correct and load-bearing:**
`.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py` computes
`pct_resolved_as_fixed` from `actionable_fixed_count / resolved_actionable_count`, both derived from
each record's `resolution` field (docstring lines 39–47, comment 69–80, accumulation loop 279–310).
`count_responded` appears nowhere in that file. The plan's premise that the retrospective's %-resolved
figures "are computed from this family of counts" is genuinely refuted.

What the method cannot reach is a caller that renames the value.
`workflow-pr-doctor/standards/automated-review-lifecycle.md` § Step 4.5 (prose at line 135, invocation
block at 137–140) invokes `post_responses` — a second production invocation site, contradicting "sole".
Its § Step 5 return summary emits `threads_resolved: {N}` (line 157) with no documented source anywhere
in the bundle: `grep -rn "threads_resolved" marketplace/ test/ .claude/` returns that one line and
nothing else, so nothing in the tree computes it. An agent executing that document must fill it from
something, and the respond return is the only candidate to hand — but that is an inference about agent
behaviour, not a derivation, and `count_responded` would in fact be the *wrong* field to fill it from
(a batched disposition is counted in `count_responded` while resolving no thread). What is established
is narrower than "a second consumer of the count": the enumeration missed an invocation site, and a
documented output field of that site has no derivation. The behavioural impact is nil — no code reads
`count_responded` — but the GATE deliverable's one job was the enumeration.

The *invocation-site* enumeration is now complete and was derived, not hand-listed:
`grep -rn "post_responses --pr-number\|github_pr \\\\" marketplace/bundles/ --include=*.md` separates
executable invocation blocks from prose references. Outside `workflow-integration-github/SKILL.md`'s own
canonical-invocation catalogue (`:62`, `:154`, `:666`) there are exactly two executable `github_pr
post_responses` blocks in the bundle — `verification-feedback.md:246` and
`automated-review-lifecycle.md:138`. The other nine documents that mention `post_responses` reference
the RESPOND loop without invoking it.

### D1 — idempotent transmission

The Sonar reference pattern was copied faithfully:

- `github_pr.py:1549` — `from _findings_core import mark_finding_responded, query_findings`
- `github_pr.py:1606-1607` — `if finding.get('responded'): skipped.append({'hash_id': hash_id, 'reason': 'already responded'})`
- `github_pr.py:1662` — stamp after a successful thread-reply **and** resolve-thread
- `github_pr.py:1679` — stamp per batch member after the batched post reports `success`

The "key, not suppression" half is in `_findings_core.py:476-481`:

```python
if parent.get('responded'):
    resolution_changed = parent.get('resolution') != resolution
    detail_changed = bool(detail) and parent.get('resolution_detail') != detail
    if resolution_changed or detail_changed:
        updates['responded'] = False
        updates['responded_at'] = None
```

This is correct for the cases it covers, and it does keep one cross-provider vocabulary. The bulk
mirror at `_findings_core.py:529-533` is correct too, and the report's characterisation of it as
"latent, not reachable by any current caller" is accurate: the only caller is
`script-shared/scripts/build/_build_shared.py:470`, which passes build finding types
(`BUILD_FINDING_TYPES` minus/plus `test-failure`) — never `pr-comment`.

**The failure path is not covered.** At `github_pr.py:1648-1651` the thread reply is posted first (line
1644); if the subsequent resolve-thread mutation fails the finding lands in `untransmitted` and
`continue`s *before* line 1662's stamp. The reply was genuinely sent. Probe (scratchpad, real store,
real module, `run_graphql` stubbed to succeed on `THREAD_REPLY_MUTATION` and fail on
`RESOLVE_THREAD_MUTATION`):

```text
ROUND1: {'status': 'partial', 'count_responded': 0, 'count_skipped': 0, 'count_untransmitted': 1}
MARKER AFTER ROUND 1: None
ROUND2: {'status': 'partial', 'count_responded': 0, 'count_skipped': 0, 'count_untransmitted': 1}
ROUND2 skipped: []
THREAD REPLIES TOTAL: 2
```

The code comment at `github_pr.py:1595-1605` asserts the opposite reading — "a crash between send and
mark leaves the finding eligible for a safe retry rather than silently dropped" (lines 1603–1605). For a
*reply-then-resolve* verb the retry is not safe: it re-posts the reply. The same shape was copied into
`gitlab_pr.py:425-429` by the follow-up plan. `workflow-integration-github/SKILL.md:141` independently
documents that this state occurs ("a thread-bearing disposition whose resolve-thread failed leaves an
unresolved reply carrying arbitrary `resolution_detail` text"), so it is not hypothetical.

The same branch also mis-signals in the direction this plan cared most about. The finding lands in
`untransmitted[]` with reason `resolve-thread failed: …` and drives `count_untransmitted` — a count
naming a disposition that *was* transmitted. It is the mirror of the defect the plan was written to fix
(`count_responded` over-counting): here the count under-counts, and a consumer reading
`count_untransmitted` as "replies that never reached the reviewer" is wrong.

### D2 — the count reports what it names

`count_responded` at `github_pr.py:1693` is `len(responded)`, and marker-skipped findings never reach
`responded`, so the name now matches the content. The decision not to add a sibling field is stated
and justified by D0's empty derived set, and already-satisfied findings are distinguished by
`skipped[].reason == 'already responded'` — the same vocabulary Sonar uses (`sonar.py:749`). The
per-consumer migration statement covers the three rows D0 found; the fourth site (G4) is unstated
because it was not found.

One vocabulary inconsistency: every other `skipped[].reason` in this verb is a snake_case token
(`no_resolution_detail` at `:1612`, `pr_number_unrecorded` / `belongs_to_pr_<n>` at `:1591`), while the
new one is the space-separated phrase `already responded`. Copied from Sonar, so cross-provider
consistent and intra-provider inconsistent. (The prose reasons in `untransmitted[]` are a different
field and are not part of this vocabulary.)

### D3 — tests

All seven tests the report names exist in the current tree and pass:

| Test | File:line | Runs |
|---|---|---|
| `test_post_responses_second_round_transmits_only_newly_resolved_dispositions` | `test/plan-marshall/workflow-integration-github/test_github_pr.py:1608` | pass |
| `test_post_responses_retransmits_a_changed_disposition` | `…/test_github_pr.py:1656` | pass |
| `test_post_responses_count_responded_names_this_rounds_transmits` | `…/test_github_pr.py:1691` | pass |
| `test_post_responses_thread_reply_path_is_idempotent_across_rounds` | `…/test_github_pr.py:1736` | pass |
| `test_resolve_finding_clears_responded_marker_on_changed_disposition` | `test/plan-marshall/manage-findings/test_findings_store.py:623` | pass |
| `test_resolve_finding_keeps_responded_marker_on_unchanged_reresolve` | `…/test_findings_store.py:638` | pass |
| `test_resolve_findings_by_type_clears_responded_marker_on_change` | `…/test_findings_store.py:658` | pass |

Discrimination is confirmed by construction rather than re-run mutation (the pre-fix tree is not
checked out): removing the `github_pr.py:1606` guard makes round 2 re-select all seven terminal
findings, so `assert second['count_responded'] == 3` fails with 7; removing the `_findings_core.py:479`
clear makes `assert changed['count_responded'] == 1` fail with 0. The report's stated RED values
(7 / 1 / 6) are each arithmetically consistent with the staged fixtures (4+3, 1, 5+1).

D3(a) is strong — it asserts the count, the hash-id sets on both sides, and that the round-2 batched
body contains no round-1 `comment_id`. D3(b) is strong. D3(c) is the weak one: its "derivation" is

```python
responded_family = {key: value for key, value in result.items() if key in ('count_responded', 'responded')}
assert responded_family, 'the return must expose a responded-count family'
```

— a hard-coded literal key pair, not a population parsed from a substrate the way
`test/_shared/_dispatch_roster.py` parses roster rows out of a Markdown document. The non-empty guard
therefore cannot fail while the return keeps either key. (The test's *remaining* assertions are real:
it does prove the count and the `responded[]` membership name only this round's transmit.) The plan's
Verification section also demands "the consumer-population size published in the **test output**"; the
size is published in the report, not by any test.

The three `_findings_core` marker tests are discriminating, with one narrow blind spot: the
clear-on-change test (`test_findings_store.py:623`) changes the resolution **and** the detail in one
call, so neither disjunct of `resolution_changed or detail_changed` is exercised on its own.

## Report-claim audit

| # | Claim (`report-01.md`) | Verdict | Evidence |
|---|---|---|---|
| 1 | "There is **no prior-transmission term** in the predicate" (pre-fix) | ACCURATE | `git show c89bfc53 -- …/github_pr.py` shows the `if finding.get('responded')` block as an addition |
| 2 | "`responded` at `github_pr.py:1593` is a local output accumulator … not a persisted per-finding marker" | ACCURATE | `responded: list[dict[str, str]] = []` at `github_pr.py:1560`, returned as `responded` at `:1696` |
| 3 | "Consumer derivation — method: grep the whole repository tree … for the literal field name" | ACCURATE as a description of what was done | Re-running it reproduces the report's hit table exactly |
| 4 | "`verification-feedback.md` Step 8 (**sole** production invoker)" | **REFUTED as to "sole"** | `automated-review-lifecycle.md:137-140` is a second executable invocation of `github_pr post_responses`; the derived invocation-site set is exactly two (see § D0) |
| 5 | "`finalize-step-review-retrospective` … **No** — different data path (the finding `resolution` family, not the post_responses return)" | ACCURATE | `review_retrospective.py:39-47,69-80,279-310`; `count_responded` absent from the file |
| 6 | "**Production readers of the field: none.**" | ACCURATE for the literal field | No code anywhere reads `count_responded`. `automated-review-lifecycle.md:157`'s `threads_resolved` is an undocumented-source field at a missed invocation site, which is an enumeration defect and a doc gap — not a demonstrated reader of this field |
| 7 | "**Producers (3):** `github_pr.py:1590`, `gitlab_pr.py:410`, `sonar.py:774`" | ACCURATE (line numbers have since drifted to 1693 / 441 / 774) | Repository-wide grep finds exactly three producers |
| 8 | "the same … shape exists in `gitlab_pr.py` … **Population = {github (fixed here), gitlab (same defect, NOT fixed), sonar (reference)}**" | ACCURATE at the time | `b19ef4a6` (PR #1191) subsequently fixed GitLab |
| 9 | "call `mark_finding_responded(plan_id, hash_id)` in the **same unit of work** that transmits — right after a successful thread-reply+resolve, and for the batch after the batch post succeeds" | ACCURATE as a description of the code; the phrase "same unit of work" overstates atomicity (two separate JSONL writes) | `github_pr.py:1662`, `:1679` |
| 10 | "`resolve_finding` clears `responded`/`responded_at` **when (and only when) the resolution or a supplied detail differs from what is stored**" | ACCURATE | `_findings_core.py:476-481` |
| 11 | "gives Sonar the same changed-disposition correctness for free without touching `sonar.py`" | ACCURATE but **untested** | `sonar.py` is absent from the commit's file list; no Sonar test exercises a changed disposition (`grep -rn "responded" test/plan-marshall/workflow-integration-sonar/*.py` → marker-persist `:409`, rerun-skip `:429`, failed-post `:458` only) |
| 12 | "After D1, `count_responded` counts only dispositions transmitted **this round**" | ACCURATE | `github_pr.py:1693` |
| 13 | "Three tests added … each verified RED against the unfixed code, then GREEN after the fix" | ACCURATE (existence and pass confirmed; RED values consistent by construction, not re-run) | Table above |
| 14 | "Commit `b0ac64d` … added four more tests" | ACCURATE as to the tests | All four exist and pass. The SHAs `4b4fb58` / `b0ac64d` are not objects in this repository (`git cat-file -t` → "Not a valid object name") — expected after a squash merge, so UNVERIFIABLE, not false |
| 15 | Finding 4: bulk clear is "latent, not reachable by any current caller" | ACCURATE | Only caller is `_build_shared.py:470` with build finding types |
| 16 | Finding 6: "Cold read of the corrected prose answers … correctly" | **OVERSTATED** | The cold read passed on the paragraph it was pointed at (`verification-feedback.md:265`) while `verification-feedback.md:243`, in the same document, still asserts "Only a finding with no `resolution_detail` is skipped" |
| 17 | "D3(c) adapts `_dispatch_roster.py`'s 'derive → assert non-empty → cover each' discipline" | **OVERSTATED**, though honestly hedged by "adapts" | `_dispatch_roster.py:25-63` parses a population out of document text and raises when the heading is absent (`:47`); the test hard-codes a two-key literal |
| 18 | Build gate: `./pw verify` green, 19238 passed | UNVERIFIABLE here (full build not run per instruction); the targeted slices pass | 14 + 3 passing tests re-run |
| 19 | Residue: "GitLab … carries the identical re-transmission defect and was left unfixed" | ACCURATE at the time, now CLOSED | `b19ef4a6` |
| 20 | Contract check row "4 Implement — Deliverables addressed" | ACCURATE but incomplete as a record | The report's Deliverables section never states the `workflow-integration-github/SKILL.md` edit the commit made (3 added lines); it surfaces only obliquely in § Build gate ("lints the edited `SKILL.md`") |

## Correctness review

**C1 — a sent reply is re-sent when resolve-thread fails, and is counted as untransmitted (CONFIRMED,
major).** `github_pr.py:1644-1651`. The thread reply is transmitted at line 1644; a non-zero `rc2` from
`RESOLVE_THREAD_MUTATION` at 1649 routes to `untransmitted` and `continue`s, skipping the stamp at
1662. The finding re-qualifies on the next pass and the identical reply is posted to the reviewer's
thread a second time. Probe output above: two `THREAD_REPLY_MUTATION` calls across two rounds, empty
`skipped`. `gitlab_pr.py:425-429` carries the same shape. This is the plan's own defect #1 surviving in
a narrower branch, and the in-code comment at `github_pr.py:1595-1605` describes the retry as "safe",
which for a two-step reply-then-resolve verb it is not. The same branch also drives
`count_untransmitted` over a disposition that reached the reviewer — the plan's defect #2 with the sign
flipped.

**C2 — a resolution-only change re-sends a byte-identical reply (CONFIRMED, minor).**
`_findings_core.py:479-481` clears the marker when `resolution_changed` alone is true, but `updates`
only carries `resolution_detail` when a `detail` argument was supplied (`_findings_core.py:463-464`).
So a `resolve` that changes `accepted` → `rejected` without a new `--detail` clears the marker while
leaving the old reply body in place. Probe output:

```text
after change -> responded: False | detail: 'Accepted: original words.' | resolution: rejected
round2 count_responded: 1
round2 body identical to round1: True
```

The reviewer receives the same words twice. The documented triage flow always supplies `--detail`
(`automated-review-lifecycle.md:131`, and every `resolve` block in `triage.md` — `:203`, `:211`,
`:228`, `:240`, `:258`), so this needs a caller who omits it — the CLI
makes `--detail` optional (`manage-findings/SKILL.md:325-327`).

**C3 — the stamp is not atomic with the send (CONFIRMED, minor, disclosed).**
`mark_finding_responded` is a separate JSONL rewrite after the transmit. For the batched path
(`github_pr.py:1664-1679`) the loop stamps N findings one at a time after a single post, so an
interruption mid-loop leaves a partially-marked batch whose unmarked members re-post in a fresh batch.
The docstring's "same unit of work" (`github_pr.py:1536-1538`) is a description of ordering, not of
atomicity. No store-level transaction primitive exists to fix this, so it is recorded as a
documented-limitation item and is deliberately **not** carried into `gaps.md` as actionable work.

**C4 — `mark_finding_responded`'s return value is discarded (CONFIRMED, minor, latent).**
`github_pr.py:1662,1679`, `gitlab_pr.py:433`, `sonar.py:764` all ignore the `{'status': 'error', …}`
branch of `_findings_core.py:573-575`. A failed marker write is silent and produces a re-send next
round. `update_jsonl_in_dir` returns False only when no file under the findings directory holds the
hash (`jsonl_store.py:110-123`), and the hash came from `query_findings` on the same plan, so the
branch is unreachable under single-process use — latent, not live (G12).

**C5 — the bound named as the backstop for C1 cannot see C1 (CONFIRMED, minor).**
`workflow-integration-github/SKILL.md:141` concedes that the self-response filter "cannot be complete"
for exactly the C1 shape — "a thread-bearing disposition whose resolve-thread failed leaves an
unresolved reply carrying arbitrary `resolution_detail` text and no transmission shape at all" — and
asserts "so a bound backs it". The bound's predicate is
`current_cycle_self_response >= _SELF_RESPONSE_LOOP_BOUND` (`github_pr.py:1224-1225`), counted by
`_current_cycle_self_response_count` → `_is_self_authored_response`, which is
`body.lstrip().startswith(_SELF_RESPONSE_HEADING)` (`:393`) with
`_SELF_RESPONSE_HEADING = '## Triage dispositions'` (`:347`). That heading is written only by
`_build_batched_response_body` (`:1473`); a thread reply posts the bare `resolution_detail`
(`:1644`). A repeated thread reply therefore never increments the counter and the bound never fires on
it (G13).

**Checked and found correct:** the `parent.get('responded')` outer guard cannot mask a needed clear
(an unmarked finding has nothing to clear); `bool(detail)` correctly treats an omitted/empty detail as
"no detail supplied", matching the `if detail:` write guard immediately above; `resolution_changed =
to_resolution != from_resolution` in the bulk path is sound because every matched record carries
`from_resolution` by construction (`_findings_core.py:511-515`); the skip is correctly placed after the
`pr_number` gate and before the `resolution_detail` check, matching the SKILL.md table order; the local
`responded` accumulator does not shadow the record field; `add_finding` generates a fresh random
`hash_id` per call (`_findings_core.py:261` → `jsonl_store.generate_hash_id`, `secrets.token_hex`) and
`cmd_fetch_findings` dedups on `(bot_kind, comment_id)` (`github_pr.py:1095-1102`), so a re-fetch
cannot resurrect an already-answered comment as a new unmarked row; and **no mutation path other than
the two `resolve` entry points can change a finding's reply body** — the complete set of record writers
is `resolve_finding`, `resolve_findings_by_type`, `promote_finding`, `mark_finding_responded`, the
Q-Gate resolvers (a different store), and `_findings_ingest.ingest_findings`, and the last is scoped to
`resolution='pending'` records (`_findings_ingest.py:95`), which an already-transmitted terminal finding
is not.

## Completeness review

**Sites.** Both transmit branches (thread-reply and batched) stamp the marker, and both are covered by
tests. The third respond provider, Sonar, already had the pattern. GitLab was correctly named as
out of scope and closed by a follow-up.

**Doc restatements of the pre-fix claim that survive.**

1. `verification-feedback.md:243` — "**Only a finding with no `resolution_detail` is skipped** — there is
   genuinely nothing to transmit". False on three counts now: `already responded`, `belongs_to_pr_<n>`
   and `pr_number_unrecorded` all skip. It sits twenty-two lines above the corrected paragraph at line
   265 in the same document, which is exactly the contradiction the plan's cold-read demand existed to
   catch.
2. `workflow-pr-doctor/standards/automated-review-lifecycle.md:135` — "findings without a `thread_id` or
   `resolution_detail` are skipped, never guessed at". Silent on the marker, and independently stale on
   `thread_id` (a thread-bearing finding with no `thread_id` is `untransmitted`, not skipped —
   `github_pr.py:1630-1640`).
3. `workflow-integration-sonar/SKILL.md:148` — "It is idempotent — … so re-invoking the verb never
   re-POSTs the same dismissal". Now incomplete: after this plan a re-decided dismissal *does* re-POST.
   Sonar's behaviour changed without its documentation changing. The same over-claim is restated in
   `sonar.py`'s own inline comment at `:745-747` ("Skip it so a re-run of `post_responses` never
   re-POSTs the same dismissal"), and `sonar.cmd_post_responses`'s docstring (`:705-716`) documents no
   idempotency contract at all — unlike the GitHub and GitLab verbs, which each carry a full
   "Idempotent across rounds" paragraph.
4. `_findings_core.py:475` — the new comment enumerates "every provider that reads the marker (GitHub,
   Sonar)". GitLab reads it too since `b19ef4a6`.

**The owning skill does not document the field or the new side effect.**
`grep -rn "responded" marketplace/bundles/plan-marshall/skills/manage-findings/` returns hits in `.py`
only — zero in `SKILL.md` or `standards/jsonl-format.md`. `jsonl-format.md` § Plan Finding Record
carries Required and Optional field tables (`:72-80` and `:84-94`) listing `promoted` / `promoted_to`
in the record example (`:51-68`) but neither `responded` nor `responded_at`, and
`manage-findings/SKILL.md` § resolve (`:322-329`) documents the verb with no mention that it now clears
a provider-transmission marker. The field is persisted into `pr-comment.jsonl` and read by three
provider scripts; its lifecycle is documented only inside those providers' own SKILL.md files.

**Missing tests.**

- No GitHub analogue of `test_failed_post_does_not_mark_responded`
  (`test/plan-marshall/workflow-integration-sonar/test_fetch_findings.py:458`) — nothing asserts that a
  failed batch post or a failed thread reply leaves the marker unset. `grep -n "^def test_post_responses"`
  lists 14 tests; neither failure-path test (`…_batch_post_failure_untransmits_whole_batch:1502`,
  `…_thread_reply_failure_is_untransmitted:1579`) inspects the stored marker. C1 lives in exactly that
  untested region.
- No Sonar test for the changed-disposition re-transmit the report claims Sonar gained "for free".
- No test for C2 (resolution-only change), and no test that isolates either disjunct of the
  clear-on-change condition.

**Consumers.** One documented invocation site beyond the derived set: `automated-review-lifecycle.md`
§ Step 4.5 / Step 5 (see D0 above). The invocation-site enumeration is now complete.

## Out-of-scope compliance

The landing touched no declared out-of-scope surface.

- *Measuring rate-limit consumption* — not attempted. Compliant.
- *Deriving a rate from prior sightings* — not attempted. Compliant.
- *Re-litigating the missing key* — confirmed once in D0 and dropped. Compliant.
- *Auditing every external-transmit verb across all providers* — the report names a population under
  the heading "Cross-provider sweep (the out-of-scope population, named)": `{github, gitlab, sonar}`.
  That is the population of `post_responses` implementations, not of "every external-transmit verb"
  (other verbs post to providers — for instance `_github.post_pr_comment` has callers outside
  `cmd_post_responses`). The plan's ⛔ was "Do both or state clearly which was skipped; do not let one
  stand in for the other." The narrower population is presented under the wider heading without saying
  the wider sweep was not done. Minor non-compliance, recorded but not raised as its own gap.
- `sonar.py` was declared read-only and was not modified — confirmed absent from the commit's file
  list. Its *behaviour* changed via the shared `resolve_finding`, which the report discloses.
- `_findings_core.py` was outside the plan's "Expected surface" but not out of scope; the report
  flagged the expansion explicitly (§ D1 "Surface note").

## Residue status

| Residue item (`report-01.md` § Residue) | Status |
|---|---|
| "GitLab (`gitlab_pr.py`) carries the identical re-transmission defect and was left unfixed … A follow-up plan should apply the same Sonar-pattern fix there." | **CLOSED** by `b19ef4a6` — "fix(review-apparatus): make gitlab_pr post_responses idempotent per (finding, disposition) (#1191)". `gitlab_pr.py:373,409-410,433` now carry the import, the skip and the stamp, and `verification-feedback.md:265` was updated from "GitHub and Sonar" to "Every respond verb — GitHub, GitLab, and Sonar". Note that the follow-up also copied C1 (`gitlab_pr.py:425-429`). |

## Summary

**Gaps by severity:** 3 major, 10 minor, 0 blockers — thirteen entries in `gaps.md`. No deliverable is
refuted and no named artifact is missing — every symbol, test and doc section the report claims exists
is in the tree and passing.

The fix is real and correctly built: the marker is imported, honoured and stamped on both transmit
branches; the clear-on-change half genuinely makes it a `(finding, disposition)` key rather than a
suppression; the count now names its content; and the plan's most valuable claim — that the
review-retrospective is not a reader of this count — is independently confirmed. What holds it back
from a clean verdict is that the plan's own defect survives on one branch (a reply is transmitted, the
resolve fails, no marker is written, the identical reply goes out again next round, and the round that
sent it reports the disposition as untransmitted — all reproduced), and that the corrected prose was
fixed in one paragraph while flat contradictions of it survive in both documents that invoke the verb,
one of them twenty-two lines earlier in the same file. All thirteen items are mechanical to close and
none requires re-deriving the plan's analysis.

## Adversarial review

This document and `gaps.md` were re-derived end to end by a second reviewer working from the clone with
no prior context. Nothing below was accepted because it was written down: every `path:line` citation was
opened, every count re-counted, and both behavioural claims re-run.

**Method.** `plan.md` and `report-01.md` read first, independently. Then every source cited above read
at the line ranges quoted. Counts re-derived: the `count_responded` grep (3 producers, 0 production
readers, doc + test hits only), `grep -n "^def test_post_responses"` (14), the seven named tests
(4 + 3, all present at the cited lines), the `already responded` literal (4 GitHub test sites,
2 GitLab, 1 Sonar, 3 provider scripts, 3 SKILL.md sites), the `threads_resolved` sweep over
`marketplace/ test/ .claude/` (1 hit), the `post_responses` executable-invocation-block sweep (2 sites
outside the owning skill), the `responded` `--include=*.md` sweep (11 hits, 6 about the marker), and the
complete record-mutation call-site set. Both test slices re-run: `-k post_responses` → 14 passed,
`-k responded` → 3 passed. Both probes re-implemented from scratch against the real modules with a
`PLAN_BASE_DIR` sandbox and re-run; outputs above are this reviewer's own, not the first reviewer's.
No repository file outside this directory and `gaps.md` was created or modified; `git status
--porcelain` confirms it.

**Outcome.** Upheld on re-derivation: C1 (probe reproduced), C2 (probe reproduced), C3, C4, the D0
retrospective refutation, the `_build_shared.py` sole-caller claim, the missing-test findings, the
D3(c) vacuous-guard finding, the four stale-doc sites, the `manage-findings` documentation omission, the
skip-reason vocabulary inconsistency, and the residue-closure record.

Overstated and now corrected: the claim that `automated-review-lifecycle.md`'s `threads_resolved` is a
*consumer of the count* — nothing in the tree computes that field, and `count_responded` would be the
wrong source for it, so the established finding is the missed invocation site plus an undocumented
output field, and its gap is minor rather than major; report-claim row 6 ("production readers: none")
is accurate for the literal field and is no longer marked overstated, while row 4 ("sole production
invoker") is refuted outright; and the headline "two stale prose restatements" undercounted the four
restatement sites the completeness review lists.

Refuted and removed: the claim (in the previous `gaps.md` G1) that a re-replying thread is "one of the
loops `_SELF_RESPONSE_LOOP_BOUND` exists to bound" — the bound counts only bodies start-anchored on
`'## Triage dispositions'`, which a thread reply never carries, so the bound cannot see this loop at
all. That refutation became a finding in its own right (C5 / G13), because
`workflow-integration-github/SKILL.md:141` asserts the bound backs precisely this hole.

Could not be verified from the clone: the report's `./pw verify` figures and the pre-fix RED runs (the
pre-fix tree is not checked out and the pre-squash SHAs `4b4fb58` / `b0ac64d` are not objects here), and
the PR's review-surface content. These stay UNVERIFIABLE, not refuted.

Added: two gaps (G12 — the discarded `mark_finding_responded` return, latent; G13 — the inert
self-response bound), the `count_untransmitted` mis-signal on the C1 branch (folded into C1 and G1,
which the first pass did not name), the `sonar.py:745-747` and `sonar.py:705-716` sites in the Sonar
documentation gap, the clear-on-change disjunct blind spot, the invocation-site completeness derivation
in § D0, and the record-mutation-path sweep in § Correctness review. Citations repaired: the in-code
comment range (`:1600-1604` → `:1595-1605`), the no-`thread_id` branch (`:1636-1642` → `:1630-1640`),
`_dispatch_roster.py` (`:26-63` → `:25-63`), the `jsonl-format.md` tables (`:70-79`/`:82-95` →
`:72-80`/`:84-94`), the record example (`:56-67` → `:51-68`), the review-retrospective loop
(`:279-282` → `:279-310`), the SKILL.md Workflow 2 step 4 range (`155-175` → `152-175`), and the
`triage.md` `--detail` reference (`:198`, which carries no `--detail`, → the actual resolve blocks at
`:203`, `:211`, `:228`, `:240`, `:258`). One count corrected: the
`workflow-integration-github/SKILL.md` transmit table has six rows, not four.

**Verdict unchanged:** verified-with-gaps.
