#!/usr/bin/env python3
"""Calibration for verify-config.py's spread-stack warning.

A space-between/-around/-evenly stack gets a spacer between its children unless every child
fills the main axis; on iOS a fill child is then only as flexible as each spacer, so it gets an
equal share of the free space and its text truncates. Android and the builder give it the rest.

    FIRES   -- a space-between row with one fill child beside hug ones
    SILENT  -- the same row with every child fill, or with a gap distribution
            -- all real exports

Usage: python3 tests/test-spread-fill.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'verify-config.py')
FLOW = os.path.join(ROOT, 'tests', 'fixtures', 'tabs-paywall.json')
ROW = 'el_RvS101'          # a space-between row of three hug children in the real export
NEEDLE = 'stack with a fill'
fails = []


def check(name, cond, detail=''):
    print(f'  {"ok   " if cond else "FAIL "} {name}')
    if not cond:
        fails.append(f'{name} {detail}'.strip())


def hits(doc):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        r = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if 'Traceback' in r.stderr:
        raise AssertionError(r.stderr)
    return [l for l in r.stdout.splitlines() if NEEDLE in l]


def row(doc):
    c = doc.get('config', doc)
    for s in c['screens']:
        if ROW in s['elements']['map']:
            def find(n):
                if n.get('id') == ROW:
                    return n
                for x in n.get('children') or []:
                    got = find(x)
                    if got:
                        return got
            return s['elements']['map'], find(s['elements']['hierarchy'])
    raise AssertionError('fixture lost its space-between row; pick another')


base = json.load(open(FLOW))
m, n = row(base)
check('fixture setup: the row is space-between with hug children',
      m[ROW]['props']['layout']['distribution']['type'] == 'space-between'
      and all(m[c['id']]['props']['width']['type'] == 'hug' for c in n['children']))

one = copy.deepcopy(base)
m, n = row(one)
m[n['children'][1]['id']]['props']['width'] = {'type': 'fill'}
got = hits(one)
check('FIRES on one fill child beside hug ones, naming the stack', len(got) == 1 and ROW in got[0], got)

every = copy.deepcopy(base)
m, n = row(every)
for c in n['children']:
    m[c['id']]['props']['width'] = {'type': 'fill'}
check('SILENT when every child fills', not hits(every))

gap = copy.deepcopy(one)
m, _ = row(gap)
m[ROW]['props']['layout']['distribution'] = {'type': 'gap', 'gap': 8}
check('SILENT with a gap distribution', not hits(gap))

corpus = sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json')))
noisy = [os.path.basename(p) for p in corpus if hits(json.load(open(p)))]
check(f'SILENT on all {len(corpus)} real exports', not noisy, noisy)

print()
if fails:
    print(f'{len(fails)} FAILED:')
    for f in fails:
        print(f'  - {f}')
    sys.exit(1)
print('all passed')
