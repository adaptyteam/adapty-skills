#!/usr/bin/env python3
"""Calibration for Formula and Date variables: `references/formulas.py`, the checks it adds to
`references/verify-config.py`, and `flowkit.formula()` / `date_variable()` / `fx()` / `config()`.

Repo-only. Runs the shipped checker as a subprocess and imports flowkit with bytecode writing
off, as `test-system-variables.py` does. The base document is the quiz fixture: its `name`
text input is an answer a formula reads as a number, and `products` is a product group.

Measured against the live validate endpoint, on a one-screen flow:

    SILENT  -- `round({{var_w}} / ({{var_h}} * {{var_h}}), 1)` and `addDays(today(), 7)` shown in
               text, and `var_bmi > 25` in a visibility condition: valid, no issues;
               a formula `{{age.value}}` over a text input, compared with `< 18`: valid;
               a custom variable referenced by its name, `{{weight}} + 1`: valid
    FIRES   -- `{{var_w}} * 1,5`: formula_syntax_error "Use a dot in a decimal number";
               Set Variable writing a formula: set_variable_formula_target

The other codes, catalog prices with `formula_undeclared_product` and the date differences are
read from the formula checker the builder and the transformer share, and from the transformer.

Usage: python3 tests/test-formulas.py    # 0 all pass, 1 a case regressed
"""
import copy, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
QUIZ = os.path.join(ROOT, 'tests', 'fixtures', 'onboarding-quiz-paywall.json')
sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk  # noqa: E402
import formulas  # noqa: E402

fails = []


def base(*variables, text_vars=()):
    """The quiz fixture plus `variables`; each id in `text_vars` is shown in a rich text."""
    d = json.load(open(QUIZ))
    d['variables'] = list(d.get('variables') or []) + [copy.deepcopy(v) for v in variables]
    para = d['localization']['content']['lc_27']['values']['en'][0]['content']
    for vid in text_vars:
        para.append({'type': 'variable', 'attrs': {'variableId': vid}})
    return d


def first(d, pred):
    for s in d['screens']:
        for e in s['elements']['map'].values():
            if pred(e):
                return e
    raise AssertionError('no element matched')


def checker(cfg):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(cfg, f)
    try:
        r = subprocess.run([sys.executable, VERIFY, f.name], capture_output=True, text=True)
    finally:
        os.unlink(f.name)
    if r.returncode == 2 or 'CHECKER ERROR' in r.stdout:
        raise RuntimeError(f'checker could not read the document:\n{r.stdout}{r.stderr}')
    return (r.stdout + r.stderr).splitlines()


def codes(cfg):
    return sorted({c for c, _, _ in formulas.issues(cfg)})


def expect(name, got, want):
    if got == want:
        print(f'ok    {name}')
    else:
        fails.append(name)
        print(f'FAIL  {name}: expected {want!r}, got {got!r}')


W = {'id': 'var_w', 'name': 'weight', 'valueType': 'number', 'value': 70}
H = {'id': 'var_h', 'name': 'height', 'valueType': 'number', 'value': 1.75}
S = {'id': 'var_s', 'name': 'label', 'valueType': 'string', 'value': 'x'}
BMI = fk.formula('bmi', 'round({{var_w}} / ({{var_h}} * {{var_h}}), 1)', variable_id='var_bmi')
END = fk.formula('plan_end', 'addDays(today(), 7)', variable_id='var_end', date_format='month-day')


def formula(expr):
    return {'id': 'var_x', 'name': 'x', 'valueType': 'formula', 'expression': expr}


# ---------------------------------------------------------------- SILENT: what the publish takes
print('silent')
for name, extra in (
        ('number and date formulas', ()),
        ('an answer read as a number', (formula('{{name.value}} * 2'),)),
        ('a custom variable by its name', (formula('{{weight}} + 1'),)),
        ('the selected plan price per month', (formula('{{products.selectedProduct.prod_price}} / 12'),)),
        ('the offer price', (formula('round({{products.selectedProduct.offer_price}}, 2)'),)),
        ('the end of the selected offer', (formula('addOfferDuration(today(), {{products.selectedProduct}})'),)),
        ('floor, mod and a leading minus', (formula('floor(mod(-{{var_w}}, 3)) - -1'),)),
        ('a formula reading a formula', (formula('addMonths({{var_end}}, 2)'),)),
        ('a Date variable in a date function', ({'id': 'var_d', 'name': 'start', 'valueType': 'date',
                                                 'value': '2026-12-01'}, formula('addWeeks({{var_d}}, 1)'))),
):
    d = base(W, H, BMI, END, *extra, text_vars=('var_bmi', 'var_end'))
    expect(f'formulas.py: {name}', codes(d), [])
    lines = checker(d)
    expect(f'verify-config: {name} has no formula ERROR',
           [l for l in lines if 'ERROR' in l and ('formula' in l.lower() or 'variable' in l.lower())], [])

d = base(W, H, BMI, END, text_vars=('var_bmi', 'var_end'))
expect('a formula shown in text is not "blank on a device"',
       [l for l in checker(d) if 'blank on a device' in l], [])
d = base(W, H, BMI)
first(d, lambda e: e['type'] == 'text')['props']['visibility'] = {
    'type': 'conditional', 'condition': {'type': '>', 'left': {'type': 'var', 'variableId': 'var_bmi'},
                                         'right': {'type': 'const', 'value': 25}}}
expect('a formula in a > condition', codes(d), [])

# ---------------------------------------------------------------- FIRES: what the publish refuses
print('fires')
for name, expr, code in (
        ('a decimal comma', '{{var_w}} * 1,5', 'formula_syntax_error'),
        ('an unknown function, names are case-sensitive', 'Round({{var_w}})', 'formula_syntax_error'),
        ('a power operator', '{{var_w}} ^ 2', 'formula_syntax_error'),
        ('an unclosed bracket', '({{var_w}} + 1', 'formula_syntax_error'),
        ('mod with one argument', 'mod({{var_w}})', 'formula_argument_count'),
        ('today with an argument', 'today(1)', 'formula_argument_count'),
        ('a Date in arithmetic', 'today() + 1', 'formula_operand_type'),
        ('round to 7 decimals', 'round({{var_w}}, 7)', 'formula_operand_type'),
        ('a string variable', '{{var_s}} + 1', 'formula_operand_type'),
        ('a product field other than the prices', '{{products.selectedProduct.prod_title}} + 1', 'formula_operand_type'),
        ('a product outside addOfferDuration', '{{products.selectedProduct}} + 1', 'formula_operand_type'),
        ('a selection answer', '{{quiz.selectedOptionId}} + 1', 'formula_unknown_reference'),
        ('a deleted variable', '{{var_gone}} + 1', 'formula_unknown_reference'),
        ('a formula reading itself', '{{var_x}} + 1', 'formula_cycle'),
):
    d = base(W, H, S, formula(expr))
    expect(f'formulas.py: {name}', codes(d), [code])
    expect(f'verify-config: {name} is an ERROR',
           any('ERROR' in l and code in l for l in checker(d)), True)

d = base(W, H, BMI, {'id': 'var_dup', 'name': 'name.value', 'valueType': 'number', 'value': 1},
         formula('{{name.value}} + 1'))
expect('a variable named like an answer', codes(d), ['formula_ambiguous_reference'])

d = base(W, H, BMI)
first(d, lambda e: e.get('interactions'))['interactions'][0]['actions'].insert(
    0, fk.set_variable([('var_bmi', 1)]))
expect('Set Variable writes a formula', codes(d), ['set_variable_formula_target'])
expect('verify-config: Set Variable writes a formula is an ERROR',
       any('ERROR' in l and 'set_variable_formula_target' in l for l in checker(d)), True)

d = base(W, END)
first(d, lambda e: e.get('interactions'))['interactions'][0]['actions'].insert(
    0, {'id': 'act_alert', 'type': 'alert', 'payload': {'title': [
        {'type': 'paragraph', 'content': [{'type': 'variable', 'attrs': {'variableId': 'var_end'}}]}]}})
expect('a Date formula in an alert title', codes(d), ['date_or_formula_in_action_text'])

for name, v, code in (
        ('a formula with a value', dict(BMI, value=3), 'invalid_formula_variable'),
        ('an external formula', dict(BMI, external=True), 'invalid_formula_variable'),
        ('a date that is not YYYY-MM-DD', {'id': 'var_d', 'name': 'd', 'valueType': 'date',
                                           'value': '01.12.2026'}, 'invalid_formula_variable'),
        ('an unknown dateFormat', dict(END, dateFormat='full'), 'invalid_formula_variable'),
):
    expect(name, codes(base(W, H, v)), [code])

# ---------------------------------------------------------------- catalog prices
# Admission: external. The publish reads a catalog product's price only through a Products row
# with no offer and no plan on a screen of the flow, and refuses a formula that the flow reads
# with no such row (`formula_undeclared_product`); a formula that nothing reads publishes.
print('catalog prices')
PAYWALL, PROD = 'scr_QXcVa3FZ', '8fb58c50-7c05-42f9-a8e3-8d0fde19505a'  # its base row is on PAYWALL
SAVING = '{{weekly.prod_price}} * 52 - {{%s.prod_price}}' % PROD


def para(*vids):
    return [{'type': 'paragraph', 'content': [{'type': 'variable', 'attrs': {'variableId': v}}
                                              for v in vids]}]


def rows(*entries, screen=PAYWALL):
    def edit(d):
        d['_meta']['screens'].setdefault(screen, {'products': []})['products'] += [
            dict(e, flowProductId=f'fp_{i}_{screen}') for i, e in enumerate(entries)]
    return edit


def tap_actions(d):
    return first(d, lambda e: e.get('interactions'))['interactions'][0]['actions']


def card(placed):
    def edit(d):
        d['components']['card'] = {
            'map': {'card_text': {'id': 'card_text', 'type': 'text',
                                  'props': {'content': {'_lid': 'lc_card'}}}},
            'hierarchy': {'id': 'root', 'children': [{'id': 'card_text'}]}}
        d['localization']['content']['lc_card'] = {'kind': 'rich-text', 'values': {'en': para('var_x')}}
        if placed:
            d['screens'][2]['elements']['hierarchy']['children'].append({'id': 'card', 'type': 'global'})
    return edit


def in_progress_bar(d):
    """The bar shows on every screen that enables it, so it is read with no placement."""
    pb = d['components']['pb_dl05vuVs']
    pb['map']['pb_text'] = {'id': 'pb_text', 'type': 'text', 'props': {'content': {'_lid': 'lc_pb'}}}
    pb['hierarchy']['children'].append({'id': 'pb_text'})
    d['localization']['content']['lc_pb'] = {'kind': 'rich-text', 'values': {'en': para('var_x')}}
    for s in d['screens']:
        h = s['elements']['hierarchy']
        h['children'] = [c for c in h['children'] if c.get('type') != 'global']


def in_text(d):
    d['localization']['content']['lc_27']['values']['en'] = para('var_x')


def in_translation(d):
    d['localization']['locales'].append({'id': 'es', 'code': 'es', 'name': 'Spanish'})
    in_undeclared_locale(d)


def in_undeclared_locale(d):
    """The publish drops a value of a locale that `localization.locales` does not declare."""
    d['localization']['content']['lc_27']['values']['es'] = para('var_x')


def in_second_progress_bar(d):
    """The publish shows only the first progress bar and ignores another one."""
    bar = d['components']['pb_dl05vuVs']['map']['el_P6zW0Xfzjx']
    d['components']['pb_second'] = {
        'map': {'pb2_bar': dict(bar, id='pb2_bar'),
                'pb2_text': {'id': 'pb2_text', 'type': 'text', 'props': {'content': {'_lid': 'lc_pb2'}}}},
        'hierarchy': {'id': 'root', 'children': [{'id': 'pb2_bar'}, {'id': 'pb2_text'}]}}
    d['localization']['content']['lc_pb2'] = {'kind': 'rich-text', 'values': {'en': para('var_x')}}


def in_action_condition(d):
    tap_actions(d).insert(0, {'id': 'act_if', 'type': 'conditional', 'payload': {
        'type': 'switch', 'cases': [[fk.gt(fk.ref('var_x'), 1), []]],
        'default': {'type': 'const', 'value': []}}})


def through_formula(d):
    d['variables'].append(fk.formula('double', '{{var_x}} * 2', variable_id='var_double'))
    d['localization']['content']['lc_27']['values']['en'] = para('var_double')


def build(expr, *edits):
    d = base(formula(expr))
    for edit in edits:
        edit(d)
    return d


WEEKLY = rows({'id': 'weekly'})
for name, d, want in (
        ('a catalog price with its base row on another screen', build(SAVING, in_text, WEEKLY), []),
        ('a catalog per-week price', build('{{weekly.prod_price_per_week}} * 4', in_text, WEEKLY), []),
        ('a per-month price of the selected plan',
         build('{{products.selectedProduct.prod_price_per_month}} * 12', in_text), []),
        ('nothing reads the formula', build(SAVING), []),
        ('only a component that no screen places reads it', build(SAVING, card(False)), []),
        ('a read formula with no row of the product', build(SAVING, in_text),
         ['formula_undeclared_product']),
        ('only an offer row and a plan row', build(SAVING, in_text, rows(
            {'id': 'weekly', 'offerId': 'intro'}, {'id': 'weekly', 'billingPlanId': 'monthly'})),
         ['formula_undeclared_product']),
        ('a base row whose id is not a string', build(SAVING, in_text, rows({'id': 5})),
         ['formula_undeclared_product']),
        ('the base row only under a deleted screen',
         build(SAVING, in_text, rows({'id': 'weekly'}, screen='scr_deleted')),
         ['formula_undeclared_product']),
        ('read only in one translation', build(SAVING, in_translation), ['formula_undeclared_product']),
        ('read only in a locale the flow does not declare', build(SAVING, in_undeclared_locale), []),
        ('read only through a placed component', build(SAVING, card(True)), ['formula_undeclared_product']),
        ('read only in the progress bar', build(SAVING, in_progress_bar), ['formula_undeclared_product']),
        ('read only in a second progress bar', build(SAVING, in_second_progress_bar), []),
        ('read only in an action condition', build(SAVING, in_action_condition),
         ['formula_undeclared_product']),
        ('read only through another formula', build(SAVING, through_formula),
         ['formula_undeclared_product']),
        ('an offer of a catalog product', build('{{weekly(intro).prod_price}}', WEEKLY),
         ['formula_operand_type']),
        ('a billing plan of a catalog product', build('{{weekly@monthly.prod_price}}', WEEKLY),
         ['formula_operand_type']),
        ('a catalog field other than the prices', build('{{weekly.offer_price}}', WEEKLY),
         ['formula_operand_type']),
        ('a group head keeps its own meaning', build('{{products.prod_price}}'),
         ['formula_unknown_reference']),
        ('a variable head keeps its own meaning',
         build('{{height.prod_price}}', lambda d: d['variables'].append(H)), ['formula_unknown_reference']),
        ('an answer head keeps its own meaning', build('{{name.prod_price}}'),
         ['formula_unknown_reference']),
):
    expect(f'formulas.py: {name}', codes(d), want)

d = build(SAVING, in_text)
expect('the undeclared product message names the formula and the product',
       [(w, m) for c, w, m in formulas.issues(d)],
       [(f'variables[{len(d["variables"]) - 1}].expression',
         'Formula "x": the product "weekly" has no Products row with no offer and no plan on any '
         'screen of the flow; add it to the Products of a screen that reads the formula')])
expect('an offer is refused as not supported yet',
       [m for _, _, m in formulas.issues(build('{{weekly(intro).prod_price}}', WEEKLY))],
       ['Formula "x": {{weekly(intro).prod_price}}: Offers, billing plans and fields other than '
        'prod_price, prod_price_per_day, prod_price_per_week, prod_price_per_month and '
        'prod_price_per_year of a catalog product are not supported yet'])

# Admission: external. The four date differences take two dates and give a Number.
print('date differences')
D = {'id': 'var_d', 'name': 'start', 'valueType': 'date', 'value': '2026-12-01'}
for name, expr, want in (
        ('daysBetween two dates', 'daysBetween({{var_d}}, today())', []),
        ('daysBetween a number and a date', 'daysBetween(5, today())', ['formula_operand_type']),
        ('a date difference where a date goes', 'addDays(monthsBetween({{var_d}}, today()), 1)',
         ['formula_operand_type']),
):
    expect(f'formulas.py: {name}', codes(base(D, formula(expr))), want)

# ---------------------------------------------------------------- flowkit
print('flowkit')
expect('fx() of an entry', fk.fx(W), '{{var_w}}')
expect('fx() of a path', fk.fx('age.value'), '{{age.value}}')
for name, call in (
        ('formula() refuses an unknown date_format', lambda: fk.formula('x', 'today()', date_format='full')),
        ('date_variable() refuses a non-ISO day', lambda: fk.date_variable('d', '12/01/2026')),
        ('number_variable() refuses a string', lambda: fk.number_variable('n', '7')),
):
    try:
        call()
        fails.append(name)
        print(f'FAIL  {name}: no error')
    except (ValueError, TypeError):
        print(f'ok    {name}')

bmi = fk.formula('bmi', f'round({fk.fx(W)} / ({fk.fx(H)} * {fk.fx(H)}), 1)')
screen = fk.screen('scr_a', [fk.text(fk.rich('Your BMI is ', fk.Var(bmi)))])
doc = fk.config(screens=[screen], variables=[W, H, bmi])
expect('config() takes a well-formed formula', codes(doc), [])
try:
    fk.config(screens=[screen], variables=[W, H, fk.formula('bmi', f'{fk.fx(W)} * 1,5')])
    fails.append('config() refuses a decimal comma')
    print('FAIL  config() refuses a decimal comma: no error')
except ValueError as e:
    expect('config() refuses a decimal comma', 'formula_syntax_error' in str(e), True)

weight = fk.number_input('weight', number_format='decimal-point')
height = fk.number_input('height', number_format='decimal-point')
h = fk.fx('height.value')
bmi = fk.formula('bmi', f'round({fk.fx("weight.value")} / ({h} * {h}), 1)')
goal = fk.formula('goal_date', 'addWeeks(today(), 8)', date_format='month-day')
result = fk.screen('scr_result', [
    weight, height,
    fk.text(fk.rich('Your BMI is ', fk.Var(bmi))),
    fk.text(fk.rich('Reach your goal by ', fk.Var(goal))),
    fk.text('Above the healthy range', visibility=fk.when(fk.gt(fk.ref(bmi['id']), 25))),
])
doc = fk.config(screens=[result], variables=[bmi, goal], typography=[('body', 'Body', 16, 'regular')])
expect('the patterns.md formula example builds clean', codes(doc), [])
expect('verify-config: the patterns.md example has no ERROR or blank warning',
       [l for l in checker(doc) if 'ERROR' in l or 'blank on a device' in l], [])

# Admission: external. Without a row of the product on the screen that reads it, the publish
# refuses the flow; the Flow Builder adds that row itself, and so does config().
saving = fk.formula('saving', '{{weekly.prod_price}} * 52 - {{annual.prod_price}}')
plans = fk.screen('scr_plans', [fk.text('Choose a plan')])
offer = fk.screen('scr_offer', [fk.text(fk.rich('Save ', fk.Var(saving)))])
doc = fk.config(screens=[plans, offer], variables=[saving], typography=[('body', 'Body', 16, 'regular')],
                meta_screens=[fk.predeclare('scr_offer', ['annual'])])
expect('config() declares a catalog price on the screen that reads it, once',
       (doc['_meta']['screens'], [s.get('products') for s in doc['screens']]),
       ({'scr_offer': {'products': [
           {'id': 'annual', 'flowProductId': fk.flow_product_id('scr_offer', 'annual')},
           {'id': 'weekly', 'flowProductId': fk.flow_product_id('scr_offer', 'weekly')}]}},
        [None, [{'id': 'weekly'}, {'id': 'annual'}]]))
expect('verify-config: a built catalog price formula has no ERROR',
       [l for l in checker(doc) if 'ERROR' in l], [])

print()
if fails:
    print(f'{len(fails)} FAILED')
    sys.exit(1)
print('all checks passed')
