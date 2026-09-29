#!/usr/bin/env python3
"""localization.py: the catalog port, its read view, and the checks built on them.

Repo-only. Four things are pinned here, and each is a way the port could be wrong quietly:

  1. `catalog()` matches the builder's own migration 013 BYTE FOR BYTE, key order and warnings
     included, on every case in `tests/localization-oracle/`. Each file there holds an input and
     the output the real TypeScript step produced for it; they cover conditional text with a
     matching and a mismatched locale, orphan locales, alerts nested in a conditional action,
     components, an existing catalog beside inline values, no declared locales, `locales` that
     is not an array, and a `defaultLocale` that is a locale CODE. A port that is merely
     plausible would drift from the builder on exactly these.
  2. It is idempotent: the tracked corpus (every fixture is stored v13) comes back unchanged.
  3. `resolve()` is a read view that cannot be mistaken for stored data: no `_lid` anywhere in
     it, no catalog left in it, and resolving it again changes nothing.
  4. The two shipped copies (flow-generator and flow-audit) are byte-identical, so a
     directory-copy install of either skill reads the catalog the same way.
"""
import copy, glob, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from v13 import localization as L  # noqa: E402

GEN = os.path.join(ROOT, 'skills', 'flow-generator', 'references', 'localization.py')
AUD = os.path.join(ROOT, 'skills', 'flow-audit', 'references', 'localization.py')
VERIFY = os.path.join(ROOT, 'skills', 'flow-generator', 'references', 'verify-config.py')

fails = []


def check(name, cond, detail=''):
    print(f'  {"ok   " if cond else "FAIL "} {name}')
    if not cond:
        fails.append(f'{name} {detail}'.strip())


print('catalog() against the builder migration (tests/localization-oracle)')
for path in sorted(glob.glob(os.path.join(HERE, 'localization-oracle', '*.json'))):
    case = json.load(open(path))
    out, warnings = L.catalog(case['input'])
    name = os.path.basename(path)[:-5]
    check(f'{name}: document identical, key order included',
          json.dumps(out) == json.dumps(case['expected']))
    check(f'{name}: warnings identical ({len(case["warnings"])})',
          json.dumps(warnings) == json.dumps(case['warnings']))
    again, w2 = L.catalog(out)
    check(f'{name}: idempotent', json.dumps(again) == json.dumps(out) and not w2)

print('\ncatalog() on the stored corpus')
corpus = sorted(glob.glob(os.path.join(HERE, 'fixtures', '*.json')))
for path in corpus:
    doc = json.load(open(path))
    out, w = L.catalog(doc)
    check(f'{os.path.basename(path)} comes back unchanged', out == doc and not w)

print('\ncatalog() refuses what it cannot convert')
for label, doc in (('schemaVersion 10', {'schemaVersion': 10, 'screens': []}),
                   ('no schemaVersion', {'screens': []}),
                   ('an envelope', {'config': {'screens': []}})):
    try:
        L.catalog(doc)
        check(f'refuses {label}', False, 'no error')
    except L.MigrationError as exc:
        check(f'refuses {label}', True)
        if label == 'schemaVersion 10':
            check('...and names the Flow Builder as the way through', 'Flow Builder' in str(exc))
src = {'schemaVersion': 12, 'screens': []}
L.catalog(src)
check('never mutates its input', src == {'schemaVersion': 12, 'screens': []})

print('\nresolve(): a read view, never stored data')
multi = json.load(open(os.path.join(HERE, 'fixtures', 'onboarding-multilocale.json')))
multi = multi.get('config', multi)
view = L.resolve(multi)
blob = json.dumps(view)
check('no `_lid` survives in the view', '"_lid"' not in blob)
check('the stored catalog is not in the view', 'localization' not in view)
check('locales and defaultLocale are at the top level',
      view.get('locales') == multi['localization']['locales']
      and view.get('defaultLocale') == multi['localization']['defaultLocale'])
check('resolving a view returns it unchanged', L.resolve(view) == view)
n_fields = sum(1 for _ in L.iter_fields(multi))
n_inline = sum(1 for _w, _k, h, k in L.iter_fields(view) if L.is_inline(h[k]))
check(f'every stored field ({n_fields}) is inline in the view', n_inline == n_fields)
check('the stored document is untouched', 'localization' in multi)

print('\nis_empty(): the fallback rule')
P = lambda t: [{'type': 'paragraph', 'content': [{'type': 'text', 'text': t}]}]
for kind, value, want in (('rich-text', '', True), ('rich-text', [], True),
                          ('rich-text', P(''), True), ('rich-text', P(' '), False),
                          ('rich-text', [{'type': 'paragraph'}], True),
                          ('rich-text', [{'type': 'paragraph', 'content': [
                              {'type': 'variable', 'attrs': {'variableId': 'x'}}]}], False),
                          ('rich-string', [], True), ('rich-string', 'a', False),
                          ('image', {'id': '1', 'url': ''}, True),
                          ('image', {'id': '1', 'url': 'https://x'}, False),
                          ('image', 'https://x', True),
                          ('video', {'videoUrl': ''}, True), (None, None, True)):
    check(f'is_empty({kind}, {json.dumps(value)[:40]}) is {want}',
          L.is_empty(kind, value) is want)

print('\nediting primitives')
doc = copy.deepcopy(multi)
before = set(doc['localization']['content'])
ref = L.new_entry(doc, 'rich-text', {'en': P('Hi'), 'sr': P('')})
check('new_entry mints an id no ref or entry already uses', ref['_lid'] not in before)
check('...and keeps only non-empty values',
      doc['localization']['content'][ref['_lid']]['values'] == {'en': P('Hi')})
twin = L.copy_entry(doc, ref)
check('copy_entry is an independent entry',
      twin['_lid'] != ref['_lid']
      and L.entry_for(doc, twin)['values'] is not L.entry_for(doc, ref)['values'])

print('\nverify-config.py: the catalog invariants')


def verify(d):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json')
        json.dump(d, open(p, 'w'))
        r = subprocess.run([sys.executable, VERIFY, p], capture_output=True, text=True)
    if r.returncode == 2:
        raise AssertionError(r.stdout + r.stderr)
    return r.stdout


def first_text(d):
    for s in d['screens']:
        for e in s['elements']['map'].values():
            if e['type'] == 'text' and L.is_ref(e['props'].get('content')):
                return e
    raise AssertionError('no text element')


def fires(name, d, fragment, level='ERROR'):
    out = verify(d)
    check(name, any(fragment in l and level in l for l in out.splitlines()), out[-400:])


check('the stored corpus has no catalog finding',
      not any('catalog' in verify(json.load(open(p))) and 'ERROR' in verify(json.load(open(p)))
              for p in corpus))

d = copy.deepcopy(multi)
d['locales'] = d['localization'].pop('locales')
d['defaultLocale'] = d['localization'].pop('defaultLocale')
del d['localization']
fires('a pre-catalog document is refused, with the way through', d, 'pre-catalog document')

d = copy.deepcopy(multi)
first_text(d)['props']['content'] = {'_localizable': True, 'values': {'en': P('graft')}}
fires('an inline value left in a catalogued document', d, 'still inline')

d = copy.deepcopy(multi)
first_text(d)['props']['content'] = {'_lid': 'lc_does_not_exist'}
fires('a ref naming no entry', d, 'naming no catalog entry')

d = copy.deepcopy(multi)
d['localization']['content'][first_text(d)['props']['content']['_lid']]['kind'] = 'image'
fires('an entry whose kind does not match its field', d, 'kind does not match')

d = copy.deepcopy(multi)
lid = first_text(d)['props']['content']['_lid']
d['localization']['content'][lid]['values']['en'] = {
    'type': 'switch', 'cases': [], 'default': {'type': 'const', 'value': P('x')}}
fires('a whole switch stored as an entry value', d, 'holds a whole switch')

d = copy.deepcopy(multi)
d['schemaVersion'] = 12
fires('a catalogued document stamped below 13', d, 'schemaVersion is 12')

d = copy.deepcopy(multi)
d['localization']['defaultLocale'] = 'xx'
fires('a defaultLocale naming no declared locale id', d, 'not one of the declared')

d = copy.deepcopy(multi)
loc = d['localization']['locales'][1]
loc['id'] = 'locale-' + loc['code']
fires('values keyed by a locale CODE whose id differs', d, 'keyed by the locale CODE')

d = copy.deepcopy(multi)
for e in d['localization']['content'].values():
    e['values'].pop('sr', None)
out = verify(d)
check('an untranslated locale is a WARNING (it falls back), never an ERROR',
      any('locale sr:' in l and 'untranslated' in l and 'warning' in l
          for l in out.splitlines())
      and not any('locale sr' in l and 'ERROR' in l for l in out.splitlines()), out[-400:])

print('\ncopies')
a, b = open(GEN, 'rb').read(), open(AUD, 'rb').read()
check('flow-generator and flow-audit ship byte-identical localization.py', a == b,
      'cp skills/flow-generator/references/localization.py skills/flow-audit/references/')

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print(f'  - {f}')
    sys.exit(1)
print('all passed')
