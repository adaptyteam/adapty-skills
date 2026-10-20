#!/usr/bin/env python3
"""Calibration for the hex-format check in `references/verify-config.py` and for
`flowkit.normalize_colors()` / `flowkit.hex_color()`.

Repo-only. The checker runs as a subprocess; flowkit is imported with bytecode off, so nothing
writes a `__pycache__` into `references/`.

Why this file exists. The flow config schema types every colour `hex` as `''` or `#RRGGBB`, alpha
only in `opacity`, and the Developer API refuses anything else on write, so `config update`
rejects a `#RGB` or a `#RRGGBBAA` anywhere in the document. Older flows still hold such values
(the builder's colour field used to save every keystroke), and the fetched config is the only
write base, so an untouched legacy colour fails the next write. The check names every one; the
normalizer rewrites them without changing what renders.

    FIRES   -- #RGB, #RRGGBBAA, 7 digits, no `#`, in props.color, a fill, a gradient stop, a
               screen background, a component element; the real export that holds #FFFFFFD9
    SILENT  -- every other real export; an empty hex; a color-style's empty hex; the catalog;
               the quiz export after normalize_colors()
    FLOWKIT -- normalize_colors keeps the effective alpha; hex_color refuses a bad hex; the CLI
               rewrites the file and reports each change

Usage: python3 tests/test-hex-format.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
FLOWKIT = os.path.join(REFS, 'flowkit.py')
CATALOG = os.path.join(REFS, 'component-catalog.json')
CORPUS = os.path.join(ROOT, 'tests', 'fixtures')
RAW = os.path.join(ROOT, 'tests', 'fixtures-raw')
QUIZ = os.path.join(CORPUS, 'onboarding-quiz-paywall.json')
VPN = os.path.join(CORPUS, 'vpn-timer-draft.json')

sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk  # noqa: E402

MINE = re.compile(r'colour hex value\(s\) are not #RRGGBB')

fails = []


def ok(name, cond, detail=''):
    if cond:
        print(f'  ok    {name}')
    else:
        fails.append(f'{name}: {detail}')
        print(f'  FAIL  {name}')


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
        r = subprocess.run([sys.executable, '-B', VERIFY, path], capture_output=True, text=True)
    if 'Traceback' in r.stderr or 'CHECKER ERROR' in r.stdout:
        raise AssertionError(f'verify-config.py crashed:\n{r.stdout}\n{r.stderr}')
    return [ln.strip() for ln in r.stdout.splitlines() if MINE.search(ln)], r.returncode


def fires(name, doc, *fragments):
    hits, code = run(doc)
    text = ' '.join(hits)
    missing = [f for f in fragments if f not in text]
    ok(name, hits and not missing and code == 1,
       f'expected an ERROR containing {missing or fragments!r} at exit 1, got exit {code}: {hits!r}')


def silent(name, doc):
    hits, _ = run(doc)
    ok(name, not hits, f'expected no hex-format finding, got {hits!r}')


def with_color(eid, value, path=QUIZ):
    """The quiz export, its own legacy #FFFFFFD9 fills normalized, with one colour injected."""
    d = copy.deepcopy(load(path))
    fk.normalize_colors(d)
    element(d, eid)['props']['color'] = value
    return d


print('FIRES on every hex the Developer API refuses:')
for bad in ('#FFF', '#FFFFFFD9', '#FFFFFFF', 'FFFFFF'):
    fires(f'{bad!r} in props.color', with_color('el_0TmKwWPBxP', {'type': 'hex', 'hex': bad}),
          'el_0TmKwWPBxP props.color', repr(bad))


def bad_stop():
    d = copy.deepcopy(load(QUIZ))
    fill = element(d, 'el_XKEBYBDCuP')['props']['fill']
    layer = fill[0] if isinstance(fill, list) else fill
    layer['stops'][0]['color'] = {'type': 'hex', 'hex': '#abc'}
    return d


fires('#abc in a gradient stop', bad_stop(), 'el_XKEBYBDCuP props.fill', "'#abc'")


def bad_screen_fill():
    d = copy.deepcopy(load(VPN))
    s = d['screens'][0]
    s.setdefault('props', {})['fill'] = [{'type': 'color',
                                          'color': {'type': 'hex', 'hex': '#00000055'}}]
    return d, s['id']


d, sid = bad_screen_fill()
fires('#00000055 in a screen background', d, f'screen {sid}', "'#00000055'")


def bad_component():
    d = copy.deepcopy(load(VPN))
    cid, comp = next(iter(d['components'].items()))
    eid, e = next(iter(comp['map'].items()))
    e.setdefault('props', {})['color'] = {'type': 'hex', 'hex': '#333'}
    return d, cid, eid


d, cid, eid = bad_component()
fires('#333 on a component element', d, f'component {cid}/{eid}', "'#333'")
fires('the real export holding #FFFFFFD9 — a legacy value the next write would carry',
      load(QUIZ), 'el_BmIBa16w7n', "'#FFFFFFD9'", 'normalize-colors')

print()
print('SILENT on the legal values:')
for path in sorted(glob.glob(os.path.join(CORPUS, '*.json'))
                   + glob.glob(os.path.join(RAW, '*.json'))):
    if path == QUIZ:
        continue
    d = load(path)
    if isinstance(d, dict) and 'screens' in d:
        silent(f'{os.path.basename(os.path.dirname(path))}/{os.path.basename(path)}', d)
silent('an empty hex', with_color('el_0TmKwWPBxP', {'type': 'hex', 'hex': ''}))
silent('a color-style carrying an empty hex',
       with_color('el_0TmKwWPBxP', {'type': 'color-style', 'colorId': 'gray-800', 'hex': '',
                                    'opacity': 100}))
silent('lower-case #rrggbb', with_color('el_0TmKwWPBxP', {'type': 'hex', 'hex': '#1f2937'}))

cat_bad = []


def cat_walk(o, p=''):
    if isinstance(o, dict):
        h = o.get('hex')
        if isinstance(h, str) and not fk.ELEMENT_HEX.match(h):
            cat_bad.append(f'{p}: {h!r}')
        for k, v in o.items():
            cat_walk(v, f'{p}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            cat_walk(v, f'{p}[{i}]')


cat_walk(json.load(open(CATALOG)))
ok('component-catalog.json holds only #RRGGBB or empty', not cat_bad, cat_bad[:5])

print()
print('FLOWKIT:')
quiz = copy.deepcopy(load(QUIZ))
changes = fk.normalize_colors(quiz)
silent('the quiz export after normalize_colors()', quiz)
ok('normalize_colors reports the four #FFFFFFD9 fills',
   sum('#FFFFFFD9' in c for c in changes) == 4, changes)
ok('#FFFFFFD9 becomes #FFFFFF at opacity 85',
   element(quiz, 'el_BmIBa16w7n')['props']['fill'][0]['color']
   == {'type': 'hex', 'hex': '#FFFFFF', 'opacity': 85},
   element(quiz, 'el_BmIBa16w7n')['props']['fill'][0]['color'])

doc = {'theme': {'colors': [{'id': 'scrim', 'light': {'hex': '#00000080'},
                             'dark': {'hex': '#fff', 'opacity': 50}}]},
       'screens': [{'id': 's', 'props': {'fill': [{'type': 'color', 'color': {
           'type': 'hex', 'hex': '#FF000080', 'opacity': 50}}]},
           'elements': {'map': {'e': {'props': {
               'color': {'type': 'color-style', 'colorId': 'scrim', 'hex': '#abc'},
               'empty': {'type': 'hex', 'hex': ''}}}}}}]}
fk.normalize_colors(doc)
tc = doc['theme']['colors'][0]
ok('a theme #RRGGBBAA moves its alpha to the token opacity',
   tc['light'] == {'hex': '#000000', 'opacity': 50}, tc['light'])
ok('a theme #RGB expands and keeps its opacity',
   tc['dark'] == {'hex': '#FFFFFF', 'opacity': 50}, tc['dark'])
scr = doc['screens'][0]['props']['fill'][0]['color']
ok('an existing opacity multiplies with the hex alpha (50% of 50%)',
   scr == {'type': 'hex', 'hex': '#FF0000', 'opacity': 25}, scr)
el = doc['screens'][0]['elements']['map']['e']['props']
ok('a color-style keeps no alpha of its own: its #RGB only expands',
   el['color'] == {'type': 'color-style', 'colorId': 'scrim', 'hex': '#AABBCC'}, el['color'])
ok('an empty hex is left alone', el['empty'] == {'type': 'hex', 'hex': ''}, el['empty'])
ok('a second pass changes nothing', fk.normalize_colors(doc) == [], fk.normalize_colors(doc))

for bad in ('#FFF', '#FFFFFFD9', 'FFFFFF'):
    try:
        fk.hex_color(bad)
        ok(f'hex_color({bad!r}) raises', False, 'it returned a colour')
    except ValueError as e:
        ok(f'hex_color({bad!r}) raises', '#RRGGBB' in str(e), str(e))
ok("hex_color('#1f2937', 40) builds", fk.hex_color('#1f2937', 40)
   == {'type': 'hex', 'hex': '#1f2937', 'opacity': 40})
try:
    fk.gradient(180, ('#FFF', 0), ('#000000', 1))
    ok('gradient() refuses a #RGB stop', False, 'it returned a gradient')
except ValueError:
    ok('gradient() refuses a #RGB stop', True)

with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, 'flow.json')
    json.dump(json.load(open(QUIZ)), open(path, 'w'))
    r = subprocess.run([sys.executable, '-B', FLOWKIT, 'normalize-colors', path],
                       capture_output=True, text=True)
    after = load(path)
    ok('the CLI rewrites the file and prints each change',
       r.returncode == 0 and r.stdout.count('#FFFFFFD9') == 4 and not run(after)[0],
       f'exit {r.returncode}: {r.stdout}{r.stderr}')
    r = subprocess.run([sys.executable, '-B', FLOWKIT, 'normalize-colors', path],
                       capture_output=True, text=True)
    ok('the CLI on a clean file says so', r.returncode == 0 and 'nothing to change' in r.stdout,
       r.stdout + r.stderr)

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
