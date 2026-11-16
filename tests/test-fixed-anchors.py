"""verify-config.py's anchored-height check on a `fixed` element, both directions.

Repo-only. Runs the shipped script as a subprocess. Built on the real timeline export
(`timeline-anchored.json`), whose rails are `absolute`, anchored top and bottom, with height
`auto`: the one form that stretches. The transformer treats a `fixed` element anchored the same
way differently: it stretches only the wrapper and gives the element no height for `auto`, so
the element hugs its content.
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
MSG = 'fixed and anchored top+bottom'
OLD = 'without an absolute top+bottom'

def rails(c):
    return [e for e in c['screens'][0]['elements']['map'].values()
            if e.get('caption') == 'Connector']

check('the fixture still carries anchored rails', len(rails(BASE)) == 2)
check('SILENT: absolute rails anchored top+bottom with height auto', MSG not in run(BASE))

fixed = copy.deepcopy(BASE)
for e in rails(fixed):
    e['props']['position']['type'] = 'fixed'
out = run(fixed)
check('FIRES: fixed rails anchored top+bottom with height auto', out.count(MSG) == 2, out[:300])
check('names fill as the stretching height', '`fill` height' in out, out[:300])
check('no second, contradictory warning on the same element', OLD not in out, out[:300])

filled = copy.deepcopy(fixed)
for e in rails(filled):
    e['props']['height'] = {'type': 'fill'}
check('SILENT: fixed rails anchored top+bottom with height fill', MSG not in run(filled))

for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    out = run(json.load(open(f)))
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}', MSG not in out, out[:200])

print(f'\n{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
