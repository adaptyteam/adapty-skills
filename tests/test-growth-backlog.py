"""growth-advisor's hypothesis backlog, driven offline: `reads.py`'s backlog functions against fixture answers.

Rows follow the shape of `hypotheses list --json` (adapty-cli `src/sdk/adapty/hypotheses/model.ts`): `state`,
a derived `phase`, `subject` with `type`, `flow_id`, `flow_screen_id`, `segment_id`, a `products` list with
`duration_type`, `trial_duration` and `country`, `stale` from the server's staleness values. Drafts are create
bodies (`hypothesis_id`, `placement_id`, `subject`, `type`, `title`, ...). Ids and names are made up.
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile

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
FLOW = '00000000-0000-4000-8000-0000000000f1'
VARIANT = '00000000-0000-4000-8000-0000000000f2'
SEG = '00000000-0000-4000-8000-0000000000e1'
TEST = '00000000-0000-4000-8000-0000000000d1'


def hid(n):
    return f'00000000-0000-4000-8000-{n:012d}'


def subject(kind='flow', screen=None, segment=None):
    return {'type': kind, 'flow_id': None if kind == 'audience' else FLOW, 'flow_screen_id': screen,
            'segment_id': segment}


def row(n, state, phase=None, kind='adapty:flow_design', subj=None, products=(), **extra):
    r = {'hypothesis_id': hid(n), 'app_id': APP, 'placement_id': PID, 'placement': {'id': PID, 'title': 'Onboarding'},
         'state': state, 'phase': phase or state, 'type': kind, 'subject': subj or subject(), 'title': f'Row {n}',
         'products': [dict(p) for p in products], 'ab_test_id': None, 'variant_flow_id': None,
         'suggested_result': None, 'stale': 'fresh', 'is_projected': False}
    r.update(extra)
    return r


def draft(kind='adapty:flow_design', subj=None, products=(), **extra):
    d = {'placement_id': PID, 'subject': subj or subject(), 'type': kind, 'title': 'Draft'}
    if products:
        d['products'] = [dict(p) for p in products]
    d.update(extra)
    return d


ANNUAL_BR = {'duration_type': 'annual', 'trial_duration': None, 'country': 'BR'}
ANNUAL_MX = {'duration_type': 'annual', 'trial_duration': None, 'country': 'MX'}
PAYWALL_SCREEN = subject('flow_screen', screen='paywall')

# --- match: one draft against the backlog
check('a draft with no row like it is new', reads.match(draft(), [])[0] == 'new')
for state in ('won', 'lost', 'inconclusive'):
    b, r = reads.match(draft(), [row(1, state)])
    check(f'a {state} row of the same change is tested', b == 'tested' and r['hypothesis_id'] == hid(1), b)
check('a stopped test with no result yet is tested', reads.match(draft(), [row(1, 'accepted', 'ended')])[0] == 'tested')
for phase in ('proposed', 'accepted', 'test_draft'):
    check(f'a {phase} row is in the backlog', reads.match(draft(), [row(1, 'proposed' if phase == 'proposed'
                                                                         else 'accepted', phase)])[0] == 'backlog')
check('a testing row is testing', reads.match(draft(), [row(1, 'accepted', 'testing')])[0] == 'testing')
check('an applied row is live', reads.match(draft(), [row(1, 'accepted', 'applied')])[0] == 'live')
check('a dismissed row is dismissed', reads.match(draft(), [row(1, 'dismissed')])[0] == 'dismissed')
check('an open row wins over a dismissed one',
      reads.match(draft(), [row(1, 'dismissed'), row(2, 'proposed')])[0] == 'backlog')
check('another type on the same flow is new', reads.match(draft('adapty:trial'), [row(1, 'proposed')])[0] == 'new')
check('the same type on another placement is new',
      reads.match(draft(), [row(1, 'proposed', placement_id=hid(99))])[0] == 'new')
check('the same type on another screen is new',
      reads.match(draft(subj=PAYWALL_SCREEN), [row(1, 'proposed', subj=subject('flow_screen', screen='intro'))])[0]
      == 'new')
check('an audience split on another segment is new',
      reads.match(draft('adapty:audience_split', subject('audience', segment=SEG)),
                  [row(1, 'proposed', kind='adapty:audience_split', subj=subject('audience', segment=hid(98)))])[0]
      == 'new')

# products: the server's duplicate check ignores them, the skill does not
price = 'growth_advisor:price'
b, r = reads.match(draft(price, PAYWALL_SCREEN, [ANNUAL_BR]),
                   [row(1, 'proposed', kind=price, subj=PAYWALL_SCREEN, products=[ANNUAL_BR])])
check('the same price move in the same country is in the backlog', b == 'backlog', b)
b, r = reads.match(draft(price, PAYWALL_SCREEN, [ANNUAL_MX]),
                   [row(1, 'proposed', kind=price, subj=PAYWALL_SCREEN, products=[ANNUAL_BR])])
check('a price move in another country, with an open one on that screen, needs force', b == 'force', b)
b, r = reads.match(draft(price, PAYWALL_SCREEN, [ANNUAL_MX]),
                   [row(1, 'won', kind=price, subj=PAYWALL_SCREEN, products=[ANNUAL_BR])])
check('a price move in another country, next to a tested one, is new', b == 'new', b)
b, _ = reads.match(draft('adapty:new_duration', PAYWALL_SCREEN, [{'duration_type': 'monthly'}]),
                   [row(1, 'won', kind='adapty:new_duration', subj=PAYWALL_SCREEN,
                        products=[{'duration_type': 'monthly', 'trial_duration': None, 'country': None}])])
check('a missing product field counts as empty', b == 'tested', b)

# --- due: what a returning session acts on
regular = {'placement_audience_id': hid(50), 'content_type': 'flow', 'flow_id': VARIANT, 'segment_ids': []}
in_test = {'placement_audience_id': hid(51), 'content_type': 'ab_test', 'ab_test_id': TEST, 'flow_id': VARIANT}
rows = [
    row(1, 'accepted', 'testing', ab_test_id=TEST),
    row(2, 'accepted', 'ended', ab_test_id=TEST),
    row(3, 'accepted', 'accepted', variant_flow_id=VARIANT),
    row(4, 'accepted', 'accepted', variant_flow_id=hid(97)),
    row(5, 'proposed', stale='flow_deleted'),
    row(6, 'accepted', 'testing', ab_test_id=TEST, suggested_result='won'),
    row(7, 'proposed', stale='not_applicable'),
    row(8, 'won'),
]
due = {h['hypothesis_id']: what for what, h in reads.due(rows, {PID: [regular]})}
check('a testing row is read-test', due.get(hid(1)) == 'read-test', due.get(hid(1)))
check('an ended row asks for its result', due.get(hid(2)) == 'ask-result', due.get(hid(2)))
check('an accepted flow whose variant a regular audience shows is a live check', due.get(hid(3)) == 'live-check')
check('an accepted flow whose variant is not shown is not due', hid(4) not in due)
check('a row whose flow is deleted is stale', due.get(hid(5)) == 'stale', due.get(hid(5)))
check('a suggested result asks for the result', due.get(hid(6)) == 'ask-result', due.get(hid(6)))
check('not_applicable is not stale', hid(7) not in due)
check('a resolved row is not due', hid(8) not in due)
due = {h['hypothesis_id']: what for what, h in reads.due([row(3, 'accepted', 'accepted', variant_flow_id=VARIANT)],
                                                          {PID: [in_test]})}
check('a variant shown only as a test arm is not a live check', not due, due)


# --- backlog_rows: every page of the list, filtered by placement
class Pages:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def __call__(self, adapty, args):
        self.calls.append(args)
        page = int(args[args.index('--page') + 1])
        return {'data': self.pages[page - 1], 'meta': {'pagination': {'pages': len(self.pages)}}}, None


fake = Pages([[row(1, 'proposed')], [row(2, 'won')]])
real = reads.cli
reads.cli = fake
try:
    got = reads.backlog_rows('adapty', APP, [PID])
finally:
    reads.cli = real
check('every page is read', [h['hypothesis_id'] for h in got] == [hid(1), hid(2)], got)
check('the list is filtered by placement', all(['--placement', PID] == c[c.index('--placement'):c.index('--placement') + 2]
                                               for c in fake.calls), fake.calls)

# --- check_drafts: what the server would refuse, said before the create
def problems(d):
    return reads.check_drafts([d])


def says(d, word):
    return any(word in p for p in problems(d))


check('a good draft has no problem', problems(draft(title='Show plans before the trial screen on Onboarding')) == [],
      problems(draft()))
check('a title over 80 characters is flagged', says(draft(title='x' * 81), 'title'))
check('a title of 80 characters passes', not says(draft(title='x' * 80), 'title'))
check('a rationale over 1200 characters is flagged', says(draft(rationale='x' * 1201), 'rationale'))
check('an action over 700 characters is flagged', says(draft(action='x' * 701), 'action'))
check('a range without its metric is flagged', says(draft(expected={'low_pct': 2, 'high_pct': 6}), 'together'))
check('a full range passes', not problems(draft(expected={'metric': 'arpu', 'low_pct': 2, 'high_pct': 6})))
check('a metric the server does not know is flagged',
      says(draft(expected={'metric': 'revenue', 'low_pct': 2, 'high_pct': 6}), 'revenue'))
check('an unknown metric in metrics_impact is flagged', says(draft(metrics_impact=['trial_to_paid']), 'trial_to_paid'))
check('flow design on an audience is flagged',
      says(draft('adapty:flow_design', subject('audience', segment=SEG)), 'adapty:flow_design'))
check('a product change on a whole flow is flagged', says(draft('adapty:new_duration', subject()), 'flow_screen'))
check('an adapty type the server does not have is flagged', says(draft('adapty:price', PAYWALL_SCREEN), 'adapty:price'))
check('our own type named like a server type is flagged', says(draft('growth_advisor:trial', PAYWALL_SCREEN),
                                                                'adapty:trial'))
check('our own price type passes', not problems(draft('growth_advisor:price', PAYWALL_SCREEN, [ANNUAL_BR])))
check('a type that breaks the namespace:name form is flagged', says(draft('Growth:Price'), 'namespace:name'))

with tempfile.TemporaryDirectory() as tmp:
    path = pathlib.Path(tmp) / 'drafts.json'
    path.write_text(json.dumps([draft(title='One'), draft(title='Two', hypothesis_id=hid(5))]))
    reads.mint_ids(str(path))
    first = json.loads(path.read_text())
    reads.mint_ids(str(path))
    again = json.loads(path.read_text())
    check('a draft without an id gets one', bool(first[0].get('hypothesis_id')), first)
    check('a draft with an id keeps it', first[1]['hypothesis_id'] == hid(5), first)
    check('ids stay the same on a second run, so a retry replays', first == again, again)

# --- review fixes
try:
    b, _ = reads.match(draft(price, PAYWALL_SCREEN, [ANNUAL_BR]),
                       [row(1, 'proposed', kind=price, subj=PAYWALL_SCREEN,
                            products=[{'duration_type': 'annual', 'trial_duration': None, 'country': None},
                                      ANNUAL_MX])])
    check('products with and without a country compare without a crash', b == 'force', b)
except TypeError as e:
    check('products with and without a country compare without a crash', False, str(e))

got = [b for b, _ in reads.match_all([draft(price, PAYWALL_SCREEN, [ANNUAL_BR]),
                                      draft(price, PAYWALL_SCREEN, [ANNUAL_MX])], [])]
check('a second draft of the same change in one batch needs force', got == ['new', 'force'], got)
got = [b for b, _ in reads.match_all([draft(), draft()], [])]
check('the same draft twice in one batch is a duplicate of the first', got == ['new', 'backlog'], got)

aud_row = row(9, 'accepted', 'applied', kind='adapty:audience_split', subj=subject('audience', segment=SEG),
              placement_audience_id=hid(50))
due = {h['hypothesis_id']: what for what, h in reads.due([aud_row], {PID: []})}
check('an audience split put live is a live check', due.get(hid(9)) == 'live-check', due)

legacy = {'type': 'paywall'}
check('our own type on a legacy paywall is not sent to a server type',
      not problems(draft('growth_advisor:new_duration', legacy)), problems(draft('growth_advisor:new_duration', legacy)))

print(f'\n{len(failures)} failed' if failures else '\nall passed')
sys.exit(1 if failures else 0)
