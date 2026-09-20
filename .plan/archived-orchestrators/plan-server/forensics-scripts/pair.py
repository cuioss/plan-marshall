import json, sys, os, re, glob
from datetime import datetime

ROOTS = sys.argv[1:]
launches = {}   # tool_use_id -> (ts, session, cmd, desc)
kills = []      # (ts, session, tool_use_id, taskid, summary)

def parse(ts):
    return datetime.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S')

for root in ROOTS:
    for path in glob.glob(os.path.join(root, '**', '*.jsonl'), recursive=True):
        sess = os.path.basename(path).replace('.jsonl', '')
        try:
            for line in open(path, errors='replace'):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                ts = d.get('timestamp', '')
                msg = d.get('message') or {}
                content = msg.get('content')
                if isinstance(content, list):
                    for it in content:
                        if isinstance(it, dict) and it.get('type') == 'tool_use' and it.get('name') == 'Bash':
                            inp = it.get('input') or {}
                            if inp.get('run_in_background'):
                                launches[it['id']] = (ts, sess, inp.get('command', ''), inp.get('description', ''))
                txt = ''
                if isinstance(content, str):
                    txt = content
                elif isinstance(content, list):
                    txt = ' '.join(x.get('text', '') for x in content if isinstance(x, dict) and x.get('type') == 'text')
                if '<status>killed</status>' in txt or 'was stopped' in txt:
                    m = re.search(r'<tool-use-id>([^<]+)</tool-use-id>', txt)
                    t = re.search(r'<task-id>([^<]+)</task-id>', txt)
                    s = re.search(r'<summary>([^<]*)</summary>', txt)
                    st = re.search(r'<status>([^<]*)</status>', txt)
                    if m:
                        kills.append((ts, sess, m.group(1), t.group(1) if t else '', (s.group(1) if s else '')[:70], st.group(1) if st else ''))
        except Exception as e:
            print('ERR', path, e, file=sys.stderr)

kills.sort()
print(f'{"KILL_TS":24} {"ELAPSED_S":>9}  {"SESSION":10} {"STATUS":8} SUMMARY / CMD')
for ts, sess, tuid, tid, summ, st in kills:
    if tuid in launches:
        lts, lsess, cmd, desc = launches[tuid]
        el = (parse(ts) - parse(lts)).total_seconds()
        print(f'{ts:24} {el:9.0f}  {sess[:8]:10} {st:8} {summ}')
        print(f'{"":24} {"start=" + lts[11:19]:>9}  cmd={cmd[:110]}')
    else:
        print(f'{ts:24} {"?":>9}  {sess[:8]:10} {st:8} {summ} [launch NOT FOUND]')
