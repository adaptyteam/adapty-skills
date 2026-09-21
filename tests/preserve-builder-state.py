#!/usr/bin/env python3
"""Carry builder-owned state from the live config into a regenerated one.

`config update` replaces the WHOLE config. So a script that rebuilds a config from source
and emits `_meta.screens: {}` will silently destroy the product attachments someone made in
the Flow Builder — the `flowProductId` values cannot be re-derived, and without them the
publish transform fails with a 422.

This is the sharp edge of "`_meta.screens` is builder-owned": it does not just mean *do not
author it*, it means **do not omit it either**. Anything the builder writes and you cannot
compute has to be carried forward on every regeneration.

    tests/preserve-builder-state.py <live-or-envelope.json> <regenerated.json> [--out FILE]

Merges, per screen id that still exists in the regenerated config:
    _meta.screens[<sid>]        product declarations incl. flowProductId, webPaywallURL
    screens[].products          the screen-owned Product + Offer registry (schemaVersion 12)
    _meta.fonts                 uploaded font records, if the regenerated config has none

The registry is carried for the same reason as the declarations it feeds: an entry can exist
with no usage anywhere on the screen, so nothing that walks the elements rebuilds it. An empty
`products` in the regenerated config is treated as absent and overwritten — `[]` is authoritative
to the builder and would declare the screen product-free, which is the loss this guards against.

Reports exactly what it carried and what it dropped, because a screen that no longer exists
legitimately loses its declarations and that should be visible rather than silent.
"""
import argparse, json, sys


def load(p):
    d = json.load(open(p))
    return d['config'] if isinstance(d.get('config'), dict) else d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('live'); ap.add_argument('new'); ap.add_argument('--out')
    a = ap.parse_args()
    live, new = load(a.live), load(a.new)

    live_meta = (live.get('_meta') or {}).get('screens') or {}
    new_meta = (new.setdefault('_meta', {}).setdefault('screens', {}))
    keep = {s['id'] for s in new.get('screens', [])}

    carried, dropped, kept_existing = [], [], []
    for sid, block in live_meta.items():
        if sid not in keep:
            dropped.append(sid); continue
        if new_meta.get(sid):
            kept_existing.append(sid); continue
        new_meta[sid] = block
        n = len((block or {}).get('products') or [])
        carried.append(f'{sid} ({n} product declaration{"s" if n != 1 else ""})')

    live_screens = {s['id']: s for s in live.get('screens') or [] if isinstance(s, dict)}
    reg_carried, reg_kept = [], []
    for s in new.get('screens') or []:
        live_reg = (live_screens.get(s.get('id')) or {}).get('products')
        if not live_reg:
            continue
        if s.get('products'):
            reg_kept.append(s['id']); continue
        s['products'] = live_reg
        reg_carried.append(f'{s["id"]} ({len(live_reg)} registry entr{"ies" if len(live_reg) != 1 else "y"})')

    fonts_note = ''
    live_fonts = (live.get('_meta') or {}).get('fonts') or []
    if live_fonts and not (new['_meta'].get('fonts') or []):
        new['_meta']['fonts'] = live_fonts
        fonts_note = f' | carried {len(live_fonts)} font record(s)'

    print('carried forward :', ', '.join(carried) or 'nothing' , fonts_note)
    if reg_carried:
        print('registry carried:', ', '.join(reg_carried))
    if kept_existing:
        print('left as authored:', ', '.join(kept_existing))
    if reg_kept:
        print('registry left as authored:', ', '.join(reg_kept))
    if dropped:
        print('DROPPED (screen no longer exists):', ', '.join(dropped))
    out = a.out or a.new
    json.dump(new, open(out, 'w'), indent=2, ensure_ascii=False)
    print('wrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
