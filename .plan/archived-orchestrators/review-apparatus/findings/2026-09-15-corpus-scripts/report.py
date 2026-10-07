#!/usr/bin/env python3
import json, os, sys, collections, re
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from classify import automated_kind, REPOS

R = json.load(open(os.path.join(BASE, "classified.json")))
POP = [r for r in R if not r["skip_label"] and r["opened_in_window"]]
SKIP = [r for r in R if r["skip_label"]]


def cr_outcome(r):
    if r["cr_reviewed"]:
        return "reviewed" + ("+refused" if r["cr_refusals"] else "")
    if r["cr_refusals"]:
        return "refused:" + ",".join(sorted(r["cr_refusals"]))
    return "absent"


def src_outcome(r):
    if r["src_reviewed"]:
        return "reviewed" + ("+refused" if r["src_refusals"] else "")
    if r["src_refusals"]:
        return "refused:" + ",".join(sorted(r["src_refusals"]))
    return "absent"


def pra_outcome(r):
    if not r["pra_present"]:
        return "absent"
    return "substantive" if r["pra_substantive"] else "canned"


print("== Coverage (population)")
tot = collections.Counter()
print("repo | PRs | pra | CR reviewed | CR refused-only | CR refused-any | Src reviewed | Src refused-only | Src refused-any | none")
for repo in REPOS:
    rr = [r for r in POP if r["repo"] == repo]
    c = collections.Counter()
    c["PRs"] = len(rr)
    for r in rr:
        c["pra"] += r["pra_present"]
        c["crrev"] += r["cr_reviewed"]
        c["crref_only"] += (not r["cr_reviewed"] and bool(r["cr_refusals"]))
        c["crref_any"] += bool(r["cr_refusals"])
        c["srcrev"] += r["src_reviewed"]
        c["srcref_only"] += (not r["src_reviewed"] and bool(r["src_refusals"]))
        c["srcref_any"] += bool(r["src_refusals"])
        c["none"] += not (r["pra_present"] or r["cr_reviewed"] or r["src_reviewed"])
    tot += c
    print(repo, dict(c))
print("TOTAL", dict(tot))

print("\n== No reviewer produced a review")
for r in POP:
    if not (r["pra_present"] or r["cr_reviewed"] or r["src_reviewed"]):
        print(r["repo"], r["number"], automated_kind(r), r["author"], r["title"][:70], r["additions"], r["deletions"],
              "CRref", r["cr_refusals"], "SRCref", r["src_refusals"])

print("\n== Substantive PRs with NO pr-agent guide")
for r in POP:
    if not r["pra_present"] and not automated_kind(r):
        print(r["repo"], r["number"], r["author"], r["createdAt"], r["title"][:70], r["additions"], r["deletions"], r["state"], "CR", cr_outcome(r), "SRC", src_outcome(r))

print("\n== pr-agent yield")
guides = [g for r in POP for g in r["pra_guides"]]
print("PRs with guide", sum(r["pra_present"] for r in POP), "guides", len(guides))
print("len partition", sorted(collections.Counter(g["len"] for g in guides).items()))
print("canned", sum(g["canned"] for g in guides), "with focus", sum(bool(g["focus"]) for g in guides),
      "security populated", sum(g["security_populated"] for g in guides))
print("multi-guide PRs", [(r["repo"], r["number"], len(r["pra_guides"])) for r in POP if len(r["pra_guides"]) > 1])
print("updated-until marker", sum(bool(g["updated_until"]) for g in guides))
for r in POP:
    for g in r["pra_guides"]:
        if g["focus"] or g["security_populated"]:
            print("  SUBST", r["repo"], r["number"], g["focus"], "sec" if g["security_populated"] else "")
imp_ic = [x for r in POP for x in r["pra_improve_ic"]]
imp_in = [(r["repo"], r["number"], len(r["pra_improve_inline"])) for r in POP if r["pra_improve_inline"]]
print("/improve issue comments", len(imp_ic), "empty", sum(x["empty"] for x in imp_ic),
      "PRs with improve ic", sum(bool(r["pra_improve_ic"]) for r in POP))
print("/improve inline", sum(n for *_, n in imp_in), "on PRs", imp_in)
print("PRs with /improve any", sum(bool(r["pra_improve_ic"] or r["pra_improve_inline"]) for r in POP))
print("PRs with /improve both empty-ic AND inline", [(r["repo"], r["number"]) for r in POP if r["pra_improve_ic"] and r["pra_improve_inline"]])
print("per repo /improve", collections.Counter(r["repo"] for r in POP if r["pra_improve_ic"] or r["pra_improve_inline"]))

print("\n== CodeRabbit yield")
for repo in REPOS:
    rr = [r for r in POP if r["repo"] == repo]
    print(repo, "inline_roots", sum(r["cr_inline"] for r in rr), "inline_all", sum(r["cr_inline_all"] for r in rr),
          "reviews", sum(r["cr_reviews"] for r in rr), "reviews_with_body", sum(r["cr_reviews_with_body"] for r in rr),
          "actionable_SD", sum(r["cr_actionable_selfdeclared"] for r in rr), "nit_SD", sum(r["cr_nitpick_selfdeclared"] for r in rr),
          "PRs actionable>=1", sum(r["cr_actionable_selfdeclared"] > 0 for r in rr))
print("TOTAL inline_roots", sum(r["cr_inline"] for r in POP), "reviews", sum(r["cr_reviews"] for r in POP),
      "actionable_SD", sum(r["cr_actionable_selfdeclared"] for r in POP))
rk = collections.Counter()
for r in POP:
    for k, v in r["cr_refusals"].items():
        rk[k] += v
print("CR refusal comments by kind", rk, "PRs by kind", collections.Counter(k for r in POP for k in r["cr_refusals"]))

print("\n== Sourcery")
sk = collections.Counter(); sp = collections.Counter()
for r in POP:
    for k, v in r["src_refusals"].items():
        sk[k] += v; sp[k] += 1
print("reviews", sum(r["src_reviews"] for r in POP), "inline", sum(r["src_inline"] for r in POP),
      "refusal artefacts", sk, "PRs by refusal kind", sp, "PRs with issue-finding reviews", sum(r["src_issue_reviews"] > 0 for r in POP))
print("size-refused PRs", [(r["repo"], r["number"]) for r in POP if "size" in r["src_refusals"]])

print("\n== Paired recall")
paired = [r for r in POP if r["cr_actionable_selfdeclared"] > 0 and r["pra_present"]]
print("paired", len(paired), "pra substantive on paired", sum(r["pra_substantive"] for r in paired),
      [(r["repo"], r["number"]) for r in paired if r["pra_substantive"]])
for repo in REPOS:
    pp = [r for r in paired if r["repo"] == repo]
    print("  ", repo, len(pp), sum(r["pra_substantive"] for r in pp))

print("\n== Four-outcome scoring (pr-agent)")
sc = collections.Counter()
per = {}
for r in POP:
    base = r["cr_reviewed"] or r["src_reviewed"]
    base_find = r["cr_actionable_selfdeclared"] > 0 or r["src_issue_reviews"] > 0 or r["cr_inline"] > 0
    if not r["pra_present"]:
        o = "pra-absent (check trigger)" if base else "pra-absent-no-baseline"
    elif not base:
        o = "unassessable-no-baseline"
    elif base_find and not r["pra_substantive"]:
        o = "deficit"
    else:
        o = "clean-corroborated"
    per[(r["repo"], r["number"])] = o
    sc[(r["repo"], o)] += 1
for k, v in sorted(sc.items()):
    print(k, v)
print(collections.Counter(per.values()))
json.dump({f"{k[0]}#{k[1]}": v for k, v in per.items()}, open(os.path.join(BASE, "scoring.json"), "w"), indent=1)

print("\n== Skip-labelled")
for repo in REPOS:
    ss = [r for r in SKIP if r["repo"] == repo]
    print(repo, len(ss), "automated", sum(bool(automated_kind(r)) or r["author"].startswith("app/") for r in ss))
    for r in ss:
        if not r["author"].startswith("app/"):
            print("   ", r["number"], r["state"], r["createdAt"][:10], r["title"][:70], f"+{r['additions']}/-{r['deletions']}", r["changedFiles"],
                  "pra", pra_outcome(r), "CR", cr_outcome(r), "SRC", src_outcome(r))
