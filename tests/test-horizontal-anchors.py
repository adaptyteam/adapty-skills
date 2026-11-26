"""An element anchored left AND right stretches between the anchors only with width `auto`.

Repo-only. Runs the shipped `verify-config.py` as a subprocess, and `flowkit._width()` in process.
Built on the real export `onboarding-multilocale.json`, whose docked buttons are `fixed`, anchored left
and right, with width `auto`: the form every real export uses. The transformer lets the anchors set the
width only for `auto`; an element that already has a width keeps it and starts at `left`, so the right
anchor pins nothing and a wide element draws past the right edge.
"""
import copy, glob, importlib.util, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
sys.path.insert(0, REFS)
spec = importlib.util.spec_from_file_location('flowkit', os.path.join(REFS, 'flowkit.py'))
fk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fk)
fails = []
MSG = 'anchored left+right'


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


BASE = json.load(open(os.path.join(ROOT, 'tests', 'fixtures', 'onboarding-multilocale.json')))
BASE = BASE.get('config', BASE)


def anchored(c):
    return [e for s in c['screens'] for e in s['elements']['map'].values()
            if isinstance((e.get('props') or {}).get('position'), dict)
            and e['props']['position'].get('left') is not None
            and e['props']['position'].get('right') is not None]


check('the fixture still carries elements anchored left and right', len(anchored(BASE)) >= 1)
check('SILENT: anchored left+right with width auto', MSG not in run(BASE))

for kind, width in (('fixed', {'type': 'fixed', 'value': 420}), ('fill', {'type': 'fill'})):
    for ptype in ('fixed', 'absolute'):
        doc = copy.deepcopy(BASE)
        el = anchored(doc)[0]
        el['props']['width'] = width
        el['props']['position']['type'] = ptype
        out = run(doc)
        check(f'FIRES: {ptype} position, anchored left+right, width {kind}', out.count(MSG) == 1, out[:300])
check('the warning names auto as the stretching width', '`auto`' in out, out[:300])

for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    out = run(json.load(open(f)))
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}', MSG not in out, out[:200])

# flowkit refuses the fixed width as it refuses fill, and still takes the other forms
pos = fk.absolute(left=16, right=16, bottom=24)
for label, fn in (('fill', lambda: fk.stack([], width='fill', position=pos)),
                  ('fixed_w', lambda: fk.stack([], fixed_w=300, position=pos))):
    try:
        fn()
        check(f'flowkit refuses {label} on an element anchored left and right', False, 'no error')
    except ValueError as e:
        check(f'flowkit refuses {label} on an element anchored left and right', "width='auto'" in str(e), str(e))
check('flowkit defaults such an element to auto',
      fk.stack([], position=pos)['props']['width'].get('type') == 'auto')
check('flowkit takes fixed_w with one horizontal anchor',
      fk.stack([], fixed_w=300, position=fk.absolute(left=16, bottom=24))['props']['width'].get('type') == 'fixed')

print(f'\n{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
