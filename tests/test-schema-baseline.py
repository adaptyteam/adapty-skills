#!/usr/bin/env python3
"""The schema step's --baseline must match findings by screen ID, not by screen position.

Repo-only. Runs the shipped `validate-with-schema.mjs` from the ajv cache dir, the way `gates.sh`
does, and skips if ajv is not installed there.

Inserting a screen in front of an existing one shifts that screen's index, so a positional
baseline reports the screen's OLD findings as new — measured in live runs, where two agents on
an add-a-screen task each spent a run proving the "new" findings were pre-existing.

    SILENT  -- a pre-existing finding on a screen that moved from index 0 to index 1
    FIRES   -- a genuinely new finding on the inserted screen

Usage: python3 tests/test-schema-baseline.py    # 0 all pass, 1 a case regressed
"""
import copy, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATOR = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'validate-with-schema.mjs')
AJV_DIR = os.path.expanduser(os.environ.get('AJV_DIR', '~/.cache/adapty-flow-schema'))
FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'reviews-carousel.json')

if not os.path.isdir(os.path.join(AJV_DIR, 'node_modules', 'ajv')):
    print(f'SKIP  no ajv in {AJV_DIR}')
    sys.exit(0)

fails = []


def run(config, baseline):
    with tempfile.TemporaryDirectory() as tmp:
        cp, bp = os.path.join(tmp, 'c.json'), os.path.join(tmp, 'b.json')
        json.dump(config, open(cp, 'w'))
        json.dump(baseline, open(bp, 'w'))
        r = subprocess.run(['node', VALIDATOR, '--config', cp, '--baseline', bp],
                           cwd=AJV_DIR, capture_output=True, text=True, timeout=120)
        if r.returncode == 2:
            print(f'SKIP  validator unavailable: {(r.stdout + r.stderr).strip()[:200]}')
            sys.exit(0)
        return r.returncode, r.stdout + r.stderr


def check(name, ok, detail=''):
    print(f'  {"ok  " if ok else "FAIL"}  {name}')
    if not ok:
        fails.append(f'{name}: {detail[:600]}')


base = json.load(open(FIXTURE))
# A finding the baseline already has: a pre-v12 border `style` on the existing screen.
el = next(e for e in base['screens'][0]['elements']['map'].values() if e['type'] == 'stack')
el.setdefault('props', {})['border'] = {'color': {'type': 'color-style', 'colorId': 'white'},
                                       'style': 'solid', 'width': 1}

inserted = {'id': 'scr_inserted', 'props': {},
            'elements': {'map': {'el_new': {'id': 'el_new', 'type': 'stack', 'states': [],
                                            'props': {}}},
                         'hierarchy': {'id': 'root', 'children': [{'id': 'el_new'}]}}}

moved = copy.deepcopy(base)
moved['screens'].insert(0, copy.deepcopy(inserted))
code, out = run(moved, base)
check('a pre-existing finding on a screen that moved down is not reported as new', code == 0, out)

broken = copy.deepcopy(moved)
broken['screens'][0]['elements']['map']['el_new']['props']['border'] = {
    'color': {'type': 'color-style', 'colorId': 'white'}, 'style': 'solid', 'width': 1}
code, out = run(broken, base)
check('a new finding on the inserted screen is reported', code == 1 and 'el_new' in out, out)
check('...and only that one, not the moved screen\'s old finding',
      code == 1 and '1 location(s) new' in out, out)

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
