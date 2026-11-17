"""verify-config.py's relative-zIndex check, both directions, and flowkit.relative()'s guard.

Repo-only. Runs the shipped script as a subprocess. Built on the real timeline export
(`timeline-anchored.json`): each row holds absolute rail and chip elements and one relative text
column, so a zIndex on the text column is the field-report shape, a relative element raised over
an absolute sibling. In the preview render the absolute sibling still paints over it.
"""
import copy, glob, importlib.util, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
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
MSG = 'zIndex on a relative element does nothing'

def screen(c):
    return c['screens'][0]['elements']

def first_row(c):
    return screen(c)['hierarchy']['children'][0]['children'][0]

def raised_text(c, pos=None):
    m = screen(c)['map']
    row = first_row(c)
    text = [x['id'] for x in row['children']
            if m[x['id']]['props'].get('position', {}).get('type') == 'relative'][0]
    m[text]['props']['position'] = pos or {'type': 'relative', 'zIndex': 10}
    return c, text

c, text = raised_text(copy.deepcopy(BASE))
out = run(c)
check('FIRES: relative zIndex beside absolute siblings', out.count(MSG) == 1, out[:300])
check('FIRES: names the element', text in out, out[:300])
check('FIRES: names the absolute sibling that paints over it', 'paints over it' in out, out[:300])

c, _ = raised_text(copy.deepcopy(BASE))
m = screen(c)['map']
for x in first_row(c)['children']:
    if m[x['id']]['props'].get('position', {}).get('type') == 'absolute':
        m[x['id']]['props']['position'] = {'type': 'relative'}
out = run(c)
check('FIRES: relative zIndex with no absolute sibling, without the sibling clause',
      MSG in out and 'paints over it' not in out, out[:300])

c, _ = raised_text(copy.deepcopy(BASE))
m = screen(c)['map']
for x in first_row(c)['children']:
    p = m[x['id']]['props'].get('position', {})
    if p.get('type') == 'absolute':
        p['zIndex'] = -10
out = run(c)
check('FIRES: absolute siblings at a negative zIndex get no sibling clause',
      MSG in out and 'paints over it' not in out, out[:300])

c, _ = raised_text(copy.deepcopy(BASE), {'type': 'absolute', 'top': 0, 'left': 40, 'zIndex': 10})
check('SILENT: the fix — the element made absolute', MSG not in run(c))

for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    out = run(json.load(open(f)))
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}', MSG not in out, out[:200])

spec = importlib.util.spec_from_file_location('flowkit', os.path.join(REFS, 'flowkit.py'))
fk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fk)
check('flowkit.relative() still emits the plain position', fk.relative() == {'type': 'relative'})
try:
    fk.relative(z=10)
    check('flowkit.relative(z=10) raises', False, 'returned without raising')
except ValueError as e:
    check('flowkit.relative(z=10) raises, pointing at absolute()', 'absolute()' in str(e), str(e))

print(f'\n{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
