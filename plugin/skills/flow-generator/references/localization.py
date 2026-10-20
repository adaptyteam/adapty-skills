#!/usr/bin/env python3
"""localization — the flow's localization catalog: write it, read through it, edit it.

A flow keeps every localizable value in ONE place, `localization.content`, and each localizable
field stores only a reference to it:

    "content": {"_lid": "lc_0"}                      <- text.props.content
    "localization": {
      "locales": [{"id": "en", "code": "en", "name": "English"}, ...],
      "defaultLocale": "en",
      "content": {"lc_0": {"kind": "rich-text", "values": {"en": [...], "fr": [...]}}}
    }

The localizable fields, and nothing else (names, ids, fills and geometry are never catalogued):
text `content`, every input and picker `placeholder`, image `image`, video `video`, alert
`title` / `message`, and the Open URL action's `url` (a `rich-string` entry, so each locale can
open its own page) -- including actions nested in conditional actions, and elements inside
`components`. `LOCALIZABLE` and `LOCALIZABLE_ACTION_FIELDS` below are that list, read off the
schema.

Three jobs, one per public function:

  catalog(flow)   Move every inline localizable value into the catalog and stamp schemaVersion
                  13. A port of the builder's own migration 013, so a document it produces is the
                  document the builder would have produced. It leaves existing refs alone, so it
                  is safe -- and REQUIRED -- after any edit that wrote an inline value into a
                  catalogued flow: grafting a flowkit fragment, lifting a catalog template, or a
                  hand-written `{"_localizable": true, "values": ...}`. It refuses a document
                  below version 12; those need the Flow Builder's full migration chain first.

  resolve(flow)   A READ-ONLY view for checkers: every ref replaced by the inline form
                  `{"_localizable": true, "values": ..., "_ref": id}` and `locales` /
                  `defaultLocale` moved to the top level, `localization` removed. The marker
                  is `_ref`, never `_lid`,
                  so a view can never pass for stored refs, and resolving a view returns it
                  unchanged. Never write it back: it duplicates shared entries, and
                  `verify-config.py` refuses its inline values.

  new_entry / copy_entry / entry_for
                  The editing primitives. An entry is SHARED by every ref that names it, so
                  editing its `values` changes all of them; an independent copy needs its own
                  entry, which `copy_entry` mints.

Two semantics every edit has to keep:
  * `values` is keyed by locale ID (`localization.locales[].id`), not by language code. They are
    often equal and nothing guarantees it.
  * An absent or empty value means "fall back to the default locale". Never copy the default
    value into other locales to "fill" them -- that turns a missing translation into an explicit
    one nobody translated. `is_empty` is the emptiness test; `None`/falsy is not.

CLI:
    python3 localization.py catalog IN.json [--out OUT.json]    # default: rewrite IN in place
    python3 localization.py resolve IN.json                     # print the read view

`catalog` prints each migration warning to stderr and exits 1 when there were any: a warning means
a value was DROPPED (a locale nobody declared, a conditional branch whose shape does not match the
default locale's), and a dropped value is something to report, not to wave through.
Exit 2: unreadable input, or a document below version 12.
"""
import copy
import json
import re
import sys

SCHEMA_VERSION = 13
#: The lowest version this module migrates from. Below it, migrations 011 (structured product
#: refs) and 012 (the screen product registry) have not run, and they are not ported here.
MIN_SOURCE_VERSION = 12

KINDS = ('rich-text', 'rich-string', 'image', 'video')

_PLACEHOLDER_TYPES = ('text-input', 'email-input', 'password-input', 'number-input',
                      'phone-input', 'date-picker', 'time-picker', 'date-time-picker')

#: element type -> {property: kind}. Every schema property with `localizable: true`.
LOCALIZABLE = {
    'text': {'content': 'rich-text'},
    'image': {'image': 'image'},
    'video': {'video': 'video'},
    **{t: {'placeholder': 'rich-string'} for t in _PLACEHOLDER_TYPES},
}

#: action type -> {payload field: kind}. A `url` is stored as a `rich-string`: its value is a
#: string or a list of text, variable and token nodes, never paragraphs.
LOCALIZABLE_ACTION_FIELDS = {
    'alert': {'title': 'rich-string', 'message': 'rich-string'},
    'openUrl': {'url': 'rich-string'},
}

_CONTENT_ID = re.compile(r'^lc_(\d+)$')
_NO_LOCALE_FALLBACK = 'en'
_SAFE_INT = 2 ** 53 - 1
_ABSENT = object()


class MigrationError(ValueError):
    """The document cannot be catalogued here (below version 12)."""


# --- small predicates, matching the schema package's --------------------------------------

def _rec(v):
    return isinstance(v, dict)


def is_ref(v):
    return isinstance(v, dict) and isinstance(v.get('_lid'), str)


def _is_switch(v):
    return _rec(v) and v.get('type') == 'switch'


def _is_const(v):
    return _rec(v) and v.get('type') == 'const'


def _empty_text_node(n):
    return _rec(n) and n.get('type') == 'text' and n.get('text') == ''


def _empty_paragraph(n):
    if not (_rec(n) and n.get('type') == 'paragraph'):
        return False
    if 'content' not in n or n['content'] is None:
        return True
    return isinstance(n['content'], list) and all(_empty_text_node(c) for c in n['content'])


def is_empty(kind, value):
    """True when `value` means "missing" for `kind`: '', [], None, an emptied rich-text
    document, or a media object whose url is ''. No trim -- whitespace is content."""
    if value is None:
        return True
    if kind == 'rich-text':
        if isinstance(value, str):
            return value == ''
        return isinstance(value, list) and all(_empty_paragraph(p) for p in value)
    if kind == 'rich-string':
        if isinstance(value, str):
            return value == ''
        return isinstance(value, list) and len(value) == 0
    if kind == 'image':
        return not _rec(value) or ('url' in value and value['url'] == '')
    if kind == 'video':
        return not _rec(value) or ('videoUrl' in value and value['videoUrl'] == '')
    return False


def is_catalog(flow):
    """The document keeps its locales under `localization`."""
    return _rec(flow) and _rec(flow.get('localization'))


def locales(flow):
    """Declared locales, wherever this document keeps them."""
    src = flow.get('localization') if is_catalog(flow) else flow
    v = (src or {}).get('locales')
    return v if isinstance(v, list) else []


def default_locale(flow):
    src = flow.get('localization') if is_catalog(flow) else flow
    return (src or {}).get('defaultLocale')


def _canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'))


# --- catalog(): the migration 013 port ------------------------------------------------------

class _Catalog:
    def __init__(self, flow, content, locs, default, canonicalized, warnings):
        self.content = content
        self.canonicalized = canonicalized
        self.warnings = warnings
        self.ordered = ([l['id'] for l in locs if _rec(l) and isinstance(l.get('id'), str)]
                        if isinstance(locs, list) else None)
        self.default = default if isinstance(default, str) else None
        undeclared_default = (None if self.ordered else (self.default or _NO_LOCALE_FALLBACK))
        if self.ordered is not None:
            self.known = set(self.ordered)
            for loc in (self.default, undeclared_default):
                if loc is not None:
                    self.known.add(loc)
        else:
            self.known = None
        self.seed = (undeclared_default if undeclared_default is not None else
                     self.default if self.default is not None else
                     (self.ordered[0] if self.ordered else _NO_LOCALE_FALLBACK))
        self.taken = set(content)
        _collect_refs(flow, self.taken)
        self.next = 0
        for cid in self.taken:
            m = _CONTENT_ID.match(cid)
            if m and int(m.group(1)) <= _SAFE_INT:
                self.next = max(self.next, int(m.group(1)) + 1)

    def is_known(self, loc):
        return self.known is None or loc in self.known

    def mint(self):
        while True:
            cid = f'lc_{self.next}'
            self.next += 1
            if cid not in self.taken:
                self.taken.add(cid)
                return cid

    def warn(self, code, loc, locales_, message):
        w = {'step': SCHEMA_VERSION, 'code': code, 'path': loc['path']}
        for k in ('screenId', 'componentId', 'elementId'):
            if loc.get(k) is not None:
                w[k] = loc[k]
        w['property'] = loc['property']
        if loc.get('actionId') is not None:
            w['actionId'] = loc['actionId']
        w['locales'] = locales_
        w['message'] = message
        self.warnings.append(w)


def _collect_refs(node, out):
    if isinstance(node, list):
        for x in node:
            _collect_refs(x, out)
    elif _rec(node):
        if is_ref(node):
            out.add(node['_lid'])
        for x in node.values():
            _collect_refs(x, out)


def _canonicalize_default(locs, default, path, warnings):
    if not isinstance(locs, list) or not isinstance(default, str):
        return default, None
    declared = [l for l in locs if _rec(l)]
    if any(l.get('id') == default for l in declared):
        return default, None
    match = next((l for l in declared if l.get('code') == default), None)
    lid = match.get('id') if match else None
    if not isinstance(lid, str):
        return default, None
    warnings.append({
        'step': SCHEMA_VERSION, 'code': 'default-locale-code-canonicalized', 'path': path,
        'locales': [default, lid],
        'message': (f'defaultLocale "{default}" is the code of locale "{lid}": the default '
                    f'locale and the values keyed by "{default}" now use "{lid}".')})
    return lid, (default, lid)


def _rekey(entries, canon, kind):
    code, lid = canon
    taken = any(loc == lid and (kind is None or not is_empty(kind, v)) for loc, v in entries)
    if taken or not any(loc == code for loc, _ in entries):
        return entries
    return [(lid if loc == code else loc, v) for loc, v in entries if loc != lid]


def _migrate_field(value, kind, loc, cat):
    if is_ref(value):
        return value
    if kind == 'rich-text' and _is_switch(value) and _fully_referenced(value):
        return value
    if _rec(value) and value.get('_localizable') is True:
        entries = list(value['values'].items()) if _rec(value.get('values')) else []
        if cat.canonicalized:
            entries = _rekey(entries, cat.canonicalized, kind)
    else:
        entries = [(cat.seed, value)]
    kept = [(l, v) for l, v in entries if cat.is_known(l)]
    orphans = [l for l, v in entries if not cat.is_known(l) and not is_empty(kind, v)]
    if orphans:
        cat.warn('orphan-locale-values-dropped', loc, orphans,
                 'Dropped values for locales not declared in localization.locales: '
                 + ', '.join(orphans) + '.')
    if kind == 'rich-text' and any(_is_switch(v) for _, v in kept):
        return _conditional_text(kept, loc, cat)
    return _promote(kind, kept, cat)


def _promote(kind, entries, cat):
    values = {l: v for l, v in entries if not is_empty(kind, v)}
    cid = cat.mint()
    cat.content[cid] = {'kind': kind, 'values': values}
    return {'_lid': cid}


def _read_switch(v):
    cases = v.get('cases') if isinstance(v.get('cases'), list) else []
    has_default = v.get('default') is not None
    leaves = [c[1] if isinstance(c, list) and len(c) > 1 else None for c in cases]
    if has_default:
        leaves = leaves + [v['default']]
    return {'cases': cases,
            'predicates': [c[0] if isinstance(c, list) and c else None for c in cases],
            'has_default': has_default, 'leaves': leaves,
            'const_leaves': [_is_const(x) for x in leaves]}


def _shape_key(s):
    return _canonical({'predicates': s['predicates'], 'hasDefault': s['has_default'],
                       'constLeaves': s['const_leaves']})


def _fully_referenced(v):
    return all(_is_const(x) and is_ref(x.get('value')) for x in _read_switch(v)['leaves'])


def _conditional_text(entries, loc, cat):
    present = [(l, v) for l, v in entries if not is_empty('rich-text', v)]
    by = {l: (l, v) for l, v in reversed(present)}
    structure = (by.get(cat.default) or
                 next((by[l] for l in (cat.ordered or []) if l in by), None) or
                 (present[0] if present else ('', None)))
    s_locale, s_value = structure
    if not _is_switch(s_value):
        switched = [l for l, v in present if _is_switch(v)]
        cat.warn('conditional-locale-shape-mismatch', loc, switched,
                 f'Conditional text for {", ".join(switched)} was dropped: '
                 f'{s_locale} holds plain text.')
        return _promote('rich-text', [(l, v) for l, v in present if not _is_switch(v)], cat)

    shape = _read_switch(s_value)
    key = _shape_key(shape)
    contributors, mismatched = [], []
    for l, v in present:
        ls = _read_switch(v) if _is_switch(v) else None
        if ls and _shape_key(ls) == key:
            contributors.append((l, ls))
        else:
            mismatched.append(l)
    if mismatched:
        lst = ', '.join(mismatched)
        cat.warn('conditional-locale-shape-mismatch', loc, mismatched,
                 f'Text for {lst} does not match the conditional structure of {s_locale} and '
                 f'was not carried over.')

    changed = False
    leaves = []
    for i, leaf in enumerate(shape['leaves']):
        if not _is_const(leaf) or is_ref(leaf.get('value')):
            leaves.append(leaf)
            continue
        values = {}
        for l, ls in contributors:
            ll = ls['leaves'][i]
            text = ll.get('value') if _is_const(ll) else None
            if not is_ref(text) and not is_empty('rich-text', text):
                values[l] = text
        cid = cat.mint()
        cat.content[cid] = {'kind': 'rich-text', 'values': values}
        changed = True
        leaves.append({'type': 'const', 'value': {'_lid': cid}})
    if not changed:
        return s_value
    out = dict(s_value)
    out['cases'] = [[c[0], leaves[i]] if isinstance(c, list) and leaves[i] is not c[1] else c
                    for i, c in enumerate(shape['cases'])]
    if shape['has_default']:
        out['default'] = leaves[len(shape['cases'])]
    return out


def _migrate_fields(record, table, owner, path, cat):
    for prop, value in list(record.items()):
        kind = table.get(prop)
        if kind:
            loc = dict(owner, property=prop, path=f'{path}.{prop}')
            record[prop] = _migrate_field(value, kind, loc, cat)


def _migrate_action(action, owner, path, cat):
    if not _rec(action) or not isinstance(action.get('type'), str):
        return
    if action['type'] == 'conditional':
        p = action.get('payload')
        if not _is_switch(p):
            return
        if isinstance(p.get('cases'), list):
            for i, c in enumerate(p['cases']):
                if isinstance(c, list) and len(c) >= 2:
                    _migrate_result(c[1], owner, f'{path}.payload.cases[{i}][1]', cat)
        _migrate_result(p.get('default'), owner, f'{path}.payload.default', cat)
        return
    table = LOCALIZABLE_ACTION_FIELDS.get(action['type'])
    if table and _rec(action.get('payload')):
        own = dict(owner, actionId=action['id']) if isinstance(action.get('id'), str) else owner
        _migrate_fields(action['payload'], table, own, f'{path}.payload', cat)


def _migrate_result(result, owner, path, cat):
    if not _is_const(result):
        return
    v = result.get('value')
    if isinstance(v, list):
        for i, a in enumerate(v):
            _migrate_action(a, owner, f'{path}.value[{i}]', cat)
    else:
        _migrate_action(v, owner, f'{path}.value', cat)


def _migrate_map(node_map, owner, path, cat):
    if not _rec(node_map):
        return
    for eid, el in node_map.items():
        if not _rec(el):
            continue
        own = dict(owner, elementId=eid)
        epath = f'{path}.{eid}'
        table = LOCALIZABLE.get(el.get('type')) if isinstance(el.get('type'), str) else None
        # Unknown element types keep their props verbatim; `propsByState` is never walked --
        # no localizable property is stateful.
        if table is not None and _rec(el.get('props')):
            _migrate_fields(el['props'], table, own, f'{epath}.props', cat)
        if isinstance(el.get('interactions'), list):
            for i, it in enumerate(el['interactions']):
                if _rec(it) and isinstance(it.get('actions'), list):
                    for j, a in enumerate(it['actions']):
                        _migrate_action(a, own, f'{epath}.interactions[{i}].actions[{j}]', cat)


def _version(flow):
    v = flow.get('schemaVersion')
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def catalog(flow):
    """Return `(new_flow, warnings)`. Never mutates `flow`. See the module docstring."""
    if not _rec(flow):
        raise MigrationError('not a flow config (expected a JSON object)')
    if _rec(flow.get('config')) and 'screens' not in flow:
        raise MigrationError('this is a `flows config get` envelope; pass its `config`')
    version = _version(flow)
    if version < MIN_SOURCE_VERSION:
        raise MigrationError(
            f'schemaVersion {version or "missing"} is below {MIN_SOURCE_VERSION}: migrations '
            f'011 and 012 have not run on it, and only the Flow Builder runs them. Ask the user '
            f'to open the flow in the Flow Builder and save it, then fetch it again.')
    if version > SCHEMA_VERSION:
        raise MigrationError(f'schemaVersion {version} is newer than {SCHEMA_VERSION}, the '
                             f'version this module writes; update the skill.')

    flow = copy.deepcopy(flow)
    warnings = []
    existing = flow.get('localization') if _rec(flow.get('localization')) else None
    src = existing if existing else flow
    locs = src.get('locales', _ABSENT)
    default, canon = _canonicalize_default(
        None if locs is _ABSENT else locs, src.get('defaultLocale', _ABSENT),
        'localization.defaultLocale' if existing else 'defaultLocale', warnings)
    content = dict(existing['content']) if existing and _rec(existing.get('content')) else {}
    if canon:
        for cid, e in list(content.items()):
            if _rec(e) and _rec(e.get('values')):
                kind = e.get('kind') if e.get('kind') in KINDS else None
                entries = list(e['values'].items())
                rekeyed = _rekey(entries, canon, kind)
                if rekeyed is not entries:
                    content[cid] = dict(e, values=dict(rekeyed))

    cat = _Catalog(flow, content, None if locs is _ABSENT else locs,
                   None if default is _ABSENT else default, canon, warnings)
    if isinstance(flow.get('screens'), list):
        for i, scr in enumerate(flow['screens']):
            if _rec(scr) and _rec(scr.get('elements')):
                owner = {'screenId': scr['id']} if isinstance(scr.get('id'), str) else {}
                _migrate_map(scr['elements'].get('map'), owner,
                             f'screens[{i}].elements.map', cat)
    if _rec(flow.get('components')):
        for cid, comp in flow['components'].items():
            if _rec(comp):
                _migrate_map(comp.get('map'), {'componentId': cid}, f'components.{cid}.map', cat)

    out = {k: v for k, v in flow.items() if k not in ('locales', 'defaultLocale', 'localization')}
    loc_out = dict(existing or {})
    # Same key order as the builder's object spread: an existing key keeps its position, a new
    # one is appended, and an absent value stays absent (JSON.stringify drops `undefined`).
    for k, v in (('locales', locs), ('defaultLocale', default), ('content', content)):
        if v is _ABSENT:
            loc_out.pop(k, None)
        else:
            loc_out[k] = v
    out['localization'] = loc_out
    out['schemaVersion'] = SCHEMA_VERSION
    return out, warnings


# --- resolve(): the read view ---------------------------------------------------------------

def resolve(flow):
    """A deep copy with every ref inlined. Read it; never write it. A legacy document (no
    `localization`) comes back as a plain copy, so a checker can report its format itself."""
    view = copy.deepcopy(flow)
    if not is_catalog(view):
        return view
    # The stored catalog leaves the view: every value now sits where it is used, and a checker
    # that walks the whole document must not meet each one a second time in the catalog.
    lz = view.pop('localization')
    content = lz.get('content') if _rec(lz.get('content')) else {}
    # The catalog is authoritative. A saved document also carries the legacy top-level fields,
    # echoed by the server as `locales: []` and a bare `defaultLocale`; letting those win reads
    # every declared locale as gone. Fall back to them only where the catalog says nothing.
    if lz.get('locales') is not None:
        view['locales'] = lz.get('locales')
    if lz.get('defaultLocale') is not None:
        view['defaultLocale'] = lz.get('defaultLocale')

    def inline(ref):
        e = content.get(ref['_lid'])
        values = copy.deepcopy(e['values']) if _rec(e) and _rec(e.get('values')) else {}
        return {'_localizable': True, 'values': values, '_ref': ref['_lid']}

    def switch_view(sw):
        leaf_refs = [x['value']['_lid'] for x in _read_switch(sw)['leaves']
                     if _is_const(x) and is_ref(x.get('value'))]
        locs = []
        for lid in leaf_refs:
            for l in ((content.get(lid) or {}).get('values') or {}):
                if l not in locs:
                    locs.append(l)

        def at(l):
            s = copy.deepcopy(sw)

            def leaf(x):
                if _is_const(x) and is_ref(x.get('value')):
                    e = content.get(x['value']['_lid']) or {}
                    return {'type': 'const', 'value': copy.deepcopy(
                        (e.get('values') or {}).get(l, ''))}
                return x
            s['cases'] = [[c[0], leaf(c[1])] if isinstance(c, list) and len(c) > 1 else c
                          for c in (s.get('cases') or [])]
            if s.get('default') is not None:
                s['default'] = leaf(s['default'])
            return s
        return {'_localizable': True, 'values': {l: at(l) for l in locs}, '_refs': leaf_refs}

    def walk_fields(record, table):
        for prop in table:
            v = record.get(prop)
            if is_ref(v):
                record[prop] = inline(v)
            elif _is_switch(v):
                record[prop] = switch_view(v)

    def walk_action(a):
        if not _rec(a):
            return
        if a.get('type') == 'conditional' and _is_switch(a.get('payload')):
            p = a['payload']
            for c in p.get('cases') or []:
                if isinstance(c, list) and len(c) > 1:
                    walk_result(c[1])
            walk_result(p.get('default'))
        elif a.get('type') in LOCALIZABLE_ACTION_FIELDS and _rec(a.get('payload')):
            walk_fields(a['payload'], LOCALIZABLE_ACTION_FIELDS[a['type']])

    def walk_result(r):
        if _is_const(r):
            v = r.get('value')
            for a in (v if isinstance(v, list) else [v]):
                walk_action(a)

    def walk_map(m):
        for el in (m or {}).values() if _rec(m) else ():
            if not _rec(el):
                continue
            table = LOCALIZABLE.get(el.get('type'))
            if table and _rec(el.get('props')):
                walk_fields(el['props'], table)
            for it in el.get('interactions') or []:
                for a in (it.get('actions') or []) if _rec(it) else []:
                    walk_action(a)

    for scr in view.get('screens') or []:
        if _rec(scr) and _rec(scr.get('elements')):
            walk_map(scr['elements'].get('map'))
    for comp in (view.get('components') or {}).values() if _rec(view.get('components')) else ():
        if _rec(comp):
            walk_map(comp.get('map'))
    return view


# --- every localizable field --------------------------------------------------------------

def iter_fields(flow):
    """Yield `(where, kind, holder, key)` for every localizable field in the document, where
    `holder[key]` is the stored value (a ref, a switch of refs, or -- before `catalog()` -- an
    inline value). `where` names the element or action, for messages. Walks what migration 013
    walks: screen and component element maps, their interactions, and conditional actions."""
    def fields(holder, table, where):
        for key, kind in table.items():
            if key in holder:
                yield where, kind, holder, key

    def action(a, where):
        if not _rec(a):
            return
        if a.get('type') == 'conditional' and _is_switch(a.get('payload')):
            p = a['payload']
            for c in p.get('cases') or []:
                if isinstance(c, list) and len(c) > 1:
                    yield from result(c[1], where)
            yield from result(p.get('default'), where)
        elif a.get('type') in LOCALIZABLE_ACTION_FIELDS and _rec(a.get('payload')):
            yield from fields(a['payload'], LOCALIZABLE_ACTION_FIELDS[a['type']],
                              f'{where} {a["type"]} {a.get("id") or ""}'.rstrip())

    def result(r, where):
        if _is_const(r):
            v = r.get('value')
            for a in (v if isinstance(v, list) else [v]):
                yield from action(a, where)

    def node_map(m, owner):
        for eid, el in (m.items() if _rec(m) else ()):
            if not _rec(el):
                continue
            where = f'{owner}/{eid}'
            table = LOCALIZABLE.get(el.get('type'))
            if table and _rec(el.get('props')):
                yield from fields(el['props'], table, where)
            for it in el.get('interactions') or []:
                for a in (it.get('actions') or []) if _rec(it) else []:
                    yield from action(a, where)

    for scr in flow.get('screens') or []:
        if _rec(scr) and _rec(scr.get('elements')):
            yield from node_map(scr['elements'].get('map'), str(scr.get('id')))
    for cid, comp in (flow.get('components') or {}).items() if _rec(flow.get('components')) else ():
        if _rec(comp):
            yield from node_map(comp.get('map'), f'component {cid}')


def refs_in(value):
    """The content ids a stored field value names: one for a ref, one per branch for a switch."""
    if is_ref(value):
        return [value['_lid']]
    if _is_switch(value):
        return [x['value']['_lid'] for x in _read_switch(value)['leaves']
                if _is_const(x) and is_ref(x.get('value'))]
    return []


def is_inline(value):
    """A stored value that `catalog()` would still have to move: anything but a ref or a
    switch whose every const branch is a ref. `None` (field absent) is not inline."""
    if value is None or is_ref(value):
        return False
    if _is_switch(value):
        return not all(is_ref(x.get('value')) for x in _read_switch(value)['leaves']
                       if _is_const(x))
    return True


def is_value_of_kind(kind, value):
    """Text kinds hold a string or a segment array, media kinds an object."""
    if kind in ('rich-text', 'rich-string'):
        return isinstance(value, (str, list))
    return _rec(value)


# --- editing primitives ---------------------------------------------------------------------

def entry_for(flow, ref):
    """The catalog entry a `{_lid}` ref names, or None when it dangles."""
    if not is_ref(ref):
        raise TypeError(f'expected a {{"_lid": ...}} ref, got {ref!r}')
    return ((flow.get('localization') or {}).get('content') or {}).get(ref['_lid'])


def _minter(flow):
    lz = flow.setdefault('localization', {})
    content = lz.setdefault('content', {})
    return _Catalog(flow, content, lz.get('locales'), lz.get('defaultLocale'), None, [])


def new_entry(flow, kind, values):
    """Add an entry to `flow` (in place) and return its ref. `values` is keyed by locale id;
    pass only the locales you actually have text for."""
    if kind not in KINDS:
        raise ValueError(f'kind must be one of {KINDS}, not {kind!r}')
    cat = _minter(flow)
    cid = cat.mint()
    cat.content[cid] = {'kind': kind,
                        'values': {l: v for l, v in values.items() if not is_empty(kind, v)}}
    return {'_lid': cid}


def copy_entry(flow, ref):
    """An independent copy of the entry `ref` names, under a new id. Use it when ONE use of a
    shared entry must change and the others must not."""
    e = entry_for(flow, ref)
    if e is None:
        raise KeyError(f'dangling ref {ref["_lid"]!r}')
    return new_entry(flow, e['kind'], copy.deepcopy(e['values']))


# --- CLI ------------------------------------------------------------------------------------

def _main(argv):
    if len(argv) < 2 or argv[0] not in ('catalog', 'resolve'):
        print(__doc__.split('CLI:')[1].split('`catalog` prints')[0].strip(), file=sys.stderr)
        return 2
    cmd, src = argv[0], argv[1]
    out_path = src
    if '--out' in argv:
        out_path = argv[argv.index('--out') + 1]
    try:
        with open(src) as f:
            doc = json.load(f)
    except (OSError, ValueError) as exc:
        print(f'cannot read {src}: {exc}', file=sys.stderr)
        return 2
    # A `flows config get` envelope is catalogued inside and written back as an envelope, so the
    # working file keeps the shape `config update` and `diff-config.py` expect.
    envelope = _rec(doc) and 'screens' not in doc and _rec(doc.get('config'))
    cfg = doc['config'] if envelope else doc
    if cmd == 'resolve':
        json.dump(resolve(cfg), sys.stdout, ensure_ascii=False, indent=2)
        return 0
    try:
        out, warnings = catalog(cfg)
    except MigrationError as exc:
        print(f'not catalogued: {exc}', file=sys.stderr)
        return 2
    with open(out_path, 'w') as f:
        json.dump(dict(doc, config=out) if envelope else out, f, ensure_ascii=False, indent=2)
    n = len(out['localization']['content'])
    print(f'catalogued -> {out_path} ({n} entries, schemaVersion {SCHEMA_VERSION})')
    for w in warnings:
        print(f'DROPPED [{w["code"]}] {w["path"]}: {w["message"]}', file=sys.stderr)
    return 1 if warnings else 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
