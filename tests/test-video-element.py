#!/usr/bin/env python3
"""Calibration for the two `video` checks in `references/verify-config.py`.

Repo-only. Runs the shipped script as a subprocess -- never imports it, so nothing writes a
`__pycache__` into `references/`.

Why this file exists. `flows media upload` REFUSES a clip: `validation_error: target_format:
value is not a valid enumeration member; permitted: 'JPEG', 'JPEG2000', 'WEBP', 'PNG', 'SVG'`.
So a video source can never be bound from the CLI, and the correct artifact is a real `video`
element with no source, styled to the box the user's clip will land in, plus a spoken handoff:
open the flow in the builder and upload it there. Two things then need a mechanical slot,
because every publish-time gate is blind to both (measured 2026-09-10 against the real transform
service in `app_finance` -- an unset `video` returns `valid: true, issues: []` in the styled, the
empty-`values`-map and the bare forms alike, and the JSON-schema check passes them too):

    FIRES   -- a `video` with no source at all (the upload the user still owes)
    FIRES   -- a `video` with `height: hug` (measured: an unset clip draws an arbitrary 256pt
               placeholder, the renderer's default and the same box an empty `image` draws, so
               the layout that was previewed is not the one that ships)
    SILENT  -- a video bound three ways (`customMediaID`, a flat `{videoUrl}`, a per-locale
               `values` map), a fixed-height video, and all 12 real exports

THE CORPUS CANNOT CALIBRATE THE FIRST CHECK, and that is stated rather than discovered later:
0 of the 12 tracked and raw exports contain a `video` element at all, so "silent on the corpus"
is VACUOUS here -- it would hold just as well for a check that fired on every video ever
written. The bound cases below are what make it discriminating, and they are the assertions to
look at first if this check is ever suspected of over-firing.

NOT SHIPPED, and recorded so nobody re-adds it from the shape of this file: a FAKE-VIDEO
detector (a stack with a Play icon standing in for the element). There is no Play-ish icon
anywhere in `component-catalog.json` or in the 12 exports, so such a guard would be calibrated
against nothing but a remembered shape in both directions -- finding 19's disqualified pattern
-- and a "Watch demo" button with a play glyph and a label is legitimate and common, so the
false-positive risk is real and unmeasurable. The lookalike is prevented at authoring time
instead: `flowkit.video()` makes the correct element the easy one, and both catalog templates
carry it.

Usage: python3 tests/test-video-element.py    # 0 all pass, 1 a case regressed
"""
import glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'skills', 'flow-generator', 'references', 'verify-config.py')
CORPUS = os.path.join(ROOT, 'tests', 'fixtures')
RAW = os.path.join(ROOT, 'tests', 'fixtures-raw')
CATALOG = os.path.join(ROOT, 'skills', 'flow-generator', 'references',
                       'component-catalog.json')

NO_SOURCE = 'video element(s) with NO source'
HUG = 'video element(s) with height: hug'

fails = []


def run(doc):
    """Every `video` finding the checker printed. Exit 2 is a checker bug, not a clean run --
    the top-level guard prints `CHECKER ERROR` to stdout, so a harness that only watched stderr
    would read a crash as "no findings" and pass every SILENT case vacuously."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        result = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if 'Traceback' in result.stderr or result.returncode == 2:
        raise AssertionError(f'verify-config.py failed (exit {result.returncode}):\n'
                             f'{result.stdout}\n{result.stderr}')
    return [ln for ln in result.stdout.splitlines() if NO_SOURCE in ln or HUG in ln]


def fires(name, doc, fragment):
    hits = run(doc)
    if not any(fragment in line for line in hits):
        fails.append(f'{name}: expected a finding containing {fragment!r}, got {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def silent(name, doc, fragment=None):
    hits = [h for h in run(doc) if fragment is None or fragment in h]
    if hits:
        fails.append(f'{name}: expected no video finding, got {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def screen_with(*elements):
    """One screen carrying `elements` beside a plain text node."""
    label = {'id': 'el_t', 'type': 'text', 'states': [], 'props': {
        'width': {'type': 'fill'}, 'height': {'type': 'hug'}, 'align': 'left',
        'layout': 'auto-height', 'decoration': 'none', 'position': {'type': 'relative'},
        'font': {'preset': 'body'}, 'color': {'type': 'hex', 'hex': '#111111'},
        'content': {'_localizable': True, 'values': {'en': [
            {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Watch'}]}]}}}}
    node_map = {'el_t': label}
    children = [{'id': 'el_t', 'children': []}]
    for el in elements:
        node_map[el['id']] = el
        children.append({'id': el['id'], 'children': []})
    return {
        'schemaVersion': 10, 'defaultLocale': 'en',
        'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}],
        'theme': {'colors': [], 'typography': []},
        '_meta': {'screens': {}, 'icons': [], 'fonts': []},
        'screens': [{'id': 'scr_1', 'caption': 'Demo', 'selectableGroups': [],
                     'props': {'safeArea': True, 'scrollable': False,
                               'padding': {'top': 8, 'left': 16, 'right': 16, 'bottom': 8},
                               'fill': {'type': 'color',
                                        'color': {'type': 'hex', 'hex': '#FFFFFF'}},
                               'layout': {'alignH': 'start', 'alignV': 'start',
                                          'direction': 'vertical',
                                          'distribution': {'type': 'gap', 'gap': 8}}},
                     'elements': {'map': node_map,
                                  'hierarchy': {'id': 'root', 'children': children}}}]}


def video(eid='el_v', *, height=('fixed', 200), source=None, corner=16):
    props = {'width': {'type': 'fill'}, 'objectFit': 'cover', 'loop': True,
             'position': {'type': 'relative'},
             'borderRadius': {'tl': corner, 'tr': corner, 'bl': corner, 'br': corner}}
    props['height'] = ({'type': 'fixed', 'value': height[1]} if height[0] == 'fixed'
                       else {'type': height[0]})
    if source:
        props.update(source)
    return {'id': eid, 'type': 'video', 'states': [], 'props': props}


# A clip the user bound in the builder, in each of the three shapes the schema allows.
BOUND_MEDIA_ID = {'customMediaID': 'cm_9f21c0'}
BOUND_FLAT = {'video': {'videoUrl': 'https://cdn.example/clip.mp4',
                        'previewUrl': 'https://cdn.example/clip.jpg',
                        'width': 1080, 'height': 1920}}
BOUND_LOCALIZED = {'video': {'_localizable': True, 'values': {'en': {
    'videoUrl': 'https://cdn.example/clip.mp4',
    'previewUrl': 'https://cdn.example/clip.jpg', 'width': 1080, 'height': 1920}}}}

# ------------------------------------------------------------------------- FIRES
print('FIRES on a video the user still has to upload:')
fires('a styled video with no source', screen_with(video()), NO_SOURCE)
fires('a bare video with no styling either',
      screen_with({'id': 'el_v', 'type': 'video', 'states': [],
                   'props': {'position': {'type': 'relative'}}}), NO_SOURCE)
fires('an empty per-locale values map counts as unset',
      screen_with(video(source={'video': {'_localizable': True, 'values': {}}})), NO_SOURCE)
fires('a blank customMediaID counts as unset',
      screen_with(video(source={'customMediaID': '   '})), NO_SOURCE)

_two = run(screen_with(video('el_v1'), video('el_v2')))
if any('el_v1' in h and 'el_v2' in h for h in _two if NO_SOURCE in h):
    print('  ok    names every unset video, not just the first')
else:
    fails.append(f'expected both ids in one finding, got {_two!r}')
    print('  FAIL  names every unset video, not just the first')

print('\nFIRES on a hug height, whatever the source:')
fires('an unset video with height: hug', screen_with(video(height=('hug',))), HUG)
fires('a BOUND video with height: hug still reflows when the file is swapped',
      screen_with(video(height=('hug',), source=BOUND_FLAT)), HUG)

# ------------------------------------------------------------------------- SILENT
# These are the discriminating cases: the corpus has no video at all, so a check that fired on
# every video would pass every corpus assertion below.
print('\nSILENT once the clip is bound (the cases that make the check discriminating):')
silent('bound by customMediaID', screen_with(video(source=BOUND_MEDIA_ID)), NO_SOURCE)
silent('bound by a flat {videoUrl, previewUrl}', screen_with(video(source=BOUND_FLAT)),
       NO_SOURCE)
silent('bound by a per-locale values map', screen_with(video(source=BOUND_LOCALIZED)),
       NO_SOURCE)

print('\nSILENT on a fixed height:')
silent('a fixed-height video', screen_with(video(source=BOUND_FLAT)))
silent('a fill-height video is not a hug', screen_with(video(height=('fill',),
                                                             source=BOUND_FLAT)))

print('\nSILENT on a screen with no video at all:')
silent('an image placeholder is the image check\'s business, not this one',
       screen_with({'id': 'el_i', 'type': 'image', 'states': [], 'props': {
           'width': {'type': 'fill'}, 'height': {'type': 'fixed', 'value': 200},
           'objectFit': 'cover', 'position': {'type': 'relative'},
           'image': {'_localizable': True, 'values': {}}}}))

_paths = sorted(glob.glob(os.path.join(CORPUS, '*.json'))) + \
         sorted(glob.glob(os.path.join(RAW, '*.json')))
print(f'\nSILENT on the tracked corpus ({len(_paths)} configs'
      f'{" — RAW ABSENT, tracked only" if not os.path.isdir(RAW) else ""})'
      f' — VACUOUS for the no-source check, see the module docstring:')
for _p in _paths:
    silent(os.path.basename(_p), json.load(open(_p)))

# ------------------------------------------------------------------- catalog contract
# `patterns.md` tells an agent that filling a template beats assembling a skeleton, so a
# template that carried a fabricated source, or a hug height, would put the recommended path
# straight into the thing the checks above exist to catch -- finding 15's class.
print('\nThe shipped catalog templates are the shape the checks expect:')
_cat = json.load(open(CATALOG))
_vids = [c for c in _cat['components'] if 'video' in json.dumps(c.get('template', {}))]
if not _vids:
    fails.append('no video template in component-catalog.json — the recommended path is gone')
    print('  FAIL  at least one video template ships')
else:
    print(f'  ok    {len(_vids)} video template(s) ship ({", ".join(c["id"] for c in _vids)})')

_SOURCE_KEYS = ('videoUrl', 'previewUrl', 'customMediaID')


def _videos(node, out):
    if isinstance(node, dict):
        if node.get('type') == 'video':
            out.append(node)
        for v in node.values():
            _videos(v, out)
    elif isinstance(node, list):
        for v in node:
            _videos(v, out)
    return out


for _c in _vids:
    _els = _videos(_c['template'], [])
    _bad = [k for el in _els for k in _SOURCE_KEYS if k in json.dumps(el.get('props', {}))]
    if _bad:
        fails.append(f'{_c["id"]}: template carries a fabricated source ({_bad}) — there is no '
                     f'CLI upload path, so any URL in a template is invented')
        print(f'  FAIL  {_c["id"]} carries no source')
    else:
        print(f'  ok    {_c["id"]} carries no source')
    _hug = [el['id'] if 'id' in el else '<unnamed>' for el in _els
            if (el.get('props') or {}).get('height', {}).get('type') == 'hug']
    if _hug:
        fails.append(f'{_c["id"]}: template video has height: hug, which draws an arbitrary '
                     f'256pt placeholder the clip will not match')
        print(f'  FAIL  {_c["id"]} gives its video a fixed height')
    else:
        print(f'  ok    {_c["id"]} gives its video a fixed height')
    _plain = [el for el in _els if 'borderRadius' not in (el.get('props') or {})]
    if _plain:
        fails.append(f'{_c["id"]}: template video carries no borderRadius — a placeholder has '
                     f'to fit the design it sits in, not read as a default box')
        print(f'  FAIL  {_c["id"]} styles its video')
    else:
        print(f'  ok    {_c["id"]} styles its video')

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
