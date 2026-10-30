#!/usr/bin/env python3
"""Join screenshots side by side so several screens can be inspected in ONE look.

Why this ships: phase 4 asks you to *look* at the render, and a multi-screen change means
several PNGs. Opening them one at a time costs a round trip and a full image each time;
one strip costs a single look, and it is also the only way to see a before/after pair or a
default-vs-selected pair next to each other, which is what makes a difference visible at all.

    montage.py out.png a.png b.png c.png          # left to right, 8px white gutter
    montage.py --gutter 0 out.png a.png b.png     # flush, for a pixel-diff comparison
    montage.py -o out.png a.png b.png             # the same; -o/--out may go anywhere

Without -o, the FIRST path is the output and the rest are the inputs.

Pure stdlib: no Pillow, no install. Handles 8-bit RGB/RGBA/greyscale non-interlaced PNGs,
which is what headless Chrome emits. Images of different heights are top-aligned and padded.
"""
import struct
import sys
import zlib

WHITE = (255, 255, 255)
# Written into every strip, so a rerun may replace its own output and nothing else.
MARK = b'Software\x00montage.py'


def read_png(path):
    """-> (width, height, channels, [row bytes]). Undoes the per-row filters."""
    data = open(path, 'rb').read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError(f'{path}: not a PNG')
    pos, idat, w = 8, b'', None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h, depth, colour, _, _, interlace = struct.unpack('>IIBBBBB', chunk)
        elif typ == b'IDAT':
            idat += chunk
        pos += 12 + ln
    if w is None:
        raise ValueError(f'{path}: no IHDR')
    if depth != 8 or interlace:
        raise ValueError(f'{path}: need 8-bit non-interlaced, got depth={depth} '
                         f'interlace={interlace}')
    nch = {0: 1, 2: 3, 4: 2, 6: 4}.get(colour)
    if nch is None:
        raise ValueError(f'{path}: palette PNGs (colour type {colour}) not supported')
    raw = zlib.decompress(idat)
    stride, rows, prev, p = w * nch, [], bytearray(w * nch), 0
    for _ in range(h):
        f = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if f == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                left = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                b = prev[i]
                c = prev[i - nch] if i >= nch else 0
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc
                                      else (b if pb <= pc else c))) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, nch, rows


def rgb_row(row, nch, w):
    if nch == 3:
        return row
    if nch == 4:
        return b''.join(row[x * 4:x * 4 + 3] for x in range(w))
    if nch == 1:
        return b''.join(bytes((row[x],)) * 3 for x in range(w))
    return b''.join(bytes((row[x * 2],)) * 3 for x in range(w))    # greyscale+alpha


def write_png(path, width, height, rows_rgb):
    def chunk(typ, payload):
        body = typ + payload
        return struct.pack('>I', len(payload)) + body + struct.pack('>I', zlib.crc32(body))

    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    body = b''.join(b'\x00' + r for r in rows_rgb)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n'
                           + chunk(b'IHDR', header)
                           + chunk(b'tEXt', MARK)
                           + chunk(b'IDAT', zlib.compress(body, 6))
                           + chunk(b'IEND', b''))


USAGE = ('usage: montage.py [--gutter N] [-o OUT.png] OUT.png|IN.png IN.png ...\n'
         '    montage.py strip.png a.png b.png        # the first path is the output\n'
         '    montage.py -o strip.png a.png b.png     # or name it with -o/--out, anywhere')


def parse(argv):
    """-> (out, sources, gutter), or a message saying what is wrong."""
    gutter, out, rest, i = 8, None, [], 0
    while i < len(argv):
        a = argv[i]
        name, eq, val = a.partition('=')
        if name in ('--gutter', '-o', '--out', '--output'):
            if not eq:
                if i + 1 >= len(argv):
                    return f'{name} needs a value'
                val, i = argv[i + 1], i + 1
            if name == '--gutter':
                try:
                    gutter = int(val)
                except ValueError:
                    return f'--gutter takes a number of pixels, not {val!r}'
            else:
                out = val
        elif a.startswith('-') and a != '-':
            return f'unknown option {a}'
        else:
            rest.append(a)
        i += 1
    if out is None:
        if len(rest) < 2:
            return 'need an output and at least one input'
        out, rest = rest[0], rest[1:]
    if not rest:
        return 'need at least one input image'
    return out, rest, gutter


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0 if argv else 2
    parsed = parse(argv)
    if isinstance(parsed, str):
        print(f'montage: {parsed}\n{USAGE}', file=sys.stderr)
        return 2
    out, sources, gutter = parsed
    # The output comes first, so `montage.py a.png b.png` used to overwrite the render a.png with
    # a strip of b.png alone, silently. Refuse to write over any file this script did not make.
    try:
        prior = open(out, 'rb').read()
    except OSError:
        prior = None
    if out in sources or (prior is not None and MARK not in prior):
        print(f'montage: {out} already exists and is not a strip this script made, so writing it '
              f'would destroy it. The output file comes first and must be a new name:\n'
              f'    montage.py strip.png {" ".join([out] + sources)}', file=sys.stderr)
        return 2
    try:
        imgs = [read_png(p) for p in sources]
    except (ValueError, OSError) as exc:
        print(f'montage: {exc}', file=sys.stderr)
        return 2
    height = max(i[1] for i in imgs)
    width = sum(i[0] for i in imgs) + gutter * (len(imgs) - 1)
    pad = bytes(WHITE) * gutter
    rows = []
    for y in range(height):
        row = bytearray()
        for k, (w, h, nch, src) in enumerate(imgs):
            if k:
                row += pad
            row += rgb_row(src[y], nch, w) if y < h else bytes(WHITE) * w
        rows.append(bytes(row))
    write_png(out, width, height, rows)
    print(f'{out}  {width}x{height}  <- {len(sources)} image(s): {", ".join(sources)}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
