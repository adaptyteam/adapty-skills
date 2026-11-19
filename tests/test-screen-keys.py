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
    FIRES   -- an unnamed entry screen with no navigation leaves the named screens unreachable
    FIRES   -- under --baseline, a new fault inside the fetched flow's unnamed screen is new
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

# A screen with no `id` is read under its label, `with no id (position N)`, but a navigate target
# resolves only to a real id: a target equal to the label is dangling and adds no edge, so the
# unnamed third screen (reached only through that target) and the screen after it are unreachable.
old = BASE.get('config', BASE)['screens'][1]['id']
doc = copy.deepcopy(BASE)
cfg = doc.get('config', doc)
third = cfg['screens'][2].pop('id')
after = [s['id'] for s in cfg['screens'][3:]]
label = 'with no id (position 3)'
code, out = run(json.loads(json.dumps(doc).replace(f'"screen": "{third}"', f'"screen": "{label}"')))
line = next((ln for ln in out.splitlines() if 'dangling navigate targets' in ln), '')
check(f'FIRES: a navigate target {label!r} (the label of an unnamed screen) is dangling',
      code == 1 and repr(label) in line, out)
line = next((ln for ln in out.splitlines() if 'unreachable from screens[0]' in ln), '')
check('FIRES: ...and it adds no edge: the unnamed screen and the screens after it are unreachable',
      all(repr(x) in line for x in [label] + after), out)

# ...and no finding of the unnamed screen prints as a real screen's: screen B has a real id ("#1",
# or the very label the unnamed screen would get), the fetched flow has a hierarchy-ref fault on
# the unnamed screen A, and the edit adds the same fault to B. The draft's fault is new: the label
# is made unlike every real id of the draft and of the baseline.
def hier_fault(cfg, i):
    cfg['screens'][i]['elements']['hierarchy'].setdefault('children', []).append({'id': 'absent'})

for real in ('#1', 'with no id (position 1)'):
    fetched = json.loads(json.dumps(BASE).replace(f'"{old}"', json.dumps(real)))
    cfg = fetched.get('config', fetched)
    cfg['screens'][0].pop('id')
    hier_fault(cfg, 0)
    draft = copy.deepcopy(fetched)
    hier_fault(draft.get('config', draft), 1)
    code, out = run(draft, baseline=fetched)
    check(f'FIRES: a fault added to the screen {real!r} is new against a baseline whose unnamed '
          f'screen is first',
          code == 1 and any('ERROR:' in ln and 'absent' in ln for ln in out.splitlines()), out)

# The real id is only in the draft: the fetched flow's unnamed first screen has the fault; the edit
# gives that screen its real id and fixes it, and gives the fault to the second screen, whose real
# id is `with no id (position 1)`. That error is new.
real = 'with no id (position 1)'
fetched = copy.deepcopy(BASE)
cfg = fetched.get('config', fetched)
cfg['screens'][0].pop('id')
hier_fault(cfg, 0)
draft = json.loads(json.dumps(BASE).replace(f'"{old}"', json.dumps(real)))
hier_fault(draft.get('config', draft), 1)
code, out = run(draft, baseline=fetched)
check(f'FIRES: a fault on the draft\'s screen {real!r} is new against a baseline whose unnamed '
      f'first screen had it',
      code == 1 and any('ERROR:' in ln and 'absent' in ln and real in ln
                        for ln in out.splitlines()), out)

# The unnamed screen keeps its place: as screens[0] it is the entry, and with no navigation of its
# own every named screen after it is unreachable.
doc = copy.deepcopy(BASE)
cfg = doc.get('config', doc)
cfg['screens'][0] = {'props': {}, 'elements': {'map': {}, 'hierarchy': {'id': 'root', 'children': []}}}
named = [s['id'] for s in cfg['screens'][1:]]
code, out = run(doc)
line = next((ln for ln in out.splitlines() if 'unreachable from screens[0]' in ln), '')
check('FIRES: an unnamed entry screen with no navigation leaves every named screen unreachable',
      all(repr(x) in line for x in named), out)

# The unnamed screen is still read: under --baseline its missing id is ALREADY IN, and a fault the
# edit adds inside it is new.
fetched = copy.deepcopy(BASE)
fetched.get('config', fetched)['screens'][0].pop('id')
draft = copy.deepcopy(fetched)
hier_fault(draft.get('config', draft), 0)
code, out = run(draft, baseline=fetched)
check('FIRES: a fault added inside the fetched flow\'s unnamed screen is new under --baseline',
      code == 1 and any('ERROR:' in ln and 'absent' in ln for ln in out.splitlines()), out)

for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    code, out = run(json.load(open(f)))
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}',
          code != 2 and not any(MSG in ln and 'screen element' not in ln
                                for ln in out.splitlines()), out[:300])

print(f'\n{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
