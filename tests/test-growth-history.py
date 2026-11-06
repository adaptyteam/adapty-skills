"""growth-advisor's past A/B tests, driven offline: `reads.py`'s `ab_tests()` against fixture answers.

The fixtures follow the shapes of real answers: `placements metrics get --based-on audience` keeps every
content an audience showed, each with its `started_at` and `stopped_at`, a test as an `ab_test` node with its
arms under it. A paywall node has a `paywall` object and its products under it (`product_id`, `product_set`);
a flow node has no flow id: it is `level: variation` with a `variation_id` and the flow's name as its `title`,
its numbers and `probability`, and the screens and products under it. `ab-tests metrics list` answers a row
per test with its arms under `items`. Ids and names are made up.
"""
import argparse
import contextlib
import datetime
import importlib.util
import io
import pathlib
import re
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


APP = '00000000-0000-4000-8000-0000000000aa'
PID = '00000000-0000-4000-8000-0000000000b1'
AUD = '00000000-0000-4000-8000-0000000000c1'
A, B, C = ('00000000-0000-4000-8000-00000000000a', '00000000-0000-4000-8000-00000000000b',
           '00000000-0000-4000-8000-00000000000c')
NAMES = {A: 'Monthly first', B: 'Annual first', C: 'Seasonal', PID: 'onboarding'}
_DAY = datetime.date.today() - datetime.timedelta(days=40)
STOP = f'{_DAY}T10:00:00.500000Z'
START = f'{_DAY - datetime.timedelta(days=30)}T10:00:00.120000Z'
SHORT_STOP = f'{_DAY - datetime.timedelta(days=26)}T10:00:00.500000Z'
LATER = f'{_DAY + datetime.timedelta(days=20)}T00:00:00Z'
TID = '00000000-0000-4000-8000-0000000000d{}'


def test_row(i, kind='paywall', stop=STOP, title='Plan order'):
    return {'ab_test_id': TID.format(i), 'title': title, 'type': kind, 'state': 'completed',
            'placement': {'placement_id': PID, 'title': 'onboarding'}, 'segment_ids': [],
            'started_at': START, 'stopped_at': stop}


def variation(cid, standalone):
    """A flow node's `variation_id`: the arm's own inside a test (as `ab-tests get` gives it), another outside."""
    return ('00000000-0000-4000-8000-0000000fa%03x' if not standalone else '00000000-0000-4000-8000-0000000fb%03x') % int(cid[-2:], 16)


def content(cid, kind, started, stopped, prods=()):
    key = {'paywall': {'paywall_id': cid, 'title': NAMES[cid]}, 'title': NAMES[cid], 'content_type': 'paywall'} if kind == 'paywall' else \
        {'level': 'variation', 'variation_id': variation(cid, True), 'title': NAMES[cid]}
    return dict(key, state='inactive' if stopped else 'live', started_at=started, stopped_at=stopped,
                items=[{'product_id': p, 'title': p} for p in prods])


def arm_node(cid, kind, prods, p2bb=None, buys=None):
    n = content(cid, kind, None, None)
    n.pop('state'), n.pop('started_at'), n.pop('stopped_at')
    n['weight'] = 50
    if kind == 'flow':
        n['variation_id'] = variation(cid, False)
        n['items'] = [{'level': 'screen', 'items': [{'level': 'product', 'product_id': p, 'title': p} for p in prods]}]
        n.update(probability=p2bb, purchases=buys, views=(buys or 0) * 20, unique_profiles_views=(buys or 0) * 20)
    else:
        n['items'] = [{'product_id': p, 'title': p, 'product_set': p.lower()} for p in prods]
    return n


def tree(kind, tests, extra):
    """One audience: the contents in `extra`, then a node per test with its arms."""
    kids = list(extra)
    for t, arms in tests:
        kids.append({'title': t['title'], 'ab_test': {'ab_test_id': t['ab_test_id'], 'title': t['title']},
                     'level': 'ab_test', 'content_type': 'ab_test', 'state': t['state'],
                     'started_at': t['started_at'], 'stopped_at': t['stopped_at'], 'items': arms})
    return {'data': {'title': 'Total', 'items': [{'audience': {'audience_id': AUD, 'title': 'All Users'},
                                                  'title': 'All Users', 'items': kids}]}}


def run(case, tests, arms_by_test, plc_tree, metrics=None, now=None):
    """`ab_tests()` with fixture answers; returns its printout. `metrics` None: the CLI has no `ab-tests metrics`."""
    adapty = f'fake-{case}'

    def fake(_adapty, args):
        if args[:2] == ['ab-tests', 'list']:
            ty = args[args.index('--type') + 1]
            return {'data': [t for t in tests if t['type'] == ty], 'meta': {'pagination': {'pages': 1}}}, None
        if args[:2] == ['ab-tests', 'get']:
            t = next(t for t in tests if t['ab_test_id'] == args[2])
            key = 'paywalls' if t['type'] == 'paywall' else 'flows'
            idk = 'paywall_id' if key == 'paywalls' else 'flow_id'
            named = 'paywall_title' if key == 'paywalls' else 'flow_name'
            return dict(t, **{key: [{idk: c, named: NAMES[c], 'weight': 50, 'variation_id': variation(c, False)}
                                    for c in arms_by_test[t['ab_test_id']]]}), None
        if args[:3] == ['placements', 'metrics', 'get']:
            return plc_tree, None
        if args[:3] == ['ab-tests', 'metrics', 'list']:
            ids = args[args.index('--ids') + 1].split(',')
            return {'data': [r for r in metrics if r['ab_test_id'] in ids]}, None
        return None, f'unexpected call {args}'
    reads.run_read = fake
    reads.has = lambda _a, words: metrics is not None if words[:2] == ['ab-tests', 'metrics'] else True
    reads.FAILED.clear()
    auds = {PID: [{'segment_ids': [], 'content_type': 'paywall', 'paywall_id': now}]} if now else {PID: []}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        reads.ab_tests(argparse.Namespace(adapty=adapty, app=APP), dict(NAMES), auds)
    return out.getvalue()


def outcome(text, title):
    """The OUTCOME line of the test whose list line names `title`."""
    block = text.split(f"{title!r} on")[1] if f"{title!r} on" in text else ''
    m = re.search(r'OUTCOME (\w+(?: \w+)?):', block)
    return m.group(1) if m else None


def metrics_row(i, p2bb, buys, ids=(A, B)):
    return {'ab_test_id': TID.format(i), 'items': [{'paywall_id': c, 'probability': p, 'purchases': n, 'views': n * 20}
                                                   for c, p, n in zip(ids, p2bb, buys)]}


PRODS = ('Monthly', 'Annual')


def paywall_case(case, p2bb, buys, before=A, after=B, stop=STOP, metrics=True, prods=(PRODS, PRODS), start=START):
    t = dict(test_row(1, stop=stop), started_at=start)
    extra = []
    if before:
        extra.append(content(before, 'paywall', '2026-01-01T00:00:00Z', start.replace('.120000', '.121000'), PRODS))
    if after:
        extra.append(content(after, 'paywall', stop.replace('.500000', '.499000'), None, PRODS))
    arms = [arm_node(A, 'paywall', prods[0]), arm_node(B, 'paywall', prods[1])]
    text = run(case, [t], {t['ab_test_id']: [A, B]}, tree('paywall', [(t, arms)], extra),
               [metrics_row(1, p2bb, buys)] if metrics else None, now=after)
    return text, outcome(text, t['title'])


# 1. the new arm beat the one the audience had before, and they kept it
text, word = paywall_case('worked', (3.0, 97.0), (240, 260))
check('kept the new arm, which came out ahead: WORKED', word == 'WORKED', text)
check('names what the audience showed before, as an arm', "before the test that audience showed 'Monthly first' (an arm)" in text, text)
check('names what came right after the stop as the arm they kept', "right after it stopped: 'Annual first' (an arm), the one they kept" in text, text)
check('same products in both arms: a design or copy change', 'products: the same in every arm (Annual, Monthly)' in text, text)
check('the summary counts it under its kind', 'same products: 1 test: 1 WORKED' in text, text)

# 2. the old version came out ahead and stayed
text, word = paywall_case('held', (97.0, 3.0), (240, 260), after=A)
check('kept the old arm, which came out ahead: HELD', word == 'HELD', text)

# 3. a tie at the top is level; a lead under the bar is the ab-tests leader, said as not settled
text, word = paywall_case('even', (50.0, 50.0), (240, 260))
check('a tie at the top: EVEN', word == 'EVEN', text)
text, word = paywall_case('unsettled', (10.0, 90.0), (300, 300))
check(f'top P2BB 90, under {reads.CLEAR}: NOT SETTLED, the leader named, nothing ruled out',
      word == 'NOT SETTLED' and "not settled: 'Annual first' is ahead at P2BB 90%" in text and 'no clear difference' not in text, text)

# 4. one arm under about 200 purchases
text, word = paywall_case('few', (2.0, 98.0), (120, 260))
check('an arm under about 200 purchases: FEW, whatever the P2BB', word == 'FEW', text)

# 5. under a week
text, word = paywall_case('short', (2.0, 98.0), (240, 260), stop=SHORT_STOP)
check('ran under a week: SHORT, before any number', word == 'SHORT', text)

# 6. a CLI without `ab-tests metrics`
text, word = paywall_case('noread', (2.0, 98.0), (240, 260), metrics=False)
check('no ab-tests metrics on a paywall test: NOT READ', word == 'NOT READ', text)
check('says once that the CLI lacks the results commands', text.count('This CLI has no `ab-tests metrics`') == 1, text)

# 7. the audience kept the arm that did not come out ahead
text, word = paywall_case('unclear', (3.0, 97.0), (240, 260), after=A)
check('kept an arm the numbers do not back: UNCLEAR', word == 'UNCLEAR', text)

# 8. P2BB not computed
text, word = paywall_case('zero', (0.0, 0.0), (240, 260))
check('P2BB 0 on every arm: NOT COMPUTED', word == 'NOT COMPUTED', text)

# 9. the test was the first thing the audience showed: neither arm is the old version
text, word = paywall_case('first', (3.0, 97.0), (240, 260), before=None)
check('no version before the test: AHEAD, never WORKED', word == 'AHEAD', text)
check('says the test was the first thing the audience showed', 'nothing: the test was the first thing it showed' in text, text)

# 10. arms that sell different products
text, word = paywall_case('plans', (3.0, 97.0), (240, 260), prods=(('Monthly',), ('Monthly', 'Annual')))
check('different products: names what each arm sells', "products differ: 'Monthly first' sells Monthly; 'Annual first' sells Annual, Monthly" in text, text)
check('the summary counts it as a change of products', 'other products: 1 test: 1 WORKED' in text, text)
check('the arm ahead sells the longer plan: PLAN LENGTHS DIFFER, with the date its buyers renew',
      "PLAN LENGTHS DIFFER: 'Annual first' sells an annual plan" in text and f'by {_DAY + datetime.timedelta(days=365)}' in text, text)
check('the note stays out of a test whose arms sell the same plans', 'PLAN LENGTHS DIFFER' not in paywall_case(
    'sameplans', (3.0, 97.0), (240, 260))[0])
text, word = paywall_case('shorter', (97.0, 3.0), (240, 260), after=A, prods=(('Monthly',), ('Monthly', 'Annual')))
check('the shorter plan ahead against the up-front bias: HELD, no note', word == 'HELD' and 'PLAN LENGTHS DIFFER' not in text, text)
text, word = paywall_case('evenplans', (50.0, 50.0), (240, 260), prods=(('Monthly',), ('Monthly', 'Annual')))
check('no arm ahead: no note', word == 'EVEN' and 'PLAN LENGTHS DIFFER' not in text, text)
text, word = paywall_case('oldplans', (3.0, 97.0), (240, 260), prods=(('Monthly',), ('Monthly', 'Annual')),
                          start='2024-03-02T10:00:00.120000Z', stop='2024-04-01T10:00:00.500000Z')
check('the date its buyers renew has passed: no note', word == 'WORKED' and 'PLAN LENGTHS DIFFER' not in text, text)
text, word = paywall_case('lifetime', (3.0, 97.0), (240, 260), prods=(('Monthly',), ('Lifetime',)))
check('a lifetime plan never renews: no note', 'PLAN LENGTHS DIFFER' not in text, text)
text, word = paywall_case('semi', (3.0, 97.0), (240, 260), prods=(('Monthly',), ('Semiannual',)))
check('a plan is named in plain words, not the raw product set', 'sells a six-month plan' in text and 'semiannual' not in text, text)

# 11. a flow test, numbers and P2BB from the placement's lifetime tree, on a CLI without `ab-tests metrics`
NAMES.update({A: 'Quiz short', B: 'Quiz long'})
t = test_row(2, kind='flow', title='Quiz length')
arms = [arm_node(A, 'flow', PRODS, 1.5, 300), arm_node(B, 'flow', PRODS, 98.5, 310)]
extra = [content(A, 'flow', '2026-01-01T00:00:00Z', START), content(B, 'flow', STOP, None)]
text = run('flow', [t], {t['ab_test_id']: [A, B]}, tree('flow', [(t, arms)], extra), None, now=None)
check('flow test read from its placement: WORKED', outcome(text, 'Quiz length') == 'WORKED', text)
check('flow arms print their purchases and P2BB', "'Quiz long' purchases 310, P2BB 98%" in text, text)
check('no CLI note for a flow-only history', 'This CLI has no' not in text, text)
check('a flow node is matched by its variation id and its name: the audience before is an arm',
      "before the test that audience showed 'Quiz short' (an arm)" in text and "right after it stopped: 'Quiz long' (an arm), the one they kept" in text, text)
NAMES.update({A: 'Monthly first', B: 'Annual first'})

# 12. two tests with one title on one audience: each matched by its id, never by its title
t1, t2 = test_row(3, title='Plan order'), dict(test_row(4, title='Plan order'), started_at=STOP, stopped_at=LATER)
arms = [arm_node(A, 'paywall', PRODS), arm_node(B, 'paywall', PRODS)]
extra = [content(A, 'paywall', '2026-01-01T00:00:00Z', START)]
text = run('twins', [t1, t2], {t1['ab_test_id']: [A, B], t2['ab_test_id']: [A, B]},
           tree('paywall', [(t1, arms), (t2, arms)], extra),
           [metrics_row(3, (3.0, 97.0), (240, 260)), metrics_row(4, (97.0, 3.0), (240, 260))])
words = re.findall(r'OUTCOME (\w+(?: \w+)?):', text)
check('the first test is followed by the second on its audience', "right after it stopped: A/B test 'Plan order'" in text, text)
check('each twin gets its own numbers', "'Annual first' purchases 260, P2BB 97%" in text and "'Monthly first' purchases 240, P2BB 97%" in text, text)
check('a test followed by another test has no known kept arm', words.count('AHEAD') == 2, words)

if failures:
    print(f'\n{len(failures)} failed')
    sys.exit(1)
print('\nall passed')
