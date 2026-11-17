#!/usr/bin/env python3
"""Calibration for the font-reference check in `references/verify-config.py`.

Repo-only. Runs the shipped script as a subprocess -- never imports it, so nothing writes a
`__pycache__` into `references/`.

Why it is a WARNING. Publishing replaces the config's `_meta.fonts` with the app's own fonts and
resolves every `family.id` there, by id or by a family name exactly one font has (trimmed, any
case). `flows config validate` answers `valid: true` for a config whose presets name the app's
fonts by id or by name with `_meta.fonts: []`, and `missing_flow_font_meta` for an id the app
lacks even when its entry is carried along. The checker cannot see the app's fonts, so a reference
the copy lacks is something to validate, not a blocker.

    FIRES (warning, never an error) -- a reference `_meta.fonts` lacks: emptied fonts, a name
    SILENT -- every tracked fixture, each with its fonts as exported

Usage: python3 tests/test-font-references.py     # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'verify-config.py')
CORPUS = os.path.join(ROOT, 'tests', 'fixtures')
TAG = 'font.family.id not in _meta.fonts'
fails = []


def lines(doc):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        r = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if 'Traceback (most recent call last)' in r.stderr:
        raise AssertionError(f'verify-config.py crashed instead of reporting:\n{r.stderr}')
    return [l for l in r.stdout.splitlines() if TAG in l]


def case(name, got, want):
    if got == want:
        print(f'  ok    {name}')
    else:
        fails.append(f'{name}: expected {want!r}, got {got!r}')
        print(f'  FAIL  {name}')


def kinds(hits):
    return sorted({'ERROR' if 'ERROR' in l else 'WARNING' if 'warning:' in l.lower() else '?'
                   for l in hits})


fixtures = sorted(glob.glob(os.path.join(CORPUS, '*.json')))
with_fonts = []
for path in fixtures:
    doc = json.load(open(path))
    case(f'silent on {os.path.basename(path)}', lines(doc), [])
    if (doc.get('_meta') or {}).get('fonts'):
        with_fonts.append((os.path.basename(path), doc))

case('the corpus has fixtures with custom fonts to inject into', bool(with_fonts), True)

for name, doc in with_fonts:
    emptied = copy.deepcopy(doc)
    emptied['_meta']['fonts'] = []
    case(f'{name}: fonts emptied warns, never errors', kinds(lines(emptied)), ['WARNING'])

    by_name = copy.deepcopy(doc)
    names = {f['id']: f.get('name') for f in by_name['_meta']['fonts']}
    by_name['_meta']['fonts'] = []
    swapped = []

    def swap(o):
        if isinstance(o, dict):
            fam = o.get('family')
            if isinstance(fam, dict) and fam.get('id') in names and names[fam['id']]:
                fam['id'] = names[fam['id']].lower()
                swapped.append(fam['id'])
            for v in o.values():
                swap(v)
        elif isinstance(o, list):
            for v in o:
                swap(v)

    swap(by_name)
    hits = lines(by_name)
    case(f'{name}: families named by name warn, never error', kinds(hits), ['WARNING'])
    case(f'{name}: the warning names the references as written',
         all(s in ' '.join(hits) for s in swapped), True)

if fails:
    print('\n'.join(['', 'FAILED:'] + fails))
    sys.exit(1)
print('\nall font-reference cases pass')
