#!/usr/bin/env python3
"""Weigh an Adapty flow config before it is saved or published: what a device downloads.

SCOPE: this SHIPS. Stdlib only. Run it on the exact bytes you are about to write.

    python3 references/weigh-config.py draft.json             # weigh; HEADs every asset URL
    python3 references/weigh-config.py --offline draft.json   # the config's own bytes only
    python3 references/weigh-config.py webp hero.png hero.webp [--max-width 1290] [--quality 82]
    python3 references/weigh-config.py swap draft.json <old-url> media/hero.json -o draft.json

Two things decide how fast a flow loads on a phone, and this reports both:

- the CONFIG itself. The app downloads all of it before the first screen shows, and almost all
  of its weight is `previewValue` -- a base64 thumbnail stored once per image per locale that has
  its own value. So a per-locale image, or a copy of the default's image in another locale, adds
  a whole preview to every download;
- the FILES the config points at. Their size is read from the asset host's `Content-Length`
  (one HEAD request per distinct URL, nothing downloaded). A 6 MB PNG behind one image element
  costs the user more than the rest of the flow together.

The weigh prints the findings in plain words, ready to relay, and the fix for each. Exit 0 when
nothing is over a threshold, 1 when there is something to tell the user, 2 when the file could
not be read.

`webp` converts one image to WebP and caps its width (1290 px is a full-width image on the
widest phone at 3x) without enlarging a smaller one. It uses Pillow when it is installed, else
`sharp` installed once into ~/.cache/adapty-flow-webp; it prints the size before and after. A GIF becomes an animated WebP
on the `sharp` path only.

`swap` rebinds every place the config uses <old-url> (each locale, each fill) to the asset a
`flows media upload --json` call returned, with its id as a string and its preview, and writes
the result. Nothing is guessed: it refuses an upload file without an id and a url.
"""
import json, os, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

KB, MB = 1024, 1024 * 1024
# Thresholds, in one place. A file above these is worth a sentence to the user; none of them is
# a publish blocker, and the save goes ahead on the user's word either way.
IMAGE_HEAVY = 500 * KB      # one image file
VIDEO_HEAVY = 5 * MB        # one video file
CONFIG_HEAVY = 1 * MB       # the config JSON the app downloads before the first screen
MEDIA_HEAVY = 3 * MB        # every distinct file the flow shows, added up
LOCALE_FILES = 3            # an image with its own file in this many locales or more
SLOW_LINK = 1.5e6 / 8       # bytes per second on a slow mobile connection (1.5 Mbit/s)
# The SDK's default `loadTimeout` for a flow's config is 5 s and the backend fetch gets 0.5 s less;
# past it, the SDK fetches again from Adapty's fallback server and throws if that fails too
# (AdaptySDK-iOS 4.3.1, Sources/Placements/UIBuilder/Adapty+UIBuilder.swift). Images are not part
# of that fetch: the screen opens and each image paints its preview until the file arrives.
SDK_WINDOW = 4.5            # seconds
MAX_WIDTH = 1290

MEDIA_KINDS = ('image', 'video')
MEDIA_PROPS = ('image', 'imageDark', 'video', 'videoDark')
URL_KEYS = ('url', 'videoUrl')


def size(n):
    return f'{n / MB:.1f} MB' if n >= MB else f'{round(n / KB)} KB'


def secs(n):
    s = n / SLOW_LINK
    return f'about {s:.0f} s' if s >= 1 else 'under a second'


def unwrap(d):
    if isinstance(d, dict) and 'screens' not in d and isinstance(d.get('config'), dict):
        return d['config']
    return d


def urls_in(value):
    if isinstance(value, dict):
        return [value[k] for k in URL_KEYS if isinstance(value.get(k), str)
                and value[k].startswith('http')]
    return []


def where_used(d):
    """{lid or id(inline value map): screen name} for every media prop on a screen element."""
    out = {}
    for s in d.get('screens') or []:
        name = s.get('caption') or s.get('name') or s.get('id') or 'a screen'
        for el in ((s.get('elements') or {}).get('map') or {}).values():
            for prop in MEDIA_PROPS:
                v = (el.get('props') or {}).get(prop)
                if isinstance(v, dict) and v.get('_lid'):
                    out.setdefault(v['_lid'], name)
                elif isinstance(v, dict) and v.get('_localizable'):
                    out.setdefault(id(v), name)
    return out


def media_entries(d):
    """Yield (key, kind, {locale: value}) for every localizable media value, both forms: the
    stored catalog (`localization.content`) and the inline `_localizable` map older documents
    carry."""
    for lid, e in ((d.get('localization') or {}).get('content') or {}).items():
        if isinstance(e, dict) and e.get('kind') in MEDIA_KINDS:
            yield lid, e['kind'], e.get('values') or {}
    for s in d.get('screens') or []:
        for el in ((s.get('elements') or {}).get('map') or {}).values():
            for prop in MEDIA_PROPS:
                v = (el.get('props') or {}).get(prop)
                if isinstance(v, dict) and v.get('_localizable'):
                    yield id(v), ('video' if prop.startswith('video') else 'image'), \
                        v.get('values') or {}


def fills(node):
    """Every flat `{type: image|video, image|video: {...}}` layer under a node: screen and stack
    fills, `propsByState`, `components`, theme colour styles. Keyed on the layer's own `type`,
    so a font's `url` is never read as an asset."""
    if isinstance(node, dict):
        t = node.get('type')
        if t in MEDIA_KINDS and isinstance(node.get(t), dict):
            yield t, node[t]
        for v in node.values():
            yield from fills(v)
    elif isinstance(node, list):
        for v in node:
            yield from fills(v)


def placed_fills(d):
    """(kind, value, where) for every fill, named by the screen that holds it."""
    for s in d.get('screens') or []:
        name = s.get('caption') or s.get('name') or s.get('id') or 'a screen'
        for kind, v in fills(s):
            yield kind, v, f'the background of {name}'
    for key, where in (('components', 'a shared component'), ('theme', 'a colour style')):
        for kind, v in fills(d.get(key)):
            yield kind, v, where


def head(url):
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=10) as r:
            n = r.headers.get('Content-Length')
            return (int(n) if n and n.isdigit() else None), (r.headers.get('Content-Type') or '')
    except Exception:
        return None, ''


def pixels(url):
    """(width, height) of an image from its first 64 KB, read with a Range request, or None.
    PNG, GIF and WebP carry their size in the header; a JPEG in its first SOF marker."""
    try:
        req = urllib.request.Request(url, headers={'Range': 'bytes=0-65535'})
        with urllib.request.urlopen(req, timeout=10) as r:
            b = r.read(65536)
    except Exception:
        return None
    be = lambda i, n: int.from_bytes(b[i:i + n], 'big')
    le = lambda i, n: int.from_bytes(b[i:i + n], 'little')
    if b[:8] == b'\x89PNG\r\n\x1a\n' and len(b) >= 24:
        return be(16, 4), be(20, 4)
    if b[:6] in (b'GIF87a', b'GIF89a'):
        return le(6, 2), le(8, 2)
    if b[:4] == b'RIFF' and b[8:12] == b'WEBP' and len(b) >= 30:
        if b[12:16] == b'VP8 ':
            return le(26, 2) & 0x3fff, le(28, 2) & 0x3fff
        if b[12:16] == b'VP8L':
            v = le(21, 4)
            return (v & 0x3fff) + 1, ((v >> 14) & 0x3fff) + 1
        if b[12:16] == b'VP8X':
            return le(24, 3) + 1, le(27, 3) + 1
    if b[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(b):
            if b[i] != 0xFF:
                i += 1
                continue
            m = b[i + 1]
            if m in (0xC0, 0xC1, 0xC2):
                return be(i + 7, 2), be(i + 5, 2)
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                i += 2
                continue
            i += 2 + be(i + 2, 2)
    return None


def weigh(path, offline):
    raw = json.load(open(path))
    d = unwrap(raw)
    config_bytes = len(json.dumps(d, separators=(',', ':'), ensure_ascii=False).encode())
    lz = d.get('localization') or {}
    dflt = lz.get('defaultLocale') or d.get('defaultLocale')
    names = {l.get('id'): l.get('name') or l.get('code') or l.get('id')
             for l in (lz.get('locales') or []) if isinstance(l, dict)}
    used = where_used(d)

    files = {}            # url -> {kind, screens, locales}
    preview_bytes = 0
    copies = []           # (screen, locale) holding the default's own file again
    own_files = []        # (screen, [locales]) where a locale has a different file
    for key, kind, vals in media_entries(d):
        screen = used.get(key, 'a shared component')
        base = urls_in(vals.get(dflt))
        own, own_preview = [], 0
        for loc, v in vals.items():
            preview_bytes += len((v or {}).get('previewValue') or '') if isinstance(v, dict) else 0
            for u in urls_in(v):
                f = files.setdefault(u, {'kind': kind, 'screens': set(), 'locales': set()})
                f['screens'].add(screen)
                f['locales'].add(loc)
                f['preview'] = f.get('preview') or bool(v.get('previewValue'))
            if loc != dflt and base:
                if urls_in(v) == base:
                    copies.append((screen, loc))
                elif urls_in(v):
                    own.append(loc)
                    own_preview += len(v.get('previewValue') or '')
        if own:
            own_files.append((screen, own, own_preview))
    for kind, v, where in placed_fills(d):
        preview_bytes += len(v.get('previewValue') or '')
        for u in urls_in(v):
            f = files.setdefault(u, {'kind': kind, 'screens': set(), 'locales': set()})
            f['screens'].add(where)
            f['preview'] = f.get('preview') or bool(v.get('previewValue'))

    if not offline and files:
        with ThreadPoolExecutor(8) as pool:
            for u, (n, ctype) in zip(files, pool.map(head, files)):
                files[u]['bytes'], files[u]['type'] = n, ctype

    lines, fixes = [], []
    # the three sentences the user reads: what is heavy, what it does to them, what I can do
    what, effects, offers = [], [], []
    loc_screen = None
    r_w = lambda w: next(r for r, x in what if x == w)
    lang = lambda l: names.get(l, l)
    if config_bytes >= CONFIG_HEAVY:
        share = f', {size(preview_bytes)} of it image previews' if preview_bytes >= KB else ''
        t = config_bytes / SLOW_LINK
        if t > SDK_WINDOW:
            then = (f'On a slow mobile connection it needs about {t:.0f} s, past the 5 s the Adapty '
                    f'SDK allows by default: the SDK then downloads it again from Adapty\'s '
                    f'fallback server, and if that fails too, your app gets an error instead of '
                    f'the flow.')
        else:
            then = (f'On a slow mobile connection that takes about {t:.0f} s of the 5 s the Adapty '
                    f'SDK allows by default; past 5 s the app gets an error instead of the flow '
                    f'unless Adapty\'s fallback server answers.')
        lines.append(f'The flow itself is {size(config_bytes)}{share}. Someone opening it for the '
                     f'first time downloads all of it before its first screen shows. {then}')
        what.append((0 if t > SDK_WINDOW else 5, f'the flow itself is {size(config_bytes)}'
                     + (', mostly image previews' if preview_bytes * 2 > config_bytes else '')))
        effects.append((3, 'On a slow mobile connection it can miss the 5 s the Adapty SDK allows '
                           'for loading a flow, and then your app may get an error instead of it.')
                       if t > SDK_WINDOW else
                       (1, f'On a slow mobile connection it takes about {t:.0f} s of the 5 s the '
                           f'Adapty SDK allows for loading a flow before its first screen.'))
    if copies:
        locs = sorted({lang(l) for _, l in copies})
        lines.append(f'{len(copies)} image(s) are stored again in {", ".join(locs)} with the same '
                     f'file as {lang(dflt)}. Those languages already show the {lang(dflt)} image, '
                     f'so each copy only adds weight.')
        fixes.append('Delete the repeated copies; nothing on screen changes. I can do it.')
        what.append((4, f'{len(copies)} image(s) are stored again in other languages with the '
                        f'same file'))
        effects.append((1, 'Each copy makes the flow every user downloads heavier and changes '
                           'nothing on screen.'))
        offers.append('delete the repeated copies')
    many = [x for x in own_files if len(x[1]) >= LOCALE_FILES]
    if many or (own_files and config_bytes >= CONFIG_HEAVY):
        for s, o, pv in (many or own_files):
            lines.append(f'An image on {s} has its own file in {len(o)} languages '
                         f'({", ".join(lang(l) for l in sorted(o)[:6])}'
                         f'{", …" if len(o) > 6 else ""}). Each user downloads only their own '
                         f'language\'s file, but the flow carries a small preview of every '
                         f'version ({size(pv)} for the other languages). That grows with each '
                         f'language you add, and the whole flow has to download within the 5 s '
                         f'the Adapty SDK allows by default before its first screen shows.')
        s0, o0 = (many or own_files)[0][:2]
        what.append((3, f'the image on {s0} has a separate file in {len(o0)} languages'))
        loc_screen = s0
        effects.append((1, 'The flow carries a preview of every version, so it gets heavier with '
                           'every language you add, and all of it loads before the first screen.'))
        offers.append(f'use one image on {s0} for every language or split the flow by language')
        fixes.append('For the per-language image, I can do either: use one image for every '
                     'language, with its words moved into a text element, or split the flow '
                     'into one flow per language group, each shown to its own audience. Tell me '
                     'which, or keep it as it is.')
    heavy = [(u, f) for u, f in files.items() if f.get('bytes') and f['bytes'] >= (
        VIDEO_HEAVY if f['kind'] == 'video' else IMAGE_HEAVY)]
    heavy_top = max((f for _, f in heavy), key=lambda f: f['bytes'], default=None)
    rest = [f for _, f in heavy if f is not heavy_top]
    if len(rest) == 1:
        what.append((2, f'the {rest[0]["kind"]} on {", ".join(sorted(rest[0]["screens"]))} adds '
                        f'another {size(rest[0]["bytes"])}'))
    elif rest:
        what.append((2, f'{len(rest)} more files add {size(sum(f["bytes"] for f in rest))}'))
    for u, f in sorted(heavy, key=lambda x: -x[1]['bytes']):
        fmt = (f.get('type') or '').split('/')[-1].upper() or os.path.splitext(u)[1][1:].upper()
        where = ', '.join(sorted(f['screens']))
        on = 'in' if where.startswith(('the background', 'a ')) else 'on'
        why = ''
        wh = pixels(u) if f['kind'] == 'image' else None
        if wh and wh[0] > MAX_WIDTH:
            why = (f', {wh[0]}×{wh[1]} px: {wh[0] / MAX_WIDTH:.0f}× wider than the widest phone '
                   f'screen ({MAX_WIDTH} px), so most of its weight is pixels nobody sees')
        elif wh:
            why = f', {wh[0]}×{wh[1]} px'
        if f['kind'] == 'video':
            seen = 'the video sits still until enough of it has downloaded'
        elif f.get('preview'):
            seen = 'people see a blurred placeholder in its place'
        else:
            seen = 'that space is empty'
        if f is heavy_top:
            wider = (f', {wh[0] / MAX_WIDTH:.0f}× wider than any phone screen shows'
                     if wh and wh[0] > MAX_WIDTH else '')
            what.append((1, f'the {f["kind"]} {on} {where} is a {size(f["bytes"])} {fmt}{wider}'))
            there = ('the video stands still' if f['kind'] == 'video' else
                     'people see a blurred placeholder there' if f.get('preview') else
                     'people see an empty space there')
            effects.append((2, f'On a slow mobile connection {there} for {secs(f["bytes"])}, '
                               f'while they decide whether to go on.'))
        lines.append(f'The {f["kind"]} {on} {where} is a {size(f["bytes"])} {fmt}{why}. The '
                     f'screen opens without waiting for it, so on a slow mobile connection {seen} '
                     f'for {secs(f["bytes"])}, and they read the screen and decide whether to go on '
                     f'before the picture arrives. File: {u}')
    if any(f['kind'] == 'image' and 'webp' not in (f.get('type') or '') for _, f in heavy):
        fixes.append('Convert the heavy images to WebP at the size they show: usually 70-90% '
                     'smaller with no visible difference. I can convert, upload and rebind them.')
        offers.insert(0, 'convert the heavy images to WebP (usually 70-90% smaller, they look '
                         'the same)')
    if any(f['kind'] == 'image' and 'webp' in (f.get('type') or '') for _, f in heavy):
        fixes.append('A WebP that is still heavy is larger than it shows: I can scale it down '
                     'to the width it fills.')
        offers.insert(0, 'scale the heavy WebP images down to the size they show')
    if any(f['kind'] == 'video' for _, f in heavy):
        fixes.append('Shorten or re-encode the video (H.264, 720 px wide is plenty for a phone) '
                     'and upload it again in the builder; I cannot upload a video.')
        offers.append('tell you how to re-encode the video for the builder')
    known = sum(f.get('bytes') or 0 for f in files.values())
    # what one user gets: the default language's files plus every fill, not each locale's variant
    mine = sum(f.get('bytes') or 0 for f in files.values()
               if not f['locales'] or dflt in f['locales'])
    if mine >= MEDIA_HEAVY and not what:
        what.append((6, f'a user in {lang(dflt)} downloads {size(mine)} of images and video'))
        effects.append((1, 'On a slow mobile connection that is '
                           f'{secs(mine)}, out of their mobile data.'))
    if mine >= MEDIA_HEAVY:
        lines.append(f'A user in {lang(dflt)} downloads {size(mine)} of images and video to see '
                     f'every screen: {secs(mine)} on a slow mobile connection, and all of it '
                     f'comes out of their mobile data.')
    unknown = [u for u, f in files.items() if f.get('bytes') is None]

    print(f'config: {size(config_bytes)} ({size(preview_bytes)} previews); '
          f'{len(files)} distinct file(s)' + ('' if offline else
          f', {size(known)} measured, {len(unknown)} not measurable'))
    if lines:
        both = lambda xs: xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]
        parts = [w for _, w in sorted(what)[:3]]
        top = next((w for r, w in what if r == 1), '')
        parts = [w.replace(f'the image on {loc_screen} has', f'the {loc_screen} image also has')
                 if r_w(w) == 3 and f' on {loc_screen} ' in top + ' ' else w for w in parts]
        if any(',' in w for w in parts) and len(parts) > 2:
            first = '; '.join(parts[:-1]) + '; and ' + parts[-1]
        elif len(parts) == 2 and ',' in parts[0]:
            first = parts[0] + ', and ' + parts[1]
        else:
            first = both(parts)
        say = [first[0].upper() + first[1:] + '.',
               max(effects, key=lambda e: e[0])[1]]
        if len(offers) == 1:
            say.append(f'I can {offers[0]} if you want.')
        elif offers:
            say.append(f'I can {", or ".join(offers)}: tell me which, or keep it as it is.')
        print('\nSay this, as the Load time line:')
        print(' '.join(say))
        print('\nDetails, only if the user asks:')
        for x in lines:
            print(f'- {x}')
        for x in dict.fromkeys(fixes):
            print(f'- Fix: {x}')
    if offline and files:
        print('\n(offline: file sizes not read; run without --offline to weigh the files)')
    elif unknown:
        print(f'\nNot measured (the host gave no size): {", ".join(unknown[:5])}')
    return 1 if lines else 0


def webp(src, dst, max_width, quality):
    before = os.path.getsize(src)
    gif = src.lower().endswith('.gif')
    done = None
    if not gif:
        try:
            from PIL import Image, ImageOps
            im = ImageOps.exif_transpose(Image.open(src))
            if im.width > max_width:
                im = im.resize((max_width, round(im.height * max_width / im.width)))
            im.save(dst, 'WEBP', quality=quality, method=6)
            done = 'Pillow'
        except ImportError:
            pass
    if not done:
        cache = os.path.expanduser('~/.cache/adapty-flow-webp')
        os.makedirs(cache, exist_ok=True)
        if not os.path.isdir(os.path.join(cache, 'node_modules', 'sharp')):
            subprocess.run(['npm', 'i', '--silent', '--no-audit', '--no-fund', 'sharp@0.33.5'],
                           cwd=cache, check=True)
        js = ("const s=require('sharp');const [i,o,w,q]=process.argv.slice(1);"
              "s(i,{animated:true}).rotate().resize({width:+w,withoutEnlargement:true})"
              ".webp({quality:+q,effort:6}).toFile(o).catch(e=>{console.error(e.message);"
              "process.exit(1)})")
        subprocess.run(['node', '-e', js, os.path.abspath(src), os.path.abspath(dst),
                        str(max_width), str(quality)], cwd=cache, check=True)
        done = 'sharp'
    after = os.path.getsize(dst)
    print(f'{src}: {size(before)} -> {dst}: {size(after)} ({100 - after * 100 // before}% '
          f'smaller, {done})')
    if after > 2.5 * MB:
        print('still over the ~2.5 MB upload cap: lower --quality or --max-width')
        return 1
    return 0


def swap(path, old, upload, out):
    up = json.load(open(upload))
    if not up.get('id') or not up.get('url'):
        sys.exit(f'{upload}: no id/url in the upload result; nothing swapped')
    new = {'id': str(up['id']), 'url': up['url']}
    if up.get('preview_base64'):
        new['previewValue'] = up['preview_base64']
    raw = json.load(open(path))
    n = 0

    def walk(o):
        nonlocal n
        if isinstance(o, dict):
            if o.get('url') == old:
                o.clear()
                o.update(new)
                n += 1
                return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(raw)
    if not n:
        sys.exit(f'{old} is not used in {path}; nothing swapped')
    json.dump(raw, open(out, 'w'), ensure_ascii=False, indent=2)
    print(f'rebound {n} place(s) from {old} to {new["url"]} -> {out}')
    return 0


def main(a):
    try:
        if a[:1] == ['webp'] and len(a) >= 3:
            w = int(a[a.index('--max-width') + 1]) if '--max-width' in a else MAX_WIDTH
            q = int(a[a.index('--quality') + 1]) if '--quality' in a else 82
            return webp(a[1], a[2], w, q)
        if a[:1] == ['swap'] and len(a) >= 4:
            out = a[a.index('-o') + 1] if '-o' in a else a[1]
            return swap(a[1], a[2], a[3], out)
        files = [x for x in a if not x.startswith('--')]
        if len(files) != 1:
            print(__doc__.split('\n\n')[1])
            return 2
        return weigh(files[0], '--offline' in a)
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        print(f'weigh-config: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
