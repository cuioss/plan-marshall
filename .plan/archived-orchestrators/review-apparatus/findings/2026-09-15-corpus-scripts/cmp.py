import json,sys,collections,re
toon, raw = sys.argv[1], sys.argv[2]
lines=open(toon).read().splitlines()
print([l for l in lines[:6]])
c=collections.Counter()
for l in lines:
    if l.startswith('  ') and '\t' in l:
        parts=l.strip().split('\t')
        c[(parts[0],parts[3])]+=1
print('ci:',sorted(c.items()), sum(c.values()))
d=json.load(open(raw))
g=collections.Counter()
for k,kind in (('issue_comments','issue_comment'),('review_comments','inline'),('reviews','review_body')):
    for x in d[k]:
        if k=='reviews' and not (x['body'] or '').strip(): continue
        g[(kind,x['user']['login'].replace('[bot]',''))]+=1
print('gh :',sorted(g.items()), sum(g.values()))
