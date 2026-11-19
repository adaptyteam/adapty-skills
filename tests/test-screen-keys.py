"""verify-config.py on a screen with a missing required key: a finding, never a CHECKER ERROR.

Repo-only. Runs the shipped script as a subprocess. The flow-schema screen is
`{id, props, caption, elements: {map, hierarchy}, selectableGroups, products}` and the Flow
Builder's screen schema requires `props` (`{}` is valid). A fetched flow can arrive with a screen
that has only `id` and `elements`; the checker used to crash on it (exit 2, `KeyError: 'props'`),
which reads as "the checker is broken" and hides the real fault of the flow.

    FIRES   -- a screen with no `props` (on the footer screen, the second read of `props`)
    FIRES   -- a screen with no `elements`
    FIRES   -- a screen with no `id`
    FIRES   -- a screen whose `elements` has no `map`, or no `hierarchy`
    FIRES   -- a navigate target equal to the position label of a screen with no `id` is dangling
    ALREADY -- under --baseline, the fault of the fetched flow is listed as ALREADY IN
    SILENT  -- every real export in tests/fixtures*
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'verify-config.py')
MSG = 'missing required key(s)'
fails = []


def run(doc, baseline=None):
    with tempfile.TemporaryDirectory() as tmp:
        cp = os.path.join(tmp, 'c.json')
        json.dump(doc, open(cp, 'w'))
        argv = [sys.executable, VERIFY, cp]
        if baseline is not None:
            bp = os.path.join(tmp, 'b.json')
            json.dump(baseline, open(bp, 'w'))
            argv = [sys.executable, VERIFY, '--baseline', bp, cp]
        r = subprocess.run(argv, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr


def check(name, ok, detail=''):
    print(('  ok    ' if ok else '  FAIL  ') + name + ('' if ok else f'  {detail[:600]}'))
    if not ok:
        fails.append(name)


BASE = json.load(open(os.path.join(ROOT, 'tests', 'fixtures', 'onboarding-permission-primer.json')))
CFG = BASE.get('config', BASE)


def footer_screen(doc):
    cfg = doc.get('config', doc)
    return next(s for s in cfg['screens']
                if any(e.get('type') == 'footer' for e in s['elements']['map'].values()))


def without(key):
    doc = copy.deepcopy(BASE)
    scr = footer_screen(doc)
    sid = scr.get('id')
    if key.startswith('elements.'):
        scr['elements'].pop(key.split('.', 1)[1])
    else:
        scr.pop(key)
    return doc, sid


for key in ('props', 'elements', 'id', 'elements.map', 'elements.hierarchy'):
    doc, sid = without(key)
    code, out = run(doc)
    line = next((ln for ln in out.splitlines() if MSG in ln), '')
    check(f'FIRES: a screen with no `{key}` gives exit 1, not a CHECKER ERROR',
          code == 1 and 'CHECKER ERROR' not in out, out)
    check(f'FIRES: the ERROR names the missing `{key}`', 'ERROR:' in line and repr(key) in line, out)
    if key != 'id':
        check(f'FIRES: the ERROR names the screen {sid}', sid in line, out)

    code, out = run(doc, baseline=doc)
    check(f'ALREADY IN: --baseline lists the fetched flow\'s screen with no `{key}` apart',
          code == 0 and 'already (error):' in out and MSG in out and 'CHECKER ERROR' not in out, out)

# A screen with no `id` gets no stand-in id: a navigate target `"#1"` names no screen of the input,
# so it stays dangling.
doc = copy.deepcopy(BASE)
cfg = doc.get('config', doc)
cfg['screens'][0].pop('id')
old = cfg['screens'][1]['id']
target = cfg['screens'][2]['id']  # navigated to from a named screen; the unnamed one is not read
code, out = run(json.loads(json.dumps(doc).replace(f'"screen": "{target}"', '"screen": "#1"')))
line = next((ln for ln in out.splitlines() if 'dangling navigate targets' in ln), '')
check('FIRES: a navigate target "#1" with the first screen unnamed is dangling',
      code == 1 and "'#1'" in line, out)

# ...and no finding of the unnamed screen prints as a real screen's: screen B has the real id "#1",
# the fetched flow has a hierarchy-ref fault on the unnamed screen A, and the edit adds the same
# fault to B. The draft's fault is new.
def hier_fault(cfg, i):
    cfg['screens'][i]['elements']['hierarchy'].setdefault('children', []).append({'id': 'absent'})

fetched = json.loads(json.dumps(BASE).replace(f'"{old}"', '"#1"'))
cfg = fetched.get('config', fetched)
cfg['screens'][0].pop('id')
hier_fault(cfg, 0)
draft = copy.deepcopy(fetched)
hier_fault(draft.get('config', draft), 1)
code, out = run(draft, baseline=fetched)
check('FIRES: a fault added to the screen "#1" is new against a baseline whose unnamed screen '
      'is first', code == 1 and any('ERROR:' in ln and 'absent' in ln for ln in out.splitlines()),
      out)

for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    code, out = run(json.load(open(f)))
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}',
          code != 2 and not any(MSG in ln and 'screen element' not in ln
                                for ln in out.splitlines()), out[:300])

print(f'\n{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
