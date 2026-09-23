#!/usr/bin/env python3
"""Calibration for how images and videos are treated across locales, in both checkers.

Repo-only. Runs `verify-config.py` as a subprocess and imports `audit-flow.py` in-process with
bytecode writing off, so nothing writes a `__pycache__` into a skill's `references/`.

Why this file exists. Text needs a value in every declared locale; media does not. The SDK
resolves a locale's assets on top of the default locale's (iOS merges the default's asset map
under the locale's own; Android loads the default's first and lets the locale override), and the
transformer drops empty media values for non-default locales for that reason. So a locale with no
image entry shows the default's file, and a copy of the default's `{id, url, previewValue}` in
another locale changes nothing on screen while repeating the base64 preview in the published
config once per locale. A flow with ~9 small previews copied into ~78 locales reached ~75 MB and
timed out at publish. The locale parity check used to ERROR on a missing image locale, which left
copying the image into every locale as the only way to clear it.

    verify-config.py
      FIRES   -- the default's image copied into every other locale
              -- a copy that differs only in its preview (same url, same asset)
              -- a video copied the same way
      SAYS    -- names the duplicated weight and the different-file exception
      SILENT  -- an image bound in the default locale only (no parity error, no copy warning)
              -- a locale that really does get a different file
              -- all real exports
      KEEPS   -- a TEXT field missing a locale still errors, so parity is not switched off
    audit-flow.py
      SILENT  -- a default-only image adds nothing to a locale's `missing` coverage count
      KEEPS   -- a text field missing a locale still counts as missing
      KEEPS   -- a locale with no text at all is still `locale-entirely-empty` when the flow
                 also carries a default-only image

Usage: python3 tests/test-image-locales.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, importlib.util, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'skills', 'flow-generator', 'references', 'verify-config.py')
AUDIT = os.path.join(ROOT, 'skills', 'flow-audit', 'references', 'audit-flow.py')
FLOW = os.path.join(ROOT, 'tests', 'fixtures', 'onboarding-multilocale.json')

URL = 'https://public-media.adapty.io/public/ef/9b/ef9b995d/hero.png'
OTHER_URL = 'https://public-media.adapty.io/public/ef/9b/ef9b995d/hero-sr.png'
PREVIEW = 'UklGRhQJAABXRUJQVlA4IAgJAAAwSQCdASos' * 60   # ~2 KB, so the KB figure is printed
COPY = 'repeat the en asset'

fails = []


def check(name, cond, detail=''):
    print(f'  {"ok   " if cond else "FAIL "} {name}')
    if not cond:
        fails.append(f'{name} {detail}'.strip())


def base_flow():
    d = json.load(open(FLOW))
    return d.get('config', d)


def with_media(values, kind='image'):
    """The multilocale fixture plus one media element whose `values` map is `values`."""
    d = base_flow()
    s = d['screens'][0]
    if kind == 'image':
        props = {'image': {'values': values, '_localizable': True},
                 'width': {'type': 'fill'}, 'height': {'type': 'fixed', 'value': 200},
                 'objectFit': 'cover', 'position': {'type': 'relative'}}
    else:
        props = {'video': {'values': values, '_localizable': True},
                 'width': {'type': 'fill'}, 'height': {'type': 'fixed', 'value': 200},
                 'objectFit': 'cover', 'position': {'type': 'relative'}}
    s['elements']['map']['el_900M'] = {'id': 'el_900M', 'type': kind, 'props': props,
                                       'states': []}
    s['elements']['hierarchy']['children'].append({'id': 'el_900M'})
    return d


def img(url=URL, preview=PREVIEW):
    return {'id': '516395', 'url': url, 'previewValue': preview}


def verify(doc):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'c.json')
        json.dump(doc, open(path, 'w'))
        r = subprocess.run([sys.executable, VERIFY, path], capture_output=True, text=True)
    if 'Traceback' in r.stderr or r.returncode == 2:
        raise AssertionError(f'verify-config.py failed to run:\n{r.stdout}\n{r.stderr}')
    return r.stdout.splitlines()


def copy_lines(lines):
    return [l for l in lines if COPY in l]


def parity_lines(lines, needle='no value for'):
    return [l for l in lines if needle in l]


print('verify-config.py')

every = {'en': img(), 'sr': img(), 'sr-Latn': img()}
out = verify(with_media(every))
check('FIRES on the default image copied into every other locale', copy_lines(out), out[-3:])
check('SAYS the duplicated weight in KB', any('KB of duplicated previewValue' in l
                                               for l in copy_lines(out)))
check('SAYS a per-locale value is for a DIFFERENT file',
      any('DIFFERENT file' in l for l in copy_lines(out)))
check('SAYS both locales, once, in one line',
      len(copy_lines(out)) == 1 and 'sr, sr-Latn' in copy_lines(out)[0], copy_lines(out))

reprev = {'en': img(), 'sr': img(preview='AAAA'), 'sr-Latn': img(preview='BBBB')}
check('FIRES on a copy that differs only in its preview (same url, same asset)',
      copy_lines(verify(with_media(reprev))))

video = {'en': {'videoUrl': 'https://x.test/a.mp4', 'previewUrl': 'https://x.test/a.png'}}
video['sr'] = dict(video['en'])
check('FIRES on a video copied the same way', copy_lines(verify(with_media(video, 'video'))))

only_default = verify(with_media({'en': img()}))
check('SILENT: an image bound in the default locale only raises no parity error',
      not parity_lines(only_default), parity_lines(only_default))
check('SILENT: an image bound in the default locale only raises no copy warning',
      not copy_lines(only_default))
check('SILENT: an image bound in the default locale only is an OK document',
      any(l.rstrip().endswith('OK') for l in only_default), only_default[-3:])

different = {'en': img(), 'sr': img(url=OTHER_URL)}
check('SILENT: a locale that really gets a different file', not copy_lines(verify(
    with_media(different))))

corpus = sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', '*.json')) +
                glob.glob(os.path.join(ROOT, 'tests', 'fixtures-raw', '*.json')))
noisy = [os.path.basename(p) for p in corpus if copy_lines(verify(json.load(open(p))))]
check(f'SILENT on all {len(corpus)} real exports', not noisy, noisy)

text_gap = base_flow()
for el in text_gap['screens'][0]['elements']['map'].values():
    vals = ((el.get('props') or {}).get('content') or {}).get('values')
    if isinstance(vals, dict) and 'sr' in vals:
        del vals['sr']
        break
check('KEEPS: a text field missing a locale still errors',
      any('locale sr: no value for' in l for l in verify(text_gap)))


print('audit-flow.py')

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('audit_flow', AUDIT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

plain_stat, _ = audit.locale_coverage(base_flow())
media_stat, _ = audit.locale_coverage(with_media({'en': img()}))
check('SILENT: a default-only image adds nothing to missing coverage',
      all(media_stat[c]['missing'] == plain_stat[c]['missing'] for c in plain_stat),
      f'{plain_stat} vs {media_stat}')

gap_stat, _ = audit.locale_coverage(text_gap)
check('KEEPS: a text field missing a locale still counts as missing',
      gap_stat['sr']['missing'] == plain_stat['sr']['missing'] + 1, gap_stat)

no_text = with_media({'en': img()})
for vals in audit._localizable_values(no_text, ['en', 'sr', 'sr-Latn']):
    vals.pop('sr', None)
entirely = [f for f in audit.check_localization(no_text)
            if f['check'] == 'locale-entirely-empty' and f['message'].startswith('sr ')]
check('KEEPS: a locale with no text is still locale-entirely-empty beside a default-only image',
      entirely, [f['check'] for f in audit.check_localization(no_text)])

print()
if fails:
    print(f'{len(fails)} FAILED:')
    for f in fails:
        print(f'  - {f}')
    sys.exit(1)
print('all passed')
