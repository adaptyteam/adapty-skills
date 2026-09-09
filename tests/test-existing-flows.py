"""Already-converted paywalls: does the plan find the flow that exists?

The dashboard's one-click **Move to new builder** recreates a Paywall Builder
paywall as a DRAFT flow (https://adapty.io/docs/convert-paywall-to-flow.md), so
a user part-way through migrating already has flows in the account. Nothing in
the API records which paywall a flow came from -- there is no back reference to
read -- so the only available signal is the name, and the only safe use of a
name match is to PROPOSE it to the user.

Both directions, per mechanism:

  * FINDS   an exact name match, a contained one, and the draft status that
            says "publish this" rather than "create one".
  * REFUSES a substring that is not a word match (`main` / `domain expert`),
            which is the whole reason matching is tokenized. A false candidate
            is worse than none here: the user is being asked to confirm the
            flow their paying customers will be served.
"""
import json
import pathlib
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parent.parent
REFS = ROOT / 'skills' / 'migrate-placements' / 'references'
sys.path.insert(0, str(REFS))
import migrate as m

MIGRATE = REFS / 'migrate.py'
TMP = ROOT / 'tests' / '_existing_flows_tmp'

failures = []


def check(label, ok, detail=''):
    print(f'{"ok  " if ok else "FAIL"}  {label}' + (f'  -- {detail}' if detail and not ok else ''))
    if not ok:
        failures.append(label)


def rget(mapping, key):
    """`mapping[key]` as a check-safe read -- a KeyError at module level aborts
    the suite, and every check below it then looks green by never running."""
    return (mapping or {}).get(key)


# --- normalize_title -------------------------------------------------------

for label, a, b in [
    ('case', 'Main Paywall', 'main paywall'),
    ('punctuation', 'Main Paywall (US)', 'main paywall us'),
    ('runs of separators collapse', 'Main   --   Paywall', 'main paywall'),
    ('emoji and dashes are separators', 'Main-Paywall', 'main paywall'),
]:
    check(f'normalize_title: {label}', m.normalize_title(a) == b,
          f'{m.normalize_title(a)!r} != {b!r}')

check('normalize_title on a non-string is empty, not a raise',
      m.normalize_title(None) == '' and m.normalize_title(7) == '')

# --- matching, both directions ---------------------------------------------

FLOWS = [
    {'id': 'f-exact', 'name': 'Main Paywall', 'status': 'published'},
    {'id': 'f-suffix', 'name': 'Main Paywall flow', 'status': 'draft'},
    {'id': 'f-substr', 'name': 'Domain expert onboarding', 'status': 'published'},
    {'id': 'f-other', 'name': 'Winback', 'status': 'dirty'},
]

got = m.match_existing_flows('Main Paywall', FLOWS)
ids = [c['flow_id'] for c in got]
check('FINDS the exact name match', 'f-exact' in ids, str(ids))
check('FINDS the natural rename (`Main Paywall` -> `Main Paywall flow`)',
      'f-suffix' in ids, str(ids))
check('the exact match sorts first, so the row the user is offered is the best one',
      ids and ids[0] == 'f-exact', str(ids))
check('REFUSES a substring that is not a word match -- `main` inside `Domain`',
      'f-substr' not in ids, str(ids))

# THE DISCRIMINATING CASE IS A ONE-TOKEN TITLE, and the check above is not it.
# Found by mutation: swapping the token walk for `' '.join(needle) in
# ' '.join(haystack)` reddened NOTHING, because normalization has already put
# spaces around the words -- `'main paywall' in 'domain expert onboarding'` is
# false as a substring too. The hazard only bites when the needle is a single
# word: `'main' in 'domain expert'` is TRUE. So this is the assertion that
# proves the walk is tokenized, and the two-token one above does not.
one = [c['flow_id'] for c in m.match_existing_flows('Main', FLOWS)]
check('a ONE-TOKEN title still refuses the substring -- `Main` does not match '
      '`Domain expert onboarding`', 'f-substr' not in one, str(one))
check('while it does match the flows that really do start with that word',
      set(one) == {'f-exact', 'f-suffix'}, str(one))
check('REFUSES an unrelated flow', 'f-other' not in ids, str(ids))
check('the match kind is reported rather than collapsed, because the user confirms',
      {c['flow_id']: c['match'] for c in got}
      == {'f-exact': 'exact', 'f-suffix': 'contains'},
      str([(c['flow_id'], c['match']) for c in got]))

check('a single-token title still matches its own flow',
      [c['flow_id'] for c in m.match_existing_flows('Winback', FLOWS)] == ['f-other'])
check('an empty or unusable title matches NOTHING rather than everything',
      m.match_existing_flows('', FLOWS) == []
      and m.match_existing_flows(None, FLOWS) == []
      and m.match_existing_flows('!!!', FLOWS) == [])
check('a flow row that is not an object is skipped, not a raise',
      [c['flow_id'] for c in m.match_existing_flows('Winback', ['nope', None, *FLOWS])]
      == ['f-other'])
check('a flow with no usable name is skipped',
      m.match_existing_flows('Main Paywall', [{'id': 'x', 'name': None}]) == [])

# THE STATUS IS WHY A CANDIDATE IS USEFUL. A converted flow is left `draft`,
# and a draft is refused at attach -- so the row has to say which of the two
# remaining actions is needed, and neither of them is `flows create`.
steps = {c['flow_id']: c['next_step'] for c in got}
check('a published candidate says `attach`', steps.get('f-exact') == 'attach', str(steps))
check('a DRAFT candidate says `publish_then_attach` -- the converted-flow case',
      steps.get('f-suffix') == 'publish_then_attach', str(steps))
check('a `dirty` candidate says `publish_then_attach` too -- only `published` attaches',
      m.match_existing_flows('Winback', FLOWS)[0]['next_step'] == 'publish_then_attach')

# --- build_plan carries them ----------------------------------------------

PLACEMENTS = [
    {'id': 'pl-a', 'developer_id': 'main', 'title': 'Main',
     'audiences': [{'paywall_id': 'pw-1', 'priority': 0, 'segment_ids': []}]},
    {'id': 'pl-b', 'developer_id': 'winback', 'title': 'Winback',
     'audiences': [{'paywall_id': 'pw-2', 'priority': 0, 'segment_ids': []}]},
]
EXISTING = {'flows': FLOWS,
            'paywalls': [{'id': 'pw-1', 'title': 'Main Paywall'},
                         {'id': 'pw-2', 'title': 'Renewal push'}]}

plan = m.build_plan(PLACEMENTS, existing=EXISTING)
needed = {row['paywall_id']: row for row in plan['flows_needed']}
check('the paywall TITLE reaches the plan -- an audience carries only the id',
      rget(needed.get('pw-1'), 'paywall_title') == 'Main Paywall',
      str(needed.get('pw-1')))
check('a paywall that already has a flow carries its candidates',
      [c['flow_id'] for c in rget(needed.get('pw-1'), 'existing_flow_candidates') or []]
      == ['f-exact', 'f-suffix'], str(needed.get('pw-1')))
check('a paywall with no match carries NO candidates key, so absence is not an empty list '
      'someone has to interpret',
      'existing_flow_candidates' not in (needed.get('pw-2') or {}),
      str(needed.get('pw-2')))

ex = rget(plan['summary'], 'existing')
check('the summary counts over the paywalls THIS PLAN needs a flow for, not the account',
      (rget(ex, 'paywalls_with_candidate'), rget(ex, 'paywalls_without_candidate'))
      == (1, 1), str(ex))
check('and it reports how much it read, so a zero can be told from a blind run',
      (rget(ex, 'flows_read'), rget(ex, 'paywalls_read')) == (4, 2), str(ex))

check('a paywall whose title could not be read is counted, not silently unmatched',
      rget(m.build_plan(PLACEMENTS, existing={'flows': FLOWS, 'paywalls': []})['summary']
           .get('existing'), 'untitled_paywalls') == 2)

check('with no existing block the plan is byte-identical to what it was before the '
      'feature -- no candidates, no summary key',
      'existing' not in (m.build_plan(PLACEMENTS)['summary'])
      and all('existing_flow_candidates' not in r and 'paywall_title' not in r
              for r in m.build_plan(PLACEMENTS)['flows_needed']))

check('a read error is carried into the summary rather than dropped',
      m.build_plan(PLACEMENTS, existing={'error': 'boom'})['summary']['existing']
      == {'error': 'boom'})

# --- describe_existing: the line an agent actually reads -------------------

line = m.describe_existing(plan['summary'])
check('describe_existing names the count and says not to create a second flow',
      '1 of 2' in line and 'do not create a second flow' in line, line)
none_line = m.describe_existing(
    m.build_plan(PLACEMENTS, existing={'flows': [], 'paywalls': EXISTING['paywalls']})['summary'])
check('with no matches it says a NAME MATCH IS THE ONLY SIGNAL rather than "nothing was '
      'converted" -- the tool cannot see a back reference and must not imply it can',
      'only signal' in none_line and 'ask' in none_line, none_line)
err_line = m.describe_existing({'existing': {'error': 'boom'}})
check('an error line points at the flows dashboard instead of reporting zero',
      'boom' in err_line and 'app.adapty.io/flows' in err_line, err_line)
check('an ABSENT block says so -- a blind run must not read as a clean one',
      'not read' in m.describe_existing({}), m.describe_existing({}))

# --- end to end through the CLI -------------------------------------------

TMP.mkdir(exist_ok=True)
shim = TMP / 'fake-adapty.py'
shim.write_text('''#!/usr/bin/env python3
"""One placement, plus 3 flows over 2 pages at page size 2 -- so a run that
reads page 1 alone misses the flow that matches."""
import json, sys
a = sys.argv[1:]
CALLS = sys.argv[0].replace('fake-adapty.py', 'calls.log')
open(CALLS, 'a').write(' '.join(a) + '\\n')
PL = [{"id": "pl-a", "developer_id": "main", "title": "Main"}]
FLOWS = [
    {"id": "f-1", "name": "Winback", "status": "published"},
    {"id": "f-2", "name": "Trial upsell", "status": "published"},
    {"id": "f-3", "name": "Main Paywall flow", "status": "draft"},
]
PW = [{"id": "pw-1", "title": "Main Paywall", "product_ids": []}]


def page(rows):
    size = int(a[a.index("--page-size") + 1]) if "--page-size" in a else 20
    num = int(a[a.index("--page") + 1]) if "--page" in a else 1
    start = (num - 1) * size
    print(json.dumps({"data": rows[start:start + size],
                      "meta": {"pagination": {"count": len(rows), "page": num,
                                              "pages": max(1, -(-len(rows) // size))}}}))
    sys.exit(0)


if a[:2] == ["placements", "list"]:
    page(PL)
if a[:2] == ["flows", "list"]:
    page(FLOWS)
if a[:2] == ["paywalls", "list"]:
    page(PW)
if a[:2] == ["placements", "get"]:
    print(json.dumps(dict(PL[0], audiences=[
        {"paywall_id": "pw-1", "priority": 0, "segment_ids": []}])))
    sys.exit(0)
print("unexpected: " + " ".join(a), file=sys.stderr)
sys.exit(9)
''')
ADAPTY = f'{sys.executable} {shim}'
calls = TMP / 'calls.log'


def run(*args):
    if calls.exists():
        calls.unlink()
    return subprocess.run([sys.executable, str(MIGRATE), *args],
                          capture_output=True, text=True)


inv = TMP / 'inventory.json'
r = run('inventory', '--app', 'app-1', '--adapty', ADAPTY, '--page-size', '2',
        '--out', str(inv))
check('inventory exits 0 with the existing-flow reads on by default',
      r.returncode == 0, r.stderr.strip()[:300])
body = json.loads(inv.read_text()) if inv.exists() else {}
check('THE FLOW LIST IS PAGED TO EXHAUSTION -- page size 2 over 3 flows, and the '
      'match is on page 2, so a single call would miss exactly the row that matters',
      len(rget(body.get('existing'), 'flows') or []) == 3,
      str(len(rget(body.get('existing'), 'flows') or [])))
check('and the paywalls come with it, since an audience carries no title',
      len(rget(body.get('existing'), 'paywalls') or []) == 1)
check('inventory says what it read, on stdout, so a run cannot look blind or clean by '
      'accident', 'existing flows: 3 flow(s)' in r.stdout, r.stdout)

r2 = run('plan', '--inventory', str(inv))
check('plan exits 0', r2.returncode == 0, r2.stderr.strip()[:300])
out = json.loads(r2.stdout) if r2.returncode == 0 else {}
row = (out.get('flows_needed') or [{}])[0]
check('END TO END: the draft flow the user already converted is proposed for the '
      'paywall, with `publish_then_attach` -- so the run publishes what exists '
      'instead of creating a second, emptier flow',
      [(c['flow_id'], c['next_step']) for c in row.get('existing_flow_candidates') or []]
      == [('f-3', 'publish_then_attach')], str(row))
check('plan repeats the line on STDERR, because its stdout is JSON and is routinely '
      'redirected to a file', 'existing flows: 1 of 1' in r2.stderr, r2.stderr)

r3 = run('inventory', '--app', 'app-1', '--adapty', ADAPTY, '--page-size', '2',
         '--out', str(inv), '--no-existing')
log = calls.read_text() if calls.exists() else ''
check('--no-existing skips BOTH extra reads -- no `flows list`, no `paywalls list`',
      r3.returncode == 0 and 'flows list' not in log and 'paywalls list' not in log,
      log)
check('and it says the plan cannot answer the question, rather than answering it with '
      'a zero', 'not read (--no-existing)' in r3.stdout, r3.stdout)
check('a plan over that inventory still says the question went unanswered',
      'existing flows: not read' in run('plan', '--inventory', str(inv)).stderr)

# A hand-edited file is exit 2 with the field named -- the same rule the placement
# rows already follow, so `plan` never subscripts its way into the catch-all.
bad = TMP / 'bad.json'
bad.write_text(json.dumps({'app': 'a', 'placements': [], 'existing': []}))
rb = run('plan', '--inventory', str(bad))
check('a malformed `existing` is exit 2 naming the field, not a traceback',
      rb.returncode == 2 and "'existing' that is a list" in rb.stderr, rb.stderr[:200])
bad.write_text(json.dumps({'app': 'a', 'placements': [], 'existing': {'flows': {}}}))
rb2 = run('plan', '--inventory', str(bad))
check('and so is a malformed `existing.flows`',
      rb2.returncode == 2 and 'existing.flows is a dict' in rb2.stderr, rb2.stderr[:200])

print()
print(f'{len(failures)} failure(s)' if failures else 'all checks passed')
raise SystemExit(1 if failures else 0)
