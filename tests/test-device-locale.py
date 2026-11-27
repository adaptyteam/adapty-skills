#!/usr/bin/env python3
"""Calibration for the device locale operands `system.region` and `system.language` --
`flowkit.region_is()` / `language_is()` and the locale checks in `references/verify-config.py`.

Repo-only. Runs the shipped checker as a subprocess and imports flowkit with bytecode writing
off, as `test-system-variables.py` does. The names in parentheses are the service's issue codes:

    FIRES   -- a value of the wrong shape, a legacy language code (naming the current one), an
               unset value, an empty list, a non-string, a list with `==`, a string with `in`,
               any other operator, a non-constant side (invalid_locale_condition); a setVariable
               that writes either id (write_to_reserved_locale); the id in text
               (unsupported_system_variable_use)
    SILENT  -- every real export in tests/fixtures; one string with `==` / `!=` and a non-empty
               list with `in` / `notIn`, in a visibility condition and a conditional action; a
               `variables[]` entry with the same id, compared with its own values and assigned

Usage: python3 tests/test-device-locale.py    # 0 all pass, 1 a case regressed
"""
import copy, glob, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
FIXTURES = sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures*', '*.json')))
sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk

R, L = 'system.region', 'system.language'
LOCALE_LINE = re.compile(r'system\.(region|language).*\((invalid_locale_condition|'
                         r'write_to_reserved_locale|unsupported_system_variable_use)\)')
fails = []


def var(vid):
    return {'type': 'var', 'variableId': vid}


def const(value):
    return {'type': 'const', 'value': value}


def cmp(t, vid, value):
    return {'type': t, 'left': var(vid), 'right': const(value)}


def run(path):
    r = subprocess.run([sys.executable, '-B', VERIFY, path], capture_output=True, text=True,
                       env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    if r.returncode == 2:
        raise RuntimeError(f'checker could not read {path}:\n{r.stdout}{r.stderr}')
    return [l for l in (r.stdout + r.stderr).splitlines() if LOCALE_LINE.search(l)]


def report(cfg):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(cfg, f)
    try:
        return run(f.name)
    finally:
        os.unlink(f.name)


def expect(name, lines, needles):
    if not needles:
        ok = not lines
    else:
        ok = any(all(n in l for n in needles) for l in lines)
    detail = '' if ok else f': expected {needles}, got {lines}'
    print(f'{"ok  " if ok else "FAIL"}  {name}{detail}')
    if not ok:
        fails.append(name)


def raises(name, fn, needle):
    try:
        fn()
    except (ValueError, TypeError) as e:
        ok = needle in str(e)
        print(f'{"ok  " if ok else "FAIL"}  {name}' + ('' if ok else f': {e}'))
        if not ok:
            fails.append(name)
        return
    fails.append(name)
    print(f'FAIL  {name}: did not raise')


COLORS = [('bg', 'Background', '#FFFFFF', '#101014'), ('ink', 'Ink', '#111114', '#F5F5F7')]
TYPO = [('body', 'Body', 16, 'regular')]


def base(condition=None):
    """A one-screen flow with a text shown by `condition`."""
    node = fk.text(fk.rich('Distance in miles'), color_id='ink',
                   visibility=fk.when(condition or fk.region_is('US')))
    return fk.config(screens=[fk.screen('scr_main', [node], fill_=fk.fill('bg'))],
                     colors=COLORS, typography=TYPO)


def text_id(cfg):
    return next(k for k, e in cfg['screens'][0]['elements']['map'].items()
                if e.get('type') == 'text')


def with_visibility(cond, variables=None):
    cfg = base()
    cfg['screens'][0]['elements']['map'][text_id(cfg)]['props']['visibility'] = {
        'type': 'conditional', 'condition': cond}
    if variables is not None:
        cfg['variables'] = variables
    return cfg


def with_actions(actions, variables=None):
    cfg = base()
    elem = cfg['screens'][0]['elements']['map'][text_id(cfg)]
    elem.setdefault('interactions', []).append({'id': 'int_tap', 'trigger': 'tap',
                                                'actions': actions})
    if variables is not None:
        cfg['variables'] = variables
    return cfg


def conditional(cond):
    return [{'id': 'act_cond', 'type': 'conditional',
             'payload': {'cases': [[cond, [{'id': 'act_nav', 'type': 'navigateBack'}]]],
                         'default': []}}]


def assign(vid, value):
    return [{'id': 'act_set', 'type': 'setVariable',
             'payload': [{'type': 'assign', 'left': var(vid), 'right': const(value)}]}]


VALID = [
    ('region == US', cmp('==', R, 'US')),
    ('region != DE', cmp('!=', R, 'DE')),
    ('region in a list', cmp('in', R, ['US', 'LR', 'MM'])),
    ('region notIn a list', cmp('notIn', R, ['US'])),
    ('language == a three-letter code', cmp('==', L, 'fil')),
    ('language in the current he/id/yi', cmp('in', L, ['he', 'id', 'yi'])),
    ('language notIn a list', cmp('notIn', L, ['en'])),
    ('the constant on the left of ==', {'type': '==', 'left': const('US'), 'right': var(R)}),
    ('region and language under &&', {'type': '&&', 'predicates': [
        cmp('==', R, 'GE'), cmp('==', L, 'ru')]}),
]

INVALID = [
    ('region of three letters', cmp('==', R, 'USA'), ['invalid_locale_condition', "'USA'"]),
    ('region with a digit', cmp('==', R, '1S'), ['invalid_locale_condition', "'1S'"]),
    ('region in lower case', cmp('in', R, ['us']), ['invalid_locale_condition', "'us'"]),
    ('language in upper case', cmp('==', L, 'EN'), ['invalid_locale_condition', "'EN'"]),
    ('language with a region', cmp('==', L, 'en-US'), ['invalid_locale_condition']),
    ('legacy iw names he', cmp('==', L, 'iw'), ['invalid_locale_condition', "use 'he'"]),
    ('legacy in as a list member names id', cmp('in', L, ['en', 'in']),
     ['invalid_locale_condition', "use 'id'", 'value[1]']),
    ('legacy ji names yi', cmp('!=', L, 'ji'), ['invalid_locale_condition', "use 'yi'"]),
    ('unset operand', {'type': '==', 'left': var(R), 'right': None},
     ['invalid_locale_condition', 'no value']),
    ('unset constant', cmp('in', L, None), ['invalid_locale_condition', 'no value']),
    ('empty list', cmp('notIn', R, []), ['invalid_locale_condition', 'empty list']),
    ('non-string list member', cmp('in', R, ['US', 42]), ['invalid_locale_condition', '42']),
    ('a number with ==', cmp('==', R, 7), ['invalid_locale_condition', 'not a string']),
    ('a list with ==', cmp('==', R, ['US']), ['invalid_locale_condition', 'a list']),
    ('a string with in', cmp('in', L, 'en'), ['invalid_locale_condition', 'takes a list']),
    ('operator >', cmp('>', R, 'US'), ['invalid_locale_condition', 'outside a comparison']),
    ('operator notEmpty', {'type': 'notEmpty', 'left': var(L)},
     ['invalid_locale_condition', 'outside a comparison']),
    ('the id as the list side of in', {'type': 'in', 'left': const('US'), 'right': var(R)},
     ['invalid_locale_condition', 'list side']),
    ('compared with another variable', {'type': '==', 'left': var(R), 'right': var(L)},
     ['invalid_locale_condition', 'constant']),
]


def main():
    # Real exports: the corpus has no locale operand, and the new checks stay silent on it.
    for path in FIXTURES:
        expect(f'real export {os.path.basename(path)}', run(path), None)

    for name, cond in VALID:
        expect(f'visibility: {name}', report(with_visibility(cond)), None)
        expect(f'conditional action: {name}', report(with_actions(conditional(cond))), None)
    for name, cond, needles in INVALID:
        expect(f'visibility: {name}', report(with_visibility(cond)), needles)
        expect(f'conditional action: {name}', report(with_actions(conditional(cond))), needles)

    cfg = with_visibility(cmp('==', R, 'USA'))
    expect('the error names the element and the condition path', report(cfg),
           [f'elements.map.{text_id(cfg)}.props.visibility.condition'])
    expect('the conditional action error names its path',
           report(with_actions(conditional(cmp('==', L, 'EN')))),
           ['interactions[0].actions[0].payload.cases[0][0]'])
    for vid in (R, L):
        expect(f'setVariable writes {vid}', report(with_actions(assign(vid, 'US'))),
               ['write_to_reserved_locale', '.payload[0].left'])
        txt = with_visibility(cmp('==', R, 'US'))
        txt['screens'][0]['elements']['map'][text_id(txt)]['props']['content'] = {
            '_localizable': True, 'values': {'en': {'type': 'doc', 'content': [
                {'type': 'paragraph', 'content': [
                    {'type': 'variable', 'attrs': {'variableId': vid}}]}]}}}
        expect(f'{vid} in text', report(txt), ['unsupported_system_variable_use'])

    # A declared variable with the same id is an ordinary custom one: its own values, a write.
    custom = [{'id': R, 'name': 'region', 'valueType': 'number', 'value': 7},
              {'id': L, 'name': 'language', 'valueType': 'string', 'value': 'custom-plan'}]
    expect('custom region compared with 7', report(with_visibility(cmp('==', R, 7), custom)),
           None)
    expect('custom language compared with custom-plan',
           report(with_actions(conditional(cmp('==', L, 'custom-plan')), custom)), None)
    expect('custom region assigned 8', report(with_actions(assign(R, 8), custom)), None)
    expect('custom declared, the other id is still checked',
           report(with_visibility(cmp('==', L, 'EN'), custom[:1])),
           ['invalid_locale_condition', 'system.language'])

    # flowkit: the helpers emit the builder's shape and refuse what the publish refuses.
    shapes = [
        ("region_is('US')", fk.region_is('US'), cmp('==', R, 'US')),
        ("region_is([...])", fk.region_is(['US', 'LR']), cmp('in', R, ['US', 'LR'])),
        ("region_is(..., negate=True)", fk.region_is('US', negate=True), cmp('!=', R, 'US')),
        ("language_is([...], negate=True)", fk.language_is(('de', 'fil'), negate=True),
         cmp('notIn', L, ['de', 'fil'])),
    ]
    for name, got, want in shapes:
        ok = got == want
        print(f'{"ok  " if ok else "FAIL"}  flowkit {name}' + ('' if ok else f': {got}'))
        if not ok:
            fails.append(name)
    for name, fn, needle in [
        ('region_is refuses lower case', lambda: fk.region_is('us'), 'two upper-case'),
        ('region_is refuses an empty list', lambda: fk.region_is([]), 'non-empty list'),
        ('language_is names he for iw', lambda: fk.language_is('iw'), "use 'he'"),
        ('language_is names id for in', lambda: fk.language_is(['en', 'in']), "use 'id'"),
        ('language_is names yi for ji', lambda: fk.language_is('ji'), "use 'yi'"),
        ('config() refuses a bad region', lambda: base(fk.eq(fk.ref(R), fk.lit('USA'))),
         'two upper-case'),
        ('config() refuses operator >', lambda: base(fk.gt(fk.ref(R), 'US')), 'cannot be'),
        ('config() refuses an empty list', lambda: base(fk.in_(fk.ref(L), fk.lit([]))),
         'non-empty list'),
        ('config() refuses a write', lambda: with_built_action(fk.set_variable([(R, 'US')])),
         'read-only'),
    ]:
        raises(name, fn, needle)
    try:
        cfg = with_built_action(fk.conditional_action(
            [(fk.language_is('de'), [fk.navigate('scr_main')])]))
        cfg2 = base(fk.region_is(['US', 'LR', 'MM'], negate=True))
        expect('flowkit output passes the checker', report(cfg) + report(cfg2), None)
    except (ValueError, TypeError) as e:
        fails.append('flowkit builds a locale flow')
        print(f'FAIL  flowkit builds a locale flow: {e}')

    print(f'\n{len(fails)} failed' if fails else '\nall passed')
    return 1 if fails else 0


def with_built_action(action):
    node = fk.text(fk.rich('Continue'), color_id='ink', actions=[action])
    return fk.config(screens=[fk.screen('scr_main', [node], fill_=fk.fill('bg'))],
                     colors=COLORS, typography=TYPO)


if __name__ == '__main__':
    sys.exit(main())
