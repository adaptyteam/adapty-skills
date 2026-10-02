#!/usr/bin/env python3
"""Calibration for layered theme styles: `verify-config.py` and `flowkit.config()`.

Repo-only. The checker runs as a subprocess; flowkit is imported with bytecode writing off, so
nothing lands in `references/__pycache__`.

A theme colour's `light`/`dark` is either `{hex, opacity}` or an ARRAY of fill layers (solid,
gradient, image, video), and every fill that references the style follows the appearance. Each
FIRES case below is a document the transform service refuses with a 422, or one it accepts and
renders wrong; each was run through the transformer and its output-schema gate first, so the
case records the service's verdict rather than a guess.

    FIRES   -- empty stack; neither side; nested color-style in a solid or a gradient stop;
               image with no url; 8-digit / empty solid hex; #RGB / unprefixed / 8-digit stop
               hex; a theme id colliding with a derived asset id; text bound to a style with
               no solid layer (accepted, draws transparent); input border bound to a style
               with two paint layers
    WARNS   -- #RGB solid hex (accepted, but the same value is refused in a stop); a carousel
               dot colour bound to a layered style; a border bound to an image-only style
    SILENT  -- every tracked and raw export; a gradient/image/scrim stack on a screen fill; a
               one-gradient input border (accepted); a
               dark-only stack; a stack used next to an image layer in an element fill; text
               bound to [image, solid] (the solid is what text draws)
    FLOWKIT -- builds a stack from gradient()/image_fill()/fill(hexval=, opacity=); raises on a
               nested reference, a bad stop hex, a video layer, a derived-id collision and text
               bound to a no-solid style

Usage: python3 tests/test-theme-styles.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'skills', 'flow-generator', 'references')
VERIFY = os.environ.get('VERIFY_CONFIG') or os.path.join(REFS, 'verify-config.py')  # mutation runs
CORPUS = os.path.join(ROOT, 'tests', 'fixtures')
RAW = os.path.join(ROOT, 'tests', 'fixtures-raw')
REVIEWS = os.path.join(CORPUS, 'reviews-carousel.json')
QUIZ = os.path.join(CORPUS, 'onboarding-quiz-paywall.json')

sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk  # noqa: E402

fails = []
URL = 'https://public-media.adapty.io/x.png'


def load(path):
    d = json.load(open(path))
    return d.get('config', d) if 'screens' not in d else d


def hx(h, o=None):
    d = {'type': 'hex', 'hex': h}
    if o is not None:
        d['opacity'] = o
    return d


def solid(h, o=None):
    return {'type': 'color', 'color': hx(h, o)}


def grad(a, b):
    return {'type': 'gradient', 'angle': 180,
            'stops': [{'color': hx(a), 'position': 0}, {'color': hx(b), 'position': 1}]}


IMG = {'type': 'image', 'image': {'id': '1', 'url': URL, 'previewValue': 'UklGRg=='}}


def style(d, cid):
    return next(c for c in d['theme']['colors'] if c['id'] == cid)


def run(doc):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        r = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if 'Traceback' in r.stderr or 'CHECKER ERROR' in r.stdout:
        raise AssertionError(f'verify-config.py crashed:\n{r.stdout}\n{r.stderr}')
    errs = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith('ERROR')]
    warns = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith('warning')]
    return errs, warns, r.returncode


def variant(base, fn):
    d = copy.deepcopy(load(base))
    fn(d)
    return d


def fires(name, doc, fragment):
    errs, _, code = run(doc)
    if code != 1 or not any(fragment in e for e in errs):
        fails.append(f'{name}: expected an ERROR containing {fragment!r}, got exit {code}: {errs!r}')
    else:
        print(f'  FIRES  {name}')


def warns(name, doc, fragment):
    errs, ws, _ = run(doc)
    mine = [e for e in errs if 'theme colour' in e or 'layered style' in e or 'bound to' in e]
    if mine or not any(fragment in w for w in ws):
        fails.append(f'{name}: expected only a warning containing {fragment!r}; '
                     f'errors {mine!r}, warnings {ws!r}')
    else:
        print(f'  WARNS  {name}')


def silent(name, doc):
    errs, ws, _ = run(doc)
    mine = [x for x in errs + ws if 'theme colour' in x or 'layered style' in x
            or 'no solid layer' in x or 'derives from' in x]
    if mine:
        fails.append(f'{name}: expected no theme-style finding, got {mine!r}')
    else:
        print(f'  SILENT {name}')


def raises(name, fn, fragment):
    try:
        fn()
    except (ValueError, TypeError) as e:
        if fragment in str(e):
            print(f'  RAISES {name}')
            return
        fails.append(f'{name}: raised, but the message lacks {fragment!r}: {e}')
        return
    fails.append(f'{name}: expected flowkit to raise')


print('verify-config.py — FIRES')
fires('empty stack', variant(REVIEWS, lambda d: style(d, 'bg').update(light=[])), 'empty layer stack')
fires('neither side', variant(REVIEWS, lambda d: (style(d, 'bg').pop('light'), style(d, 'bg').pop('dark'))),
      'neither `light` nor `dark`')
fires('nested reference in a solid', variant(REVIEWS, lambda d: style(d, 'bg').update(
    light=[{'type': 'color', 'color': {'type': 'color-style', 'colorId': 'card'}}])),
    'cannot reference another style')
fires('nested reference in a stop', variant(REVIEWS, lambda d: style(d, 'bg').update(
    light=[{'type': 'gradient', 'angle': 0, 'stops': [
        {'color': {'type': 'color-style', 'colorId': 'card'}, 'position': 0},
        {'color': hx('#FFFFFF'), 'position': 1}]}])), 'must be a literal')
fires('image with no url', variant(REVIEWS, lambda d: style(d, 'bg').update(
    light=[{'type': 'image', 'image': {'id': '1'}}])), 'needs `image.url`')
for tag, h in (('8-digit', '#FFFFFFD9'), ('empty', '')):
    fires(f'{tag} solid hex', variant(REVIEWS, lambda d, h=h: style(d, 'bg').update(light=[solid(h)])),
          'is refused')
for tag, h in (('#RGB', '#fff'), ('unprefixed', 'FFFFFF'), ('8-digit', '#FFFFFFD9')):
    fires(f'{tag} stop hex', variant(REVIEWS, lambda d, h=h: style(d, 'bg').update(light=[grad(h, '#EEEEEE')])),
          'gradient stop hex')


def collide(d):
    style(d, 'bg').update(light=[solid('#FFFFFF'), grad('#FFFFFF', '#EEEEEE')])
    d['theme']['colors'].append({'id': 'bg_fill_1', 'name': 'x', 'light': {'hex': '#123456'}})


fires('derived-id collision', variant(REVIEWS, collide), "['bg_fill_1']")
fires('text on a gradient-only style', variant(REVIEWS, lambda d: style(d, 'ink').update(
    light=[grad('#111114', '#333344')])), 'draws fully TRANSPARENT')
fires('text on a dark image-only style', variant(REVIEWS, lambda d: style(d, 'ink').update(
    dark=[IMG])), 'no solid layer in dark')


def input_border(d, layers=None):
    style(d, 'card').update(light=layers or [solid('#F4F6FA'), grad('#FFFFFF', '#E0E0FF')])
    m = d['screens'][0]['elements']['map']
    m['el_probe_input'] = {'id': 'el_probe_input', 'type': 'email-input', 'states': [],
                           'props': {'customId': 'email', 'border': {
                               'style': 'solid', 'width': 1,
                               'color': {'type': 'color-style', 'colorId': 'card'}}}}
    d['screens'][0]['elements']['hierarchy']['children'].append({'id': 'el_probe_input', 'children': []})


fires('input border on two paint layers', variant(REVIEWS, input_border), 'unsupported_input_border_layers')

print('verify-config.py — WARNS')
warns('#RGB solid hex', variant(REVIEWS, lambda d: style(d, 'bg').update(light=[solid('#fff')])),
      'write #RRGGBB')
warns('dots bound to a layered style', variant(REVIEWS, lambda d: style(d, 'ink').update(
    light=[IMG, solid('#111114')])), 'carousel colour bound to the layered style')


def image_border(d):
    style(d, 'muted').update(light=[IMG])
    m = d['screens'][0]['elements']['map']
    m['el_C_004S']['props']['border'] = {'style': 'solid', 'width': 1,
                                         'color': {'type': 'color-style', 'colorId': 'muted'}}
    for e in m.values():                      # keep this case about the border alone
        if e['type'] in ('text', 'carousel'):
            e['props'].pop('dots', None)
            if (e['props'].get('color') or {}).get('colorId') == 'muted':
                e['props']['color'] = {'type': 'color-style', 'colorId': 'ink'}


warns('border on an image-only style', variant(REVIEWS, image_border), 'border draws only')

print('verify-config.py — SILENT')
for path in sorted(glob.glob(os.path.join(CORPUS, '*.json')) + glob.glob(os.path.join(RAW, '*.json'))):
    silent(os.path.relpath(path, ROOT), load(path))
silent('gradient light, image + scrim dark on the screen fill', variant(REVIEWS, lambda d: style(d, 'bg').update(
    light=[grad('#FFFFFF', '#EEF0FF')], dark=[IMG, solid('#000000', 40)])))
silent('dark-only stack', variant(REVIEWS, lambda d: (style(d, 'bg').pop('light'),
                                                      style(d, 'bg').update(dark=[grad('#000000', '#222222')]))))


def mixed(d):
    style(d, 'card').update(light=[grad('#FFFFFF', '#E0E0FF')])
    d['screens'][0]['elements']['map']['el_C_004S']['props']['fill'] = [
        IMG, {'type': 'color', 'color': {'type': 'color-style', 'colorId': 'card'}}]


silent('stack next to an image layer in an element fill', variant(REVIEWS, mixed))


def text_on_image_solid(d):
    style(d, 'ink').update(light=[IMG, solid('#111114')])
    d['screens'][0]['elements']['map']['el_C_013C']['props'].pop('dots', None)


silent('text on [image, solid]', variant(REVIEWS, text_on_image_solid))
def heading_on_bg(bg_layers):
    """The heading sits straight on the screen fill; make its ink near-white in light mode."""
    def fn(d):
        style(d, 'bg').update(light=bg_layers)
        style(d, 'ink').update(light={'hex': '#F5F5F7'})
    return fn


# A background stack resolves only when every layer is a solid. A solids-only stack is read
# (the legibility check still sees near-white on white); one with an image is skipped, never
# read as its solid layer, which would report contrast against a colour the image covers.
errs, ws, _ = run(variant(REVIEWS, heading_on_bg([solid('#FFFFFF')])))
if not any('text is 1.0' in w and 'light mode' in w for w in ws):
    fails.append(f'solids-only bg stack: expected the legibility warning, got {ws!r}')
else:
    print('  WARNS  near-white text on a solids-only bg stack (legibility)')
errs, ws, _ = run(variant(REVIEWS, heading_on_bg([solid('#FFFFFF'), IMG])))
if any('against its background in light mode' in w and 'el_C_014T' in w for w in ws):
    fails.append(f'bg stack with an image: must be unresolvable, got {ws!r}')
else:
    print('  SILENT near-white text on a bg stack with an image (unresolvable)')
silent('input border on one gradient layer (the service accepts one)',
       variant(REVIEWS, lambda d: input_border(d, [grad('#FFFFFF', '#E0E0FF')])))

print('flowkit.config()')
card = fk.stack([fk.text(fk.rich('Hi'), preset='h1', color_id='ink')], fill_=fk.fill('card'))
scr = [fk.screen('scr_main', [card], fill_=fk.fill('bg'))]
TYPO = [('h1', 'H1', 28, 'bold')]
INK = ('ink', 'Ink', '#111114', '#F5F5F7')

built = fk.config(screens=scr, typography=TYPO, colors=[
    ('bg', 'Bg', fk.gradient(180, ('#FFFFFF', 0), ('#EEF0FF', 1)),
     fk.image_fill(URL, preview='UklGRg==') + fk.fill(hexval='#000000', opacity=40)),
    ('card', 'Card', '#F4F6FA', None), INK])
bg = style(built, 'bg')
if not (isinstance(bg['light'], list) and bg['dark'][1]['color'] == {'type': 'hex', 'hex': '#000000', 'opacity': 40}
        and 'dark' not in style(built, 'card')):
    fails.append(f'flowkit stack shape: {json.dumps(built["theme"]["colors"])}')
else:
    print('  BUILDS stack from gradient()/image_fill()/fill(hexval=, opacity=)')
silent('flowkit-built stack', built)

raises('nested reference', lambda: fk.config(screens=scr, typography=TYPO, colors=[
    ('bg', 'Bg', fk.fill('card'), None), ('card', 'Card', '#FFFFFF', None), INK]), 'another style')
raises('bad stop hex', lambda: fk.config(screens=scr, typography=TYPO, colors=[
    ('bg', 'Bg', fk.gradient(0, ('#fff', 0), ('#000000', 1)), None), ('card', 'C', '#FFFFFF', None), INK]),
    '#RRGGBB')
raises('video layer', lambda: fk.config(screens=scr, typography=TYPO, colors=[
    ('bg', 'Bg', [{'type': 'video', 'video': {'videoUrl': 'v', 'previewUrl': 'p'}}], None),
    ('card', 'C', '#FFFFFF', None), INK]), 'video')
raises('empty stack', lambda: fk.config(screens=scr, typography=TYPO, colors=[
    ('bg', 'Bg', [], None), ('card', 'C', '#FFFFFF', None), INK]), 'non-empty list')
raises('derived-id collision', lambda: fk.config(screens=scr, typography=TYPO, colors=[
    ('bg', 'Bg', fk.fill(hexval='#FFFFFF') + fk.gradient(0, ('#FFFFFF', 0), ('#000000', 1)), None),
    ('bg_fill_1', 'X', '#123456', None), ('card', 'C', '#FFFFFF', None), INK]), 'bg_fill_1')
raises('text on a no-solid style', lambda: fk.config(screens=scr, typography=TYPO, colors=[
    ('bg', 'Bg', '#FFFFFF', None), ('card', 'C', '#FFFFFF', None),
    ('ink', 'Ink', fk.gradient(0, ('#111114', 0), ('#333344', 1)), None)]), 'transparent')

if fails:
    print('\nFAIL')
    for f in fails:
        print(' -', f)
    sys.exit(1)
print('\nall pass')
