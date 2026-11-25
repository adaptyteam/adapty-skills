#!/usr/bin/env python3
"""The `store-compliance` checker on its own, and the seam `flow-audit` calls it through.

The checks themselves are calibrated in `test-store-review.py` (advisory shapes) and
`test-audit-flow.py` (the required mechanisms), both through `flow-audit`'s report. This file
covers what only shows when the two skills are apart:

  - `store-check.py --report`, the standalone verdict line and its disclaimer;
  - `store-check.py --json` equals the store findings `audit-flow.py --json` prints;
  - `flow-audit` copied without `store-compliance` says so as a question, and its verdict
    never reads a bare "Ready to publish".

Runs the shipped scripts as subprocesses, so nothing writes a `__pycache__` into them.
Usage: python3 tests/test-store-check.py     # 0 all pass, 1 a case regressed
"""
import glob, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, 'plugin', 'skills')
AUDIT = os.path.join(SKILLS, 'flow-audit', 'references', 'audit-flow.py')
STORE = os.path.join(SKILLS, 'store-compliance', 'references', 'store-check.py')
FIX = os.path.join(ROOT, 'tests', 'fixtures')
CATALOG = os.path.join(ROOT, 'tests', 'catalog-fixture.json')
DISCLAIMER = 'a clean check is not an approval, and a finding is not a rejection'

fails = []


def check(name, cond, detail=''):
    print(f'  {"ok  " if cond else "FAIL"}  {name}' + ('' if cond else f' {detail}'))
    if not cond:
        fails.append(name)


def run(script, *args):
    r = subprocess.run([sys.executable, script, *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


print('standalone report')
rc, out, err = run(STORE, os.path.join(FIX, 'comparison-paywall.json'), '--catalog', CATALOG,
                   '--report')
check('a paywall with no Restore and no legal links reads as a rejection',
      out.startswith('**The stores will reject this as it is: 3 things to fix first.**'), out)
check('...exits 1, as a blocker does', rc == 1, rc)
check('...and keeps the guideline number in the fix', '(App Store 3.1.1)' in out, out)
check('every report ends on the disclaimer and the one page to read next',
      DISCLAIMER in out and out.rstrip().endswith(
          'https://adapty.io/docs/prepare-your-app-for-store-review'), out[-300:])

rc, out, err = run(STORE, os.path.join(FIX, 'onboarding-permission-primer.json'), '--report')
check('a clean flow says nothing is missing and still carries the disclaimer',
      out.startswith('**Nothing the stores require is missing, and nothing here has drawn')
      and DISCLAIMER in out and rc == 0, out)

rc, out, err = run(STORE, os.path.join(FIX, 'reviews-carousel.json'), '--report')
check('an open question about a required mechanism holds the verdict',
      out.startswith('**I could not confirm everything the stores require: 1 thing'), out)

rc, out, err = run(STORE, os.path.join(FIX, 'tabs-paywall.json'), '--catalog', CATALOG,
                   '--report')
check('a risk alone never reads as a rejection, and the verb agrees with one',
      out.startswith('**Nothing the stores require is missing, but 1 thing here has drawn'),
      out)

rc, out, err = run(STORE, os.path.join(FIX, 'tabs-paywall.json'), '--report', '--json')
check('--report and --json together is a usage error', rc == 2, rc)

print('\nthe seam flow-audit merges through')
for path in sorted(glob.glob(os.path.join(FIX, '*.json'))):
    for stores in (None, 'ios', 'android'):
        extra = ['--catalog', CATALOG] + (['--stores', stores] if stores else [])
        _, s_out, _ = run(STORE, path, '--json', *extra)
        _, a_out, _ = run(AUDIT, path, '--json', *extra)
        mine = json.loads(s_out)['findings']
        merged = [f for f in json.loads(a_out)['findings'] if f['family'] == 'compliance']
        check(f'{os.path.basename(path)} {stores or "any store"}: flow-audit carries every '
              'store finding, in order', mine == merged,
              f'{[f["check"] for f in mine]} vs {[f["check"] for f in merged]}')

print('\nflow-audit copied without store-compliance')
with tempfile.TemporaryDirectory() as tmp:
    alone = os.path.join(tmp, 'skills', 'flow-audit')
    shutil.copytree(os.path.join(SKILLS, 'flow-audit'), alone)
    script = os.path.join(alone, 'references', 'audit-flow.py')
    primer = os.path.join(FIX, 'onboarding-permission-primer.json')
    _, out, _ = run(script, primer, '--json', '--catalog', CATALOG)
    found = [f['check'] for f in json.loads(out)['findings']]
    check('the store rules that did not run are one question', 'store-check-missing' in found,
          found)
    _, out, _ = run(script, primer, '--report', '--catalog', CATALOG)
    check('...the verdict is never a bare "Ready to publish"',
          '**Ready to publish' not in out.split('\n', 1)[0], out.split('\n', 1)[0])
    check('...and the next step asks for the whole plugin', 'whole Adapty skills plugin' in out,
          out[-600:])
    _, out, _ = run(AUDIT, primer, '--json', '--catalog', CATALOG)
    check('in the plugin, the same flow has no such question',
          'store-check-missing' not in [f['check'] for f in json.loads(out)['findings']])

print('\nlegal links: a link that is plainly something else is not the missing one')


def legal_findings(urls):
    """tabs-paywall.json with its two link buttons labelled "Link" and pointed at `urls`,
    in order, so only the url can say what each link is."""
    text = open(os.path.join(FIX, 'tabs-paywall.json'), encoding='utf-8').read()
    text = text.replace('"Terms"', '"Link"').replace('"Privacy"', '"Link"')
    olds = ('https://example.com/terms', 'https://example.com/privacy')
    for i, old in enumerate(olds):
        assert text.count(f'"{old}"') == 1, old
        text = text.replace(f'"{old}"', f'"@url{i}@"')
    for i, new in enumerate(urls):
        text = text.replace(f'"@url{i}@"', f'"{new}"')
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        f.write(text)
    _, out, _ = run(STORE, f.name, '--json')
    os.unlink(f.name)
    return {x['check']: x['severity'] for x in json.loads(out)['findings']
            if x['check'] in ('no-terms-link', 'no-privacy-link')}


got = legal_findings(['https://example.com/terms', 'https://example.com/checkout'])
check('terms and a checkout only: no Privacy link is a blocker',
      got == {'no-privacy-link': 'blocker'}, got)
got = legal_findings(['https://example.com/privacy', 'https://example.com/pay'])
check('privacy and a payment page only: no Terms link is a blocker',
      got == {'no-terms-link': 'blocker'}, got)
got = legal_findings(['https://example.com/legal', 'https://example.com/checkout'])
check('a /legal page may serve both: a question, never a blocker',
      got == {'no-privacy-link': 'question'}, got)
got = legal_findings(['https://example.com/terms', 'https://example.com/help'])
check('an unexplained link keeps it a question', got == {'no-privacy-link': 'question'}, got)

print('\n--screens: the outline the agent reads for consumer law and app-level rules')
for path in sorted(glob.glob(os.path.join(FIX, '*.json'))):
    code, out, err = run(STORE, path, '--screens')
    name = os.path.basename(path)
    check(f'{name}: exits 0 and starts at the first screen',
          code == 0 and out.startswith('Screen 1: "'), (code, out[:80], err[-200:]))
    check(f'{name}: names no element id', not re.search(r'\bel_[A-Za-z0-9]{6,}', out),
          re.findall(r'\bel_[A-Za-z0-9]{6,}', out)[:3])
quiz = os.path.join(FIX, 'onboarding-quiz-paywall.json')
_, out, _ = run(STORE, quiz, '--screens')
check('a price variable stays readable as {field}', '{prod_price_per_month}/month' in out, out[-400:])
check('a button says where it leads and what it does',
      'button "Subscribe": starts a purchase' in out and 'goes to "Quiz"' in out, out[:400])
check('a quiz branch lists both screens', 'goes to "Rock"; goes to "Hip hop"' in out)
_, out, _ = run(STORE, os.path.join(FIX, 'vpn-timer-draft.json'), '--screens')
check('a countdown is named', '- a countdown timer' in out, out)

if fails:
    print(f'\n{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('\nall passed')
