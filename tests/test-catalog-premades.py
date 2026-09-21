#!/usr/bin/env python3
"""Contract for `references/component-catalog.json` as a whole, and the deviations it carries.

Repo-only. Reads the shipped catalog and exercises `flowkit.from_catalog` against every entry.

The catalog is the builder's own premade set, extracted by running the dashboard's
`elements-menu/*.ts` through its real `Element.create` factory. **Four values were deliberately
changed on the way in**, and this file is where they are pinned. There is no generator in this
repo, so a refresh from source is a manual act — and without these assertions it silently
reverts all four. Each `DEVIATION` row below is a red test with its reason attached, which is the
only form that survives someone re-running the extraction.

The rest of the file is the contract every entry has to meet to be worth preferring over a
hand-built skeleton: the group it needs is declared, its slots address real nodes, and it states
no offer nobody verified.

Usage: python3 tests/test-catalog-premades.py    # 0 all pass, 1 a case regressed
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REFS = os.path.join(ROOT, 'skills', 'flow-generator', 'references')
sys.dont_write_bytecode = True
sys.path.insert(0, REFS)

import flowkit as fk  # noqa: E402

CATALOG = json.load(open(os.path.join(REFS, 'component-catalog.json')))
BY_ID = {c['id']: c for c in CATALOG['components']}
FAILURES = []


def check(name, cond, detail=''):
    if cond:
        print(f'  ok    {name}')
    else:
        print(f'  FAIL  {name}' + (f'   {detail}' if detail else ''))
        FAILURES.append(name)


def walk(node):
    yield node
    for child in node.get('children') or []:
        yield from walk(child)


def at(node, path):
    for step in path:
        node = node[step]
    return node


# An offer claim is a price, a discount or a duration. A template that states one ships it into
# every flow built from it, and nothing downstream can tell an invented number from a real one.
CLAIM = re.compile(r'\$\s?\d|\d+\s?%|\bsave\b|\bper (?:month|year|week)\b'
                   r'|/\s?(?:mo|month|yr|year|wk|week)\b|\b\d+\s*days?\b', re.I)


def main():
    print('DEVIATIONS from the builder source — each is deliberate, and reverting it is a defect:')

    # 1. The palette types the trial switch `single_choice`, which a device cannot switch back
    #    OFF. Device-confirmed on a published flow: as `toggle` it switches both ways.
    check('trial-toggle declares a `toggle` group, not `single_choice`',
          [g['type'] for g in BY_ID['trial-toggle']['groups']] == ['toggle'],
          BY_ID['trial-toggle'].get('groups'))

    # 2. `opacity` is 0-100 in this format (real exports carry 0/20/26/50/63/100). The carousel
    #    premade ships `opacity: 1`, which is 1% — an invisible fill, not a design.
    ones = [c['id'] for c in CATALOG['components']
            for n in walk(c['template'])
            for v in [n.get('props') or {}]
            if json.dumps(v).find('"opacity": 1,') >= 0 or json.dumps(v).find('"opacity": 1}') >= 0]
    check('no template carries `opacity: 1` (1% on a 0-100 scale)', not ones, sorted(set(ones)))

    # 3. Once that fill is opaque it must follow the appearance, or dark mode is gray-700 text on
    #    a white card. Every genuine export binds a surface to a token, never to a literal hex.
    slide_fills = [layer.get('color') for slide in BY_ID['carousel']['template']['children']
                   for layer in (slide.get('props') or {}).get('fill') or []]
    check('the carousel slide fill is a theme token, not a literal hex',
          slide_fills and all(c.get('type') == 'color-style' for c in slide_fills), slide_fills)

    # 4. Every product premade ships sample prices, savings and trial durations.
    claims = {c['id']: sorted(set(CLAIM.findall(json.dumps(c['template']))))
              for c in CATALOG['components']
              if CLAIM.search(json.dumps(c['template']))}
    check('no product template states a price, discount or duration',
          not any(k.startswith('prod-') for k in claims),
          {k: v for k, v in claims.items() if k.startswith('prod-')})
    check('and no other template does either', not claims, claims)

    print()
    print('Every entry:')
    no_slots, unresolved, undeclared = [], [], []
    for c in CATALOG['components']:
        if c.get('agent_allowed') is not True:
            continue
        # a slot that does not resolve is a slot an agent fills into the wrong node, silently
        for name, slot in (c.get('slots') or {}).items():
            try:
                if slot['kind'] == 'items':
                    unit = at(c['template'], slot['path'])[slot['item_index']]
                    for inner in slot['item_slots'].values():
                        at(unit, inner['path'])
                else:
                    at(c['template'], slot['path'])
            except Exception:                                   # noqa: BLE001
                unresolved.append(f"{c['id']}.{name}")
        # a template whose nodes carry a groupId must say which group, or the insert is dangling
        used = {(n.get('props') or {}).get('groupId') for n in walk(c['template'])} - {None}
        if used and not c.get('groups'):
            undeclared.append(c['id'])
        if used and c.get('groups') and used != {g['id'] for g in c['groups']}:
            undeclared.append(f"{c['id']} (declares {[g['id'] for g in c['groups']]}, uses {used})")
        if not c.get('slots'):
            no_slots.append(c['id'])

    check('every slot path resolves', not unresolved, unresolved)
    check('every template using a groupId declares that group', not undeclared, undeclared)
    print(f'  note  {len(no_slots)} agent-allowed entries carry no slots '
          f'(legal — a spinner has nothing to fill)')

    print()
    print('Product entries — the shape a hand-built plan card keeps getting wrong:')
    for c in CATALOG['components']:
        if not c['id'].startswith('prod-'):
            continue
        cards = [n for n in walk(c['template']) if n.get('type') == 'product']
        ok_default = sum(bool((n.get('props') or {}).get('default')) for n in cards) == 1
        ok_unbound = all((n.get('props') or {}).get('product') == {'id': ''} for n in cards)
        ok_state = all(any(s.get('id') == 'selected' for s in n.get('states') or [])
                       and (n.get('propsByState') or {}).get('selected') for n in cards)
        check(f"{c['id']}: {len(cards)} cards, one default, unbound, selected appearance",
              cards and ok_default and ok_unbound and ok_state,
              f'default={ok_default} unbound={ok_unbound} state={ok_state}')

    print()
    print('from_catalog over the whole catalog:')
    broke = []
    for c in CATALOG['components']:
        if c.get('agent_allowed') is not True:
            continue
        try:
            nodes = fk.from_catalog(c)
            assert nodes and all(n.get('id') for n in nodes)
        except Exception as exc:                                # noqa: BLE001
            broke.append(f"{c['id']}: {type(exc).__name__} {exc}")
    check('every agent-allowed entry converts to authoring nodes', not broke, broke[:4])

    # the repeat rule: every copy of a unit that starts selected would otherwise be the default
    plans = fk.from_catalog(BY_ID['prod-vertical-list'], group_id='g',
                            items=[{'title': f'P{i}', 'product_id': f'u{i}'} for i in range(3)])[0]
    check('items= makes exactly one repeat the default',
          [c['props']['default'] for c in plans['_children']] == [True, False, False],
          [c['props']['default'] for c in plans['_children']])
    check('items= writes every value through its declared slot',
          [c['props']['product']['id'] for c in plans['_children']] == ['u0', 'u1', 'u2'])

    # fills= must refuse what it cannot write, rather than silently doing nothing
    try:
        fk.from_catalog(BY_ID['btn-base'], fills={'nope': 'x'})
        check('fills= refuses an unknown slot', False)
    except KeyError as exc:
        check('fills= refuses an unknown slot', 'nope' in str(exc))
    try:
        fk.from_catalog(BY_ID['btn-base']['template'], fills={'label': 'x'})
        check('fills= refuses a bare template, which carries no slots', False)
    except TypeError as exc:
        check('fills= refuses a bare template, which carries no slots', 'entry' in str(exc))

    print()
    if FAILURES:
        print(f'{len(FAILURES)} failure(s): ' + ', '.join(FAILURES))
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
