"""verify-config.py: a timer with a timer-end action must contain a text showing its digits.

Repo-only. Device-measured: timers whose child was a logo or plain text did not fire; the same
timers fired once a `timer_*` digits text was added, visible or coloured like the background.
"""
import glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'verify-config.py')
fails = []

def run(doc):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(doc, f)
    r = subprocess.run([sys.executable, VERIFY, f.name], capture_output=True, text=True)
    os.unlink(f.name)
    if r.returncode == 2:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout

def check(name, ok, detail=''):
    print(('  ok    ' if ok else '  FAIL  ') + name + ('' if ok else f'  {detail}'))
    if not ok:
        fails.append(name)

plain = {'bold': False, 'italic': False, 'underline': False, 'strikethrough': False}
def txt(eid, content):
    return {'id': eid, 'type': 'text', 'states': [], 'props': {'content': {'_localizable': True, 'values': {'en': [{'type': 'paragraph', 'content': content}]}}}}
def doc(child_els, nest=False):
    m = {'el_t': {'id': 'el_t', 'type': 'timer', 'states': [], 'props': {'customId': 'd', 'duration': {'days': 0, 'hours': 0, 'minutes': 0, 'seconds': 2}},
                  'interactions': [{'id': 'int_t', 'trigger': 'timer-end', 'actions': [{'id': 'a', 'type': 'navigate', 'payload': {'type': 'screen', 'screen': 'scr_b'}}]}]}}
    kids = []
    for e in child_els:
        m[e['id']] = e; kids.append({'id': e['id']})
    if nest:
        m['el_wrap'] = {'id': 'el_wrap', 'type': 'stack', 'states': [], 'props': {}}
        kids = [{'id': 'el_wrap', 'children': kids}]
    scr = lambda sid, mm, h: {'id': sid, 'elements': {'map': mm, 'hierarchy': h}, 'props': {}}
    return {'schemaVersion': 13, 'variables': [], 'components': {},
            'theme': {'colors': [], 'typography': []},
            'localization': {'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}], 'defaultLocale': 'en', 'content': {}},
            '_meta': {'icons': [], 'fonts': [], 'screens': {}},
            'screens': [scr('scr_a', m, {'id': 'root', 'children': [{'id': 'el_t', 'children': kids}]}),
                        scr('scr_b', {}, {'id': 'root', 'children': []})]}

MSG = 'no text inside it'
digits = txt('el_d', [{'type': 'token', 'attrs': {'token': 'timer_seconds'}}])
words = txt('el_w', [{'text': 'Loading', 'type': 'text', 'attrs': plain}])
image = {'id': 'el_i', 'type': 'image', 'states': [], 'props': {}}
check('FIRES: no children', MSG in run(doc([])))
check('FIRES: only plain text inside', MSG in run(doc([words])))
check('FIRES: only an image inside', MSG in run(doc([image])))
check('SILENT: digits inside', MSG not in run(doc([digits])))
check('SILENT: digits nested in a stack beside a logo', MSG not in run(doc([image, digits], nest=True)))
for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}', MSG not in run(json.load(open(f))))
print()
if fails:
    print(f'{len(fails)} FAILED'); sys.exit(1)
print('all passed')
