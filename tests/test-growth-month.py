"""growth-advisor's audit and the month still running, driven offline: `reads.py`'s `month_in_progress()`.

Every audit read ends with the last full month. An app or a placement that went live this month shows
nothing there, so the audit says so first, with the range to read again. Chart answers follow the shape of
`analytics chart --json`: `data.segments[]`, the total group marked `is_total`, its months under `values`.
Numbers are made up.
"""
import argparse
import contextlib
import importlib.util
import io
import pathlib
import sys

sys.dont_write_bytecode = True

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent)
READS = ROOT / 'plugin' / 'skills' / 'growth-advisor' / 'references' / 'reads.py'
spec = importlib.util.spec_from_file_location('reads', READS)
reads = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reads)

failures = []


def check(label, ok, detail=''):
    print(f'{"ok  " if ok else "FAIL"}  {label}' + (f'  -- {detail}' if detail and not ok else ''))
    if not ok:
        failures.append(label)


def answer(months):
    return {'data': {'segments': [{'title': 'Total', 'is_total': True,
                                   'values': [{'x': m, 'value': v} for m, v in months]}]}}


def run(window, now, to='2026-11-26'):
    """`window` and `now` map a chart id to its answer's months over the window and over this month."""
    def fake(_adapty, args):
        cid = args[args.index('--chart') + 1]
        frm = args[args.index('--date-from') + 1]
        return answer((now if frm.endswith('-11-01') else window).get(cid, [])), None
    reads._CALLS.clear()
    reads.run_read = fake
    a = argparse.Namespace(adapty='adapty', app='app', to=to, months=6)
    f, t = reads.window(a.months, a.to)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = reads.month_in_progress(a, f, t)
    return r, buf.getvalue()


def test_new_app_says_so():
    r, out = run({'installs': [('2026-10-01', 12)], 'revenue': [('2026-10-01', 0)]},
                 {'installs': [('2026-11-01', 900)], 'revenue': [('2026-11-01', 450.0)]})
    check('more installs this month than the window: a NOTE', 'NOTE' in out and 'installs (900)' in out, out)
    check('the NOTE names revenue too', 'revenue (450)' in out, out)
    check('the NOTE gives the range to read again', '--date-from 2026-11-01 --date-to 2026-11-26' in out, out)


def test_settled_app_quiet():
    r, out = run({'installs': [('2026-0%d-01' % m, 1000) for m in range(5, 10)] + [('2026-10-01', 1000)],
                  'revenue': [('2026-10-01', 5000.0)]},
                 {'installs': [('2026-11-01', 800)], 'revenue': [('2026-11-01', 4000.0)]})
    check('a month in progress smaller than the window: quiet', 'NOTE' not in out, out)
    check('it compared both', r == {'installs': (6000, 800), 'revenue': (5000.0, 4000.0)}, r)


def test_first_of_month():
    r, out = run({}, {'installs': [('2026-11-01', 5)]}, to='2026-11-01')
    check('on the first of a month nothing is read', r is None and out == '', (r, out))


for t in (test_new_app_says_so, test_settled_app_quiet, test_first_of_month):
    try:
        t()
    except Exception as e:
        check(t.__name__, False, f'{type(e).__name__}: {e}')
print(f'\n{len(failures)} failure(s)')
sys.exit(1 if failures else 0)
