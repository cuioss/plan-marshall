import json, sys, os, re, glob

ROOTS = sys.argv[1:]
KILL = re.compile(r'\b(pkill|killall|kill\s+-|kill\s+%|kill\s+\d|xargs\s+kill)', re.I)

rows = []
for root in ROOTS:
    for path in glob.glob(os.path.join(root, '**', '*.jsonl'), recursive=True):
        try:
            with open(path, errors='replace') as f:
                for ln, line in enumerate(f, 1):
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
                    items = content if isinstance(content, list) else []
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        if it.get('type') == 'tool_use' and it.get('name') == 'Bash':
                            inp = it.get('input') or {}
                            cmd = inp.get('command', '')
                            bg = inp.get('run_in_background', False)
                            desc = inp.get('description', '')
                            if KILL.search(cmd):
                                rows.append(('KILL', ts, path, ln, cmd, desc, bg))
                            elif bg:
                                rows.append(('BG', ts, path, ln, cmd, desc, bg))
                        if it.get('type') == 'tool_result':
                            c = it.get('content')
                            txt = ''
                            if isinstance(c, str):
                                txt = c
                            elif isinstance(c, list):
                                txt = ' '.join(x.get('text', '') for x in c if isinstance(x, dict))
                            if re.search(r'was stopped|Background command .* stopped|killed|Killed', txt):
                                rows.append(('STOP', ts, path, ln, txt[:400], '', False))
                    if isinstance(content, str) and re.search(r'was stopped', content):
                        rows.append(('STOPTXT', ts, path, ln, content[:400], '', False))
        except Exception as e:
            print('ERR', path, e, file=sys.stderr)

rows.sort(key=lambda r: r[1])
for kind, ts, path, ln, cmd, desc, bg in rows:
    print(f'{kind}\t{ts}\t{os.path.basename(path)}:{ln}\tbg={bg}\tdesc={desc!r}\tcmd={cmd!r}')
