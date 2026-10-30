#!/usr/bin/env python3
"""Offline checks for the render scripts: `shoot.sh`, `preview-with-playwright.mjs`, `montage.py`.

Repo-only. Runs the shipped scripts as subprocesses and never touches the network: `shoot.sh` gets
a stand-in browser, a stand-in `adapty` and a local HTTP server for its host probe; the
Playwright helpers run on a page built with `setContent`, and only when Playwright and a
Chromium-based browser are installed (skipped otherwise).

    montage     -o/--out anywhere and --gutter=N work; a bad flag prints the argument order
    locale      --locale makes that language the default and only one; a value it lacks falls
                back to the old default's (the empty-image report); unknown code and a
                non-catalog config fail with exit 2 and say why; --no-previews strips them;
                --save-config keeps the input's shape (envelope or bare)
    shoot.sh    a browser that exits without a file is reported with what it said, at once and
                without the 60 s retry; every screen prints progress; TIME_LIMIT stops the run and
                names what was not rendered; a stopped run keeps and names what it finished
    in-page     overlays beside the screen are hidden and named, the screen's own docked layer is
                not; the scroller is found only when it is at least half the screen

Usage: python3 tests/test-render-scripts.py      # 0 all pass, 1 a case regressed
"""
import copy, http.server, json, os, shutil, signal, struct, subprocess, sys, tempfile, threading, time, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# RENDER_REF points the suite at a mutated copy of references/, to confirm each check can fail.
REF = os.environ.get('RENDER_REF') or os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
SHOOT = os.path.join(REF, 'shoot.sh')
PW = os.path.join(REF, 'preview-with-playwright.mjs')
MONTAGE = os.path.join(REF, 'montage.py')
FIX = os.path.join(ROOT, 'tests', 'fixtures')

fails = []


def check(name, ok, detail=''):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
    if not ok:
        fails.append(f'{name}: {detail}'.strip())


def png(path, w=120, h=200, ink=lambda x, y: 10 <= x < 110 and 20 <= y < 180):
    """A small RGB PNG; the default draws one large block, which passes `--sanity`."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw += bytes((20, 20, 20) if ink(x, y) else (250, 250, 250))

    def chunk(t, b):
        return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    with open(path, 'wb') as fh:
        fh.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                 + chunk(b'IDAT', zlib.compress(bytes(raw))) + chunk(b'IEND', b''))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def load(name):
    with open(os.path.join(FIX, name), encoding='utf-8') as fh:
        return json.load(fh)


def flow_of(doc):
    return doc['config'] if isinstance(doc.get('config'), dict) else doc.get('flow', doc)


tmp = tempfile.mkdtemp(prefix='render-scripts-')
try:
    # ---------------------------------------------------------------- montage
    print('montage.py')
    a, b = os.path.join(tmp, 'a.png'), os.path.join(tmp, 'b.png')
    png(a); png(b)
    m = lambda k: os.path.join(tmp, f'm{k}.png')
    for k, (label, argv) in enumerate([('-o first', ['-o', m(1), a, b]), ('--out last', [a, b, '--out', m(2)]),
                                       ('--out=', ['--out=' + m(3), a, b]),
                                       ('--gutter=0 positional', ['--gutter=0', m(4), a, b]),
                                       ('--gutter 0 after the inputs', [m(5), a, b, '--gutter', '0'])], 1):
        r = run([sys.executable, MONTAGE, *argv])
        check(f'montage accepts {label}', r.returncode == 0 and os.path.getsize(m(k)) > 0, r.stderr)
    r = run([sys.executable, MONTAGE, '--output-file', 'x.png', a])
    check('montage: a bad flag prints the argument order',
          r.returncode == 2 and 'usage:' in r.stderr and 'the first path is the output' in r.stderr, r.stderr)
    r = run([sys.executable, MONTAGE, '--help'])
    check('montage --help exits 0 with the usage', r.returncode == 0 and '-o/--out' in r.stdout, r.stdout[:200])
    r = run([sys.executable, MONTAGE, a, b])
    check('montage still refuses to overwrite an input', r.returncode == 2 and 'not a strip' in r.stderr, r.stderr)

    # ---------------------------------------------------------------- the config copies (no browser)
    print('preview-with-playwright.mjs, config copies')
    node = shutil.which('node')
    if not node:
        print('  skip  node is not installed')
    else:
        def save(src_doc, *opts, name='in.json'):
            src = os.path.join(tmp, name)
            with open(src, 'w', encoding='utf-8') as fh:
                json.dump(src_doc, fh)
            dst = os.path.join(tmp, 'out-' + name)
            r = run([node, PW, '--config', src, *opts, '--save-config', dst])
            got = json.load(open(dst, encoding='utf-8')) if r.returncode == 0 else None
            return r, got

        multi = load('onboarding-multilocale.json')
        r, got = save(multi, '--locale', 'sr')
        lz = flow_of(got)['localization'] if got else {}
        src_lz = flow_of(multi)['localization']
        only_sr = all(set(v['values']) <= {'sr'} for v in lz.get('content', {}).values())
        same = all(lz['content'][k]['values'].get('sr') == v['values'].get('sr')
                   for k, v in src_lz['content'].items()) if got else False
        check('--locale sr: sr is the default and only locale',
              r.returncode == 0 and lz.get('defaultLocale') == 'sr' and [l['code'] for l in lz['locales']] == ['sr'],
              r.stderr)
        check('--locale sr: every value is the sr value, nothing else kept', only_sr and same)

        # The report: a copy with another default drew images stored only under the first language
        # as empty. Two locales, de with texts only.
        vpn = load('vpn-timer-draft.json')
        two = copy.deepcopy(vpn)
        tl = flow_of(two)['localization']
        tl['locales'].append({'id': 'de', 'code': 'de', 'name': 'German'})
        for item in tl['content'].values():
            if item['kind'] != 'image' and 'en' in item['values']:
                item['values']['de'] = item['values']['en']
        n_images = sum(1 for v in tl['content'].values() if v['kind'] == 'image')
        r, got = save(two, '--locale', 'de', name='two.json')
        gl = flow_of(got)['localization'] if got else {}
        filled = all(gl['content'][k]['values'].get('de') == v['values'].get('en')
                     for k, v in tl['content'].items() if v['kind'] == 'image') if got else False
        check('--locale de: an image only in en shows the en image', r.returncode == 0 and n_images > 0 and filled, r.stderr)
        check('--locale de: says how many values fell back', f'{n_images} images' in r.stderr and 'en value' in r.stderr, r.stderr)

        r, _ = save(multi, '--locale', 'xx', name='bad.json')
        check('--locale unknown: exit 2 and lists the codes', r.returncode == 2 and 'sr-Latn' in r.stderr, r.stderr)
        r, _ = save(load('onboarding-custom-actions.json'), '--locale', 'en', name='old.json')
        check('--locale on a config with no catalog: exit 2 and says so',
              r.returncode == 2 and 'schemaVersion below 13' in r.stderr, r.stderr)

        quiz = load('onboarding-custom-actions.json')
        assert 'previewValue' in json.dumps(quiz), 'fixture lost its previews; pick another'
        r, got = save(quiz, '--no-previews', name='quiz.json')
        check('--no-previews strips every previewValue, keeps a bare config bare',
              r.returncode == 0 and 'previewValue' not in json.dumps(got) and 'screens' in got, r.stderr)
        env = {'config': flow_of(multi), 'remote_configs': [], 'id': 'x'}
        r, got = save(env, '--locale', 'en', name='env.json')
        check('--save-config keeps an envelope an envelope',
              r.returncode == 0 and isinstance(got.get('config'), dict) and got.get('id') == 'x', r.stderr)
        r = run([node, PW, '--config', os.path.join(tmp, 'env.json'), '--screen', 'a', '--screen', 'b',
                 '--out', os.path.join(tmp, 'x.png')])
        check('several screens without {screen} in --out: exit 2 before any browser',
              r.returncode == 2 and '{screen}' in r.stderr, r.stderr)

    # ---------------------------------------------------------------- shoot.sh with a stand-in browser
    print('shoot.sh, offline')

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    bin_dir = os.path.join(tmp, 'bin')
    os.makedirs(bin_dir)
    adapty = os.path.join(bin_dir, 'adapty')
    with open(adapty, 'w') as fh:   # prints a short preview URL naming the screen
        fh.write('#!/bin/bash\nscreen=default\nwhile [ $# -gt 0 ]; do [ "$1" = --screen ] && screen=$2; shift; done\n'
                 f'echo "http://127.0.0.1:{port}/flow-preview?screen=$screen#config=x"\n')
    drawn = os.path.join(tmp, 'drawn.png')
    png(drawn, 430, 900, lambda x, y: 20 <= x < 410 and (100 <= y < 300 or 600 <= y < 860))

    def browser(name, body):
        path = os.path.join(bin_dir, name)
        with open(path, 'w') as fh:
            fh.write('#!/bin/bash\nshot=""; for a in "$@"; do case "$a" in --screenshot=*) shot="${a#--screenshot=}";; esac; done\n'
                     'url="${@: -1}"\n' + body)
        os.chmod(path, 0o755)
        return path
    os.chmod(adapty, 0o755)
    ok_browser = browser('ok-browser', f'sleep 0.3; cp "{drawn}" "$shot"\n')
    dead_browser = browser('dead-browser', 'echo "[0101/000000.000:FATAL:zygote_host_impl_linux.cc] Running as root without --no-sandbox is not supported." >&2\nexit 1\n')
    slow_b = browser('slow-on-b', f'case "$url" in *screen=scr_b*) sleep 60;; esac; cp "{drawn}" "$shot"\n')
    late_browser = browser('late-browser', f'sleep 3; cp "{drawn}" "$shot"\n')

    cfg = os.path.join(tmp, 'cfg.json')
    shutil.copy(os.path.join(FIX, 'reviews-carousel.json'), cfg)

    def shoot(browser_path, screens, extra=None, **kw):
        out = tempfile.mkdtemp(dir=tmp)
        env = dict(os.environ, PLAYWRIGHT='0', CHROME=browser_path, ADAPTY=adapty, OUT=out, **(extra or {}))
        return out, subprocess.Popen(['bash', SHOOT, cfg, *screens], stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, env=env, **kw)

    t0 = time.time()
    out, p = shoot(ok_browser, ['scr_a', 'scr_b', 'scr_c'])
    text = p.communicate(timeout=120)[0]
    check('three screens: progress for each, rendered, one strip',
          p.returncode == 0 and all(f'[{i}/3]' in text for i in (1, 2, 3)) and text.count('   rendered ') == 3
          and 'strip-' in text, text)

    t0 = time.time()
    out, p = shoot(dead_browser, ['scr_a', 'scr_b'])
    text = p.communicate(timeout=120)[0]
    took = time.time() - t0
    check('a browser that exits without a file: says what it said, no 60 s retry, stops the batch',
          p.returncode == 1 and 'exited without a screenshot' in text and 'no-sandbox' in text
          and 'retrying' not in text and '[2/2]' not in text and took < 20, f'{took:.0f}s\n{text}')

    out, p = shoot(late_browser, ['scr_a', 'scr_b', 'scr_c'], {'TIME_LIMIT': '1'})
    text = p.communicate(timeout=120)[0]
    check('TIME_LIMIT stops the run and names the screens not rendered',
          p.returncode == 1 and 'TIME_LIMIT of 1s reached' in text and 'scr_b scr_c' in text, text)

    out, p = shoot(slow_b, ['scr_a', 'scr_b', 'scr_c'], start_new_session=True)
    seen, deadline = '', time.time() + 60
    while 'rendered scr_a' not in seen and time.time() < deadline:
        line = p.stdout.readline()
        if not line:
            break
        seen += line
    while '[2/3]' not in seen and time.time() < deadline:
        seen += p.stdout.readline()
    time.sleep(1)
    p.send_signal(signal.SIGTERM)
    text = seen + p.communicate(timeout=30)[0]
    kept = [f for f in os.listdir(out) if f.startswith('shot-') and f.endswith('-scr_a.png')]
    check('a stopped run keeps and names what it finished, and what it did not',
          p.returncode == 143 and 'Not rendered: scr_b scr_c' in text and 'LOOK AT:' in text and kept, text)
    server.shutdown()

    # ---------------------------------------------------------------- in-page helpers
    print('preview-with-playwright.mjs, in-page helpers')
    pw_dir = os.path.expanduser('~/.cache/adapty-flow-playwright')
    have_pw = any(os.path.isdir(os.path.join(pw_dir, 'node_modules', n)) for n in ('playwright', 'playwright-core'))
    if not (node and have_pw):
        print('  skip  Playwright is not installed in ~/.cache/adapty-flow-playwright')
    else:
        probe = os.path.join(tmp, 'probe.mjs')
        with open(probe, 'w') as fh:
            fh.write(f'''
import {{createRequire}} from 'node:module'
const mod = await import({json.dumps('file://' + PW)})
let chromium
for (const n of ['playwright', 'playwright-core']) {{ try {{ chromium = createRequire(process.cwd() + '/x.js')(n).chromium; break }} catch {{}} }}
let browser
for (const p of mod.browserCandidates()) {{ try {{ browser = await chromium.launch({{executablePath: p}}); break }} catch {{}} }}
if (!browser) {{ try {{ browser = await chromium.launch() }} catch {{ console.log('NO-BROWSER'); process.exit(0) }} }}
const page = await browser.newPage({{viewport: {{width: 1000, height: 1200}}}})
await page.setContent(`<div id=page><div id=stage style="width:390px;height:844px;position:relative;margin:100px">
  <div data-screen-content style="position:relative;width:390px;height:844px">
    <div id=scroll style="overflow-y:auto;height:844px"><div style="height:900px">tall content</div>
      <div style="overflow-y:auto;height:100px"><div style="height:500px">a card with its own scroll</div></div></div>
    <div id=dock style="position:absolute;bottom:0;left:0;right:0;height:60px">Continue</div>
  </div></div></div>
  <div id=toast style="position:fixed;top:120px;left:120px;width:200px;height:40px">Scheduled maintenance</div>
  <div id=far style="position:fixed;top:0;left:700px;width:200px;height:40px">elsewhere</div>`)
const hidden = await page.evaluate(mod.pageHideOverlays, '[data-screen-content]')
const dockShown = await page.evaluate(() => {{
  let o = 1
  for (let el = document.getElementById('dock'); el; el = el.parentElement) o *= Number(getComputedStyle(el).opacity)
  return String(o)
}})
const scroller = await page.evaluate(mod.pageScroller, '[data-screen-content]')
const blank = await page.evaluate(mod.pageIsBlank, '[data-screen-content]')
await page.setContent('<div data-screen-content style="width:390px;height:844px;background:#123"></div>')
const blank2 = await page.evaluate(mod.pageIsBlank, '[data-screen-content]')
console.log(JSON.stringify({{hidden, dockShown, scroller, blank, blank2}}))
await browser.close()
''')
        r = run([node, probe], cwd=pw_dir, timeout=120)
        if 'NO-BROWSER' in r.stdout:
            print('  skip  no Chromium-based browser could be launched')
        else:
            try:
                res = json.loads(r.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                res = {}
            check('overlay beside the screen hidden and named; one elsewhere left alone',
                  res.get('hidden') == ['Scheduled maintenance'], r.stdout + r.stderr)
            check("the screen's own docked layer is never hidden", res.get('dockShown') == '1', r.stdout)
            check('the screen scroller is found, a card with its own scroll is not',
                  res.get('scroller') == {'client': 844, 'scroll': 1000}, r.stdout)
            check('blank: text means drawn, a plain block means blank',
                  res.get('blank') is False and res.get('blank2') is True, r.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f.splitlines()[0][:300])
    sys.exit(1)
print('all checks passed')
