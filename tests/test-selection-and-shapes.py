#!/usr/bin/env python3
"""verify-config.py's group-default, rich-text variable and mixed-font checks, both directions.

Repo-only. Runs the shipped script as a subprocess on mutated copies of the real exports, so each
case is a real document one edit away from the defect.

    FIRES   -- a product group with no default (warning); a tab group with no default
               (warning); a quiz group with no default whose selection a text reads (warning);
               a rich-text variable node with `variableId` beside `attrs` (error); a font with
               a preset and a family (warning)
    SILENT  -- every tracked export; a quiz group with no default that only a condition reads
               (the corpus's own shape); the same text read with one option marked default; a
               state font of a preset plus a weight (trap 17's shape)
    FLOWKIT -- on_selected() refuses a font with a preset and a family

Usage: python3 tests/test-selection-and-shapes.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
FIX = os.path.join(ROOT, 'tests', 'fixtures')
sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk  # noqa: E402

fails = []


def load(name):
    d = json.load(open(os.path.join(FIX, name)))
    return copy.deepcopy(d.get('config', d) if 'screens' not in d else d)


def run(doc):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        r = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if r.returncode == 2 or 'Traceback' in r.stderr:
        raise RuntimeError(r.stdout + r.stderr)
    lines = [ln.strip() for ln in r.stdout.splitlines()]
    return ([ln for ln in lines if ln.startswith('ERROR')],
            [ln for ln in lines if ln.startswith('warning')])


def check(name, ok, detail=''):
    print(('  ok    ' if ok else '  FAIL  ') + name + ('' if ok else f'  {detail}'))
    if not ok:
        fails.append(name)


def element(d, eid):
    for s in d['screens']:
        if eid in s['elements']['map']:
            return s['elements']['map'][eid]
    raise KeyError(eid)


def append_node(d, lid, node):
    """Add a node to the first paragraph of a catalog rich-text entry, every locale."""
    for v in d['localization']['content'][lid]['values'].values():
        v[0]['content'].append(node)


VAR = lambda vid: {'type': 'variable', 'attrs': {'variableId': vid}}
DEFAULT = 'default: true'
FINDINGS = (DEFAULT, 'beside `attrs`', 'a preset AND a family')

# SILENT on every tracked export, for every check in this file.
for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    errs, warns = run(json.load(open(f)))
    mine = [x for x in errs + warns if any(k in x for k in FINDINGS)]
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}', not mine, mine)

# --- a group with no default ----------------------------------------------------------------
d = load('comparison-paywall.json')
element(d, 'el_DtR1jkQi8C')['props']['default'] = False
_, w = run(d)
check('FIRES: product group with its one default removed',
      any('product group products' in x and DEFAULT in x for x in w), w)

d = load('tabs-paywall.json')
element(d, 'el_RvTabite065')['props']['default'] = False
_, w = run(d)
check('FIRES: tab group with its default removed',
      any('tab group tabs' in x and DEFAULT in x for x in w), w)

# The quiz group has no default in the real export and only a condition reads it: silent above.
# A text that prints the selection makes the missing default visible, so it fires.
d = load('onboarding-quiz-paywall.json')
append_node(d, 'lc_11', VAR('quiz.selectedOptionId'))
_, w = run(d)
check('FIRES: quiz group with no default whose selection a text reads',
      any('selectable group quiz' in x and DEFAULT in x for x in w), w)
element(d, 'el_7xR3X1HUGD')['props']['default'] = True
_, w = run(d)
check('SILENT: the same text read with one option marked default',
      not any(DEFAULT in x for x in w), w)

# --- rich-text variable node shape ----------------------------------------------------------
d = load('onboarding-quiz-paywall.json')
append_node(d, 'lc_11', {'type': 'variable', 'variableId': 'name.value', 'attrs': {}})
e, _ = run(d)
check('FIRES: variableId beside attrs is an error that names the fix',
      any('beside `attrs`' in x and 'name.value' in x for x in e), e)
d = load('onboarding-quiz-paywall.json')
append_node(d, 'lc_11', VAR('name.value'))
e, w = run(d)
check('SILENT: the same variable inside attrs',
      not any('beside `attrs`' in x for x in e + w), e)

# --- preset XOR manual font -----------------------------------------------------------------
d = load('vpn-timer-draft.json')
fam = next(e['props']['font']['family'] for s in d['screens'] for e in s['elements']['map'].values()
           if isinstance((e.get('props') or {}).get('font'), dict) and 'family' in e['props']['font'])
d = load('onboarding-quiz-paywall.json')
el = element(d, 'el_GtJBKATh48')
el['props']['font'] = dict(el['props']['font'], family=fam, size=18)
_, w = run(d)
check('FIRES: a font with a preset and a family',
      any('a preset AND a family' in x and 'el_GtJBKATh48' in x for x in w), w)
d = load('onboarding-quiz-paywall.json')
el = element(d, 'el_7xR3X1HUGD')
el.setdefault('propsByState', {}).setdefault('selected', {})['font'] = {'preset': 'body',
                                                                       'weight': 'bold'}
_, w = run(d)
check('SILENT: a state font of a preset plus a weight',
      not any('a preset AND a family' in x for x in w), w)

# --- flowkit --------------------------------------------------------------------------------
try:
    fk.on_selected(fk.text(fk.rich('x'), preset='plan'),
                   font={'preset': 'plan', 'family': {'type': 'system', 'family': 'system'}})
    check('FLOWKIT: on_selected refuses a preset with a family', False, 'did not raise')
except ValueError as exc:
    check('FLOWKIT: on_selected refuses a preset with a family', 'preset AND a family' in str(exc),
          str(exc))

print()
if fails:
    print(f'{len(fails)} FAILED'); sys.exit(1)
print('all passed')
