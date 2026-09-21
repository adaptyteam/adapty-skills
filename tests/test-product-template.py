#!/usr/bin/env python3
"""Contract for the `prod-vertical-list` entry in `references/component-catalog.json`.

Repo-only. Reads the shipped catalog and exercises `flowkit.from_catalog` against it.

Why this file exists. Plan cards are the commonest thing on a paywall and the catalog shipped
them as a stub: `agent_allowed: false`, an empty template, and `patterns.md` telling agents to
respect the flag and assemble the cards by hand. Hand assembly is where the dead selected state
comes from — the selected LOOK baked into whichever card starts selected, so tapping the other
one changes nothing, and every gate passes because the document is well formed.

The rows below are the properties that make the template worth preferring over a skeleton. Each
one is a defect the hand-built version actually shipped:

    a native `product` element         not a stack that looks like a card
    one shared product group           not three cards that do not know about each other
    `states` + `propsByState.selected` not a baked-in selected look
    exactly one `default: true`        not none (nothing selected) and not three
    an EMPTY `product.id`              not an invented or borrowed product UUID
    no price, discount or trial copy   not a sample price that ships as a fabricated claim

Slot paths are walked rather than eyeballed: a slot that does not resolve is a slot an agent
fills into the wrong node, silently.

Usage: python3 tests/test-product-template.py    # 0 all pass, 1 a case regressed
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REFS = os.path.join(ROOT, 'skills', 'flow-generator', 'references')
sys.dont_write_bytecode = True
sys.path.insert(0, REFS)

import flowkit as fk  # noqa: E402

FAILURES = []


def check(name, cond, detail=''):
    if cond:
        print(f'  ok    {name}')
    else:
        print(f'  FAIL  {name}' + (f'   {detail}' if detail else ''))
        FAILURES.append(name)


def at(node, path):
    """Resolve a slot path, the way an agent filling the template by hand would."""
    for step in path:
        node = node[step]
    return node


def cards_of(template):
    return [c for c in template['children'] if c.get('type') == 'product']


# Deliberately loose: any of these in a shipped template is a claim nobody verified.
MONEY = re.compile(r'\$\s?\d|\d+\s?%|\bfree trial\b|\bsave\b|\bper (?:month|year|week)\b'
                   r'|/\s?(?:mo|month|yr|year|wk|week)\b', re.I)


def main():
    catalog = json.load(open(os.path.join(REFS, 'component-catalog.json')))
    entry = next((c for c in catalog['components'] if c['id'] == 'prod-vertical-list'), None)
    if entry is None:
        print('prod-vertical-list is missing from the catalog')
        return 1

    template = entry['template']
    cards = cards_of(template)

    check('the entry is agent-insertable', entry.get('agent_allowed') is True)
    check('it declares a product-typed group',
          entry.get('groups') == [{'id': 'products', 'type': 'product'}], entry.get('groups'))
    check('every child of the wrapper is a native product element',
          len(cards) == len(template['children']) and len(cards) >= 2,
          [c.get('type') for c in template['children']])

    group_id = entry['groups'][0]['id']
    check('every card binds the declared group',
          all(c['props'].get('groupId') == group_id for c in cards))
    check('exactly one card is selected by default',
          sum(c['props'].get('default') is True for c in cards) == 1,
          [c['props'].get('default') for c in cards])

    check('every card declares the system selected state',
          all({'id': 'selected', 'type': 'system'} in (c.get('states') or []) for c in cards))
    check('every card carries a selected APPEARANCE, so tapping changes something',
          all((c.get('propsByState') or {}).get('selected') for c in cards))
    # `.get` throughout: a mutation that removes propsByState must FAIL this row, not end the
    # run on a KeyError and leave every row below it unreported.
    check('the selected override repeats the whole prop it touches, never a delta',
          all(isinstance(v, dict) and v for c in cards
              for v in ((c.get('propsByState') or {}).get('selected') or {'x': {}}).values()))

    check('no card carries a product id — the agent or the user chooses one',
          all(c['props'].get('product') == {'id': ''} for c in cards),
          [c['props'].get('product') for c in cards])

    money = MONEY.findall(json.dumps(template))
    check('the template states no price, discount or trial', not money, money)

    # Slots. `items` repeats item 0, so the per-item paths are resolved against every card.
    slots = entry['slots']['items']
    check('the items slot addresses the wrapper children',
          at(template, slots['path']) is template['children'])
    for name, slot in slots['item_slots'].items():
        ok, seen = True, []
        for card in cards:
            try:
                seen.append(at(card, slot['path']))
            except (KeyError, IndexError, TypeError):
                ok = False
        check(f'slot {name!r} resolves on every card', ok and len(seen) == len(cards), seen)
    check('the product_id slot points at the binding itself',
          slots['item_slots']['product_id']['path'] == ['props', 'product', 'id'])

    # from_catalog is the only route from a template into an assembled screen.
    nodes = fk.from_catalog(json.loads(json.dumps(template)), group_id='plans')
    for i, card in enumerate(nodes[0]['_children']):
        card['props']['product'] = {'id': f'prod-{i}'}
    # A guard inside screen() raising here is a FAILING row, not a reason to end the run and
    # leave everything below it unreported.
    try:
        screen = fk.screen('scr_pay', nodes, scrollable=True,
                           selectable_groups=[{'id': 'plans', 'type': 'product'}])
    except Exception as exc:                                    # noqa: BLE001
        screen = {'products': [f'screen() refused: {exc}']}
    check('a screen built from it registers every card as a product binding',
          [p['id'] for p in screen['products'] if isinstance(p, dict)]
          == [f'prod-{i}' for i in range(len(cards))], screen.get('products'))

    # The catalog is the path the skill tells agents to prefer, so a template naming a theme
    # token the other agent-allowed templates do not use would resolve to nothing on insertion.
    used = set(re.findall(r'"colorId":\s*"([^"]+)"', json.dumps(template)))
    elsewhere = set(re.findall(r'"colorId":\s*"([^"]+)"', json.dumps(
        [c['template'] for c in catalog['components']
         if c['id'] != 'prod-vertical-list' and c.get('agent_allowed')])))
    check('every theme token it names is one the rest of the catalog already uses',
          used <= elsewhere, sorted(used - elsewhere))

    presets = set(re.findall(r'"preset":\s*"([^"]+)"', json.dumps(template)))
    presets_elsewhere = set(re.findall(r'"preset":\s*"([^"]+)"', json.dumps(
        [c['template'] for c in catalog['components']
         if c['id'] != 'prod-vertical-list' and c.get('agent_allowed')])))
    check('every typography preset it names is one the rest of the catalog already uses',
          presets <= presets_elsewhere, sorted(presets - presets_elsewhere))

    # The template ships unbound cards on purpose, so the checker has to say something useful
    # about that state. An empty id and a chosen-but-undeclared product are different
    # situations, and `predeclare()` — the advice for the second — does not apply to the first.
    # They wore one message until this template made the empty case the common one.
    verify = os.path.join(REFS, 'verify-config.py')

    def findings(product_id, declared=None):
        doc = {'schemaVersion': 12, 'defaultLocale': 'en',
               'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}],
               'variables': [], 'components': {},
               'theme': {'colors': [], 'typography': []},
               '_meta': {'icons': [], 'fonts': [],
                         'screens': {'scr_a': {'products': declared}} if declared else {}},
               'screens': [{'id': 'scr_a', 'props': {},
                            'selectableGroups': [{'id': 'plans', 'type': 'product'}],
                            'elements': {
                                'map': {'el_c': {'id': 'el_c', 'type': 'product', 'states': [
                                    {'id': 'selected', 'type': 'system'}],
                                    'propsByState': {'selected': {'border': {'width': 2}}},
                                    'props': {'groupId': 'plans', 'default': True,
                                              'product': {'id': product_id}}}},
                                'hierarchy': {'id': 'root', 'children': [{'id': 'el_c'}]}}}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'c.json')
            json.dump(doc, open(path, 'w'))
            out = subprocess.run([sys.executable, verify, path], capture_output=True, text=True)
        if 'CHECKER ERROR' in out.stdout:
            return f'CHECKER ERROR: {out.stdout}'
        return out.stdout

    empty = findings('')
    check('an unbound card is reported as a card with no product chosen',
          'no product chosen' in empty and 'predeclare' not in empty, empty.strip()[:110])
    undeclared = findings('8fb58c50-7c05-42f9-a8e3-8d0fde19505a')
    check('and a chosen-but-undeclared product still gets the predeclare advice',
          'predeclare' in undeclared and 'no product chosen' not in undeclared,
          undeclared.strip()[:110])

    print()
    if FAILURES:
        print(f'{len(FAILURES)} failure(s): ' + ', '.join(FAILURES))
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
