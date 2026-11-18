"""A countdown to a date: flowkit.timer(end_date=...) and verify-config's publish-refusal check.

Repo-only. The schema keeps `endDate.date` optional so a builder draft saves without one;
publish refuses an `until_date` timer with no date, or with a date, time or zone that is not
valid. A past date is valid.

    python3 tests/test-timer-until-date.py
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk  # noqa: E402

fails = []

def check(name, ok, detail=''):
    print(('  ok    ' if ok else '  FAIL  ') + name + ('' if ok else f'  {detail}'))
    if not ok:
        fails.append(name)

def raises(fn):
    try:
        fn()
    except ValueError as e:
        return str(e)
    return None

# --- flowkit -----------------------------------------------------------------------------
end = fk.timer_end_date('2026-11-28', '23:59', time_zone='Europe/Berlin')
check('end date shape', end == {'date': '2026-11-28', 'time': '23:59', 'timeZone': 'Europe/Berlin'}, end)
digits = fk.timer_digits(('days', 'hours', 'minutes', 'seconds'))
t = fk.timer([digits], end_date=end)
check('until_date behavior', t['props']['behavior'] == 'until_date', t['props'].get('behavior'))
check('endDate stored', t['props'].get('endDate') == end, t['props'].get('endDate'))
check('local time zone', fk.timer_end_date('2026-11-28', time_zone='local')['timeZone'] == 'local')
check('UTC zone', fk.timer_end_date('2026-11-28', '00:00', time_zone='UTC')['timeZone'] == 'UTC')
check('past date is valid', fk.timer_end_date('2020-01-01', time_zone='UTC')['date'] == '2020-01-01')
check('duration timer has no endDate', 'endDate' not in fk.timer([digits], minutes=5)['props'])
check('RAISES: no zone', raises(lambda: fk.timer_end_date('2026-11-28', time_zone=None)) is not None)
check('RAISES: unknown zone', raises(lambda: fk.timer_end_date('2026-11-28', time_zone='Mars/Base')) is not None)
check('RAISES: date not on the calendar', raises(lambda: fk.timer_end_date('2026-02-30', time_zone='UTC')) is not None)
check('RAISES: bad time', raises(lambda: fk.timer_end_date('2026-11-28', '24:00', time_zone='UTC')) is not None)
check('RAISES: bad date form', raises(lambda: fk.timer_end_date('28.11.2026', time_zone='UTC')) is not None)
check('RAISES: until_date with no end', raises(lambda: fk.timer([digits], behavior='until_date')) is not None)
check('RAISES: end and duration together', raises(lambda: fk.timer([digits], minutes=5, end_date=end)) is not None)

# --- verify-config -----------------------------------------------------------------------
def run(doc):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(doc, f)
    r = subprocess.run([sys.executable, VERIFY, f.name], capture_output=True, text=True)
    os.unlink(f.name)
    if r.returncode == 2:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout

def doc(end_date, in_component=False):
    props = {'customId': 'sale', 'behavior': 'until_date',
             'duration': {'days': 0, 'hours': 0, 'minutes': 0, 'seconds': 0}}
    if end_date is not None:
        props['endDate'] = end_date
    m = {'el_t': {'id': 'el_t', 'type': 'timer', 'states': [], 'props': props}}
    scr_map, comps = ({}, {'cmp_a': {'map': m, 'hierarchy': {'id': 'root', 'children': [{'id': 'el_t'}]}}}) \
        if in_component else (m, {})
    h = {'id': 'root', 'children': [] if in_component else [{'id': 'el_t'}]}
    return {'schemaVersion': 13, 'variables': [], 'components': comps,
            'theme': {'colors': [], 'typography': []},
            'localization': {'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}], 'defaultLocale': 'en', 'content': {}},
            '_meta': {'icons': [], 'fonts': [], 'screens': {}},
            'screens': [{'id': 'scr_a', 'elements': {'map': scr_map, 'hierarchy': h}, 'props': {}}]}

MSG = 'publish refuses the flow'
check('FIRES: no endDate', MSG in run(doc(None)))
check('FIRES: no date', MSG in run(doc({'time': '23:59', 'timeZone': 'UTC'})))
check('FIRES: date not on the calendar', MSG in run(doc({'date': '2026-02-30', 'time': '23:59', 'timeZone': 'UTC'})))
check('FIRES: bad time', MSG in run(doc({'date': '2026-11-28', 'time': '7pm', 'timeZone': 'UTC'})))
check('FIRES: unknown zone', MSG in run(doc({'date': '2026-11-28', 'time': '23:59', 'timeZone': 'Mars/Base'})))
check('FIRES: in a component', MSG in run(doc(None, in_component=True)))
check('SILENT: full end, named zone', MSG not in run(doc(end)))
check('SILENT: local time', MSG not in run(doc({'date': '2026-11-28', 'time': '23:59', 'timeZone': 'local'})))
check('SILENT: past date', MSG not in run(doc({'date': '2020-01-01', 'time': '00:00', 'timeZone': 'UTC'})))
print()
if fails:
    print(f'{len(fails)} FAILED'); sys.exit(1)
print('all passed')
