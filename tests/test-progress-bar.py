"""verify-config.py's progress-bar checks, both directions.

Repo-only. Runs the shipped script as a subprocess. The SILENT shape is the device-verified one: a
single-segment bar whose loader `fill` is the track and `color` is the progress, which advanced on
a real device across the screens that switch it on.
"""
import copy, glob, json, os, subprocess, sys, tempfile

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

col = lambda c: [{'type': 'color', 'color': {'type': 'color-style', 'colorId': c}}]
def bar(cid, track='gray-200', prog='accent'):
    b, s, l = f'el_{cid}B', f'el_{cid}S', f'el_{cid}L'
    size = {'width': {'type': 'fill'}, 'height': {'type': 'hug'}}
    return {'map': {
        b: {'id': b, 'type': 'progress-bar', 'props': {'type': 'single-segment', 'template': 'linear',
            'oneSegmentPerScreen': False, 'width': {'type': 'fill'}, 'height': {'type': 'fixed', 'value': 20}}},
        s: {'id': s, 'type': 'progress-bar-segment', 'props': dict(size, customId='progress'),
            'propsByState': {k: dict(size) for k in ('completed', 'current', 'upcoming')}},
        l: {'id': l, 'type': 'progress-bar-loader', 'props': {'fill': col(track),
            'color': {'type': 'color-style', 'colorId': prog}, 'width': {'type': 'fill'},
            'height': {'type': 'fixed', 'value': 8}, 'duration': 300, 'easing': 'ease-in-out',
            'position': {'type': 'relative'}}}},
        'hierarchy': {'id': 'root', 'children': [{'id': b, 'children': [{'id': s, 'children': [{'id': l}]}]}]}}

def doc(components):
    scr = {'id': 'scr_a', 'elements': {'map': {}, 'hierarchy': {'id': 'root', 'children':
           [{'id': k, 'type': 'global'} for k in components]}},
           'props': {'progressBar': {'enabled': True, 'segment': 'progress'}}}
    return {'schemaVersion': 13, 'screens': [scr], 'components': components, 'variables': [],
            'theme': {'colors': [{'id': c, 'name': c, 'light': {'hex': '#E0E0E0'}, 'dark': {'hex': '#E0E0E0'}}
                                 for c in ('gray-200', 'accent')], 'typography': []},
            'localization': {'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}],
                             'defaultLocale': 'en', 'content': {}},
            '_meta': {'icons': [], 'fonts': [], 'screens': {}}}

PB = 'progress bar'
check('SILENT: the device-verified shape', PB not in run(doc({'pb_a': bar('a')})))
check('FIRES: track and progress the same colour',
      'looks full on every screen' in run(doc({'pb_a': bar('a', track='accent')})))
check('FIRES: two bars in one flow', '2 progress bars' in run(doc({'pb_a': bar('a'), 'pb_b': bar('b')})))
for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    out = run(json.load(open(f)))
    check(f'SILENT on real export {os.path.relpath(f, ROOT)}', PB not in out, out[:200])

print()
if fails:
    print(f'{len(fails)} FAILED'); sys.exit(1)
print('all passed')
