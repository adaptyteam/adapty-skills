#!/usr/bin/env python3
"""Calibration for the text-fit checks in `references/verify-config.py`.

Repo-only. Runs the shipped script as a subprocess, so nothing writes a `__pycache__` into
`references/`.

Two checks. `autoShrink` outside a bounded box (no positive `maxLines`, no positive fixed height,
or a fixed height under `layout: "auto-height"`) does nothing on a device: the transformer emits
`on_overflow: scale` only inside one. And a bounded text without `autoShrink` whose translation is
over a fifth longer than the default locale's is cut off with an ellipsis in that locale.

No export in the corpus bounds a text, so SILENT on the corpus is trivially true; the cases below
are injected into a copy of the one multi-locale fixture.

    FIRES   -- autoShrink with no bound, autoShrink under auto-height, a non-boolean autoShrink,
               a long translation under maxLines, a long translation under a fixed height
    SILENT  -- every fixture, the long translation once autoShrink is on, a translation the
               same length as the default

Usage: python3 tests/test-text-fit.py     # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'verify-config.py')
BASE = os.path.join(ROOT, 'tests', 'fixtures', 'onboarding-multilocale.json')
IDLE, LONG = 'autoShrink does nothing', 'longer than the default locale'
FAILURES = []


def run(cfg):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(cfg, f)
    try:
        return subprocess.run([sys.executable, VERIFY, f.name], capture_output=True,
                              text=True).stdout
    finally:
        os.unlink(f.name)


def check(name, cond, detail=''):
    print(f'  {"ok  " if cond else "FAIL"}  {name}' + ('' if cond else f'   {detail[:400]}'))
    if not cond:
        FAILURES.append(name)


def target(cfg):
    """The first text whose catalog entry has a value in a second locale."""
    lz = cfg['localization']
    for s in cfg['screens']:
        for e in s['elements']['map'].values():
            ref = e.get('props', {}).get('content')
            if e['type'] == 'text' and isinstance(ref, dict) and '_lid' in ref:
                vals = lz['content'][ref['_lid']]['values']
                other = [l for l in vals if l != lz['defaultLocale']]
                if other:
                    return e['props'], vals, other[0]
    raise SystemExit('no translated text in the base fixture')


def lengthen(v):
    s = json.dumps(v)
    return json.loads(s.replace('"text": "', '"text": "A much longer translation of ', 1))


def main():
    for p in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
        out = run(json.load(open(p, encoding='utf-8')))
        check(f'silent on {os.path.relpath(p, ROOT)}', IDLE not in out and LONG not in out, out)

    base = json.load(open(BASE, encoding='utf-8'))
    base = base.get('config', base)

    def case(edit):
        cfg = copy.deepcopy(base)
        props, vals, loc = target(cfg)
        edit(props, vals, loc, cfg['localization']['defaultLocale'])
        return run(cfg)

    out = case(lambda p, v, l, d: p.update(autoShrink=True))
    check('fires: autoShrink with no line limit or fixed height', IDLE in out, out)
    out = case(lambda p, v, l, d: p.update(autoShrink=True, layout='auto-height',
                                           height={'type': 'fixed', 'value': 40}))
    check('fires: a fixed height under auto-height', IDLE in out, out)
    out = case(lambda p, v, l, d: p.update(autoShrink='yes', maxLines=1))
    check('fires: a non-boolean autoShrink is an error', 'autoShrink is' in out and 'ERROR' in out, out)
    out = case(lambda p, v, l, d: p.update(autoShrink=True, maxLines=1))
    check('silent: autoShrink inside a line limit', IDLE not in out, out)

    def long_(extra):
        def edit(p, v, l, d):
            v[l] = lengthen(v[d])
            p.update(extra)
        return edit
    out = case(long_({'maxLines': 1}))
    check('fires: a long translation under maxLines', LONG in out, out)
    out = case(long_({'layout': 'fixed', 'height': {'type': 'fixed', 'value': 40}}))
    check('fires: a long translation under a fixed height', LONG in out, out)
    out = case(long_({'maxLines': 1, 'autoShrink': True}))
    check('silent: the long translation once autoShrink is on', LONG not in out, out)
    out = case(lambda p, v, l, d: (v.__setitem__(l, copy.deepcopy(v[d])), p.update(maxLines=1)))
    check('silent: a translation as long as the default', LONG not in out, out)

    print()
    if FAILURES:
        print(f'{len(FAILURES)} failure(s): ' + ', '.join(FAILURES))
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
