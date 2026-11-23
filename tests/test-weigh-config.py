#!/usr/bin/env python3
"""Calibration for `weigh-config.py`, the load-time weigh run before a save or a publish.

Repo-only. Runs the shipped script as a subprocess. File sizes come from a local HTTP server
this suite starts, so nothing reaches the network.

    FIRES   -- an image file over the threshold, named by its screen, with the WebP fix
            -- an image stored one byte over 1 MiB; a video stored at 5 MiB
            -- the default's image copied into other locales
            -- an image with its own file in three or more locales, with both fixes
            -- a three-sentence summary: what is heavy, what it does, what I can do
            -- a config over the threshold, with its preview share
    SILENT  -- every real export, offline (their config bytes are all under the threshold)
            -- an image bound in the default locale only, a small file
            -- one locale with its own file in a light config
            -- an image stored at 700 KB, 900 KB or exactly 1 MiB; a video one byte under 5 MiB
    SWAP    -- rebinds every place an old URL is used, id as a string, preview included
            -- refuses an upload result with no url
    WEBP    -- converts a PNG and does not enlarge it
            -- keeps an output over 2.5 MiB with exit 0 and no upload-cap message (save stubbed)

Usage: python3 tests/test-weigh-config.py    # 0 all pass, 1 a case regressed
"""
import base64, glob, http.server, json, os, subprocess, sys, tempfile, threading, zlib, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
from v13 import catalogued, localization  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGH = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'weigh-config.py')
FLOW = os.path.join(ROOT, 'tests', 'fixtures', 'onboarding-multilocale.json')
PREVIEW = 'UklGRhQJAABXRUJQVlA4IAgJAAAwSQCdASos' * 60

MIB = 1024 * 1024
SIZES = {'/big.png': 1536 * 1024, '/small.png': 20 * 1024, '/es.png': 20 * 1024,
         '/fr.png': 20 * 1024, '/de.png': 20 * 1024, '/700k.png': 700 * 1024,
         '/900k.png': 900 * 1024, '/edge.png': MIB, '/over.png': MIB + 1,
         '/under.mp4': 5 * MIB - 1, '/at.mp4': 5 * MIB}


class Sized(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200 if self.path in SIZES else 404)
        if self.path in SIZES:
            self.send_header('Content-Type', 'video/mp4' if self.path.endswith('.mp4')
                             else 'image/png')
            self.send_header('Content-Length', str(SIZES[self.path]))
        self.end_headers()

    def log_message(self, *a):
        pass


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Sized)
threading.Thread(target=server.serve_forever, daemon=True).start()
HOST = f'http://127.0.0.1:{server.server_address[1]}'

fails = []


def check(name, cond, detail=''):
    print(f'  {"ok   " if cond else "FAIL "} {name}')
    if not cond:
        fails.append(f'{name} {detail}'.strip())


def flow(values, locales=('en',), kind='image'):
    d = json.load(open(FLOW))
    d = localization.resolve(d.get('config', d))   # the read view, so locales can be set inline
    d['locales'] = [{'id': l, 'code': l, 'name': l.upper()} for l in locales]
    d['defaultLocale'] = locales[0]
    s = d['screens'][0]
    s['caption'] = 'Welcome'
    s['elements']['map']['el_900M'] = {
        'id': 'el_900M', 'type': kind, 'states': [],
        'props': {kind: {'_localizable': True, 'values': values},
                  'width': {'type': 'fill'}, 'height': {'type': 'fixed', 'value': 200},
                  'objectFit': 'cover', 'position': {'type': 'relative'}}}
    s['elements']['hierarchy']['children'].append({'id': 'el_900M'})
    return catalogued(d, allow_drops=True)


def img(path, preview=PREVIEW):
    return {'id': '516395', 'url': HOST + path, 'previewValue': preview}


def weigh(doc, *flags):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json')
        json.dump(doc, open(p, 'w'))
        r = subprocess.run([sys.executable, WEIGH, *flags, p], capture_output=True, text=True)
    if r.returncode == 2 or 'Traceback' in r.stderr:
        raise AssertionError(f'weigh-config.py failed to run:\n{r.stdout}\n{r.stderr}')
    return r.returncode, r.stdout


print('weigh-config.py')

for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json'))):
    code, out = weigh(json.load(open(f)), '--offline')
    check(f'SILENT offline on {os.path.relpath(f, ROOT)}', code == 0, out)

code, out = weigh(flow({'en': img('/small.png')}))
check('SILENT on a small default-only image', code == 0, out)

for path in ('/700k.png', '/900k.png', '/edge.png'):
    code, out = weigh(flow({'en': img(path)}))
    check(f'SILENT on an image stored at {SIZES[path]} bytes', code == 0, out)
code, out = weigh(flow({'en': img('/over.png')}))
check('FIRES on an image stored at 1 048 577 bytes', code == 1 and '1.0 MB PNG' in out, out)

video = lambda path: flow({'en': {'videoUrl': HOST + path}}, kind='video')
# both clips are over the 3 MB a user downloads in all, so only the file's own line tells
code, out = weigh(video('/under.mp4'))
check('SILENT on a video one byte under 5 MiB', 'The video on' not in out, out)
code, out = weigh(video('/at.mp4'))
check('FIRES on a video stored at 5 MiB', code == 1 and 'The video on Welcome is a 5.0 MB' in out,
      out)

code, out = weigh(flow({'en': img('/big.png')}))
check('FIRES on a 1.5 MB image', code == 1 and '1.5 MB PNG' in out, out)
check('NAMES the screen that shows it', 'on Welcome' in out, out)
check('OFFERS the WebP conversion', 'WebP' in out, out)
say = out.split('Say this, as the Load time line:\n')[-1].split('\n')[0]
check('SAYS three sentences: what, what it does, what I can do',
      say.count('. ') + say.endswith('.') == 3 and 'placeholder' in say and 'I can' in say, say)

code, out = weigh(flow({'en': img('/small.png'), 'es': img('/small.png')}, ('en', 'es')))
check('FIRES on the default copied into another locale', code == 1 and 'stored again in ES' in out,
      out)

code, out = weigh(flow({'en': img('/small.png'), 'es': img('/es.png')}, ('en', 'es')))
check('SILENT on one locale with its own file in a light config', code == 0, out)

locs = ('en', 'es', 'fr', 'de')
code, out = weigh(flow({l: img('/small.png' if l == 'en' else f'/{l}.png') for l in locs}, locs))
check('FIRES on an image with its own file in three locales', code == 1 and
      'own file in 3 languages' in out, out)
check('OFFERS one image for every language', 'one image for every language' in out, out)
check('OFFERS a flow per language group', 'split the flow by language' in out, out)

heavy = flow({'en': img('/small.png', PREVIEW * 600)})
code, out = weigh(heavy, '--offline')
check('FIRES on a config over 1 MB, with the preview share', code == 1 and
      'The flow itself is' in out and 'of it image previews' in out, out)

with tempfile.TemporaryDirectory() as tmp:
    doc = flow({'en': img('/big.png'), 'es': img('/big.png')}, ('en', 'es'))
    cfg, up, bad = (os.path.join(tmp, n) for n in ('c.json', 'up.json', 'bad.json'))
    json.dump({'config': doc}, open(cfg, 'w'))
    json.dump({'id': 777, 'url': 'https://public-media.adapty.io/x/big.webp',
               'preview_base64': 'UklGRnew'}, open(up, 'w'))
    json.dump({'id': 777}, open(bad, 'w'))
    r = subprocess.run([sys.executable, WEIGH, 'swap', cfg, HOST + '/big.png', up],
                       capture_output=True, text=True)
    swapped = json.load(open(cfg))['config']['localization']['content']
    vals = [v for e in swapped.values() if e.get('kind') == 'image' for v in e['values'].values()]
    check('SWAP rebinds both locales', r.returncode == 0 and 'rebound 2' in r.stdout, r.stdout)
    check('SWAP writes the id as a string with the preview',
          all(v == {'id': '777', 'url': 'https://public-media.adapty.io/x/big.webp',
                    'previewValue': 'UklGRnew'} for v in vals), vals)
    r = subprocess.run([sys.executable, WEIGH, 'swap', cfg, 'https://x/old.png', bad],
                       capture_output=True, text=True)
    check('SWAP refuses an upload result with no url', r.returncode != 0, r.stdout)

    # a 64x32 opaque PNG, written by hand so the suite needs no image library
    raw = b''.join(b'\x00' + bytes([200, 40, 90]) * 64 for _ in range(32))
    chunk = lambda t, d: (struct.pack('>I', len(d)) + t + d +
                          struct.pack('>I', zlib.crc32(t + d) & 0xffffffff))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 64, 32, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
    src, dst = os.path.join(tmp, 'a.png'), os.path.join(tmp, 'a.webp')
    open(src, 'wb').write(png)
    r = subprocess.run([sys.executable, WEIGH, 'webp', src, dst], capture_output=True, text=True)
    head = open(dst, 'rb').read(30) if os.path.exists(dst) else b''
    check('WEBP writes a WebP file', r.returncode == 0 and head[8:12] == b'WEBP', r.stdout + r.stderr)
    width = struct.unpack('<H', head[26:28])[0] & 0x3fff if head[12:16] == b'VP8 ' else None
    check('WEBP does not enlarge a small image', width in (None, 64), width)

    # the image save stubbed (a stand-in Pillow) to write 2 700 000 bytes, over 2.5 MiB
    stub = '''
import runpy, sys, types
class Im:
    width, height = 4000, 3000
    def resize(self, wh):
        self.width, self.height = wh
        return self
    def save(self, dst, *a, **k):
        open(dst, 'wb').write(b'RIFF' + bytes(2700000 - 4))
pil, image, ops = (types.ModuleType(n) for n in ('PIL', 'PIL.Image', 'PIL.ImageOps'))
image.open = lambda p: Im()
ops.exif_transpose = lambda im: im
pil.Image, pil.ImageOps = image, ops
sys.modules.update({'PIL': pil, 'PIL.Image': image, 'PIL.ImageOps': ops})
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
    big = os.path.join(tmp, 'big.webp')
    r = subprocess.run([sys.executable, '-c', stub, WEIGH, 'webp', src, big],
                       capture_output=True, text=True)
    kept = os.path.getsize(big) if os.path.exists(big) else None
    check('WEBP keeps an output over 2.5 MiB, exit 0, no upload-cap message',
          r.returncode == 0 and kept == 2700000 and '2.5 MB' not in r.stdout + r.stderr,
          (r.returncode, kept, r.stdout + r.stderr))

server.shutdown()
print(f'\n{"FAILED: " + str(len(fails)) if fails else "all passed"}')
sys.exit(1 if fails else 0)
