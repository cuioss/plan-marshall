# Background-build kill — forensic analysis (2026-07-15)

> **This is the epic's single evidence document.** All backward-looking material — the kill
> forensics, the falsified hypotheses, the upstream corroboration, and the setsid/daemonization
> experiment — lives here and only here. The goal-facing documents (`00-README.md`, `plans/*`)
> state conclusions and link back to the section that proves them.

## Verdict

**Candidate 1 — the harness/Bash-tool background primitive stops the job in-env. HIGH confidence.**

**Candidate 2 (sibling-agent over-broad reap) is FALSIFIED**, not merely weakened.

### The single most decisive piece of evidence

On **2026-07-12T14:18:31.218Z**, session `646410d9` had a background job killed at **72 seconds elapsed**. The command was:

```json
{"command":"sleep 300","description":"Pace merge-queue poll (5 min)","run_in_background":true}
```
> `646410d9-f0e6-4b85-ab8e-b424683aaa92.jsonl:2317`, launched `2026-07-12T14:17:18.867Z`, tool_use id `toolu_01412YTJMSPVx5QknaaKCvXX`, cwd `/Users/oliver/git/plan-marshall/.plan/local/worktrees/plan-15-architecture-data-sweep`, Claude Code `version: 2.1.207`

A bare **`sleep 300` was killed at 72s**. This single fact rules out, simultaneously:

- **the wrapper timeout** — `sleep` never enters `_build_execute.py`;
- **memory pressure / OOM / jetsam** — `sleep` holds ~0 RSS and 0% CPU, so no resource-based reaper would ever select it;
- **the documented pytest reap procedure** — `pgrep -afl pytest` cannot match `sleep 300`;
- **build-tool-specific causes** — there is no build involved at all.

And it did **not** die at 300s of its own accord: it was killed externally, at 72s, while doing nothing. It was killed **0.78 s** after a *different* session (`7349072b`) had its 770-s-elapsed `ci_complete_precondition` job killed. Whatever kills these jobs is indifferent to what the job is, what it costs, and how long it has run — and it reaches across sessions at the same instant. That is a supervisor of *background tasks*, i.e. the harness primitive.

### Supporting quantified result

| Notification status | n | Cross-session clusters (≤5 s) | Notifs inside a multi-session cluster | Rate |
|---|---|---|---|---|
| `killed` | 90 | 14 | 29 | **32.2 %** |
| `completed` | 1504 | 15 | 30 | **2.0 %** |

Kills are **16× more likely** than completions to be synchronized with a *different session's* event within 5 s, despite completions outnumbering kills 17:1. This rules out the "clustered notification delivery" artifact (if delivery ticks were shared, completions would cluster at the same rate — they do not). *Inference, but the 16× margin is large and the baseline is well-populated.*

---

## Method

### What I searched

1. **All 1 722 background-task notifications** across every `*.jsonl` under `/Users/oliver/.claude/projects/-Users-oliver-git-plan-marshall/` and `/Users/oliver/.claude/projects/-Users-oliver-git-TokenSheriff/` (top-level sessions **and** `subagents/` sub-directories), parsed with a JSON parser rather than regex-over-lines. Statuses: `completed` 1504, `?` 111, `killed` 90, `failed` 16, `stopped` 1.
2. **Every Bash tool_use** whose command matched `pkill|killall|kill -|kill %|kill <pid>|xargs kill`.
3. Paired each `killed` notification to its launching Bash call via `<tool-use-id>` → `tool_use.id` (exact join, not heuristic), yielding true elapsed-time-before-death.
4. macOS `pmset -g log` for sleep/wake/thermal transitions; `uptime`.
5. `/Users/oliver/git/plan-marshall/.plan/archived-plans/` and `/Users/oliver/git/plan-marshall/.plan/temp/dormated-plans/`.
6. `/Users/oliver/git/plan-marshall/.plan/local/logs/`.
7. Zero-length task-output files under `/private/tmp/claude-501/.../tasks/`.

### The 5 most recent top-level sessions (by mtime)

| mtime (epoch) | Size | File |
|---|---|---|
| 1784137964 | 1 966 677 | `c16a9bd8-2fbe-41ad-856a-1faa68b7a9fe.jsonl` (this forensics session) |
| 1784137922 | 3 193 126 | `25326d05-5fde-4bde-bb4c-bb4852c08104.jsonl` (`upgrade-regen-safety`) |
| 1784135689 | 4 240 046 | `ced3ef27-b593-4ee0-92d7-a90a3461ecb7.jsonl` (`ext-point-verify-consumers`) |
| 1784134729 | 2 827 708 | `d0365a0b-f4ae-467a-ad2c-b7811a3e0c64.jsonl` (`hardening-sweep`) |
| 1784119897 | 3 306 606 | `da02f32e-ac36-4b10-b407-10a4bf95380a.jsonl` |

I deliberately widened beyond these 5 — the decisive evidence (the `sleep 300` case, the 3-session cluster) lies in older sessions, and restricting to 5 would have missed it. Cross-repo evidence comes from `-Users-oliver-git-TokenSheriff/353f910e-8a5b-4744-b2ae-b35eac20a5fe.jsonl`.

### What I could NOT access

- **`log show` returns empty output for every query, including `--last 5m` with no predicate.** The unified log is unreachable from this sandbox. **The OOM/jetsam hypothesis therefore could not be tested directly via system logs** — it is refuted on the `sleep 300` logic above, not by log absence. NOT FOUND ≠ tested.
- **Per-process memory/RSS history** — unavailable retrospectively; no sampling was running.
- **The killing signal number** (SIGTERM vs SIGKILL) — the harness reports only `<status>killed</status>`; the signal is not recorded anywhere I can reach.
- **The killer's identity** — no audit trail attributes the kill to a PID or process. See Open Questions.

---

## Timeline (the correlation table)

### 14 cross-session synchronized kill clusters (span ≤ 5 s, ≥2 distinct sessions)

| Cluster start (UTC) | n | Span | Sessions | Elapsed-at-death per job |
|---|---|---|---|---|
| 2026-06-29T12:01:55.421Z | 2 | 0.97 s | `fc5e46b9`, `7f5464ea` | 213 s / **827 s** |
| 2026-06-29T12:31:55.974Z | 2 | 0.16 s | `7f5464ea`, `eb52a7c2` | 545 s / ? |
| 2026-06-29T13:38:09.016Z | 2 | 1.47 s | `7f5464ea`, `a4dd9f29` | 211 s / 616 s |
| 2026-06-29T13:39:29.424Z | 2 | 1.11 s | `7f5464ea`, `a4dd9f29` | 46 s / 51 s |
| 2026-07-08T05:57:39.180Z | 2 | 0.52 s | `b9c901fd`, `b6b1ee37` | 120 s / 581 s |
| 2026-07-10T17:32:38.817Z | 2 | 0.14 s | `be858d1b`, `4360c138` | 282 s / 32 s |
| 2026-07-10T19:16:37.191Z | 2 | 0.97 s | `a7408d23`, `16788809` | 341 s / 286 s |
| 2026-07-10T19:20:04.209Z | 2 | 0.34 s | `a7408d23`, `16788809` | 171 s / 148 s |
| **2026-07-12T14:18:31.218Z** | 2 | 0.78 s | `646410d9`, `7349072b` | **72 s (`sleep 300`)** / 770 s |
| 2026-07-13T09:37:35.526Z | 2 | 0.19 s | `f67aeaaa`, `2ae4c25a` | 450 s / 123 s |
| **2026-07-13T16:07:09.479Z** | **3** | 1.53 s | `7de9d95c`, `f409d6b9`, `a1727ef5` | 468 s / 327 s / 688 s |
| 2026-07-13T17:43:19.635Z | 2 | 0.89 s | `7de9d95c`, `a1727ef5` | 521 s / 441 s |
| 2026-07-13T17:45:34.105Z | 2 | 1.47 s | `7de9d95c`, `a1727ef5` | 98 s / 114 s |
| **2026-07-15T15:14:21.735Z** | 2 | 0.29 s | `d0365a0b`, `25326d05` | **615 s / 173 s** |

Within every cluster the elapsed times **differ wildly** (827 s beside 213 s; 770 s beside 72 s). The synchronizing variable is **wall-clock instant**, never job age. *This is the structural signature of an external, indiscriminate stop — not of any per-job property.*

### The observed incident, reconstructed (2026-07-15)

| UTC | Session | Event |
|---|---|---|
| 14:54:56.104 | `ced3ef27` | BG launch: `pyproject_build run --command-args "coverage"` |
| 14:56:51.805 | `ced3ef27` | **`<status>killed</status>` — "Run whole-tree coverage detached (orchestrator-tier)" was stopped** (elapsed **115 s**) |
| 14:58:14.505 | `ced3ef27` | BG relaunch: `coverage` |
| 15:04:06.929 | `d0365a0b` | BG launch: `module-tests` (whole-tree) |
| 15:11:28.919 | `25326d05` | BG launch: `module-tests` (whole-tree, re-run) |
| **15:14:21.191** | `d0365a0b` | `queue-operation/enqueue` carrying the kill notification |
| **15:14:21.735** | `d0365a0b` | **killed** — elapsed **615 s** |
| **15:14:22.025** | `25326d05` | **killed** — elapsed **173 s** |
| 15:14:35.525 | `d0365a0b` | `Read` of task output → *"Warning: the file exists but the contents are empty."* |
| 15:14:54.491 | `d0365a0b` | BG relaunch: `module-tests` |
| 15:15:11.557 | `ced3ef27` | **`completed`** — `status: success, exit_code: 0, duration_seconds: 1014` |
| 15:15:24.624 | `25326d05` | BG relaunch: `module-tests` |
| 15:17:46.173 | `25326d05` | **killed** — elapsed **142 s** |
| 15:29:26.991 | `25326d05` | Operator answers `AskUserQuestion`: *"Run in foreground, but use the correct command (the build wrapper)"* |
| 16:01:21.582 | `d0365a0b` | BG launch: `coverage` |
| 16:03:26.086 | `d0365a0b` | **killed** — elapsed **125 s** |
| 16:53:11.432 | `ced3ef27` | **killed** — "Wait for post-merge CI" (elapsed **109 s**) |
| 17:42:39.373 | `353f910e` **(TokenSheriff)** | BG launch: `build-maven:maven run --command-args "verify"` |
| 17:44:40.709 | `353f910e` | **killed** — elapsed **121 s** |
| 17:45:06.838 | `353f910e` | BG relaunch: `maven run --command-args "verify"` |
| 17:49:12.934 | `353f910e` | **killed** — elapsed **246 s** |

**The critical control in this window:** `ced3ef27`'s `coverage` job ran **from 14:58:14 straight through the 15:14:21 kill instant** and completed normally at 15:15:11 with **`duration_seconds: 1014`**. Three whole-tree builds were in flight at 15:14:21; two died, one survived — and the survivor was **the oldest and longest-running of the three**.

> **This falsifies "long-running background jobs cannot survive."** A 1014-s background build survived, in the same repo, on the same machine, in the same minute that a 173-s sibling was killed. Duration is not the discriminator. *(Contradicts the coordinator's framing — see Contradictions.)*

### Elapsed-time-before-death distribution (n = 86 paired kills)

**11 s, 32 s, 40 s, 46 s, 49 s, 51 s, 55 s, 59 s, 64 s, 72 s, 76 s, 89 s, 92 s, 98 s, 99 s, 109 s, 113 s, 115 s, 120 s, 121 s, 123 s, 125 s, 142 s, 148 s, 171 s, 173 s, 174 s, 176 s, 182 s, 211 s, 213 s, 246 s, 266 s, 282 s, 286 s, 327 s, 341 s, 353 s, 357 s, 369 s, 441 s, 450 s, 468 s, 485 s, 520 s, 541 s, 545 s, 581 s, 615 s, 616 s, 653 s, 670 s, 670 s, 688 s, 689 s, 711 s, 770 s, 827 s …**

Range **11 s → 827 s**, no mode, no ceiling. The 11-s kill (`458ae45a`, 2026-07-14T09:30:01.481Z, "Re-run module-tests plan-marshall (orchestrator-tier)", launched 09:29:50) is on its own sufficient to exclude every duration-based mechanism.

> **Confirms the established finding and answers evidence-item 5 explicitly: NO killed job died at or near 1021 s.** The maximum observed is 827 s, comfortably under the 817 × 1.25 = 1021 s effective ceiling; the two 2026-07-15 `module-tests` kills died at 615 s and 173 s. **The wrapper timeout is fully exonerated.** No contradiction with the established findings on this point.

---

## Evidence for Candidate 1

1. **`sleep 300` killed at 72 s** — `646410d9-f0e6-4b85-ab8e-b424683aaa92.jsonl:2317`, killed `2026-07-12T14:18:31.218Z`. Only a background-task supervisor can stop a job with no resource footprint, no build, and no matching process name. *Decisive.*
2. **Synchronized multi-session kills, 14 clusters, up to 3 sessions in 1.53 s** (2026-07-13T16:07:09–11, sessions `7de9d95c` / `f409d6b9` / `a1727ef5`, elapsed 468 s / 327 s / 688 s). No in-repo mechanism and no transcript command can produce this.
3. **Statistical discrimination**: kills cluster cross-session at **32.2 %** vs completions at **2.0 %** (16×). Excludes the notification-delivery-artifact explanation.
4. **Cross-repo, cross-toolchain invariance**: the identical `<status>killed</status>` + zero-byte-output signature appears for
   - `pyproject_build` / pytest (plan-marshall),
   - `build-maven:maven run --command-args "verify"` (TokenSheriff, `353f910e-…jsonl`, 17:44:40 and 17:49:12),
   - `ci_complete_precondition resolve` and `tools-integration-ci:ci checks wait` (network waits, no build),
   - `gh run watch` (TokenSheriff, 2026-07-14T07:39:35.005Z),
   - `sleep 300` (no-op).
   The **only** invariant across all five is `run_in_background: true`.
5. **Zero output, structurally**: killed jobs' output files are **0 bytes** — `buuvmm0e9.output` (0 B), `bljspd15x.output` (0 B), `bhcpfxv7x.output` (0 B), `b4mwuf2zn.output` (0 B), `b6va4tcwi.output` (0 B). Sessions read them and got *"Warning: the file exists but the contents are empty."* (`25326d05:1068`, `d0365a0b:995`). Consistent with the wrapper being killed before its first flush; `except TimeoutExpired` never ran, so no diagnostic was written.
6. **Independent precedent**, consistent: the #868 background ci-wait was "repeatedly KILLED in-env" (given).
7. **The `queue-operation` events preceding each kill are notification *delivery*, not cause** — verified by dumping the raw records: `{"type":"queue-operation","operation":"enqueue",...,"content":"<task-notification>…<status>killed</status>…"}` (`d0365a0b:983`) followed by `{"operation":"dequeue"}` (`d0365a0b:984`). They carry the already-decided kill. **NOT a trigger.**

## Evidence for Candidate 2

**NOT FOUND. There is none.**

Exhaustively:

- **Zero `kill` / `pkill` / `killall` / `xargs kill` Bash calls exist anywhere in the 2026-07-13 → 2026-07-16 incident window**, in either repo, in top-level sessions or subagent transcripts. Every regex hit in that window is a *search for* kill-related code, not a kill:
  - `agent-a94f7118951d9e406.jsonl:5,9,14,22,31,34,37` (2026-07-15T17:18:22–17:18:59Z) — the prior forensic agent running `grep`/`rg` for `psutil|SIGKILL|SIGTERM|killpg|pkill`;
  - `agent-ababc46092128594d.jsonl:19,20` (2026-07-15T17:52:53Z) — **my own** search commands in this investigation.
- **Widened per the coordinator's instruction** to `maven`, `mvn`, `java`, `gradle`, `node`: **NOT FOUND** — no kill command targeting any of these exists in any transcript, in any window.
- **Broad-pattern kills exist only far outside the incident window** and none coincide with any kill cluster. The corpus-wide inventory of actually-executed kills is: `pkill -f "…"` ×6, `pkill -9 -f "…"` ×1, `pkill -f bx3rhvltn` ×1, `kill %1` ×11, and explicit PID lists (`kill 87614 87663 87664`, `kill 48833 48846 53908 …`, `kill -9 77946 77955 84018`, `kill -9 74526 74533 74535 77301`, `kill 72315`, `kill 37896 37899`, `kill 23685 26464`). **None falls within seconds before any of the 90 kills.**
- **The mechanism is unavailable in 67 % of cases**: at the moment of death, **58 of 86** paired kills (67 %) had **zero** other sessions with any background job in flight. A sibling reap requires a sibling doing something to reap; two-thirds of these kills happened with no sibling activity at all.
- **A pytest-scoped reap cannot kill a Maven/JVM build in a different repository** — yet TokenSheriff's `maven verify` was killed twice (17:44:40, 17:49:12) with the identical signature. Confirms the coordinator's reasoning.
- **A pytest-scoped reap cannot kill `sleep 300`** — yet it was killed at 72 s.

## Evidence AGAINST each

### Against Candidate 1

- **Weak/none.** The only friction is that the *mechanism* inside the harness is unidentified — I have established the signature and excluded the alternatives, but I cannot name the code path or the signal, because the harness is outside this repo and `log show` is unreachable. This makes Candidate 1 an **inference to the best explanation from exclusion**, not a directly-observed cause. It is not a positive observation of the harness killing a job.
- The survivor case (`ced3ef27`, 1014 s) shows the harness does **not** stop all background jobs, so any account must explain **selectivity** — see Open Questions.

### Against Candidate 2

- Falsified on four independent grounds, any one of which is sufficient: (1) no kill commands exist in the window; (2) `sleep 300` and Maven are unreachable by the `pgrep -afl pytest` procedure; (3) 67 % of kills occur with no sibling background activity; (4) no repo code can kill 3 sessions in 1.53 s — the established finding that `os.kill`/`SIGTERM`/`SIGKILL`/`psutil`/`pkill`/`killpg` have **zero executable matches** in the repo is independently corroborated by `agent-a94f7118951d9e406.jsonl:32,38`, whose only hits were **docstring prose** in `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/build_queue.py:28,226` (describing a hard-killed *lock holder*, not performing a kill).

### Against the resource-exhaustion / OOM sub-hypothesis (not one of the two candidates, but tested)

- **`sleep 300` killed at 72 s** — zero RSS, zero CPU. No memory-pressure reaper selects a sleeping shell over a multi-GB pytest tree. Refuted.
- **The largest, oldest, most memory-hungry job survived** (`ced3ef27` coverage, 1014 s) while two younger ones died at the same instant — the exact inverse of jetsam's largest-first selection policy.
- Host load was high (`uptime`: `load averages: 5.84 10.89 14.20`, up 14 days) — this is *consistent with* strain but explains nothing given the two points above. Recorded, not relied upon.

### Against the sleep/wake sub-hypothesis

- **Refuted.** `pmset -g log` shows **no** Sleep/DarkWake/Wake-from transition anywhere near any kill instant. The only entries in the 16:00–18:59 local window on 2026-07-15 are `runningboardd` idle-sleep assertion summaries at 14:04:48 and 18:19:48 — neither within ~3 h of the 17:14 local (15:14 Z) double kill. `uptime` confirms 14 days without reboot. No thermal or maintenance events either (**NOT FOUND**).

### Against the "background jobs die at the spawning context's turn boundary" hypothesis (lesson `2026-06-24-18-001`)

- **Not supported for these events, and partly contradicted.** All 2026-07-15 kills were **orchestrator-tier**, launched by the top-level session (`isSidechain: false`, `caller: {"type":"direct"}`) — there is no leaf context to end. In `d0365a0b` and `25326d05` the spawning turn was still live and idle-waiting at the kill instant, and both sessions continued normally afterwards (`d0365a0b:988–1009`, `25326d05:1066–1092`).
- The lesson's mechanism (leaf's context ends → job orphaned) is real but describes a **different** failure mode. It does **not** explain orchestrator-tier kills. *Inference.*
- **NOT FOUND**: no compaction, session restart, or subagent-completion event within seconds of any of the 14 clusters.

---

## Historical pattern

### How far back

**At least 2026-06-23** — 23 days before the observed incident. Earliest paired kill:

| First occurrence | Session | Job | Elapsed |
|---|---|---|---|
| 2026-06-23T18:57:37.545Z | `7fa848b1` | "Watch CI checks on PR #766" | 653 s |

Total: **90 killed background jobs** across `-Users-oliver-git-plan-marshall` + `-Users-oliver-git-TokenSheriff`. This is **chronic and long-standing**, not a 2026-07-15 regression. Dated occurrences include 06-23, 06-29 (×6), 06-30, 07-07 (×4), 07-08 (×2), 07-09 (×5), 07-10 (×5), 07-12, 07-13 (×14), 07-14 (×3), 07-15 (×7).

### Correlation with concurrency — **weaker than assumed**

| Status | n | Mean *other* sessions with a BG job in flight at the event | Distribution |
|---|---|---|---|
| `killed` | 86 | **0.37** | 0 others: 58 (67 %) · 1: 24 (28 %) · 2: 4 (5 %) |
| `completed` | 762 | **0.27** | 0 others: 593 (78 %) · 1: 133 (17 %) · 2: 32 (4 %) · 3: 4 (1 %) |

**The correlation with concurrency is real but weak (0.37 vs 0.27), and concurrency is plainly not necessary: 67 % of kills happened with no other session running anything in the background.** The operator's framing — "when 2-3 plan worktrees run concurrently" — describes the *observed* incident accurately but **over-generalizes**: the majority of kills across 23 days were solo. Concurrency raises the odds somewhat and makes the synchronized clusters *visible*, but it is not the trigger. *Inference from the table above; the effect size is small and I have not tested it for significance.*

### Per-occurrence record from archived / dormated plans

**NOT FOUND — and this is itself a finding.** `rg` over `/Users/oliver/git/plan-marshall/.plan/archived-plans/` and `/Users/oliver/git/plan-marshall/.plan/temp/dormated-plans/` for `killed externally|killed with no output|killed before producing|was stopped|zero output` returned **zero hits**. Matches for `killed|orphan` in those trees are unrelated (`argparse_rejection` stderr dumps, prose about extension-point removal).

**Implication:** ~90 kill events over 23 days left **no trace in any plan-scoped artifact** — not in `decision.log`, `status.json`, `metrics.md`, or `work/`. The events live **only** in the session transcripts. Retrospectives and metrics have been silently blind to this failure mode for the entire period, and every plan's wall-clock/idle accounting silently absorbs the re-run cost. *This is the reason the pattern went undiagnosed for 23 days.* (Corroborates source-C's noted limitation: the ledger has no `status` field and timeouts record `exit_code: 0`.)

### Global logs (source C)

`rg -c 'Timeout after' /Users/oliver/git/plan-marshall/.plan/local/logs/` → **zero hits**, across all `script-execution-*.log` and `work-*.log`. **Confirms the established finding**: the wrapper timeout never fired.

### Build-output logs (source D)

`/Users/oliver/git/plan-marshall/.plan/temp/build-output/` contains **no files from 2026-07-15** — newest are May/June (`default/`, `plan-marshall/`). The killed builds never reached the point of writing a build log. Numerous 0-byte `test-*.log` files exist there (e.g. `default/test-2026-05-29-215021.log`, `default/test-2026-05-19-215053.log`) but they predate the window by weeks and I have **no evidence** tying them to this mechanism — noted, not attributed.

The direct artifacts are instead the **0-byte task-output files**: `25326d05/tasks/buuvmm0e9.output` (0 B, mtime Jul 15 17:11:29 local = launch time, never written), `25326d05/tasks/bljspd15x.output` (0 B), `d0365a0b/tasks/bhcpfxv7x.output` (0 B), `d0365a0b/tasks/b4mwuf2zn.output` (0 B), `25326d05/tasks/b6va4tcwi.output` (0 B). Successful peers in the same directories are 32 KB – 967 KB (e.g. `d0365a0b/tasks/b2leckdib.output` = 967 361 B).

---

## Contradictions with the established findings

**None with the established findings.** All four are corroborated:

1. *`subprocess.run(..., timeout=)` at `_build_execute.py:216-235` is the only OS-level kill in the source* — corroborated; the independent search (`agent-a94f7118951d9e406.jsonl:31,34,37`) found only docstring prose elsewhere (`build_queue.py:28,226`).
2. *The timeout did not fire* — **strongly corroborated and extended**: max observed elapsed is **827 s**, and one death at **11 s**; `rg 'Timeout after'` → 0 hits; `timeout_seconds: 817` un-ratcheted.
3. *The wrapper was killed from outside* — corroborated; extended to "and so were `sleep`, `gh run watch`, and `mvn`".
4. *The build-queue lock is not the cause* — corroborated; no queue operation coincides with any kill, and `sleep 300` never touches the queue.

**One contradiction with the coordinator's mid-task framing** (not with the established findings):

> *"The invariant across both incidents is: LONG-RUNNING + BACKGROUNDED… Foreground worked… Test whether the discriminator is background-vs-foreground rather than duration alone."*

**`run_in_background: true` is confirmed as a necessary condition** (all 90 kills are backgrounded; no foreground command in the corpus was ever killed this way). **But "long-running" is falsified as a component of the invariant**: `ced3ef27`'s **1014-s** background build **completed successfully** at 15:15:11, having survived the 15:14:21 kill that took a **173-s** sibling. Deaths span **11 s → 827 s**. Backgrounded-ness is the discriminator; **duration is not**, in either direction.

A second, softer correction: the fallback builds that "worked" were **both narrower and foreground**. TokenSheriff's successful fallback (`maven verify -pl token-sheriff-client -pl token-sheriff-validation`, 1 m 41 s) changed **two** variables at once, so it does not isolate background-vs-foreground. The clean isolation comes from the corpus, not from that fallback.

---

## Upstream corroboration — added 2026-07-15, AFTER the analysis above

The analysis reached "the harness" **by exclusion**, without consulting Claude Code's docs or issue
tracker. That check was run afterwards. It **confirms the failure class is real and known upstream**
— but, importantly, **none of the documented policies explains our data.**

### Confirmed real (verified via `gh api`, exact title match — not taken on trust)

| Issue | Title | State |
|---|---|---|
| [anthropics/claude-code#25188](https://github.com/anthropics/claude-code/issues/25188) | *"Background task cleanup kills long-running processes started via Bash tool"* | closed |
| [anthropics/claude-code#68625](https://github.com/anthropics/claude-code/issues/68625) | *"[BUG] Claude Desktop (Windows) silently kills run_in_background tasks after 15-min idle — WarmLifecycle taskkills the embedded CLI process tree"* | open |

> **Provenance caution:** these came from a `claude-code-guide` subagent that also wrote *"1,722+
> reports"* — reflecting **our own** notification count back as if it were community bug reports.
> That is a confabulation tell, so both issue numbers were independently verified via `gh api`
> before being recorded here. **The two above are real. Two others it cited (#32050, #70686) were
> NOT verified — do not cite them without checking.**

### Documented reaping policies — and why they DON'T fit our data

The guide reported these as documented Claude Code behaviour (**quotes NOT independently verified
against the docs — treat as second-hand**):

- Background tasks terminated if **output exceeds 5 GB**.
- Background tasks terminated **on OS memory pressure, "provided the session has been idle for at
  least 30 minutes with no turn or subagent running"** (attributed to ~v2.1.193).
- #68625: Claude **Desktop** (Windows) 15-min idle kill via `WarmLifecycle` (`idleTimeoutMs:
  900*1e3`, `timeoutOnHidden: true`).
- Auto-cleanup at **context compaction or session end**.

**Every one of these is contradicted or inapplicable for our 90 kills:**

| Documented policy | Why it does not explain our data |
|---|---|
| 5 GB output cap | Killed jobs produced **0 bytes**. `sleep 300` produces nothing. |
| Memory pressure + **session idle ≥30 min, no turn running** | Our kills happened with **turns live and sessions actively working** (`d0365a0b`/`25326d05` were mid-turn and continued normally afterwards). The idle precondition was not met. |
| Desktop 15-min idle (`WarmLifecycle`) | We are on **macOS CLI**, not Windows Desktop. And `sleep 300` died at **72 s** — far under 15 min. |
| Cleanup at compaction / session end | **NOT FOUND**: no compaction, session restart, or subagent-completion event within seconds of any of the 14 clusters. Sessions continued normally after the kills. |

**Conclusion (inference):** the class is confirmed upstream, but our specific kills match **no
documented policy** — they are either undocumented behaviour or a distinct code path. This
**sharpens open question 1 rather than answering it**: whatever selects the victims, it is not any
published rule. It also means an upstream report should lead with the `sleep 300` case and the
synchronized cross-session clusters, since those are the parts no existing issue describes.

**Not yet done:** no upstream issue has been filed for our signature. See
[`plans/plan-background-build-kill.md`](plans/plan-background-build-kill.md) deliverable 4.

## The setsid / daemonization experiment (2026-07-15, session `a485d883`)

**Question:** does detaching a child from the backgrounded Bash job's process tree let it escape the
harness's reaper — i.e. is cleanup process-group/session-scoped, or does it walk the process tree?
This was the hard gate in front of Rung 2 (the server): if nothing escapes, a server's children die
exactly like today's jobs and the server buys nothing.

**Method:** a `run_in_background` Bash job runs a Python launcher that spawns a heartbeat child
(appends a timestamp to a file every second) in a given detachment shape, then blocks as the
reapable "wait". After the job is killed, the heartbeat file shows to the second whether and when
the child died. Kill trigger: `TaskStop` on the job (deterministic proxy for the spontaneous
reaper), plus one control arm left running that caught a **natural** reap. macOS ships no `setsid`
binary; detachment used `subprocess.Popen(..., start_new_session=True)` (`os.setsid()` in the
child).

| Arm | Shape | Outcome |
|---|---|---|
| **A** | Heartbeat child in its **own session + own process group** (verified `pgid==sid==pid`), still **live-parented** to the waiting launcher | **KILLED** with the launcher — heartbeat froze at the exact kill timestamp; both PIDs gone. SIGHUP is excluded (own session, no controlling terminal): the child was actively killed. **Cleanup walks the process tree; it is not pgroup/session-scoped.** |
| **B** | Same as A, left running as a natural-reap control | **Natural spontaneous kill landed ~1844 s after launch** (`status: killed`, unprompted — extends the corpus' 11→827 s death span). Launcher AND own-session setsid child died together, heartbeat frozen at the kill instant. **The tree-walk finding holds against the real reaper, not just the `TaskStop` proxy.** |
| **C** | **Double-fork daemonization**: launcher → intermediate (own session, exits immediately) → heartbeat (own session, **re-parented to PID 1**, verified `ppid=1`) | **SURVIVED** — daemon alive and heartbeating 55 s after the same kill mechanism took its launcher. No parent link remains for the tree walk to follow. |

**Verdict:** plain `setsid`-style detachment does NOT escape the reaper; **full double-fork
daemonization (re-parent to PID 1) DOES.** The double-fork arm was proxy-verified only, but a
reaper stronger than the observed tree-walk would need spawn-time descendant snapshotting, which
cannot enumerate a post-hoc double-forked grandchild either — residual risk minimal. This is the
evidence behind the Rung 2 hard constraint: *the server must be launched via double-fork
daemonization, never as a live-parented detached child.*

Arm B's natural kill is also a corpus datapoint: it hit a process whose only activity was one
30-second-interval print loop — further confirmation that job content is irrelevant and that death
times have no ceiling.

## The failure is NORMALIZED as "flaky environment" — why 23 days passed undiagnosed

**Added 2026-07-16 from TokenSheriff PR #572's landing report** (the same TokenSheriff session already
in the timeline above — the `(no pre-commit profile)` retries at 17:44:40 / 17:49:12 — so this is
**not** an independent incident, but it IS the agent's own contemporaneous characterization):

> *"**Flaky background CI/build waits** — several long-running background calls were killed by the
> environment with no output partway through. **All were transient; retrying resolved them every
> time.**"*

Filed under "notable deviations", one line, no follow-up.

**Every clause is factually right and the conclusion is wrong.** They *were* killed by the
environment, with no output. But "transient" is precisely what this is **not** — it is a systematic,
23-day, 90-event, cross-repo reap (§ Historical pattern). And "retrying resolved them every time" is
survivorship framing: the retry succeeds *eventually* because kill selection is indiscriminate, not
because the condition cleared.

**This is the actual answer to "why did this go undiagnosed for 23 days?"** The § Historical pattern
section establishes the *artifact*-level blindness (no `status` field; timeouts exit 0; nothing in
`decision.log`/`status.json`/`metrics.md`). This is the *cognitive* half:

- Agents encountering it reach for the nearest available explanation — "flaky", "transient",
  "environment issue" — and **move on without escalating**. Each occurrence is individually
  survivable, so none becomes a report.
- The cost is absorbed silently into wall-clock and re-runs, which the artifacts then record as
  ordinary "idle waiting on CI/builds".
- **The 90 events were never 90 signals. They were 90 shrugs.**

**Design consequence — this is a first-class requirement, not a nicety:** any mitigation MUST make
the kill *legible at the call site*, or agents will keep pattern-matching it to "flaky" and blind-
retrying regardless of what the ledger records. See
[`plans/plan-background-build-kill.md`](plans/plan-background-build-kill.md) deliverable 2
(killed-job detector) — this section is its strongest justification. **Both observed incident
families (plan-marshall 07-15, TokenSheriff #572) blind-retried before escalating; #572 never
escalated at all.**

**Corollary for the corpus count:** open question 6 asks whether some of the 90 were benign. This
cuts the other way too — **kills characterized as "flaky" and silently retried may be
under-reported**, since nothing obliges an agent to record them.

## The ~12-hour orphan (hardening-sweep / PR #910, 2026-07-16) — worst observed impact

From #910's landing report:

> *"an orphaned `finalize-step-simplify` leaf dispatch (**its own backgrounded build silently died
> for ~12h** — a known harness issue, not a plan-marshall bug) was recovered by re-running
> verification directly"*

**Two firsts, and one encouraging sign.**

**1. Detection latency, not job lifetime — and it dwarfs everything in the corpus.** The paired-kill
distribution above spans **11 s → 827 s** with no ceiling. **~12 h is ~52× the maximum.** The
resolution is almost certainly that the *death* was ordinary (inside the known range) and the
**~12 h is how long the plan sat parked on a job that was already dead** — nothing surfaced it.
*(Inference — this run's paired kill is not in the analysed corpus; re-run `forensics-scripts/` to
confirm the actual elapsed-before-death.)* Either way it is the **worst observed impact of the
legibility gap**: a finalize step blocked for half a day on a corpse. It also means the ~90-event
corpus measures *kills*, never *dwell time* — the real cost is strictly larger than the counts imply.

**2. It was a LEAF that backgrounded a build — a D6 coverage gap in phase-6-finalize.** plan-6's D6
compose-time `execution_tier` guard was verified live and closed leaf *self*-backgrounding
(`HANDOVER.md:75-76`; `feedback_orchestrator_owns_long_builds`: "leaves never background"). `#897`
already found the guard does NOT cover the **initial phase-5 envelope call site**
(`HANDOVER.md:186-190`). **`finalize-step-simplify` is a dispatched leaf and it backgrounded a
build anyway — so the gap extends into phase-6-finalize.** That is a distinct, previously-unrecorded
D6 hole, and it is *upstream* of the kill: had the guard fired, the build would have taken the
orchestrator-tier yield and never been a leaf-owned background job. **Fixing the D6 gap removes this
class of exposure independently of anything in this epic.**

**3. The diagnosis is propagating — the agent called it *"a known harness issue, not a plan-marshall
bug"* and stopped chasing it.** Contrast TokenSheriff #572's *"flaky… transient"* (§ above). That is
this evidence doc working as intended: correct attribution on first contact, no wasted root-cause
hunt. **But note what it did NOT prevent: ~12 h of dwell.** Knowing the cause does not make the
failure *visible* — only detection does. This is the sharpest argument yet that
[`plans/plan-background-build-kill.md`](plans/plan-background-build-kill.md) deliverable 2
(killed-job detector) is the highest-value item in the epic, and that it is **independent of, and
should land before, either rung.**

## Open questions the evidence cannot settle

1. **What selects *which* backgrounded jobs die?** The 15:14:21 event killed 2 of 3 in-flight jobs and spared the oldest/longest. Selection is neither by age, nor size, nor tool, nor repo. **Unexplained.** This is the highest-value remaining question — it is the difference between "the harness stops background jobs" and a fix. **Sharpened by the upstream check (above): it is not any *documented* policy either** — the 5 GB cap, the memory-pressure-plus-30-min-idle rule, the Desktop 15-min idle timer, and compaction/session-end cleanup are each contradicted or inapplicable.
2. **What triggers a cluster?** 14 clusters over 23 days with no correlated OS power, thermal, sleep/wake, compaction, or session-lifecycle event. Something reaches ≥3 sessions within 1.53 s. A shared parent process or a machine-wide Claude Code supervisor is the natural suspect — **untested**, as I cannot see the harness's own logs. The ~0.2–1.5 s intra-cluster stagger *looks like* a sequential loop over sessions (*inference from the stagger's regularity; could equally be independent reactions to one shared signal*).
3. **SIGTERM or SIGKILL?** Unrecorded. Decisive for distinguishing a graceful supervisor stop from a hard kill — the wrapper's `except TimeoutExpired` not running is consistent with **either** an unhandled SIGTERM or a SIGKILL.
4. **Is this specific to Claude Code `2.1.207`?** The version is stamped per-record (`"version":"2.1.207"` at `646410d9:2317`). I did **not** test whether kill density changes across versions — a tractable follow-up against the 90-kill corpus.
5. **Does the harness impose an undocumented background-job cap or idle deadline?** Would explain selectivity under concurrency but **not** the 67 % of kills with no sibling activity, nor `sleep 300` at 72 s. **Not investigated** — requires harness documentation I do not have.
6. **Were any of the 90 kills actually benign** (e.g. a job whose session moved on)? I did not classify kills by whether the session still wanted the result. The 2026-07-15 ones were plainly unwanted (all were immediately relaunched), but the corpus-wide 90 may include benign cancellations, which would inflate the historical count. **Unquantified — treat 90 as an upper bound on genuine failures.**

---

### Reproduction scripts — PRESERVED at [`forensics-scripts/`](forensics-scripts/)

Originally written to a session-scoped scratchpad (which is destroyed when that session ends); copied
here 2026-07-15 so the analysis stays reproducible.

| Script | What it does |
|---|---|
| [`forensics-scripts/scan.py`](forensics-scripts/scan.py) | Extracts KILL / BG / STOP events with timestamps. |
| [`forensics-scripts/pair.py`](forensics-scripts/pair.py) | Joins kills to launches via `<tool-use-id>`; prints elapsed-before-death. |
| [`forensics-scripts/cluster.py`](forensics-scripts/cluster.py) | Finds cross-session kill clusters ≤ 5 s (the 14-cluster result). |
| [`forensics-scripts/notif.py`](forensics-scripts/notif.py) | Killed-vs-completed clustering rates (the 32.2 % / 2.0 % result). |
| [`forensics-scripts/conc.py`](forensics-scripts/conc.py) | In-flight concurrency at kill vs completion (the 67 %-solo result). |

**Input corpus:** `~/.claude/projects/-Users-oliver-git-plan-marshall/*.jsonl` and
`~/.claude/projects/-Users-oliver-git-TokenSheriff/*.jsonl` (top-level **and** `subagents/`
sub-directories). These accumulate over time, so a re-run will cover a *larger* window than this
report — the counts here (1,722 notifications / 90 kills, through 2026-07-15) are a snapshot, not a
fixed total. **Re-running is also the cheapest way to test open question 4** (whether kill density
changes across Claude Code versions).
