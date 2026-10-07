#!/usr/bin/env python3
"""Trigger confound (plan-marshall), refined four-outcome scoring, epoch cut."""
import json, os, re, collections, glob
BASE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(BASE, "classified.json")))
POP = [r for r in R if not r["skip_label"] and r["opened_in_window"]]
EPOCH_PM = "2026-09-03T22:04:35Z"  # plan-marshall #1388 merged: repo-local .pr_agent.toml removed

enum = json.load(open(os.path.join(BASE, "enumeration.json")))
head = {(repo, p["number"]): p["headRefName"] for repo, ps in enum.items() for p in ps}

runs = [r for pg in json.load(open(os.path.join(BASE, "pm_pragent_runs.json"))) for r in pg["workflow_runs"]]
pm = [r for r in POP if r["repo"] == "plan-marshall"]
by_branch = collections.defaultdict(list)
for r in R:
    if r["repo"] == "plan-marshall":
        by_branch[head[("plan-marshall", r["number"])]].append(r)
pra_shas = collections.defaultdict(set)
unmapped = 0
for run in runs:
    if run["event"] != "pull_request" or run["conclusion"] != "success":
        continue
    cands = [r for r in by_branch.get(run["head_branch"], []) if r["createdAt"] <= run["created_at"]]
    if not cands:
        unmapped += 1
        continue
    pr = max(cands, key=lambda r: r["createdAt"])
    pra_shas[pr["number"]].add(run["head_sha"])
for r in pm:
    for g in r["pra_guides"]:
        if g["updated_until"]:
            pra_shas[r["number"]].add(g["updated_until"])


def src_count(repo, n):
    d = json.load(open(os.path.join(BASE, "raw", f"{repo}__{n}.json")))
    tot = 0
    for x in d["reviews"] + d["issue_comments"]:
        if x["user"]["login"] != "sourcery-ai[bot]":
            continue
        b = x["body"] or ""
        m = re.search(r"I've found (\d+) security issues?, and (\d+) other issues?", b)
        if m:
            tot += int(m.group(1)) + int(m.group(2)); continue
        m = re.search(r"I've found (\d+) issues?", b)
        if m:
            tot += int(m.group(1))
    return tot


print("unmapped pull_request success runs", unmapped)
same = diff = 0
prs_same = set(); prs_diff = set(); prs_nosha = set()
for r in pm:
    if not r["cr_actionable_by_commit"] or not r["pra_present"]:
        continue
    shas = pra_shas.get(r["number"], set())
    if not shas:
        prs_nosha.add(r["number"])
    for c, n in r["cr_actionable_by_commit"].items():
        if c in shas:
            same += n; prs_same.add(r["number"])
        else:
            diff += n; prs_diff.add(r["number"])
print("CR actionable (self-declared) on commit pr-agent reviewed:", same, "PRs", len(prs_same))
print("CR actionable on commit pr-agent never observably reviewed:", diff, "PRs", len(prs_diff))
print("PRs with no pr-agent sha recovered", sorted(prs_nosha))
paired_pm = [r for r in pm if r["cr_actionable_selfdeclared"] > 0 and r["pra_present"]]
first_commit_hit = sum(1 for r in paired_pm if any(c in pra_shas.get(r["number"], set()) for c in r["cr_actionable_by_commit"]))
print("paired plan-marshall PRs", len(paired_pm), "with >=1 same-commit CR actionable", first_commit_hit)

# ---- refined four-outcome scoring
sc = collections.Counter(); per = {}
for r in POP:
    dep = "dependabot" in r["author"]
    base = r["cr_reviewed"] or r["src_reviewed"]
    bcount = max(r["cr_actionable_selfdeclared"], src_count(r["repo"], r["number"]))
    if not r["pra_present"]:
        o = "excluded-by-design (dependabot org skip rule)" if dep else "NO-RESULT (check trigger)"
    elif not base:
        o = "unassessable-no-baseline"
    elif bcount > r["pra_findings"]:
        o = "deficit" + ("(pra non-empty)" if r["pra_findings"] else "")
    else:
        o = "clean-corroborated"
    per[f"{r['repo']}#{r['number']}"] = {"outcome": o, "baseline_count": bcount, "pra_findings": r["pra_findings"]}
    sc[(r["repo"], o)] += 1
for k, v in sorted(sc.items()):
    print(k, v)
print(collections.Counter(v["outcome"] for v in per.values()))
json.dump(per, open(os.path.join(BASE, "scoring.json"), "w"), indent=1)
cc = [k for k, v in per.items() if v["outcome"] == "clean-corroborated"]
print("clean-corroborated", cc)
print("deficit non-empty", [(k, v) for k, v in per.items() if "non-empty" in v["outcome"]])

# ---- epoch cut (plan-marshall pr-agent yield), keyed on the time the CURRENT guide body was produced
print("\n== plan-marshall epoch cut at", EPOCH_PM)
for name, pred in (("A <", lambda t: t < EPOCH_PM), ("B >=", lambda t: t >= EPOCH_PM)):
    gs = [(r, g) for r in pm for g in r["pra_guides"] if pred(g["updated_at"])]
    prs = {r["number"] for r, g in gs}
    subst = [r["number"] for r, g in gs if g["focus"] or g["security_populated"]]
    imp = [r for r in pm if r["pra_improve_ic"] or r["pra_improve_inline"]]
    print(name, "guides", len(gs), "substantive", len(subst), subst,
          "canned", sum(g["canned"] for r, g in gs))
for name, pred in (("A <", lambda t: t < EPOCH_PM), ("B >=", lambda t: t >= EPOCH_PM)):
    prs = [r for r in pm if (r["pra_improve_ic"] or r["pra_improve_inline"]) and pred(r["createdAt"])]
    print(name, "/improve PRs (by PR open time)", len(prs), "non-empty", sum(bool(r["pra_improve_inline"]) for r in prs),
          [r["number"] for r in prs if r["pra_improve_inline"]])
# other repos: no epoch, but show cross-check
