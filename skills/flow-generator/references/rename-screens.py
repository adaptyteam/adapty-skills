#!/usr/bin/env python3
"""Rename screen ids across a flow config, rewriting every reference site.

Why this exists. A screen id is the ONE analytics-visible id in a flow that cannot be set in
the Flow Builder. It rides out to the app as `instanceId` on both `flow_screen_showed` and
`flow_user_input` (`generate-handlers.ts:489,716,824`, unified-builder-transformer@dcf2df4),
so a customer forwarding events to Amplitude or Mixpanel reads `scr_oAPBHPa7 -> scr_03lOfpai`
instead of `welcome -> signup`, and has to keep an id->name mapping by hand. Everything else
in that payload is already author-supplied and already settable in the builder: an input and
an option report `props.customId`, a group reports `selectableGroups[].id`. Element `el_XXXX`
map keys never leave the config at all -- do not rename those to "tidy up", because they DO
compile into the generated runtime script and a bad one is a black screen on device
(`verify-config.py` owns that rule).

THREE reference sites, and the set is closed rather than guessed:

    screens[].id                  the declaration
    _meta.screens.<id>            the per-screen product declaration, keyed by screen id
    navigate.payload.screen       every jump, INCLUDING ones nested inside a `conditional`
                                  action's `cases`/`default` branches

`IActionNavigate.payload.screen` is the only string-typed screen reference in the published
schema; the entry screen is `screens[0]` by position, not a named pointer, so there is no
start-screen field to keep in step. Measured over all 12 tracked and raw fixtures: those three
sites account for every occurrence of a screen id.

Rewriting is PATH-KEYED, never value-keyed -- the same trap `snippet.py` documents. A screen
called `tabs` and an element whose `type` is the string `tabs` are indistinguishable to a
value-keyed rewriter, which would rename the element type and silently kill the tab bar.

WHAT THIS DOES NOT DO. It will not touch a live flow; it reads a file and writes a file. Run
it on the config you fetched in phase 2, then take the result through the normal gates and the
phase-5 approval ask like any other change.

BEFORE YOU RENAME A LIVE FLOW, say this to the user: renaming breaks analytics continuity.
Historical events stay under the old id in Adapty's own flow metrics AND in whatever external
tool they forward to, so a funnel spanning the rename splits in two. It is a rename-at-creation
feature far more than a rename-anytime one.

Screen ids are NOT restricted to `[A-Za-z0-9_]`. Hyphens are fine and bare UUIDs are common --
4 of 36 screen ids in the corpus are UUIDs, each the entry screen of a published flow -- because
a screen id is not emitted as an identifier in the generated script the way an element id is.

    usage: rename-screens.py CONFIG old=new [old=new ...]      print the result to stdout
           rename-screens.py CONFIG --map renames.json         same, renames from a JSON object
           rename-screens.py CONFIG old=new -o OUT.json        write the result to a file

    exit 0  renamed, report on stderr
         1  refused -- an unknown source id, a collision, or a malformed target
         2  the config could not be read
"""
import json
import os
import sys


def load(path):
    """Accept the `config get` envelope or a bare config, like every other script here."""
    d = json.load(open(path, encoding='utf-8'))
    return d['config'] if isinstance(d, dict) and 'config' in d and 'screens' in d.get(
        'config', {}) else d


def parse_renames(args):
    out = {}
    for a in args:
        if '=' not in a:
            raise ValueError(f'expected old=new, got {a!r}')
        old, new = a.split('=', 1)
        out[old.strip()] = new.strip()
    return out


def plan(config, renames):
    """Refuse anything ambiguous BEFORE touching the document. Returns a list of problems."""
    existing = [s.get('id') for s in config.get('screens') or []]
    problems = []

    for old, new in renames.items():
        if old not in existing:
            problems.append(f'no screen with id {old!r} — this config has: '
                            f'{", ".join(str(x) for x in existing)}')
        if not new or not new.strip():
            problems.append(f'{old!r} -> empty id')

    # A target that is already taken, and was not itself renamed away in the same pass. The
    # exemption is what makes a swap (a=b, b=a) and a shift (a=b, b=c) expressible; without it
    # every chained rename would look like a collision.
    for old, new in renames.items():
        if new in existing and new != old and new not in renames:
            problems.append(f'{old!r} -> {new!r} collides with a screen that already exists')

    # Two sources landing on one target silently deletes a screen from `_meta.screens` and
    # merges two nodes of the navigation graph.
    targets = list(renames.values())
    for t in sorted({t for t in targets if targets.count(t) > 1}):
        srcs = sorted(o for o, n in renames.items() if n == t)
        problems.append(f'{", ".join(srcs)} all rename to {t!r}')

    return problems


def apply(config, renames):
    """Rewrite the three sites. Returns a per-site count for the disclosure the caller owes."""
    hits = {'screens[].id': 0, '_meta.screens': 0, 'navigate.payload.screen': 0}

    for s in config.get('screens') or []:
        if s.get('id') in renames:
            s['id'] = renames[s['id']]
            hits['screens[].id'] += 1

    meta = config.get('_meta')
    if isinstance(meta, dict) and isinstance(meta.get('screens'), dict):
        rebuilt = {}
        for k, v in meta['screens'].items():
            if k in renames:
                hits['_meta.screens'] += 1
                rebuilt[renames[k]] = v
            else:
                rebuilt[k] = v
        meta['screens'] = rebuilt

    def walk(o):
        # Keyed on the FIELD, never on the value: `payload.screen` under a `navigate` action.
        # Recursing the whole document is what covers a `navigate` buried in a `conditional`'s
        # `cases` (a two-element [predicate, {type: const, value: [...actions]}] list) and its
        # `default` branch, without hand-walking that shape -- which drifted once already in
        # this repo's own history.
        if isinstance(o, dict):
            if o.get('type') == 'navigate' and isinstance(o.get('payload'), dict):
                tgt = o['payload'].get('screen')
                if isinstance(tgt, str) and tgt in renames:
                    o['payload']['screen'] = renames[tgt]
                    hits['navigate.payload.screen'] += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(config)
    return hits


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print('usage: rename-screens.py CONFIG old=new [old=new ...] [-o OUT.json]',
              file=sys.stderr)
        return 2

    path, rest, out = argv[0], argv[1:], None
    if '-o' in rest:
        i = rest.index('-o')
        if i + 1 >= len(rest):
            print('ERROR: -o needs a path', file=sys.stderr)
            return 2
        out = rest[i + 1]
        rest = rest[:i] + rest[i + 2:]

    try:
        config = load(path)
        if '--map' in rest:
            i = rest.index('--map')
            renames = json.load(open(rest[i + 1], encoding='utf-8'))
            rest = rest[:i] + rest[i + 2:]
            renames.update(parse_renames(rest))
        else:
            renames = parse_renames(rest)
    except (OSError, ValueError, KeyError, IndexError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2

    if not renames:
        print('ERROR: no renames given', file=sys.stderr)
        return 2

    problems = plan(config, renames)
    if problems:
        print('REFUSED — nothing was changed:', file=sys.stderr)
        for p in problems:
            print(f'  - {p}', file=sys.stderr)
        return 1

    hits = apply(config, renames)

    for old, new in sorted(renames.items()):
        print(f'  {old} -> {new}', file=sys.stderr)
    print(f'  sites rewritten: ' + ', '.join(f'{k} {v}' for k, v in hits.items()),
          file=sys.stderr)
    # A screen nothing jumps to is legal (it may be `screens[0]`), so this is a prompt to look
    # rather than a refusal -- but a rename that rewrites no navigation on a MIDDLE screen
    # usually means the jump lives somewhere this did not reach.
    if hits['navigate.payload.screen'] == 0:
        print('  note: no navigate target pointed at any renamed screen. Expected only if the '
              'renamed screens are entry screens; otherwise check for a jump this missed.',
              file=sys.stderr)
    print('  disclose to the user: analytics continuity breaks — historical events stay under '
          'the old id in Adapty flow metrics and in their own analytics.', file=sys.stderr)

    text = json.dumps(config, indent=1, ensure_ascii=False)
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
        print(f'  written: {out}', file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
