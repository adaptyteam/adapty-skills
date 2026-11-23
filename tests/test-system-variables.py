#!/usr/bin/env python3
"""Calibration for system variables — `flowkit.platform_is()` / `SYSTEM_VARIABLES` and the
system-variable checks in `references/verify-config.py`.

Repo-only. Runs the shipped checker as a subprocess and imports flowkit with bytecode writing
off, as `test-custom-tags.py` does.

`system.platform` is read-only device context: the transform service compiles it to the SDK's
own platform value, so nothing in the document produces it. The names in parentheses are the
service's issue codes:

    FIRES   -- a comparison with a value the SDK never reports (invalid_system_variable_value),
               in a visibility condition and in a conditional action; the id in text
               (unsupported_system_variable_use); a setVariable that writes it
               (invalid_action_payload)
    SILENT  -- `== 'ios'`, `!= 'android'`, with no `variables[]` entry

Usage: python3 tests/test-system-variables.py    # 0 all pass, 1 a case regressed
"""
import copy, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk  # noqa: E402

MINE = re.compile(r'system\.platform')
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
    if any(needle in l for l in lines):
        print(f'ok    {name}')
    else:
        fails.append(name)
        print(f'FAIL  {name}: expected {needle!r}, got {lines}')


def silent(name, cfg):
    lines = report(cfg)
    if lines:
        fails.append(name)
        print(f'FAIL  {name}: expected silence, got {lines}')
    else:
        print(f'ok    {name}')


def raises(name, fn, needle):
    try:
        fn()
    except (ValueError, TypeError) as e:
        if needle in str(e):
            print(f'ok    {name}')
        else:
            fails.append(name)
            print(f'FAIL  {name}: raised without {needle!r}: {e}')
        return
    fails.append(name)
    print(f'FAIL  {name}: did not raise')


COLORS = [('bg', 'Background', '#FFFFFF', '#101014'), ('ink', 'Ink', '#111114', '#F5F5F7')]
TYPO = [('body', 'Body', 16, 'regular')]


def build(condition, variables=()):
    node = fk.text(fk.rich('Manage your subscription in App Store settings'), color_id='ink',
                   visibility=fk.when(condition))
    return fk.config(screens=[fk.screen('scr_main', [node], fill_=fk.fill('bg'))],
                     colors=COLORS, typography=TYPO, variables=list(variables))


def main():
    ios = fk.platform_is('ios')
    if ios != {'type': '==', 'left': {'type': 'var', 'variableId': 'system.platform'},
               'right': {'type': 'const', 'value': 'ios'}}:
        fails.append('platform_is shape')
        print(f'FAIL  platform_is builds the builder\'s comparison: {ios}')
    raises('platform_is refuses a value the SDK never reports', lambda: fk.platform_is('huawei'),
           'reports no other value')

    good = build(ios)
    silent('a platform condition resolves without a variables[] entry', good)
    silent('!= android is legal', build(fk.neq(fk.ref('system.platform'), fk.lit('android'))))
    raises('config() refuses a comparison with huawei',
           lambda: build(fk.eq(fk.ref('system.platform'), fk.lit('huawei'))), 'never reports')

    bad = copy.deepcopy(good)
    for o in fk._walk_dicts(bad['screens']):
        if o.get('type') == 'const' and o.get('value') == 'ios':
            o['value'] = 'huawei'
    fires('verify-config: comparison with huawei', bad, 'invalid_system_variable_value')

    act = copy.deepcopy(good)
    elem = next(iter(act['screens'][0]['elements']['map'].values()))
    elem.setdefault('interactions', []).append({'id': 'int_tap', 'trigger': 'tap', 'actions': [
        fk.conditional_action([(fk.eq(fk.ref('system.platform'), fk.lit('web')), [])])]})
    fires('verify-config: comparison inside a conditional action', act,
          'invalid_system_variable_value')

    txt = copy.deepcopy(good)
    elem = next(iter(txt['screens'][0]['elements']['map'].values()))
    elem['props']['visibility'] = {'type': 'visible'}
    elem.setdefault('interactions', []).append({'id': 'int_tap', 'trigger': 'tap', 'actions': [
        {'id': 'act_x', 'type': 'setVariable', 'payload': [
            {'type': 'assign', 'left': {'type': 'var', 'variableId': 'system.platform'},
             'right': {'type': 'const', 'value': 'ios'}}]}]})
    elem['props']['content'] = {'_localizable': True, 'values': {'en': {'type': 'doc', 'content': [
        {'type': 'paragraph', 'content': [
            {'type': 'variable', 'attrs': {'variableId': 'system.platform'}}]}]}}}
    fires('verify-config: system variable in text', txt, 'unsupported_system_variable_use')
    fires('verify-config: setVariable writes it', txt, 'read-only')

    print(f'\n{len(fails)} failed' if fails else '\nall passed')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
