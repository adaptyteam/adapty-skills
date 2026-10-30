#!/usr/bin/env python3
"""`verify-config.py --baseline`: a finding the fetched flow already had is listed apart and does
not fail the run; a finding this edit adds still does.

Repo-only. Runs the shipped script as a subprocess -- never imports it, so nothing writes a
`__pycache__` into `references/`.

Why. Three runs editing one fetched flow read that flow's own elements without `states` as their
defect, and the run failed for something the edit never touched. The skill's rule for a blocker
already in the fetched flow is to name it and work around it, never to fix it unasked; the local
walk now says which findings those are.

    ALREADY  -- the baseline's own finding, under ALREADY IN, exit 0
    NEW      -- a finding the draft adds, as an ERROR, exit 1, beside the old one
    PLAIN    -- without --baseline nothing changes

Usage: python3 tests/test-structure-baseline.py     # 0 all pass, 1 a case regressed
"""
import copy, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'verify-config.py')
FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'reviews-carousel.json')
STATES = 'has no `states` key'
fails = []


def run(draft, baseline=None):
    with tempfile.TemporaryDirectory() as tmp:
        dp, bp = os.path.join(tmp, 'draft.json'), os.path.join(tmp, 'flow.backup.json')
        json.dump(draft, open(dp, 'w'))
        argv = [sys.executable, VERIFY, dp]
        if baseline is not None:
            json.dump(baseline, open(bp, 'w'))
            argv = [sys.executable, VERIFY, '--baseline', bp, dp]
        r = subprocess.run(argv, capture_output=True, text=True)
    if r.returncode == 2 or 'Traceback' in r.stderr:
        raise AssertionError(f'verify-config.py crashed:\n{r.stdout}{r.stderr}')
    lines = r.stdout.splitlines()
    return (r.returncode, [l for l in lines if 'ERROR:' in l], [l for l in lines if 'already (' in l],
            r.stdout)


def check(name, ok, detail=''):
    print(f'  {"ok  " if ok else "FAIL"}  {name}')
    if not ok:
        fails.append(f'{name}: {detail[:700]}')


def strip_states(doc, n):
    """`doc` with the first `n` stack elements of its first screen missing `states`."""
    m = doc['screens'][0]['elements']['map']
    for e in [e for e in m.values() if e['type'] == 'stack'][:n]:
        e.pop('states', None)
    return doc


raw = json.load(open(FIXTURE))
base = strip_states(copy.deepcopy(raw), 1)
draft = copy.deepcopy(base)
draft['screens'][0]['caption'] = 'Reviews (edited)'     # the edit: nothing the checker reads

rc, errs, old, out = run(draft, base)
check('ALREADY: the fetched flow\'s own missing `states` is listed apart, exit 0',
      rc == 0 and not errs and any(STATES in l for l in old) and 'ALREADY IN flow.backup.json' in out
      and 'do not block this edit' in out, out)

rc, errs, old, out = run(strip_states(copy.deepcopy(base), 2), base)
check('NEW: a second element losing `states` in this edit is an ERROR, exit 1',
      rc == 1 and any(STATES in l for l in errs) and any(STATES in l for l in old), out)

rc, errs, old, out = run(draft)
check('PLAIN: without --baseline the same finding is an ERROR, as before',
      rc == 1 and any(STATES in l for l in errs) and not old, out)

rc, errs, old, out = run(copy.deepcopy(raw), base)
check('a draft that FIXED the old finding reports nothing at all',
      rc == 0 and not errs and not old, out)

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
