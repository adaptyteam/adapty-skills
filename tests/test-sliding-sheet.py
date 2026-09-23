#!/usr/bin/env python3
"""Calibration for the sliding-sheet checks in `references/verify-config.py`.

Repo-only. Runs the shipped script as a subprocess -- never imports it, so nothing writes a
`__pycache__` into `references/`.

A `sliding-sheet` is the "Overlay" hero: a screen-root panel that starts `startPosition`% up
from the bottom and rides over the fixed cover band as the screen scrolls. Read from the
transform service source (`attachRootSlidingSheetHeroCover` and neighbours): it looks for the
sheet among the ROOT children only, turns every other root element into the cover band, and
lifts a footer found directly inside the sheet to the screen's pinned bar. From the builder's
schema: `parentRule: root`, `singleton`, `startPosition` 0..100, and the footer's parent rule
widened to root OR a direct child of the sheet. And from QA of the feature: a tap on an element in
the cover band does not register on Android (shipped as a known SDK limitation).

    FIRES   -- a sheet nested in a stack; two sheets; startPosition out of range or not a number;
               a footer nested in a stack (with and without a sheet on the screen); a sheet with
               no fill; a tappable element in the cover band
    SILENT  -- a correct sheet screen; a footer directly inside the sheet; a tappable element
               inside the sheet; a tappable cover element when the sheet is statically hidden;
               a footer at the root beside a sheet; all 12 real exports

THE CORPUS CANNOT CALIBRATE THE SHEET CHECKS: 0 of the 12 tracked and raw exports contain a
sliding sheet, so "silent on the corpus" is vacuous for every check keyed on one. The SILENT
cases built from real export screens are what make those checks discriminating. The footer
placement check IS calibrated by the corpus: every real footer is a root child and it stays
silent on all of them.

Usage: python3 tests/test-sliding-sheet.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'skills', 'flow-generator', 'references', 'verify-config.py')
BASE = os.path.join(ROOT, 'tests', 'fixtures', 'onboarding-multilocale.json')

MINE = ('sliding sheet', 'is nested inside another element', 'cover band above the sliding sheet')

fails = []


def run(doc):
    """Every sliding-sheet finding the checker printed. Exit 2 is a checker bug, not a clean
    run -- the top-level guard prints `CHECKER ERROR` to stdout, so a harness that only watched
    stderr would read a crash as "no findings" and pass every SILENT case vacuously."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        result = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if 'Traceback' in result.stderr or result.returncode == 2:
        raise AssertionError(f'verify-config.py failed (exit {result.returncode}):\n'
                             f'{result.stdout}\n{result.stderr}')
    return [ln for ln in result.stdout.splitlines() if any(f in ln for f in MINE)]


def fires(name, doc, fragment):
    hits = run(doc)
    if not any(fragment in line for line in hits):
        fails.append(f'{name}: expected a finding containing {fragment!r}, got {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def silent(name, doc):
    hits = run(doc)
    if hits:
        fails.append(f'{name}: expected no sliding-sheet finding, got {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def sheet(eid='el_sheet', **props):
    p = {'startPosition': 55, 'width': {'type': 'fill'}, 'height': {'type': 'hug'},
         'layout': {'direction': 'vertical', 'alignH': 'center', 'alignV': 'start',
                    'distribution': {'type': 'gap', 'gap': 16}},
         'padding': {'top': 24, 'right': 16, 'bottom': 16, 'left': 16},
         'borderRadius': {'tl': 20, 'tr': 20, 'bl': 0, 'br': 0},
         'fill': [{'type': 'color', 'color': {'type': 'hex', 'hex': '#FFFFFF', 'opacity': 100}}]}
    p.update(props)
    return {'id': eid, 'type': 'sliding-sheet', 'caption': 'Sliding sheet', 'props': p,
            'states': []}


def plain(eid, kind='stack', tap=False):
    e = {'id': eid, 'type': kind, 'props': {'width': {'type': 'fill'}, 'height': {'type': 'hug'},
         'layout': {'direction': 'vertical', 'alignH': 'start', 'alignV': 'start',
                    'distribution': {'type': 'gap', 'gap': 0}},
         'position': {'type': 'relative'}}, 'states': []}
    if kind == 'footer':
        e['props']['fill'] = [{'type': 'color',
                               'color': {'type': 'hex', 'hex': '#FFFFFF', 'opacity': 100}}]
    if tap:
        e['interactions'] = [{'id': 'int_' + eid, 'trigger': 'tap',
                              'actions': [{'id': 'act_' + eid, 'type': 'closeFlow'}]}]
    return e


def doc_with(hierarchy, *elements, sheet_on_first=True):
    """The first screen of a real export, its existing root children moved into `hierarchy`'s
    placeholder `'*'` so every case keeps real builder content around what it tests."""
    d = json.load(open(BASE))
    d = d.get('config', d)
    s = d['screens'][0]
    m, h = s['elements']['map'], s['elements']['hierarchy']
    real = h['children']
    for e in elements:
        m[e['id']] = e

    def expand(items):
        out = []
        for it in items:
            if it == '*':
                out.extend(copy.deepcopy(real))
            else:
                it = dict(it)
                if 'children' in it:
                    it['children'] = expand(it['children'])
                out.append(it)
        return out
    h['children'] = expand(hierarchy)
    return d


print('verify-config.py: sliding sheet')

# ---- the correct shapes ----------------------------------------------------------------
silent('a sheet at the root holding the real content',
       doc_with([{'id': 'el_sheet', 'children': ['*']}], sheet()))
silent('a sheet with an image-free cover beside it, holding the real content',
       doc_with([{'id': 'el_logo'}, {'id': 'el_sheet', 'children': ['*']}],
                sheet(), plain('el_logo')))
silent('a footer directly inside the sheet',
       doc_with([{'id': 'el_sheet', 'children': ['*', {'id': 'el_foot'}]}],
                sheet(), plain('el_foot', 'footer')))
silent('a footer at the root beside a sheet',
       doc_with([{'id': 'el_sheet', 'children': ['*']}, {'id': 'el_foot'}],
                sheet(), plain('el_foot', 'footer')))
silent('a tappable close button INSIDE the sheet',
       doc_with([{'id': 'el_sheet', 'children': [{'id': 'el_close'}, '*']}],
                sheet(), plain('el_close', tap=True)))
silent('a tappable footer at the root is the pinned bar, not the cover',
       doc_with([{'id': 'el_sheet', 'children': ['*']},
                 {'id': 'el_foot', 'children': [{'id': 'el_cta'}]}],
                sheet(), plain('el_foot', 'footer'), plain('el_cta', tap=True)))
silent('a statically hidden sheet makes no cover, so a tap beside it is fine',
       doc_with([{'id': 'el_close'}, {'id': 'el_sheet', 'children': ['*']}],
                sheet(visibility={'type': 'hidden'}), plain('el_close', tap=True)))
silent('startPosition absent takes the default',
       doc_with([{'id': 'el_sheet', 'children': ['*']}],
                {**sheet(), 'props': {k: v for k, v in sheet()['props'].items()
                                      if k != 'startPosition'}}))
silent('startPosition at both ends of the range',
       doc_with([{'id': 'el_sheet', 'children': ['*']}], sheet(startPosition=0)))
silent('startPosition 100', doc_with([{'id': 'el_sheet', 'children': ['*']}],
                                     sheet(startPosition=100)))

# ---- placement ---------------------------------------------------------------------------
fires('a sheet nested inside a stack',
      doc_with([{'id': 'el_wrap', 'children': [{'id': 'el_sheet', 'children': ['*']}]}],
               sheet(), plain('el_wrap')),
      'is not a direct child of the screen root')
fires('two sheets on one screen',
      doc_with([{'id': 'el_sheet', 'children': ['*']}, {'id': 'el_sheet2'}],
               sheet(), sheet('el_sheet2')),
      '2 sliding sheets')
fires('a footer nested in a stack inside the sheet',
      doc_with([{'id': 'el_sheet', 'children': ['*', {'id': 'el_wrap',
                'children': [{'id': 'el_foot'}]}]}],
               sheet(), plain('el_wrap'), plain('el_foot', 'footer')),
      'is nested inside another element')
fires('a footer nested in a stack on a screen with no sheet',
      doc_with(['*', {'id': 'el_wrap', 'children': [{'id': 'el_foot'}]}],
               plain('el_wrap'), plain('el_foot', 'footer')),
      'is nested inside another element')

# ---- props -------------------------------------------------------------------------------
for bad_sp in (101, -1, '55', True):
    fires(f'startPosition {bad_sp!r}',
          doc_with([{'id': 'el_sheet', 'children': ['*']}], sheet(startPosition=bad_sp)),
          'has startPosition')
fires('a sheet with no fill',
      doc_with([{'id': 'el_sheet', 'children': ['*']}],
               {**sheet(), 'props': {k: v for k, v in sheet()['props'].items() if k != 'fill'}}),
      'has no fill')

# ---- taps in the cover band --------------------------------------------------------------
fires('a tappable close button in the cover band',
      doc_with([{'id': 'el_close'}, {'id': 'el_sheet', 'children': ['*']}],
               sheet(), plain('el_close', tap=True)),
      'el_close is tappable and sits in the cover band')
fires('a tappable element nested deep in the cover band',
      doc_with([{'id': 'el_top', 'children': [{'id': 'el_close'}]},
                {'id': 'el_sheet', 'children': ['*']}],
               sheet(), plain('el_top'), plain('el_close', tap=True)),
      'el_close is tappable and sits in the cover band')

# ---- the corpus --------------------------------------------------------------------------
for path in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', '*.json'))
                   + glob.glob(os.path.join(ROOT, 'tests', 'fixtures-raw', '*.json'))):
    d = json.load(open(path))
    silent(f'real export {os.path.relpath(path, ROOT)}', d)

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all passed')
