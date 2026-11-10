#!/usr/bin/env python3
"""Quiz branching, sibling-flow languages and navigateNext reachability.

Runs both shipped scripts as subprocesses (never imports them, so nothing writes a
`__pycache__` into `references/`). Every FIRES case has a SILENT twin, because a branch
check that fires on intentional designs is worse than none.
"""
import copy, glob, json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v13 import catalogued, values_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, 'plugin', 'skills', 'flow-audit', 'references', 'audit-flow.py')
VERIFY = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'verify-config.py')
QUIZ = os.path.join(ROOT, 'tests', 'fixtures', 'onboarding-quiz-paywall.json')
fails = []


def check(name, ok, detail=''):
    print(('  ok    ' if ok else '  FAIL  ') + name)
    if not ok:
        fails.append(f'{name}: {str(detail)[:600]}')


def audit(doc, *extra):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json'); json.dump(catalogued(doc), open(p, 'w'))
        args = []
        for i, x in enumerate(extra):
            if isinstance(x, (dict, list)):
                q = os.path.join(tmp, f'x{i}.json'); json.dump(catalogued(x), open(q, 'w')); args.append(q)
            else:
                args.append(x)
        r = subprocess.run([sys.executable, AUDIT, p, '--json', *args], capture_output=True, text=True)
        rep = subprocess.run([sys.executable, AUDIT, p, '--report', *args], capture_output=True, text=True)
    assert 'Traceback' not in r.stderr, r.stderr
    return json.loads(r.stdout)['findings'], rep.stdout


def nav(findings):
    return [f for f in findings if f['family'] == 'navigation']


def quiz():
    return json.load(open(QUIZ))


def quiz_screen(d):
    return next(s for s in d['screens'] if s.get('caption') == 'Quiz')


def two_screens(action):
    return {'screens': [
        {'id': 'scr_a', 'caption': 'A', 'props': {}, 'elements': {'map': {'el_n': {
            'id': 'el_n', 'type': 'text', 'props': {'content': {'values': {'en': 'Next'}}},
            'interactions': [{'id': 'i', 'trigger': 'tap', 'actions': [action]}]}},
            'hierarchy': {'id': 'el_n', 'children': []}}},
        {'id': 'scr_b', 'caption': 'B', 'props': {}, 'elements': {'map': {'el_c': {
            'id': 'el_c', 'type': 'text', 'props': {'content': {'values': {'en': 'Done'}}},
            'interactions': [{'id': 'i2', 'trigger': 'tap', 'actions': [
                {'id': 'a2', 'type': 'closeFlow', 'payload': {}}]}]}},
            'hierarchy': {'id': 'el_c', 'children': []}}}],
        'locales': [{'id': 'l', 'code': 'en', 'name': 'English'}], 'defaultLocale': 'en',
        'theme': {'colors': [], 'typography': []}, '_meta': {'screens': {}, 'icons': [], 'fonts': []}}



print('quiz branching')
f, _ = audit(quiz())
check('SILENT on the real quiz: Rock -> Rock, Rap -> Hip hop, and the Next button is '
      'not counted as an answer', not nav(f), nav(f))

d = quiz(); quiz_screen(d)['elements']['map']['el_7xR3X1HUGD']['props']['customId'] = 'rock_music'
f, rep = audit(d)
dead = [x for x in nav(f) if x['check'] == 'dead-branch']
check('FIRES dead-branch when an answer is renamed and the branch still names the old ID',
      len(dead) == 1 and dead[0]['severity'] == 'blocker' and '"rock"' in dead[0]['message'], nav(f))
check('...and names the IDs the question does have, so the fix is concrete',
      bool(dead) and 'rock_music' in dead[0]['fix'] and 'hiphop' in dead[0]['fix'], dead)
check('...without also reporting the same problem as a fall-through',
      not [x for x in nav(f) if x['check'] == 'fallthrough-to-answer-screen'], nav(f))

s = json.dumps(quiz())
swapped = json.loads(s.replace('"screen": "scr_03lOfpai"', '"screen": "TMP"')
                      .replace('"screen": "scr_Lpfvqycr"', '"screen": "scr_03lOfpai"')
                      .replace('"screen": "TMP"', '"screen": "scr_Lpfvqycr"'))
f, _ = audit(swapped)
mm = [x for x in nav(f) if x['check'] == 'branch-mismatch']
check('FIRES branch-mismatch when "Rock" leads to the screen named after the other answer',
      len(mm) == 1 and '"Rock"' in mm[0]['message'] and '"Hip hop"' in mm[0]['message'], nav(f))


def add_answer(d, cid, text, default_caption=None):
    q = quiz_screen(d); m = q['elements']['map']
    new = copy.deepcopy(m['el_MNAYinLoBf']); new['id'] = 'el_jazz'
    new['props']['customId'] = cid
    m['el_jazz'] = new
    q['elements']['hierarchy']['children'].insert(1, {'id': 'el_jazz', 'children': []})
    if default_caption:
        next(s for s in d['screens'] if s['id'] == 'scr_Lpfvqycr')['caption'] = default_caption
    return d


f, _ = audit(add_answer(quiz(), 'jazz', 'Jazz'))
ft = [x for x in nav(f) if x['check'] == 'fallthrough-to-answer-screen']
check('FIRES fall-through when a third answer has no branch and "otherwise" goes to the '
      'screen named after "Rap"', len(ft) == 1 and ft[0]['severity'] == 'risk'
      and '"Hip hop"' in ft[0]['message'], nav(f))
f, _ = audit(add_answer(quiz(), 'jazz', 'Jazz', default_caption='More genres'))
check('SILENT when "otherwise" goes to a screen that fits every remaining answer (a design, '
      'like "Accelerated path" for everyone past beginner)', not nav(f), nav(f))

print('\nbranches count as a way off a screen')
# A paywall whose only way out is a close button on the NEXT screen, reached through a
# conditional branch: before branches were followed, the audit could not see that path
# and called the paywall a trap.
def branch_exit():
    d = two_screens({'id': 'a', 'type': 'conditional', 'payload': {'type': 'switch', 'cases': [],
                     'default': {'type': 'const', 'value': [
                         {'id': 'n', 'type': 'navigate', 'payload': {'type': 'screen', 'screen': 'scr_b'}}]}}})
    m = d['screens'][0]['elements']['map']
    m['el_buy'] = {'id': 'el_buy', 'type': 'text', 'props': {'content': {'values': {'en': 'Buy'}}},
                   'interactions': [{'id': 'ib', 'trigger': 'tap', 'actions': [
                       {'id': 'ab', 'type': 'purchase', 'payload': {}}]}]}
    d['screens'][0]['elements']['hierarchy'] = {'id': 'root', 'children': [
        {'id': 'el_n', 'children': []}, {'id': 'el_buy', 'children': []}]}
    return d
f, _ = audit(branch_exit())
check('a way out reached through a conditional branch counts as a way out',
      not [x for x in f if x['check'] == 'no-escape-from-paywall'], f)

print('\nsibling-flow languages')
d = quiz()
f, rep = audit(d, '--sibling-locales', {'Main paywall': ['en', 'ru'], 'Onboarding': ['en']})
ms = [x for x in f if x['check'] == 'missing-sibling-locale']
check('FIRES when another published flow also offers a language this one lacks',
      len(ms) == 1 and 'ru' in ms[0]['message'] and '"Main paywall"' in ms[0]['message']
      and ms[0]['severity'] == 'risk', f)
f, _ = audit(d, '--sibling-locales', {'Onboarding': ['en']})
check('SILENT when every sibling language is already here',
      not [x for x in f if x['check'] == 'missing-sibling-locale'], f)
f, _ = audit(d)
check('SILENT when siblings were not fetched', not [x for x in f if x['check'] == 'missing-sibling-locale'])

print('\npartly translated languages')
MULTI = os.path.join(ROOT, 'tests', 'fixtures', 'onboarding-multilocale.json')
d = json.load(open(MULTI))
_dropped = [0]
def _drop_sr(o):
    if isinstance(o, dict):
        vals = o.get('values')
        if o.get('kind') and isinstance(vals, dict) and 'sr' in vals and _dropped[0] < 10:
            del vals['sr']; _dropped[0] += 1
        for v in o.values(): _drop_sr(v)
    elif isinstance(o, list):
        for v in o: _drop_sr(v)
_drop_sr(d['localization']['content'])
f, rep = audit(d)
mt = [x for x in f if x['check'] == 'missing-translation']
check('fixture setup: ten Serbian values removed', _dropped[0] == 10, _dropped)
check('FIRES missing-translation, a blocker naming the language and the count',
      len(mt) == 1 and mt[0]['severity'] == 'blocker' and 'Serbian' in mt[0]['message']
      and '10 of' in mt[0]['message'], f)
f, _ = audit(json.load(open(MULTI)))
check('SILENT on the fully translated fixture',
      not [x for x in f if x['check'] == 'missing-translation'], f)


def _with_links(d):
    """Add a Terms openUrl whose url has only the default locale's value (verify-config
    forbids copying it into the others), and a text field holding only a bare URL."""
    el = d['screens'][0]['elements']['map']['el_003T']
    el['interactions'] = [{'id': 'i_terms', 'trigger': 'tap', 'actions': [
        {'id': 'a_terms', 'type': 'openUrl', 'payload': {'url': {'_lid': 'lc_9001'}}}]}]
    content = d['localization']['content']
    content['lc_9001'] = {'kind': 'rich-string', 'values': {'en': 'terms.example.com/en'}}
    content['lc_9002'] = {'kind': 'rich-text', 'values': {'en': [{'type': 'paragraph', 'content': [
        {'type': 'text', 'text': 'https://example.com/privacy'}]}]}}
    m = d['screens'][0]['elements']['map']
    m['el_url'] = {'id': 'el_url', 'type': 'text', 'props': {'content': {'_lid': 'lc_9002'}}}
    d['screens'][0]['elements']['hierarchy']['children'].append({'id': 'el_url', 'children': []})
    return d


f, _ = audit(_with_links(json.load(open(MULTI))))
check('SILENT on link addresses kept in the default locale only (openUrl url, bare URL)',
      not [x for x in f if x['check'] in ('missing-translation', 'untranslated')
           and ('example.com' in x['message'] or x['check'] == 'missing-translation')], f)


def _missing_message(d):
    _dropped[0] = 0
    _drop_sr(d['localization']['content'])
    return [x['message'] for x in audit(d)[0] if x['check'] == 'missing-translation']


_plain, _linked = _missing_message(json.load(open(MULTI))), _missing_message(
    _with_links(json.load(open(MULTI))))
check('...and the links count in neither the missing count nor the total',
      len(_linked) == 1 and '10 of' in _linked[0] and _linked == _plain, (_plain, _linked))

print('\nsibling-flow languages, spelled another way')
d = _with_links(json.load(open(MULTI)))
f, _ = audit(d, '--sibling-locales', {'Paywall': ['EN', 'SR-latn', 'sr_Latn']})
check('SILENT when a sibling spells a language with other casing or an underscore',
      not [x for x in f if x['check'] == 'missing-sibling-locale'], f)
f, _ = audit(d, '--sibling-locales', {'Paywall': ['EN', 'pt-br'], 'Onboarding': ['pt-BR']})
ms = [x for x in f if x['check'] == 'missing-sibling-locale']
check('...and still FIRES, once per language, on a language this flow lacks',
      len(ms) == 1 and ms[0]['message'].count('pt-') == 1, f)

print('\nnavigateNext counts for reachability (verify-config)')


def unreachable(doc):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json'); json.dump(catalogued(doc), open(p, 'w'))
        out = subprocess.run([sys.executable, VERIFY, p], capture_output=True, text=True).stdout
    assert 'CHECKER ERROR' not in out, out
    return 'unreachable' in out, out


u, out = unreachable(two_screens({'id': 'a', 'type': 'navigateNext', 'payload': {}}))
check('a screen reached by "Navigate Next" is not reported unreachable', not u, out)
u, out = unreachable(two_screens({'id': 'a', 'type': 'nothing', 'payload': {}}))
check('...while a screen nothing leads to still is', u, out)

print('\nnavigate transitions (verify-config)')


def verify_out(doc):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json'); json.dump(catalogued(doc), open(p, 'w'))
        out = subprocess.run([sys.executable, VERIFY, p], capture_output=True, text=True).stdout
    assert 'CHECKER ERROR' not in out, out
    return out


def go(transition, kind='navigate'):
    payload = {'type': 'screen', 'screen': 's2', 'transition': transition}
    return {'id': 'a', 'type': kind, 'payload': payload}


PUSH = {'type': 'push', 'direction': 'left', 'easing': 'ease-out', 'duration': 350, 'delay': 0}
FADE = {'type': 'fadeThrough', 'easing': 'linear', 'duration': 300, 'delay': 0}
for t in ({'type': 'none'}, PUSH, {**PUSH, 'type': 'slideIn', 'direction': 'up'},
          {**PUSH, 'type': 'slideOut', 'easing': 'ease-out-bounce', 'duration': 0, 'delay': 5000},
          FADE):
    out = verify_out(two_screens(go(t)))
    check(f'{t["type"]} passes', 'transition' not in out, out)
for why, t in (('no delay', {k: v for k, v in PUSH.items() if k != 'delay'}),
               ('direction on fadeThrough', {**FADE, 'direction': 'up'}),
               ('over 5000 ms', {**PUSH, 'duration': 5001}),
               ('fractional ms', {**PUSH, 'duration': 12.5}),
               ('true for a number', {**PUSH, 'delay': True}),
               ('unknown easing', {**PUSH, 'easing': 'spring'}),
               ('unknown direction', {**PUSH, 'direction': 'bottom'}),
               ('unknown type', {'type': 'slide', 'speed': 'fast'}),
               ('not an object', 'push')):
    out = verify_out(two_screens(go(t)))
    check(f'refused: {why}', 'bad transition' in out, out)
nested = {'id': 'c', 'type': 'conditional', 'payload': {
    'type': 'switch', 'cases': [],
    'default': {'type': 'const', 'value': [go({'type': 'slide'})]}}}
check('refused inside a conditional branch', 'bad transition' in verify_out(two_screens(nested)))
for kind in ('navigateBack', 'navigateNext'):
    out = verify_out(two_screens({'id': 'a', 'type': kind, 'payload': {'transition': PUSH}}))
    check(f'{kind} with a transition is refused', 'only `navigate` reads' in out, out)
print('\nShow / Hide animations (verify-config)')


def shown(animation, target='el_n', kind='showElement'):
    return {'id': 'a', 'type': kind, 'payload': {'elements': [target], 'animation': animation}}


FADE_IN = {'type': 'fade', 'duration': 300, 'delay': 3000, 'easing': 'ease-out'}
for t in (FADE_IN, {**FADE_IN, 'type': 'rise', 'distance': 48}, {**FADE_IN, 'type': 'pop'},
          {'type': 'none', 'delay': 5000}, {**FADE_IN, 'delay': 60000}):
    out = verify_out(two_screens(shown(t)))
    check(f'{t["type"]} animation passes', 'animation' not in out, out)
check('a hide takes one too', 'animation' not in verify_out(two_screens(shown(FADE_IN, kind='hideElement'))))
for why, t in (('unknown type', {**FADE_IN, 'type': 'slide'}),
               ('over 60000 ms', {**FADE_IN, 'delay': 60001}),
               ('no duration', {k: v for k, v in FADE_IN.items() if k != 'duration'}),
               ('a bounce easing', {**FADE_IN, 'easing': 'ease-out-bounce'}),
               ('a pop scale of 1', {**FADE_IN, 'type': 'pop', 'scale': 1}),
               ('not an object', 'fade')):
    out = verify_out(two_screens(shown(t)))
    check(f'refused animation: {why}', 'bad animation' in out, out)
out = verify_out(two_screens(shown(FADE_IN, target='el_c')))
check('an animated Show of an element on another screen warns it plays at once',
      'not on this screen' in out, out)
cond = two_screens(shown(FADE_IN))
cond['screens'][0]['elements']['map']['el_n']['props']['visibility'] = {
    'type': 'conditional', 'condition': {}}
check('an animated Show of a conditional element warns it plays at once',
      'conditional visibility' in verify_out(cond))
check('an instant Show of another screen\'s element is not warned about',
      'not on this screen' not in verify_out(two_screens(
          {'id': 'a', 'type': 'showElement', 'payload': {'elements': ['el_c']}})))
for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    out = subprocess.run([sys.executable, VERIFY, f], capture_output=True, text=True).stdout
    if 'animation' in out and ('Show / Hide' in out or 'bad animation' in out):
        check(f'animation checks silent on {os.path.basename(f)}', False, out)
check('animation checks silent on every real export', True)

for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    out = subprocess.run([sys.executable, VERIFY, f], capture_output=True, text=True).stdout
    if 'bad transition' in out or 'only `navigate` reads' in out:
        check(f'silent on {os.path.basename(f)}', False, out)
check('silent on every real export', True)

print()
if fails:
    print(f'{len(fails)} FAILED')
    for x in fails:
        print('  -', x)
    sys.exit(1)
print('all checks passed')
