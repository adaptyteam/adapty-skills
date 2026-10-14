#!/usr/bin/env python3
"""canvas — draw how a flow's screens connect, as one HTML page you open in a browser.

    python3 canvas.py draft.json --open                # write canvas.html beside the config, open it
    python3 canvas.py draft.json --shots DIR           # take the renders from another directory
    python3 canvas.py draft.json --text                # the same graph as plain text, for a chat reply

Reads a bare config or a `config get` envelope. Nothing is sent anywhere and nothing is written but
the one HTML file (or nothing at all with --text).

What becomes an arrow: every `navigate` the flow can run — on a tap, at a timer's end, inside each
branch of a conditional action (one arrow per case, plus "otherwise") — and `navigateNext`, which
goes to the next screen in `screens[]` order. What becomes a badge instead: actions that leave the
flow or have no fixed target — purchase, restore, close, back, custom actions. Screens nobody can
reach from the first screen, and screens with no way out at all, are flagged on the page.

Thumbnails: each screen uses the newest `*-<screen-id>.png` (shoot.sh writes
`shot-<sig>-<screen-id>.png`) or `<screen-id>.png` found in --shots DIR, which defaults to the
config's own directory -- where shoot.sh writes unless OUT says otherwise. Images are embedded, so the page is one file you can send.
A screen without a render draws as a card listing its buttons.

Stdlib only.
"""
import argparse
import base64
import glob
import html
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import localization
except Exception:  # a copy without localization.py still draws, with less text
    localization = None

NODE_W = 184
SHOT_H = 398           # 184 at the phone's 430:932 aspect
CARD_H = 150
COL_GAP = 170
ROW_GAP = 70           # between screens stacked in one column
PAD = 60
TERMINAL = {'purchase': 'buys', 'restorePurchases': 'restores', 'closeFlow': 'closes flow',
            'navigateBack': 'back', 'custom': 'custom action'}


# ---------- reading the config ----------

def load(path):
    with open(path) as f:
        d = json.load(f)
    if isinstance(d, dict) and 'config' in d and 'screens' not in d:
        d = d['config']
    if localization is not None:
        try:
            d = localization.resolve(d)
        except Exception:
            pass
    return d


def text_of(value, locale):
    """Visible words of a localizable or rich-text value, variables shown as {name}."""
    if isinstance(value, dict) and value.get('_localizable'):
        vals = value.get('values') or {}
        value = vals.get(locale) or next(iter(vals.values()), None)
    out = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('text'), str):
                out.append(o['text'])
            elif o.get('type') == 'variable':
                vid = (o.get('attrs') or {}).get('variableId') or o.get('variableId') or ''
                out.append('{' + vid.split('.')[-1] + '}')
            elif o.get('type') == 'switch':
                walk((o.get('default') or {}).get('value'))
                return
            for k, v in o.items():
                if k not in ('text',):
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    if isinstance(value, str):
        return ' '.join(value.split())
    walk(value)
    return ' '.join(' '.join(out).split())


def short(s, n=28):
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


class Screen:
    def __init__(self, raw, idx, locale):
        self.raw, self.idx, self.id = raw, idx, raw['id']
        self.name = raw.get('caption') or raw.get('name') or f'Screen {idx + 1}'
        self.map = (raw.get('elements') or {}).get('map') or {}
        self.children = {}

        def index(node):
            kids = [c['id'] for c in node.get('children') or []]
            self.children[node.get('id')] = kids
            for c in node.get('children') or []:
                index(c)
        index((raw.get('elements') or {}).get('hierarchy') or {})
        self.locale = locale
        self.option_label = {}
        for e in self.map.values():
            p = e.get('props') or {}
            for key in ('optionCustomId', 'customId'):
                if isinstance(p.get(key), str) and p[key]:
                    self.option_label.setdefault(p[key], self.label_of(e['id']))

    def label_of(self, eid):
        """The words a person sees on an element: its own text, else its subtree's first text,
        else the name of an icon inside it (a bare arrow button reads `ArrowLeft`)."""
        icon, stack = '', [eid]
        while stack:
            e = self.map.get(stack.pop(0)) or {}
            p = e.get('props') or {}
            if 'content' in p:
                t = text_of(p['content'], self.locale)
                if t:
                    return t
            if e.get('type') == 'icon' and not icon:
                icon = (p.get('icon') or {}).get('name') or ''
            stack.extend(self.children.get(e.get('id'), []))
        return icon


def cond_text(c, screens_by_id, screen):
    """A condition as words: `quiz = Rock`, `a and b`."""
    if not isinstance(c, dict):
        return 'condition'
    t = c.get('type')
    if t in ('&&', '||'):
        parts = [cond_text(p, screens_by_id, screen) for p in c.get('predicates') or []]
        return (' and ' if t == '&&' else ' or ').join(parts) or 'always'
    if t in ('==', '!=', '>', '<', '>=', '<='):
        left, right = c.get('left') or {}, c.get('right') or {}
        name = (left.get('variableId') or '').split('.')[0] or 'value'
        val = right.get('value')
        if isinstance(val, str):
            val = screen.option_label.get(val) or val
        op = {'==': '=', '!=': '≠'}.get(t, t)
        return f'{name} {op} {short(str(val), 22)}'
    if t in ('has', 'has_not', 'empty', 'not_empty'):
        return t.replace('_', ' ')
    return 'condition'


def extract(d):
    locale = d.get('defaultLocale') or ((d.get('localization') or {}).get('defaultLocale')) or 'en'
    screens = [Screen(s, i, locale) for i, s in enumerate(d.get('screens') or [])]
    by_id = {s.id: s for s in screens}
    edges = {}           # (src, dst) -> {labels, kind}
    badges = {s.id: [] for s in screens}

    def add_edge(src, dst, label, kind):
        e = edges.setdefault((src, dst), {'labels': [], 'kind': kind})
        if label and label not in e['labels']:
            e['labels'].append(label)
        if kind == 'branch':
            e['kind'] = 'branch'

    def run(actions, s, trigger, conds):
        for a in actions or []:
            if not isinstance(a, dict):
                continue
            t, payload = a.get('type'), a.get('payload') or {}
            # A branch is told apart by its condition, not by the button every case shares.
            lead = ' · '.join(conds) if conds else trigger
            if t == 'navigate':
                dst = payload.get('screen')
                if dst:
                    add_edge(s.id, dst, lead, 'branch' if conds else 'plain')
            elif t == 'navigateNext':
                if s.idx + 1 < len(screens):
                    add_edge(s.id, screens[s.idx + 1].id, lead, 'branch' if conds else 'plain')
            elif t == 'conditional':
                for case in payload.get('cases') or []:
                    if isinstance(case, list) and len(case) == 2:
                        body = case[1].get('value') if isinstance(case[1], dict) else case[1]
                        run(body, s, trigger, conds + [cond_text(case[0], by_id, s)])
                dflt = payload.get('default')
                if dflt is not None:
                    body = dflt.get('value') if isinstance(dflt, dict) else dflt
                    run(body, s, trigger, conds + ['otherwise'])
            elif t in TERMINAL:
                word = TERMINAL[t]
                if t == 'custom':
                    word = f"custom: {payload.get('id') or payload.get('actionId') or a.get('id') or ''}".strip(': ')
                if word not in badges[s.id]:
                    badges[s.id].append(word)

    for s in screens:
        def walk(o, eid=None):
            if isinstance(o, dict):
                for inter in o.get('interactions') or []:
                    trig = inter.get('trigger') or 'tap'
                    if trig == 'tap':
                        lbl = s.label_of(eid) if eid else ''
                        trig = f'“{short(lbl, 22)}”' if lbl else 'tap'
                    elif trig in ('timer-end', 'timerEnd'):
                        trig = 'after timer'
                    run(inter.get('actions'), s, trig, [])
                for k, v in o.items():
                    if k != 'interactions':
                        walk(v, eid)
            elif isinstance(o, list):
                for v in o:
                    walk(v, eid)
        for eid, e in s.map.items():
            walk(e, eid)
        walk({k: v for k, v in s.raw.items() if k != 'elements'})

    return screens, edges, badges


# ---------- layout ----------

def layout(screens, edges):
    ids = [s.id for s in screens]
    out = {}
    for (a, b) in edges:
        out.setdefault(a, []).append(b)
    level, order = {}, []
    if ids:
        level[ids[0]] = 0
        queue = [ids[0]]
        while queue:
            cur = queue.pop(0)
            order.append(cur)
            for nxt in sorted(out.get(cur, []), key=lambda x: ids.index(x) if x in ids else 1e9):
                if nxt in ids and nxt not in level:
                    level[nxt] = level[cur] + 1
                    queue.append(nxt)
    unreachable = [i for i in ids if i not in level]
    last = max(level.values(), default=-1)
    for i in unreachable:
        level[i] = last + 1
        order.append(i)
    cols = {}
    for i in order:
        cols.setdefault(level[i], []).append(i)
    return level, cols, set(unreachable)


def dead_end(outs, badges):
    """No arrow out, and nothing that ends the flow either. A back button alone does not count:
    the person can only retrace their steps, so the path forward stops here."""
    return not outs and not (set(badges) - {'back'})


def branch_points(screens, edges, level):
    """Screens where the path splits: a conditional decides, or two different buttons lead
    forward to two different screens. A back arrow beside a Continue button is not a split."""
    out = set()
    for s in screens:
        fwd = {b for (a, b), e in edges.items()
               if a == s.id and (e['kind'] == 'branch' or level.get(b, 1e9) > level[s.id])}
        if len(fwd) > 1:
            out.add(s.id)
    return out


# ---------- output ----------

def find_shots(dirpath, ids):
    shots = {}
    if not dirpath:
        return shots
    for sid in ids:
        cands = glob.glob(os.path.join(dirpath, f'*-{sid}.png')) + \
            glob.glob(os.path.join(dirpath, f'{sid}.png'))
        cands = [c for c in cands if not os.path.basename(c).startswith('NOT-A-RENDER')]
        if cands:
            shots[sid] = max(cands, key=os.path.getmtime)
    return shots


def as_text(screens, edges, badges, unreachable, branches):
    name = {s.id: s.name for s in screens}
    lines = []
    for s in screens:
        outs = [(b, e) for (a, b), e in edges.items() if a == s.id]
        head = ('◆ ' if s.id in branches else '▢ ') + s.name
        if s.id in unreachable:
            head += '   (nothing leads here)'
        lines.append(head)
        for b, e in outs:
            lines.append(f"    {' / '.join(e['labels']) or 'go'}  →  {name.get(b, b + ' (missing)')}")
        if badges[s.id]:
            lines.append('    ' + ', '.join(badges[s.id]))
        if dead_end(outs, badges[s.id]):
            lines.append('    (no way out)')
    return '\n'.join(lines)


def render_html(screens, edges, badges, level, cols, unreachable, shots, title, branches):
    has_shots = bool(shots)
    node_h = SHOT_H + 46 if has_shots else CARD_H
    step = NODE_W + COL_GAP

    # One row, left to right, however long the flow: the map is read as a line from the first
    # screen to the last. The page opens at a readable size and scrolls sideways.
    pos = {}
    max_rows = max((len(v) for v in cols.values()), default=1)
    row_h = max_rows * node_h + (max_rows - 1) * ROW_GAP
    for c, members in cols.items():
        col_h = len(members) * node_h + (len(members) - 1) * ROW_GAP
        y0 = PAD + (row_h - col_h) / 2
        for i, sid in enumerate(members):
            pos[sid] = (PAD + c * step, y0 + i * (node_h + ROW_GAP))
    width = PAD * 2 + (max(cols, default=0) + 1) * step - COL_GAP
    total_h = PAD * 2 + row_h
    row_bottom = PAD + row_h

    paths, labels = [], []
    out_count, in_count = {}, {}
    for (a, b) in edges:
        out_count[a] = out_count.get(a, 0) + 1
        in_count[b] = in_count.get(b, 0) + 1
    out_i, in_i, lane = {}, {}, {}
    idx = {s.id: s.idx for s in screens}
    extra_bottom = 0
    for (a, b), e in sorted(edges.items(), key=lambda kv: (pos.get(kv[0][0], (0, 0)), pos.get(kv[0][1], (0, 0)))):
        if a not in pos:
            continue
        ax, ay = pos[a]
        oi = out_i.get(a, 0); out_i[a] = oi + 1
        sy = ay + node_h * (oi + 1) / (out_count[a] + 1)
        text = ' / '.join(e['labels']) or 'go'
        cls = 'edge ' + e['kind']
        if b not in pos:
            d = f'M{ax + NODE_W},{sy} L{ax + NODE_W + 90},{sy}'
            cls += ' missing'
            text += f' → missing screen {b}'
            mx, my = ax + NODE_W + 45, sy - 10
        else:
            bx, by = pos[b]
            ii = in_i.get(b, 0); in_i[b] = ii + 1
            ty = by + node_h * (ii + 1) / (in_count[b] + 1)
            if level[b] > level[a]:
                x1, x2 = ax + NODE_W, bx
                c = max(60, (x2 - x1) * 0.45)
                d = f'M{x1},{sy} C{x1 + c},{sy} {x2 - c},{ty} {x2},{ty}'
                mx, my = (x1 + x2) / 2, (sy + ty) / 2
            elif level[b] == level[a]:
                # Same column: a bracket on the right-hand side. Dashed only when it returns to a
                # screen that comes earlier in the flow.
                xr = ax + NODE_W + 46
                d = f'M{ax + NODE_W},{sy} C{xr},{sy} {xr},{ty} {bx + NODE_W},{ty}'
                mx, my = xr - 10, (sy + ty) / 2
                if idx[b] < idx[a]:
                    cls += ' back'
            else:
                # Into an earlier column: leave by the left edge and arrive at the right edge, so
                # the arrow runs through the gaps between columns and never behind a screen
                # stacked in the same column. Dashed when it returns to an earlier screen.
                x1, x2 = ax, bx + NODE_W
                if level[a] - level[b] == 1:
                    d = f'M{x1},{sy} C{x1 - 60},{sy} {x2 + 60},{ty} {x2},{ty}'
                    mx, my = (x1 + x2) / 2, (sy + ty) / 2
                else:  # several columns back: down the gap, under the row, up the gap
                    k = lane['back'] = lane.get('back', 0) + 1
                    yb = row_bottom + 26 + 22 * k
                    d = (f'M{x1},{sy} C{x1 - 45},{sy} {x1 - 45},{yb} {x1 - 90},{yb} '
                         f'L{x2 + 90},{yb} C{x2 + 45},{yb} {x2 + 45},{ty} {x2},{ty}')
                    mx, my = (x1 + x2) / 2, yb - 6
                    extra_bottom = max(extra_bottom, 26 + 22 * k)
                if idx[b] < idx[a]:
                    cls += ' back'
        quiet = (e['kind'] == 'plain' and out_count[a] == 1 and b in pos
                 and not any(lbl.startswith('after') for lbl in e['labels']))
        paths.append(f'<path class="{cls}" data-from="{html.escape(a)}" data-to="{html.escape(b)}" d="{d}" marker-end="url(#arrow)"/>')
        if quiet:  # one plain way forward: the arrow says it all
            continue
        labels.append(f'<div class="elabel {e["kind"]}" data-from="{html.escape(a)}" data-to="{html.escape(b)}" '
                      f'style="left:{mx}px;top:{my}px">{html.escape(short(text, 60))}</div>')
    total_h += extra_bottom

    nodes = []
    for s in screens:
        x, y = pos[s.id]
        outs = {b for (a, b) in edges if a == s.id}
        flags = []
        if s.id in branches:
            flags.append('<span class="flag branch">branches</span>')
        if s.id in unreachable:
            flags.append('<span class="flag warn">nothing leads here</span>')
        if dead_end(outs, badges[s.id]):
            flags.append('<span class="flag warn">no way out</span>')
        if s.idx == 0:
            flags.append('<span class="flag start">start</span>')
        badge = ''.join(f'<span class="badge">{html.escape(w)}</span>' for w in badges[s.id])
        if s.id in shots:
            with open(shots[s.id], 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            body = f'<img src="data:image/png;base64,{b64}" alt="{html.escape(s.name)}">'
        else:
            buttons = []
            for eid, e in s.map.items():
                if e.get('interactions'):
                    lbl = s.label_of(eid)
                    if lbl and lbl not in buttons:
                        buttons.append(lbl)
            items = ''.join(f'<li>{html.escape(short(b, 26))}</li>' for b in buttons[:5])
            body = f'<div class="card-body"><ul>{items or "<li class=muted>no buttons</li>"}</ul></div>'
        nodes.append(
            f'<div class="node{" has-shot" if s.id in shots else ""}" data-id="{html.escape(s.id)}" '
            f'style="left:{x}px;top:{y}px;width:{NODE_W}px;height:{node_h}px">'
            f'<div class="head"><span class="num">{s.idx + 1}</span>'
            f'<span class="name" title="{html.escape(s.id)}">{html.escape(s.name)}</span></div>'
            f'<div class="flags">{"".join(flags)}{badge}</div>{body}</div>')

    n_branch = len(branches)
    stats = f'{len(screens)} screens · {n_branch} branch point{"s" if n_branch != 1 else ""}'
    if unreachable:
        stats += f' · {len(unreachable)} unreachable'
    return TEMPLATE.format(
        title=html.escape(title), stats=html.escape(stats), w=int(width), h=int(total_h),
        paths='\n'.join(paths), labels='\n'.join(labels), nodes='\n'.join(nodes))


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — screen map</title>
<style>
:root {{
  --bg:#f4f4f2; --dot:#d9d9d4; --panel:#ffffff; --ink:#1b1b1a; --muted:#73736e; --line:#9a9a93;
  --accent:#6b4eff; --accent-soft:#ece8ff; --warn:#c2410c; --warn-soft:#fdeee5; --ok:#15803d;
  --ok-soft:#e5f5ea; --shadow:0 1px 2px rgba(0,0,0,.06),0 8px 24px rgba(0,0,0,.06);
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#141413; --dot:#2a2a28; --panel:#1f1f1d; --ink:#ecece8; --muted:#9a9a93; --line:#6a6a64;
  --accent:#9d8bff; --accent-soft:#2b2547; --warn:#fb923c; --warn-soft:#3a2416; --ok:#4ade80;
  --ok-soft:#173222; --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);
}} }}
:root[data-theme="dark"] {{
  --bg:#141413; --dot:#2a2a28; --panel:#1f1f1d; --ink:#ecece8; --muted:#9a9a93; --line:#6a6a64;
  --accent:#9d8bff; --accent-soft:#2b2547; --warn:#fb923c; --warn-soft:#3a2416; --ok:#4ade80;
  --ok-soft:#173222; --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);
}}
* {{ box-sizing:border-box }}
html,body {{ margin:0; height:100%; background:var(--bg); color:var(--ink);
  font:13px/1.35 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; overflow:hidden }}
header {{ position:fixed; inset:0 0 auto 0; z-index:10; display:flex; gap:16px; align-items:center;
  padding:12px 16px; background:color-mix(in srgb,var(--bg) 85%,transparent); backdrop-filter:blur(8px) }}
header h1 {{ font-size:15px; margin:0; font-weight:650 }}
header .stats {{ color:var(--muted) }}
header .tools {{ margin-left:auto; display:flex; gap:6px }}
button {{ font:inherit; color:var(--ink); background:var(--panel); border:1px solid var(--dot);
  border-radius:8px; padding:5px 10px; cursor:pointer }}
button:hover {{ border-color:var(--line) }}
#viewport {{ position:absolute; inset:0; cursor:grab;
  background-image:radial-gradient(var(--dot) 1px,transparent 1px); background-size:22px 22px }}
#viewport.dragging {{ cursor:grabbing }}
#world {{ position:absolute; left:0; top:0; transform-origin:0 0 }}
svg {{ position:absolute; left:0; top:0; overflow:visible; pointer-events:none }}
.edge {{ fill:none; stroke:var(--line); stroke-width:1.6 }}
.edge.branch {{ stroke:var(--accent); stroke-width:2 }}
.edge.back {{ stroke-dasharray:5 5 }}
.edge.missing {{ stroke:var(--warn) }}
.edge.dim, .elabel.dim, .node.dim {{ opacity:.18 }}
.edge.hot {{ stroke-width:3 }}
#arrow path {{ fill:var(--line) }}
.elabel {{ position:absolute; transform:translate(-50%,-50%); white-space:nowrap; font-size:11.5px;
  padding:2px 8px; border-radius:999px; background:var(--panel); color:var(--muted);
  border:1px solid var(--dot); pointer-events:none; z-index:2 }}
.elabel.branch {{ color:var(--accent); background:var(--accent-soft); border-color:transparent; font-weight:550 }}
.node {{ position:absolute; background:var(--panel); border-radius:16px; box-shadow:var(--shadow);
  border:1px solid var(--dot); overflow:hidden; display:flex; flex-direction:column; cursor:pointer;
  transition:opacity .15s }}
.node:hover {{ border-color:var(--accent) }}
.head {{ display:flex; gap:8px; align-items:center; padding:9px 11px 4px }}
.num {{ flex:none; width:20px; height:20px; border-radius:6px; display:grid; place-items:center;
  background:var(--bg); color:var(--muted); font-size:11px; font-weight:600 }}
.name {{ font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap }}
.flags {{ display:flex; flex-wrap:wrap; gap:4px; padding:2px 11px 8px; min-height:8px }}
.flag,.badge {{ font-size:10.5px; padding:1px 7px; border-radius:999px; background:var(--bg); color:var(--muted) }}
.flag.branch {{ background:var(--accent-soft); color:var(--accent) }}
.flag.warn {{ background:var(--warn-soft); color:var(--warn) }}
.flag.start {{ background:var(--ok-soft); color:var(--ok) }}
.node img {{ display:block; width:100%; flex:1; min-height:0; object-fit:cover; object-position:top;
  border-top:1px solid var(--dot) }}
.card-body ul {{ margin:0; padding:2px 11px 10px 26px; color:var(--muted) }}
.card-body li {{ margin:2px 0 }}
.muted {{ list-style:none; margin-left:-15px }}
#lightbox {{ position:fixed; inset:0; z-index:20; display:none; place-items:center;
  background:rgba(0,0,0,.6) }}
#lightbox.open {{ display:grid }}
#lightbox img {{ max-height:92vh; max-width:92vw; border-radius:18px; box-shadow:var(--shadow) }}
.legend {{ position:fixed; left:16px; bottom:14px; z-index:10; display:flex; gap:14px; color:var(--muted);
  font-size:12px; background:var(--panel); border:1px solid var(--dot); border-radius:10px; padding:7px 12px }}
.legend i {{ display:inline-block; width:22px; height:0; border-top:2px solid var(--line);
  vertical-align:middle; margin-right:6px }}
.legend i.b {{ border-color:var(--accent) }} .legend i.d {{ border-top-style:dashed }}
@media (max-width:640px) {{ .legend {{ display:none }} header {{ flex-wrap:wrap }} }}
</style></head><body>
<header><h1>{title}</h1><span class="stats">{stats}</span>
<div class="tools"><button id="fit">Fit</button><button id="zin">+</button><button id="zout">−</button><button id="theme">Theme</button></div></header>
<div id="viewport"><div id="world" style="width:{w}px;height:{h}px">
<svg width="{w}" height="{h}"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>
{paths}
</svg>
{labels}
{nodes}
</div></div>
<div class="legend"><span><i></i>always</span><span><i class="b"></i>depends on an answer</span><span><i class="d"></i>goes back</span></div>
<div id="lightbox"><img alt=""></div>
<script>
const vp=document.getElementById('viewport'), world=document.getElementById('world');
let s=1,x=0,y=0;
const apply=()=>world.style.transform=`translate(${{x}}px,${{y}}px) scale(${{s}})`;
function fit(){{ const W=vp.clientWidth,H=vp.clientHeight-60,w=world.offsetWidth,h=world.offsetHeight;
  s=Math.min(1,W/w,H/h); x=(W-w*s)/2; y=60+(H-h*s)/2; apply(); }}
function start(){{ const H=vp.clientHeight-60,h=world.offsetHeight;
  s=Math.min(1,Math.max(.45,H/h)); x=0; y=60+Math.max(0,(H-h*s)/2); apply(); }}
function zoom(f,cx=vp.clientWidth/2,cy=vp.clientHeight/2){{ const n=Math.min(3,Math.max(.15,s*f));
  x=cx-(cx-x)*n/s; y=cy-(cy-y)*n/s; s=n; apply(); }}
vp.addEventListener('wheel',e=>{{ e.preventDefault();
  if(e.ctrlKey||e.metaKey) zoom(Math.exp(-e.deltaY/200),e.clientX,e.clientY); else {{ x-=e.deltaX; y-=e.deltaY; apply(); }} }},{{passive:false}});
let drag=null;
vp.addEventListener('pointerdown',e=>{{ if(e.target.closest('.node')) return; drag=[e.clientX-x,e.clientY-y]; vp.classList.add('dragging'); }});
addEventListener('pointermove',e=>{{ if(drag){{ x=e.clientX-drag[0]; y=e.clientY-drag[1]; apply(); }} }});
addEventListener('pointerup',()=>{{ drag=null; vp.classList.remove('dragging'); }});
document.getElementById('fit').onclick=fit;
document.getElementById('zin').onclick=()=>zoom(1.25);
document.getElementById('zout').onclick=()=>zoom(.8);
document.getElementById('theme').onclick=()=>{{ const r=document.documentElement;
  const dark=r.dataset.theme? r.dataset.theme==='dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  r.dataset.theme=dark?'light':'dark'; }};
const all=[...document.querySelectorAll('.edge,.elabel')], nodes=[...document.querySelectorAll('.node')];
nodes.forEach(n=>{{ const id=n.dataset.id;
  n.addEventListener('mouseenter',()=>{{ const near=new Set([id]);
    all.forEach(el=>{{ const on=el.dataset.from===id||el.dataset.to===id;
      if(on){{ near.add(el.dataset.from); near.add(el.dataset.to); }}
      el.classList.toggle('dim',!on); el.classList.toggle('hot',on); }});
    nodes.forEach(m=>m.classList.toggle('dim',!near.has(m.dataset.id))); }});
  n.addEventListener('mouseleave',()=>{{ all.forEach(el=>el.classList.remove('dim','hot')); nodes.forEach(m=>m.classList.remove('dim')); }});
  n.addEventListener('click',()=>{{ const img=n.querySelector('img'); if(!img) return;
    const lb=document.getElementById('lightbox'); lb.querySelector('img').src=img.src; lb.classList.add('open'); }});
}});
document.getElementById('lightbox').onclick=e=>e.currentTarget.classList.remove('open');
addEventListener('keydown',e=>{{ if(e.key==='Escape') document.getElementById('lightbox').classList.remove('open'); if(e.key==='0') fit(); if(e.key==='Home') start(); }});
start();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description='Draw how a flow\'s screens connect.')
    ap.add_argument('config', help='a bare config or a `config get` envelope')
    ap.add_argument('--shots', help='directory holding renders named *-<screen-id>.png, as shoot.sh '
                                    'writes them (default: the config\'s directory)')
    ap.add_argument('--out', help='HTML path (default: canvas.html beside the config)')
    ap.add_argument('--title', help='page title (default: the envelope name or the file name)')
    ap.add_argument('--open', action='store_true', help='open the page in the default browser')
    ap.add_argument('--text', action='store_true', help='print the graph as text instead of writing HTML')
    a = ap.parse_args()

    try:
        d = load(a.config)
    except (OSError, ValueError) as e:
        print(f'canvas: cannot read {a.config}: {e}', file=sys.stderr)
        return 2
    if not d.get('screens'):
        print('canvas: the config has no screens', file=sys.stderr)
        return 2
    screens, edges, badges = extract(d)
    level, cols, unreachable = layout(screens, edges)
    branches = branch_points(screens, edges, level)

    if a.text:
        print(as_text(screens, edges, badges, unreachable, branches))
        return 0

    title = a.title
    if not title:
        try:
            with open(a.config) as f:
                env = json.load(f)
            title = env.get('name') or env.get('title')
        except Exception:
            title = None
    title = title or os.path.splitext(os.path.basename(a.config))[0]
    shots = find_shots(a.shots or os.path.dirname(os.path.abspath(a.config)), [s.id for s in screens])
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.config)), 'canvas.html')
    with open(out, 'w') as f:
        f.write(render_html(screens, edges, badges, level, cols, unreachable, shots, title, branches))
    print(f'canvas: {out}')
    print(f'  {len(screens)} screens, {len(edges)} connections, '
          f'{len(shots)} with a render' + (f', {len(unreachable)} unreachable' if unreachable else ''))
    if a.open:
        opener = 'open' if sys.platform == 'darwin' else ('start' if os.name == 'nt' else 'xdg-open')
        try:
            subprocess.run([opener, out], check=False, shell=(os.name == 'nt'))
        except OSError:
            print('  could not open a browser here — open the file above yourself')
    return 0


if __name__ == '__main__':
    sys.exit(main())
