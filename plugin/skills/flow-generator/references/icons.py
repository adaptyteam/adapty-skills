#!/usr/bin/env python3
"""The renderer's own icon bundle — the markup a flow needs that an author cannot invent.

A `phosphor` icon resolves from the renderer's OWN bundle by name, so an authored
`raw` under a name the bundle lacks draws NOTHING — measured: a correct two-stroke SVG under
`name: "CloseX"`, correctly declared in `_meta.icons`, rendered as empty space twice, while
`name: "X"` drew immediately. Every gate is blind to it: `flows config validate` returns
`valid: true`, the schema types `name` as a bare string, and `config preview` draws a blank the
same way a 1pt element does. The standing advice was therefore "take the name AND its `raw` from
a real export", which limits an author to the dozen glyphs the corpus happens to contain. This
module replaces that with the bundle itself: 4,536 variants over 1,512 names, three weights.

The pack is vendored VERBATIM from `adapty/adapty-agents`, which generates it and ships it in
production (`src/share/generated/phosphor-icons.json.gz`). Verbatim is the point: re-vendoring is
a plain copy and a diff against upstream stays meaningful. Everything this skill adds — the
builder's serialization of `raw`, the `_meta.icons` entry shape — lives here in code, never in
the data.

    python3 icons.py ArrowRight              # the _meta.icons entry, as JSON
    python3 icons.py Star fill               # a weight other than regular
    python3 icons.py spinner1                # a Builder custom icon, for spinner()
    python3 icons.py --search arrow          # names containing "arrow"

Importable as `icons` by anything sitting beside it (`flowkit.py`, `verify-config.py`).
"""

import difflib
import gzip
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ICON_PACK = os.path.join(_HERE, 'phosphor-icons.json.gz')
CUSTOM_ICONS = os.path.join(_HERE, 'custom-icons.json')

# The three weights the builder publishes. The upstream Phosphor package ships six (thin, light,
# duotone as well); the pack carries the three the Dashboard resolves, and a weight outside them
# is not a near-miss to suggest but a value the renderer has no glyph for.
WEIGHTS = ('regular', 'bold', 'fill')

_cache = {}


def _load(path):
    if path not in _cache:
        opener = gzip.open if path.endswith('.gz') else open
        with opener(path, 'rt', encoding='utf-8') as fh:
            _cache[path] = json.load(fh)
    return _cache[path]


# --------------------------------------- icons ---------------------------------------

def pack_version():
    """The Phosphor package and version the vendored markup came from."""
    pack = _load(ICON_PACK)
    return f"{pack['package']}@{pack['version']}"


def phosphor_names():
    """Every icon name in the bundle, sorted."""
    return sorted({key.split('::')[0] for key in _load(ICON_PACK)['icons']})


def has_phosphor(name, weight='regular'):
    return f'{name}::{weight}' in _load(ICON_PACK)['icons']


def suggest(name, limit=6):
    """Close matches for a name the bundle lacks — the whole value of a failed lookup."""
    names = phosphor_names()
    close = difflib.get_close_matches(name, names, n=limit, cutoff=0.6)
    if close:
        return close
    lowered = name.lower()
    return [n for n in names if lowered in n.lower()][:limit]


def icon_raw(name, weight='regular'):
    """The bundle's markup for one variant, serialized the way the BUILDER writes it.

    Two normalizations, both measured rather than guessed. The builder's export adds
    `width="20" height="20"` and expands `<path/>` to `<path></path>`; with those applied, the
    pack's markup is byte-identical to the export's for all 12 distinct icons in the tracked and
    raw corpus. The baked `20` is inert — real exports carry it unchanged beside elements whose
    `props.icon.size` is 12, 13, 15, 22, 24 and 30 — so it is a serialization detail, not a size.
    Emitting the builder's form rather than the pack's keeps an authored entry indistinguishable
    from a saved one, which is what stops a later `diff-config.py` reporting churn.
    """
    raw = _load(ICON_PACK)['icons'].get(f'{name}::{weight}')
    if raw is None:
        return None
    raw = raw.replace(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">',
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" '
        'viewBox="0 0 256 256">')
    out = []
    while True:
        start = raw.find('<path')
        if start == -1:
            out.append(raw)
            break
        end = raw.find('>', start)
        tag = raw[start:end + 1]
        out.append(raw[:start])
        if tag.endswith('/>'):
            out.append(tag[:-2].rstrip() + '></path>')
        else:
            out.append(tag)
        raw = raw[end + 1:]
    return ''.join(out)


def icon_meta(name, weight='regular'):
    """One publishable `_meta.icons` entry: `{name, weight, raw}` — the shape all 41 corpus
    entries use, and the only shape `verify-config.py` accepts.

    Raises on a name or weight the bundle lacks, with suggestions. Unrepresentable beats
    detectable: a blank where an icon should be is invisible to every gate this skill can run,
    so the wrong name must not survive authoring.
    """
    if weight not in WEIGHTS:
        raise ValueError(
            f'icon weight {weight!r} is not published; the builder resolves {", ".join(WEIGHTS)}')
    raw = icon_raw(name, weight)
    if raw is None:
        hint = ', '.join(suggest(name)) or 'nothing close'
        other = [w for w in WEIGHTS if has_phosphor(name, w)]
        if other:
            raise ValueError(
                f'{name!r} has no {weight!r} weight in {pack_version()}; it ships as '
                f'{", ".join(other)}')
        raise ValueError(
            f'{name!r} is not a Phosphor icon in {pack_version()}, so the renderer resolves '
            f'nothing and the element draws BLANK — no gate will tell you. Did you mean: {hint}?')
    return {'name': name, 'weight': weight, 'raw': raw}


def custom_names():
    """The non-Phosphor glyphs the Builder itself publishes — the five loader spinners."""
    return sorted(_load(CUSTOM_ICONS)['icons'])


def custom_icon_meta(name):
    """The `_meta.icons` entry for one Builder-published custom icon, e.g. `spinner1`.

    `spinner()` refuses a phosphor icon (the publish gate answers 422, *Spinner element only
    supports custom icons*) and needs a declared entry with real markup — and the component
    catalog names `spinner1` in its loader templates while carrying no `_meta.icons` anywhere,
    so until now there was nowhere to get that markup from. Weight is always `regular`: that is
    the weight the Builder publishes them under.
    """
    raw = _load(CUSTOM_ICONS)['icons'].get(name)
    if raw is None:
        raise ValueError(
            f'{name!r} is not a Builder custom icon; the published set is '
            f'{", ".join(custom_names())}')
    return {'name': name, 'weight': _load(CUSTOM_ICONS)['weight'], 'raw': raw}


# ---------------------------------------- cli ----------------------------------------

def _main(argv):
    if not argv:
        print(__doc__.strip().split('\n\n')[-2], file=sys.stderr)
        return 2
    if argv[0] == '--search':
        needle = ' '.join(argv[1:]).lower()
        if not needle:
            print('--search needs something to search for', file=sys.stderr)
            return 2
        # The custom names join the pool: an agent searching "spinner" is usually after
        # `spinner1`, and leaving them out sends it to `Spinner`, a static glyph that does not
        # rotate — the substitution `spinner()` exists to refuse.
        hits = [n for n in phosphor_names() + custom_names() if needle in n.lower()]
        print('\n'.join(hits) if hits else f'no icon matches {needle!r}')
        return 0 if hits else 1
    try:
        if argv[0] in _load(CUSTOM_ICONS)['icons']:
            entry = custom_icon_meta(argv[0])
        else:
            entry = icon_meta(argv[0], argv[1] if len(argv) > 1 else 'regular')
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
