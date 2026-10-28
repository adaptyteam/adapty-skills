#!/usr/bin/env python3
"""Calibration for the partial state-override check in `references/verify-config.py`.

Repo-only. Runs the shipped script as a subprocess -- never imports it, so nothing writes a
`__pycache__` into `references/`.

Why this file exists. A prop in `propsByState.<state>` replaces the base prop whole: a key the
override leaves out falls back to its default, it is not inherited. The transformer deep-merged
until October 2026, and `flow-schema.md` trap 17 taught the merge, so a delta override
(`font: {weight}` over a base `font: {preset}`) is the shape an author writes from the old rule.
Nothing else sees it: `flows config validate` accepts both shapes, and the preview draws the
replacement the device draws, so the render looks deliberate.

    FIRES   -- a state prop object that drops a key its base prop has
    SILENT  -- every real export, the catalog, and a colour switched to another variant

Usage: python3 tests/test-state-override.py     # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'verify-config.py')
CORPUS = os.path.join(ROOT, 'tests', 'fixtures')
RAW = os.path.join(ROOT, 'tests', 'fixtures-raw')

PARTIAL = 'a state replaces each prop whole'

fails = []


def run(doc):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json')
        json.dump(doc, open(p, 'w'))
        r = subprocess.run([sys.executable, VERIFY, p], capture_output=True, text=True)
    if 'Traceback' in r.stderr:
        raise AssertionError(f'verify-config.py crashed:\n{r.stderr}')
    return [l for l in r.stdout.splitlines() if PARTIAL in l]


def fires(name, doc, fragment):
    hits = run(doc)
    if not any(fragment in l for l in hits):
        fails.append(f'{name}: expected a warning naming {fragment!r}, got {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def silent(name, doc):
    hits = run(doc)
    if hits:
        fails.append(f'{name}: expected no partial-override warning, got {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def card(selected, *, state='selected', base_extra=None):
    """One selectable card whose `selected` (or other) state carries `selected` as its props."""
    props = {'width': {'type': 'fill'}, 'height': {'type': 'hug'},
             'position': {'type': 'relative'}, 'groupId': 'g', 'default': True,
             'font': {'preset': 'body'},
             'border': {'width': 2, 'color': {'type': 'hex', 'hex': '#000000', 'opacity': 0}},
             'padding': {'top': 16, 'right': 16, 'bottom': 16, 'left': 16}}
    props.update(base_extra or {})
    el = {'id': 'el_C', 'type': 'selectable', 'caption': 'card',
          'states': [{'id': state, 'type': 'system'}], 'props': props,
          'propsByState': {state: selected}}
    return {
        'schemaVersion': 10, 'defaultLocale': 'en',
        'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}],
        'variables': [], 'components': [],
        'theme': {'colors': [{'id': 'ink', 'light': {'hex': '#111111', 'opacity': 100},
                              'dark': {'hex': '#111111', 'opacity': 100}}],
                  'typography': [{'id': 'body', 'size': 14, 'weight': 'regular'}]},
        '_meta': {'icons': [], 'fonts': [], 'screens': {}},
        'screens': [{'id': 'scr_c', 'caption': 'Cards',
                     'selectableGroups': [{'id': 'g', 'type': 'single_choice'}],
                     'props': {'scrollable': True},
                     'elements': {'map': {'el_C': el},
                                  'hierarchy': {'id': 'root', 'children': [{'id': 'el_C'}]}}}]}


COMPLETE = {'font': {'preset': 'body', 'weight': 'bold'},
            'border': {'width': 2, 'color': {'type': 'hex', 'hex': '#FF3C45', 'opacity': 100}},
            'padding': {'top': 16, 'right': 16, 'bottom': 16, 'left': 16}}

# ---------------------------------------------------------------- SILENT: the real corpus
print('SILENT on every real export and the catalog (the false-positive half):')
for path in sorted(glob.glob(os.path.join(CORPUS, '*.json'))):
    silent(f'tracked {os.path.basename(path)}', json.load(open(path)))
for path in sorted(glob.glob(os.path.join(RAW, '*.json'))):
    silent(f'raw {os.path.basename(path)}', json.load(open(path)))
silent('every key repeated, values changed', card(COMPLETE))
silent('a colour switched from a token to a hex is a new value, not a partial one',
       card({'color': {'type': 'hex', 'hex': '#FFFFFF'}},
            base_extra={'color': {'type': 'color-style', 'colorId': 'ink'}}))
silent('a prop the base does not have at all', card({'margin': {'bottom': 8}}))
# The two false positives a test round produced, each on real agent output.
silent('a manual font (own size) in place of the preset draws the same',
       card({'font': {'size': 16, 'weight': 'bold'}}))
silent('a border without `style` draws the same (only `none` changes it)',
       card({'border': {'width': 2, 'color': {'type': 'color-style', 'colorId': 'ink'}}},
            base_extra={'border': {'width': 1, 'style': 'solid',
                                   'color': {'type': 'color-style', 'colorId': 'ink'}}}))
silent('a list prop (fill) is replaced as a value, not compared by key',
       card({'fill': [{'type': 'color', 'color': {'type': 'hex', 'hex': '#FFFFFF'}}]},
            base_extra={'fill': [{'type': 'color', 'color': {'type': 'hex', 'hex': '#000000',
                                                             'opacity': 100}}]}))

# ------------------------------------------------------------------- FIRES: each mechanism
print('\nFIRES on a delta override (the false-negative half):')
fires('a font weight with the base preset left out', card({'font': {'weight': 'bold'}}),
      'font.preset')
fires('a border colour with the width left out',
      card({'border': {'color': {'type': 'hex', 'hex': '#FF3C45', 'opacity': 100}}}),
      'border.width')
fires('an empty padding drops all four sides', card({'padding': {}}), 'padding.top')
fires('a state other than selected (invalid) is checked the same way',
      card({'border': {'color': {'type': 'hex', 'hex': '#FF3C45'}}}, state='invalid'),
      'propsByState.invalid')
_comp = card({'font': {'weight': 'bold'}})
_comp['components'] = {'cmp_1': {'map': {'el_K': copy.deepcopy(
    _comp['screens'][0]['elements']['map']['el_C'])}, 'hierarchy': {'id': 'el_K'}}}
_comp['screens'][0]['elements']['map']['el_C']['propsByState'] = {'selected': COMPLETE}
fires('an element inside a component is checked too', _comp, 'component cmp_1')

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
