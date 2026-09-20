"""Derive every figure in the cloud-run quality analysis for `code-intelligence-substrate`.

Follows doc/concepts/analyzis-cloud-plan/README.adoc. Nothing here is transcribed: every table the
report carries is produced by this script from the ingested corpus.
"""
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter, defaultdict

REPO = pathlib.Path("/Users/oliver/git/plan-marshall")
EPIC = REPO / ".plan/local/orchestrator/code-intelligence-substrate"
RUNS = EPIC / "cloud-runs"
LANE_SKILL = ".claude/skills/cloud-plan-lane/SKILL.md"

PR_RE = re.compile(r'\*\*PR:\*\*\s*\[#(\d+)\]')
GAP_RE = re.compile(r'^## (G\d+)\b', re.M)
KIND_RE = re.compile(r'^- \*\*Kind:\*\*\s*(.+?)\s*$', re.M)
SEV_RE = re.compile(r'^- \*\*Severity:\*\*\s*([a-z]+)', re.M)
WHERE_RE = re.compile(r'^- \*\*Where:\*\*\s*(.+?)\s*$', re.M)
OVERALL_RE = re.compile(r'^\*\*Overall verdict:\*\*\s*(.+?)\s*$', re.M)
DROW_RE = re.compile(r'^\|\s*(D\d+)\s*\|(.*)\|\s*$', re.M)


def sh(*args):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True).stdout


def plan_dirs():
    return sorted(p for p in RUNS.iterdir() if p.is_dir() and not p.name.startswith("_"))


def read(p):
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------- Step 0: lane-fix exclusion
def landing_commit(pr):
    """Resolve a PR's landing commit ANCHORED TO THE END OF THE SUBJECT LINE.

    A bare --grep also matches commits that merely mention the number in their body.
    """
    out = sh("git", "log", "--all", "--format=%H%x09%s", "-F", "--grep", f"(#{pr})")
    for line in out.splitlines():
        sha, _, subj = line.partition("\t")
        if subj.rstrip().endswith(f"(#{pr})"):
            return sha
    return None


def production_files(sha):
    out = sh("git", "show", "--name-only", "--format=", sha)
    files = [f for f in out.splitlines() if f.strip()]
    return [f for f in files if not f.startswith("doc/plans/")]


def step0():
    rows, excluded = [], []
    for d in plan_dirs():
        # A plan resumed across sessions carries its PR in the LAST report, not the first:
        # 350/report-01.md records "PR: none - run 01 was halted before the PR cycle".
        pr = None
        for rp in sorted(d.glob("report-*.md")):
            m = PR_RE.search(read(rp) or "")
            if m:
                pr = m.group(1)
        sha = landing_commit(pr) if pr else None
        prod = production_files(sha) if sha else []
        is_lanefix = bool(prod) and set(prod) == {LANE_SKILL}
        rows.append(dict(plan=d.name, pr=pr, sha=(sha or "")[:9],
                         prod_files=len(prod), lane_fix=is_lanefix))
        if is_lanefix:
            excluded.append(d.name)
    return rows, excluded


# ---------------------------------------------------------------- Steps 1-3
def per_plan(d):
    ver, gaps = read(d / "verification.md") or "", read(d / "gaps.md") or ""
    overall = OVERALL_RE.search(ver)
    # deliverable rows: leading token of the Verdict cell (last column)
    dels = {}
    for m in DROW_RE.finditer(ver):
        cells = [c.strip() for c in m.group(2).split("|")]
        verdict = cells[-1] if cells else ""
        tok = verdict.split()[0].strip("*`—-").upper() if verdict else ""
        dels.setdefault(m.group(1), tok)
    ids = GAP_RE.findall(gaps)
    kinds = KIND_RE.findall(gaps)
    sevs = SEV_RE.findall(gaps)
    wheres = WHERE_RE.findall(gaps)
    return dict(
        plan=d.name,
        overall=(overall.group(1).split("—")[0].strip() if overall else "(none)"),
        dels=dels,
        n_del=len(dels),
        d_fail=sum(1 for v in dels.values() if v not in ("CONFIRMED",)),
        gap_ids=ids, kinds=kinds, sevs=sevs, wheres=wheres,
    )


# This corpus uses its own Kind vocabulary rather than the one truthful-signals used. The mapping
# onto the README's three classes is stated here so the partition is auditable, not asserted.
REAL = {"bug", "test-gap", "missing-detector"}
SWEEP = {"incomplete"}
DOC = {"doc-defect", "omission", "report-defect"}


def classify(kind):
    k = kind.strip().lower().strip("`*")
    k = re.split(r"[ (/,]", k)[0]
    if k in SWEEP:
        return "sweep"
    if k in DOC:
        return "doc"
    if k in REAL:
        return "real"
    return f"?{k}"


def main():
    rows, excluded = step0()
    plans = [p for p in plan_dirs() if p.name not in excluded]
    data = [per_plan(d) for d in plans]

    print("=" * 78)
    print("STEP 0 — lane-fix exclusion (criterion: ONLY production file is the lane skill)")
    print("=" * 78)
    unresolved = [r for r in rows if not r["sha"]]
    print(f"run directories scanned: {len(rows)}")
    print(f"PRs resolved to a landing commit: {len(rows) - len(unresolved)}")
    if unresolved:
        print("  UNRESOLVED:", [(r['plan'][:28], r['pr']) for r in unresolved])
    print(f"lane-fix PRs inside this corpus: {len(excluded)} {excluded}")
    # how many lane-fix PRs exist repo-wide
    allc = sh("git", "log", "--all", "--format=%H%x09%s")
    lane_total = 0
    for line in allc.splitlines():
        sha, _, subj = line.partition("\t")
        if not re.search(r"\(#\d+\)$", subj.rstrip()):
            continue
        prod = production_files(sha)
        if prod and set(prod) == {LANE_SKILL}:
            lane_total += 1
    print(f"lane-fix PRs repo-wide: {lane_total}  (outside this corpus: {lane_total - len(excluded)})")

    print()
    print("=" * 78)
    print("STEP 1 — populations")
    print("=" * 78)
    n_del = sum(d["n_del"] for d in data)
    n_gap = sum(len(d["gap_ids"]) for d in data)
    print(f"plans      : {len(data)}")
    print(f"deliverables: {n_del}")
    print(f"gaps        : {n_gap}")
    print(f"severity    : {dict(Counter(s for d in data for s in d['sevs']))}")

    print()
    print("=" * 78)
    print("STEP 2 — deliverable fidelity  (Verdict != CONFIRMED)")
    print("=" * 78)
    d_fail = sum(d["d_fail"] for d in data)
    plans_with_fail = sum(1 for d in data if d["d_fail"])
    print(f"D-fail / deliverables : {d_fail}/{n_del} = {100*d_fail/n_del:.1f}%")
    print(f"plans with >=1 D-fail : {plans_with_fail}/{len(data)} = {100*plans_with_fail/len(data):.1f}%")
    print(f"verdict token tally   : {dict(Counter(v for d in data for v in d['dels'].values()))}")
    print(f"overall verdicts      : {dict(Counter(d['overall'] for d in data))}")

    print()
    print("=" * 78)
    print("STEP 3 — gap taxonomy")
    print("=" * 78)
    kc = Counter(k.strip().lower().strip('`*') for d in data for k in d["kinds"])
    print(f"kinds present ({len(kc)} distinct):")
    for k, v in kc.most_common():
        print(f"   {v:4d}  {k}")
    cls = Counter(classify(k) for d in data for k in d["kinds"])
    print(f"\nthree-way partition: {dict(cls)}")
    tot = sum(cls.values())
    for c in ("real", "sweep", "doc"):
        print(f"   {c:6s} {cls[c]:4d}  {100*cls[c]/tot:.1f}%")
    unk = {k: v for k, v in cls.items() if k.startswith("?")}
    if unk:
        print(f"   UNMAPPED: {unk}")
    print(f"kinds recorded: {sum(len(d['kinds']) for d in data)} of {n_gap} gaps")

    # target: report-01.md vs live surface
    rep_t = sum(1 for d in data for w in d["wheres"] if "report-0" in w.lower())
    print(f"\ngaps targeting the run's own report-01.md: {rep_t}/{sum(len(d['wheres']) for d in data)} "
          f"where-fields = {100*rep_t/max(1,sum(len(d['wheres']) for d in data)):.1f}%")

    print()
    print("=" * 78)
    print("PER-PLAN LEDGER")
    print("=" * 78)
    prmap = {r["plan"]: r for r in rows}
    print(f"{'plan':<62} {'PR':>5} {'ovr':<22} {'D':>3} {'Df':>3} {'G':>4} {'hi':>3}")
    for d in sorted(data, key=lambda x: x["plan"]):
        r = prmap[d["plan"]]
        hi = sum(1 for s in d["sevs"] if s == "high")
        print(f"{d['plan'][:62]:<62} {r['pr'] or '-':>5} {d['overall'][:22]:<22} "
              f"{d['n_del']:>3} {d['d_fail']:>3} {len(d['gap_ids']):>4} {hi:>3}")

    json.dump({"rows": rows, "data": [{k: v for k, v in d.items()} for d in data]},
              open("/private/tmp/claude-501/-Users-oliver-git-plan-marshall/518a46ed-6f9f-4d30-953d-44090e7a1635/scratchpad/analysis.json", "w"))
    print("\n[state written to analysis.json]")


main()
