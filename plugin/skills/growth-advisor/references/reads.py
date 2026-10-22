#!/usr/bin/env python3
"""Run growth-advisor's reads one at a time and print them as month tables.

    python3 <skill>/references/reads.py audit --app <APP_ID> --adapty "$ADAPTY" [--months 6]
    python3 <skill>/references/reads.py placement --app <APP_ID> --adapty "$ADAPTY" --placement <PLACEMENT_ID> [--months 12]

`audit` runs "The audit reads" in diagnosis.md over the last full months. `placement` reads one
placement: its audiences by name, every paywall or flow that sold on it, the weekly purchase count
a Time line needs, and, when one paywall replaced another, the before/after comparison.

Every table prints every group, sorted by the last full month, and says how many groups had a
value in it. The last full month is marked with `*`. Conversions print the rate in percent and the
number at the first step. A read that fails is printed as FAILED and listed again at the end: say
in the reply what could not be read. Every call is a read; nothing here writes.
"""
import argparse
import datetime as dt
import json
import shlex
import subprocess
import sys
import time

FAILED = []
NOTED = []
NO_DATA = '00000000-0000-0000-0000-000000000000'
FEW = 20   # paid users behind a rate below which the rate is noise


def cli(adapty, args):
    """Run one CLI read; on a rate limit wait once and retry once. Returns (body, error)."""
    cmd = shlex.split(adapty) + list(args) + ['--json']
    for attempt in (1, 2):
        p = subprocess.run(cmd, capture_output=True, text=True)
        out, body = p.stdout, None
        if '{' in out:
            try:
                body = json.JSONDecoder().raw_decode(out[out.index('{'):])[0]
            except ValueError:
                body = None
        if p.returncode == 0 and isinstance(body, dict) and 'error' not in body:
            time.sleep(0.6)
            return body, None
        err = body.get('error') if isinstance(body, dict) else None
        wait = err.get('retry_after_seconds') if isinstance(err, dict) else None
        if p.returncode == 4 and wait and attempt == 1:
            time.sleep(float(wait) + 0.5)
            continue
        msg = err.get('message') if isinstance(err, dict) else None
        return None, msg or ((p.stderr.strip().splitlines() or ['exit %d' % p.returncode])[-1][:200])
    return None, 'rate limited twice'


def every_page(adapty, app, topic):
    rows, page = [], 1
    while True:
        body, err = cli(adapty, [topic, 'list', '--app', app, '--page-size', '100', '--page', str(page)])
        if err:
            FAILED.append(f'{topic} list: {err}')
            return rows
        rows += body.get('data') or []
        pages = ((body.get('meta') or {}).get('pagination') or {}).get('pages') or 1
        if page >= pages:
            return rows
        page += 1


def window(months, to=None):
    today = dt.date.fromisoformat(to) if to else dt.date.today()
    last = today.replace(day=1) - dt.timedelta(days=1)          # end of the last full month
    first = last.replace(day=1)
    for _ in range(months - 1):
        first = (first - dt.timedelta(days=1)).replace(day=1)
    return first.isoformat(), last.isoformat()


def num(v):
    if v is None:
        return '-'
    a = abs(v)
    if a >= 1e6:
        return f'{v / 1e6:.2f}M'
    if a >= 1e4:
        return f'{v / 1e3:.1f}k'
    if a >= 100:
        return f'{v:.0f}'
    return f'{v:.2f}' if isinstance(v, float) else str(v)


def label(x):
    return x[:10] if isinstance(x, str) and len(x) >= 10 and x[4] == '-' else str(x)


def segments(body):
    return ((body or {}).get('data') or {}).get('segments') or []


def last_value(s):
    v = s.get('values') or []
    return (v[-1].get('value') or 0) if v else 0


def show(title, cmd, body, err, names=None, conv=False, top=None, cols=None):
    """Print one read. Returns its segments (empty on failure).

    `top` prints the largest groups and sums the rest into one line, so a total over every group
    stays visible; `cols` keeps the first periods of a non-date axis (retention, LTV)."""
    print(f'\n## {title}\n   adapty {cmd}')
    if err:
        print(f'   FAILED: {err}')
        FAILED.append(f'{title}: {err}')
        return []
    segs = segments(body)
    if not segs:
        print('   (no data)')
        return []
    if conv and 'view-paid' in cmd and not NOTED:
        NOTED.append(1)
        print('   view-paid: rate % paid/paywall views. Its paid users include renewals of people already subscribed and\n'
              '   one-time purchases, so they are not new buyers: count those with new subscriptions.')
    xs = [label(p.get('x')) for p in segs[0].get('values') or []]
    dated = bool(xs) and all(len(x) == 10 and x[4] == '-' for x in xs)
    if dated and all(x.endswith('-01') for x in xs):
        xs = [x[:7] for x in xs]
    n = len(xs) if dated or not cols else min(cols, len(xs))
    xs = xs[:n]
    w = 17 if conv else 9
    head = [f'{x:>{w}}' for x in xs]
    if dated and head:
        head[-1] = f'{xs[-1] + "*":>{w}}'
    print('   ' + ' ' * 38 + '  '.join(head))
    total = [s for s in segs if s.get('is_total')]
    rest = sorted((s for s in segs if not s.get('is_total')), key=lambda s: (-last_value(s), -(s.get('value') or 0)))
    shown = rest if not top or len(rest) <= top + 1 else rest[:top]
    few_rows = 0
    for s in total + shown:
        name = (names or {}).get(s.get('key')) or s.get('title') or s.get('key') or '?'
        if conv:
            pts = (s.get('values') or [])[:n]
            if pts and max((p.get('value_to') or 0) for p in pts) < FEW:
                name, few_rows = '~ ' + str(name), few_rows + 1
            cells = [f"{num(p.get('value'))}% {num(p.get('value_to'))}/{num(p.get('value_from'))}" for p in pts]
        else:
            cells = [num(p.get('value')) for p in (s.get('values') or [])[:n]]
        print(f'   {str(name)[:37]:37} ' + '  '.join(f'{c:>{w}}' for c in cells))
    if len(shown) < len(rest) and not conv:
        others = rest[len(shown):]
        sums = [sum((s.get('values') or [{}] * n)[i].get('value') or 0 for s in others) for i in range(n)]
        print(f'   {"+ " + str(len(others)) + " more groups, summed":38}' + '  '.join(f'{num(c):>{w}}' for c in sums))
    if rest:
        live = sum(1 for s in rest if last_value(s))
        print(f'   groups: {len(rest)}, with a value in {xs[-1] if xs else "the last period"}: {live}')
    if conv:
        print('   cells: rate % paid/first step.' + (f' ~ = under {FEW} paid in every period: those rates are noise.'
              ' Give the counts, and do not compare, rank, date or explain a change from them.' if few_rows else ''))
    if conv and dated and total:
        onset(total[0], xs)
    return segs


def onset(seg, xs):
    """Name the peak and the first period after it 15% or more below it, so a fall is dated from the data."""
    v = [(p.get('value') if p.get('value_from') else None) for p in (seg.get('values') or [])][:len(xs)]
    idx = [i for i, x in enumerate(v) if x is not None and i > 0]   # the first period starts mid-history
    if len(idx) < 4:
        return
    paid = [(p.get('value_to') or 0) for p in (seg.get('values') or [])][:len(xs)]
    if sorted(paid[i] for i in idx)[len(idx) // 2] < FEW:
        print(f'   onset: none to name: under {FEW} paid in most periods, so the rate moves by chance.')
        return
    peak = max(idx, key=lambda i: v[i])
    below = next((i for i in idx if i > peak and v[i] < 0.85 * v[peak]), None)
    if below is None:
        print(f'   onset: peak {xs[peak]} {num(v[peak])}%; nothing after it is 15% or more below it')
        return
    print(f'   onset: peak {xs[peak]} {num(v[peak])}%; 15% or more below it since {xs[below]} ({num(v[below])}%), '
          f'now {num(v[idx[-1]])}%.' + (' The peak is the start of this window: the fall may have begun earlier, '
          'read further back before dating it.' if peak == idx[0] else ''))


def read(adapty, app, title, args, names=None, conv=False, top=None, cols=None):
    body, err = cli(adapty, args + ['--app', app])
    return show(title, ' '.join(args), body, err, names, conv, top, cols)


def chart(chart_id, f, t, gb=None, gran='month', filters=()):
    a = ['analytics', 'chart', '--chart', chart_id, '--date-from', f, '--date-to', t, '--granularity', gran]
    a += ['--group-by', gb] if gb else []
    for flt in filters:
        a += ['--filter', flt]
    return a


def conversion(conv_id, f, t, gran='month', filters=()):
    a = ['analytics', 'conversion', '--conversion', conv_id, '--date-from', f, '--date-to', t, '--granularity', gran]
    for flt in filters:
        a += ['--filter', flt]
    return a


def year_over_year(a):
    """The last three full months against the same three a year earlier, by store, and any store launch:
    a six-month window cannot show either."""
    f, t = window(15, a.to)
    reads = [('installs', chart('installs', f, t, 'store')),
             ('new subscriptions', chart('subscriptions_new', f, t, 'store')),
             ('first-payment revenue', chart('revenue', f, t, 'store', filters=['renewal_period=1']))]
    rows, launches = {}, []
    for title, args in reads:
        body, err = cli(a.adapty, args + ['--app', a.app])
        if err:
            FAILED.append(f'year over year, {title}: {err}')
            continue
        for s in segments(body):
            if s.get('key') == NO_DATA or (not s.get('is_total') and s.get('title') == 'No Data'):
                continue
            v = [p.get('value') or 0 for p in s.get('values') or []]
            ms = [label(p.get('x'))[:7] for p in s.get('values') or []]
            if len(v) < 15:
                continue
            name = 'Total' if s.get('is_total') else (s.get('title') or s.get('key'))
            rows.setdefault(name, {})[title] = (sum(v[-3:]), sum(v[:3]))
            if title == 'installs' and not s.get('is_total'):
                for i in range(3, len(v)):
                    before = sum(v[i - 3:i]) / 3
                    if before < 10 and v[i] >= 100:
                        launches.append(f'{name} in {ms[i]} (installs {before:.0f}/month before, {num(v[i])} that month)')
                        break
    if not rows:
        return
    print(f'\n## the last 3 full months against the same 3 months a year earlier, by store ({window(3, a.to)[0][:7]}..{t[:7]} vs {f[:7]}..)')
    for name, d in rows.items():
        cells = []
        for title, _ in reads:
            if title in d:
                now, then = d[title]
                ch = f' {(now / then - 1):+.0%}' if then else ''
                cells.append(f'{title} {num(now)} vs {num(then)}{ch}')
        print(f'   {str(name)[:20]:20} ' + ' | '.join(cells))
    for x in launches:
        print(f'   NOTE: a store launched: {x}. Any before/after across that month mixes in the new store\'s users; '
              'name the launch next to it, and read each store against its own past.')


def main_market(segs):
    total = next((s.get('value') or 0 for s in segs if s.get('is_total')), 0)
    rows = sorted(((s.get('value') or 0, s.get('title')) for s in segs if not s.get('is_total')),
                  key=lambda r: -r[0])
    if not total or not rows:
        return
    shares = [(v / total, t) for v, t in rows]
    top, second = shares[0], (shares[1] if len(shares) > 1 else (0, None))
    is_main = top[0] >= 0.5 or (top[0] >= 0.4 and top[0] >= 5 * second[0])
    print('   shares of the window: ' + ', '.join(f'{t} {s:.0%}' for s, t in shares[:6]))
    print(f'   main market: {top[1]} ({top[0]:.0%})' if is_main else
          f'   main market: none ({top[1]} {top[0]:.0%}, next {second[1]} {second[0]:.0%})')


def name_map(adapty, app, topics):
    names, lists = {}, {}
    for n in topics:
        lists[n] = every_page(adapty, app, n)
        for r in lists[n]:
            names[r.get('id')] = r.get('title') or r.get('name') or r.get('developer_id')
    return names, lists


def audit(a):
    f, t = window(a.months, a.to)
    print(f'# audit {f} .. {t} (the last full month is marked *)')
    names, lists = name_map(a.adapty, a.app, ('placements', 'paywalls', 'flows', 'products', 'segments'))
    print('\n## lists, every page: ' + ', '.join(f'{n} {len(r)}' for n, r in lists.items()))
    print('\n## audiences of every placement, lowest priority first (every placement read)')
    print('   A/B tests: a running one can show below as "A/B test <title>"; name it. Past tests never show, and a '
          'running one may not: never write that no test runs or ran; ask what runs on the placement you would test.')
    for p in lists['placements']:
        print(f"   placement {p.get('title')!r} id {p.get('id')}"
              f"{'' if p.get('is_active', True) else ' (inactive)'}")
        print_audiences(a.adapty, a.app, p.get('id'), names)

    def R(title, args, conv=False, top=None, cols=None):
        return read(a.adapty, a.app, title, args, names, conv, top, cols)
    R('1. revenue, new vs renewal', chart('revenue', f, t, 'renewal_status'))
    R('revenue by store', chart('revenue', f, t, 'store'))
    year_over_year(a)
    R('2. revenue by plan length', chart('revenue', f, t, 'duration'))
    main_market(R('revenue by country', chart('revenue', f, t, 'country'), top=12))
    R('3. installs by country', chart('installs', f, t, 'country'), top=12)
    R('installs by store', chart('installs', f, t, 'store'))
    R('installs by channel', chart('installs', f, t, 'attribution_channel'), top=12)
    R('4. new paid subscriptions by first-payment offer (a converted trial counts as No Offer)',
      chart('subscriptions_new', f, t, 'offer_category'))
    R('new paid subscriptions by plan length', chart('subscriptions_new', f, t, 'duration'))
    R('5. new trials by product (whether a plan has a trial)', chart('trials_new', f, t, 'store_product_id'))
    R('6. endings by reason', chart('subscriptions_expired', f, t, 'cancellation_reason'))
    R('7. refunds by country', chart('refund_money', f, t, 'country'), top=12)
    placements = R('8. new subscriptions by placement', chart('subscriptions_new', f, t, 'placement_id'))
    R('new subscriptions by paywall', chart('subscriptions_new', f, t, 'paywall_id'))
    wf = (dt.date.fromisoformat(t) - dt.timedelta(days=27)).isoformat()
    R('new subscriptions per week by placement, the last 4 weeks (the count a Time line uses)',
      chart('subscriptions_new', wf, t, 'placement_id', 'week'))
    for c in ('install-trial', 'trial-paid', 'install-paid', 'view-paid'):
        R(f'9. conversion {c}', conversion(c, f, t), conv=True)
    R('11. retention by plan length', ['analytics', 'retention', '--date-from', f, '--date-to', t,
                                         '--group-by', 'duration'], cols=13)
    lf, lt = window(6, (dt.date.fromisoformat(t) - dt.timedelta(days=364)).isoformat())
    R(f'12. LTV by plan length, by day, cohorts {lf[:7]}..{lt[:7]}: every plan has reached day 365, so the plans compare',
      ['analytics', 'ltv', '--date-from', lf, '--date-to', lt, '--group-by', 'duration',
       '--period-type', 'days', '--renewal-days', '30,90,180,365'])
    for s in placements:
        if s.get('is_total') or s.get('key') in (None, NO_DATA) or not last_value(s):
            continue
        R(f"13. view-paid on {names.get(s['key']) or s.get('title')}",
          conversion('view-paid', f, t, filters=[f"placement_id={s['key']}"]), conv=True)
    paywall_map(a, names, lists['placements'])
    print('\nNext, for every placement a hypothesis would run on: reads.py placement --placement <id>')


def paywall_map(a, names, placements):
    """Which paywalls sold on which placements, month by month, over 13 months: a promo, a test or an offer
    can run on a placement other than the one you looked at."""
    f, t = window(13, a.to)
    by_pw = {}
    print(f'\n## paywalls that sold, by placement, {f[:7]}..{t[:7]} (every placement with a sale read)')
    body, err = cli(a.adapty, chart('subscriptions_new', f, t, 'placement_id') + ['--app', a.app])
    sold = {s.get('key') for s in segments(body) if not s.get('is_total') and s.get('value')} if not err else None
    for p in placements:
        if sold is not None and p.get('id') not in sold:
            continue
        body, err = cli(a.adapty, chart('subscriptions_new', f, t, 'paywall_id', filters=[f"placement_id={p.get('id')}"])
                        + ['--app', a.app])
        if err:
            FAILED.append(f"paywalls on {p.get('title')}: {err}")
            continue
        segs = [s for s in segments(body) if not s.get('is_total') and s.get('value')]
        if not segs:
            continue
        print(f"   {p.get('title')}:")
        for s in sorted(segs, key=lambda s: -(s.get('value') or 0)):
            months = [label(x.get('x'))[:7] for x in s.get('values') or [] if x.get('value')]
            name = names.get(s.get('key')) or s.get('title') or s.get('key')
            span = months[0] if len(months) == 1 else f'{months[0]}..{months[-1]}'
            print(f"      {str(name)[:60]:60} {num(s.get('value')):>7}  {span}")
            if s.get('key') not in (None, NO_DATA):
                by_pw.setdefault(name, []).append(p.get('title'))
    shared = {k: v for k, v in by_pw.items() if len(v) > 1}
    for k, v in shared.items():
        print(f'   NOTE: "{k}" sold on {len(v)} placements: {", ".join(map(str, v))}. A promo or test on one of them '
              'may also run on the others.')


def series(segs, key=None):
    s = next((x for x in segs if (x.get('is_total') if key is None else x.get('key') == key)), None)
    return [(label(p.get('x'))[:7], p) for p in (s or {}).get('values') or []]


def started_stopped(segs, months):
    out = []
    for s in segs:
        if s.get('is_total'):
            continue
        v = [p.get('value') or 0 for p in s.get('values') or []]
        tot = sum(v)
        if not tot or len(v) != len(months):
            continue
        on = [i for i, x in enumerate(v) if x >= 0.05 * max(v)]
        if on and on[0] > 1:
            out.append((months[on[0]], f"{s.get('title')} started"))
        if on and on[-1] < len(v) - 1:
            out.append((months[on[-1] + 1], f"{s.get('title')} stopped"))
    return out


def switch_report(names, months, sh, conv, whole, old, new, products=(), store=None):
    o, n = sh[old], sh[new]
    print(f'\n## switch: {names.get(old, old)} -> {names.get(new, new)}, store {store or "all"}')
    print('   share of the placement\'s purchases, old/new: ' +
          '  '.join(f'{m} {o[i]:.0%}/{n[i]:.0%}' for i, m in enumerate(months)))
    ro = {m: p.get('value') for m, p in conv.get(old, []) if p.get('value_from')}
    rn = {m: p.get('value') for m, p in conv.get(new, []) if p.get('value_from')}
    # the window's first month is left out: a conversion read starting mid-history inflates it
    carried = [m for i, m in enumerate(months) if i and o[i] >= 0.3 and m in ro]
    if carried:
        print('   old view-paid while it carried the placement: ' + '  '.join(f'{m} {num(ro[m])}%' for m in carried))
        peak = max(range(1, len(months)), key=lambda i: o[i])
        fall = next((i for i in range(peak, len(months)) if o[i] < 0.8 * o[peak]), len(months))
        pre = [months[i] for i in range(max(1, fall - 3), fall) if months[i] in ro]
        if pre:
            lvl = sum(ro[m] for m in pre) / len(pre)
            low = min(carried, key=lambda m: ro[m])
            print(f'   old level before its share fell ({pre[0]}..{pre[-1]}): {num(lvl)}%; '
                  f'its lowest month while carrying: {num(ro[low])}% ({low})')
    for i, m in enumerate(months):
        if o[i] >= 0.05 and n[i] >= 0.05 and m in ro and m in rn and ro[m]:
            print(f'   both selling in {m}: old {num(ro[m])}%, new {num(rn[m])}%, new/old {rn[m] / ro[m]:.2f}')
    after = [m for m in months[-3:] if m in rn]
    if after:
        print('   new view-paid, the last 3 full months: ' + '  '.join(f'{m} {num(rn[m])}%' for m in after))
    w = [(m, p.get('value')) for m, p in whole if p.get('value_from')][1:]
    if w:
        print('   whole placement view-paid: ' + '  '.join(f'{m} {num(v)}%' for m, v in w))
        if w[0][1] and w[-1][1] < 0.85 * w[0][1]:
            print(f'   THE WHOLE PLACEMENT FELL, {w[0][0]} {num(w[0][1])}% -> {w[-1][0]} {num(w[-1][1])}%: '
                  'say so next to the before/after; a better new paywall does not mean the placement got better.')
    sw = next((i for i in range(len(months)) if n[i] >= 0.05), None)
    near = [(m, x) for m, x in started_stopped(products, months)
            if sw is not None and abs(months.index(m) - sw) <= 1]
    if near:
        print('   other changes on this placement in the same months: ' + '; '.join(f'{x} ({m})' for m, x in near))
    print('   Size the change against the old level before its fall and the month both sold, never the old\n'
          '   lowest month. Before/after is not an A/B test: name every other change in the same months.')


def print_audiences(adapty, app, pid, names):
    body, err = cli(adapty, ['placements', 'get', pid, '--app', app])
    if err:
        print(f'   FAILED: {err}')
        FAILED.append(f'placements get {names.get(pid, pid)}: {err}')
        return
    aud = sorted((body.get('data') or body).get('audiences') or [], key=lambda x: x.get('priority', 0))
    for x in aud:
        segs = [names.get(s, s) for s in x.get('segment_ids') or []] or ['All users']
        if x.get('content_type') == 'ab_test' or x.get('ab_test_id'):
            target = f"A/B test {x.get('ab_test_title') or x.get('ab_test_id')}"
        else:
            cid = x.get('paywall_id') or x.get('flow_id')
            target = names.get(cid, cid)
        print(f"   {x.get('priority'):>3}  {' + '.join(map(str, segs))[:64]:64} -> {target}")
    tests = sorted({x.get('ab_test_title') or x.get('ab_test_id') for x in aud
                    if x.get('content_type') == 'ab_test' or x.get('ab_test_id')})
    if tests:
        print(f"   NOTE: an A/B test runs on this placement now: {', '.join(map(str, tests))}. Name it, compare "
              'nothing on this placement as before/after across its start, and ask its result before suggesting '
              'another test on these audiences.')
    if aud and all(x.get('segment_ids') for x in aud):
        print('   no All users audience: users outside these segments see nothing here, or an A/B test is hidden')


def placement(a):
    f, t = window(a.months, a.to)
    pid, flt = a.placement, [f'placement_id={a.placement}']
    print(f'# placement {pid}, {f} .. {t} (the last full month is marked *)')
    names, _ = name_map(a.adapty, a.app, ('placements', 'paywalls', 'flows', 'segments'))
    print(f"\n## audiences of {names.get(pid, pid)}, lowest priority first")
    print('   A/B tests: a running one can show below as "A/B test <title>"; name it. Past tests never show, and a '
          'running one may not: never write that no test runs or ran; ask what runs on the placement you would test.')
    print_audiences(a.adapty, a.app, pid, names)

    def R(title, args, conv=False):
        return read(a.adapty, a.app, title, args, names, conv)
    store_segs = R('revenue on this placement by store', chart('revenue', f, t, 'store', filters=flt))
    rev = sum(s.get('value') or 0 for s in store_segs if not s.get('is_total'))
    stores = [s.get('key') for s in sorted((s for s in store_segs if not s.get('is_total')), key=lambda s: -(s.get('value') or 0))
              if s.get('key') and rev and (s.get('value') or 0) >= 0.15 * rev] or [None]
    wf = (dt.date.fromisoformat(t) - dt.timedelta(days=27)).isoformat()
    R('new subscriptions per week on this placement, the last 4 weeks (the count a Time line uses)',
      chart('subscriptions_new', wf, t, gran='week', filters=flt))
    R('new trials per week on this placement, the last 4 weeks', chart('trials_new', wf, t, gran='week', filters=flt))
    products = R('new subscriptions on this placement by product', chart('subscriptions_new', f, t, 'store_product_id', filters=flt))
    contents = []
    for gb in ('paywall_id', 'flow_id'):
        segs = R(f'new subscriptions on this placement by {gb}, every one that sold', chart('subscriptions_new', f, t, gb, filters=flt))
        if any(not s.get('is_total') and s.get('key') not in (None, NO_DATA) and s.get('value') for s in segs):
            contents.append((gb, segs))
    # the same per store: a paywall can sell in one store only, or leak into a store its name excludes
    every_store = [s.get('key') for s in store_segs if not s.get('is_total') and s.get('key')][:3]
    for gb, _ in contents:
        for store in every_store:
            segs = R(f'new subscriptions on this placement by {gb}, store {store}',
                     chart('subscriptions_new', f, t, gb, filters=flt + [f'store={store}']))
            other = {'app_store': ('android', 'google', 'play'), 'play_store': ('ios', 'iphone', 'apple', 'app store')}.get(store, ())
            for s in segs:
                name = str(s.get('title') or '')
                if s.get('is_total') or not s.get('value') or not any(w in name.lower() for w in other):
                    continue
                months = [f"{label(p.get('x'))[:7]} {p.get('value')}" for p in s.get('values') or [] if p.get('value')]
                print(f'   NOTE: "{name}" names another platform but sold {num(s.get("value"))} in {store}: '
                      + ', '.join(months) + '. Say so; it may be shown to users it was not meant for.')
    def conv_read(title, filters):
        b, e = cli(a.adapty, conversion('view-paid', f, t, filters=filters) + ['--app', a.app])
        return series(show(title, ' '.join(conversion('view-paid', f, t, filters=filters)), b, e, names, True))
    for gb, segs in contents:
        total = next((s for s in segs if s.get('is_total')), None)
        tv = [p.get('value') or 0 for p in (total or {}).get('values') or []]
        months = [label(p.get('x'))[:7] for p in (total or {}).get('values') or []]
        sh = {s['key']: [(p.get('value') or 0) / y if y else 0 for p, y in zip(s.get('values') or [], tv)]
              for s in segs if not s.get('is_total') and s.get('key') not in (None, NO_DATA)}
        big = sorted((k for k, v in sh.items() if max(v or [0]) >= 0.05), key=lambda k: -max(sh[k]))[:8]
        pairs = [(o, n) for o in big if max(sh[o]) >= 0.3 and sh[o][-1] < 0.1
                 for n in big if n != o and sh[n][0] < 0.1 and sh[n][-1] >= 0.3]
        # every paywall that sold in the main store; in the other stores, only the ones in a switch
        for i, store in enumerate(stores):
            sflt = flt + ([f'store={store}'] if store else [])
            keys = big if i == 0 else sorted({k for pair in pairs for k in pair})
            if i and not keys:
                continue
            whole = conv_read(f'view-paid on this placement, store {store or "all"}', sflt)
            conv = {k: conv_read(f'view-paid of {names.get(k, k)}, store {store or "all"}', sflt + [f'{gb}={k}'])
                    for k in keys}
            for old, new in pairs:
                switch_report(names, months, sh, conv, whole, old, new, products, store)


def run():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('command', choices=('audit', 'placement'))
    ap.add_argument('--app', required=True)
    ap.add_argument('--adapty', default='adapty', help='the resolved $ADAPTY command string')
    ap.add_argument('--placement')
    ap.add_argument('--months', type=int)
    ap.add_argument('--to', help='YYYY-MM-DD; the window ends with the last full month before it')
    a = ap.parse_args()
    if a.command == 'placement' and not a.placement:
        ap.error('placement needs --placement <PLACEMENT_ID>')
    a.months = a.months or (6 if a.command == 'audit' else 12)
    (audit if a.command == 'audit' else placement)(a)
    if FAILED:
        print('\n## could not read: say so in the reply, and what it leaves open')
        for x in FAILED:
            print('   ' + x)
    return 0


if __name__ == '__main__':
    sys.exit(run())
