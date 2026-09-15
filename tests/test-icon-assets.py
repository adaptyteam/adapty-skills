#!/usr/bin/env python3
"""Calibration for `references/icons.py` and the phosphor-name check in `verify-config.py`.

Repo-only. The verify half runs the shipped script as a subprocess -- never imports it, so
nothing writes a `__pycache__` into `references/`. The resolver half imports `icons` with
bytecode writing already off, the same guarded import `test-flowkit.py` uses.

Why this file exists. A `phosphor` icon resolves from the renderer's OWN bundle by name, so a
name the bundle lacks draws NOTHING and an authored `raw` does not rescue it -- measured twice
on `CloseX` with correct markup, against `X` which drew immediately. Nothing else can see it:
`flows config validate` returns `valid: true`, the schema types the name as a bare string, and a
blank reads as a spacing bug in a screenshot. The standing answer was "take the name AND its raw
from a real export", which limits an author to the dozen glyphs the corpus happens to hold.

The decisive row here is `pack markup matches the real export byte for byte`. It is what makes
the vendored bundle usable as a source of `_meta.icons` entries rather than merely as a
spellchecker: with the builder's two serialization quirks applied (`width="20" height="20"`, and
`<path/>` expanded), the pack's markup equals the export's exactly for every distinct icon in
the tracked and raw corpus. If that row ever fails, the emitted entries have started to differ
from what the builder writes, and `diff-config.py` will report churn on every round trip.

    FIRES   -- an invented phosphor name; a real name at a weight the bundle lacks; either of
               those on a `leadingIcon`; one finding per distinct unknown
    SILENT  -- all 12 real configs; every icon in `component-catalog.json`; a `custom` icon
               under any name; an icon element missing `weight` (the older check owns that one)

Negative-tested per mechanism, each reddening only its own rows:
    * drop the `has_phosphor` guard in verify-config.py   -> the 5 FIRES rows + 2 resolver rows
    * drop the width/height rewrite in `icons.icon_raw`   -> the byte-identical row
    * drop the `<path/>` expansion in `icons.icon_raw`    -> the byte-identical row
    * scope the walk to `icon` and skip `leadingIcon`     -> the leadingIcon row only

Usage: python3 tests/test-icon-assets.py    # 0 all pass, 1 a case regressed
"""
import glob, json, os, re, subprocess, sys, tempfile

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
CATALOG = os.path.join(REFS, 'component-catalog.json')
sys.path.insert(0, REFS)
import icons  # noqa: E402

MARKER = 'phosphor-icons/core'          # every finding from this check names the pack version

fails = []


def check(name, ok, detail=''):
    if ok:
        print(f'  ok    {name}')
    else:
        fails.append(f'{name}: {detail}')
        print(f'  FAIL  {name}  {detail}')


def run(doc):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        result = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if 'Traceback' in result.stderr:
        raise AssertionError(f'verify-config.py crashed:\n{result.stderr}')
    if result.returncode == 2:
        # The checker's own guard prints CHECKER ERROR to stdout and exits 2; without this a
        # malformed fixture reads as "no findings" and every SILENT row passes vacuously.
        raise AssertionError(f'verify-config.py reported a checker error:\n{result.stdout}')
    return [line for line in result.stdout.splitlines() if MARKER in line]


def fires(name, doc, fragment):
    hits = run(doc)
    check(name, any(fragment in line for line in hits),
          f'expected a finding containing {fragment!r}, got {hits!r}')


def silent(name, doc):
    hits = run(doc)
    check(name, not hits, f'expected no phosphor finding, got {hits!r}')


def icon_el(eid, name, weight='regular', kind='phosphor', key='icon'):
    return {'id': eid, 'type': 'icon' if key == 'icon' else 'text', 'states': [], 'props': {
        key: {'name': name, 'size': 22, 'type': kind, **({} if weight is None
                                                         else {'weight': weight})},
        'width': {'type': 'hug'}, 'height': {'type': 'hug'},
        'position': {'type': 'relative'}}}


def doc_with(*elements, declare=True):
    """One screen carrying `elements`, each declared in `_meta.icons` unless told otherwise.

    Declaring by default is what keeps these rows testing THIS check: an undeclared icon also
    trips the older used-but-absent error, and a row that fires for two reasons proves neither.
    """
    declared = []
    for element in elements:
        for key in ('icon', 'leadingIcon'):
            ic = element['props'].get(key)
            if ic and declare:
                declared.append({'name': ic['name'], 'weight': ic.get('weight', 'regular'),
                                 'raw': '<svg xmlns="http://www.w3.org/2000/svg"></svg>'})
    return {
        'schemaVersion': 10, 'defaultLocale': 'en',
        'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}],
        'theme': {'colors': [], 'typography': []},
        '_meta': {'screens': {}, 'icons': declared, 'fonts': []},
        'screens': [{'id': 'scr_1', 'caption': 'Screen', 'selectableGroups': [],
                     'props': {'safeArea': True, 'scrollable': True,
                               'padding': {'top': 8, 'left': 16, 'right': 16, 'bottom': 8},
                               'fill': {'type': 'color',
                                        'color': {'type': 'hex', 'hex': '#FFFFFF'}},
                               'layout': {'alignH': 'start', 'alignV': 'start',
                                          'direction': 'vertical',
                                          'distribution': {'type': 'gap', 'gap': 8}}},
                     'elements': {
            'map': {e['id']: e for e in elements},
            'hierarchy': {'id': 'root',
                          'children': [{'id': e['id'], 'children': []} for e in elements]}}}]}


def corpus():
    seen = {}
    for path in sorted(set(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', '*.json'))) |
                       set(glob.glob(os.path.join(ROOT, 'tests', 'fixtures-raw', '*.json')))):
        doc = json.load(open(path))
        yield path, doc.get('config', doc)


# ------------------------------------------------------------------ the bundle vs the builder
print('The vendored pack against real builder output:')

export_raw = {}
for path, doc in corpus():
    for entry in (doc.get('_meta') or {}).get('icons') or []:
        export_raw.setdefault((entry.get('name'), entry.get('weight')),
                              (entry.get('raw'), os.path.basename(path)))

# timeline-anchored.json is the corpus's one HYBRID (real screen, borrowed theme, hand-authored
# icon markup) and is excluded from census counts everywhere else for the same reason: its
# `raw` carries width 24 where every genuine export carries 20, so it would be measuring our own
# authoring rather than the builder's.
export_raw = {k: v for k, v in export_raw.items() if v[1] != 'timeline-anchored.json'}

missing = sorted(k for k in export_raw if not icons.has_phosphor(*k))
check('every icon in the corpus resolves in the bundle', not missing, f'missing: {missing}')

mismatched = [f'{name}::{weight} (from {src})'
              for (name, weight), (raw, src) in sorted(export_raw.items())
              if icons.icon_raw(name, weight) != raw]
check(f'pack markup matches the real export byte for byte ({len(export_raw)} icons)',
      not mismatched, f'differs for: {mismatched}')

catalog_icons, catalog_custom = set(), set()


def _walk_catalog(node):
    if isinstance(node, dict):
        for key in ('icon', 'leadingIcon'):
            ic = node.get(key)
            if isinstance(ic, dict) and ic.get('name'):
                target = catalog_custom if ic.get('type') == 'custom' else catalog_icons
                target.add((ic['name'], ic.get('weight', 'regular')))
        for value in node.values():
            _walk_catalog(value)
    elif isinstance(node, list):
        for value in node:
            _walk_catalog(value)


_walk_catalog(json.load(open(CATALOG)))
unresolved = sorted(k for k in catalog_icons if not icons.has_phosphor(*k))
check(f'every phosphor icon in component-catalog.json resolves ({len(catalog_icons)})',
      not unresolved, f'missing: {unresolved}')
check('the catalog names only custom icons the Builder publishes',
      all(n in icons.custom_names() for n, _ in catalog_custom),
      f'unknown custom: {sorted(catalog_custom)}')

# The recommended path must not lead into the refusal: `patterns.md` tells an agent to fill a
# catalog template first, so a template naming an icon this check rejects would be finding 15's
# class again -- which is what the two rows above pin.

# ------------------------------------------------------------------------------- the resolver
print('\nThe resolver:')

check('a known name resolves at every published weight',
      all(icons.has_phosphor('Star', w) for w in icons.WEIGHTS))
check('an invented name does not resolve', not icons.has_phosphor('CloseX'))

try:
    icons.icon_meta('CloseX')
    check('icon_meta raises on an invented name', False, 'no raise')
except ValueError as exc:
    check('icon_meta raises on an invented name, naming the blank and suggesting names',
          'BLANK' in str(exc) and 'Did you mean' in str(exc), str(exc))

try:
    icons.icon_meta('Star', 'thin')
    check('icon_meta raises on an unpublished weight', False, 'no raise')
except ValueError as exc:
    # `thin` is a real Phosphor weight upstream and is NOT in the Builder's pack, which is the
    # interesting half: the message has to say which weights this name actually ships as.
    check('icon_meta raises on an unpublished weight, naming the ones that ship',
          'regular' in str(exc) and 'fill' in str(exc), str(exc))

entry = icons.icon_meta('ArrowRight')
check('icon_meta returns exactly {name, weight, raw}',
      set(entry) == {'name', 'weight', 'raw'}, sorted(entry))
check('the emitted raw is real markup, not a stub',
      entry['raw'].startswith('<svg') and '<path' in entry['raw'])

check('the five Builder spinners resolve',
      sorted(icons.custom_names()) == ['spinner1', 'spinner2', 'spinner3', 'spinner4',
                                        'spinner5'], icons.custom_names())
check('a custom icon carries the weight the Builder publishes it under',
      icons.custom_icon_meta('spinner1')['weight'] == 'regular')
try:
    icons.custom_icon_meta('spinner9')
    check('custom_icon_meta raises on a name the Builder does not publish', False, 'no raise')
except ValueError as exc:
    check('custom_icon_meta raises on a name the Builder does not publish',
          'spinner1' in str(exc), str(exc))

check('suggestions are returned for a near miss', 'ArrowRight' in icons.suggest('ArrowRigth'),
      icons.suggest('ArrowRigth'))

# ------------------------------------------------------------------------------------- FIRES
print('\nFIRES on a name the renderer cannot resolve:')

fires('an invented phosphor name', doc_with(icon_el('el_a', 'CloseX')), 'draws BLANK')
fires('a real name at a weight the bundle lacks',
      doc_with(icon_el('el_a', 'Star', 'thin')), 'ships as')
fires('an invented name on a `leadingIcon`',
      doc_with(icon_el('el_a', 'CloseX', key='leadingIcon')), 'draws BLANK')

_two = run(doc_with(icon_el('el_a', 'CloseX'), icon_el('el_b', 'OpenY')))
check('one finding per distinct unknown name', len(_two) == 2, f'got {_two!r}')

_dupe = run(doc_with(icon_el('el_a', 'CloseX'), icon_el('el_b', 'CloseX')))
check('the same unknown name twice is reported once', len(_dupe) == 1, f'got {_dupe!r}')

# ------------------------------------------------------------------------------------ SILENT
print('\nSILENT on real builder output:')

for path, doc in corpus():
    silent(f'{os.path.basename(path)} ({os.path.basename(os.path.dirname(path))})', doc)

silent('a `custom` icon under a name the Builder publishes',
       doc_with(icon_el('el_a', 'spinner1', kind='custom')))
silent('a `custom` icon under any other name — custom renders from its own declared raw',
       doc_with(icon_el('el_a', 'houseStyleGlyph', kind='custom')))
silent('an icon element with no weight — the older name/weight check owns that one',
       doc_with(icon_el('el_a', 'Star', weight=None)))

print()
if fails:
    print(f'{len(fails)} FAILED')
    for line in fails:
        print(f'  - {line}')
    sys.exit(1)
print('all passed')
