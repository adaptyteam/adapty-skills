"""growth-advisor's `reads.py` printers, driven offline: `show()` on conversion and chart answers, and the
name fallbacks. A rate above 100% is flagged in both shapes of answer and dates nothing; a period after the
window's end is never starred or read; a row with no name prints its id. Ids and numbers are made up.
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


def shown(cmd, body, conv=True):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        reads.show('t', cmd, body, None, conv=conv)
    return out.getvalue()


CONV = 'analytics conversion --conversion view-paid --date-from 2025-01-01 --date-to 2025-06-30 --granularity month'
MONTHS = ['2025-01-01', '2025-02-01', '2025-03-01', '2025-04-01', '2025-05-01', '2025-06-01']


def pts(rates, months=MONTHS):
    return [{'x': m, 'value': r, 'value_to': 400, 'value_from': 1000} for m, r in zip(months, rates)]


# a: the whole-window answer, one value per group
text = shown(CONV, {'data': {'segments': [{'key': 'ios', 'title': 'App Store', 'value': 140.0},
                                          {'key': 'and', 'title': 'Google Play', 'value': 4.0}]}})
check('a whole-window rate above 100% is flagged', '! App Store' in text and 'Leave those rows out' in text, text)
check('a whole-window rate under 100% is not', '! Google Play' not in text, text)

# a: no onset on a total above 100%
total = {'key': 'total', 'is_total': True, 'values': pts([40, 41, 42, 130, 30, 30])}
text = shown(CONV, {'data': {'segments': [total]}})
check('a total above 100% is flagged', '! total' in text, text)
check('a total above 100% gets no onset', 'onset' not in text, text)
text = shown(CONV, {'data': {'segments': [dict(total, values=pts([40, 41, 42, 43, 30, 30]))]}})
check('a valid total still gets its onset', 'onset: peak 2025-04' in text, text)

# b: a partial bucket after the window's end
late = pts([40, 41, 42, 43, 44, 45, 99], MONTHS + ['2025-07-01'])
text = shown(CONV, {'data': {'segments': [dict(total, values=late)]}})
check('the window end is starred, not the partial month after it', '2025-06*' in text and '2025-07' not in text, text)
check('the partial month is never read', '99' not in text, text)
CHART = 'analytics chart --chart revenue --date-from 2025-01-01 --date-to 2025-06-30 --granularity month'
seg = {'key': 'x', 'title': 'App Store', 'values': [{'x': m, 'value': 10} for m in MONTHS] + [{'x': '2025-07-01', 'value': 0}]}
text = shown(CHART, {'data': {'segments': [seg]}}, conv=False)
check('a group live in the last full month counts as live', 'with a value in 2025-06: 1' in text, text)

# c: no name falls back to the id
ID = '00000000-0000-4000-8000-0000000000f1'
reads.prefetch = lambda *_a: None
reads.every_page = lambda _ad, _app, _n: [{'id': ID, 'title': '', 'name': None, 'developer_id': ''}]
names, _ = reads.name_map('adapty', 'app', ['flows'])
check('a row with no title, name or developer id is named by its id', names.get(ID) == ID, names)
reads.shown_on = lambda *_a: {}
reads.lifetime = lambda *_a: {}
out = io.StringIO()
with contextlib.redirect_stdout(out):
    reads.flows_reach(argparse.Namespace(), {}, [{'id': ID, 'name': None, 'status': 'published'}], [], [])
check('a flow with no name prints its id', ID in out.getvalue() and 'None' not in out.getvalue(), out.getvalue())

if failures:
    print(f'\n{len(failures)} failed')
    sys.exit(1)
print('\nall passed')
