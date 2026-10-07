"""A loader is the `spinner` element, never a still `icon` of one.

Reported: asked for a loading screen, an agent placed a static icon that looks like a spinner
instead of the `spinner` element. `icons.py --search spinner` listed the static phosphor
`Spinner` first, above the rotating spinner glyphs, so the search pointed at the fake.

Rows, both directions:
- the search lists the rotating glyphs first and labels the static ones;
- `flowkit.icon()` refuses a static loader glyph unless told it is deliberate;
- `verify-config.py` warns on an `icon` element using one, and is silent on a real spinner and
  on the corpus;
- a timer that moves the flow on is captioned, so it does not read as an empty frame.
"""
import glob, json, os, subprocess, sys, tempfile

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
ICONS = os.path.join(REFS, 'icons.py')
sys.path.insert(0, REFS)
import flowkit as f  # noqa: E402

fails = []


def check(name, ok, detail=''):
    print(('ok    ' if ok else 'FAIL  ') + name)
    if not ok:
        fails.append(f'{name}: {detail}')


def findings(doc):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        r = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if 'Traceback' in r.stderr or r.returncode == 2:
        raise AssertionError(f'verify-config.py failed:\n{r.stdout}\n{r.stderr}')
    return [l for l in r.stdout.splitlines() if 'static picture of a loader' in l]


def build(nodes):
    return f.config(screens=[f.screen('scr_a', nodes)])


# --- the search an agent runs -----------------------------------------------------------------
out = subprocess.run([sys.executable, ICONS, '--search', 'spinner'],
                     capture_output=True, text=True).stdout.splitlines()
check('--search spinner lists a rotating glyph first', bool(out) and out[0].startswith('spinner1'),
      out[:2])
static = [l for l in out if l.split()[0] in ('Spinner', 'SpinnerGap', 'SpinnerBall')]
check('--search spinner labels every static loader glyph',
      len(static) == 3 and all('does not rotate' in l for l in static), static)
lock = subprocess.run([sys.executable, ICONS, '--search', 'Lock'],
                      capture_output=True, text=True).stdout.splitlines()
check('--search Lock still lists the exact icon first', bool(lock) and lock[0] == 'Lock', lock[:2])

# --- the helper ---------------------------------------------------------------------------------
try:
    f.icon('Spinner')
    check('icon("Spinner") is refused', False, 'no error')
except ValueError as e:
    check('icon("Spinner") is refused, pointing at spinner()', "spinner('spinner1')" in str(e), e)
try:
    f.icon('SpinnerGap', static_loader=True)
    check('icon("SpinnerGap", static_loader=True) is allowed', True)
except ValueError as e:
    check('icon("SpinnerGap", static_loader=True) is allowed', False, e)
try:
    f.icon('CircleNotch')
    check('icon("CircleNotch") is allowed: agents use it as a ring glyph', True)
except ValueError as e:
    check('icon("CircleNotch") is allowed: agents use it as a ring glyph', False, e)

# --- the checker --------------------------------------------------------------------------------
fake = build([f.icon('SpinnerGap', static_loader=True), f.text('Loading…')])
check('verify-config warns on an icon element using SpinnerGap', len(findings(fake)) == 1,
      findings(fake))
real = build([f.spinner('spinner1'), f.text('Loading…')])
check('verify-config is silent on a real spinner element', not findings(real), findings(real))
ring = build([f.icon('CircleNotch'), f.icon('CircleNotch'), f.text('Close your rings')])
check('verify-config is silent on CircleNotch used as decoration', not findings(ring), findings(ring))
plain = build([f.icon('Lock')])
check('verify-config is silent on an ordinary icon', not findings(plain), findings(plain))
corpus = sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', '*.json')) +
                glob.glob(os.path.join(ROOT, 'tests', 'fixtures-raw', '*.json')))
for path in corpus:
    hits = findings(json.load(open(path)))
    check(f'silent on {os.path.basename(path)}', not hits, hits)

# --- the auto-advance timer ---------------------------------------------------------------------
def timer(**kw):
    return f.timer([f.timer_digits(('seconds',))], seconds=2, **kw)


check('a timer that moves the flow on is captioned Auto-advance',
      timer(actions=[f.navigate('scr_b')]).get('caption') == 'Auto-advance')
check('an explicit caption wins',
      timer(actions=[f.navigate('scr_b')], caption='Wait').get('caption') == 'Wait')
check('a display-only timer gets no caption', 'caption' not in timer())

print()
if fails:
    print(f'{len(fails)} FAILED')
    for line in fails:
        print(f'  - {line}')
    sys.exit(1)
print('all passed')
