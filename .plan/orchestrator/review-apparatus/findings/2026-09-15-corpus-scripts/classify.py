#!/usr/bin/env python3
"""Classify raw per-PR dumps. Re-runnable; reads raw/ only."""
import json, glob, os, re, sys, collections

BASE = os.path.dirname(os.path.abspath(__file__))
LOWER = "2026-08-30T20:16:39Z"
PRA = "cuioss-review-bot[bot]"
CR = "coderabbitai[bot]"
SRC = "sourcery-ai[bot]"
REPOS = ["plan-marshall", "cui-http", "TokenSheriff", "API-Sheriff",
         "cui-test-mockwebserver-junit5", "cui-test-juli-logger"]
KNOWN_BOTS = {PRA, CR, SRC}

FOCUS_RE = re.compile(r"<details><summary><a href='[^']*'><strong>(.*?)</strong></a>", re.S)
UPDATED_RE = re.compile(r"Review updated until commit https://github\.com/[^/]+/[^/]+/commit/([0-9a-f]{40})")
ACTIONABLE_RE = re.compile(r"\*\*Actionable comments posted: (\d+)\*\*")
NITPICK_RE = re.compile(r"Nitpick comments \((\d+)\)")


def strip_html_comments(b):
    return re.sub(r"<!--.*?-->", "", b or "", flags=re.S)


def cr_refusal_kind(body):
    # Structural markers only -- a conversational reply that merely QUOTES "Review rate limited"
    # (observed: cui-http#179 comment 5481669579) is not a refusal. (Correction 1.)
    b = strip_html_comments(body)
    if re.search(r"^> ## Review limit reached", b, re.M):
        return "rate"
    if re.search(r"<summary>⚠️ Action not completed</summary>\s*\n\s*Review rate limited", b):
        return "rate"
    if re.match(r"\s*Your \[plan\]\([^)]*\) includes PR reviews subject to \[rate limits\]", b):
        return "rate"
    m = re.search(r"^> ## Review skipped\s*\n>\s*\n>\s*(.*)$", b, re.M)
    if m:
        line = m.group(1)
        if re.search(r"label", line, re.I):
            return "skipped-label"
        if re.search(r"No new commits", line, re.I):
            return None  # not a refusal: nothing to review
        if re.search(r"Too many files|exceed|too large", line, re.I):
            return "size"
        if re.search(r"branch", line, re.I):
            return "skipped-base-branch"
        return "skipped-other:" + line[:60]
    if re.search(r"^> ## Reviews paused", b, re.M):
        return "paused"
    if re.search(r"^> ## Review failed", b, re.M):
        if re.search(r"pull request is closed", b, re.I):
            return None  # closed PR, not a refusal of an open diff
        return "failed"
    return None


def src_refusal_kind(body):
    b = body or ""
    if "used your own review budget" in b:
        return "quota"
    if "larger than the review limit" in b or "unable to review this pull request" in b:
        return "size"
    return None


def classify(path):
    d = json.load(open(path))
    pr = d["pr"]
    ic, rc, rv = d["issue_comments"], d["review_comments"], d["reviews"]
    labels = [l["name"] for l in pr.get("labels", [])]
    r = {
        "repo": d["repo"], "number": pr["number"], "title": pr["title"],
        "createdAt": pr["createdAt"], "state": pr.get("state"), "mergedAt": pr.get("mergedAt"),
        "author": pr["author"]["login"], "labels": labels,
        "skip_label": "skip-bot-review" in labels,
        "opened_in_window": pr["createdAt"] >= LOWER,
        "additions": pr.get("additions"), "deletions": pr.get("deletions"), "changedFiles": pr.get("changedFiles"),
        "baseRefName": pr.get("baseRefName"),
    }
    # ---- pr-agent
    guides = [x for x in ic if x["user"]["login"] == PRA and x["body"].startswith("## PR Reviewer Guide")]
    sugg_ic = [x for x in ic if x["user"]["login"] == PRA and x["body"].startswith("## PR Code Suggestions")]
    other_pra_ic = [x for x in ic if x["user"]["login"] == PRA and x not in guides and x not in sugg_ic]
    sugg_inline = [x for x in rc if x["user"]["login"] == PRA]
    g_recs = []
    for g in guides:
        b = g["body"]
        focus = FOCUS_RE.findall(b)
        sec_canned = "No security concerns identified" in b
        g_recs.append({
            "id": g["id"], "len": len(b), "created_at": g["created_at"], "updated_at": g["updated_at"],
            "canned": ("No major issues detected" in b and sec_canned),
            "focus": [re.sub(r"<.*?>", "", f).strip() for f in focus],
            "security_populated": not sec_canned,
            "updated_until": (UPDATED_RE.search(b).group(1) if UPDATED_RE.search(b) else None),
        })
    r["pra_guides"] = g_recs
    r["pra_present"] = bool(guides)
    r["pra_substantive"] = any(g["focus"] or g["security_populated"] for g in g_recs)
    r["pra_findings"] = sum(len(g["focus"]) for g in g_recs) + sum(1 for g in g_recs if g["security_populated"])
    r["pra_improve_ic"] = [{"id": x["id"], "len": len(x["body"]),
                            "empty": "No code suggestions found" in x["body"]} for x in sugg_ic]
    r["pra_improve_inline"] = [{"id": x["id"], "commit_id": x.get("commit_id"), "path": x.get("path"),
                                "body": x["body"][:400]} for x in sugg_inline]
    r["pra_other_ic"] = [x["body"][:200] for x in other_pra_ic]
    # ---- CodeRabbit
    cr_ic = [x for x in ic if x["user"]["login"] == CR]
    cr_rc = [x for x in rc if x["user"]["login"] == CR]
    cr_rv = [x for x in rv if x["user"]["login"] == CR]
    refusals = collections.Counter()
    summary_reviewed = False
    no_actionable_summary = False
    for x in cr_ic:
        k = cr_refusal_kind(x["body"])
        if k:
            refusals[k] += 1
        b = x["body"] or ""
        if "walkthrough_start" in b or "No actionable comments were generated" in b:
            summary_reviewed = True
        if "No actionable comments were generated" in b:
            no_actionable_summary = True
    actionable = 0
    nit = 0
    for x in cr_rv:
        for m in ACTIONABLE_RE.findall(x["body"] or ""):
            actionable += int(m)
        for m in NITPICK_RE.findall(x["body"] or ""):
            nit += int(m)
    # inline root comments only (not replies) for volume
    cr_inline_roots = [x for x in cr_rc if not x.get("in_reply_to_id")]
    r["cr_inline"] = len(cr_inline_roots)
    r["cr_inline_all"] = len(cr_rc)
    r["cr_reviews"] = len(cr_rv)
    r["cr_reviews_with_body"] = sum(1 for x in cr_rv if (x["body"] or "").strip())
    r["cr_actionable_selfdeclared"] = actionable
    r["cr_nitpick_selfdeclared"] = nit
    r["cr_ic"] = len(cr_ic)
    r["cr_refusals"] = dict(refusals)
    # "reviewed" = produced a review artefact: a review, a root inline comment, or a walkthrough summary
    r["cr_reviewed"] = bool(cr_rv or cr_inline_roots or summary_reviewed)
    r["cr_no_actionable_summary"] = no_actionable_summary
    r["cr_present_any"] = bool(cr_ic or cr_rc or cr_rv)
    r["cr_review_commits"] = sorted({x.get("commit_id") for x in cr_rv if x.get("commit_id")})
    r["cr_actionable_by_commit"] = {}
    for x in cr_rv:
        n = sum(int(m) for m in ACTIONABLE_RE.findall(x["body"] or ""))
        if n:
            r["cr_actionable_by_commit"][x.get("commit_id")] = r["cr_actionable_by_commit"].get(x.get("commit_id"), 0) + n
    # ---- Sourcery
    s_rv = [x for x in rv if x["user"]["login"] == SRC]
    s_ic = [x for x in ic if x["user"]["login"] == SRC]
    s_rc = [x for x in rc if x["user"]["login"] == SRC]
    s_ref = collections.Counter()
    s_reviewed = 0
    s_issue_reviews = 0
    for x in s_rv + s_ic:
        k = src_refusal_kind(x["body"])
        if k:
            s_ref[k] += 1
        elif (x["body"] or "").strip():
            s_reviewed += 1
            m = re.search(r"I've found (\d+)", x["body"] or "")
            if m:
                s_issue_reviews += 1
    r["src_reviews"] = len(s_rv)
    r["src_reviewed"] = bool(s_reviewed or s_rc)
    r["src_refusals"] = dict(s_ref)
    r["src_inline"] = len(s_rc)
    r["src_issue_reviews"] = s_issue_reviews
    # ---- other bots
    others = collections.Counter()
    for k, arr in (("ic", ic), ("rc", rc), ("rv", rv)):
        for x in arr:
            u = x.get("user") or {}
            if u.get("type") == "Bot" and u.get("login") not in KNOWN_BOTS:
                others[u["login"]] += 1
    r["other_bots"] = dict(others)
    # ---- humans / our answers
    r["human_authors"] = sorted({(x.get("user") or {}).get("login") for x in ic + rc + rv
                                 if (x.get("user") or {}).get("type") == "User"})
    r["commits"] = [c["sha"] for c in d.get("commits", [])]
    return r


def automated_kind(r):
    a = r["author"]
    t = r["title"].lower()
    if "dependabot" in a:
        return "dependabot"
    if a in ("cuioss-release-bot[bot]", "app/cuioss-release-bot") or "release-bot" in a:
        return "release-bot"
    if re.search(r"update cui-java-parent|cuioss-organization workflows|chore\(deps\)|bump ", t):
        return "version-bump"
    return None


def main():
    recs = []
    for f in sorted(glob.glob(os.path.join(BASE, "raw", "*.json"))):
        recs.append(classify(f))
    with open(os.path.join(BASE, "classified.json"), "w") as fo:
        json.dump(recs, fo, indent=1)
    print("records", len(recs))


if __name__ == "__main__":
    main()
