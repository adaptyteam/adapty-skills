"""verify-config.py's tall-phone checks: where a tall phone's extra height goes, and a spread list.

Repo-only. Runs the shipped script as a subprocess on screens built with flowkit: a hero block,
a content stack and a bar holding a tappable CTA, the shape users report as a dead band under the
bar on a tall phone. Each way of giving the extra height a place must silence the first check;
every real export in tests/fixtures* must stay silent on both.
"""
import glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
sys.path.insert(0, REFS)
import flowkit as fk
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

BAND = "nothing takes a tall phone's extra height"
SPREAD = 'so on a tall phone the gaps between them grow'

def t(s):
    return fk.text(s, preset='body', color_id='ink')

def hero(fill=False):
    if fill:
        return fk.stack([], height='fill', fill_=fk.fill(hexval='#6A3FA0'))
    return fk.stack([], fixed_h=300, fill_=fk.fill(hexval='#6A3FA0'))

def content(rows=None):
    return rows or fk.stack([t('Title'), t('One'), t('Two'), t('Three')], gap=8)

def cta():
    return fk.stack([t('Continue')], fixed_h=56, actions=[fk.close()])

def bar():
    return fk.stack([cta(), t('Terms')], gap=12)

def doc(nodes, **kw):
    kw.setdefault('scrollable', True)
    kw.setdefault('fill_', fk.fill(hexval='#FFFFFF'))
    return fk.config(screens=[fk.screen('s', nodes, **kw)],
                     colors=[('ink', 'Ink', '#1A1A1A', '#1A1A1A')],
                     typography=[('body', 'Body', 16, 'regular')])

out = run(doc([hero(), content(), bar()]))
check('FIRES: top-aligned gap root, bar in flow', out.count(BAND) == 1, out[:400])

for name, d in [
    ('a footer', doc([hero(), content(), fk.footer([cta()], fill_=fk.fill(hexval='#FFFFFF'))])),
    ('a root spread', doc([fk.stack([hero(), content()]), bar()], distribution='space-between')),
    ('a fill-height hero', doc([hero(fill=True), content(), bar()])),
    ('root alignV end', doc([hero(), content(), bar()], align_v='end')),
    ('a docked bar', doc([hero(), content(), fk.stack([t('Continue')], fixed_h=56, actions=[fk.close()],
                                                       position=fk.docked(bottom=24, left=16, right=16))])),
    ('one root child holding everything', doc([fk.stack([hero(), content(), bar()])])),
    ('a non-scrollable screen', doc([hero(), content(), bar()], scrollable=False)),
    ('no tappable bar at the end', doc([hero(), bar(), content()])),
]:
    out = run(d)
    check(f'SILENT: {name}', BAND not in out, out[:400])

rows = fk.stack([t('One'), t('Two'), t('Three')], height='fill', distribution='space-between')
out = run(doc([hero(), fk.stack([t('Title'), rows]), bar()], distribution='space-between'))
check('FIRES: space-between on a fill-height list', out.count(SPREAD) == 1, out[:400])

card = fk.stack([t('1 week'), t('$4.99'), t('per week')], fixed_h=110, distribution='space-between')
out = run(doc([hero(), fk.stack([t('Title'), card]), bar()], distribution='space-between'))
check('SILENT: a fixed-height card spreading its own lines', SPREAD not in out, out[:400])

two = fk.stack([t('One'), t('Two')], height='fill', distribution='space-between')
out = run(doc([hero(), fk.stack([t('Title'), two]), bar()], distribution='space-between'))
check('SILENT: a two-child spread (one seam, not a list)', SPREAD not in out, out[:400])

COVER = 'fill child ignores the footer'
try:
    doc([hero(fill=True), content(), fk.footer([cta()], fill_=fk.fill(hexval='#FFFFFF'))])
    check('flowkit.screen refuses a footer beside a fill-height root child', False, 'no raise')
except ValueError as e:
    check('flowkit.screen refuses a footer beside a fill-height root child', 'DEVICE-CONFIRMED' in str(e))

d = doc([hero(fill=True), content(), bar()])
s = d['screens'][0]['elements']
s['map'][s['hierarchy']['children'][-1]['id']]['type'] = 'footer'
s['map'][s['hierarchy']['children'][-1]['id']]['props']['fill'] = fk.fill(hexval='#FFFFFF')
out = run(d)
check('FIRES: footer beside a fill-height hero', out.count(COVER) == 1, out[:400])
out = run(doc([hero(), content(), fk.footer([cta()], fill_=fk.fill(hexval='#FFFFFF'))]))
check('SILENT: footer beside a fixed-height hero', COVER not in out, out[:400])

for path in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '**', '*.json'), recursive=True)):
    raw = json.load(open(path))
    if not isinstance(raw, dict) or 'screens' not in raw.get('config', raw):
        continue
    out = run(raw)
    check(f'SILENT on real export {os.path.relpath(path, ROOT)}',
          BAND not in out and SPREAD not in out and COVER not in out, out[:400])

print(f'\n{len(fails)} failure(s)')
sys.exit(1 if fails else 0)
