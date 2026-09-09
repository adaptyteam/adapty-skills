#!/usr/bin/env python3
"""Calibration for `references/rename-screens.py` and the orphaned-`_meta.screens` check.

Repo-only. Runs both shipped scripts as subprocesses -- never imports them, so nothing writes
a `__pycache__` into `references/`.

Why this file exists. A screen id is the one analytics-visible id in a flow that the Flow
Builder cannot set: it reaches the app as `instanceId` on both `flow_screen_showed` and
`flow_user_input` (`generate-handlers.ts:489,716,824`,
unified-builder-transformer@dcf2df4). Renaming it by hand is a three-site edit, and the site
everyone forgets is `_meta.screens`, whose key IS the screen id. Measured against production
(adapty 0.8.2, a real flow in app_finance): rename the paywall screen, leave the key, and
`flows config validate` refuses the flow --

    _meta.screens["paywall_final"].products is missing flowProductId for product "<uuid>"

-- while `verify-config.py` reported OK, because a product under a stale key is indistinguishable
from the ordinary bound-but-not-yet-declared state of a freshly authored flow. So the tool
exists to do all three sites at once, and the check exists to catch the hand edit that did not.

    ORACLE for the tool: after a rename, `verify-config.py` reports nothing it did not report
    before. The rename introduces no breakage -- it is not required to fix pre-existing findings.
    That is not circular: `verify-config.py` predates this tool and already owns the invariants
    a bad rename breaks (dangling navigate targets, unreachable screens, orphaned meta keys).

Usage: python3 tests/test-rename-screens.py     # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'skills', 'flow-generator', 'references')
RENAME = os.path.join(REFS, 'rename-screens.py')
VERIFY = os.path.join(REFS, 'verify-config.py')
CORPUS = os.path.join(ROOT, 'tests', 'fixtures')
RAW = os.path.join(ROOT, 'tests', 'fixtures-raw')

ORPHAN = 'names no screen in this config'

fails = []


def ok(name):
    print(f'  ok    {name}')


def bad(name, msg):
    fails.append(f'{name}: {msg}')
    print(f'  FAIL  {name}')


def rename(doc, *args):
    """Run the tool. Returns (exit_code, parsed_config_or_None, stderr)."""
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json')
        json.dump(doc, open(p, 'w'))
        r = subprocess.run([sys.executable, RENAME, p, *args],
                           capture_output=True, text=True)
    if 'Traceback' in r.stderr:
        raise AssertionError(f'rename-screens.py crashed:\n{r.stderr}')
    out = None
    if r.returncode == 0 and r.stdout.strip():
        out = json.loads(r.stdout)
    return r.returncode, out, r.stderr


def findings(doc):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json')
        json.dump(doc, open(p, 'w'))
        r = subprocess.run([sys.executable, VERIFY, p], capture_output=True, text=True)
    if 'Traceback' in r.stderr:
        raise AssertionError(f'verify-config.py crashed:\n{r.stderr}')
    # Exit 2 is the CHECKER ERROR guard and it prints to STDOUT, so without this a malformed
    # case reads as "no findings" and every comparison below passes for the wrong reason.
    if r.returncode == 2 or 'CHECKER ERROR' in r.stdout:
        raise AssertionError(f'verify-config.py could not read the document:\n{r.stdout}')
    return sorted(l.strip() for l in r.stdout.splitlines()
                  if 'ERROR:' in l or 'warning:' in l)


def findings_modulo(doc, renames):
    """Findings with the renamed ids mapped back, so the oracle compares like with like.

    Many messages embed the screen id (`<screen>/<element>: text is 1.08:1 ...`, `product ...
    on screen <screen> ...`), so a raw string diff reports every pre-existing finding on a
    renamed screen as NEW. Three real exports failed this way before the normalisation --
    tabs-paywall's three undeclared `const` purchases, timeline-anchored's six dark-mode
    contrast warnings, vpn-timer-draft's three stale sizing values -- none of them caused by
    the rename. This does not blunt the oracle: a finding the rename actually introduces has
    no counterpart in the before-set whatever id it names.
    """
    out = []
    for f in findings(doc):
        for old, new in renames.items():
            f = f.replace(new, old)
        out.append(f)
    return sorted(out)


# ------------------------------------------------------------------ a three-screen flow
def flow():
    """Three screens in a chain, the last carrying a product declaration, plus a `navigate`
    buried inside a `conditional` action -- the shape a hand-written rewriter misses."""
    def screen(sid, nav=None, product=None, conditional=None):
        acts = []
        if nav:
            acts.append({'id': 'act_' + sid, 'type': 'navigate',
                         'payload': {'type': 'screen', 'screen': nav}})
        if conditional:
            acts.append({'id': 'act_c_' + sid, 'type': 'conditional', 'payload': {
                'cases': [[{'type': 'eq', 'left': {'type': 'const', 'value': 1},
                            'right': {'type': 'const', 'value': 1}},
                           {'type': 'const', 'value': [
                               {'id': 'act_yes', 'type': 'navigate',
                                'payload': {'type': 'screen', 'screen': conditional[0]}}]}]],
                'default': {'type': 'const', 'value': [
                    {'id': 'act_no', 'type': 'navigate',
                     'payload': {'type': 'screen', 'screen': conditional[1]}}]}}})
        el = {'id': 'el_' + sid, 'type': 'stack', 'states': [],
              'props': {'width': {'type': 'fill'}, 'height': {'type': 'hug'},
                        'position': {'type': 'relative'},
                        'layout': {'direction': 'vertical',
                                   'distribution': {'type': 'gap', 'gap': 0}}}}
        if acts:
            el['interactions'] = [{'id': 'int_' + sid, 'trigger': 'tap', 'actions': acts}]
        emap = {el['id']: el}
        kids = [{'id': el['id']}]
        if product:
            pel = {'id': 'el_p_' + sid, 'type': 'product', 'states': [],
                   'props': {'width': {'type': 'fill'}, 'height': {'type': 'hug'},
                             'position': {'type': 'relative'}, 'groupId': 'plans',
                             'default': True, 'product': {'id': product},
                             'layout': {'direction': 'vertical',
                                        'distribution': {'type': 'gap', 'gap': 0}}}}
            emap[pel['id']] = pel
            kids.append({'id': pel['id']})
        return {'id': sid, 'props': {}, 'elements': {
            'map': emap, 'hierarchy': {'id': 'root', 'children': kids}},
            'selectableGroups': ([{'id': 'plans', 'type': 'product'}] if product else [])}

    pid = '11111111-2222-3333-4444-555555555555'
    return {'schemaVersion': 10, 'defaultLocale': 'en',
            'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}],
            'theme': {'colors': [], 'typography': []},
            '_meta': {'screens': {'scr_pay': {'products': [
                {'id': pid, 'flowProductId': '99999999-8888-7777-6666-555555555555'}]}}},
            'screens': [screen('scr_one', nav='scr_two'),
                        screen('scr_two', conditional=('scr_pay', 'scr_one')),
                        screen('scr_pay', product=pid)]}


def ids(doc):
    return [s['id'] for s in doc['screens']]


def navs(doc):
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get('type') == 'navigate':
                found.append(o['payload']['screen'])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(doc)
    return sorted(found)


# ------------------------------------------------------------------ the three sites
print('rewrites every reference site:')

code, out, err = rename(flow(), 'scr_one=welcome')
if code != 0:
    bad('renames the declaration', f'exit {code}: {err}')
elif ids(out) != ['welcome', 'scr_two', 'scr_pay']:
    bad('renames the declaration', f'got {ids(out)}')
else:
    ok('renames the declaration (screens[].id)')

# The plain top-level jump.
code, out, _ = rename(flow(), 'scr_two=signup')
if out and navs(out) == sorted(['signup', 'scr_pay', 'scr_one']):
    ok('rewrites a top-level navigate target')
else:
    bad('rewrites a top-level navigate target', f'got {navs(out) if out else None}')

# The one a hand-written rewriter misses: a navigate nested in a `conditional`'s `cases`, whose
# case is a two-element [predicate, {type: const, value: [...actions]}] list, and in `default`.
code, out, _ = rename(flow(), 'scr_pay=paywall')
if out and 'paywall' in navs(out) and 'scr_pay' not in navs(out):
    ok('rewrites a navigate nested inside a conditional case')
else:
    bad('rewrites a navigate nested inside a conditional case', f'got {navs(out) if out else None}')

code, out, _ = rename(flow(), 'scr_one=welcome')
if out and 'welcome' in navs(out) and 'scr_one' not in navs(out):
    ok('rewrites a navigate inside a conditional default branch')
else:
    bad('rewrites a navigate inside a conditional default branch',
        f'got {navs(out) if out else None}')

# The site everyone forgets, and the one that makes a flow unpublishable.
code, out, _ = rename(flow(), 'scr_pay=paywall')
if out and list(out['_meta']['screens']) == ['paywall']:
    ok('moves the _meta.screens key with the screen')
else:
    bad('moves the _meta.screens key with the screen',
        f'got {list(out["_meta"]["screens"]) if out else None}')

# Renaming every screen at once must not lose a site or trip over its own output.
code, out, _ = rename(flow(), 'scr_one=welcome', 'scr_two=signup', 'scr_pay=paywall')
if out and ids(out) == ['welcome', 'signup', 'paywall'] and \
        navs(out) == sorted(['signup', 'paywall', 'welcome']) and \
        list(out['_meta']['screens']) == ['paywall']:
    ok('renames all three screens in one pass')
else:
    bad('renames all three screens in one pass', f'ids={ids(out) if out else None}')


# ------------------------------------------------------------------ path-keyed, not value-keyed
print('\nkeyed on the field, never on the value:')

# `snippet.py`'s documented trap, reproduced for screens: a screen whose id collides with a
# string that means something else in the document. A value-keyed rewriter renames the element
# TYPE here and silently kills the element.
# Rename the first screen to `stack`, the exact string three elements carry as their `type`.
# Quoting both sides of the replace keeps `"el_scr_one"` (a different quoted string) intact, so
# only the screen id and the navigate targets pointing at it move.
_d = json.loads(json.dumps(flow()).replace('"scr_one"', '"stack"'))
_types_before = sorted(e['type'] for s in _d['screens'] for e in s['elements']['map'].values())
code, out, _ = rename(_d, 'stack=welcome')
_types_after = sorted(e['type'] for s in out['screens']
                      for e in s['elements']['map'].values()) if out else None
if out and _types_after == _types_before and 'stack' in _types_after:
    ok('a screen id equal to an element type does not rewrite the type')
else:
    bad('a screen id equal to an element type does not rewrite the type',
        f'element types changed: {_types_before} -> {_types_after}')


# ------------------------------------------------------------------ refusals
print('\nrefuses rather than half-renaming:')

for name, args, why in [
    ('an unknown source id', ('scr_nope=welcome',), 'no screen with'),
    ('a target that already exists', ('scr_one=scr_two',), 'collides'),
    ('two sources onto one target', ('scr_one=x', 'scr_two=x'), 'all rename to'),
    ('an empty target', ('scr_one=',), 'empty id'),
]:
    code, out, err = rename(flow(), *args)
    if code == 1 and why in err:
        ok(f'refuses {name}')
    else:
        bad(f'refuses {name}', f'exit {code}, stderr {err!r}')

# A refusal must leave the document untouched -- a partial rename is worse than none, because
# the config still looks plausible and the broken half is a dangling navigate.
code, out, _ = rename(flow(), 'scr_one=welcome', 'scr_two=scr_pay')
if code == 1 and out is None:
    ok('a refusal emits no document at all')
else:
    bad('a refusal emits no document at all', f'exit {code}, got a document: {out is not None}')

# A swap and a shift are legal: the collision test must exempt a target that is itself being
# renamed away in the same pass, or every chained rename reads as a collision.
code, out, _ = rename(flow(), 'scr_one=scr_two', 'scr_two=scr_one')
if code == 0 and out and ids(out) == ['scr_two', 'scr_one', 'scr_pay']:
    ok('a swap is allowed (the target is renamed away in the same pass)')
else:
    bad('a swap is allowed', f'exit {code}, ids={ids(out) if out else None}')


# ------------------------------------------------------------------ the oracle
print('\nintroduces no new verify-config findings:')

_before = findings(flow())
for _args in (('scr_one=welcome',), ('scr_pay=paywall',),
              ('scr_one=welcome', 'scr_two=signup', 'scr_pay=paywall')):
    _code, _out, _ = rename(flow(), *_args)
    _map = dict(a.split('=', 1) for a in _args)
    _new = [f for f in findings_modulo(_out, _map) if f not in _before]
    if _new:
        bad(f'rename {" ".join(_args)} introduces no new findings', f'new: {_new!r}')
    else:
        ok(f'rename {" ".join(_args)} introduces no new findings')

# The same oracle over every real export: rename the first screen and nothing may degrade.
for path in sorted(glob.glob(os.path.join(CORPUS, '*.json'))) + \
            sorted(glob.glob(os.path.join(RAW, '*.json'))):
    name = os.path.basename(path)
    tag = 'tracked' if os.path.dirname(path) == CORPUS else 'raw'
    doc = json.load(open(path))
    doc = doc['config'] if 'config' in doc and 'screens' in doc.get('config', {}) else doc
    first = doc['screens'][0]['id']
    before = findings(doc)
    code, out, err = rename(copy.deepcopy(doc), f'{first}=renamed_entry')
    if code != 0:
        bad(f'{name} ({tag}) renames its entry screen', f'exit {code}: {err}')
        continue
    new = [f for f in findings_modulo(out, {first: 'renamed_entry'}) if f not in before]
    if new:
        bad(f'{name} ({tag}) renames its entry screen cleanly', f'new findings: {new!r}')
    else:
        ok(f'{name} ({tag}) renames its entry screen cleanly')


# ------------------------------------------------------------------ the orphan check
print('\nthe orphaned _meta.screens key (the hand-edit backstop):')

_d = flow()
_d['screens'][2]['id'] = 'paywall'          # renamed by hand ...
for _s in _d['screens']:                     # ... navigation kept in step ...
    pass
_j = json.dumps(_d).replace('"screen": "scr_pay"', '"screen": "paywall"')
_d = json.loads(_j)                          # ... but _meta.screens left behind.
if any(ORPHAN in f for f in findings(_d)):
    ok('fires on a screen renamed without its _meta.screens key')
else:
    bad('fires on a screen renamed without its _meta.screens key',
        f'got {findings(_d)!r}')

_d = flow()
_d['_meta']['screens']['scr_deleted'] = {'products': []}
if any(ORPHAN in f for f in findings(_d)):
    ok('fires on a key left behind by a deleted screen')
else:
    bad('fires on a key left behind by a deleted screen', f'got {findings(_d)!r}')

_code, _out, _ = rename(flow(), 'scr_pay=paywall')
if not any(ORPHAN in f for f in findings(_out)):
    ok('silent after the tool does the same rename')
else:
    bad('silent after the tool does the same rename', f'got {findings(_out)!r}')

for path in sorted(glob.glob(os.path.join(CORPUS, '*.json'))) + \
            sorted(glob.glob(os.path.join(RAW, '*.json'))):
    name, tag = os.path.basename(path), ('tracked' if os.path.dirname(path) == CORPUS else 'raw')
    hits = [f for f in findings(json.load(open(path))) if ORPHAN in f]
    if hits:
        bad(f'{name} ({tag}) has no orphaned meta key', f'got {hits!r}')
    else:
        ok(f'{name} ({tag}) has no orphaned meta key')


print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
