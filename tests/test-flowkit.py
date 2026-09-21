#!/usr/bin/env python3
"""Tests for skills/flow-generator/references/flowkit.py.

A shape helper that has drifted from the format is worse than no helper, because it is
confidently wrong at scale. So this asserts the invariants flowkit exists to guarantee, and
then puts its output through the same schema gate a real config goes through.

    python3 tests/test-flowkit.py

Exit codes follow the repo convention: 0 clean, 1 failures, 2 infrastructure problem.
"""
import json
import os
import subprocess
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# a skills dir installs by plain copy, so a __pycache__ under references/ would SHIP with it
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, 'skills', 'flow-generator', 'references'))

import flowkit as fk  # noqa: E402

FAILURES = []


def check(name, cond, detail=''):
    if cond:
        print(f'  ok    {name}')
    else:
        print(f'  FAIL  {name}' + (f'   {detail}' if detail else ''))
        FAILURES.append(name)


def raises(fn, exc=ValueError):
    try:
        fn()
        return False
    except exc:
        return True


def _message(fn, exc=ValueError):
    """The text of the refusal, for the rows where the DIAGNOSTIC is the thing being tested.

    A bare `raises(...)` on a helper that forwards `**kw` tests the downstream signature rather
    than the guard — the trap this suite has already been caught by — and for a guard whose
    whole value is telling an author WHY, the message is the behaviour.
    """
    try:
        fn()
    except exc as caught:
        return str(caught)
    return ''


def sample():
    """A document exercising the pieces most likely to drift."""
    ids = fk.Ids('el_T')
    fk._ids = ids
    tick = fk.stack([fk.icon('Check', size_pt=15, color_id='on')],
                    fixed_w=26, fixed_h=26, corner=fk.radius(9999),
                    direction='horizontal', align_h='center', align_v='center',
                    visibility=fk.hidden(), caption='Tick',
                    props_by_state={'selected': {'visibility': fk.visible(),
                                                 'fill': fk.fill('accent')}})
    card = fk.product(
        [fk.stack([tick], height='fixed', fixed_h=26, direction='horizontal',
                  align_h='end', caption='Tick row'),
         fk.text(fk.rich('Individual'), preset='h1', color_id='ink'),
         fk.text(fk.rich('12 mo, ', fk.Span('$79.99', bold=True), ' or ',
                         fk.Var('0000.prod_price')),
                 preset='body', color_id='muted')],
        product_id='11111111-2222-3333-4444-555555555555', group_id='plans', default=True,
        padding=fk.pad(14, 16, 16, 14), corner=fk.radius(16), fill_=fk.fill('card'),
        border='accent', border_width=3, caption='Plan')
    cta = fk.stack([fk.text(fk.rich('Continue'), preset='body', color_id='on', align='center')],
                   direction='horizontal', align_h='center', align_v='center',
                   fixed_h=46, corner=fk.radius(9999), fill_=fk.fill('accent'),
                   position=fk.docked(bottom=18, left=16, right=16), caption='CTA',
                   actions=[fk.purchase('plans')])
    rail = fk.stack([], fixed_w=38, fixed_h=78, corner=fk.radius(16),
                    fill_=fk.gradient(180, ('#E1D6EB', 0), ('#EDE9F0', 1)), caption='Rail')
    countdown = fk.timer([fk.timer_digits(units=('minutes', 'seconds'), preset='body',
                                          color_id='ink')],
                         custom_id='offer', minutes=15, padding=fk.pad(12, 16, 16, 12),
                         corner=fk.radius(20), fill_=fk.fill('card'),
                         visibility=fk.visible(), caption='Countdown')
    reviews = fk.carousel(
        [fk.stack([fk.text(fk.rich(f'"Review {i}"'), preset='body', color_id='ink')],
                  fixed_w=340, fixed_h=120, corner=fk.radius(16), fill_=fk.fill('card'),
                  padding=fk.pad(16, 16, 16, 16), caption=f'Slide {i}')
         for i in (1, 2, 3)],
        slide_w=340, slide_h=120, caption='Reviews')
    return fk.config(
        screens=[fk.screen('scr_main', [card, rail, cta, countdown, reviews], caption='Plans',
                           fill_=fk.fill('bg'), padding=fk.pad(0, 0, 0, 120),
                           selectable_groups=[{'id': 'plans', 'type': 'product'}])],
        colors=[('bg', 'Background', '#FFFFFF', '#101014'),
                ('card', 'Card', '#F3F6FB', '#1A1A20'),
                ('ink', 'Ink', '#111114', '#F5F5F7'),
                ('muted', 'Muted', '#5F6368', '#9AA0A8'),
                ('accent', 'Accent', '#4A6EBD', '#5C80CF'),
                ('on', 'On accent', '#FFFFFF', '#FFFFFF')],
        typography=[('h1', 'H1', 25, 'bold'), ('body', 'Body', 16, 'regular')],
        icons=[{'name': 'Check', 'weight': 'bold', 'raw': '<svg/>'}])


def main():
    cfg = sample()
    scr = cfg['screens'][0]
    node_map = scr['elements']['map']

    print('flowkit')
    # the invariant the module exists for: hierarchy and map must agree exactly
    seen = []

    def walk(node):
        if node['id'] != 'root':
            seen.append(node['id'])
        for kid in node.get('children', []):
            walk(kid)

    walk(scr['elements']['hierarchy'])
    check('hierarchy and map hold the same ids',
          sorted(seen) == sorted(node_map), f'{len(seen)} in tree vs {len(node_map)} in map')
    check('no id appears twice in the tree', len(seen) == len(set(seen)))
    check('no leftover _children in the map',
          not any('_children' in n for n in node_map.values()))

    # duplicate ids must raise, not silently drop an element
    try:
        dup = fk.stack([], node_id='el_dup')
        dup2 = fk.stack([], node_id='el_dup')
        fk.flatten([dup, dup2])
        check('flatten rejects a duplicate id', False, 'no error raised')
    except ValueError:
        check('flatten rejects a duplicate id', True)

    # The stamped version and the shapes that entitle the module to stamp it. These belong
    # together: the number is a claim about the document, so a test that pins it without
    # pinning the shapes would go green on a flow the builder then refuses to migrate.
    check('schemaVersion is 12', cfg['schemaVersion'] == 12)
    fills = [n['props']['fill'] for n in node_map.values() if 'fill' in n['props']]
    fills.append(scr['props']['fill'])
    check('every fill is an array (010)', all(isinstance(f, list) for f in fills),
          f'{sum(1 for f in fills if not isinstance(f, list))} non-array')
    check('every screen carries a products registry (012)',
          all(isinstance(s.get('products'), list) for s in cfg['screens']))

    # the divergence this module was built to kill
    spans = None
    for n in node_map.values():
        c = n['props'].get('content')
        if isinstance(c, dict) and len(c.get('values', {}).get('en', [])) == 1:
            content = c['values']['en'][0]['content']
            if any(s.get('type') == 'variable' for s in content):
                spans = content
    check('rich() produced a span list containing a variable', spans is not None)
    if spans:
        kinds = [s['type'] for s in spans]
        check('Var -> variable node, Span -> text node',
              kinds == ['text', 'text', 'text', 'variable'], str(kinds))
        check('a Span carries its own colour only when asked',
              'color' not in spans[0]['attrs'])
        check('a bold Span sets bold', spans[1]['attrs']['bold'] is True)
    try:
        fk.rich('x', ('var', 'y'))
        check('rich() rejects an ambiguous bare tuple', False, 'tuple was accepted')
    except TypeError:
        check('rich() rejects an ambiguous bare tuple', True)

    # things the traps say must hold
    prod = [n for n in node_map.values() if n['type'] == 'product'][0]
    check('product carries groupId, default and product.id',
          prod['props']['groupId'] == 'plans' and prod['props']['default'] is True
          and 'id' in prod['props']['product'])
    check('product gets the system selected state',
          prod['states'] == [{'id': 'selected', 'type': 'system'}])
    cta = [n for n in node_map.values() if n.get('caption') == 'CTA'][0]
    check('purchase buys the group selection, not a const',
          cta['interactions'][0]['actions'][0]['payload']['product']['variableId']
          == 'plans.selectedProduct')
    check('a docked element sets left and right and bottom',
          set(cta['props']['position']) >= {'type', 'bottom', 'left', 'right'})
    rail = [n for n in node_map.values() if n.get('caption') == 'Rail'][0]
    check('a gradient does not end on a bare colour object',
          isinstance(rail['props']['fill'], list)
          and rail['props']['fill'][0]['type'] == 'gradient')
    # pinned against tests/fixtures/*.json, where two real exports use this exact shape
    check('navigate payload is {type: screen, screen: id}',
          fk.navigate('scr_x')['payload'] == {'type': 'screen', 'screen': 'scr_x'},
          json.dumps(fk.navigate('scr_x')['payload']))

    check('_meta.screens is left empty (builder-owned)', cfg['_meta']['screens'] == {})

    # flow_product_id(): the builder's own derivation, reproduced. These nine vectors are real
    # builder-minted values from three independent sources -- if any one of them breaks, the
    # derivation has drifted and every predeclared draft is minting ids the builder disagrees
    # with. Sources, in order: the builder's unit test `buildFlowMeta.test.ts` (both branches),
    # the demo flow `demo/src/data/calm.data.ts`, and the transformer fixture
    # `src/fixtures/v5/progress-bar-connectors/input.json`.
    for screen, product, offer, expected in [
        ('screen-1', 'annual', None, '2093eb92-15e4-50c4-b918-910385b6646d'),
        ('screen-1', 'annual', 'trial', '00b2d28e-21a5-5ccc-837b-ebb1c685793f'),
        ('screen-1', 'component', 'offer', '333d04d7-c788-53eb-a0b3-d240ef8764da'),
        ('scr_lsT14qTJ', 'b136422f-8153-402a-afbb-986929c68f6a', None,
         'e6633f38-f060-55c7-92fc-bf8a2ef76b61'),
        ('scr_lsT14qTJ', 'ac281b85-9294-4109-b9f1-4ab66b52d263', None,
         '8dfdde18-e09e-555d-a9d5-b55fd42eb068'),
        ('scr_lsT14qTJ', '4f930955-b0e4-47c3-8bb9-abd1bbdccabd', None,
         '085c69fb-f8da-5b9e-a503-f42ec7e0e5df'),
        ('ae4fbd22-7b44-4aea-aa24-a3d227c085fd', '73d6328a-7b76-46af-949b-d3d34c329e7c', None,
         '9974b07a-6b26-55a0-882d-58c821ce4e88'),
        ('ae4fbd22-7b44-4aea-aa24-a3d227c085fd', '33bc0f34-76c5-4598-9a85-3dd66bac9079', None,
         '6ce1b2c9-9059-57d1-8ee2-331ff6d20d33'),
        ('ae4fbd22-7b44-4aea-aa24-a3d227c085fd', '7ce976b7-ca13-42b8-a4a0-365d6ed4297b', None,
         '5f3456cc-f8fd-56a6-aadd-ea0ba7a63a34'),
    ]:
        got = fk.flow_product_id(screen, product, offer)
        pair = f'{screen}:{product}' + (f':{offer}' if offer else '')
        check(f'flow_product_id matches the builder for {pair}', got == expected, got)

    # the empty-namespace detail the earlier search missed: uuid5 over a ZERO namespace is a
    # different hash input (16 zero bytes vs no prefix), and would silently produce wrong ids
    check('flow_product_id is not uuid5 over a zero namespace',
          fk.flow_product_id('screen-1', 'annual')
          != str(uuid.uuid5(uuid.UUID(int=0), 'screen-1:annual')))

    # predeclare(): the declaration that lets a NEW draft preview on a device
    pids = ['db3cfae2-5266-4678-85b3-b2ea535301ce', 'a80615bd-86b5-4851-b895-a343fa7db228']
    dec = fk.predeclare('scr_pro', pids)
    entries = dec['scr_pro']['products']
    check('predeclare emits one entry per product', [e['id'] for e in entries] == pids)
    check('predeclare emits only id and flowProductId when there is no offer',
          all(set(e) == {'id', 'flowProductId'} for e in entries))
    check('predeclare is deterministic', fk.predeclare('scr_pro', pids) == dec)
    check('predeclare is screen-scoped',
          fk.predeclare('scr_other', pids)['scr_other']['products'][0]['flowProductId']
          != entries[0]['flowProductId'])
    check('predeclare agrees with flow_product_id',
          [e['flowProductId'] for e in entries]
          == [fk.flow_product_id('scr_pro', p) for p in pids])

    # exact pairs: a product bound WITH an offer is a different entry and a different id
    paired = fk.predeclare('scr_pro', [pids[0], (pids[0], 'trial')])['scr_pro']['products']
    check('predeclare accepts a (product, offer) pair', len(paired) == 2)
    check('predeclare carries offerId, in the builder key order',
          list(paired[1]) == ['id', 'offerId', 'flowProductId'], json.dumps(paired[1]))
    check('an offer-bound pair gets its own id',
          paired[0]['flowProductId'] != paired[1]['flowProductId'])
    check('the offer-bound id is the builder\'s',
          paired[1]['flowProductId'] == fk.flow_product_id('scr_pro', pids[0], 'trial'))
    check('a list is accepted where a tuple is',
          fk.predeclare('scr_pro', [[pids[0], 'trial']])['scr_pro']['products'] == [paired[1]])
    check('config(meta_screens=...) carries it through',
          fk.config(screens=[], meta_screens=dec)['_meta']['screens'] == dec)
    check('opacity, when given, is a percentage not a fraction',
          fk.hex_color('#101828', opacity=6)['opacity'] == 6)

    # distribution has four modes, and only the gap form used to be reachable
    check('default distribution is the gap form',
          fk.layout(gap=12)['distribution'] == {'gap': 12, 'type': 'gap'})
    check('a spread mode carries no gap key',
          fk.layout(distribution='space-between')['distribution']
          == {'type': 'space-between'})
    check('all three spread modes are accepted',
          all(fk.layout(distribution=m)['distribution']['type'] == m
              for m in fk.SPREAD_MODES))
    try:
        fk.layout(distribution='space-araound')
        check('an unknown distribution raises rather than emitting junk',
              False, 'typo was accepted')
    except ValueError:
        check('an unknown distribution raises rather than emitting junk', True)
    # image() — an uploaded asset was unreachable from this module before 0.8.0's media upload
    HERO = 'https://public-media.adapty.io/public/1e/5b/1e5bbbb4/hero.png'
    img = fk.image(HERO, media_id=516395, preview=fk.NO_PREVIEW, fixed_w=242,
                   corner=fk.radius(20))
    check('image binds the url inside the per-locale localizable map',
          img['props']['image'] == {'_localizable': True,
                                    'values': {'en': {'id': '516395', 'url': HERO}}},
          json.dumps(img['props']['image']))
    check('a numeric media id is written as a string',
          isinstance(img['props']['image']['values']['en']['id'], str))
    check('image defaults to a hug height, whose drawn size is the asset aspect',
          img['props']['height'] == {'type': 'hug'} and img['props']['objectFit'] == 'cover')
    ph = fk.image(fk.PLACEHOLDER, fixed_w=242, fixed_h=180)
    check('PLACEHOLDER emits an empty values map, wrapper intact',
          ph['props']['image'] == {'values': {}, '_localizable': True})
    check('a fixed image box is honoured over the hug default',
          ph['props']['height'] == {'type': 'fixed', 'value': 180})
    try:
        fk.image('')
        check('an image with no url raises rather than emitting an empty map', False,
              'empty url was accepted')
    except TypeError:
        check('an image with no url raises rather than emitting an empty map', True)
    try:
        fk.image(HERO, fit='contain')
        check('an objectFit outside the two-value enum raises', False, 'contain was accepted')
    except ValueError:
        check('an objectFit outside the two-value enum raises', True)

    # previewValue — the base64 thumbnail the renderer paints while the asset downloads. With
    # the key absent the renderer draws a transparent 1x1 and the screen has a hole until the
    # download finishes, and no gate sees it. Only the upload returns it, so `preview=` is
    # REQUIRED here: a default would let "the upload gave me none" and "I never captured one"
    # write the same document, and only the first is finished work.
    PREV = 'UklGRhQJAABXRUJQVlA4IAgJAAAwSQCdASos'
    withp = fk.image(HERO, media_id=516395, preview=PREV)
    check('preview binds as previewValue, bare, beside id and url',
          withp['props']['image']['values']['en'] ==
          {'url': HERO, 'id': '516395', 'previewValue': PREV},
          json.dumps(withp['props']['image']['values']['en']))
    check('no preview OMITS the key rather than writing null — what the builder does when the '
          'upload generated none',
          'previewValue' not in
          fk.image(HERO, media_id=1, preview=fk.NO_PREVIEW)['props']['image']['values']['en'])
    for bad, why in ((lambda: fk.image(HERO, preview='data:image/webp;base64,AAA'),
                      'a data URI is refused: the field wants bare base64'),
                     (lambda: fk.image(HERO, preview='   '),
                      'a blank preview is refused rather than written as an empty string')):
        try:
            bad()
            check(why, False, 'accepted')
        except (TypeError, ValueError) as exc:
            # Assert on the MESSAGE: the whole value of these guards is telling an author where
            # the string comes from, and a bare `raises` here would pass on any exception.
            check(why, 'preview_base64' in str(exc) or 'BARE base64' in str(exc), str(exc)[:60])

    for bad, why, want in (
            (lambda: fk.image(HERO, media_id=516395),
             'image() with no preview= at all raises rather than quietly omitting the field',
             'required'),
            (lambda: fk.image_fill(HERO, media_id=516395),
             'image_fill() with no preview= raises too — a background is the most visible hole',
             'required'),
            (lambda: fk.image(fk.PLACEHOLDER, preview=PREV),
             'a preview on a PLACEHOLDER raises: there is no asset for it to be a preview of',
             'contradiction')):
        try:
            bad()
            check(why, False, 'accepted')
        except TypeError as exc:
            # The message is the guard. `preview` is keyword-only, so a bare `raises` here would
            # also pass on Python's own missing-argument error, which teaches an author nothing.
            check(why, want in str(exc), str(exc)[:70])
    check('NO_PREVIEW is a distinct object, not a falsy value another argument could collide with',
          fk.NO_PREVIEW is not None and fk.NO_PREVIEW is not fk.PLACEHOLDER and
          bool(fk.NO_PREVIEW))

    # image_fill() — the SAME asset binds a second way, flat, with no locale map. There was no
    # helper for it, so a background image was hand-assembled and its preview was the easiest
    # thing to leave out.
    bg = fk.image_fill(HERO, media_id=516395, preview=PREV, hexval='#0B0B10')
    check('image_fill emits one flat layer, preview included',
          bg == [{'type': 'image',
                  'image': {'url': HERO, 'id': '516395', 'previewValue': PREV},
                  'color': {'type': 'hex', 'hex': '#0B0B10'}}], json.dumps(bg))
    check('image_fill wraps in a one-item array, like every other v10 fill',
          isinstance(bg, list) and len(bg) == 1)
    check('image_fill refuses two colour sources',
          raises(lambda: fk.image_fill(HERO, preview=fk.NO_PREVIEW, color_id='bg',
                                       hexval='#FFF'), TypeError))

    # video() — `flows media upload` REFUSES a clip (permitted formats are JPEG/JPEG2000/WEBP/
    # PNG/SVG), so the only correct artifact is a styled element with NO source plus a spoken
    # "open the builder and upload it". Before this helper there was no way to emit one from
    # this module, so a video was hand-assembled or, worse, faked with a stack and a Play icon.
    vid = fk.video(fixed_h=220, corner=fk.radius(16), margin=fk.pad(0, 0, 0, 16))
    check('video emits the element type, not a stack lookalike', vid['type'] == 'video')
    check('video carries NO source key at all',
          not {'video', 'customMediaID'} & set(vid['props']))
    check('video keeps the fixed height it was given',
          vid['props']['height'] == {'type': 'fixed', 'value': 220})
    check('video loops and covers by default',
          vid['props']['loop'] is True and vid['props']['objectFit'] == 'cover')
    check('video carries the design props through',
          vid['props']['borderRadius'] == {'tl': 16, 'tr': 16, 'bl': 16, 'br': 16}
          and vid['props']['margin']['bottom'] == 16)
    # Measured: with height:hug an unset clip draws an arbitrary 256pt box (the renderer's
    # default, the same one an empty image draws), so the previewed layout is not the shipped
    # one. Unrepresentable beats detectable — `fixed_h` has no default.
    def no_height_says_why():
        try:
            fk.video()
            return False
        except TypeError as e:
            return 'fixed_h' in str(e)

    check('a video with no height raises rather than defaulting to hug', no_height_says_why())
    check('...and the raise names fixed_h, whichever guard catches it',
          no_height_says_why())
    check('fixed_h rejects a non-number', raises(lambda: fk.video(fixed_h='220'), TypeError))
    check('fixed_h rejects a bool, which is an int in Python',
          raises(lambda: fk.video(fixed_h=True), TypeError))
    # These assert on the MESSAGE, not merely that something raised. `**kw` reaches `_node`,
    # which rejects an unknown keyword on its own — so a bare `raises(...)` here passes with the
    # guard deleted, and pins _node's signature rather than this rule. The diagnostic IS the
    # deliverable: it has to tell an agent why no URL can exist and what to do instead.
    def refuses_source(arg):
        try:
            fk.video(fixed_h=200, **{arg: 'https://cdn/x.mp4'})
            return False
        except TypeError as e:
            return 'takes no source' in str(e) and 'upload the clip' in str(e)

    for arg in ('url', 'video', 'media_id', 'customMediaID', 'videoUrl'):
        check(f'video refuses a fabricated source by name, and says why ({arg})',
              refuses_source(arg))
    check('video enforces the same two-value objectFit enum',
          raises(lambda: fk.video(fixed_h=200, fit='contain'), ValueError))
    # `IVideoElementProps` has no `fill`, no `align` and no `layout` — placement is the parent's
    # job — so a caller reaching for one should hit _node's own signature rather than have it
    # silently land in props.
    check('video takes no fill (the schema has none)',
          raises(lambda: fk.video(fixed_h=200, fill_=fk.fill('bg')), TypeError))

    spread_stack = fk.stack([], distribution='space-evenly')
    check('stack passes distribution through',
          spread_stack['props']['layout']['distribution']
          == {'type': 'space-evenly'})
    check('screen passes distribution through',
          fk.screen('scr_d', [], distribution='space-between',
                    scrollable=False)['props']['layout']['distribution']
          == {'type': 'space-between'})

    # The stretch-between-anchors pair. Both halves are measured render failures, so flowkit
    # refuses each half alone rather than emitting it and warning about it later.
    rail = fk.stack([], width='fixed', fixed_w=8, height='auto',
                    position=fk.absolute(top=10, left=12, bottom=-18, z=-10))
    check('absolute() keeps every offset it was given',
          rail['props']['position'] == {'type': 'absolute', 'top': 10, 'left': 12,
                                        'bottom': -18, 'zIndex': -10})
    check('a top+bottom anchored stack takes height auto',
          rail['props']['height'] == {'type': 'auto'})
    check('absolute() omits the offsets it was not given',
          fk.absolute(top=0, left=0) == {'type': 'absolute', 'top': 0, 'left': 0})
    check('anchored top+bottom with a fill height raises',
          raises(lambda: fk.stack([], height='fill',
                                  position=fk.absolute(top=10, bottom=-18))))
    check('height auto without a bottom anchor raises',
          raises(lambda: fk.stack([], height='auto', position=fk.absolute(top=10))))
    check('height auto on a relative element raises',
          raises(lambda: fk.stack([], height='auto')))
    check('size rejects a kind that is not a kind',
          raises(lambda: fk.size('atuo')))

    # A rail fades on ALPHA, so a stop needs an optional third item; without it the composition
    # in patterns.md was unreachable from this module.
    fade = fk.gradient(180, ('#0E9F6E', 0, 100), ('#0E9F6E', 1, 22))
    check('a gradient stop carries a per-stop opacity when given one',
          [s['color'].get('opacity') for s in fade[0]['stops']] == [100, 22])
    check('a two-item gradient stop still omits opacity entirely',
          'opacity' not in fk.gradient(180, ('#FFF', 0), ('#000', 1))[0]['stops'][0]['color'])

    # Typography leading, verified present on 6 of 7 presets in a real export.
    typo = fk.config(screens=[fk.screen('scr_t', [])],
                     typography=[('a', 'A', 30, 'bold', 34, -0.5),
                                 ('b', 'B', 15, 'regular', 21),
                                 ('c', 'C', 13, 'regular')])['theme']['typography']
    check('typography carries lineHeight and letterSpacing when given',
          typo[0]['settings'] == {'size': 30, 'weight': 'bold', 'lineHeight': 34,
                                  'letterSpacing': -0.5})
    check('lineHeight alone is allowed', typo[1]['settings'].get('lineHeight') == 21
          and 'letterSpacing' not in typo[1]['settings'])
    check('the plain four-item preset is unchanged',
          typo[2]['settings'] == {'size': 13, 'weight': 'regular'})

    # --- timer -------------------------------------------------------------------------
    # The bug this guards: a countdown's digit tokens carry a `timer_` PREFIX. The bare names
    # save and pass `flows config validate`, and the Flow Builder then paints them red
    # "Unknown" while the device/preview renders the literal "%minutes%".
    # `component-catalog.json` shipped the bare names until 2026-08-25, so the prefix is
    # exactly the kind of shape a helper has to own rather than leave to an author.
    digits = fk.timer_digits(units=('hours', 'minutes', 'seconds'))
    nodes = digits['props']['content']['values']['en'][0]['content']
    check('every timer digit token carries the timer_ prefix',
          [n['attrs']['token'] for n in nodes if n.get('type') == 'token']
          == ['timer_hours', 'timer_minutes', 'timer_seconds'], str(nodes))
    check('units are emitted in the order given, not in TIMER_UNITS order',
          [n['attrs']['token'] for n in
           fk.timer_digits(units=('seconds', 'minutes'))['props']['content']['values']['en'][0]
           ['content'] if n.get('type') == 'token'] == ['timer_seconds', 'timer_minutes'])
    check('the separator is a rich-text node, not a bare string',
          [n.get('text') for n in nodes if n.get('type') == 'text'] == [':', ':']
          and all('attrs' in n for n in nodes if n.get('type') == 'text'))
    check('an unknown timer unit raises rather than emitting a bare token',
          raises(lambda: fk.timer_digits(units=('hours', 'mins'))))

    # SUPERSEDED 2026-09-01: this block used to build the delay timer CHILDLESS and assert
    # that "a delay timer with no digit child draws nothing, which is the invisible-delay
    # shape". Device-measured over three trips, that shape does not fire at all — see the
    # guard below and CLAUDE.md finding 29. The timer-end assertion survives; the
    # invisible-delay one was encoding the wrong claim and is replaced by its opposite.
    delay = fk.timer([fk.timer_digits(units=('seconds',))],
                     actions=[{'id': 'act_next', 'type': 'navigate',
                               'payload': {'type': 'screen', 'screen': 'scr_next'}}],
                     seconds=3)
    check("a timer's own interaction fires on timer-end, not tap",
          [i['trigger'] for i in delay.get('interactions', [])] == ['timer-end'], str(delay))
    check('a firing delay timer carries a child, because a childless one does not advance',
          len(delay.get('_children') or []) == 1)
    check('duration carries all four units',
          fk.timer(days=1, hours=2, minutes=3, seconds=4)['props']['duration']
          == {'days': 1, 'hours': 2, 'minutes': 3, 'seconds': 4})
    check('a timer carries states, like every other element', fk.timer()['states'] == [])

    # and finally: does the real schema gate accept it?
    checker = os.path.join(HERE, 'schema-check.py')
    if not os.path.exists(checker):
        print('  SKIP  schema gate (tests/schema-check.py missing)')
    else:
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
            json.dump(cfg, fh)
            path = fh.name
        try:
            res = subprocess.run([sys.executable, checker, path],
                                 capture_output=True, text=True, timeout=180)
            out = (res.stdout + res.stderr).strip().splitlines()
            line = out[0] if out else '(no output)'
            if res.returncode == 2:
                print(f'  SKIP  schema gate unavailable: {line}')
            else:
                check('flowkit output passes the schema gate', ' OK ' in f' {line} ', line)
        except (subprocess.TimeoutExpired, OSError) as exc:
            print(f'  SKIP  schema gate could not run: {exc}')
        finally:
            os.unlink(path)

    # The token vocabulary is the schema's, not ours: `ETimerToken` is the ground truth, so if
    # the builder ever adds a unit, TIMER_UNITS has to move with it. The gate above warms this
    # cache. Note the schema does NOT constrain a token node's own `attrs.token` (it is typed a
    # bare string and never $refs ETimerToken), which is why the bad name has to be caught here
    # and in verify-config.py rather than by the schema check.
    schema_cache = os.path.join(tempfile.gettempdir(), 'adapty-flow.schema.json')
    enum = None
    if os.path.exists(schema_cache):
        try:
            enum = json.load(open(schema_cache)).get('$defs', {}).get('ETimerToken', {}).get('enum')
        except (ValueError, OSError):
            enum = None
    if not enum:
        print('  SKIP  TIMER_UNITS vs schema enum (no cached schema, or no ETimerToken in it)')
    else:
        check('TIMER_UNITS matches the schema ETimerToken enum',
              sorted(enum) == sorted(f'timer_{u}' for u in fk.TIMER_UNITS), str(enum))

    # footer() — the pinned bottom bar. Before this existed, an author reaching for a bar that
    # stays put found only docked(), and the documented steer was AWAY from the native element;
    # the result was a "fake footer" (an empty fixed stack with a fill behind docked children)
    # that passed every local gate. Each guard below stands for one measured render.
    f = fk.footer([fk.text(fk.localized('CONTINUE'))], fill_=fk.fill('surface'))
    check('footer() emits type footer', f['type'] == 'footer', f['type'])
    check('footer() is relative, not positioned — the pinning is the element\'s own',
          f['props']['position']['type'] == 'relative', str(f['props']['position']))
    check('footer() carries the opaque fill it was given', 'fill' in f['props'])
    check('a footer with no fill raises (content would scroll through it)',
          raises(lambda: fk.footer([fk.text(fk.localized('X'))])))
    check('a positioned footer raises (that is the fake-footer shape)',
          raises(lambda: fk.footer([], fill_=fk.fill('surface'),
                                   position=fk.docked(bottom=24))))
    check('two footers on one screen raise (a second one draws zero pixels)',
          raises(lambda: fk.screen('scr_x', [fk.footer([], fill_=fk.fill('surface')),
                                             fk.footer([], fill_=fk.fill('surface'))])))
    check('a footer on a non-scrollable screen raises (device-confirmed: it does not render)',
          raises(lambda: fk.screen('scr_ns', [fk.footer([], fill_=fk.fill('surface'))],
                                   scrollable=False)))
    check('one footer per screen is fine',
          fk.screen('scr_y', [fk.stack([]), fk.footer([], fill_=fk.fill('surface'))])
            is not None)

    # carousel() — the swipeable element. Same story as footer(): the module exposed no way to
    # build one, so an author reaching for a reviews slider found only stack(), and the result
    # was a static card plus decorative dot stacks — one frozen slide, dead dots, and a
    # screenshot that looks finished. The preview never swipes, so no local render sees it.
    car = [n for n in node_map.values() if n['type'] == 'carousel'][0]
    check('carousel() emits type carousel', car['type'] == 'carousel')
    check('carousel props match the real-export key set (no layout prop exists on a carousel)',
          set(car['props']) == {'gap', 'width', 'height', 'slideWidth', 'slideHeight', 'dots'},
          str(sorted(car['props'])))
    check('slide geometry is fixed — a hug slide is dropped on device',
          car['props']['slideWidth']['type'] == 'fixed'
          and car['props']['slideHeight']['type'] == 'fixed')
    check('height defaults to the slide height',
          car['props']['height'] == car['props']['slideHeight'])
    check('the dots are the element\'s own, with all four keys IDots requires',
          set(car['props']['dots']) == {'color', 'activeColor', 'size', 'gap'},
          str(sorted(car['props']['dots'])))
    check('one node per slide, and no dot children among them',
          len([n for n in node_map.values() if str(n.get('caption', '')).startswith('Slide')]) == 3)
    check('a single-slide carousel raises (that is the frozen slide)',
          raises(lambda: fk.carousel([fk.stack([])], slide_w=340, slide_h=120)))
    check('dot-like stacks passed as slides raise (the dots come from props.dots)',
          raises(lambda: fk.carousel(
              [fk.stack([], fixed_w=6, fixed_h=6, corner=fk.radius(9999)) for _ in range(3)],
              slide_w=340, slide_h=120)))
    check('dots=False omits the key rather than emitting a partial IDots',
          'dots' not in fk.carousel([fk.stack([]), fk.stack([])], slide_w=340, slide_h=120,
                                    dots=False)['props'])
    check('a dot colour given as a theme id becomes a color-style, so the dots follow the theme',
          fk.carousel([fk.stack([]), fk.stack([])], slide_w=340, slide_h=120,
                      dot_color='muted')['props']['dots']['color']
          == {'type': 'color-style', 'colorId': 'muted'})
    check('a dot colour given as a hex stays a hex',
          fk.carousel([fk.stack([]), fk.stack([])], slide_w=340, slide_h=120,
                      dot_color='#101828')['props']['dots']['color']['type'] == 'hex')

    # --- conditions, actions and tabs: the three transformer refusals flowkit could not
    # express before 2026-08-28. Each raise below is a hard 422 made unrepresentable.
    check('when() builds the third visibility form',
          fk.when(fk.not_empty(fk.ref('email.value')))
          == {'type': 'conditional',
              'condition': {'type': 'notEmpty',
                            'left': {'type': 'var', 'variableId': 'email.value'}}})
    check('a comparison auto-wraps a bare value as a const, which is what the walker wants',
          fk.eq(fk.ref('g.selectedOptionId'), 'gold')['right']
          == {'type': 'const', 'value': 'gold'})
    check('`assign` is refused as a condition (schema-legal, no case in the walker)',
          raises(lambda: fk.when({'type': 'assign', 'left': fk.ref('a'),
                                  'right': fk.lit(1)})))
    check('...but `assign` is exactly what set_variable emits, where it IS legal',
          fk.set_variable([('a', 1)])['payload'][0]['type'] == 'assign')
    check('an unknown expression type is refused',
          raises(lambda: fk.when({'type': 'bogus'})))
    check('an empty variableId is refused',
          raises(lambda: fk.when({'type': 'var', 'variableId': ''})))
    check('a comparison missing an operand is refused',
          raises(lambda: fk.when({'type': '==', 'left': fk.ref('a')})))
    check('a bare string where an expression belongs is refused',
          raises(lambda: fk.when('email.value'), (ValueError, TypeError)))
    check('predicates ABSENT is accepted, because the service accepts it',
          fk.when({'type': '&&'})['condition'] == {'type': '&&'})
    check('ref() refuses an empty id', raises(lambda: fk.ref('')))

    check('open_url refuses an empty url', raises(lambda: fk.open_url('')))
    check('open_url emits payload.url', fk.open_url('https://a.io/t')['payload']['url']
          == 'https://a.io/t')
    check('restore() is restorePurchases and takes no payload',
          fk.restore() == {'id': 'act_restore', 'type': 'restorePurchases'})
    check('select_product refuses an empty element id',
          raises(lambda: fk.select_product('')))
    check('custom_action refuses an empty payload id', raises(lambda: fk.custom_action('')))
    check('alert with neither title nor message is refused', raises(lambda: fk.alert()))
    check('alert with only a message is fine', fk.alert(message='Hi')['payload'] == {'message': 'Hi'})
    check('set_variable refuses an empty assignment list', raises(lambda: fk.set_variable([])))
    check('set_variable refuses an assignment with no target',
          raises(lambda: fk.set_variable([('', 1)])))
    check('conditional_action refuses an empty case list',
          raises(lambda: fk.conditional_action([])))
    check('conditional_action refuses a case that is not a (predicate, actions) pair',
          raises(lambda: fk.conditional_action([(fk.ref('a'),)]), (ValueError, TypeError)))
    check('conditional_action emits [predicate, value] tuples',
          len(fk.conditional_action([(fk.eq(fk.ref('a'), 1), [fk.close()])])
              ['payload']['cases'][0]) == 2)
    check('an empty conditional branch becomes the real export\'s no-op, not an omission',
          fk.conditional_action([(fk.eq(fk.ref('a'), 1), [])])['payload']['default']['value']
          == [{'id': '', 'type': 'nothing'}])

    SEL = {'fill': fk.fill('pillOn')}

    def _tabs(**kw):
        kw.setdefault('item_selected', SEL)
        return fk.tabs([fk.tab([fk.text('M')], [fk.text('mp')]),
                        fk.tab([fk.text('A')], [fk.text('ap')])], **kw)

    check('tabs() stamps ONE group id on every tab-item, so they cannot disagree',
          {e['props']['groupId'] for e in fk.flatten([_tabs(group_id='g')])[0].values()
           if e.get('type') == 'tab-item'} == {'g'})
    check('tabs() emits the five element types a real export uses, not a flat bar',
          {e['type'] for e in fk.flatten([_tabs(group_id='g')])[0].values()}
          >= {'tabs', 'tab-bar', 'tab-item', 'tab-content-wrapper', 'tab-content'})
    check('tabs() pairs each label with its panel, so ordinal linkage cannot drift',
          len([e for e in fk.flatten([_tabs(group_id='g')])[0].values()
               if e.get('type') == 'tab-item'])
          == len([e for e in fk.flatten([_tabs(group_id='g')])[0].values()
                  if e.get('type') == 'tab-content']))
    check('tabs() refuses a single tab',
          raises(lambda: fk.tabs([fk.tab([], [])], group_id='g', item_selected=SEL)))
    check('tabs() refuses an empty group id', raises(lambda: _tabs(group_id='')))
    check('tabs() refuses a plain stack as a tab (a stack is never a group member)',
          raises(lambda: fk.tabs([fk.tab([], []), fk.stack([])], group_id='g', item_selected=SEL),
                 (ValueError, TypeError)))
    check('tabs() refuses two default tabs',
          raises(lambda: fk.tabs([fk.tab([], [], default=True),
                                  fk.tab([], [], default=True)],
                                 group_id='g', item_selected=SEL)))
    # --- the dead-pill defect: states declared, nothing overridden (finding 37) ---
    check('tabs() refuses a missing item_selected, naming the defect',
          raises(lambda: fk.tabs([fk.tab([], []), fk.tab([], [])], group_id='g'),
                 (ValueError, TypeError)))
    def _msg(fn):
        try: fn()
        except Exception as e: return str(e)
        return ''
    check('tabs() refuses an empty item_selected, and the message names the dead pill',
          'NOTHING ON SCREEN CHANGES' in _msg(lambda: _tabs(group_id='g', item_selected={})))
    check('every tab-item carries propsByState.selected — without it the pill never moves',
          all(e.get('propsByState', {}).get('selected')
              for e in fk.flatten([_tabs(group_id='g')])[0].values()
              if e.get('type') == 'tab-item'))
    check('the selected override is the props the caller passed, not a guess',
          all(e.get('propsByState', {}).get('selected') == SEL
              for e in fk.flatten([_tabs(group_id='g')])[0].values()
              if e.get('type') == 'tab-item'))
    check('every tab-item still declares the system selected state',
          all(e.get('states') == [{'id': 'selected', 'type': 'system'}]
              for e in fk.flatten([_tabs(group_id='g')])[0].values()
              if e.get('type') == 'tab-item'))
    check('tabs() sets layout.clipContent, which both sources set and panels need',
          all(e['props']['layout'].get('clipContent') is True
              for e in fk.flatten([_tabs(group_id='g')])[0].values()
              if e.get('type') == 'tabs'))
    check('heights default to hug — fill inside a hug parent collapses (trap 13)',
          all(e['props']['height'] == {'type': 'hug'}
              for e in fk.flatten([_tabs(group_id='g')])[0].values()
              if e.get('type') in ('tabs', 'tab-content-wrapper', 'tab-content')))
    check('content_height="fill" is still reachable for an all-fill chain',
          all(e['props']['height'] == {'type': 'fill'}
              for e in fk.flatten([_tabs(group_id='g', content_height='fill')])[0].values()
              if e.get('type') in ('tab-content-wrapper', 'tab-content')))
    check('a tab group declared other than single_choice is refused by screen()',
          raises(lambda: fk.screen('s1', [_tabs(group_id='g')],
                                   selectable_groups=[{'id': 'g', 'type': 'multi_choice'}])))
    check('a tab group declared single_choice is accepted',
          fk.screen('s1', [_tabs(group_id='g')],
                    selectable_groups=[{'id': 'g', 'type': 'single_choice'}])['id'] == 's1')
    check('a member whose group is not declared is refused',
          raises(lambda: fk.screen('s1', [fk.selectable([], group_id='nope')])))
    check('a group declared with no members is refused',
          raises(lambda: fk.screen('s1', [fk.text('hi')],
                                   selectable_groups=[{'id': 'g', 'type': 'toggle'}])))
    check('a group type outside the four real ones is refused',
          raises(lambda: fk.screen('s1', [fk.selectable([], group_id='g')],
                                   selectable_groups=[{'id': 'g', 'type': 'tabs'}])))

    def _cfg(vid, with_input=True):
        kids = []
        if with_input:
            inp = fk.stack([])
            inp['type'] = 'email-input'
            inp['props']['customId'] = 'email'
            kids.append(inp)
        kids.append(fk.stack([fk.text('Go')], visibility=fk.when(fk.not_empty(fk.ref(vid)))))
        return fk.config(screens=[fk.screen('scr_a', kids)])

    check('config() accepts a condition variable an input produces', _cfg('email.value')['screens'])
    check('config() refuses a condition variable nothing produces (TS2304 before this)',
          raises(lambda: _cfg('emial.value')))

    # --- the input family. `custom_id` is the producer for `<id>.value`, which is what every
    # conditional gate reads, so the failures here are the same 422 the condition helpers guard.
    check('email_input reproduces the real export prop set, key for key',
          set(fk.email_input('email', placeholder='Email', fill_=fk.fill('card'),
                             border='line',
                             corner=fk.radius(14), margin=fk.pad(22, 0, 0, 0))['props'])
          == {'border', 'borderRadius', 'customId', 'fill', 'font', 'height', 'margin',
              'padding', 'placeholder', 'position', 'validateEmailFormat', 'width'})
    check('every input type is emitted under its own element type',
          [fk.text_input('a')['type'], fk.email_input('b')['type'],
           fk.password_input('c')['type'], fk.number_input('d')['type'],
           fk.phone_input('e')['type'], fk.date_picker('f')['type'],
           fk.time_picker('g')['type'], fk.date_time_picker('h')['type']]
          == list(fk.INPUT_TYPES))
    check('an input refuses an empty custom_id (it is the producer for <id>.value)',
          raises(lambda: fk.text_input('')))
    check('a placeholder is a bare localizable string, not rich text',
          fk.text_input('a', placeholder='Name')['props']['placeholder']
          == {'values': {'en': 'Name'}, '_localizable': True})
    check('passing rich() as a placeholder is refused',
          raises(lambda: fk.text_input('a', placeholder=fk.rich('Name')),
                 (ValueError, TypeError)))
    check('date_picker refuses a format outside the schema enum',
          raises(lambda: fk.date_picker('d', date_format='dd/mm/yyyy')))
    check('date_picker accepts the three the schema allows',
          all(fk.date_picker('d', date_format=f)['props']['dateFormat'] == f
              for f in fk.DATE_FORMATS))
    check('time_picker refuses a format outside the enum',
          raises(lambda: fk.time_picker('t', time_format='24 hour')))
    check('number_input refuses a format outside the enum',
          raises(lambda: fk.number_input('n', number_format='float')))
    check('password_input refuses an unknown requirement key',
          raises(lambda: fk.password_input('p', requirements={'emoji': True})))
    check('password_input passes the schema-allowed requirement keys through',
          fk.password_input('p', requirements={'minLength': 8, 'number': True})
          ['props']['passwordRequirements'] == {'minLength': 8, 'number': True})
    # Same parameter name, same meaning, across helpers. An agent in the 2026-08-28 round hit
    # the version where it did NOT hold and had to repair a bare-string border by hand.
    check('an input border means what a stack border means (a theme colour id, wrapped)',
          fk.text_input('x', border='line')['props']['border']
          == fk.stack([], border='line')['props']['border'])
    check('an input border refuses a pre-built object, so the two cannot drift apart',
          raises(lambda: fk.text_input('x', border={'color': 1}), (ValueError, TypeError)))
    check('border_width carries through on an input as it does on a stack',
          fk.text_input('x', border='line', border_width=2)['props']['border']['width'] == 2)

    check('email_input validate_format defaults on and is a real boolean',
          fk.email_input('e')['props']['validateEmailFormat'] is True)

    def _two_inputs(id_a, id_b):
        return fk.config(screens=[fk.screen('s1', [fk.email_input(id_a), fk.text_input(id_b)])])

    check('config() refuses two inputs sharing one customId', raises(lambda: _two_inputs('x', 'x')))
    check('config() accepts distinct customIds', bool(_two_inputs('x', 'y')['screens']))

    def _gated(vid):
        return fk.config(screens=[fk.screen('s1', [
            fk.email_input('email'),
            fk.stack([fk.text('Go')], visibility=fk.when(fk.not_empty(fk.ref(vid))))])])

    check('an input PRODUCES the variable a condition consumes', bool(_gated('email.value')))
    check('...and a typo in that variable is still caught', raises(lambda: _gated('emial.value')))

    # --- theme colour hexes. The accepted/refused split below was measured against the real
    # transform service on 2026-08-28, and it is POSITION-SCOPED: element colours accept all
    # of these, theme colours accept only #RRGGBB.
    def _theme(h):
        return fk.config(screens=[fk.screen('s1', [fk.text('hi')])],
                         colors=[('bg', 'Bg', h, '#000000')],
                         typography=[('body', 'Body', 16, 'regular')])

    for good in ('#FFFFFF', '#ffffff', '#00ff7f'):
        check(f'theme hex {good} is accepted (service: ACCEPTED)', bool(_theme(good)))
    for bad_hex in ('#fff', '', 'FFFFFF', '#FFFFFFD9', '#FFFFFFF', 'white'):
        check(f'theme hex {bad_hex!r} raises (service: REFUSED, and location-free)',
              raises(lambda h=bad_hex: _theme(h)))
    check('an ELEMENT colour stays lax — the service accepts a 3-digit hex there',
          fk.hex_color('#fff')['hex'] == '#fff')

    # --- on_selected(): the capability whose ABSENCE shipped a broken paywall (2026-08-28).
    # Without it there was no way to express "selected" from this module, so the look got baked
    # into whichever card started selected and tapping changed nothing on screen.
    _card = fk.on_selected(fk.product([], product_id='p1', group_id='plans', default=True),
                           fill=fk.fill('planOn'), padding=fk.pad(16, 16, 16, 16))
    check('on_selected declares the system selected state on a group member',
          _card['states'] == [{'id': 'selected', 'type': 'system'}])
    check('on_selected puts the overrides under propsByState.selected',
          sorted(_card['propsByState']['selected']) == ['fill', 'padding'])
    _txt = fk.on_selected(fk.text(fk.rich('Annual'), preset='plan'), color=fk.color('ink'))
    check('on_selected works on a descendant too — a text carries the override',
          _txt['propsByState']['selected']['color']['colorId'] == 'ink')
    check('...and does NOT declare states on a non-member element', _txt.get('states') == [])
    check('on_selected with no overrides raises (it would silently do nothing)',
          raises(lambda: fk.on_selected(fk.text(fk.rich('x')))))

    # --- carousel margin: the dot band is the last few px of the carousel's own box and the
    # next element starts immediately after, so clearance is a margin and nothing else.
    _c = fk.carousel([fk.stack([]), fk.stack([])], slide_w=300, slide_h=100,
                     margin={'bottom': 12})
    check('carousel() accepts a margin', _c['props']['margin'] == {'bottom': 12})
    check('carousel() without one writes no margin key',
          'margin' not in fk.carousel([fk.stack([]), fk.stack([])],
                                      slide_w=300, slide_h=100)['props'])

    _COLORS_MIN = [('bg', 'Background', '#FFFFFF', '#101014'),
                   ('ink', 'Ink', '#111114', '#F5F5F7')]
    _TYPO_MIN = [('body', 'Body', 16, 'regular')]

    # --- switch_rich: conditional copy, the mechanism behind a personalization payoff.
    # Shape asserted against the real export tests/fixtures do not carry one of, so the
    # reference is bf5d731e ("Language onboarding — quizzes + branching") in app_finance:
    # the switch nests INSIDE the locale, cases are [cond, const] PAIRS, default is a const.
    _sw = fk.switch_rich(
        [(fk.eq(fk.ref('goal.selectedOptionId'), 'sleep'), ['Sleep plan'])],
        default=['Your plan'])
    _en = _sw['values']['en']
    check('switch_rich nests the switch inside the locale, not around it',
          _sw['_localizable'] is True and _en['type'] == 'switch')
    check('switch_rich emits [condition, const] case pairs',
          isinstance(_en['cases'][0], list) and len(_en['cases'][0]) == 2
          and _en['cases'][0][1]['type'] == 'const')
    check('switch_rich wraps each branch as paragraph blocks, like rich()',
          _en['default']['value'][0]['type'] == 'paragraph'
          and _en['default']['value'][0]['content'][0]['text'] == 'Your plan')
    check('switch_rich takes a bare string as one part',
          fk.switch_rich([(fk.eq(fk.ref('goal.selectedOptionId'), 'a'), 'X')],
                         default='Y')['values']['en']['cases'][0][1]['value'][0]
          ['content'][0]['text'] == 'X')
    check('switch_rich carries Span styling through a branch',
          _sw is not None and fk.switch_rich(
              [(fk.eq(fk.ref('goal.selectedOptionId'), 'a'), [fk.Span('b', bold=True)])],
              default='y')['values']['en']['cases'][0][1]['value'][0]['content'][0]
          ['attrs']['bold'] is True)
    check('switch_rich with no cases raises (it would render the default and nothing else)',
          raises(lambda: fk.switch_rich([], default='x')))
    check('switch_rich rejects a built localizable as parts (it would nest a values map)',
          raises(lambda: fk.switch_rich(
              [(fk.eq(fk.ref('g.selectedOptionId'), 'a'), fk.rich('x'))], default='y'),
              TypeError))
    check('switch_rich rejects a malformed case pair',
          raises(lambda: fk.switch_rich([(fk.eq(fk.ref('g.selectedOptionId'), 'a'),)],
                                        default='y'), TypeError))
    check('switch_rich checks the condition against the service walker',
          raises(lambda: fk.switch_rich([({'type': 'assign'}, 'x')], default='y')))

    # An unresolved variable in a conditional-text switch is COMPILED, so it is fatal —
    # measured against the live service: valid:false, "Generated scripts failed validation",
    # code and path both null. A `variable` SPAN in the same prop is not: it renders its
    # literal token and publishes. Both directions, because the span must NOT be flagged.
    def _doc(content_prop):
        t = fk.text(fk.rich('x'), preset='body', color_id='ink')
        t['props']['content'] = content_prop
        member = fk.selectable([fk.text(fk.rich('A'), preset='body', color_id='ink')],
                               group_id='goal', custom_id='a', default=True)
        s = fk.screen('scr_a', [member, t], fill_=fk.fill('bg'),
                      selectable_groups=[{'id': 'goal', 'type': 'single_choice'}])
        return lambda: fk.config(screens=[s], colors=_COLORS_MIN, typography=_TYPO_MIN)

    check('config() accepts a conditional-text switch on a group that exists',
          _doc(fk.switch_rich([(fk.eq(fk.ref('goal.selectedOptionId'), 'a'), 'A')],
                              default='B'))() is not None)
    check('config() refuses a conditional-text switch naming nothing (hard 422 otherwise)',
          raises(_doc(fk.switch_rich(
              [(fk.eq(fk.ref('nosuch.selectedOptionId'), 'a'), 'A')], default='B'))))
    check('...and still leaves a plain variable SPAN alone — it renders, it does not compile',
          _doc(fk.rich('Hi ', fk.Var('nosuch.value')))() is not None)

    # --- a timer that fires must have a child. Device-measured 2026-09-01 over three trips:
    # the childless form does NOT advance, and every other gate is blind (validate passes both,
    # preview never navigates at all). Raised rather than warned: the flow stops dead and only
    # hardware can show it. This CORRECTS the shape patterns.md published as device-verified.
    check('a timer with a timer-end action and no children raises',
          raises(lambda: fk.timer([], custom_id='d', seconds=3,
                                  actions=[fk.navigate('scr_next')])))
    check('...and the same timer WITH a child is fine',
          fk.timer([fk.timer_digits(units=('seconds',))], custom_id='d', seconds=3,
                   actions=[fk.navigate('scr_next')])['interactions'][0]['trigger']
          == 'timer-end')
    check('...while a childless timer with NO action stays legal (a decorative countdown)',
          fk.timer([], custom_id='d', seconds=3)['type'] == 'timer')

    # ---- attach_point(): the single-plan hidden product element.
    # patterns.md spelled this skeleton with `height: fixed 0` until 2026-09-02 -- the exact shape
    # verify-config.py errors on under trap 15 -- and flowkit exposed no helper, so it was
    # hand-assembled from that skeleton every time. Both halves of finding 12 in one place.
    _ap = fk.attach_point(product_id='p-uuid', group_id='plans')
    check('attach_point is a product element',
          _ap['type'] == 'product')
    check('attach_point height is hug, NEVER fixed 0 (trap 15)',
          _ap['props']['height'] == {'type': 'hug'})
    check('attach_point is hidden — that is what collapses the space',
          _ap['props']['visibility'] == {'type': 'hidden'})
    check('attach_point binds the product and the group',
          _ap['props']['product'] == {'id': 'p-uuid'} and _ap['props']['groupId'] == 'plans')
    check('attach_point is the group default — a lone member must be selected',
          _ap['props']['default'] is True)
    check('attach_point carries the selected system state like any group member',
          _ap['states'] == [{'id': 'selected', 'type': 'system'}])

    # --- id hygiene: the ids that become identifiers in the generated script ---------------
    #
    # An element id outside [A-Za-z0-9_] breaks the generated runtime script and the flow draws
    # a BLACK SCREEN on device, while validate, the schema check and `config preview` all stay
    # green. Unrepresentable beats detectable, so config() raises. SCREEN ids are deliberately
    # NOT checked: 4 of 36 screen ids in the corpus are bare UUIDs on published flows.
    def _doc(screens, **kw):
        return fk.config(screens=screens,
                         colors=[('ink', 'Ink', '#111114', '#F5F5F7')],
                         typography=[('body', 'Body', 16, 'regular')], **kw)

    def _scr(sid, eid, **kw):
        return fk.screen(sid, [fk.text(fk.rich('Hi'), node_id=eid, preset='body',
                                       color_id='ink')], **kw)

    check('config() raises on an element id with a hyphen',
          raises(lambda: _doc([_scr('scr_1', 'el-hero')])))
    check('config() raises on an element id with a dot',
          raises(lambda: _doc([_scr('scr_1', 'el.hero')])))
    check('config() accepts a UUID SCREEN id — real published exports use one',
          _doc([_scr('9fd7c4e1-2b3a-4c5d-8e6f-0a1b2c3d4e5f', 'el_ok')]) is not None)
    check('config() raises on the same element id across two screens',
          raises(lambda: _doc([_scr('scr_1', 'el_cta'), _scr('scr_2', 'el_cta')])))
    check('config() raises on an off-charset customId',
          raises(lambda: _doc([fk.screen('scr_1', [
              fk.text_input('user-name', node_id='el_in')])])))

    # `pt-br` saves and is refused at publish; `sr-Latn` is a real code in a real export, so the
    # naive `^[a-z]{2}(-[A-Z]{2})?$` would be wrong in the other direction.
    check('config() raises on a lowercase region locale code (pt-br)',
          raises(lambda: _doc([_scr('scr_1', 'el_ok')],
                              locales=(('en', 'English'), ('pt-br', 'Portuguese')))))
    check('config() raises on a lowercase script subtag (sr-latn)',
          raises(lambda: _doc([_scr('scr_1', 'el_ok')],
                              locales=(('en', 'English'), ('sr-latn', 'Serbian')))))
    check('config() accepts pt-BR, zh-Hans and sr-Latn',
          _doc([_scr('scr_1', 'el_ok')],
               locales=(('en', 'English'), ('pt-BR', 'Portuguese'),
                        ('zh-Hans', 'Chinese'), ('sr-Latn', 'Serbian'))) is not None)
    # --- icons resolve from the bundle, and _meta.icons is DERIVED ---------------------------
    # Used-here-declared-there is a two-place binding whose second place no gate can see, and the
    # name itself is a third: a phosphor name the renderer's bundle lacks draws blank with an
    # authored `raw` sitting right there.
    print('\nicons:')

    def _iconed(*nodes, **kw):
        return fk.config(screens=[fk.screen('scr_i', list(nodes))],
                         colors=[('ink', 'Ink', '#111114', '#F5F5F7')], **kw)

    check('icon() raises on a name the bundle does not carry',
          raises(lambda: fk.icon('CloseX')))
    check("icon()'s refusal says the element draws blank, not merely that the name is unknown",
          'BLANK' in _message(lambda: fk.icon('CloseX')))
    check('icon() raises on a weight the Builder does not publish',
          raises(lambda: fk.icon('Star', weight='thin')))
    check('icon() accepts a real name at a real weight',
          fk.icon('Star', weight='fill') is not None)

    _cfg = _iconed(fk.icon('ArrowRight'), fk.icon('Star', weight='fill'),
                   typography=[('body', 'Body', 16, 'regular')])
    _declared = {(i['name'], i['weight']) for i in _cfg['_meta']['icons']}
    check('config() declares every icon the tree uses',
          _declared == {('ArrowRight', 'regular'), ('Star', 'fill')}, sorted(_declared))
    check('a derived declaration carries the real markup',
          all(i['raw'].startswith('<svg') and '<path' in i['raw']
              for i in _cfg['_meta']['icons']))

    _spun = _iconed(fk.spinner('spinner1'), typography=[('body', 'Body', 16, 'regular')])
    check('config() declares a Builder custom icon used by spinner()',
          [(i['name'], i['weight']) for i in _spun['_meta']['icons']] == [('spinner1', 'regular')],
          _spun['_meta']['icons'])
    # spinner() deliberately does NOT restrict the name: a custom icon renders from its own
    # declared raw, so a house glyph is legal — but then the entry is the author's to supply,
    # and config() is where that becomes knowable.
    check('config() raises on a custom icon with no markup anywhere',
          raises(lambda: _iconed(fk.spinner('houseGlyph'),
                                 typography=[('body', 'Body', 16, 'regular')])))
    check('config() accepts that same custom icon when the author declares it',
          _iconed(fk.spinner('houseGlyph'), typography=[('body', 'Body', 16, 'regular')],
                  icons=[{'name': 'houseGlyph', 'weight': 'regular',
                          'raw': '<svg xmlns="http://www.w3.org/2000/svg"></svg>'}])
          is not None)

    _explicit = _iconed(fk.icon('ArrowRight'), typography=[('body', 'Body', 16, 'regular')],
                        icons=[{'name': 'ArrowRight', 'weight': 'regular', 'raw': '<svg/>'}])
    check("an author's own entry wins over the derived one",
          [i['raw'] for i in _explicit['_meta']['icons']] == ['<svg/>'],
          _explicit['_meta']['icons'])

    # --- structured product refs (011) and the screen registry (012) ---------------------
    # Both halves matter and they fail in opposite directions. An unconverted ref is a flow
    # that publishes without its offer; a ref converted on a guess is a flow the transformer
    # rejects outright (`unknown_product_group`, `malformed_target`). So every case below
    # asserts which way it went, and the negative cases outnumber the positive ones.
    def _refs(doc):
        found = []

        def walk(o):
            if isinstance(o, list):
                for x in o:
                    walk(x)
            elif isinstance(o, dict):
                if isinstance(o.get('attrs'), dict) and 'productRef' in o['attrs']:
                    found.append(o['attrs']['productRef'])
                if o.get('type') == 'productRef':
                    found.append({k: v for k, v in o.items() if k != 'type'})
                for x in o.values():
                    walk(x)
        walk(doc)
        return found

    _groups = [{'id': 'plans', 'type': 'product'}]
    _bound = fk.screen('scr_p', [
        fk.product([], product_id='p_year', group_id='plans', default=True, offer_id='trial7'),
        fk.product([], product_id='p_month', group_id='plans'),
        fk.text(fk.rich('then ', fk.Var('p_year.prod_price'))),
        fk.text(fk.rich('now ', fk.Var('plans.selectedProduct.prod_price'))),
        fk.text(fk.rich('mine ', fk.Var('my_custom.value'))),
    ], selectable_groups=_groups)
    _found = _refs(_bound)
    check('a bound product resolves, carrying its offer id',
          {'target': {'kind': 'product', 'id': 'p_year', 'offerId': 'trial7'},
           'field': 'prod_price'} in _found, _found)
    check("a product group's selectedProduct resolves",
          {'target': {'kind': 'selected', 'groupId': 'plans'},
           'field': 'prod_price'} in _found, _found)
    check('the legacy variableId is kept beside the ref (dual write)',
          'p_year.prod_price' in json.dumps(_bound))
    check('an ordinary dotted variable is left alone',
          not any('my_custom' in json.dumps(r) for r in _found))
    check('a base binding omits offerId rather than nulling it',
          {'id': 'p_month'} in _bound['products'] and
          {'id': 'p_year', 'offerId': 'trial7'} in _bound['products'], _bound['products'])

    # A DSL operand, which is REPLACED rather than dual-written: an expression has one type.
    # This is a separate branch from the rich-text spans above and needs its own case — a
    # field-value comparison migrates on its own, independently of the identity pair below.
    _dsl = fk.screen('scr_v', [
        fk.product([], product_id='p_a', group_id='plans', default=True, offer_id='intro'),
        fk.stack([fk.text('Trial')],
                 visibility=fk.when(fk.eq(fk.ref('p_a.is_free_trial'), fk.lit(True)))),
    ], selectable_groups=_groups)
    check('a DSL var operand becomes a productRef node, offer and all',
          {'target': {'kind': 'product', 'id': 'p_a', 'offerId': 'intro'},
           'field': 'is_free_trial'} in _refs(_dsl), _refs(_dsl))
    check('its literal operand is untouched', '"value": true' in json.dumps(_dsl))

    # Migration 011's leftovers taxonomy, one case each. All three stay legacy.
    _ambiguous = fk.screen('scr_a', [
        fk.product([], product_id='p', group_id='plans', default=True, offer_id='t1'),
        fk.product([], product_id='p', group_id='plans', offer_id='t2'),
        fk.text(fk.rich(fk.Var('p.prod_price'))),
    ], selectable_groups=_groups)
    check('two offers of one product on a screen: no ref, the offer is unguessable',
          _refs(_ambiguous) == [], _refs(_ambiguous))

    _unbound = fk.screen('scr_u', [fk.text(fk.rich(fk.Var('ghost.prod_price')))])
    check('a product bound nowhere on the screen: no ref',
          _refs(_unbound) == [] and 'ghost.prod_price' in json.dumps(_unbound))

    _foreign = fk.screen('scr_f', [
        fk.selectable([fk.text('a')], group_id='quiz'),
        fk.text(fk.rich(fk.Var('quiz.selectedProduct.prod_price'))),
    ], selectable_groups=[{'id': 'quiz', 'type': 'single_choice'}])
    check('selectedProduct on a non-product group: no ref (transformer would refuse it)',
          _refs(_foreign) == [], _refs(_foreign))

    # The two contracts a productRef must never enter.
    _purchase = fk.screen('scr_b', [
        fk.product([], product_id='p_a', group_id='plans', default=True),
        fk.stack([fk.text('Buy')], actions=[fk.purchase('plans')]),
    ], selectable_groups=_groups)
    check('a purchase payload keeps its dynamicProduct var node',
          '"product": {"type": "var", "variableId": "plans.selectedProduct"}'
          in json.dumps(_purchase))

    _assign = fk.screen('scr_s', [
        fk.product([], product_id='p_a', group_id='plans', default=True),
        fk.stack([fk.text('go')],
                 actions=[fk.set_variable([('p_a.prod_price', fk.lit('x'))])]),
    ], selectable_groups=_groups)
    check('assign.left stays a var node per the JSONAssign contract',
          '"left": {"type": "var", "variableId": "p_a.prod_price"}' in json.dumps(_assign))

    # An identity comparison converts as a UNIT or not at all: one structured side and one
    # legacy side compares a ref against a raw string and is always false.
    _pair = fk.screen('scr_c', [
        fk.product([], product_id='p_year', group_id='plans', default=True),
        fk.product([], product_id='p_month', group_id='plans'),
        fk.stack([fk.text('Best value')],
                 visibility=fk.when(fk.eq(fk.ref('plans.selectedProduct'),
                                          fk.lit('p_year')))),
    ], selectable_groups=_groups)
    check('an identity pair converts both operands, fieldless',
          _refs(_pair) == [{'target': {'kind': 'selected', 'groupId': 'plans'}},
                           {'target': {'kind': 'product', 'id': 'p_year'}}], _refs(_pair))

    _half = fk.screen('scr_d', [
        fk.product([], product_id='p_year', group_id='plans', default=True),
        fk.stack([fk.text('x')],
                 visibility=fk.when(fk.eq(fk.ref('plans.selectedProduct'),
                                          fk.lit('never_bound')))),
    ], selectable_groups=_groups)
    check('an unresolvable operand leaves BOTH sides legacy, never a mixed pair',
          _refs(_half) == [] and 'never_bound' in json.dumps(_half), _refs(_half))

    # A `const` purchase binds with no element behind it, and still has to be declared.
    _const = fk.screen('scr_e', [
        fk.stack([fk.text('buy')], actions=[
            {'id': 'a1', 'type': 'purchase',
             'payload': {'product': {'type': 'const',
                                     'value': {'id': 'p_const', 'offerId': 'intro'}}}}]),
    ])
    check('a const purchase product reaches the registry with no product element',
          _const['products'] == [{'id': 'p_const', 'offerId': 'intro'}], _const['products'])


    # --- catalog templates -----------------------------------------------------------------
    # A catalog template is the builder's own output, in the EXPORT shape. Until from_catalog()
    # existed there was no way to feed one to screen(), so the templates the skill tells agents
    # to prefer were unreachable from the module that assembles the document.
    _cat = json.load(open(os.path.join(ROOT, 'skills', 'flow-generator', 'references',
                                       'component-catalog.json')))
    _by_id = {c['id']: c for c in _cat['components']}

    _tpl = json.loads(json.dumps(_by_id['prod-vertical-list']['template']))
    _nodes = fk.from_catalog(_tpl, group_id='plans')
    check('from_catalog returns a list of nodes', isinstance(_nodes, list) and len(_nodes) == 1)
    check('from_catalog does not mutate the template it was given',
          _tpl == _by_id['prod-vertical-list']['template'])
    check('from_catalog renames the group so two templates cannot share one',
          all(n['props']['groupId'] == 'plans' for n in _nodes[0]['_children']))

    def _walk_nodes(node):
        yield node
        for kid in node.get('_children', []):
            yield from _walk_nodes(kid)

    _all = list(_walk_nodes(_nodes[0]))
    check('from_catalog mints an id for every node',
          all(n.get('id') for n in _all) and len({n['id'] for n in _all}) == len(_all))
    check('from_catalog moves children into the authoring key',
          all('children' not in n for n in _all))

    # The footer template ships `"id": ""` on its restore interaction — the builder's placeholder.
    _foot = fk.from_catalog(json.loads(json.dumps(_by_id['footer']['template'])))
    _inters = [i for n in _walk_nodes(_foot[0]) for i in n.get('interactions', [])]
    check('from_catalog fills the placeholder interaction and action ids',
          _inters and all(i['id'] and all(a['id'] for a in i['actions']) for i in _inters))
    check('from_catalog refuses a catalog ENTRY where a template was meant',
          raises(lambda: fk.from_catalog(_by_id['footer']), TypeError))

    # A screen assembled from the two templates is the commonest paywall there is, and it has to
    # come out of the module publishable rather than merely well-formed.
    _plans = fk.from_catalog(json.loads(json.dumps(_by_id['prod-vertical-list']['template'])),
                             group_id='plans')
    for _i, _card in enumerate(_plans[0]['_children']):
        _card['props']['product'] = {'id': f'prod-{_i}'}
    try:
        _scr = fk.screen('scr_pay', _plans + fk.from_catalog(
            json.loads(json.dumps(_by_id['footer']['template']))), scrollable=True,
            selectable_groups=[{'id': 'plans', 'type': 'product'}])
    except Exception as _exc:                                   # noqa: BLE001
        _scr = {'products': [{'id': f'screen() refused: {_exc}'}]}
    check('a screen built from the product template declares every card in its registry',
          [p['id'] for p in _scr['products']] == ['prod-0', 'prod-1', 'prod-2'],
          _scr.get('products'))

    # --- font weights ----------------------------------------------------------------------
    # `weight: 600` passes the publish gate and then kills the render.
    check('a numeric font weight is refused',
          'not a font weight' in _message(
              lambda: fk.config(screens=[], colors=[], typography=[('b', 'B', 16, 600)])))
    check('every name in FONT_WEIGHTS is accepted',
          all(fk.config(screens=[], colors=[],
                        typography=[('b', 'B', 16, w)])['theme']['typography'][0]['settings']
              ['weight'] == w for w in fk.FONT_WEIGHTS))

    print()
    if FAILURES:
        print(f'{len(FAILURES)} failure(s): ' + ', '.join(FAILURES))
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
