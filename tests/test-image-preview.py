#!/usr/bin/env python3
"""Calibration for the `previewValue` check in `references/verify-config.py`.

Repo-only. Runs the shipped script as a subprocess -- never imports it, so nothing writes a
`__pycache__` into `references/`.

Why this file exists. `IImage` is `{id, url, previewValue?}`, and `previewValue` is the base64
thumbnail the renderer paints while the full asset downloads. Absent, the renderer has nothing
to paint and substitutes a transparent 1x1, so the screen shows a hole for as long as the
download takes. Nothing catches it: `flows config validate` returns valid:true either way, the
schema declares the field optional, and `config preview` renders a local file where there is no
download to wait for. The builder's own upload path writes `previewValue` from the API's
`preview_base64` and omits the key when no preview was generated -- the shape reproduced here.

The check is BASELINE-GATED, and that is the load-bearing decision -- on ownership, not on
repairability. An image this draft added is one the agent bound, so the value was in its hands a
command ago or sits in whatever other flow already carries the asset; an image that arrived with
a fetched config was bound by someone else, and adding a preview there is a change to report and
offer rather than to make on the way past. Hence both directions below are about PROVENANCE, not
shape. The message is asserted too: the finding is only actionable if it says where the value
comes from, and that is the half an agent turns into "well, the field must be optional".

    FIRES   -- an image the draft added, element form and fill form
            -- a fill inside `components`, not just under `screens`
            -- an image whose baseline DID carry a preview and the draft dropped it
    SAYS    -- the finding names the upload and the lift-it-from-another-config route
    SILENT  -- all 12 real exports with no baseline, and each against itself
            -- an image inherited from the baseline already missing its preview
            -- a placeholder (empty `values`), which the empty-image check owns
            -- a `_meta.fonts` url, which is a url and is not an image

Usage: python3 tests/test-image-preview.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'skills', 'flow-generator', 'references', 'verify-config.py')
CORPUS = os.path.join(ROOT, 'tests', 'fixtures')
RAW = os.path.join(ROOT, 'tests', 'fixtures-raw')

MARKER = 'previewValue'
URL = 'https://public-media.adapty.io/public/ef/9b/ef9b995d/hero.png'
PREVIEW = 'UklGRhQJAABXRUJQVlA4IAgJAAAwSQCdASos'

fails = []


def run(doc, baseline=None):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        argv = [sys.executable, VERIFY]
        if baseline is not None:
            base = os.path.join(tmp, 'b.json')
            json.dump(baseline, open(base, 'w'))
            argv += ['--baseline', base]
        result = subprocess.run(argv + [path], capture_output=True, text=True)
    if 'Traceback' in result.stderr:
        raise AssertionError(f'verify-config.py crashed:\n{result.stderr}')
    if result.returncode == 2:
        raise AssertionError(f'verify-config.py reported a CHECKER ERROR:\n{result.stdout}')
    return [line for line in result.stdout.splitlines() if MARKER in line]


def fires(name, doc, baseline=None):
    hits = run(doc, baseline)
    print(f'  {"ok   " if hits else "FAIL "} {name}')
    if not hits:
        fails.append(f'{name}: expected a previewValue finding, got none')


def silent(name, doc, baseline=None):
    hits = run(doc, baseline)
    print(f'  {"ok   " if not hits else "FAIL "} {name}')
    if hits:
        fails.append(f'{name}: expected no previewValue finding, got {hits!r}')


def says(name, want, doc, baseline=None):
    hits = run(doc, baseline)
    got = ' '.join(hits)
    ok = bool(hits) and all(w in got for w in want)
    print(f'  {"ok   " if ok else "FAIL "} {name}')
    if not ok:
        fails.append(f'{name}: {got[:160]!r} does not carry {want!r}')


def img_value(preview=True, url=URL):
    v = {'id': '533693', 'url': url}
    if preview:
        v['previewValue'] = PREVIEW
    return v


def image_el(eid='el_img', preview=True, url=URL, empty=False):
    content = ({'_localizable': True, 'values': {}} if empty else
               {'_localizable': True, 'values': {'en': img_value(preview, url)}})
    return {'id': eid, 'type': 'image', 'states': [], 'props': {
        'image': content, 'objectFit': 'cover', 'width': {'type': 'fill'},
        'height': {'type': 'hug'}, 'position': {'type': 'relative'}}}


def doc_with(element, *, screen_fill=None, fonts=()):
    screen_props = {'safeArea': True, 'scrollable': False,
                    'padding': {'top': 8, 'left': 16, 'right': 16, 'bottom': 8},
                    'fill': screen_fill or {'type': 'color',
                                            'color': {'type': 'hex', 'hex': '#FFFFFF'}},
                    'layout': {'alignH': 'start', 'alignV': 'start', 'direction': 'vertical',
                               'distribution': {'type': 'gap', 'gap': 8}}}
    return {
        'schemaVersion': 10, 'defaultLocale': 'en',
        'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}],
        'theme': {'colors': [], 'typography': []},
        '_meta': {'screens': {}, 'icons': [], 'fonts': list(fonts)},
        'screens': [{'id': 'scr_1', 'caption': 'Paywall', 'selectableGroups': [],
                     'props': screen_props,
                     'elements': {
            'map': {element['id']: element},
            'hierarchy': {'id': 'root',
                          'children': [{'id': element['id'], 'children': []}]}}}]}


EMPTY_BASE = doc_with(image_el(empty=True))

# ------------------------------------------------------------------------- FIRES
print('FIRES on an image this draft added with no previewValue:')
fires('element form, preview missing', doc_with(image_el(preview=False)), EMPTY_BASE)
fires('element form, previewValue empty string',
      doc_with({**image_el(), 'props': {**image_el()['props'], 'image': {
          '_localizable': True,
          'values': {'en': {'id': '1', 'url': URL, 'previewValue': '   '}}}}}), EMPTY_BASE)

_fill = doc_with(image_el(eid='el_t', empty=True), screen_fill=[
    {'type': 'image', 'image': {'id': '1', 'url': URL}}])
fires('background fill form, preview missing', _fill, EMPTY_BASE)

_component = doc_with(image_el(eid='el_t', empty=True))
_component['components'] = {'cmp_1': {
    'map': {'el_c': {'id': 'el_c', 'type': 'stack', 'states': [], 'props': {
        'fill': [{'type': 'image', 'image': {'id': '1', 'url': URL}}],
        'width': {'type': 'fill'}, 'height': {'type': 'hug'},
        'position': {'type': 'relative'}}}},
    'hierarchy': {'id': 'root', 'children': [{'id': 'el_c', 'children': []}]}}}
fires('a fill inside `components`, which is why the walk is not screens-only',
      _component, EMPTY_BASE)

_regressed = doc_with(image_el(preview=False))
fires('the baseline HAD a preview for this url and the draft dropped it',
      _regressed, doc_with(image_el(preview=True)))

# -------------------------------------------------------------------------- SAYS
print('\nSAYS where to get the value back, because a dead end is what gets rationalised away:')
says('the finding names the upload, the config lookup, and what an empty lookup means',
     ['media upload --json', 'config get', 'not that the field is optional'],
     doc_with(image_el(preview=False)), EMPTY_BASE)

# ------------------------------------------------------------------------- SILENT
print('\nSILENT where the finding would be wrong or unactionable:')
silent('element form, preview present', doc_with(image_el()), EMPTY_BASE)
silent('inherited: baseline carries the same url already without a preview',
       doc_with(image_el(preview=False)), doc_with(image_el(preview=False)))
silent('a placeholder — the empty-values check owns that one, not this one',
       doc_with(image_el(empty=True)), EMPTY_BASE)
silent('a `_meta.fonts` url is a url and is not an image',
       doc_with(image_el(), fonts=[{'id': 'f1', 'family': 'Inter',
                                    'url': 'https://public-media.adapty.io/f/inter.ttf'}]),
       EMPTY_BASE)
silent('no --baseline at all: provenance is unknown, so nothing is claimed',
       doc_with(image_el(preview=False)))

print('\nSILENT on every real export (no baseline, and each against itself):')
for path in sorted(glob.glob(os.path.join(CORPUS, '*.json')) +
                   glob.glob(os.path.join(RAW, '*.json'))):
    doc = json.load(open(path))
    name = os.path.relpath(path, ROOT)
    silent(f'{name} (no baseline)', doc)
    silent(f'{name} (against itself)', doc, doc)

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all cases pass')
