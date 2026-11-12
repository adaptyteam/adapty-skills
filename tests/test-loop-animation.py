#!/usr/bin/env python3
"""An element's own looping `props.animation`: verify-config.py warns on each case the
transformer skips (it publishes and nothing moves), and stays silent on every kind it plays.

Runs verify-config.py as a subprocess, so nothing writes a `__pycache__` into `references/`.
Every FIRES case has a SILENT twin.
"""
import copy, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references')
VERIFY = os.path.join(REFS, 'verify-config.py')
FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'comparison-paywall.json')
CTA = 'el_F0vCURJIk3'      # Fill x Hug, one theme-colour fill
CLOSE = 'el_0CtOCYAnUI'    # fixed 32 x 32, no fill
fails = []

sys.dont_write_bytecode = True
sys.path.insert(0, REFS)
import flowkit as fk  # noqa: E402


def check(name, ok, detail=''):
    print(('  ok    ' if ok else '  FAIL  ') + name)
    if not ok:
        fails.append(f'{name}: {str(detail)[:600]}')


def base():
    d = json.load(open(FIXTURE))
    return d.get('config', d)


def element(d, eid):
    for s in d['screens']:
        if eid in s['elements']['map']:
            return s['elements']['map'][eid]
    raise KeyError(eid)


def warnings(d):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'c.json')
        json.dump(d, open(p, 'w'))
        r = subprocess.run([sys.executable, VERIFY, p], capture_output=True, text=True)
    assert 'Traceback' not in r.stderr + r.stdout, r.stderr + r.stdout
    return [l for l in r.stdout.splitlines() if 'animation' in l or 'pulse' in l
            or 'wave' in l or 'shimmer' in l or 'color-shift' in l]


def with_anim(eid, anim, **props):
    d = base()
    e = element(d, eid)
    e['props'].update(props)
    e['props']['animation'] = anim
    return d


def main():
    check('the fixture alone is silent', warnings(base()) == [], warnings(base()))

    fixed = {'width': {'type': 'fixed', 'value': 300}, 'height': {'type': 'fixed', 'value': 56}}
    # Every kind at the builder's defaults, on a layout it plays on: silent.
    for kind in fk.LOOP_ANIMATIONS:
        w = warnings(with_anim(CTA, fk.loop_animation(kind), **fixed))
        check(f'silent: {kind} at its defaults on a fixed CTA', w == [], w)

    fires = {
        'unknown type': with_anim(CTA, {**fk.loop_animation('pulse'), 'type': 'sparkle'}),
        'missing waveColor': with_anim(CTA, {k: v for k, v in fk.loop_animation('wave-fill').items()
                                             if k != 'waveColor'}, **fixed),
        'pulse with a wave key': with_anim(CTA, {**fk.loop_animation('pulse'), 'waveSize': 8}),
        'fadeAmount over 100': with_anim(CTA, {**fk.loop_animation('breathe'), 'fadeAmount': 120}),
        'an easing it lacks': with_anim(CTA, {**fk.loop_animation('glow'), 'easing': 'spring'}),
        'pulse with the canvas-only halo': with_anim(CTA, {
            **fk.loop_animation('pulse'), 'shadowColor': {'type': 'hex', 'hex': '#333333'},
            'shadowSize': 8}),
        'wave on Fill x Hug': with_anim(CTA, fk.loop_animation('wave-fill')),
        'wave with a margin': with_anim(CTA, fk.loop_animation('wave-outline'), **fixed,
                                        margin={'top': 8}),
        'shimmer on no fill': with_anim(CLOSE, fk.loop_animation('shimmer')),
        'shimmer on a gradient': with_anim(CTA, fk.loop_animation('shimmer'), fill=[{
            'type': 'gradient', 'gradient': {'type': 'linear', 'angle': 90, 'stops': []}}]),
        'color-shift on two layers': with_anim(CTA, fk.loop_animation('color-shift'), fill=[
            {'type': 'color', 'color': {'type': 'hex', 'hex': '#FFFFFF'}},
            {'type': 'color', 'color': {'type': 'hex', 'hex': '#000000', 'opacity': 40}}]),
    }
    for why, d in fires.items():
        check(f'fires: {why}', len(warnings(d)) == 1, warnings(d))

    # A shimmer on a theme colour: the dark value decides, letter case included.
    def shimmer_on_theme(dark):
        d = with_anim(CTA, fk.loop_animation('shimmer'),
                      fill=[{'type': 'color', 'color': {'type': 'color-style', 'colorId': 'tst'}}])
        entry = {'id': 'tst', 'name': 'Test', 'light': {'hex': '#adbfad'}}
        if dark is not None:
            entry['dark'] = dark
        d['theme']['colors'].append(entry)
        return warnings(d)
    check('silent: shimmer on a theme colour without dark', shimmer_on_theme(None) == [])
    check('silent: shimmer on a theme colour whose dark equals light',
          shimmer_on_theme({'hex': '#adbfad'}) == [])
    check('fires: shimmer on a theme colour whose dark differs in case only',
          len(shimmer_on_theme({'hex': '#ADBFAD'})) == 1)
    check('silent: color-shift on no fill',
          warnings(with_anim(CLOSE, fk.loop_animation('color-shift'))) == [])

    # The state a wave is shown in counts too.
    d = base()
    e = element(d, CTA)
    e.setdefault('propsByState', {})['selected'] = {'animation': fk.loop_animation('wave-fill')}
    check('fires: a wave in propsByState on Fill x Hug', len(warnings(d)) == 1, warnings(d))

    print()
    if fails:
        print(f'{len(fails)} FAILED')
        for f in fails:
            print(' -', f)
        sys.exit(1)
    print('all passed')


if __name__ == '__main__':
    main()
