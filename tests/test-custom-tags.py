#!/usr/bin/env python3
"""Calibration for custom tags — `flowkit.app_value()` and the custom-tag checks in
`references/verify-config.py`.

Repo-only. Runs the shipped checker as a subprocess, so nothing writes a `__pycache__` into
`references/`; imports flowkit with bytecode writing off, as `test-flowkit.py` does.

A custom tag is a `variables[]` entry with `external: true`. The app supplies its value at
runtime by the variable's `name`; the variable's `value` is the fallback the SDK shows when the
app does not. Every rule below is one the transform service enforces (the two errors) or warns
on (the two warnings) — the names in parentheses are its issue codes:

    FIRES   -- an invalid name, a reserved name (`PRICE`, `price`, `TIMER_x`) and an empty one
               (custom_tag_invalid_name); a tag name shared with another variable
               (custom_tag_duplicate_name); a tag read by a visibility condition, by conditional
               text, or by setVariable (external_variable_in_logic); a tag inside an alert
               (custom_tag_in_script_context); `external` on an array (ignored, warned)
    SILENT  -- all real exports; a tag in plain text; a dotted and a hyphenated name; two
               regular variables sharing a name (out of scope, as in the service)

flowkit raises on every FIRES shape it can be asked to build, and refuses a fallback whose type
does not match. The last block ties `RESERVED_TAG_NAMES` in the two files together.

Usage: python3 tests/test-custom-tags.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk  # noqa: E402

MINE = re.compile(r'custom tag|external: true')
fails = []


def report(cfg):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(cfg, f)
    try:
        r = subprocess.run([sys.executable, VERIFY, f.name], capture_output=True, text=True)
    finally:
        os.unlink(f.name)
    if r.returncode == 2:
        raise RuntimeError(f'checker could not read the document:\n{r.stdout}{r.stderr}')
    return [l for l in (r.stdout + r.stderr).splitlines() if MINE.search(l)]


def fires(name, cfg, needle):
    lines = report(cfg)
    if not any(needle in l for l in lines):
        fails.append(name)
        print(f'FAIL  {name}: expected {needle!r}, got {lines}')
    else:
        print(f'ok    {name}')


def silent(name, cfg):
    lines = report(cfg)
    if lines:
        fails.append(name)
        print(f'FAIL  {name}: expected silence, got {lines}')
    else:
        print(f'ok    {name}')


def raises(name, fn, needle, exc=(ValueError, TypeError)):
    try:
        fn()
    except exc as e:
        if needle in str(e):
            print(f'ok    {name}')
            return
        fails.append(name)
        print(f'FAIL  {name}: raised without {needle!r}: {e}')
        return
    fails.append(name)
    print(f'FAIL  {name}: did not raise')


def check(name, cond, detail=''):
    if cond:
        print(f'ok    {name}')
    else:
        fails.append(name)
        print(f'FAIL  {name} {detail}')


COLORS = [('bg', 'Background', '#FFFFFF', '#101014'), ('ink', 'Ink', '#111114', '#F5F5F7')]
TYPO = [('body', 'Body', 16, 'regular')]


def build(parts, variables, extra=()):
    nodes = [fk.text(fk.rich(*parts), color_id='ink')] + list(extra)
    return fk.config(screens=[fk.screen('scr_main', nodes, fill_='bg')], colors=COLORS,
                     typography=TYPO, variables=variables)


def main():
    name = fk.app_value('user_name', fallback='there')
    coins = fk.app_value('app.coins-balance', value_type='number', fallback=0)
    good = build(['Hi, ', fk.Var(name), '! You have ', fk.Var(coins), ' coins'], [name, coins])

    # --- flowkit ------------------------------------------------------------------------------
    check('app_value builds an external variable with the fallback as its value',
          name == {'id': 'var_user_name', 'name': 'user_name', 'valueType': 'string',
                   'value': 'there', 'external': True})
    check('a dotted/hyphenated name gets an identifier-safe id',
          coins['id'] == 'var_app_coins_balance')
    check('Var() takes the app_value entry itself',
          fk._span(fk.Var(name)) == {'type': 'variable', 'attrs': {'variableId': 'var_user_name'}})
    raises('a reserved name is refused', lambda: fk.app_value('PRICE', fallback=''), 'reserved')
    raises('a reserved name is refused case-insensitively',
           lambda: fk.app_value('price', fallback=''), 'reserved')
    raises('the TIMER_ prefix is reserved', lambda: fk.app_value('TIMER_hh', fallback=''),
           'reserved')
    raises('a space is refused', lambda: fk.app_value('user name', fallback=''), 'invalid')
    raises('a trailing dot is refused', lambda: fk.app_value('user.', fallback=''), 'invalid')
    raises('an array is refused', lambda: fk.app_value('x', value_type='array', fallback=[]),
           'value_type')
    raises('a number fallback for a string tag is refused',
           lambda: fk.app_value('x', fallback=3), 'not a string')
    raises('a bool is not a number', lambda: fk.app_value('x', value_type='number',
                                                          fallback=True), 'not a number')
    raises('fallback is required', lambda: fk.app_value('x'), 'fallback', exc=TypeError)
    gated = fk.text(fk.rich('y'), color_id='ink')
    gated['props']['visibility'] = fk.when(fk.eq(fk.ref(name['id']), 'Max'))
    raises('a tag in a visibility condition is refused',
           lambda: build(['x'], [name], [gated]), 'read by logic')
    raises('a tag in conditional text is refused',
           lambda: fk.config(screens=[fk.screen('scr_main', [fk.text(fk.switch_rich(
               [(fk.eq(fk.ref(name['id']), 'Max'), ['Hey Max'])], default=['Hi']),
               color_id='ink')], fill_='bg')], colors=COLORS, typography=TYPO,
               variables=[name]),
           'read by logic')
    raises('a tag in an alert is refused',
           lambda: build(['x'], [name], [fk.stack([], actions=[
               fk.alert(title=fk.rich('Hi ', fk.Var(name)))])]),
           'inside an')
    other = {'id': 'var_other', 'name': 'user_name', 'valueType': 'string', 'value': ''}
    raises('a tag name shared with another variable is refused',
           lambda: build(['x'], [name, other]), 'duplicate')
    raises('a variable id declared twice is refused',
           lambda: build(['x'], [name, dict(name)]), 'declared twice')
    check('a tag in plain text builds', good['variables'][0]['external'] is True)

    # --- verify-config: SILENT ----------------------------------------------------------------
    silent('a tag in plain text', good)
    reg = copy.deepcopy(good)
    reg['variables'] += [{'id': 'var_a', 'name': 'dup', 'valueType': 'string', 'value': ''},
                         {'id': 'var_b', 'name': 'dup', 'valueType': 'string', 'value': ''}]
    silent('two regular variables sharing a name (out of scope)', reg)
    for path in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', '*.json'))
                       + glob.glob(os.path.join(ROOT, 'tests', 'fixtures-raw', '*.json'))):
        silent(f'real export {os.path.basename(path)}', json.load(open(path)))

    # --- verify-config: FIRES -----------------------------------------------------------------
    def with_vars(mutate):
        c = copy.deepcopy(good)
        mutate(c['variables'])
        return c

    for bad_name, why in (('PRICE', 'reserved'), ('price', 'reserved'), ('TIMER_mm', 'reserved'),
                          ('user name', 'invalid'), ('.x', 'invalid'), ('', 'empty')):
        fires(f'name {bad_name!r} is {why}',
              with_vars(lambda v, n=bad_name: v[0].update(name=n)), f'is {why}')
    fires('a tag name shared with another variable',
          with_vars(lambda v: v.append({'id': 'var_z', 'name': 'user_name',
                                        'valueType': 'string', 'value': ''})),
          'custom_tag_duplicate_name')
    fires('external on an array is ignored',
          with_vars(lambda v: v.append({'id': 'var_arr', 'name': 'arr', 'valueType': 'array',
                                        'itemType': 'string', 'value': [], 'external': True})),
          'flag is ignored')

    def first_text(c):
        m = c['screens'][0]['elements']['map']
        return next(e for e in m.values() if e['type'] == 'text')

    vis = copy.deepcopy(good)
    first_text(vis)['props']['visibility'] = {
        'type': 'conditional',
        'condition': {'type': '==', 'left': {'type': 'var', 'variableId': 'var_user_name'},
                      'right': {'type': 'const', 'value': 'Max'}}}
    fires('a tag in a visibility condition', vis, 'in logic')

    sw = copy.deepcopy(good)
    first_text(sw)['props']['content']['values']['en'] = {
        'type': 'switch',
        'cases': [[{'type': '>', 'left': {'type': 'var', 'variableId': 'var_app_coins_balance'},
                    'right': {'type': 'const', 'value': 100}},
                   {'type': 'const', 'value': [{'type': 'paragraph', 'content': [
                       {'type': 'text', 'text': 'Rich!', 'attrs': {}}]}]}]],
        'default': {'type': 'const', 'value': [{'type': 'paragraph', 'content': [
            {'type': 'text', 'text': 'Hi', 'attrs': {}}]}]}}
    fires('a tag in conditional text', sw, 'in logic')

    sv = copy.deepcopy(good)
    first_text(sv)['interactions'] = [{'id': 'i1', 'trigger': 'tap', 'actions': [
        fk.set_variable([('var_user_name', 'Max')])]}]
    fires('a tag written by setVariable', sv, 'in logic')

    al = copy.deepcopy(good)
    first_text(al)['interactions'] = [{'id': 'i1', 'trigger': 'tap', 'actions': [
        fk.alert(title=fk.rich('Hi ', fk.Var('var_user_name')))]}]
    fires('a tag inside an alert', al, 'inside an interaction')

    # --- fallbacks a multi-locale flow cannot show ---------------------------------------------
    multi = copy.deepcopy(good)
    multi['locales'].append({'id': 'sr', 'code': 'sr', 'name': 'Serbian'})
    fires('a word fallback on a multi-locale flow', multi, 'untranslated')
    neutral = copy.deepcopy(multi)
    neutral['variables'][0]['value'] = ''
    silent('an empty or numeric fallback on a multi-locale flow', neutral)
    gap = copy.deepcopy(neutral)
    para = first_text(gap)['props']['content']['values']['en'][0]['content']
    para[0]['text'] = 'Hi '
    para.insert(2, {'type': 'text', 'text': ' there', 'attrs': {}})
    vals = first_text(gap)['props']['content']['values']
    vals['sr'] = copy.deepcopy(vals['en'])     # two locales, one element: one warning, not two
    fires('an empty fallback between two spaces', gap, 'double space')
    check('the double-space warning is reported once per element',
          sum('double space' in l for l in report(gap)) == 1)

    # --- the two reserved lists are one list ----------------------------------------------------
    src = open(VERIFY).read()
    block = re.search(r'RESERVED_TAG_NAMES = frozenset\(\{(.*?)\}\)', src, re.S).group(1)
    names = set(re.findall(r"'([A-Z_]+)'", block))
    check('verify-config and flowkit reserve the same names', names == fk.RESERVED_TAG_NAMES,
          f'diff: {names ^ fk.RESERVED_TAG_NAMES}')

    print()
    if fails:
        print(f'{len(fails)} failure(s): ' + ', '.join(fails))
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
