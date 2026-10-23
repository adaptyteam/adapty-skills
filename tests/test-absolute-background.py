"""verify-config.py's screen-sized absolute image check, both directions.

Repo-only. Runs the shipped script as a subprocess. Built on the real VPN timer export, whose hero
is an absolute image 242pt wide with a hug height: that one must stay silent. Growing it to a
full-screen background, or past the screen's width, must fire.
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

BASE = json.load(open(os.path.join(ROOT, 'tests', 'fixtures', 'vpn-timer-draft.json')))
BASE = BASE.get('config', BASE)
MSG = 'takes their taps'

def hero(c):
    for s in c['screens']:
        for e in s['elements']['map'].values():
            if e.get('type') == 'image' and e['props'].get('position', {}).get('type') == 'absolute':
                return e['props']
    raise RuntimeError('no absolute image in the fixture')

check('SILENT: the export as it is (242pt hero, hug height)', MSG not in run(BASE))

full = copy.deepcopy(BASE)
hero(full).update(width={'type': 'fill'}, height={'type': 'fill'})
out = run(full)
check('FIRES: fill x fill absolute image', MSG in out, out[:300])
check('POINTS AT the screen fill for an image', "screen's `fill`" in out, out[:300])

wide = copy.deepcopy(BASE)
hero(wide)['width'] = {'type': 'fixed', 'value': 520}
out = run(wide)
check('FIRES: wider than the screen, whatever the height', 'widens the screen' in out, out[:300])

fixed = copy.deepcopy(full)
hero(fixed)['position']['type'] = 'fixed'
check('FIRES: the same background positioned fixed', MSG in run(fixed))

flow = copy.deepcopy(full)
hero(flow)['position'] = {'type': 'relative'}
check('SILENT: the same box in flow', MSG not in run(flow))

for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    out = run(json.load(open(f)))
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}', MSG not in out, out[:200])

print(f'\n{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
