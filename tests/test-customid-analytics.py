#!/usr/bin/env python3
"""Calibration for the analytics-id checks in `references/verify-config.py`.

Repo-only. Runs the shipped script as a subprocess -- never imports it, so nothing writes a
`__pycache__` into `references/`.

Why this file exists. An input or a selectable option reports what the user entered to the
app through `flow_user_input`, and the id in that payload is NOT the element's `el_XXXX` map
key -- it is the author-supplied `props.customId` (a group reports its `selectableGroups[].id`
instead). Read from source, `unified-builder-transformer@dcf2df4`:

    generate-handlers.ts:717,825   elementId: ${JSON.stringify(trackedInput.customId)}
    generate-handlers.ts:849       ... JSON.stringify(selectable.groupId) ...
    generate-meta.ts:245           analyticsId: ${JSON.stringify(el.optionCustomId ?? '')}

`customId` is OPTIONAL in the published schema (`required` is absent on all eleven input and
selectable props types), and when it is missing the transformer silently declines to track:

    user-input-analytics.ts:98     if (!EDITABLE_INPUT_TYPES.has(element.type) || !customId) return

For a selectable group the same gate is GROUP-WIDE rather than per option, which is what makes
this worth a mechanical check rather than a note -- one blank or one duplicate takes every
answer in the group with it (collect-variables.ts:1246-1252):

    if (groupType !== 'toggle' &&
        (!allUniqueNonEmpty(groupElements.map(e => e.optionCustomId)) ||
         !allUniqueNonEmpty(groupElements.map(e => e.optionId)))) {
      continue        // analyticsEnabled stays false for EVERY member
    }

Nothing else catches it. `flows config validate` returns valid (the document is well formed),
the schema passes it (the field is optional), and `config preview` draws a working quiz. The
customer finds out when no answers arrive.

SCOPE, and it is calibrated rather than mirrored from the transformer. Only groups that
actually report user input are checked: `single_choice`/`multi_choice` whose members are
`selectable`. Excluded, each with real corpus instances behind it -- `product` groups (6
instances, 0 ever carry a customId) and `tab-item` groups (2 instances, same), because the
docs state that product selections and tab switches do not raise the event at all; and
`toggle` groups, which the transformer exempts by name.

    ERROR    -- two options in a reporting group share one customId. Wrong in every state
                the author could have meant, and absent from every real export.
    warning  -- a reporting group where SOME options carry a customId and others do not. Just
                as fatal at runtime, but indistinguishable from a half-finished edit, and a
                GENUINE export here has exactly that shape -- so erroring would fire on real
                published builder output, which this repo treats as disqualifying.
    warning  -- a reporting group where NO option carries one. Weaker still: a group that
                only drives branching never needed analytics, and `selectedOptionId` keys on
                `optionId`, not `customId`.
    warning  -- an input element with no customId. Untracked, and no condition can read
                `<customId>.value` either.

`tests/fixtures/onboarding-quiz-paywall.json` and its raw twin FIRE, and that is asserted here
rather than suppressed: the `quiz` group has `rock` and `hiphop` filled and its third option
blank -- two of three siblings, which is a human leaving a field empty, not a generated
artifact. Editing a fixture to quiet a checker is how a corpus stops being evidence.

Usage: python3 tests/test-customid-analytics.py     # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, 'skills', 'flow-generator', 'references', 'verify-config.py')
CORPUS = os.path.join(ROOT, 'tests', 'fixtures')
RAW = os.path.join(ROOT, 'tests', 'fixtures-raw')

# The three message fragments this suite owns. Any other finding from verify-config.py is
# somebody else's check and must not make a case here pass or fail.
PARTIAL = 'has no customId while its siblings do'
DUPE = 'sharing the customId'
NONE_SET = 'no option carries a customId'
INPUT_UNSET = 'input has no customId'
OURS = (PARTIAL, DUPE, NONE_SET, INPUT_UNSET)

fails = []


def run(doc):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json')
        json.dump(doc, open(p, 'w'))
        r = subprocess.run([sys.executable, VERIFY, p], capture_output=True, text=True)
    if 'Traceback' in r.stderr:
        raise AssertionError(f'verify-config.py crashed:\n{r.stderr}')
    # Exit 2 is the top-level CHECKER ERROR guard, and it prints to STDOUT. Without this the
    # whole suite is unfailable in one direction: a malformed case yields no findings, so every
    # `silent()` assertion passes for the wrong reason. Caught exactly that way while writing
    # this file -- a fixture with `locales: ['en']` instead of `[{code: 'en'}]`.
    if r.returncode == 2 or 'CHECKER ERROR' in r.stdout:
        raise AssertionError(f'verify-config.py could not read the document (exit '
                             f'{r.returncode}) — the case is malformed, not silent:\n{r.stdout}')
    errs = [l.split('ERROR:', 1)[1].strip() for l in r.stdout.splitlines() if 'ERROR:' in l]
    warns = [l.split('warning:', 1)[1].strip() for l in r.stdout.splitlines() if 'warning:' in l]
    return errs, warns


def fires(name, doc, fragment, level='error'):
    errs, warns = run(doc)
    lines = errs if level == 'error' else warns
    if not any(fragment in l for l in lines):
        fails.append(f'{name}: expected a {level} containing {fragment!r}, '
                     f'got errors={errs!r} warnings={warns!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


def silent(name, doc):
    errs, warns = run(doc)
    hits = [l for l in errs + warns if any(f in l for f in OURS)]
    if hits:
        fails.append(f'{name}: expected no analytics-id finding, got {hits!r}')
        print(f'  FAIL  {name}')
    else:
        print(f'  ok    {name}')


# ------------------------------------------------------------------ builders
def option(eid, group_id, custom_id, *, kind='selectable', default=False):
    props = {'width': {'type': 'fill'}, 'height': {'type': 'hug'},
             'position': {'type': 'relative'}, 'groupId': group_id, 'default': default,
             'layout': {'direction': 'vertical', 'distribution': {'type': 'gap', 'gap': 0}}}
    if custom_id is not None:
        props['customId'] = custom_id
    if kind == 'product':
        props['product'] = {'id': f'00000000-0000-0000-0000-{eid[-12:]:>012}'}
    return {'id': eid, 'type': kind, 'states': [], 'props': props}


def quiz(custom_ids, *, group_type='single_choice', kind='selectable'):
    """One screen holding one group, with a member per entry in `custom_ids`."""
    eids = [f'el_opt{i}' for i in range(len(custom_ids))]
    emap = {e: option(e, 'quiz', c, kind=kind, default=(i == 0))
            for i, (e, c) in enumerate(zip(eids, custom_ids))}
    return {'schemaVersion': 10, 'defaultLocale': 'en',
            'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}],
            'theme': {'colors': [], 'typography': []},
            'screens': [{'id': 'scr_quiz', 'props': {}, 'elements': {
                'map': emap,
                'hierarchy': {'id': 'root', 'children': [{'id': e} for e in eids]}},
                'selectableGroups': [{'id': 'quiz', 'type': group_type}]}]}


def with_input(custom_id, kind='text-input'):
    props = {'width': {'type': 'fill'}, 'height': {'type': 'fixed', 'value': 56},
             'position': {'type': 'relative'}}
    if custom_id is not None:
        props['customId'] = custom_id
    return {'schemaVersion': 10, 'defaultLocale': 'en',
            'locales': [{'id': 'en', 'code': 'en', 'name': 'English'}],
            'theme': {'colors': [], 'typography': []},
            'screens': [{'id': 'scr_form', 'props': {}, 'elements': {
                'map': {'el_in': {'id': 'el_in', 'type': kind, 'states': [], 'props': props}},
                'hierarchy': {'id': 'root', 'children': [{'id': 'el_in'}]}},
                'selectableGroups': []}]}


# ------------------------------------------------------------------ FIRES: the group is dark
# The shape found in a real export: two of three siblings filled in. Whoever authored this
# wanted the answers, and gets none of them.
fires('an option with no customId beside options that have one',
      quiz(['rock', 'hiphop', None]), PARTIAL, level='warning')

# Whitespace is not a value. `allUniqueNonEmpty` trims before testing, so "  " reads as blank
# to the transformer and would read as filled to a naive `is not None` check here.
fires('an option whose customId is whitespace',
      quiz(['rock', 'hiphop', '   ']), PARTIAL, level='warning')

# The other half of `allUniqueNonEmpty`. Two options claiming one id is never deliberate, and
# it kills the group exactly as a blank does.
fires('two options sharing one customId',
      quiz(['rock', 'rock', 'hiphop']), DUPE)

# The gate is on group type, and multi_choice reaches it the same way single_choice does.
fires('a multi_choice group with one option unset',
      quiz(['rock', None], group_type='multi_choice'), PARTIAL, level='warning')


# ------------------------------------------------------------------ FIRES: weaker, a warning
# No option carries one. Unlike the partial case there is no evidence the author wanted
# analytics -- a group that only drives branching reads `selectedOptionId`, which keys on
# `optionId` and works fine without any customId. So: report, do not block.
fires('a reporting group where no option carries a customId',
      quiz([None, None, None]), NONE_SET, level='warning')

# An input is inert for data without one: untracked by the transformer, and unreadable by a
# condition, since the handle a gate reads is `<customId>.value`.
fires('an input element with no customId',
      with_input(None), INPUT_UNSET, level='warning')


# ------------------------------------------------------------------ SILENT: correct shapes
silent('every option carries a unique customId', quiz(['rock', 'hiphop', 'jazz']))
silent('a single-option group with a customId', quiz(['rock']))
silent('an input with a customId', with_input('email', kind='email-input'))

# `password-input` is absent from the transformer's INPUT_TYPES map and the docs say a password
# field sends no event, so a missing customId there loses no analytics. Warning about it would
# be a claim that is simply false.
silent('a password input with no customId', with_input(None, kind='password-input'))

# Excluded families, each with real corpus instances behind the exclusion. Product selections
# and tab switches do not raise `flow_user_input` at all, so a blank customId costs nothing.
#
# NEGATIVE-TEST NOTE, recorded because it looks decorative and is not. A product group is
# excluded TWICE over -- once by the group-type filter and once by the member-element-type
# guard -- so disabling either one alone reddens nothing here, and this case reads as an
# assertion that cannot fail. Disabling BOTH reddens it together with SIX real exports
# (comparison-paywall, onboarding-multilocale and tabs-paywall, tracked and raw). That is the
# measurement behind scoping this check by hand instead of mirroring the transformer, whose
# own gate runs over product groups too: a faithful mirror fires on every real paywall here.
silent('a product group carries no customId anywhere',
       quiz([None, None], group_type='product', kind='product'))
silent('a tab bar carries no customId anywhere',
       quiz([None, None, None], kind='tab-item'))

# The transformer exempts `toggle` from the option-id rule by name -- a toggle reports a
# boolean, so it has no option ids to report.
silent('a toggle group with no option customId',
       quiz([None], group_type='toggle'))


# ------------------------------------------------------------------ the real corpus
# Silent on every genuine export but one, and that one is asserted rather than suppressed.
EXPECTED_FIRES = {'onboarding-quiz-paywall.json'}
seen_fire = set()
for path in sorted(glob.glob(os.path.join(CORPUS, '*.json'))) + \
            sorted(glob.glob(os.path.join(RAW, '*.json'))):
    name = os.path.basename(path)
    tag = 'tracked' if os.path.dirname(path) == CORPUS else 'raw'
    doc = json.load(open(path))
    if name in EXPECTED_FIRES:
        # `quiz` on scr_oAPBHPa7: options `rock` and `hiphop` are set, the third is not, so
        # the whole single_choice group reports nothing. A true finding on real builder
        # output -- see this file's header for why the fixture is left alone.
        fires(f'{name} ({tag}) — real export, quiz group has one option unset', doc, PARTIAL,
              level='warning')
        seen_fire.add(name)
    else:
        silent(f'{name} ({tag})', doc)

missing = EXPECTED_FIRES - seen_fire
if missing:
    fails.append(f'expected-FIRES fixture(s) not found in the corpus: {sorted(missing)} — '
                 f'if a fixture was renamed or removed, update EXPECTED_FIRES')
    print(f'  FAIL  expected-FIRES fixtures present')


print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
