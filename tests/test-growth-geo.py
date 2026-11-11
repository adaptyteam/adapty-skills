"""growth-advisor's top-countries block, driven offline: `reads.py`'s `geo()` against fixture answers.

Country keys are ISO codes as charts give them; conversions are read per country with `--filter country=`
and `--filter store=` (App Store), and their `data.value` is the rate in percent. Grades come from
`market-grid.csv` next to `reads.py`. Numbers are made up.
"""
import argparse
import contextlib
import importlib.util
import io
import pathlib
import sys

sys.dont_write_bytecode = True

ROOT = pathlib.Path(__file__).resolve().parent.parent
READS = ROOT / 'plugin' / 'skills' / 'growth-advisor' / 'references' / 'reads.py'
spec = importlib.util.spec_from_file_location('reads', READS)
reads = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reads)

failures = []


def check(label, ok, detail=''):
    print(f'{"ok  " if ok else "FAIL"}  {label}' + (f'  -- {detail}' if detail and not ok else ''))
    if not ok:
        failures.append(label)


def seg(code, title, value):
    return {'key': code, 'title': title, 'value': value, 'values': [{'x': '2026-10-01', 'value': value}]}


def total(rows):
    return [{'key': None, 'title': 'Total', 'is_total': True, 'value': sum(r['value'] for r in rows)}] + rows


REVENUE = total([seg('US', 'United States', 50000), seg('GB', 'United Kingdom', 9000), seg('DE', 'Germany', 7000),
                 seg('FR', 'France', 5000), seg('CA', 'Canada', 4000), seg('BR', 'Brazil', 900),
                 seg('JP', 'Japan', 800)])
INSTALLS = total([seg('US', 'United States', 40000), seg('BR', 'Brazil', 30000), seg('JP', 'Japan', 20000),
                  seg('GB', 'United Kingdom', 6000), seg('DE', 'Germany', 5000), seg('FR', 'France', 4000),
                  seg('CA', 'Canada', 3000)])
RATES = {('trial-paid', 'JP'): 1.0, ('trial-paid', 'US'): 90.0}
BASES = {}
COUNTRY_VALUES = [('US', 'United States'), ('GB', 'United Kingdom'), ('DE', 'Germany'), ('FR', 'France'),
                  ('CA', 'Canada'), ('BR', 'Brazil'), ('JP', 'Japan')]


def run(stores=('app_store',), category='Productivity'):
    def fake(_adapty, args):
        if args[:3] == ['analytics', 'values', '--dimension'] and args[3] == 'country':
            return {'data': [{'value': 'v-' + c, 'label': t} for c, t in COUNTRY_VALUES]}, None
        if args[:3] == ['analytics', 'values', '--dimension'] and args[3] == 'store':
            labels = {'app_store': 'App Store', 'play_store': 'Google Play'}
            return {'data': [{'value': s, 'label': labels[s]} for s in stores]}, None
        if args[:2] == ['analytics', 'conversion']:
            conv = args[args.index('--conversion') + 1]
            flt = [args[i + 1] for i, x in enumerate(args) if x == '--filter']
            code = next(x.split('=', 1)[1] for x in flt if x.startswith('country='))
            if not code.startswith('v-'):
                return None, f'not a filter value: {code}'
            code = code[2:]
            return {'data': {'value': RATES.get((conv, code), 30.0 if conv == 'trial-paid' else 1.5),
                             'value_from': BASES.get((conv, code), 1000)}}, None
        return None, f'unexpected call {args}'
    reads.run_read = fake
    reads._CALLS.clear()
    reads.FAILED.clear()
    a = argparse.Namespace(adapty='fake', app='app', to=None, category=category)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rows = reads.geo(a, REVENUE, INSTALLS, '2026-05-01', '2026-10-31')
    return rows, out.getvalue()


def test_top_countries():
    rows, _ = run()
    codes = [r['country'] for r in rows]
    check('top countries: top 5 by revenue plus low-rpi install countries', set(codes) == {'US', 'GB', 'DE', 'FR', 'CA', 'BR', 'JP'}, codes)
    low = {r['country'] for r in rows if r['low_rpi']}
    check('BR and JP flagged low revenue per install', low == {'BR', 'JP'}, low)


def test_grade():
    rows, _ = run()
    by = {r['country']: r for r in rows}
    check('JP trial-paid below the APAC p25 is weak', by['JP']['trial_paid_grade'] == 'weak', by['JP'])
    check('US trial-paid above the US p75 is strong', by['US']['trial_paid_grade'] == 'strong', by['US'])
    check('Canada has no region row: no grade', by['CA']['region'] is None and by['CA']['trial_paid_grade'] is None, by['CA'])


def test_category_fallback():
    row = reads.grid_row('trial-paid', 'Weekly', 'MEA', 'No Such Category')
    check('a category with no row falls back to All categories', row and row['category_used'] == 'All categories', row)


def test_google_play_only():
    rows, out = run(stores=('play_store',))
    check('Google Play only: no grades', all(r['trial_paid_grade'] is None and r['view_paid_grade'] is None for r in rows))
    check('Google Play only: says why', 'no median: Google Play' in out, out[:300])


def test_print():
    _, out = run()
    lines = [l for l in out.splitlines() if l.startswith('   ') and ' rpi ' in l]
    check('block heading', out.lstrip().startswith('## top countries:'), out[:120])
    check('one line per country', len(lines) == 7, len(lines))
    jp = next((l for l in lines if l.split()[0] == 'JP'), '')
    check('a line carries rpi, both rates, the grade and the language', all(x in jp for x in ('rpi', 'view-paid', 'trial-paid', 'weak', 'ja')), jp)
    check('revenue per install is never graded', not any('rpi weak' in l or 'rpi strong' in l for l in lines))


def test_small_base_not_graded():
    BASES[('trial-paid', 'JP')] = 5
    try:
        rows, _ = run()
    finally:
        BASES.clear()
    jp = next(r for r in rows if r['country'] == 'JP')
    check('a rate on under 20 trials is not graded', jp['trial_paid_grade'] is None, jp)


def test_zero_revenue_not_top():
    global REVENUE
    keep = REVENUE
    REVENUE = total([seg('US', 'United States', 900), seg('GE', 'Georgia', 0), seg('NO', 'Norway', 0)])
    try:
        rows, _ = run()
    finally:
        REVENUE = keep
    codes = {r['country'] for r in rows}
    check('a country with no revenue is not a revenue leader', 'NO' not in codes and 'GE' not in codes, codes)


def test_all_plans_row():
    rows, out = run()
    jp = next(r for r in rows if r['country'] == 'JP')
    check('rates across plans are graded against the All plans row', jp['plan_used'] == 'All plans', jp)
    check('the filter value comes from analytics values', not reads.FAILED, reads.FAILED)


for t in (test_all_plans_row, test_small_base_not_graded, test_zero_revenue_not_top, test_top_countries, test_grade, test_category_fallback, test_google_play_only, test_print):
    try:
        t()
    except Exception as e:  # a missing function is a failure, not a crash of the whole file
        check(t.__name__, False, f'{type(e).__name__}: {e}')
print(f'\n{len(failures)} failure(s)')
sys.exit(1 if failures else 0)
