#!/usr/bin/env python3
"""Calibrate device_locale.py through the shipped verifier and flowkit authoring helpers.

Usage: python3 tests/test-device-locale.py    # 0 all pass, 1 a case regressed
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / 'plugin' / 'skills' / 'flow-generator' / 'references'
VERIFY = REFS / 'verify-config.py'
FIXTURES = sorted(ROOT.glob('tests/fixtures*/*.json'))
sys.dont_write_bytecode = True
sys.path.insert(0, str(REFS))
import flowkit as fk

REGION, LANGUAGE = 'system.region', 'system.language'
LOCALE_LINE = re.compile(r'system\.(region|language).*\((invalid_locale_condition|'
                         r'write_to_reserved_locale|unsupported_system_variable_use)\)')
COLORS = [('bg', 'Background', '#FFFFFF', '#101014'), ('ink', 'Ink', '#111114', '#F5F5F7')]
TYPO = [('body', 'Body', 16, 'regular')]
MILES = 'Distance in miles'
FAILS = []


def cmp(operator, vid, value):
    return {'type': operator, 'left': fk.ref(vid), 'right': fk.lit(value)}


def run(path):
    return subprocess.run([sys.executable, '-B', str(VERIFY), path], capture_output=True,
                          text=True, timeout=10)


def verify(cfg):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'config.json'
        path.write_text(json.dumps(cfg), encoding='utf-8')
        return run(path)


def check(name, passed, detail=''):
    print(f'{"ok  " if passed else "FAIL"}  {name}' + (f': {detail}' if not passed else ''))
    if not passed:
        FAILS.append(name)


def expect(name, cfg, code=0, *, issue=(), absent=()):
    result = verify(cfg)
    lines = result.stdout.splitlines()
    matched = not issue or any('ERROR:' in line and all(word in line for word in issue)
                               for line in lines)
    check(name, result.returncode == code and matched
          and all(word not in result.stdout for word in absent),
          f'expected exit {code}, {issue}, without {absent}; got exit {result.returncode}:\n'
          f'{result.stdout}{result.stderr}')


def raises(name, fn, needle):
    try:
        fn()
    except ValueError as exc:
        check(name, needle in str(exc), f'expected {needle!r}; got {exc}')
    else:
        check(name, False, f'expected {needle!r}; config was accepted')


def screen(condition=None, *, actions=()):
    node = fk.text(fk.rich(MILES), color_id='ink', actions=actions,
                   visibility=fk.when(condition or fk.region_is('US')))
    return fk.screen('scr_main', [node], fill_=fk.fill('bg'))


def config(condition=None, *, actions=(), variables=(), components=None):
    return fk.config(screens=[screen(condition, actions=actions)], colors=COLORS,
                     typography=TYPO, variables=variables, components=components)


def first_text(content):
    return next(e for e in content['map'].values() if e['type'] == 'text')


def with_visibility(cond, *, variables=()):
    cfg = config(variables=variables)
    elem = first_text(cfg['screens'][0]['elements'])
    elem['props']['visibility']['condition'] = cond
    return cfg


def with_conditional_action(cond):
    cfg = config(actions=[fk.conditional_action([(fk.language_is('es'), [fk.navigate_back()])])])
    elem = first_text(cfg['screens'][0]['elements'])
    elem['interactions'][0]['actions'][0]['payload']['cases'][0][0] = cond
    return cfg


def with_component(cond):
    return {'cmp_units': screen(cond)['elements']}


def main():
    # Admission: external. Assert the shipped verifier verdict and the authoring helper's output.
    for path in FIXTURES:
        result = run(path)
        lines = [line for line in result.stdout.splitlines() if LOCALE_LINE.search(line)]
        check(f'real export {path.name}', result.returncode in (0, 1) and not lines,
              result.stdout + result.stderr)

    authored = [
        ('region equals an unlisted code', fk.region_is('ZZ'), cmp('==', REGION, 'ZZ')),
        ('region does not equal one code', fk.region_is('DE', negate=True),
         cmp('!=', REGION, 'DE')),
        ('region is any of a list', fk.region_is(['US', 'LR']), cmp('in', REGION, ['US', 'LR'])),
        ('language is none of a list', fk.language_is(('de', 'fil'), negate=True),
         cmp('notIn', LANGUAGE, ['de', 'fil'])),
    ]
    for name, built, expected in authored:
        check(f'{name} output', built == expected, f'expected {expected}; got {built}')
        expect(name, config(built))

    expect('canonical language list in a Conditional Action',
           config(actions=[fk.conditional_action([
               (fk.language_is(['he', 'id', 'yi']), [fk.navigate_back()]),
           ])]))

    invalid = [
        ('region of three letters', cmp('==', REGION, 'USA'), ("'USA'",)),
        ('region with a digit', cmp('==', REGION, '1S'), ("'1S'",)),
        ('lower-case region list member', cmp('in', REGION, ['us']), ("'us'",)),
        ('upper-case language', cmp('==', LANGUAGE, 'EN'), ("'EN'",)),
        ('language with a region', cmp('==', LANGUAGE, 'en-US'), ("'en-US'",)),
        ('legacy iw names he', cmp('==', LANGUAGE, 'iw'), ("Use 'he'",)),
        ('legacy in names id', cmp('in', LANGUAGE, ['en', 'in']), ("Use 'id'", 'value[1]')),
        ('legacy ji names yi', cmp('!=', LANGUAGE, 'ji'), ("Use 'yi'",)),
        ('unset operand', {'type': '==', 'left': fk.ref(REGION), 'right': None}, ('no value',)),
        ('empty list', cmp('notIn', REGION, []), ('non-empty list',)),
        ('non-string list member', cmp('in', REGION, ['US', 42]), ('42', 'value[1]')),
        ('non-string scalar', cmp('==', REGION, 7), ('is not a string',)),
        ('list with equality', cmp('==', REGION, ['US']), ('one string',)),
        ('string with membership', cmp('in', LANGUAGE, 'en'), ('non-empty list', "'en'")),
        ('unsupported operator', cmp('>', REGION, 'US'), ('cannot be compared',)),
        ('bare locale operand', fk.ref(LANGUAGE), ('left operand',)),
        ('raw right operand', {'type': '==', 'left': fk.ref(REGION), 'right': 'US'},
         ('constant on the right',)),
        ('another variable on the right',
         {'type': '==', 'left': fk.ref(REGION), 'right': fk.ref('some_region')},
         ('constant on the right',)),
        ('reserved region on the right of ==',
         {'type': '==', 'left': fk.lit('US'), 'right': fk.ref(REGION)},
         ('left operand', '.condition.right')),
        ('reserved language on the right of !=',
         {'type': '!=', 'left': fk.lit('es'), 'right': fk.ref(LANGUAGE)},
         ('left operand', '.condition.right')),
    ]
    for name, cond, detail in invalid:
        expect(name, with_visibility(cond), 1,
               issue=('invalid_locale_condition', 'props.visibility.condition', *detail),
               absent=('It passes `validate` and ships as is',) if name == 'unset operand' else ())

    malformed = {'type': '>', 'left': {'type': 'var', 'variableId': []}, 'right': fk.lit('US')}
    expect('an invalid id is a shape issue', with_visibility(malformed), 1,
           issue=('invalid condition expression', 'props.visibility.condition.left.variableId'))
    expect('invalid locale in a Conditional Action', with_conditional_action(cmp('==', LANGUAGE, 'EN')),
           1, issue=('invalid_locale_condition', '.actions[0].payload.cases[0][0]'))

    component_cfg = config(components=with_component(fk.region_is('US')))
    component = first_text(component_cfg['components']['cmp_units'])
    component['props']['visibility']['condition'] = cmp('==', REGION, 'USA')
    expect('invalid locale in a shared component', component_cfg, 1,
           issue=('invalid_locale_condition', 'components.cmp_units.map.', 'props.visibility.condition'))

    cfg = config(actions=[fk.set_variable([('some_region', 'US')])])
    element = first_text(cfg['screens'][0]['elements'])
    assignment = element['interactions'][0]['actions'][0]['payload'][0]
    assignment['left'] = fk.ref(REGION)
    expect('reserved assignment target', cfg, 1, issue=('write_to_reserved_locale', '.payload[0].left'))
    cfg = config()
    element = first_text(cfg['screens'][0]['elements'])
    element['props']['content'] = {
        '_localizable': True, 'values': {'en': {'type': 'doc', 'content': [
            {'type': 'paragraph', 'content': [
                {'type': 'variable', 'attrs': {'variableId': LANGUAGE}}]}]}}}
    expect('locale in rich text', cfg, 1, issue=('unsupported_system_variable_use', '.props.content'))

    custom = [{'id': REGION, 'name': 'region', 'valueType': 'number', 'value': 7},
              {'id': LANGUAGE, 'name': 'language', 'valueType': 'string', 'value': 'custom-plan'}]
    shadowed = config(fk.all_(cmp('==', REGION, 7), cmp('==', LANGUAGE, 'custom-plan')),
                      variables=custom, actions=[fk.set_variable([(REGION, 8)])])
    expect('custom declarations keep comparisons and assignment', shadowed,
           absent=('identifier(s) outside',))
    expect('only the declared id is custom',
           with_visibility(cmp('==', LANGUAGE, 'EN'), variables=custom[:1]),
           1, issue=('invalid_locale_condition', LANGUAGE))
    custom_blank = {'type': '==', 'left': fk.ref(REGION), 'right': None}
    result = verify(with_visibility(custom_blank, variables=custom))
    check('legacy warning still describes the custom blank',
          result.returncode == 0 and 'It passes `validate` and ships as is' in result.stdout,
          result.stdout + result.stderr)

    for name, fn, detail in [
        ('region_is refuses lower case', lambda: fk.region_is('us'), 'two upper-case'),
        ('region_is refuses an empty list', lambda: fk.region_is([]), 'non-empty list'),
        ('language_is names he for iw', lambda: fk.language_is('iw'), "Use 'he'"),
        ('config refuses a reserved right operand',
         lambda: config(fk.eq(fk.lit('US'), fk.ref(REGION))), 'left operand'),
        ('config refuses a bare reserved read', lambda: config(fk.ref(LANGUAGE)), 'left operand'),
        ('config refuses a reserved write',
         lambda: config(actions=[fk.set_variable([(REGION, 'US')])]), 'read-only'),
        ('config refuses a reserved read in an assignment',
         lambda: config(variables=custom[:1],
                        actions=[fk.set_variable([(REGION, fk.ref(LANGUAGE))])]), 'left operand'),
        ('config refuses a bad comparison in a component',
         lambda: config(components=with_component(cmp('==', REGION, 'USA'))), 'components.cmp_units'),
    ]:
        raises(name, fn, detail)

    print(f'\n{len(FAILS)} failed' if FAILS else '\nall passed')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
