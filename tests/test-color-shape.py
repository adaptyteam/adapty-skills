#!/usr/bin/env python3
"""Calibration for the colour-shape check in `references/verify-config.py`.

Repo-only. Runs the shipped script as a subprocess -- never imports it into this process, so
nothing writes a `__pycache__` into `references/`.

Why this file exists. Every colour an element carries is an `IColor`: `{type: hex, hex}` or
`{type: color-style, colorId}`. The Flow Builder's renderer throws on any other shape, and the
throw is caught only by the editor's top-level error boundary, so ONE bad value anywhere makes
the whole flow unopenable in the dashboard. The skill wrote two such shapes into a customer
flow -- a theme colour ENTRY (`{"id": "<colorId>"}`) where a reference belongs, on 20 elements,
and a fill LAYER (`{"type": "color", "color": {...}}`) in a `border.color` -- and every gate an
agent runs passed it: `flows config validate` returned `valid: true, issues: []` for both,
`verify-config.py` said OK, and the device rendered. Only the advisory schema check saw it.

The check walks by KEY NAME (`ICOLOR_KEYS`, read off every `$ref: IColor` site in the
published schema), not by props path, so `propsByState`, gradient stops, rich-text span
attributes and component elements are all reached. The cases below inject one defect at a
time into a REAL export, at each of those positions.

    FIRES   -- `{id}` in props.color, props.icon.color, propsByState.*.color; a fill layer in
               border.color; a color-style with no / an empty colorId; a hex with no hex; a
               bare hex string; a bad gradient stop; a bad rich-text span colour; a bad colour
               on a component element
    SILENT  -- all 12 real exports; a color-style carrying extra `hex`/`opacity` (25 real
               values in `onboarding-quiz-paywall.json` look like this); every colour value
               in `component-catalog.json`, which `patterns.md` tells an agent to use first

Usage: python3 tests/test-color-shape.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
CATALOG = os.path.join(REFS, 'component-catalog.json')
CORPUS = os.path.join(ROOT, 'tests', 'fixtures')
RAW = os.path.join(ROOT, 'tests', 'fixtures-raw')
QUIZ = os.path.join(CORPUS, 'onboarding-quiz-paywall.json')
COMPARISON = os.path.join(CORPUS, 'comparison-paywall.json')
VPN = os.path.join(CORPUS, 'vpn-timer-draft.json')

MINE = re.compile(r'colour value\(s\) are not a valid colour')

fails = []


def load(path):
    d = json.load(open(path))
    return d.get('config', d) if 'screens' not in d else d


def element(d, eid):
    for s in d['screens']:
        if eid in s['elements']['map']:
            return s['elements']['map'][eid]
    raise KeyError(eid)


def run(doc):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        result = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    # `CHECKER ERROR` goes to stdout at exit 2; reading stderr alone would let every SILENT
    # case pass vacuously on a document the checker could not read.
    if 'Traceback' in result.stderr or 'CHECKER ERROR' in result.stdout:
        raise AssertionError(f'verify-config.py crashed on this document:\n{result.stdout}\n'
                             f'{result.stderr}')
    hits = [ln.strip() for ln in result.stdout.splitlines() if MINE.search(ln)]
    return hits, result.returncode


def fires(name, doc, *fragments):
    hits, code = run(doc)
    text = ' '.join(hits)
    missing = [f for f in fragments if f not in text]
    if not hits or missing or code != 1:
        fails.append(f'{name}: expected an ERROR containing {missing or fragments!r} at exit 1, '
                     f'got exit {code}: {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def silent(name, doc):
    hits, _ = run(doc)
    if hits:
        fails.append(f'{name}: expected no colour-shape finding, got {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def injected(path, eid, mutate):
    d = copy.deepcopy(load(path))
    mutate(element(d, eid))
    return d


THEME_ENTRY = {'id': 'gray-800'}
FILL_LAYER = {'type': 'color', 'color': {'hex': '#806E5E', 'type': 'hex'}}

print('FIRES on each malformed shape, at each position the schema types as IColor:')
fires('theme colour entry in props.color — the 20-element shape the skill shipped',
      injected(QUIZ, 'el_0TmKwWPBxP', lambda e: e['props'].__setitem__('color', THEME_ENTRY)),
      'el_0TmKwWPBxP props.color', 'is a theme colour entry',
      '{"type": "color-style", "colorId": "gray-800"}')
fires('fill layer in props.border.color — the other shape the skill shipped',
      injected(QUIZ, 'el_BmIBa16w7n',
               lambda e: e['props']['border'].__setitem__('color', FILL_LAYER)),
      'el_BmIBa16w7n props.border.color', 'is a fill layer',
      '{"hex": "#806E5E", "type": "hex"}')
fires('theme colour entry in props.icon.color',
      injected(QUIZ, 'el_3YpqPH3dze',
               lambda e: e['props']['icon'].__setitem__('color', THEME_ENTRY)),
      'el_3YpqPH3dze props.icon.color')
fires('theme colour entry in propsByState.selected.color — a selected look',
      injected(COMPARISON, 'el_3eNsJZL6zo',
               lambda e: e['propsByState']['selected'].__setitem__('color', THEME_ENTRY)),
      'el_3eNsJZL6zo propsByState.selected.color')
fires('fill layer in propsByState.selected.border.color',
      injected(COMPARISON, 'el_DtR1jkQi8C',
               lambda e: e['propsByState']['selected']['border'].__setitem__('color',
                                                                              FILL_LAYER)),
      'el_DtR1jkQi8C propsByState.selected.border.color')
fires('color-style with no colorId',
      injected(QUIZ, 'el_0TmKwWPBxP',
               lambda e: e['props'].__setitem__('color', {'type': 'color-style'})),
      'has no `colorId`')
fires('color-style with an empty colorId',
      injected(QUIZ, 'el_0TmKwWPBxP',
               lambda e: e['props'].__setitem__('color', {'type': 'color-style',
                                                          'colorId': ' '})),
      'has no `colorId`')
fires('hex with no hex',
      injected(QUIZ, 'el_0TmKwWPBxP',
               lambda e: e['props'].__setitem__('color', {'type': 'hex', 'opacity': 100})),
      'has no string `hex`')
fires('a bare hex string',
      injected(QUIZ, 'el_0TmKwWPBxP', lambda e: e['props'].__setitem__('color', '#FFFFFF')),
      '"#FFFFFF" is not a colour object')


def bad_stop(e):
    fill = e['props']['fill']
    layer = fill[0] if isinstance(fill, list) else fill
    layer['stops'][0]['color'] = THEME_ENTRY


fires('theme colour entry in a gradient stop',
      injected(QUIZ, 'el_XKEBYBDCuP', bad_stop), 'el_XKEBYBDCuP props.fill')


def bad_span(e):
    # No real export carries a span colour, so this attaches one to the first text node.
    def walk(o):
        if isinstance(o, dict):
            if o.get('type') == 'text' and 'text' in o:
                o.setdefault('attrs', {})['color'] = THEME_ENTRY
                return True
            return any(walk(v) for v in o.values())
        if isinstance(o, list):
            return any(walk(v) for v in o)
        return False
    if not walk(e['props']['content']):
        raise AssertionError('fixture text element has no text node to attach a span colour to')


fires('theme colour entry in a rich-text span attribute',
      injected(QUIZ, 'el_0TmKwWPBxP', bad_span), 'el_0TmKwWPBxP props.content')


def bad_component():
    d = copy.deepcopy(load(VPN))
    cid, comp = next(iter(d['components'].items()))
    eid, e = next(iter(comp['map'].items()))
    e.setdefault('props', {})['color'] = THEME_ENTRY
    return d, cid, eid


d, cid, eid = bad_component()
fires('theme colour entry on a component element', d, f'component {cid}/{eid} props.color')

print()
print('SILENT on every real export:')
for path in sorted(glob.glob(os.path.join(CORPUS, '*.json'))
                   + glob.glob(os.path.join(RAW, '*.json'))):
    d = load(path)
    if not isinstance(d, dict) or 'screens' not in d:
        continue
    silent(f'{os.path.basename(os.path.dirname(path))}/{os.path.basename(path)}', d)
if not glob.glob(os.path.join(RAW, '*.json')):
    print('  (tests/fixtures-raw/ absent — the 5 raw exports were not checked)')

print()
print('SILENT on the legal shapes the guard must not reach:')
silent('color-style carrying extra hex/opacity — 25 real values look like this',
       injected(QUIZ, 'el_0TmKwWPBxP',
                lambda e: e['props'].__setitem__('color', {'type': 'color-style',
                                                           'colorId': 'gray-800',
                                                           'hex': '#1F2937',
                                                           'opacity': 100})))
silent('hex with an opacity',
       injected(QUIZ, 'el_0TmKwWPBxP',
                lambda e: e['props'].__setitem__('color', {'type': 'hex', 'hex': '#1F2937',
                                                           'opacity': 50})))

print()
print('SILENT on every colour in component-catalog.json (the recommended path):')
# The catalog is templates, not a config, so the shipped shape predicate is applied to it
# directly -- in a child process run with -B, so no bytecode lands in `references/`. The
# script has no `__main__` guard, so loading it runs the CLI: point it at a real fixture,
# swallow its output and its exit, and use the functions it defined on the way.
probe = (
    'import contextlib, importlib.util, io, json, sys\n'
    f'sys.argv = ["verify-config.py", {QUIZ!r}]\n'
    f'spec = importlib.util.spec_from_file_location("vc", {VERIFY!r})\n'
    'vc = importlib.util.module_from_spec(spec)\n'
    'with contextlib.redirect_stdout(io.StringIO()):\n'
    '    try:\n'
    '        spec.loader.exec_module(vc)\n'
    '    except SystemExit:\n'
    '        pass\n'
    f'cat = json.load(open({CATALOG!r}))\n'
    'n = 0; bad = []\n'
    'for key, v in vc.iter_color_values(cat):\n'
    '    n += 1\n'
    '    p = vc.icolor_problem(v)\n'
    '    if p: bad.append(f"{key}: {p}")\n'
    'print(json.dumps({"n": n, "bad": bad[:5], "nbad": len(bad)}))\n')
out = subprocess.run([sys.executable, '-B', '-c', probe], capture_output=True, text=True)
try:
    res = json.loads(out.stdout)
except ValueError:
    res = None
if not res or res['n'] < 100 or res['nbad']:
    fails.append(f'catalog: expected 100+ colour values and none malformed, got {res or out.stderr}')
    print('  FAIL  component-catalog.json')
else:
    print(f'  ok    component-catalog.json ({res["n"]} colour values)')

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
