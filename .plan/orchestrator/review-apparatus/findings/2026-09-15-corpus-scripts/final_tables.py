import json,collections,re
R=json.load(open('classified.json')); S=json.load(open('scoring.json'))
POP=[r for r in R if not r['skip_label'] and r['opened_in_window']]
REPOS=['plan-marshall','cui-http','TokenSheriff','API-Sheriff']
print('CR refused-only by kind')
for r in POP:
    if not r['cr_reviewed'] and r['cr_refusals']: pass
print(collections.Counter((r['repo'],tuple(sorted(r['cr_refusals']))) for r in POP if not r['cr_reviewed'] and r['cr_refusals']))
print('CR paused PRs',[(r['repo'],r['number']) for r in POP if 'paused' in r['cr_refusals']])
print('Sourcery per repo', {repo: dict(collections.Counter(k for r in POP if r['repo']==repo for k in r['src_refusals'])) for repo in REPOS})
print('Sourcery reviews per repo', {repo: (sum(r['src_reviews'] for r in POP if r['repo']==repo), sum(r['src_inline'] for r in POP if r['repo']==repo), sum(r['src_issue_reviews']>0 for r in POP if r['repo']==repo)) for repo in REPOS})
print('pra guides per repo', {repo:(sum(len(r['pra_guides']) for r in POP if r['repo']==repo), sum(r['pra_substantive'] for r in POP if r['repo']==repo)) for repo in REPOS})
print('marker per repo', {repo:sum(1 for r in POP if r['repo']==repo for g in r['pra_guides'] if g['updated_until']) for repo in REPOS})
print('guide len by repo', {repo:sorted(collections.Counter(g['len'] for r in POP if r['repo']==repo for g in r['pra_guides']).items()) for repo in REPOS})
# appendix
def cro(r):
    if r['cr_reviewed']: return 'reviewed'+('+ref' if r['cr_refusals'] else '')
    if r['cr_refusals']: return 'REFUSED:'+','.join(sorted(r['cr_refusals']))
    return '—'
def sro(r):
    if r['src_reviewed']: return 'reviewed'+('+ref' if r['src_refusals'] else '')
    if r['src_refusals']: return 'REFUSED:'+','.join(sorted(r['src_refusals']))
    return '—'
rows=[]
for r in sorted(POP,key=lambda r:(REPOS.index(r['repo']),r['number'])):
    s=S[f"{r['repo']}#{r['number']}"]['outcome']
    s={'excluded-by-design (dependabot org skip rule)':'n/a dependabot','NO-RESULT (check trigger)':'never-triggered'}.get(s,s)
    t=re.sub(r'\|','/',r['title'])[:48]
    imp=''
    if r['pra_improve_inline']: imp=f" +improve:{len(r['pra_improve_inline'])}"
    rows.append(f"| {r['repo']} | {r['number']} | {t} | {r['createdAt'][:10]} | {r['state'][0]} | {s}{imp} | {cro(r)} | {sro(r)} | {'y' if r['pra_substantive'] else 'n' if r['pra_present'] else '—'} | {r['cr_actionable_selfdeclared']} |")
open('appendix.md','w').write('\n'.join(rows))
print(len(rows))
