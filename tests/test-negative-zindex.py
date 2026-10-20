"""verify-config.py's negative-zIndex check, both directions.

Repo-only. Runs the shipped script as a subprocess. Built on the real timeline export
(`timeline-anchored.json`), whose rails carry `zIndex: -10` and draw because no ancestor of the
rail has a fill. Putting a fill on the list container hides every rail in the preview render.
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'verify-config.py')
fails = []

def run(doc):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(doc, f)
    r = subprocess.run([sys.executable, VERIFY, f.name], capture_output=True, text=True)
    os.unlink(f.name)
    if r.returncode == 2:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout

def check(name, ok, detail=''):
    print(('  ok    ' if ok else '  FAIL  ') + name + ('' if ok else f'  {detail}'))
    if not ok:
        fails.append(name)

BASE = json.load(open(os.path.join(ROOT, 'tests', 'fixtures', 'timeline-anchored.json')))
BASE = BASE.get('config', BASE)
LIST = 'el_miDCuM5HE8'  # the stack holding the timeline rows
CARD = [{'type': 'color', 'color': {'type': 'hex', 'hex': '#EDE7FF', 'opacity': 100}}]
MSG = 'negative zIndex inside'

def screen(c):
    return c['screens'][0]['elements']

def carded():
    c = copy.deepcopy(BASE)
    screen(c)['map'][LIST]['props']['fill'] = CARD
    return c

def rail_first_no_z(c):
    m = screen(c)['map']
    for e in m.values():
        if e.get('caption') == 'Connector':
            e['props']['position'].pop('zIndex', None)
    for row in screen(c)['hierarchy']['children'][0]['children']:
        ch = row.get('children') or []
        rails = [x for x in ch if m[x['id']].get('caption') == 'Connector']
        row['children'] = rails + [x for x in ch if x not in rails]
    return c

out = run(carded())
check('FIRES: rails at zIndex -10 inside a filled card', out.count(MSG) == 2, out[:300])
check('FIRES: names the filled ancestor', LIST in out, out[:300])
check('SILENT: the fix — rail first, no zIndex, same card', MSG not in run(rail_first_no_z(carded())))

deep = carded()
m = screen(deep)['map']
m[LIST]['props'].pop('fill')
row = screen(deep)['hierarchy']['children'][0]['children'][0]['id']
m[row]['props']['fill'] = CARD
check('FIRES: the filled ancestor is the row itself', MSG in run(deep))

for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    out = run(json.load(open(f)))
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}', MSG not in out, out[:200])

print(f'\n{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
