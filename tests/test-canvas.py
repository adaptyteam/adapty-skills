#!/usr/bin/env python3
"""Checks for `references/canvas.py`, the screen map.

Repo-only. Imports the shipped script with bytecode off so nothing writes a `__pycache__` into
`references/`, and runs it once as a subprocess to cover the HTML and text outputs.

What a wrong map costs: it is shown to the user as the answer to "how are my screens connected",
so a missing arrow reads as a dead end and a missing branch reads as a straight line. So every
kind of connection the config can express is pinned here, in both directions.

    ARROWS  -- a tap `navigate`, each case of a conditional plus its `otherwise`, `navigateNext`,
               a timer's end, a target that does not exist
    BADGES  -- purchase, close, back: they leave the screen without a fixed target, so no arrow
    FLAGS   -- a branch point; a screen nothing leads to; a screen with no way out
    NOT     -- a back button beside Continue is not a branch point

Usage: python3 tests/test-canvas.py    # 0 all pass, 1 a case regressed
"""
import importlib.util, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
SCRIPT = os.path.join(REFS, 'canvas.py')
FIX = os.path.join(ROOT, 'tests', 'fixtures')

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('canvas', SCRIPT)
canvas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canvas)

fails = []


def check(name, ok):
    print(('ok   ' if ok else 'FAIL ') + name)
    if not ok:
        fails.append(name)


def graph(d):
    screens, edges, badges = canvas.extract(d)
    level, cols, unreachable = canvas.layout(screens, edges)
    return screens, edges, badges, unreachable, canvas.branch_points(screens, edges, level)


def button(eid, actions, trigger='tap'):
    return {'id': eid, 'type': 'stack', 'props': {},
            'interactions': [{'id': 'i' + eid, 'trigger': trigger, 'actions': actions}]}


def screen(sid, *elements):
    return {'id': sid, 'caption': sid, 'props': {},
            'elements': {'map': {e['id']: e for e in elements},
                         'hierarchy': {'id': 'root', 'children': [{'id': e['id']} for e in elements]}}}


def nav(t):
    return {'id': '', 'type': 'navigate', 'payload': {'type': 'screen', 'screen': t}}


# --- real exports ------------------------------------------------------------------------------

d = canvas.load(os.path.join(FIX, 'onboarding-quiz-paywall.json'))
sc, ed, bd, un, br = graph(d)
ids = {s.name: s.id for s in sc}
quiz = ids['Quiz']
outs = {b: e for (a, b), e in ed.items() if a == quiz}
check('quiz: one arrow per case plus otherwise', set(outs) == {ids['Rock'], ids['Hip hop']})
check('quiz: case arrows are branch kind', all(e['kind'] == 'branch' for e in outs.values()))
check('quiz: the default case is labelled otherwise', outs.get(ids['Hip hop'], {}).get('labels') == ['otherwise'])
check('quiz: a case reads as the option the person picked',
      any('Rock' in lbl for lbl in outs.get(ids['Rock'], {}).get('labels', [])))
check('quiz: is a branch point', quiz in br)
check('quiz: purchase and close are badges on the paywall',
      {'buys', 'closes flow'} <= set(bd[ids['Paywall After']]))
check('quiz: nothing unreachable', not un)

d = canvas.load(os.path.join(FIX, 'onboarding-multilocale.json'))
sc, ed, bd, un, br = graph(d)
ids = {s.name: s.id for s in sc}
check('multilocale: Agree / Decline is a branch point', ids['Commitment'] in br)
check('multilocale: a back arrow beside Continue is NOT a branch point', ids['Profile'] not in br)
check('multilocale: a tap edge is labelled with the button text',
      ed.get((ids['Welcome'], ids['Create account']), {}).get('labels') == ['“Get started”'])

# --- constructed cases -------------------------------------------------------------------------

d = {'screens': [
    screen('a', button('b1', [{'id': '', 'type': 'navigateNext'}])),
    screen('b', button('t1', [nav('c')], trigger='timer-end')),
    screen('c', button('b2', [nav('nowhere')])),
    screen('d', button('b3', [nav('a')])),
    screen('e'),
]}
sc, ed, bd, un, br = graph(d)
check('navigateNext draws an arrow to the next screen', ('a', 'b') in ed)
check('a timer end draws an arrow labelled "after timer"', ed.get(('b', 'c'), {}).get('labels') == ['after timer'])
check('a target that does not exist still draws (to a missing screen)', ('c', 'nowhere') in ed)
check('a screen nothing leads to is flagged', {'d', 'e'} <= un)
text = canvas.as_text(sc, ed, bd, un, br)
block_e = text[text.index('▢ e'):]
check('text: a screen with no way out says so', '(no way out)' in block_e)
check('text: a screen with an arrow out does not', '(no way out)' not in text[:text.index('▢ e')])
check('text: an unreachable screen says so', '(nothing leads here)' in text)
check('text: a missing target says so', 'nowhere (missing)' in text)

d = {'screens': [screen('a', button('b1', [{'id': '', 'type': 'navigateBack'}, {'id': '', 'type': 'closeFlow'}]))]}
sc, ed, bd, un, br = graph(d)
check('back and close are badges, not arrows', not ed and set(bd['a']) == {'back', 'closes flow'})

# --- the script end to end ---------------------------------------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    out = os.path.join(tmp, 'map.html')
    r = subprocess.run([sys.executable, SCRIPT, os.path.join(FIX, 'onboarding-multilocale.json'),
                        '--out', out], capture_output=True, text=True)
    page = open(out).read() if os.path.exists(out) else ''
    check('html: exits 0 and writes the page', r.returncode == 0 and '<svg' in page)
    check('html: one card per screen', page.count('class="node') == 7)
    check('html: a branch point is flagged on its card', 'flag branch' in page)
    check('html: no stray template braces', '{{' not in page and '}}' not in page)
    r = subprocess.run([sys.executable, SCRIPT, os.path.join(tmp, 'absent.json')],
                       capture_output=True, text=True)
    check('a missing file exits 2 with a message, not a traceback',
          r.returncode == 2 and 'Traceback' not in r.stderr)
    src = os.path.join(tmp, 'flow.json')
    with open(os.path.join(FIX, 'onboarding-quiz-paywall.json')) as f, open(src, 'w') as g:
        g.write(f.read())
    r = subprocess.run([sys.executable, SCRIPT, src, '--text'], capture_output=True, text=True)
    check('--text prints the map and writes no file',
          r.returncode == 0 and '◆ Quiz' in r.stdout and not os.path.exists(os.path.join(tmp, 'canvas.html')))

print(f'\n{len(fails)} failed' if fails else '\nall passed')
sys.exit(1 if fails else 0)
