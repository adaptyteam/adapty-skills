#!/usr/bin/env python3
"""Calibration for the empty-`product` check in `references/verify-config.py`.

Repo-only. Runs the shipped checker as a subprocess, and imports `flowkit` with bytecode off so
nothing writes a `__pycache__` into `references/`.

Why this file exists. On a single-plan screen the skill used to emit an empty, hidden `product`
element as an "attach point" and leave the plan's name and price as loose text beside it. The
builder draws that empty element as a 1x1 box that breaks the layout, while `config preview`
collapses it and every other gate passes it. The fix is to wrap the plan text in the `product`
element; this check warns on the empty one.

    FIRES   -- an empty hidden `product` (the old attach point), an empty visible one, and a
               `const` purchase of the product a `product` element on the screen binds
    SILENT  -- the plan text wrapped in `product`, a multi-card plan picker, all real exports

Usage: python3 tests/test-single-plan.py    # 0 all pass, 1 a case regressed
"""
import glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')

sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk  # noqa: E402

MARKER = 'with no children'
P = '11111111-2222-3333-4444-555555555555'
Q = '66666666-7777-8888-9999-000000000000'
fails = []


def run(doc):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        r = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if 'Traceback' in r.stderr or r.returncode == 2:
        raise AssertionError(f'verify-config.py did not run cleanly:\n{r.stdout}{r.stderr}')
    return r.stdout.splitlines()


def expect(name, doc, want, marker=MARKER):
    hits = [line for line in run(doc) if marker in line]
    if bool(hits) != want:
        fails.append(f'{name}: expected {"a finding" if want else "silence"}, got {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def price_text():
    return [fk.text(fk.rich('Premium')), fk.text(fk.rich(fk.Var(f'{P}.prod_price'), ' / year'))]


def doc(nodes, products=(P,)):
    return fk.config(
        screens=[fk.screen('scr_main', nodes, fill_=fk.fill('bg'),
                           selectable_groups=[{'id': 'plans', 'type': 'product'}])],
        colors=[('bg', 'Background', '#FFFFFF', '#101014')],
        meta_screens=fk.predeclare('scr_main', list(products)))


def empty_product(**kw):
    node = fk.product((), product_id=P, group_id='plans', default=True,
                      width='hug', height='hug', **kw)
    return node


expect('FIRES: empty hidden product beside loose price text (the old attach point)',
       doc([empty_product(visibility=fk.hidden()), *price_text()]), True)
expect('FIRES: empty visible product',
       doc([empty_product(), *price_text()]), True)
expect('SILENT: the plan text wrapped in the product element',
       doc([fk.single_plan(price_text(), product_id=P, group_id='plans')]), False)
expect('SILENT: a two-card plan picker',
       doc([fk.product([fk.text(fk.rich('Annual'))], product_id=P, group_id='plans',
                       default=True),
            fk.product([fk.text(fk.rich('Monthly'))], product_id=Q, group_id='plans')],
           products=(P, Q)), False)

# --- the CTA on a screen with a `product` element buys the selection, never a `const` id ---
CONST = 'by `const` while'


def const_buy(pid):
    return {'id': 'act_buy', 'type': 'purchase',
            'payload': {'product': {'type': 'const', 'value': {'id': pid}}}}


def plan_with_cta(action):
    return doc([fk.single_plan(price_text(), product_id=P, group_id='plans'),
                fk.stack([fk.text(fk.rich('Continue'))], actions=[action])])


expect('FIRES: const purchase of the product the card already binds',
       plan_with_cta(const_buy(P)), True, CONST)
expect('SILENT: the CTA buys plans.selectedProduct',
       plan_with_cta(fk.purchase('plans')), False, CONST)
expect('SILENT: const purchase on a screen with no product element',
       fk.config(screens=[fk.screen('scr_main', [fk.stack([fk.text(fk.rich('Buy'))],
                                                          actions=[const_buy(P)])])],
                 meta_screens=fk.predeclare('scr_main', [P])), False, CONST)

real = sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', '*.json'))
              + glob.glob(os.path.join(ROOT, 'tests', 'fixtures-raw', '*.json')))
for path in real:
    expect(f'SILENT: {os.path.relpath(path, ROOT)}', json.load(open(path)), False)
    expect(f'SILENT (const): {os.path.relpath(path, ROOT)}', json.load(open(path)), False, CONST)

if fails:
    print(f'\n{len(fails)} case(s) regressed:')
    for f in fails:
        print('  ' + f)
    sys.exit(1)
print('\nall cases pass')
