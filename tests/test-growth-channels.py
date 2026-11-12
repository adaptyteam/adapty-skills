"""growth-advisor's paid-vs-organic trial gate, driven offline: `reads.py`'s `channels()`.

Paid vs organic is the `attribution_status` dimension: `non_organic`, `organic`, and No Data (`""`), which
counts as neither. `trials_new` grouped by it gives the share; `conversion trial-paid` filtered to each status
gives the rates. The gate fires at 30%+ paid trials and paid trial → paid 5+ points below organic.
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


def run(trials, rates, keyed=True, bases=None):
    """trials: {status_key: count}; rates: {status_value: trial-paid %}."""
    def fake(_adapty, args):
        if args[:2] == ['analytics', 'chart']:
            segs = [{'key': k if keyed else None, 'title': {'non_organic': 'Non Organic', 'organic': 'Organic', '': 'No Data'}[k],
                     'value': v} for k, v in trials.items()]
            return {'data': {'segments': [{'key': None, 'title': 'Total', 'is_total': True,
                                           'value': sum(trials.values())}] + segs}}, None
        if args[:2] == ['analytics', 'conversion']:
            flt = [args[i + 1] for i, x in enumerate(args) if x == '--filter']
            st = next(x.split('=', 1)[1] for x in flt if x.startswith('attribution_status='))
            return {'data': {'value': rates.get(st), 'value_from': (bases or {}).get(st, 500)}}, None
        return None, f'unexpected call {args}'
    reads.run_read = fake
    reads._CALLS.clear()
    reads.FAILED.clear()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        r = reads.channels(argparse.Namespace(adapty='fake', app='app'), '2026-05-01', '2026-10-31')
    return r, out.getvalue()


def test_channels_fire():
    r, out = run({'non_organic': 400, 'organic': 500, '': 100}, {'non_organic': 12.0, 'organic': 27.0})
    check('fires at 40% paid and 15 points below organic', r and r['fires'], r)
    check('paid share counts No Data in the total', r and abs(r['paid_share'] - 0.4) < 1e-9, r)
    check('prints the gate line', 'FEATURE GATE: trial still active' in out, out)


def test_channels_quiet():
    r, out = run({'non_organic': 200, 'organic': 800}, {'non_organic': 12.0, 'organic': 27.0})
    check('quiet at 20% paid', r and not r['fires'], r)
    check('no gate line when quiet', 'FEATURE GATE' not in out, out)
    r2, _ = run({'non_organic': 500, 'organic': 500}, {'non_organic': 24.0, 'organic': 27.0})
    check('quiet when paid is under 5 points below organic', r2 and not r2['fires'], r2)


def test_titles_without_keys():
    r, _ = run({'non_organic': 400, 'organic': 500, '': 100}, {'non_organic': 12.0, 'organic': 27.0}, keyed=False)
    check('groups matched by title when keys differ', r and r['fires'], r)


def test_small_numbers_quiet():
    r, out = run({'non_organic': 4, 'organic': 6}, {'non_organic': 0.0, 'organic': 33.0},
                 bases={'non_organic': 4, 'organic': 6})
    check('under 20 trials a side never fires', not (r and r['fires']), r)


def test_no_data_only():
    r, out = run({'': 1000}, {})
    check('every trial No Data: None', r is None, r)
    check('nothing graded printed', 'FEATURE GATE' not in out and 'paid' not in out.split('\n', 2)[-1], out)


for t in (test_channels_fire, test_channels_quiet, test_titles_without_keys, test_small_numbers_quiet, test_no_data_only):
    try:
        t()
    except Exception as e:
        check(t.__name__, False, f'{type(e).__name__}: {e}')
print(f'\n{len(failures)} failure(s)')
sys.exit(1 if failures else 0)
