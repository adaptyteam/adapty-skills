#!/usr/bin/env python3
"""Is this flow ready for production?

Structural, offline half of the `flow-audit` skill. Takes a flow config and the app's
product catalog; returns findings. No network, no CLI calls -- `SKILL.md` owns those, so
this script stays testable against fixtures.

Severity is a verdict input, not a mood:
  blocker  -- the flow will not work for a real user, OR will show them something false
  risk     -- it works and is probably not what anyone intended
  question -- not decidable from the data available; state what you could not see

Every check here is calibrated in both directions against `tests/fixtures/`. See
`checks.md` before changing one -- most of these were wrong on first contact with real
data, and the traps are recorded there.

Usage:
  audit-flow.py <config.json> [--catalog <catalog.json>] [--stores ios,android]
                [--json | --report] [--name <name>] [--flow-id <id>] [--status <status>]
                [--placements <placements.json>]
Exit: 0 no blockers, 1 at least one blocker, 2 usage or unreadable input.

`--json` prints the raw findings; `--report` prints the user-facing report (verdict,
findings by severity, languages, store review, what happens next, what to check
yourself) and the two are mutually exclusive. `--name`/`--flow-id`/`--status` come
from `flows list`, not the config, and feed `render()`'s header and the
`flow-untitled` check. `--placements` is a JSON array of `placements get` bodies; with
`--flow-id` it answers whether any placement shows this flow.
"""
import ast, json, os, re, sys

# The localization catalog reader, shipped beside this file (a byte-identical copy of
# flow-generator's, so a directory-copy install of this skill alone still has it). Every check
# below reads the resolved view it produces: a stored flow holds `{_lid}` refs, and a check
# that read those directly would see no text anywhere and report a clean flow.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    import localization as _loc
finally:
    sys.dont_write_bytecode = _bytecode

SEVERITIES = ('blocker', 'risk', 'question')
FAMILIES = ('triggers', 'compliance', 'products', 'variables', 'localization',
            'placeholders', 'placement', 'navigation')


def finding(severity, family, check, message, fix, screen=None, element=None):
    assert severity in SEVERITIES, severity
    assert family in FAMILIES, family
    return {'severity': severity, 'family': family, 'check': check, 'screen': screen,
            'element': element, 'message': message, 'fix': fix}


def screen_name(config, sid):
    """The name the Flow Builder shows for a screen (its `caption`), falling back to
    the id when a screen has none. Every location a user reads goes through this: a
    screen id like `scr_RvSel001` means nothing to them, while "Select plan" is what
    they see in the builder's screen list.
    """
    for s in (config or {}).get('screens') or []:
        if s.get('id') == sid:
            return s.get('caption') or sid
    return sid


def _tag(f, **report_only):
    """Attach report-only fields (underscore-prefixed) that `render()` needs to merge
    findings -- a product title, a store, an amount -- so it never has to parse them
    back out of the message. `--json` strips every underscore key, so the finding
    contract stays the seven keys it has always been."""
    f.update({f'_{k.lstrip("_")}': v for k, v in report_only.items()})
    return f


def load_config(path):
    """Accept either the `config get` envelope or a bare config, and return the READ VIEW:
    every catalog ref inlined, `locales`/`defaultLocale` copied to the top level."""
    doc = json.load(open(path))
    doc = doc['config'] if isinstance(doc, dict) and 'config' in doc else doc
    return _loc.resolve(doc) if isinstance(doc, dict) else doc


def elements(config):
    """Yield (screen, element_id, element) over every screen element."""
    for s in config.get('screens') or []:
        for eid, e in ((s.get('elements') or {}).get('map') or {}).items():
            yield s, eid, e


# An affordance the copy promises. Deliberately short and specific: the check is that
# copy NAMES an action while neither the element itself NOR ANY ANCESTOR (walked through
# the screen's `elements.hierarchy` tree) carries an interaction. The ancestor walk is
# load-bearing: `tabs-paywall.json`'s "Skip"/"Terms"/"Restore"/"Privacy" and this
# fixture's own "Skip" text are all standalone labels whose tap target lives on a parent
# `stack`, and the walk clears every one of them. `comparison-paywall.json`'s "Restore" /
# "Terms" / "Privacy" (el_CqN7LxyqK8 / el_WiqJNVPbb8 / el_zSZPjSyaqU) are genuinely dead --
# no ancestor is wired, and the whole flow contains no `restorePurchases` action and no
# `openUrl` action anywhere. `cancel anytime` was dropped from the vocabulary: in
# `timeline-anchored.json` it is reassurance copy ("Cancel anytime."), never an
# affordance a user taps, and it was the one true false positive under this vocabulary.
AFFORDANCE_WORDS = ('restore', 'terms', 'eula', 'privacy', 'skip',
                     'manage subscription', 'unsubscribe')

# An affordance is a LABEL, not a sentence -- word-boundary matching alone is not
# enough, since "in terms of cost per session" contains `terms` as a whole word.
# Four reproduced false-positive blockers under raw substring matching, all ordinary
# marketing copy that happens to contain an affordance word in passing: "Restore your
# natural sleep rhythm in 7 days", "We take your privacy seriously and never sell
# your data" (near-boilerplate on a paywall), "The best value in terms of cost per
# session", "Skip the guesswork — we plan every workout for you". The fix: split the
# element's text on the separators a real label ROW uses to pack several affordances
# into one element ("Restore purchase · Terms · Privacy" -- `el_089T` in
# `onboarding-multilocale.json`), then treat a segment as an affordance only when the
# ENTIRE segment (stripped of trailing punctuation) IS that affordance -- the bare
# word, or the word plus one of a small closed set of qualifiers that still read as a
# label ("Restore purchase", "Terms of use"). A segment carrying a sentence around
# the word is never a label, however it is punctuated. `comparison-paywall.json`'s
# "Restore" / "Terms" / "Privacy" (three separate elements, so each is trivially its
# own whole segment) and `el_089T`'s three-affordance row must both still fire.
AFFORDANCE_SEPARATORS = re.compile(r'\s*(?:·|\||•|/|\n)\s*|\s+and\s+', re.I)
AFFORDANCE_QUALIFIERS = ('purchase', 'purchases', 'policy', 'of use', 'of service',
                         '& conditions', 'and conditions')


def _affordance_labels(text):
    """The AFFORDANCE_WORDS this copy names AS A LABEL -- never as a word merely
    present inside a longer sentence. See the module comment above for why."""
    segs = {seg.strip().lower().strip('.,:;!?')
            for seg in AFFORDANCE_SEPARATORS.split(text or '')}
    segs.discard('')
    out = []
    for w in AFFORDANCE_WORDS:
        if w in segs or any(f'{w} {q}' in segs for q in AFFORDANCE_QUALIFIERS):
            out.append(w)
    return out


def flat_text(value, locale=None):
    """Flatten a localizable and/or rich-text value to its literal text.

    Returns '' for a value whose only content is a variable/token/image node -- a price
    element is exactly that shape, so callers must not read '' as "empty field".
    """
    if isinstance(value, dict) and 'values' in value:
        vals = value['values']
        value = vals.get(locale) if locale in (vals or {}) else next(iter((vals or {}).values()), None)
    out = []

    def walk(n):
        if isinstance(n, dict):
            if n.get('type') == 'text':
                out.append(n.get('text', ''))
            for x in (n.get('content') or []):
                walk(x)
        elif isinstance(n, list):
            for x in n:
                walk(x)
        elif isinstance(n, str):
            out.append(n)
    walk(value)
    return ' '.join(''.join(out).split())


def node_kinds(value, locale=None):
    """The node `type`s present in a localizable/rich-text value."""
    if isinstance(value, dict) and 'values' in value:
        vals = value['values']
        value = vals.get(locale) if locale in (vals or {}) else next(iter((vals or {}).values()), None)
    kinds = []

    def walk(n):
        if isinstance(n, dict):
            if n.get('type'):
                kinds.append(n['type'])
            for x in (n.get('content') or []):
                walk(x)
        elif isinstance(n, list):
            for x in n:
                walk(x)
        elif isinstance(n, str):
            kinds.append('text')
    walk(value)
    return kinds


def default_locale(config):
    return config.get('defaultLocale') or next(
        (l.get('id') for l in (config.get('locales') or [])), None)


def locale_ids(config):
    """Declared locale ids -- what every `values` map is keyed by."""
    return [l.get('id') for l in (config.get('locales') or []) if l.get('id')]


def locale_names(config):
    """id -> the name the builder shows ("Serbian (Latin)"), never the id or code."""
    return {l.get('id'): l.get('name') or l.get('code') or l.get('id')
            for l in (config.get('locales') or []) if l.get('id')}


def actions_of(element):
    for i in (element.get('interactions') or []):
        for a in (i.get('actions') or []):
            yield i, a


def _parent_map(hierarchy):
    """child element id -> parent element id, from a screen's `elements.hierarchy` tree."""
    pm = {}

    def walk(node, parent):
        nid = node.get('id')
        if parent is not None and nid is not None:
            pm[nid] = parent
        for c in (node.get('children') or []):
            walk(c, nid)
    if hierarchy:
        walk(hierarchy, None)
    return pm


def _wired(eid, elements_map, parent_map):
    """True if this element or any ancestor (per `parent_map`) carries a real interaction."""
    seen = set()
    cur = eid
    while cur is not None and cur not in seen:
        seen.add(cur)
        e = elements_map.get(cur)
        if e and (e.get('interactions') or []):
            return True
        cur = parent_map.get(cur)
    return False


def check_triggers(config):
    out = []
    dl = default_locale(config)
    pm_cache = {}
    for s, eid, e in elements(config):
        m = (s.get('elements') or {}).get('map') or {}
        key = id(s)
        if key not in pm_cache:
            pm_cache[key] = _parent_map((s.get('elements') or {}).get('hierarchy'))
        pm = pm_cache[key]
        txt = flat_text((e.get('props') or {}).get('content'), dl)
        named = _affordance_labels(txt)
        if named and not _wired(eid, m, pm):
            out.append(finding(
                'blocker', 'triggers', 'dead-affordance',
                f'"{txt[:70]}" looks tappable but does nothing: it says '
                f'{_join_and(named)}, and neither it nor anything around it has an '
                f'On Tap action.',
                'Give it an On Tap action that does what the text says. If it names '
                'several things, make each one its own tappable element.',
                s['id'], eid))
        for i, a in actions_of(e):
            if a.get('type') == 'nothing':
                out.append(finding(
                    'risk', 'triggers', 'action-nothing',
                    'A tap here is set to "Do nothing", so it looks tappable and '
                    'nothing happens.',
                    'Give it a real action, or remove the On Tap interaction.',
                    s['id'], eid))
            if a.get('type') == 'openUrl' and not (a.get('payload') or {}).get('url'):
                out.append(finding(
                    'blocker', 'triggers', 'openurl-no-url',
                    'An "Open URL" action has no web address, so the tap goes nowhere.',
                    'Enter the address, or remove the action.',
                    s['id'], eid))
        for i in (e.get('interactions') or []):
            if not (i.get('actions') or []):
                out.append(finding(
                    'risk', 'triggers', 'interaction-no-actions',
                    'This element has an On Tap interaction with no actions in it, so '
                    'the tap does nothing.',
                    'Add an action to it, or remove the interaction.', s['id'], eid))
    return out


ESCAPE_ACTIONS = ('closeFlow', 'navigateBack')

# Legal-link detection lives on the openUrl action's URL PAYLOAD, never on the
# button's label. A label is a design choice -- measured: 7 of 9 real escape
# affordances (`escape_labels` above) are icon-only with no text at all, which is
# exactly why escape detection lives on action type rather than copy. A button
# labeled "Legal" that opens https://example.com/terms is a real terms link; matching
# on the label instead would have called it absent. Two small, separate vocabularies
# of URL tokens, matched case-insensitively against the url itself:
TERMS_URL_WORDS = ('terms', 'tos', 'eula', 'legal', 'conditions')
PRIVACY_URL_WORDS = ('privacy', 'policy')


def _url_tokens(url):
    """Split a url into lowercase alphanumeric tokens on any non-alphanumeric run.

    Matching a vocabulary word by substring containment is a false-negative trap:
    'tos' matches inside 'photos' and 'autos', 'legal' matches inside 'illegally',
    which SILENCES a real compliance blocker -- a paywall whose only openUrl points
    at a hero image reads as compliant. Tokenizing on separators and requiring an
    EXACT token match closes that: 'photos'/'hero'/'jpg' and 'illegally'/'obtained'/
    'content' contain no vocabulary token, while '/tos' and 'terms-of-service' still
    tokenize to 'tos' and 'terms'/'of'/'service' respectively.

    Deliberate direction of error: a concatenated path with no separator at all
    (`/termsofservice`) now tokenizes to one unsplit word and will not match, which
    turns a would-be silent pass into a QUESTION asking the human to confirm the url.
    A question is honest; false silence on an App Store 3.1.2 requirement is not.
    """
    return set(re.split(r'[^a-z0-9]+', url.lower()))


def selling_screens(config):
    """A screen sells if it binds a product or carries a purchase action."""
    out = set()
    for s, eid, e in elements(config):
        if ((e.get('props') or {}).get('product') or {}).get('id'):
            out.add(s['id'])
        for _, a in actions_of(e):
            if a.get('type') == 'purchase':
                out.add(s['id'])
    return out


def _nav_targets(node, sid, order):
    """Every screen a navigate or navigateNext anywhere inside `node` can lead to,
    including inside a conditional's branches -- a branch is still a way off the
    screen, and missing it made the reachability walk blind to quiz routing."""
    out = []
    if isinstance(node, dict):
        if node.get('type') == 'navigate':
            tgt = (node.get('payload') or {}).get('screen')
            if tgt:
                out.append(tgt)
        elif node.get('type') == 'navigateNext':
            i = order.index(sid) if sid in order else -1
            if 0 <= i < len(order) - 1:
                out.append(order[i + 1])
        for v in node.values():
            out += _nav_targets(v, sid, order)
    elif isinstance(node, list):
        for v in node:
            out += _nav_targets(v, sid, order)
    return out


def nav_graph(config):
    """screen id -> screens reachable by one navigate/navigateNext edge, branches included."""
    order = [s['id'] for s in config.get('screens') or []]
    edges = {sid: set() for sid in order}
    for s, eid, e in elements(config):
        for _, a in actions_of(e):
            edges[s['id']].update(_nav_targets(a, s['id'], order))
    return edges


def escape_screens(config):
    """Screens that carry an escape action of their own."""
    out = set()
    for s, eid, e in elements(config):
        for _, a in actions_of(e):
            if a.get('type') in ESCAPE_ACTIONS:
                out.add(s['id'])
    return out


def escape_labels(config):
    """(screen, label) for every escape affordance. Measured: 7 of 9 are icon-only, so
    the label is reported as evidence and never used for detection."""
    dl = default_locale(config)
    out = []
    for s, eid, e in elements(config):
        for _, a in actions_of(e):
            if a.get('type') in ESCAPE_ACTIONS:
                out.append((s['id'],
                            flat_text((e.get('props') or {}).get('content'), dl)
                            or 'an icon with no text'))
    return out


def openurl_urls(config):
    """Every url carried by an openUrl action's payload, flattened to plain text.

    The mechanism's own target, not the button's label -- see the vocab comment
    above. A url may be a plain string or a localizable/rich-text value; `flat_text`
    already handles the latter, so both shapes are covered here. Empty urls (an
    `openUrl` with no `url` at all) are dropped -- `check_triggers`'s
    `openurl-no-url` already flags that as its own defect, so this list is never the
    reason `no-terms-link`/`no-privacy-link` mistakes an unset url for a real one.
    """
    dl = default_locale(config)
    out = []
    for _, eid, e in elements(config):
        for _, a in actions_of(e):
            if a.get('type') != 'openUrl':
                continue
            url = (a.get('payload') or {}).get('url')
            text = url if isinstance(url, str) else flat_text(url, dl)
            if text:
                out.append(text)
    return out


def _reaches(edges, start, targets):
    seen, queue = {start}, [start]
    while queue:
        cur = queue.pop(0)
        if cur in targets:
            return cur
        for nxt in edges.get(cur, ()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return None


def check_compliance(config):
    out = []
    # `no-escape-in-flow` applies to ANY flow, selling or not -- a non-paywall
    # onboarding flow with no way off is exactly the case this check exists to name,
    # so it runs ahead of the selling-screen gate below rather than behind it.
    # `no-escape-from-paywall` stays scoped to selling screens: it needs both a
    # selling screen and a nav graph to walk from it.
    edges, escapes = nav_graph(config), escape_screens(config)
    if not escapes:
        out.append(finding(
            'question', 'compliance', 'no-escape-in-flow',
            'Nothing in this flow lets a user leave it: there is no "Close Flow" or '
            '"Navigate back" action anywhere.',
            'If your app shows this flow with its own close button or swipe-to-dismiss, '
            'you are fine. If not, add a close button with a "Close Flow" action.'))

    selling = selling_screens(config)
    if not selling:
        return out
    dl = default_locale(config)
    all_actions = {a.get('type') for _, eid, e in elements(config) for _, a in actions_of(e)}
    corpus_text = ' '.join(
        flat_text((e.get('props') or {}).get('content'), dl).lower()
        for _, eid, e in elements(config))

    if 'restorePurchases' not in all_actions:
        out.append(finding(
            'blocker', 'compliance', 'no-restore',
            'There is no way to restore a purchase. Someone who reinstalls your app '
            'or moves to a new phone cannot get their subscription back.'
            + (' The text mentions "restore", but nothing is wired to it.'
               if 'restore' in corpus_text else ''),
            'Add a "Restore purchases" action to a button, usually a small link under '
            'the purchase button. (App Store 3.1.1)'))

    # Three outcomes, in order of certainty. (1) No `openUrl` action anywhere: there
    # cannot be a legal link without one, so both checks are a blocker. (2) An
    # `openUrl` exists and some url matches the pattern: silent -- the link is real,
    # whatever the button says. (3) An `openUrl` exists but nothing matches: this is
    # NOT a blocker, because the audit cannot know what an arbitrary url points to --
    # a shortlink or a `/legal` page may well serve the document -- so it is a
    # question that names the urls actually found and asks the human to confirm.
    urls = openurl_urls(config)
    url_token_sets = [_url_tokens(u) for u in urls]
    for words, name, label in ((TERMS_URL_WORDS, 'no-terms-link', 'Terms of Use'),
                              (PRIVACY_URL_WORDS, 'no-privacy-link', 'Privacy Policy')):
        if not urls:
            out.append(finding(
                'blocker', 'compliance', name,
                f'There is no link to your {label}: the flow has no "Open URL" '
                'action at all.',
                f'Add a link with an "Open URL" action that opens your {label} page. '
                '(App Store 3.1.2)'))
            continue
        # Exact token match, never substring containment -- see `_url_tokens`.
        if any(w in toks for toks in url_token_sets for w in words):
            continue  # a url matches -- the link is real, regardless of the label
        shown = ', '.join(sorted(set(urls)))
        out.append(finding(
            'question', 'compliance', name,
            f'The flow has links, but none of them looks like your {label}: {shown}',
            f'If one of them is your {label}, there is nothing to do. If not, add a '
            f'link with an "Open URL" action that opens it.'))

    if escapes:
        # Evidence for the human, never a detection signal: 7 of 9 measured escape
        # affordances are icon-only with no text at all, so a label can only be shown,
        # not matched on. Dedup so a flow with several identical icon buttons prints
        # one line instead of one per button.
        seen_labels = []
        for _, lbl in escape_labels(config):
            if lbl not in seen_labels:
                seen_labels.append(lbl)
        labels_str = '; '.join(seen_labels)
        for sid in sorted(selling):
            if _reaches(edges, sid, escapes) is None:
                out.append(finding(
                    'blocker', 'compliance', 'no-escape-from-paywall',
                    'Someone who does not buy cannot leave this screen: no "Close Flow" '
                    'or "Navigate back" action can be reached from it. Other screens in '
                    f'the flow do have a way out ({labels_str}).',
                    'Add a close button with a "Close Flow" action. A close icon with no '
                    'text is enough.', sid))
    # else: escapes is empty, already handled above by `no-escape-in-flow` -- when
    # there is no escape ANYWHERE, the per-screen reachability blocker below would be
    # true of every selling screen too, which is exactly the redundant restating the
    # flow-wide question already exists to avoid.
    return out


def _element_product_id(e):
    """The product id bound via a `product` ELEMENT's own props, or None.

    The one extraction site for this shape -- it used to be typed out identically in
    `bound_products`, `check_period_claim` and `check_price_integrity`, which is
    exactly the kind of duplication that lets a fix land in one place and miss the
    other two. This shape is the only one that gives a caller an element to attach a
    finding to AND card copy to read (via `card_text`/`_element_blobs`), which is
    why `check_period_claim` and `check_price_integrity` -- both of which need card
    copy -- stay scoped to it alone and never see the shape below.
    """
    return ((e.get('props') or {}).get('product') or {}).get('id')


def _const_purchase_product_id(action):
    """The product id bound by a `const` purchase ACTION's payload, or None.

    A `const` purchase action binds a product with no `product` element behind it and
    no card copy to read -- CLAUDE.md documents the shape (verified against
    `verify-config.py`'s own `missing flowProductId` check, path `...purchase.product`).
    Only the catalog checks (`product-not-in-catalog` and friends) need to see this
    shape, since none of them read card copy -- see `bound_products`.
    """
    if action.get('type') != 'purchase':
        return None
    prod = (action.get('payload') or {}).get('product') or {}
    if prod.get('type') != 'const':
        return None
    return (prod.get('value') or {}).get('id')


def bound_products(config):
    """(screen id, element id, product id) for every product binding in the flow --
    a `product` element's own props, OR a `const` purchase action carried by an
    element's interactions. Catalog-only consumer: this is the shape the four
    catalog checks need (none of them read card copy). `check_period_claim` and
    `check_price_integrity` need card copy, which only the element shape has, so
    they call `_element_product_id` directly and never this function -- see its
    docstring for why that split is deliberate, not an oversight.

    Deduplicated per (screen, element, product): an element carrying both a
    `product` prop AND a `const` purchase action for the same id would otherwise
    report the same binding site twice.
    """
    out = []
    for s, eid, e in elements(config):
        seen_here = set()
        pid = _element_product_id(e)
        if pid:
            out.append((s['id'], eid, pid))
            seen_here.add(pid)
        for _, a in actions_of(e):
            cpid = _const_purchase_product_id(a)
            if cpid and cpid not in seen_here:
                out.append((s['id'], eid, cpid))
                seen_here.add(cpid)
    return out


def _format_sites(sites, config, cap=3):
    """Render binding sites by the screen names the builder shows: 'the "Plans"
    screen', 'the "Plans" and "Offer" screens', 'the "A", "B", "C" screens and 2 more'.

    One entry per SCREEN, not per element -- an element id means nothing to the
    person reading the report, and two cards on one screen are one place to look.
    Capped so a product bound across many screens still reads as one line, with the
    count after 'and' covering every screen that did not make the cut.
    """
    names = []
    for sid, _eid in sites:
        name = screen_name(config, sid)
        if name not in names:
            names.append(name)
    shown = [f'"{n}"' for n in names[:cap]]
    extra = len(names) - len(shown)
    if extra > 0:
        return f'the {", ".join(shown)} screens and {extra} more'
    return f'the {_join_and(shown)} screen' + ('s' if len(shown) > 1 else '')


def check_products_catalog(config, catalog, stores):
    """Cross-reference bound products against the live catalog.

    `stores` is the set of stores the app ships on, or None when unknown. Unknown is why
    a store gap is a question rather than a blocker -- the audit cannot see the app.

    `base_plan_id` is read ONLY off a `play_store` entry -- it is a Google Play concept
    and is null on essentially every `app_store` entry, so reading it unscoped fires on
    the whole catalog.

    All four checks below dedup PER PRODUCT, not per binding: the same product bound
    on two elements must produce one finding, not two, and that finding's message
    names every binding site (`_format_sites`) so fixing the deduped finding does not
    leave the user unaware that a second screen binds the same broken product. This
    used to be inconsistent -- `product-not-in-catalog` fired once per binding because
    its `continue` sat before the `seen` check, while the other three checks deduped
    but silently dropped every site after the first. Grouping by product id up front
    fixes both: dedup is now uniform, and no location is ever silently dropped.
    """
    out = []
    if catalog is None:
        if bound_products(config):
            out.append(finding(
                'question', 'products', 'catalog-not-fetched',
                'I could not read your product list, so I could not check the products '
                'this flow sells.',
                'Fetch the product list and run the audit again.'))
        return out
    by_id = {p['id']: p for p in catalog}
    by_pid = {}
    for sid, eid, pid in bound_products(config):
        by_pid.setdefault(pid, []).append((sid, eid))

    for pid, sites in by_pid.items():
        first_sid, first_eid = sites[0]
        # ' It is on the "Plans" screen.' -- or nothing on a one-screen flow, where
        # naming the screen tells the reader nothing.
        sites_str = ('' if len(config.get('screens') or []) <= 1
                     else f' It is on {_format_sites(sites, config)}.')
        prod = by_id.get(pid)
        if prod is None:
            out.append(finding(
                'blocker', 'products', 'product-not-in-catalog',
                f'This flow sells a product that does not exist in your app ({pid}), '
                f'so the purchase will fail.{sites_str}',
                'Choose one of your existing products for it, or create the product '
                'in the Adapty dashboard first.', first_sid, first_eid))
            continue
        title = prod.get('title') or pid
        vendors = prod.get('vendor_products') or {}
        if not prod.get('access_level_id'):
            out.append(finding(
                'blocker', 'products', 'product-no-access-level',
                f'"{title}" has no access level, so someone who buys it gets nothing '
                f'unlocked.{sites_str}',
                'In the Adapty dashboard, open the product and set its access level.',
                first_sid, first_eid))
        if not vendors:
            out.append(finding(
                'blocker', 'products', 'product-store-gap',
                f'"{title}" is not linked to the App Store or Google Play, so nobody '
                f'can buy it.{sites_str}',
                'In the Adapty dashboard, open the product and add its App Store '
                'and/or Google Play product ID.',
                first_sid, first_eid))
        else:
            missing = {'ios': 'app_store', 'android': 'play_store'}
            store_word = {'ios': ('App Store', 'iOS'), 'android': ('Google Play', 'Android')}
            for want, key in missing.items():
                store_name, platform = store_word[want]
                if key in vendors:
                    continue
                if stores is None:
                    out.append(_tag(finding(
                        'question', 'products', 'product-store-gap',
                        f'"{title}" has no {store_name} product ID, so it cannot be '
                        f'bought on {platform}.{sites_str}',
                        f'If you ship on {platform}, add its {store_name} product ID '
                        f'in the Adapty dashboard.',
                        first_sid, first_eid), _title=title, _store=store_name,
                        _platform=platform, _sites=sites))
                elif want in stores:
                    out.append(_tag(finding(
                        'blocker', 'products', 'product-store-gap',
                        f'"{title}" has no {store_name} product ID, but your app ships '
                        f'on {platform}, so the purchase will fail there.'
                        f'{sites_str}',
                        f'In the Adapty dashboard, add its {store_name} product ID.',
                        first_sid, first_eid), _title=title, _store=store_name,
                        _platform=platform, _sites=sites))
            play = vendors.get('play_store')
            if play and not play.get('base_plan_id'):
                out.append(finding(
                    'blocker', 'products', 'play-base-plan-missing',
                    f'"{title}" has a Google Play product ID but no base plan ID. '
                    f'Google Play needs both to sell a subscription.'
                    f'{sites_str}',
                    'In the Adapty dashboard, add the base plan ID from Play Console '
                    'to the product.',
                    first_sid, first_eid))
    return out


# A trial duration is not a billing period: "7 Days Trial" read as weekly, which broke
# the naive version on a real flow. Stripped before any period matching.
TRIAL_RE = re.compile(r'\b\d+\s*(?:-|\s)?\s*(?:day|week|month)s?\s*(?:free\s*)?trial\b'
                      r'|\btrial\b', re.I)

# Ordered longest-unit-first. A multiplied unit ("12 mo") names the OUTER period and must
# be consumed before the bare unit ("mo") can claim it -- otherwise "12 mo • $79.99" on an
# annual product reads as monthly. `once` is deliberately absent: "Billed once a year"
# read as lifetime.
#
# `[\s-]*` between the digit and the unit, not `\s*` -- real copy hyphenates ("12-month
# plan", "3-month plan", "52-week plan") and a bare `\s*` never matches a hyphen, so
# every one of those fell through to the bare-unit rule below and read as monthly/
# weekly instead of annual/quarterly. The bare monthly/weekly rules also gained the
# plural (`months`, `weeks`) -- without it "12-months" matched no rule at all rather
# than falling through, because "month"/"mo"/"mos" all fail their own trailing `\b`
# against the extra trailing "s". The ordering and destructive consumption are
# unchanged: "12 months" is still eaten whole by the annual multiplied-unit rule
# before the bare monthly rule ever sees it, so it still resolves to {'annual'} alone.
PERIOD_RULES = [
    ('annual',    r'\b(?:12[\s-]*(?:mo|mos|month|months)|52[\s-]*(?:wk|weeks?))\b'),
    ('quarterly', r'\b(?:3[\s-]*(?:mo|mos|month|months)|13[\s-]*(?:wk|weeks?))\b'),
    ('annual',    r'\b(?:year|yearly|annual|annually|yr)\b|/\s*(?:yr|year)'),
    ('quarterly', r'\b(?:quarter|quarterly)\b'),
    ('monthly',   r'\b(?:month|months|monthly|mo|mos)\b|/\s*(?:mo|month)'),
    ('weekly',    r'\b(?:week|weeks|weekly|wk)\b|/\s*(?:wk|week)'),
    ('lifetime',  r'\b(?:lifetime|one[ -]?time)\b'),
]


# A period word is a genuine billing CLAIM only in a price/billing context -- never
# merely present anywhere in the card's copy. Reproduced: rewriting a real annual
# card's text to "Pro | Weekly progress reports" read as a WEEKLY period claim purely
# because the benefit sentence contains the word "weekly"; `period_terms` also
# returned {monthly} for "Cancel anytime, no monthly fees" (near-boilerplate),
# {annual} for "Save 50% a year" (a savings claim, not a period), and {monthly} for
# "Your monthly report" (a feature, not a plan). The real corpus is terse ("Yearly",
# "Monthly", "12 mo • $79.99"), which is exactly why calibration never caught this --
# every real card's period word WAS the whole point of its segment, so "present
# anywhere" and "in billing context" happened to coincide.
#
# `card_text` joins a card's descendant text elements with " | ", so context is
# judged per SEGMENT, split on that same separator -- one product card's own price
# line must not lend a neighbouring benefit line's unrelated period word legitimacy
# just because `card_text` concatenated them into one blob. Within a segment, a
# period match counts as a claim when EITHER removing the matched text leaves
# nothing but whitespace/punctuation or a bare plan noun (`monthly` alone, or
# `12-month plan`'s trailing `plan` -- the segment names nothing else), OR the
# segment carries a currency amount (`MONEY_RE`), a `/` rate marker (already part of
# several `PERIOD_RULES` alternatives, e.g. `/mo`), or a billing verb (`billed`,
# `per`, `every`, `renews`). A price-VARIABLE's own text never reaches this
# function at all -- `card_text` calls `flat_text`, which renders a `variable` node
# as `''`, so an empty segment is dropped by `card_text` before the join; there is
# no literal "adjacent to a price variable" case left to detect here.
PLAN_LABEL_TRAILERS = {'plan'}
BILLING_VERB_RE = re.compile(r'\b(?:billed|per|every|renews?)\b', re.I)


def _billing_context(segment, start, end):
    """True if the period match `segment[start:end]` sits in a price/billing
    context, per the module comment above `period_terms`."""
    leftover = (segment[:start] + segment[end:]).strip(' \t-—|·/.,')
    if not leftover or leftover.lower() in PLAN_LABEL_TRAILERS:
        return True
    if MONEY_RE.search(segment) or '/' in segment:
        return True
    return bool(BILLING_VERB_RE.search(segment))


def period_terms(text):
    """The billing periods this copy claims, in a price/billing context (see the
    module comment above). Longest unit first, trials stripped, one card-text
    segment at a time."""
    found = set()
    for raw in (text or '').split(' | '):
        segment = TRIAL_RE.sub(' ', raw)
        rest = segment
        for name, rx in PERIOD_RULES:
            for m in list(re.finditer(rx, rest, re.I)):
                if _billing_context(segment, m.start(), m.end()):
                    found.add(name)
                rest = rest[:m.start()] + ' ' * (m.end() - m.start()) + rest[m.end():]
    return found


def _descendants(node):
    ids = [node.get('id')]
    for ch in (node.get('children') or []):
        ids += _descendants(ch)
    return [i for i in ids if i]


def _find_node(node, target):
    if node.get('id') == target:
        return node
    for ch in (node.get('children') or []):
        got = _find_node(ch, target)
        if got:
            return got
    return None


def card_text(config, screen, element_id, locale=None):
    """A product card's own text plus every descendant's, joined.

    A card's price and period live in sibling `text` elements linked through
    `hierarchy`, not nested inside the product element's props.
    """
    els = (screen.get('elements') or {})
    emap, hier = els.get('map') or {}, els.get('hierarchy') or {}
    node = _find_node(hier, element_id)
    ids = _descendants(node) if node else [element_id]
    parts = []
    for eid in ids:
        e = emap.get(eid) or {}
        if e.get('type') != 'text':
            continue
        got = flat_text((e.get('props') or {}).get('content'), locale)
        if got:
            parts.append(got)
    return ' | '.join(parts)


def check_period_claim(config, catalog):
    """A finding is a card naming EXACTLY ONE period term that disagrees.

    A card naming both (`$6.67/MO` beside `12 mo • $79.99`) is the legitimate
    equivalent-price pattern -- 4 of 8 real cards -- so presence is not the test, arity
    is.
    """
    out = []
    if not catalog:
        return out
    by_id = {p['id']: p for p in catalog}
    dl = default_locale(config)
    for s in config.get('screens') or []:
        for eid, e in ((s.get('elements') or {}).get('map') or {}).items():
            pid = _element_product_id(e)
            if not pid or pid not in by_id:
                continue
            actual = by_id[pid].get('period')
            if not actual:
                continue
            claimed = period_terms(card_text(config, s, eid, dl))
            if len(claimed) == 1 and actual not in claimed:
                said = next(iter(claimed))
                out.append(finding(
                    'blocker', 'products', 'period-claim-mismatch',
                    f'This card says {said}, but "{by_id[pid].get("title") or pid}" is '
                    f'set up as {actual}, so buyers see the wrong billing period.',
                    f'Choose the {said} product for this card, or change the text to '
                    f'say {actual}.',
                    s['id'], eid))
    return out


# symbol+digits, or digits+ISO code
MONEY_RE = re.compile(r'(?:[$€£¥₹₽]\s?\d[\d.,]*)'
                      r'|(?:\d[\d.,]*\s?(?:USD|EUR|GBP|RUB|INR)\b)')
VAR_RE = re.compile(r'\b([0-9a-fA-F-]{36})\.([A-Za-z_]+)\b')


def _element_blobs(config, screen, element_id, locale):
    """Per-descendant-element text blobs, variable ids rendered inline.

    Returns `[(eid, blob), ...]` for every descendant `text` element with non-empty
    content -- one entry PER ELEMENT, not one joined string for the whole card. This
    is what lets `hardcoded-price` judge a literal against the specific element that
    carries it (see the scoping comment on `check_price_integrity`).

    A price element's entire content is a single `variable` node -- `flat_text`
    returns '' for it by design, which is exactly why `card_text` cannot be reused
    here. This walk renders the variable's id inline instead of dropping it, which is
    also why the id itself must never be fed into `period_terms`: a variable id looks
    like `<uuid>.prod_price_per_month`, and the word `month` in it is not a period
    claim written by a human.
    """
    els = (screen.get('elements') or {})
    emap, hier = els.get('map') or {}, els.get('hierarchy') or {}
    node = _find_node(hier, element_id)
    ids = _descendants(node) if node else [element_id]
    out = []
    for eid in ids:
        e = emap.get(eid) or {}
        if e.get('type') != 'text':
            continue
        cont = (e.get('props') or {}).get('content')
        val = cont
        if isinstance(cont, dict) and 'values' in cont:
            vals = cont['values'] or {}
            val = vals.get(locale) if locale in vals else next(iter(vals.values()), None)
        parts = []

        def walk(n):
            if isinstance(n, dict):
                if n.get('type') == 'text':
                    parts.append(n.get('text', ''))
                elif n.get('type') == 'variable':
                    parts.append(' ' + str((n.get('attrs') or {}).get('variableId', '')) + ' ')
                for x in (n.get('content') or []):
                    walk(x)
            elif isinstance(n, list):
                for x in n:
                    walk(x)
            elif isinstance(n, str):
                parts.append(n)
        walk(val)
        joined = ' '.join(''.join(parts).split())
        if joined:
            out.append((eid, joined))
    return out


def _card_blob(config, screen, element_id, locale):
    """Whole-card text with variable ids rendered inline, so `foreign-price-variable`
    reads one string. `foreign-price-variable` is deliberately CARD-scoped -- see the
    scoping comment on `check_price_integrity` for why it must stay that way while
    `hardcoded-price` (using `_element_blobs` instead) is element-scoped.
    """
    return ' | '.join(b for _, b in _element_blobs(config, screen, element_id, locale))


def check_price_integrity(config, catalog):
    """Two defects, and they are scoped DIFFERENTLY on purpose -- do not "fix" that.

    `foreign-price-variable`: a card whose ONLY price variable(s) name a DIFFERENT
    product than the one it is bound to. This one stays CARD-scoped, because its
    question is arity over the whole card -- the same logic already established for
    `period-claim-mismatch`: does the card reference its OWN product's price
    variable ANYWHERE among its elements. A card referencing a foreign price variable
    ALONGSIDE its own is the was/now comparison pattern, not a defect: measured on a
    real shipped card that sells its own product and additionally shows a
    struck-through rate from another plan for comparison, purchase binding correct
    throughout. Flagging that trains a user to ignore this whole finding family. Only
    a card with NO reference to its own product's price variable is actually showing
    the wrong price -- that is the real defect this check exists to catch, and it
    stays a blocker.

    `hardcoded-price`: a plain currency literal with no price variable backing it.
    This one is ELEMENT-scoped: it judges each currency literal against the specific
    element that carries it, never against the whole card. A card-scoped test asks
    "does this card use variables at all" when the question that matters is "is THIS
    literal backed by a variable" -- measured false negative: keep a real card's
    price variable, add a sibling text element reading "was $99.99", and the
    card-scoped version reported 0 findings while the fabricated price shipped. A
    real price variable on one element must never license a fabricated literal on a
    sibling. A zero literal ("$0 during trial") is legitimate copy and is excluded --
    only a NON-ZERO literal counts, at either scope.
    """
    out = []
    by_id = {p['id']: p for p in (catalog or [])}
    dl = default_locale(config)
    for s in config.get('screens') or []:
        for eid, e in ((s.get('elements') or {}).get('map') or {}).items():
            pid = _element_product_id(e)
            if not pid:
                continue

            # foreign-price-variable: card-scoped, arity over the whole card's blob.
            blob = _card_blob(config, s, eid, dl)
            refs = {m.group(1) for m in VAR_RE.finditer(blob)}
            foreign = refs - {pid}
            if foreign and pid not in refs:
                names = ', '.join((by_id.get(f, {}).get('title') or f) for f in sorted(foreign))
                out.append(finding(
                    'blocker', 'products', 'foreign-price-variable',
                    f'This card sells "{by_id.get(pid, {}).get("title") or pid}" but '
                    f'shows the price of {names}, so buyers see the wrong price.',
                    'Change the price on this card to the price of the product it sells.',
                    s['id'], eid))

            # hardcoded-price: element-scoped -- judge each descendant text element
            # against ITS OWN blob, not the card's. Anchored at the element that
            # actually carries the literal, not at the card's own element id.
            for lit_eid, elblob in _element_blobs(config, s, eid, dl):
                elrefs = {m.group(1) for m in VAR_RE.finditer(elblob)}
                money = [m.group(0) for m in MONEY_RE.finditer(elblob)]
                nonzero = [m for m in money if re.sub(r'[^\d]', '', m).strip('0')]
                if nonzero and not elrefs:
                    out.append(_tag(finding(
                        'blocker', 'products', 'hardcoded-price',
                        f'{nonzero[0]} is typed into the text here. If it is a price, '
                        f'it will not show in the buyer\'s currency and will not '
                        f'change when you change the price in the store.',
                        'If it is a price, replace it with the product\'s price. If '
                        'it is a savings figure, check that it still holds when '
                        'prices change.',
                        s['id'], lit_eid), _amount=nonzero[0]))
    return out


# --- STORE REVIEW (advisory). See `references/store-review.md` for the rejection
# notices these rest on. Every check below emits `risk` or `question`, NEVER `blocker`:
# store review is a human process that changes without announcement (the January 2026
# toggle wave arrived with no guideline edit and no grace period), so a checker can
# name a hazard and must not issue a verdict. `render()` prints these under their own
# heading with a fixed disclaimer, and they are excluded from the verdict counts.

# A weight is a name, not a number, and the two prominence checks need to order them.
# Ranks are ordinal only -- nothing reads the gaps.
WEIGHT_RANK = {'thin': 1, 'extralight': 2, 'ultralight': 2, 'light': 3, 'regular': 4,
               'normal': 4, 'medium': 5, 'semibold': 6, 'demibold': 6, 'bold': 7,
               'extrabold': 8, 'heavy': 8, 'black': 9}

# The price variable whose value IS the amount the store charges, per catalog `period`.
# `prod_price` is always the billed amount whatever the period. A period absent from
# this map (quarterly, lifetime, or anything added later) has no per-unit alias, so
# only `prod_price` counts for it -- which is correct, not a gap.
BILLED_SUFFIX = {'weekly': 'prod_price_per_week', 'monthly': 'prod_price_per_month',
                 'annual': 'prod_price_per_year'}


def is_billed_suffix(suffix, period):
    """True if this price variable renders the amount the user is actually charged."""
    return suffix == 'prod_price' or (bool(period) and suffix == BILLED_SUFFIX.get(period))


def resolve_font(config, element):
    """(size, weight rank) for a text element, resolving the theme typography preset.

    An element's own `font.size`/`font.weight` override the preset. A preset that names
    no size at all resolves to 0, which makes both prominence comparisons fall through
    rather than fire -- silence is the right direction of error for an advisory check
    reading a theme it does not fully understand.
    """
    presets = {t.get('id'): (t.get('settings') or {})
               for t in ((config.get('theme') or {}).get('typography') or [])}
    f = (element.get('props') or {}).get('font') or {}
    base = presets.get(f.get('preset')) or {}
    size = f.get('size') or base.get('size') or 0
    weight = f.get('weight') or base.get('weight') or 'regular'
    return size, WEIGHT_RANK.get(str(weight).lower(), 0)


def price_sites(config, screen, locale):
    """Every price variable drawn on this screen, with the type it is set in.

    Returns `[(element_id, product_id, suffix, size, weight_rank), ...]`.

    SCREEN-scoped, deliberately, where `check_price_integrity` is card-scoped. The
    June 2026 rejection is about what the user SEES -- a billed amount printed in the
    footnote under the CTA satisfies "clearly and conspicuously displayed" just as
    well as one printed inside the card, and a card-scoped walk would report that
    perfectly compliant layout as a defect.

    Reads `props.content` only. A price drawn from `propsByState.<state>.content` is
    invisible here: measured, `tabs-paywall.json` binds and prices its products in a
    shape this walk returns nothing for, so that flow gets no price findings rather
    than wrong ones. Silence, not a guess -- recorded in `store-review.md`.

    LATENT FONT MISATTRIBUTION, recorded rather than fixed because it is unreachable
    today: this filters to `type == 'text'` and then calls `_element_blobs`, which
    walks DESCENDANTS, while `resolve_font(config, e)` reads the font off the PARENT
    `e`. Across all 12 tracked and raw fixtures no text element is a descendant of
    another text element, so every blob's font really is its own element's -- checked,
    not assumed. If a nested text element ever appears, a price drawn by the child
    would be sized by the ancestor, and both prominence comparisons would read the
    wrong number. Resolve the font per blob element (the `eid` `_element_blobs`
    returns) if that day comes.
    """
    out = []
    emap = (screen.get('elements') or {}).get('map') or {}
    for eid, e in emap.items():
        if e.get('type') != 'text':
            continue
        for _, blob in _element_blobs(config, screen, eid, locale):
            size, rank = resolve_font(config, e)
            for m in VAR_RE.finditer(blob):
                suffix = m.group(2)
                if suffix.startswith('prod_price'):
                    out.append((eid, m.group(1), suffix, size, rank))
    return out


def check_price_prominence(config, catalog):
    """The June 2026 rejection, in two checks.

    Notice, verbatim: "The auto-renewable subscription displays the monthly calculated
    pricing for the subscription more clearly and conspicuously than the billed
    amount." The customer had to change every active paywall.

    `billed-amount-not-shown` is the hard case: a derived per-unit figure is drawn and
    the amount the store will actually charge appears NOWHERE on the screen.
    `derived-price-louder` is the soft one: both are drawn, and the derived figure wins
    on size or weight. Both are `risk`, because "conspicuously" is a judgement over
    colour, position and container as well as type, and this reads only type.

    Unknown period -> `question`. With no catalog row there is no `period`, so which
    suffix IS the billed amount is undecidable -- and guessing produced a measured
    false positive on `onboarding-quiz-paywall.json`, whose per-year + per-month pair
    is the COMPLIANT shape.

    But that question is SUPPRESSED whenever the missing catalog row is already
    reported: its entire content would be "I could not find that product in the
    catalog", which the report has said once already, and this check would repeat it
    once per (screen, product). Measured on `onboarding-quiz-paywall.json`: two
    `product-not-in-catalog` blockers plus two advisory questions saying the same
    thing; with `--catalog` omitted, one `catalog-not-fetched` question plus one
    advisory question per price site. This file establishes the pattern twice already
    -- `check_products_catalog` returns after a single `catalog-not-fetched`, and
    `check_period_claim` returns on a falsy catalog. The question survives only for
    the two cases nothing else covers, and they get DIFFERENT wording because a
    single sentence was wrong for one of them: a product that IS in the catalog whose
    row carries no `period`, and a product reached only through a price variable --
    absent from the catalog and bound nowhere, so `check_products_catalog` never saw
    it either, since that check walks `bound_products`.
    """
    out = []
    by_id = {p['id']: p for p in (catalog or [])}
    # None when there is no catalog at all (`catalog-not-fetched` covers the whole
    # flow with one question); otherwise every BOUND product missing from the catalog,
    # each of which is already a `product-not-in-catalog` blocker. A price variable
    # naming a product that is bound NOWHERE is in neither set, so it keeps its
    # question -- nothing else in the report mentions it.
    already_reported = (None if catalog is None
                        else {pid for _, _, pid in bound_products(config)
                              if pid not in by_id})
    dl = default_locale(config)
    for s in config.get('screens') or []:
        sites = price_sites(config, s, dl)
        if not sites:
            continue
        for pid in sorted({p for _, p, _, _, _ in sites}):
            rows = [r for r in sites if r[1] == pid]
            row = by_id.get(pid)
            period = (row or {}).get('period')
            title = (row or {}).get('title') or pid
            billed = [r for r in rows if is_billed_suffix(r[2], period)]
            derived = [r for r in rows if r[2].startswith('prod_price_per')
                       and not is_billed_suffix(r[2], period)]
            if not derived:
                continue
            if not billed:
                if period:
                    out.append(finding(
                        'risk', 'compliance', 'billed-amount-not-shown',
                        f'This screen shows "{title}" as a price per '
                        f'{derived[0][2].rsplit("_", 1)[-1]}, but not the amount the '
                        f'store actually charges. Apple has rejected paywalls for '
                        f'exactly this.',
                        f'Show the billed {period} amount too, at least as prominently. '
                        f'You can keep the calculated price: it shows the saving. '
                        f'(App Store 3.1.2(c), Google Play)',
                        s['id'], rows[0][0]))
                elif already_reported is None or pid in already_reported:
                    # Already reported, once, by `check_products_catalog` -- see the
                    # docstring. Silence here, not a second copy of that sentence.
                    pass
                elif row is None:
                    # No catalog row AND not a bound product, so `check_products_catalog`
                    # never saw it either -- that check walks `bound_products`, and this
                    # id reaches us only through a price variable. Nothing else in the
                    # report mentions it, so the question stays; but it must not claim a
                    # catalog entry that does not exist, which is what the single earlier
                    # wording did. `title` is the bare id here, by construction.
                    out.append(finding(
                        'question', 'compliance', 'billed-amount-not-shown',
                        f'This screen shows a calculated price for a product that is '
                        f'not in your product list and not sold anywhere in this flow '
                        f'({pid}), so I cannot tell whether the billed amount is shown.',
                        'Check that this price belongs to a product you actually sell: '
                        'an unknown product usually means it was left behind by an edit. '
                        'Then make sure the amount the store charges is on the screen. '
                        '(App Store 3.1.2, Google Play)',
                        s['id'], rows[0][0]))
                else:
                    out.append(finding(
                        'question', 'compliance', 'billed-amount-not-shown',
                        f'This screen shows a calculated price for "{title}", but the '
                        f'product has no billing period set, so I cannot tell whether '
                        f'the billed amount is shown.',
                        'Make sure the amount the store actually charges is on this '
                        'screen, not only a calculated per-month price. '
                        '(App Store 3.1.2, Google Play)',
                        s['id'], rows[0][0]))
                continue
            bmax = max((r[3], r[4]) for r in billed)
            dmax = max((r[3], r[4]) for r in derived)
            if dmax > bmax:
                # Name the dimension that actually differs. `dmax > bmax` compares
                # (size, weight rank) TUPLES, so weight only breaks a tie on equal
                # size -- and the earlier single wording ("set larger or heavier
                # (13pt) than the billed amount (13pt)") printed the same number
                # twice and never mentioned weight on exactly that path. The weight
                # NAME is not recoverable here: `WEIGHT_RANK` is many-to-one
                # (regular/normal both rank 4), so the size-equal branch names the
                # dimension and leaves the value to the config.
                if dmax[0] > bmax[0]:
                    louder = (f'is bigger than the billed amount '
                              f'({dmax[0]} pt against {bmax[0]} pt)')
                else:
                    louder = (f'is bolder than the billed amount, '
                              f'both at {dmax[0]} pt')
                out.append(finding(
                    'risk', 'compliance', 'derived-price-louder',
                    f'The calculated price for "{title}" {louder}. Apple wants the '
                    f'billed amount to be the more prominent of the two, and has '
                    f'rejected paywalls over it.',
                    'Make the billed amount bigger or bolder than the calculated one, '
                    'for example billed amount bold at 14 pt and the per-month price at '
                    '12 pt. (App Store 3.1.2(c), Google Play)',
                    s['id'], derived[0][0]))
    return out


def _switch_shaped(props):
    """A pill: a fixed box wider than tall, fully rounded on all four corners.

    Measured against the corpus: exactly ONE element in 12 real exports matches --
    a 50x30 stack on `onboarding-multilocale.json`'s `scr_notify`, which is a
    notifications opt-in. So shape alone is nearly specific enough and is still not
    used alone; see `check_trial_toggle` for the second and third signals.

    Shape only -- deliberately blind to `propsByState`. A pill can also be a static
    "3-day trial" badge chip on a plan card, which is the check's own recommended fix;
    `check_trial_toggle` requires the state-dependence separately, on the same element,
    so a badge (shape but no `propsByState.selected`) never reaches this function's
    caller alone.
    """
    w, h = (props.get('width') or {}), (props.get('height') or {})
    if w.get('type') != 'fixed' or h.get('type') != 'fixed':
        return False
    width, height = w.get('value') or 0, h.get('value') or 0
    if not (width > height > 0):
        return False
    br = props.get('borderRadius') or {}
    return all((br.get(k) or 0) >= height / 2 for k in ('tl', 'tr', 'bl', 'br'))


def check_trial_toggle(config, stores):
    """Apple began rejecting the free-trial on/off switch in January 2026 under App
    Store 3.1.2.

    No guideline edit, no documentation change, no grace period -- apps just started
    coming back rejected. Adapty warned roughly twenty customer teams on 2026-02-11 and
    several replied that it had already happened to them. The objection: the trial's
    terms are not visible unless the user touches the switch, so a user who never
    touches it is never shown them.

    iOS only -- Android and web implementations were unaffected -- so an app that does
    not ship on iOS gets nothing. Unknown stores still print, worded as iOS.

    THREE signals, all required, because any pair alone false-fires. Shape alone hits
    the corpus's one notifications toggle; trial copy alone hits every paywall that
    mentions a trial, which is most of them; shape-plus-copy alone also hits a static
    "3-day trial" badge chip on a plan card -- the check's own recommended remediation
    -- because a badge can be pill-shaped and say "trial" without being a switch. The
    third signal, state-dependence (`propsByState.selected` on the SAME pill-shaped
    element), is what a switch has and a badge does not: the catalog's own
    `trial-toggle` template's pill child moves its knob (`layout.alignH`) between
    states, while a static badge carries no `propsByState` at all.
    """
    if stores is not None and 'ios' not in stores:
        return []
    out = []
    dl = default_locale(config)
    selling = selling_screens(config)
    for s in config.get('screens') or []:
        if s['id'] not in selling:
            continue
        els = s.get('elements') or {}
        emap, hier = els.get('map') or {}, els.get('hierarchy') or {}
        for eid, e in emap.items():
            if not (e.get('props') or {}).get('groupId'):
                continue
            node = _find_node(hier, eid)
            kids = _descendants(node) if node else [eid]
            if not any(_switch_shaped((emap.get(k) or {}).get('props') or {})
                       and ((emap.get(k) or {}).get('propsByState') or {}).get('selected')
                       for k in kids):
                continue
            copytext = ' '.join(flat_text(((emap.get(k) or {}).get('props') or {})
                                          .get('content'), dl) for k in kids)
            if not TRIAL_RE.search(copytext):
                continue
            out.append(finding(
                'risk', 'compliance', 'trial-toggle',
                'This looks like a free-trial switch: the user has to flip it to see the '
                'trial. Apple has been rejecting this pattern, with no warning.',
                'Show the trial without a tap: two plans side by side with the trial on '
                'one of them, or a timeline that says when the first charge happens. If '
                'you keep the switch, expect questions at iOS review. (App Store 3.1.2)',
                s['id'], eid))
    return out


def check_disclosure(config, catalog):
    """The Schedule 2 disclosure floor, on the screen itself.

    Apple's App Store 3.1.2 rejection boilerplate, as reviewers send it: "Apps offering
    auto-renewable subscriptions must include all of the following required information
    in the binary: Title of auto-renewing subscription; Length of subscription; Price of
    subscription, and price per unit if appropriate; Functional links to the privacy
    policy and Terms of Use (EULA)." Terms and privacy are already covered by
    `no-terms-link`/`no-privacy-link`. This function covers the other two: LENGTH
    (`no-period-disclosed`) and what happens when a free trial ends
    (`trial-terms-incomplete`).

    Screen-scoped and reported ONCE per screen. The period may legitimately be stated
    outside the card -- "Billed yearly" under the CTA discloses it for every card above
    -- so a card-scoped test would flag a compliant layout, and one row per card would
    bury four identical findings in the report.

    Reuses `period_terms`, so it inherits that function's billing-context guard, which
    took four measured false positives to get right ("Weekly progress reports" read as a
    weekly billing claim). Inverted here for `no-period-disclosed`: the check is that NO
    period term appears anywhere on the screen.

    Both checks read the same per-screen `blob`, so a screen with neither a stated
    period nor stated trial terms produces both findings -- deliberately: they are two
    separate disclosures and a user reading the report should see both gaps, not just
    whichever the code happened to check first.
    """
    out = []
    dl = default_locale(config)
    selling = selling_screens(config)
    lifetime_only = {p['id'] for p in (catalog or [])
                     if p.get('period') in ('lifetime', None)}
    for s in config.get('screens') or []:
        if s['id'] not in selling:
            continue
        bound = {pid for sid, _, pid in bound_products(config) if sid == s['id']}
        # A screen selling only one-time purchases has no billing period to disclose.
        if bound and bound <= lifetime_only:
            continue
        emap = (s.get('elements') or {}).get('map') or {}
        blob = ' | '.join(
            flat_text((e.get('props') or {}).get('content'), dl)
            for e in emap.values() if e.get('type') == 'text')
        if not period_terms(blob):
            out.append(finding(
                # Says only what the check knows: no period term appears in this
                # screen's copy. It must NOT assert that a price is shown -- the one
                # real export this fires on, `tests/fixtures/tabs-paywall.json`, has
                # ZERO price variables in the whole document (recorded in
                # `store-review.md`), so the earlier wording ("a user sees a price
                # and a button") asserted a fact its only real firing case
                # contradicts, and its fix pointed at a price that is not there.
                'risk', 'compliance', 'no-period-disclosed',
                'This screen asks people to subscribe but never says how often they '
                'will be billed.',
                'Add the billing period to the text: "Billed yearly" under the button, '
                'or "/year" next to the price. '
                '(App Store 3.1.2, Google Play)',
                s['id']))

        # trial-terms-incomplete. Google Play, verbatim: developers must "clearly and
        # accurately describe the terms of your offer, including the duration, pricing,
        # and description of accessible content or services" and explain "the paid
        # subscription cost after the offer ends". Apple rejects the same omission under
        # App Store 3.1.2. The test is narrow on purpose: the copy PROMISES a trial and the screen
        # says nothing anywhere about a charge following it. THREE satisfiers -- a
        # currency amount, a billing verb, or a period term -- a deliberately generous
        # bar, because this check reads copy and copy is where false positives are
        # cheapest to create and most expensive to keep.
        #
        # A fourth, `VAR_RE.search(blob)` (a price VARIABLE), was here and was DEAD
        # CODE: `blob` comes from `flat_text`, which renders a variable node as '' by
        # design (see its docstring), so no variable id ever reaches this string and
        # the branch could not match. Removing it reddened nothing. Do not re-add it --
        # this file's own history is full of assertions that shipped unable to fail,
        # and a satisfier that cannot fire is a fourth one only on paper. If a
        # variable-backed price should count here, `after` has to read
        # `_element_blobs`, which renders variable ids inline, not `flat_text`.
        if not TRIAL_RE.search(blob):
            continue
        after = (MONEY_RE.search(blob)
                 or BILLING_VERB_RE.search(blob) or period_terms(blob))
        if after:
            continue
        out.append(finding(
            'risk', 'compliance', 'trial-terms-incomplete',
            'This screen offers a free trial but does not say what happens when it '
            'ends: no price, no billing period, nothing about renewal.',
            'Say what the trial turns into, next to the offer: "Free for 7 days, '
            'then $79.99/year". (App Store 3.1.2, '
            'Google Play)',
            s['id']))
    return out


# A url that looks like it takes the user somewhere to pay. Matched as exact tokens,
# never substrings -- `_url_tokens`' own docstring records why ('tos' matches inside
# 'photos'). `subscribe` is deliberately absent: a marketing page at /subscribe is an
# ordinary content-gating link, not evidence of a purchase flow, so including it would
# manufacture a question on almost every subscription app's marketing site.
#
# The vocabulary names a PAYMENT MECHANISM, never a PRODUCT SURFACE -- that line is
# what keeps this list from regrowing the words dropped below. `billing`, `upgrade`
# and `paywall` were all tried and dropped on real-world false positives: `billing`
# fires on `/support/billing`, `/account/billing-history`, `/help/manage-billing` --
# and `billing` is the decisive case, because Google Play *requires* an accessible
# subscription-management path, plausibly living at exactly that kind of url, so the
# token would fire on a link another store demands the app carry. `upgrade` fires on
# `/why-upgrade`, `/upgrade-info`, `/compare-plans-upgrade`; `paywall` fires on an
# attribution deep link routing back into the app's OWN paywall
# (`yourapp.onelink.me/xyz?af_dp=yourapp://paywall`). All three name an in-app surface
# or a management/marketing path, never a payment mechanism. `paddle` stays despite its
# own narrow false positive (`/blog/paddle-boarding-tips`) because, unlike the three
# dropped words, it names a real web-checkout processor and nothing else plausible
# collides with it as often.
PURCHASE_URL_WORDS = ('checkout', 'pay', 'payment', 'stripe', 'paddle',
                      'purchase', 'buy')


def _screen_openurls(screen, locale):
    """Every openUrl target on this one screen, flattened to plain text.

    KNOWN DUPLICATION, recorded on purpose rather than refactored: this is
    `openurl_urls`'s body with the scope narrowed from the whole flow to one screen,
    and the two were deliberately left as twins. `openurl_urls` feeds two shipped
    BLOCKERS (`no-terms-link`, `no-privacy-link`); this feeds one advisory question
    (`external-purchase-link`). Unifying them would put a live blocker's url handling
    at risk to save twelve lines. **A future fix to how urls are read must land in
    BOTH functions** -- that is the whole reason this note exists, because a fix
    applied to one twin and not the other is exactly the kind of defect that gets
    rediscovered as a bug months later.
    """
    out = []
    for eid, e in ((screen.get('elements') or {}).get('map') or {}).items():
        for _, a in actions_of(e):
            if a.get('type') != 'openUrl':
                continue
            url = (a.get('payload') or {}).get('url')
            text = url if isinstance(url, str) else flat_text(url, locale)
            if text:
                out.append(text)
    return out


def check_external_purchase(config, stores):
    """App Store 3.1.1: an app may not steer users to a purchase mechanism other than
    in-app purchase, except on the US storefront or under an entitlement.

    A `question`, and it stays one however suspicious the url looks. The audit cannot
    see which storefronts the app ships to, and cannot know whether the developer holds
    the External Link Account Entitlement -- both of which make the same link legal. It
    is worth asking anyway because Adapty ships web paywalls, so this is a real
    foot-gun rather than a hypothetical.
    """
    if stores is not None and 'ios' not in stores:
        return []
    out = []
    dl = default_locale(config)
    selling = selling_screens(config)
    for s in config.get('screens') or []:
        if s['id'] not in selling:
            continue
        hits = [u for u in _screen_openurls(s, dl)
                if set(PURCHASE_URL_WORDS) & _url_tokens(u)]
        if not hits:
            continue
        out.append(finding(
            'question', 'compliance', 'external-purchase-link',
            'This screen links to what looks like a payment page: '
            + ', '.join(sorted(set(hits)))
            + '. Outside the US, Apple does not allow sending users to pay outside '
            'the app.',
            'If it is a payment page and you sell outside the US, remove it: this is a '
            'reliable rejection. If it is a help page, or you sell only in the US, you '
            'are fine. (App Store 3.1.1)',
            s['id']))
    return out


# A localizable field carrying only a `variable`/`token`/`image` node has no literal
# text by construction -- a price element's whole content IS a `variable` node. A
# literal-text-only presence test reports every price on every paywall as empty, which
# is the exact bug that made an earlier version of `check_localization` miss its own
# injected defect. An empty `text` node is deliberately NOT in this list: a paragraph
# containing `{'type': 'text', 'text': ''}` carries no content at all and must still
# count as empty.
SUBSTANTIVE_NODES = ('variable', 'token', 'image')


def _localizable_values(config, locales):
    """Every localizable `values` map keyed by at least one declared locale."""
    found = []

    def walk(o):
        if isinstance(o, dict):
            vals = o.get('values')
            if isinstance(vals, dict) and set(vals) & set(locales):
                found.append(vals)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(config)
    return found


def _has_content(value, locale):
    """A value counts as present if it carries literal text OR a variable/token/image
    node. See `SUBSTANTIVE_NODES` above for why -- get this wrong and the check is
    worthless, because it either misses a truly empty translation or flags every price.

    A per-locale IMAGE ELEMENT value is a second trap of the exact same shape, and it
    was measured firing an `empty-translation` false positive on two real, working
    fixtures (`onboarding-quiz-paywall.json`, `vpn-timer-draft.json`) before this
    clause existed: the value there is a bare `{'id': ..., 'url': ...}` object with
    NO `type` discriminator at all (`verify-config.py`'s own image check reads the
    same shape), so `node_kinds`/`flat_text` -- which only understand richtext-shaped
    nodes (`type` + `content`) -- see nothing and call it empty. A truthy `url` is
    the signal; an unfilled slot is `{}` and stays correctly empty.

    A CONDITIONAL-TEXT `switch` is the third trap of the same shape, and it was measured
    firing an `empty-translation` BLOCKER on three legitimate, service-approved fields in
    a real onboarding flow: the per-locale value there is not a block array
    at all but `{'type': 'switch', 'cases': [[cond, const], ...], 'default': const}`, so
    `flat_text`/`node_kinds` see nothing and call it empty. This is the copy a
    personalization payoff is made of -- the highest-value pattern `onboarding-teardown`
    recommends -- so the false positive landed a blocker on exactly the screen the sibling
    skill exists to produce. The branches are recursed rather than the type merely
    accepted, so an all-empty switch still counts as empty.

    KNOWN LIMITATION, deliberately not fixed here: `flat_text` still returns '' for a
    switch, so a conditional field is invisible to the `same`-as-base parity count and to
    every other check that reads visible text. Widening `flat_text` reaches the price and
    store-review checks, which are calibrated against measured false positives, so it
    needs its own calibration rather than a ride on this one.
    """
    if flat_text(value, locale):
        return True
    if any(k in SUBSTANTIVE_NODES for k in node_kinds(value, locale)):
        return True
    if isinstance(value, dict) and value.get('type') == 'switch':
        branches = [c[1] for c in (value.get('cases') or [])
                    if isinstance(c, (list, tuple)) and len(c) == 2]
        if 'default' in value:
            branches.append(value['default'])
        return any(_has_content(b.get('value'), locale)
                   for b in branches if isinstance(b, dict))
    return isinstance(value, dict) and bool(value.get('url'))


def _is_media_field(vals, base):
    """True when this localizable holds an image or video: `{id, url, previewValue?}` or
    `{videoUrl, ...}`, read off the default locale's value (or any value, if it has none)."""
    v = vals.get(base) if base in vals else next(iter(vals.values()), None)
    return isinstance(v, dict) and any(
        isinstance(v.get(k), str) and v[k].strip() for k in ('url', 'videoUrl'))


def _is_empty_value(v):
    """The catalog's emptiness rule, for either value family: text or media."""
    if isinstance(v, dict) and v.get('type') != 'switch' and ('url' in v or 'videoUrl' in v):
        return _loc.is_empty('image' if 'url' in v else 'video', v)
    return _loc.is_empty('rich-text', v)


def locale_coverage(config):
    """Per-locale coverage stats and examples, over every localizable value in the flow.

    `stat[code]` is `{'missing', 'empty', 'same'}` int counts, keyed by locale ID:
    `missing` is the field has no value for this locale, or an empty one -- both fall back
    to the default locale's text; `empty` is a value that is NOT empty by the catalog's rule
    and still shows nothing (whitespace only), so the field is blank there; `same`
    is the value is identical to the base locale's text (a proper noun, or a missed
    translation -- `check_localization` cannot tell which, so it is a risk, not a
    blocker). `examples[code]` holds up to 4 sample base-locale strings behind a
    `same` hit, for the report to show.
    """
    locales = locale_ids(config)
    base = default_locale(config)
    stat = {l: {'missing': 0, 'empty': 0, 'same': 0} for l in locales}
    examples = {l: [] for l in locales}
    for vals in _localizable_values(config, locales):
        base_text = flat_text(vals.get(base), base) if base in vals else ''
        media = _is_media_field(vals, base)
        for code in locales:
            # An EMPTY value ('' , [], an emptied paragraph) is the same as no value: both
            # fall back to the default locale's text. So both count as missing, never as a
            # blank field.
            if code not in vals or _is_empty_value(vals[code]):
                # A locale with no media entry shows the default locale's file (the SDK
                # resolves a locale's assets on top of the default's), so it is not missing --
                # and counting it would push a copy of the default's image, preview and all,
                # into every locale.
                if not media:
                    stat[code]['missing'] += 1
                continue
            if not _has_content(vals[code], code):
                stat[code]['empty'] += 1
                continue
            if code != base and base_text and flat_text(vals[code], code) == base_text \
                    and len(base_text) > 3:
                stat[code]['same'] += 1
                if len(examples[code]) < 4:
                    examples[code].append(base_text[:40])
    return stat, examples


def check_localization(config):
    """`empty-translation` and `locale-entirely-empty` are blockers -- a user in that
    locale sees a blank field, or a whole language that was declared and never filled.
    `untranslated` is different in kind, not just severity: matching the base locale is
    not itself wrong (a brand name is SUPPOSED to be identical everywhere), so it can
    only ever be a risk, and it is reported ONCE for the whole flow rather than once
    per locale.

    That last point is a deliberate departure from the plan this check was written
    from: appending one `untranslated` finding per locale double-counts a value that
    is identical across every non-base locale (this fixture's two brand-name hits are
    identical in BOTH `sr` and `sr-Latn`), and the coverage table already carries the
    per-locale breakdown -- a second, per-locale finding would just restate it.
    """
    out = []
    locales = locale_ids(config)
    if not locales:
        return out
    base = default_locale(config)
    # The builder shows a language by its name ("Serbian (Latin)"), not its code.
    name = locale_names(config)
    nm = lambda c: name.get(c) or c
    stat, examples = locale_coverage(config)
    total = sum(1 for vals in _localizable_values(config, locales)
                if not _is_media_field(vals, base))

    for code in locales:
        s = stat[code]
        if s['empty']:
            out.append(finding(
                'blocker', 'localization', 'empty-translation',
                f'{s["empty"]} text field(s) are empty in {nm(code)}, so those parts of '
                f'the screen show nothing in {nm(code)}.',
                f'Fill in the {nm(code)} text, or remove {nm(code)} from the flow\'s '
                f'languages.'))
        if total and 0 < s['missing'] < total and code != base:
            # Missing, not empty: the language has no key at all for these fields. One
            # translated field used to be enough to keep a nearly untranslated language
            # out of the report -- measured on a real flow listing Russian with 80 of
            # its 81 text fields missing, which printed only a table row.
            out.append(finding(
                'blocker', 'localization', 'missing-translation',
                f'{nm(code)} is listed as a language, but {s["missing"]} of {total} text '
                f'fields have no {nm(code)} text yet.',
                f'Translate the remaining text into {nm(code)}, or remove {nm(code)} from '
                f'the flow\'s languages.'))
        if total and s['missing'] == total and code != base:
            out.append(finding(
                'blocker', 'localization', 'locale-entirely-empty',
                f'{nm(code)} is listed as a language but has no text anywhere in the flow.',
                f'Translate the flow into {nm(code)}, or remove it from the languages.'))

    # Grouped, once for the whole flow -- see the docstring above for why.
    hit_locales = [code for code in locales if code != base and stat[code]['same']]
    if hit_locales:
        seen = []
        for code in hit_locales:
            for ex in examples[code]:
                if ex not in seen:
                    seen.append(ex)
        counts = ', '.join(f'{nm(code)}: {stat[code]["same"]}' for code in hit_locales)
        shown = ', '.join(f'"{x}"' for x in seen[:4])
        out.append(finding(
            'risk', 'localization', 'untranslated',
            f'Some text is the same as in {nm(base)} ({counts}), for example {shown}. '
            f'That is expected for brand and product names; the rest may be a missed '
            f'translation.',
            'Translate anything in that list that is not a name.'))
    return out


# Anchored or multi-word on purpose. A bare word list flags real copy: "Sample a new
# workout every week" is a legitimate headline, so `sample` alone cannot be a signal.
PLACEHOLDER_RE = re.compile(
    r'lorem ipsum'
    r'|\byour (?:text|headline|title|copy|value) here\b'
    r'|^(?:text|title|subtitle|button|label|heading|placeholder)$'
    r'|\bTODO\b|\bTBD\b|\bFIXME\b'
    r'|\bplaceholder text\b', re.I)


def check_placeholders(config):
    out = []
    dl = default_locale(config)
    for s, eid, e in elements(config):
        txt = flat_text((e.get('props') or {}).get('content'), dl)
        if txt and PLACEHOLDER_RE.search(txt.strip()):
            out.append(finding(
                'risk', 'placeholders', 'placeholder-copy',
                f'This looks like unfinished text: "{txt[:60]}"',
                'Replace it with the real text.', s['id'], eid))
    return out


def _variable_refs(config):
    """Every `variableId` value referenced anywhere in the config as a real
    consumption site -- a `var` predicate operand (`{'type': 'var', 'variableId':
    ...}`), a `purchase` action's dynamic product, or a rich-text `variable` node's
    `attrs`. Walked structurally over the parsed document rather than over a
    serialized blob: a substring scan also matches a vid that happens to be a
    substring of an unrelated string, and undercounts nothing here since every
    consumption site puts the id under a `variableId` key.

    Skips a `setVariable` action node entirely (not just its `payload`), so the
    assignment that PRODUCES a variable is never mistaken for a site that READS one
    -- whether that action names its own target under `payload.id` or
    `payload.variableId`.
    """
    refs = set()

    def walk(n):
        if isinstance(n, dict):
            if n.get('type') == 'setVariable':
                return
            vid = n.get('variableId')
            if isinstance(vid, str):
                refs.add(vid)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(config)
    return refs


def check_variables(config):
    """A producer nobody consumes. `verify-config.py` already owns the reverse (a
    consumer with no producer), so only this direction is checked here.

    Scoped to explicit `setVariable` actions only -- deliberately narrower than an
    earlier draft, which also treated any element's `groupId` as a producer of
    `<groupId>.selectedOptionId`. That fired on every real, shipped fixture that
    has a group, and the reason is that the variable a group implies is not
    decidable from the config alone: a product group's is
    `<groupId>.selectedProduct` (`onboarding-quiz-paywall.json`'s `products` group,
    `comparison-paywall.json`'s), a `tab-item` group exposes no readable variable
    at all (`tabs-paywall.json`'s three-member `tabs` group switches visible
    content natively), and a single `selectable` sharing a `groupId` with no other
    member is a plain toggle, not a choice with a reader to find
    (`onboarding-multilocale.json`'s one-member `notify` group). Three different
    real shapes, all of them fine, and no rule short of a fixture-specific
    exception separated them -- so this check stays on the one producer kind the
    config states unambiguously.
    """
    out = []
    produced = {}
    for s, eid, e in elements(config):
        for _, a in actions_of(e):
            if a.get('type') == 'setVariable':
                payload = a.get('payload') or {}
                vid = payload.get('id') or payload.get('variableId')
                if vid:
                    produced.setdefault(vid, (s['id'], eid))
    if not produced:
        return out
    refs = _variable_refs(config)
    for vid, (sid, eid) in produced.items():
        if vid not in refs:
            out.append(finding(
                'risk', 'variables', 'variable-no-consumer',
                f'The variable "{vid}" is set but never used anywhere in the flow.',
                'Use it in a condition or a text field, or remove the "Set Variable" '
                'action that sets it.', sid, eid))
    return out


# --- the FAKE CAROUSEL. A swipeable row of cards with indicator dots is the `carousel`
# element, which is swipeable and draws its OWN dots from `props.dots`. Hand-built as a
# static card plus a row of decorative dot `stack`s it screenshots identically and is
# inert on the device: one frozen slide, no swipe, dots that never move. Nothing else in
# this audit sees it -- it publishes, it renders, and every other gate passes it.
#
# Ported from `flow-generator`'s `verify-config.py` after a user reported the fake
# shipping despite the guidance, and calibrated the same way: the seven fake shapes
# rebuilt from a real carousel export must all be caught, and all 12 real configs in the
# corpus must stay clean. Severity is `risk`, not `blocker` -- the flow sells and
# publishes fine, so this is a quality defect shown to paying users rather than a reason
# to hold the release.
DOT_GLYPHS = set('•‣●○▪▫⚫⚪·∙‧・')
DOT_ICON_NAMES = {'circle', 'dot', 'dotoutline'}
VIEWPORT_PT = 430          # the widest common device; a fixed row past this overflows everywhere


def _fixed(props, axis):
    v = (props.get(axis) or {})
    return v.get('value') if v.get('type') == 'fixed' else None


def _dot_stack(e):
    """A leaf stack small and round enough to be an indicator dot.

    Height anchors the test and width may run to 3x it, because the ACTIVE dot is very
    often a pill. Requiring width == height is what let the reported shape through.
    """
    if e.get('type') != 'stack':
        return False
    pr = e.get('props') or {}
    w, h = _fixed(pr, 'width'), _fixed(pr, 'height')
    if not isinstance(w, (int, float)) or not isinstance(h, (int, float)):
        return False
    return h <= 14 and w <= max(3 * h, 12) and bool(pr.get('borderRadius'))


def _dot_icon(e):
    if e.get('type') != 'icon':
        return False
    ic = (e.get('props') or {}).get('icon') or {}
    return str(ic.get('name', '')).lower() in DOT_ICON_NAMES and (ic.get('size') or 0) <= 16


def _dot_text(e, locale=None):
    """A text node whose visible characters are only bullet glyphs -- `● ○ ○`."""
    if e.get('type') != 'text':
        return False
    txt = flat_text((e.get('props') or {}).get('content'), locale) or ''
    visible = [c for c in txt if not c.isspace()]
    return len(visible) >= 3 and all(c in DOT_GLYPHS for c in visible)


def _row_marker(node, m):
    """(length, index) for an indicator row: how many markers it has and which one is the
    odd one out -- the ACTIVE marker, drawn wider or in another colour. None when no
    single marker stands out."""
    kids = [c.get('id') for c in node.get('children') or []]
    sig = [(json.dumps(((m.get(k) or {}).get('props') or {}).get('width'), sort_keys=True),
            json.dumps(((m.get(k) or {}).get('props') or {}).get('fill'), sort_keys=True))
           for k in kids]
    odd = [i for i, x in enumerate(sig) if sig.count(x) == 1]
    return (len(kids), odd[0] if len(odd) == 1 else None)


def _step_indicator_rows(config):
    """Node ids of dot rows that are a STEP INDICATOR, not a fake slider.

    A fake slider is one frozen screen. A step indicator is the same row repeated on
    several screens with the active marker in a different place on each -- "step 1 of
    3", "step 2 of 3". Both signals are required: a fake slider copied unchanged onto
    two screens keeps its active marker in one place and still fires. Measured on
    Lingua Pro, whose "Progress dots" (three pills, the wide one moving 1 -> 2 -> 3
    across Welcome, Goal and Pace) fired three times as a fake carousel.
    """
    rows = {}
    for s in config.get('screens') or []:
        m = (s.get('elements') or {}).get('map') or {}

        def walk(node):
            kids = node.get('children') or []
            if len(kids) >= 2 and all(not c.get('children') for c in kids):
                length, odd = _row_marker(node, m)
                if odd is not None:
                    rows.setdefault(length, []).append((s.get('id'), node.get('id'), odd))
            for c in kids:
                walk(c)
        walk((s.get('elements') or {}).get('hierarchy') or {})
    step = set()
    for length, found in rows.items():
        screens = {sid for sid, _, _ in found}
        if len(screens) >= 2 and len({odd for _, _, odd in found}) >= 2:
            step.update(nid for _, nid, _ in found)
    return step


def check_fake_carousel(config):
    out = []
    dl = default_locale(config)
    step_rows = _step_indicator_rows(config)
    for s in config.get('screens') or []:
        m = ((s.get('elements') or {}).get('map') or {})
        if any(e.get('type') == 'carousel' for e in m.values()):
            continue
        hierarchy = (s.get('elements') or {}).get('hierarchy') or {}

        def walk(node):
            kids = node.get('children') or []
            leaves = [(c.get('id'), m.get(c.get('id'), {}))
                      for c in kids if not c.get('children')]
            dots = sorted(i for i, e in leaves if _dot_stack(e) or _dot_icon(e)
                          or _dot_text(e, dl))
            # A single text node of bullet glyphs IS the whole indicator row, so it
            # counts alone; two is the floor otherwise, because a two-slide carousel
            # gets exactly two dots.
            if node.get('id') in step_rows:
                pass
            elif len(dots) >= 2 or any(_dot_text(e, dl) for _, e in leaves):
                out.append(finding(
                    'risk', 'placeholders', 'fake-carousel',
                    f'This looks like a slider but is not one: {len(dots)} dots drawn by '
                    f'hand under a single card. Users see one slide that does not swipe, '
                    f'and the dots never move.',
                    'Replace it with a Carousel element and delete the dots: a Carousel '
                    'swipes and draws its own dots.',
                    s.get('id'), dots[0] if dots else None))
            parent = m.get(node.get('id'), {})
            # `props.layout` is a bare STRING ('auto-height') on a text element, so it
            # cannot be assumed to be an object.
            lay = (parent.get('props') or {}).get('layout')
            lay = lay if isinstance(lay, dict) else {}
            if lay.get('direction') == 'horizontal':
                widths = [_fixed(m.get(c.get('id'), {}).get('props') or {}, 'width')
                          for c in kids
                          if m.get(c.get('id'), {}).get('type') == 'stack']
                widths = [w for w in widths if isinstance(w, (int, float))]
                dist = lay.get('distribution')
                gap = (dist.get('gap') if isinstance(dist, dict) else lay.get('gap')) or 0
                if (len(widths) >= 2 and len(set(widths)) == 1
                        and sum(widths) + gap * (len(widths) - 1) > VIEWPORT_PT):
                    out.append(finding(
                        'risk', 'placeholders', 'fake-carousel',
                        f'{len(widths)} cards in a row ({widths[0]} pt each) are wider than '
                        f'the screen, and there is no Carousel, so the cards past the edge are '
                        f'cut off instead of scrolling.',
                        'Put the cards in a Carousel element so they scroll.',
                        s.get('id'), node.get('id')))
            for c in kids:
                walk(c)

        walk(hierarchy)
    return out


def _norm(text):
    return re.sub(r'[^a-z0-9]', '', (text or '').lower())


def _branches(config):
    """Every conditional that routes on a single-choice answer: yields
    (screen, group id, [(answer ids, target screen ids)], default target screen ids)."""
    order = [s['id'] for s in config.get('screens') or []]
    for s, eid, e in elements(config):
        stack = [a for _, a in actions_of(e)]
        while stack:
            a = stack.pop()
            if not isinstance(a, dict):
                continue
            if a.get('type') != 'conditional':
                continue
            pl = a.get('payload') or {}
            cases, group = [], None
            for case in pl.get('cases') or []:
                if not (isinstance(case, list) and len(case) == 2):
                    continue
                cond, then = case
                preds = (cond.get('predicates') if isinstance(cond, dict)
                         and cond.get('type') in ('&&', '||') else [cond])
                vals = []
                for pd in preds or []:
                    left = (pd or {}).get('left') or {}
                    right = (pd or {}).get('right') or {}
                    vid = left.get('variableId') or ''
                    if (pd.get('type') == '==' and vid.endswith('.selectedOptionId')
                            and right.get('type') == 'const'
                            and isinstance(right.get('value'), str)):
                        group = vid.split('.')[0]
                        vals.append(right['value'])
                if vals:
                    cases.append((vals, _nav_targets(then, s['id'], order)))
            if group and cases:
                yield (s, group, cases,
                       _nav_targets(pl.get('default'), s['id'], order))


def _answers(config, group):
    """customId -> the answer's visible text, for one selectable group."""
    dl = default_locale(config)
    out = {}
    for s in config.get('screens') or []:
        m = (s.get('elements') or {}).get('map') or {}
        pm_children = {}

        def index(n):
            pm_children[n.get('id')] = [c.get('id') for c in n.get('children') or []]
            for c in n.get('children') or []:
                index(c)
        index((s.get('elements') or {}).get('hierarchy') or {})

        def text_of(eid):
            t = flat_text(((m.get(eid) or {}).get('props') or {}).get('content'), dl)
            return ' '.join(x for x in [t] + [text_of(c) for c in pm_children.get(eid, [])]
                            if x).strip()
        n = 0
        for eid, e in m.items():
            pr = e.get('props') or {}
            if pr.get('groupId') == group and e.get('type') == 'selectable':
                # The element that CARRIES the branch on this group is its submit
                # button, not an answer -- the builder makes the quiz's Next button a
                # group member (caption "Button" in the quiz fixture). Counting it as an
                # answer invented a "Next" answer that falls through to a named screen.
                if f'{group}.selectedOptionId' in json.dumps(e.get('interactions') or []):
                    continue
                n += 1
                cid = pr.get('customId')
                if isinstance(cid, str) and cid.strip():
                    out[cid] = text_of(eid) or cid
                else:
                    # An answer with no ID can never be named in a branch, so it always
                    # takes the "otherwise" path -- exactly the answer this check must
                    # see. Keyed so it can never collide with a real ID.
                    ordinal = {1: '1st', 2: '2nd', 3: '3rd'}.get(n, f'{n}th')
                    out[f'\0{n}'] = text_of(eid) or f'the {ordinal} answer'
    return out


def check_navigation(config):
    """Does each quiz branch go where its answer says it should?

    Three checks, each keyed to something observable rather than to intent:
    - a branch naming an answer ID the question does not have can never fire (blocker);
    - a branch that leads to a screen NAMED after a different answer is probably wired
      to the wrong screen (risk);
    - an "otherwise" path that leads to a screen named after ONE answer, while other
      answers also fall through to it, sends those answers to that one answer's screen
      (risk).
    The last two need the name signal on purpose: sending "some" and "talk" to an
    "Accelerated path" screen is a design, not a bug, and must stay silent -- it does
    on the real "Language onboarding" flow this was calibrated against.
    """
    out = []
    cap = {s['id']: s.get('caption') or s['id'] for s in config.get('screens') or []}
    for s, group, cases, default in _branches(config):
        answers = _answers(config, group)
        if not answers:
            continue
        def label(cid):
            text = answers.get(cid) or cid
            if cid.startswith('\0'):
                return text if text.startswith('the ') else f'"{text}"'
            return f'"{text}"' 
        by_name = {}
        for cid, text in answers.items():
            if cid.startswith('\0'):
                continue
            for key in {_norm(cid), _norm(text)} - {''}:
                by_name[key] = cid
        covered = set()
        for vals, targets in cases:
            for v in vals:
                covered.add(v)
                tnames = _join_and(f'"{cap.get(t, t)}"' for t in dict.fromkeys(targets))
                if v not in answers:
                    known = _join_and(f'{label(c)} (ID "{c}")' for c in answers
                                      if not c.startswith('\0'))
                    out.append(finding(
                        'blocker', 'navigation', 'dead-branch',
                        f'The "{cap[s["id"]]}" screen sends people who pick "{v}" '
                        f'{"to " + tnames if tnames else "somewhere"}, but no answer to this '
                        f'question has that ID, so nobody ever goes there: everyone takes '
                        f'the other path.',
                        f'Point this branch at one of the answers the question has: {known}.',
                        s['id']))
                    continue
                for t in targets:
                    owner = by_name.get(_norm(cap.get(t)))
                    if owner and owner != v:
                        out.append(finding(
                            'risk', 'navigation', 'branch-mismatch',
                            f'People who pick {label(v)} on the "{cap[s["id"]]}" screen go to '
                            f'the "{cap.get(t, t)}" screen, which is named after a different '
                            f'answer, {label(owner)}.',
                            f'Check this branch in the builder and point it at the screen '
                            f'meant for {label(v)}.', s['id']))
        rest = [c for c in answers if c not in covered]
        # A dead branch already explains why its answer falls through; saying it again as
        # a fall-through repeats one problem as two.
        if any(v not in answers for vals, _ in cases for v in vals):
            continue
        for t in dict.fromkeys(default):
            owner = by_name.get(_norm(cap.get(t)))
            others = [c for c in rest if c != owner]
            if owner and others:
                out.append(finding(
                    'risk', 'navigation', 'fallthrough-to-answer-screen',
                    f'On the "{cap[s["id"]]}" screen only '
                    f'{_join_and(label(c) for c in covered if c in answers)} '
                    f'{"has" if len(covered) == 1 else "have"} a branch of '
                    f'{"its" if len(covered) == 1 else "their"} own. '
                    f'{_join_and(label(c) for c in others)} also '
                    f'go{"es" if len(others) == 1 else ""} to the "{cap.get(t, t)}" screen, '
                    f'which is named after {label(owner)}.',
                    f'Give {_join_and(label(c) for c in others)} '
                    f'{"its" if len(others) == 1 else "their"} own branch, or point the '
                    f'"otherwise" path at a screen that fits every remaining answer.',
                    s['id']))
    return out


def check_sibling_locales(config, siblings):
    """Languages the app's other published flows offer and this one does not.

    `siblings` is {flow name: [locale codes]} for the app's OTHER published flows, or
    None when they were not fetched. The audit cannot know which markets the app
    serves; what it can see is that the rest of the app already speaks a language this
    flow does not. A risk, never a blocker: an English-only flow is a legitimate choice.
    """
    if not siblings:
        return []
    names = {l.get('code'): l.get('name') or l.get('code')
             for l in config.get('locales') or [] if l.get('code')}
    # Sibling flows are compared by language CODE: ids are per-flow and need not agree.
    mine = set(names)
    have = {}
    for flow, entries in siblings.items():
        for x in entries or []:
            code = x.get('code') if isinstance(x, dict) else x
            if not code or code in mine:
                continue
            names.setdefault(code, (x.get('name') if isinstance(x, dict) else None) or code)
            have.setdefault(code, []).append(flow)
    if not have:
        return []
    langs = _join_and(names[c] for c in sorted(have))
    ours = _join_and(names[c] for c in sorted(mine)) or 'one language'
    where = _join_and(f'"{n}"' for n in sorted({n for ns in have.values() for n in ns})[:3])
    return [finding(
        'risk', 'localization', 'missing-sibling-locale',
        f'Your other published flows ({where}) are also in {langs}; this one is only in '
        f'{ours}.',
        f'If people who use your app in {langs} see this flow, translate it too.')]


def audit(config, catalog=None, stores=None):
    findings = []
    findings += check_triggers(config)
    findings += check_compliance(config)
    findings += check_products_catalog(config, catalog, stores)
    findings += check_period_claim(config, catalog)
    findings += check_price_integrity(config, catalog)
    findings += check_price_prominence(config, catalog)
    findings += check_trial_toggle(config, stores)
    findings += check_disclosure(config, catalog)
    findings += check_external_purchase(config, stores)
    findings += check_localization(config)
    findings += check_placeholders(config)
    findings += check_fake_carousel(config)
    findings += check_variables(config)
    findings += check_navigation(config)
    return findings


def check_meta(meta):
    """Findings about the flow's dashboard metadata rather than its config -- the
    NAME and STATUS live in `flows list` output, not in the config, so neither can be
    reached from inside `audit()`. Wired into `main()` after `audit()` runs.
    """
    out = []
    name = (meta or {}).get('name') or ''
    if name.strip().lower() in ('untitled', 'untitled flow', 'new flow', ''):
        if name:
            out.append(finding(
                'question', 'placeholders', 'flow-untitled',
                f'The flow is still called "{name}".',
                'Give it a real name in the dashboard so your team can find it.'))
    status = (meta or {}).get('status') or ''
    if status == 'publication_failed':
        out.append(finding(
            'question', 'placeholders', 'publication-failed',
            'The last attempt to publish this flow failed (the dashboard shows it as '
            'Failed). Nothing in this audit explains why, so I will not guess.',
            'Open the flow in the Flow Builder: it shows why the publish failed.'))
    return out


ORDER = {'blocker': 0, 'risk': 1, 'question': 2}

# Store-review checks are partitioned out of the severity groups and printed under
# their own heading. They are advisory: they never count toward the verdict, never
# reach `VERDICT_CONDITIONAL`, and never route to GROUP_ANSWER (whose heading reads
# "they change the verdict" — by construction these do not).
STORE_REVIEW_CHECKS = frozenset({
    'trial-toggle', 'billed-amount-not-shown', 'derived-price-louder',
    'no-period-disclosed', 'trial-terms-incomplete', 'external-purchase-link',
    # The report-only merge of the two `check_disclosure` halves (see
    # `_merge_disclosure`). It must be listed here or `render()`'s partition would
    # route it into RISKS instead of the advisory section.
    'trial-terms-incomplete-merged',
})

# Verbatim. Both directions are stated on purpose: a clean section is not a pass, and a
# finding is not a rejection. An earlier draft of this feature gave the verdict line a
# store dimension ("1 would fail App Store review"); that is exactly the certificate
# this section must not issue, and it was dropped.
STORE_REVIEW_HEADING = "Store review (advisory, doesn't block publishing)"

# A short, human label per check -- a few words, no colon-clauses -- for the verdict
# line ONLY. The full message stays in the finding row below it; the verdict line is
# the one thing a client is guaranteed to read, so it names the FAMILY of defect, not
# a slice of prose. Derived from the check name, never from the message text.
CHECK_LABELS = {
    'dead-affordance': 'dead affordance row',
    # `dead-affordance-merged` sets its own `_label` at creation time (from whichever
    # of `MERGE_ORDER`'s checks it absorbed), so `_verdict_labels`'s
    # `f.get('_label') or CHECK_LABELS.get(...)` fallback never reaches this entry
    # today -- it exists so a future change that ever constructs one WITHOUT `_label`
    # set still prints a real label instead of the raw check name.
    'dead-affordance-merged': 'dead affordance row',
    'action-nothing': 'unwired action',
    'openurl-no-url': 'broken link action',
    'interaction-no-actions': 'empty interaction',
    'no-restore': 'no restore action',
    'no-terms-link': 'no legal links',
    'no-privacy-link': 'no legal links',
    'no-escape-in-flow': 'no way off the flow',
    'no-escape-from-paywall': 'no way off the paywall',
    'catalog-not-fetched': 'catalog not fetched',
    'product-not-in-catalog': 'product not in catalog',
    'product-no-access-level': 'product missing access level',
    'product-store-gap': 'missing store binding',
    'play-base-plan-missing': 'missing Play base plan',
    'period-claim-mismatch': 'wrong billing period',
    'foreign-price-variable': 'wrong price shown',
    'hardcoded-price': 'hardcoded price',
    'empty-translation': 'empty translation',
    'locale-entirely-empty': 'locale entirely empty',
    'untranslated': 'untranslated text',
    'placeholder-copy': 'placeholder copy',
    'variable-no-consumer': 'unused variable',
    'flow-untitled': 'flow untitled',
    'publication-failed': 'flow failed to publish',
}

# Plural forms that a naive trailing-'s' gets wrong (a leading noun, not the last
# word, needs to change). Anything absent from this dict falls back to a trailing
# 's' on the whole label, which is correct for every single-final-noun label above
# (`hardcoded price` -> `hardcoded prices`, `empty translation` -> `empty
# translations`).
PLURAL_OVERRIDES = {
    'product not in catalog': 'products not in catalog',
    'product missing access level': 'products missing access level',
    'wrong price shown': 'wrong prices shown',
    'locale entirely empty': 'locales entirely empty',
}

# Labels that are already a negation read correctly no matter how many times the
# underlying check fired -- "no legal links" is true whether one link is missing or
# both, so it is never counted. (Two distinct checks, `no-terms-link` and
# `no-privacy-link`, share this one label, which is exactly how a naive count-prefix
# produced the ungrammatical "2 no legal links".) A count only helps a countable
# noun, where pluralizing the label (via `PLURAL_OVERRIDES` or the trailing-'s'
# fallback) keeps it grammatical instead.
NEGATION_LABELS = {
    'no restore action',
    'no legal links',
    'no way off the flow',
    'no way off the paywall',
}


def _pluralize(label):
    if label in PLURAL_OVERRIDES:
        return PLURAL_OVERRIDES[label]
    return label if label.endswith('s') else label + 's'


def _verdict_labels(blockers, cap=4):
    """Distinct, short labels for the verdict line -- counting repeats where a count
    helps a countable noun (`2 hardcoded prices`), capped so a dozen blocker rows
    still fit on one line. A merged finding (see `_collapse_for_report`) carries its
    own `_label`, chosen by `MERGE_ORDER`, instead of the raw `check` name.

    A label in `NEGATION_LABELS` reads correctly whether it fired once or several
    times ("no legal links" is true regardless of how many links are missing), so it
    is printed once with no count prefix -- prefixing a count there ("2 no legal
    links") reads ungrammatically because the label already negates.
    """
    order, counts = [], {}
    for f in blockers:
        label = f.get('_label') or CHECK_LABELS.get(f['check'], f['check'])
        if label not in counts:
            counts[label] = 0
            order.append(label)
        counts[label] += 1
    parts = [
        (l if l in NEGATION_LABELS else
         (f'{counts[l]} {_pluralize(l)}' if counts[l] > 1 else l))
        for l in order
    ]
    shown = parts[:cap]
    extra = len(parts) - len(shown)
    return ', '.join(shown) + (f' +{extra} more' if extra > 0 else '')


# --- Report-only collapse of `dead-affordance` with the compliance blockers it
# already explains, AND of several SIBLING `dead-affordance` findings with each
# other. This lives entirely in the renderer -- `check_triggers` and
# `check_compliance` keep firing independently, which is what lets a flow that is
# missing a restore action but has NO dead-affordance row of its own still report its
# own separate `no-restore` blocker. Only `--report` output collapses; `--json` and
# `audit()` keep printing every finding the checks actually produced, which is what
# calibration (`tests/test-audit-flow.py`'s `of()` helper) reads.
AFFORDANCE_TO_CHECK = {'restore': 'no-restore', 'terms': 'no-terms-link',
                       'eula': 'no-terms-link', 'privacy': 'no-privacy-link'}
MERGE_ORDER = ('no-restore', 'no-terms-link', 'no-privacy-link')
# What the dead text looks like it is, and the rule that requires it -- one entry per
# compliance check a dead row can stand in for. Keyed the same as `LEGAL_NAME` and
# `ACTION_PHRASE`.
BULLET_INFO = {
    'no-restore': ('a Restore button', 'App Store 3.1.1'),
    'no-terms-link': ('a link to your Terms of Use', 'App Store 3.1.2'),
    'no-privacy-link': ('a link to your Privacy Policy', 'App Store 3.1.2'),
}
LEGAL_NAME = {'no-terms-link': 'Terms of Use', 'no-privacy-link': 'Privacy Policy'}
# What to give ONE element, in the builder's own action names.
WORD_NUM = {1: 'one', 2: 'two', 3: 'three'}
ACTION_PHRASE = {
    'no-restore': 'a "Restore purchases" action',
    'no-terms-link': 'an "Open URL" action that opens your Terms of Use page',
    'no-privacy-link': 'an "Open URL" action that opens your Privacy Policy page',
}

# The second report-only collapse: the two `check_disclosure` halves, when both fire
# on the SAME screen. Ordered absorber-last, mirroring `MERGE_ORDER`'s convention of
# naming the checks that get consumed; `_collapse_for_report` requires every name
# here to be present on one screen before it merges anything.
DISCLOSURE_MERGE = ('no-period-disclosed', 'trial-terms-incomplete')


def _merge_disclosure(screen):
    """One row for a screen that discloses neither the billing period nor what
    happens after the trial. See `_collapse_for_report`'s second pass for why
    `trial-terms-incomplete` is the absorber.
    """
    return finding(
        'risk', 'compliance', 'trial-terms-incomplete-merged',
        'This screen offers a free trial but says neither how often it bills nor what '
        'happens when the trial ends.',
        'Say both next to the offer, in one line: "Free for 7 days, then $79.99/year". '
        '(App Store 3.1.2, Google Play)',
        screen)


def _element_text(config, sid, eid):
    """The literal text of one element, read from the CONFIG -- never parsed back out
    of a finding's message. The report used to recover it (and the affordance words)
    by regex over `check_triggers`' own wording, which made every rewording of that
    message a silent break in the merge; reading the element costs one lookup and
    frees the message to say whatever reads best.
    """
    for s in config.get('screens') or []:
        if s.get('id') != sid:
            continue
        e = ((s.get('elements') or {}).get('map') or {}).get(eid) or {}
        return flat_text((e.get('props') or {}).get('content'), default_locale(config))
    return ''


def _join_and(items):
    """'a' / 'a and b' / 'a, b and c' -- no Oxford comma, matching `render`'s own
    number joins."""
    items = list(items)
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    return ', '.join(items[:-1]) + f' and {items[-1]}'


def _merge_dead_affordance_group(screen, parent, parsed, matched, config):
    """One finding covering every `dead-affordance` finding in `parsed` -- a list of
    `(raw_finding, named_words)` pairs that all share one screen and one parent
    element (or, when `parent` is None, a single pair that has no parent at all) --
    plus the compliance blockers named in `matched` (a subsequence of `MERGE_ORDER`).

    `len(parsed) == 1` is one element whose OWN text names several things ("Restore
    purchase · Terms · Privacy"): the fix is to split it, or to wire it when it names
    only one. `len(parsed) > 1` is several SIBLING elements under one parent, each
    naming one thing (`comparison-paywall.json`'s Restore/Terms/Privacy row): the fix
    is to wire each of them. The two read and fix differently, so the branch is on
    `len(parsed)`, not on `len(matched)` alone.
    """
    legal = [c for c in matched if c in LEGAL_NAME]
    what = _join_and(BULLET_INFO[c][0] for c in matched)
    rules = list(dict.fromkeys(BULLET_INFO[c][1].split()[-1] for c in matched))
    cites = 'App Store ' + _join_and(rules)
    trailer = (' The flow has no "Open URL" action anywhere, so these links do not '
               'exist yet.' if legal else '')

    if len(parsed) == 1:
        dead, _named = parsed[0]
        raw_text = _element_text(config, dead['screen'], dead['element'])
        message = (f'"{raw_text}" looks like {what}, but nothing happens when it is '
                   f'tapped: it has no On Tap action. Apple requires '
                   f'{"these" if len(matched) > 1 else "it"} on a subscription '
                   f'screen ({cites}).{trailer}')
        if len(matched) == 1:
            fix = f'Give it {ACTION_PHRASE[matched[0]]}.'
        else:
            parts = []
            if 'no-restore' in matched:
                parts.append('one with a "Restore purchases" action')
            if legal:
                names = _join_and(LEGAL_NAME[c] for c in legal)
                if len(legal) == 1:
                    parts.append(f'one with an "Open URL" action that opens your '
                                 f'{names} page')
                else:
                    parts.append(f'{WORD_NUM.get(len(legal), len(legal))} with "Open '
                                 f'URL" actions that open your {names} pages')
            fix = (f'Split it into {WORD_NUM.get(len(matched), len(matched))} '
                   f'tappable elements: ' + _join_and(parts) + '.')
        element = dead['element']
    else:
        texts = {d['element']: _element_text(config, d['screen'], d['element'])
                 for d, _words in parsed}
        elem_list = _join_and(f'"{texts[d["element"]]}"' for d, _words in parsed)
        message = (f'{elem_list} look like {what}, but nothing happens when any of '
                   f'them is tapped: none has an On Tap action. Apple requires these on '
                   f'a subscription screen ({cites}).{trailer}')
        clauses, covered = [], set()
        for c in matched:
            owners = [d['element'] for d, words in parsed
                      if any(w in words for w, cc in AFFORDANCE_TO_CHECK.items()
                             if cc == c)]
            covered.update(owners)
            if owners:
                clauses.append(f'{_join_and(chr(34) + texts[o] + chr(34) for o in owners)} '
                               f'{ACTION_PHRASE[c]}')
        fix = ('Give ' + _join_and(clauses) + '.') if clauses else (
            'Give each of them a real action.')
        # A sibling whose word maps to no firing compliance check (a "Skip" label in
        # the same row) is still named, so nothing in the group is silently dropped.
        rest = [texts[d['element']] for d, _w in parsed if d['element'] not in covered]
        if rest:
            fix += (f' {_join_and(chr(34) + t + chr(34) for t in rest)} in the same '
                    f'row {"has" if len(rest) == 1 else "have"} no action either.')
        element = parent

    merged = finding('blocker', 'triggers', 'dead-affordance-merged', message, fix,
                      screen, element)
    merged['_label'] = CHECK_LABELS[next(c for c in MERGE_ORDER if c in matched)]
    # Report-only, like `_label`: which legal pages the fix needs an address for, so
    # the next-step offer can ask for them without parsing this finding's text.
    merged['_needs'] = [LEGAL_NAME[c] for c in legal]
    return merged


def _collapse_for_report(findings, config):
    """Merge each `dead-affordance` blocker with the flow-wide compliance blockers it
    names and that are already firing, AND merge several SIBLING `dead-affordance`
    findings that share a parent element with each other first (DEFECT 1). Returns
    a new list; never mutates `findings`, and never touches a compliance finding
    that no dead row actually overlaps with.

    Sibling grouping is STRUCTURAL, not text-parsed: it walks the same
    `elements.hierarchy` tree `check_triggers`' own ancestor check uses (via
    `_parent_map`, over `config` -- the one piece of context `findings` alone does
    not carry) and groups STRICTLY by `(screen, parent element)`. Two dead rows on
    the same screen under DIFFERENT parents never merge -- a user sees those as
    separate rows -- and a dead-affordance finding whose element has no parent at
    all (the screen's own root) groups alone, since it cannot share a parent with
    anything. The per-finding affordance words are recomputed from the element's own
    text in the config (`_element_text`), never parsed out of a message, so the
    wording of `check_triggers`' finding is free to change.
    """
    compliance_pos = {}
    for i, f in enumerate(findings):
        if (f['severity'] == 'blocker' and f['screen'] is None
                and f['check'] in BULLET_INFO and f['check'] not in compliance_pos):
            compliance_pos[f['check']] = i

    screens_by_id = {s['id']: s for s in config.get('screens') or []}
    parent_maps = {}

    def parent_of(sid, eid):
        if sid not in parent_maps:
            scr = screens_by_id.get(sid) or {}
            hier = (scr.get('elements') or {}).get('hierarchy')
            parent_maps[sid] = _parent_map(hier)
        return parent_maps[sid].get(eid)

    groups = {}
    order = []
    for i, f in enumerate(findings):
        if f['severity'] != 'blocker' or f['check'] != 'dead-affordance':
            continue
        named = set(_affordance_labels(_element_text(config, f['screen'], f['element'])))
        if not named:
            continue
        parent = parent_of(f['screen'], f['element'])
        key = ((f['screen'], parent) if parent is not None
               else (f['screen'], f['element'], '_solo'))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append((i, f, named))

    consumed = set()
    replacements = {}
    for key in order:
        members = groups[key]
        named_union = set().union(*(named for _, _, named in members))
        matched = [c for c in MERGE_ORDER
                   if c in compliance_pos
                   and any(w in named_union for w, cc in AFFORDANCE_TO_CHECK.items()
                           if cc == c)]
        if not matched:
            continue
        for c in matched:
            consumed.add(compliance_pos[c])
        screen = key[0]
        parent = key[1] if len(key) == 2 else None
        parsed = [(f, named) for _, f, named in members]
        replacements[members[0][0]] = _merge_dead_affordance_group(
            screen, parent, parsed, matched, config)
        for idx, _f, _named in members[1:]:
            consumed.add(idx)

    # --- Second collapse, same mechanism, different pair: the two `check_disclosure`
    # halves on ONE screen. `trial-terms-incomplete` absorbs `no-period-disclosed`,
    # never the reverse, because its claim is the superset -- its own message already
    # says "no price, NO BILLING PERIOD, nothing about renewal", and its fix ("Free
    # for 7 days, then $79.99/year") states the billing period the other finding asks
    # for. Two rows for one defect, anchored to the same screen, with the second
    # restating and satisfying the first, is a report arguing with itself.
    #
    # Report-only, exactly like the dead-affordance collapse above: both checks keep
    # firing independently, so `--json` and `audit()` still carry both (which is what
    # `tests/test-store-review.py` calibrates against, and what keeps a screen that
    # fires only ONE of them reporting its own row unchanged).
    by_screen = {}
    for i, f in enumerate(findings):
        if i in consumed or f['check'] not in DISCLOSURE_MERGE:
            continue
        by_screen.setdefault(f['screen'], {}).setdefault(f['check'], i)
    for sid, pos in by_screen.items():
        if len(pos) < len(DISCLOSURE_MERGE):
            continue
        first = min(pos.values())
        for i in pos.values():
            if i != first:
                consumed.add(i)
        replacements[first] = _merge_disclosure(sid)

    # --- Third collapse: `no-terms-link` and `no-privacy-link` as BLOCKERS (the flow
    # has no "Open URL" action at all) are one gap with one fix. Two rows that differ
    # by one noun make the user read the same finding twice. Report-only, like the
    # others; the question form (links exist, none looks right) stays separate,
    # because each of those names different urls.
    legal_pos = {f['check']: i for i, f in enumerate(findings)
                 if i not in consumed and f['severity'] == 'blocker'
                 and f['check'] in LEGAL_NAME and f['check'] not in
                 {findings[j]['check'] for j in consumed}}
    if len(legal_pos) == 2:
        first = min(legal_pos.values())
        consumed.update(i for i in legal_pos.values() if i != first)
        merged = finding(
            'blocker', 'compliance', 'no-legal-links-merged',
            'There are no links to your Terms of Use or Privacy Policy: the flow has no '
            '"Open URL" action at all.',
            'Add two links with "Open URL" actions that open those pages. '
            '(App Store 3.1.2)')
        merged['_needs'] = ['Terms of Use', 'Privacy Policy']
        replacements[first] = merged

    # --- Fourth collapse: the same gap for several products or amounts. A missing
    # Google Play ID on two products is one answer ("do you ship on Android?") and one
    # place to fix it; four typed-in prices on one screen are one habit. Grouped on the
    # report-only fields the checks attach (`_tag`), never on message text.
    groups = {}
    for i, f in enumerate(findings):
        if i in consumed or i in replacements:
            continue
        if f['check'] == 'product-store-gap' and f.get('_store'):
            groups.setdefault(('gap', f['severity'], f['_store']), []).append(i)
        elif f['check'] == 'hardcoded-price' and f.get('_amount'):
            groups.setdefault(('price', f['screen']), []).append(i)
    for key, idx in groups.items():
        if len(idx) < 2:
            continue
        fs = [findings[i] for i in idx]
        first = idx[0]
        consumed.update(idx[1:])
        if key[0] == 'gap':
            store, platform = fs[0]['_store'], fs[0]['_platform']
            titles = _join_and(f'"{f["_title"]}"' for f in fs)
            sites = [site for f in fs for site in f.get('_sites') or []]
            where = ('' if len(config.get('screens') or []) <= 1
                     else f' They are on {_format_sites(sites, config)}.')
            if key[1] == 'question':
                msg = (f'{titles} have no {store} product ID, so they cannot be bought on '
                       f'{platform}.{where}')
                fix = (f'If you ship on {platform}, add their {store} product IDs in the '
                       f'Adapty dashboard.')
            else:
                msg = (f'{titles} have no {store} product ID, but your app ships on '
                       f'{platform}, so those purchases will fail there.{where}')
                fix = f'In the Adapty dashboard, add their {store} product IDs.'
            merged = finding(key[1], 'products', 'product-store-gap', msg, fix,
                             fs[0]['screen'], fs[0]['element'])
            merged.update(_store=store, _platform=platform)
        else:
            amounts = _join_and(f['_amount'] for f in fs)
            merged = finding(
                'blocker', 'products', 'hardcoded-price',
                f'{len(fs)} amounts are typed into the text here: {amounts}. If they are '
                f'prices, they will not show in the buyer\'s currency and will not change '
                f'when you change prices in the store.',
                'If they are prices, replace them with the product\'s price. If they are '
                'savings figures, check that they still hold when prices change.',
                fs[0]['screen'], fs[0]['element'])
        replacements[first] = merged

    # --- Fifth collapse: one finding repeated word for word on several screens (the
    # same fake slider on three quiz screens). One row naming every screen, instead of
    # three rows the reader has to compare to see they are the same.
    same = {}
    for i, f in enumerate(findings):
        if i in consumed or i in replacements or not f['screen']:
            continue
        same.setdefault((f['check'], f['severity'], f['message'], f['fix']), []).append(i)
    for key, idx in same.items():
        screens = list(dict.fromkeys(findings[i]['screen'] for i in idx))
        if len(screens) < 2:
            continue
        consumed.update(idx[1:])
        f0 = findings[idx[0]]
        names = _join_and(f'"{screen_name(config, sid)}"' for sid in screens)
        replacements[idx[0]] = finding(
            f0['severity'], f0['family'], f0['check'],
            f'{f0["message"]} It is on the {names} screens.', f0['fix'])

    return [replacements.get(i, f) for i, f in enumerate(findings) if i not in consumed]


# --- WHAT HAPPENS NEXT: route every (already-numbered) finding by WHO does the work,
# which is a different axis from severity -- severity says how bad it is, this says
# who has to act on it. Routed by CHECK NAME, never by parsing `message` text (that
# trap was closed once already, in the dead-affordance merge above; do not reopen
# it). An unmapped check name defaults to GROUP_FLOW rather than being dropped -- a
# finding missing from this section entirely is the one failure this must never
# have, and "assume I can fix it" is the least surprising wrong guess for a check
# nobody has taught this table about yet.
GROUP_ANSWER, GROUP_FLOW, GROUP_DASHBOARD, GROUP_OPTIONAL = 1, 2, 3, 4
NEXT_STEP_ORDER = (GROUP_ANSWER, GROUP_FLOW, GROUP_DASHBOARD, GROUP_OPTIONAL)

# Default group per check name: where the FIX lives, regardless of this instance's
# severity. GROUP_FLOW means "the agent can do it" -- a flow edit, a placement, or
# fetching what the audit was missing -- and GROUP_DASHBOARD means only the user can.
CHECK_TO_GROUP = {
    'dead-affordance': GROUP_FLOW,
    'dead-affordance-merged': GROUP_FLOW,
    'action-nothing': GROUP_FLOW,
    'openurl-no-url': GROUP_FLOW,
    'interaction-no-actions': GROUP_FLOW,
    'no-restore': GROUP_FLOW,
    'no-terms-link': GROUP_FLOW,
    'no-privacy-link': GROUP_FLOW,
    'no-legal-links-merged': GROUP_FLOW,
    'no-escape-in-flow': GROUP_FLOW,
    'no-escape-from-paywall': GROUP_FLOW,
    'catalog-not-fetched': GROUP_FLOW,
    'product-not-in-catalog': GROUP_DASHBOARD,
    'product-no-access-level': GROUP_DASHBOARD,
    'product-store-gap': GROUP_DASHBOARD,
    'play-base-plan-missing': GROUP_DASHBOARD,
    'period-claim-mismatch': GROUP_FLOW,
    'foreign-price-variable': GROUP_FLOW,
    'hardcoded-price': GROUP_FLOW,
    'empty-translation': GROUP_FLOW,
    'locale-entirely-empty': GROUP_FLOW,
    'missing-translation': GROUP_FLOW,
    'untranslated': GROUP_OPTIONAL,
    'placeholder-copy': GROUP_FLOW,
    'fake-carousel': GROUP_FLOW,
    'variable-no-consumer': GROUP_FLOW,
    'flow-untitled': GROUP_DASHBOARD,
    'publication-failed': GROUP_DASHBOARD,
    'no-placement': GROUP_FLOW,
    'dead-branch': GROUP_FLOW,
    'branch-mismatch': GROUP_FLOW,
    'fallthrough-to-answer-screen': GROUP_FLOW,
    'missing-sibling-locale': GROUP_FLOW,
    'placement-inactive': GROUP_DASHBOARD,
    'trial-toggle': GROUP_FLOW,
    'billed-amount-not-shown': GROUP_FLOW,
    'derived-price-louder': GROUP_FLOW,
    'no-period-disclosed': GROUP_FLOW,
    'trial-terms-incomplete': GROUP_FLOW,
    'trial-terms-incomplete-merged': GROUP_FLOW,
    'external-purchase-link': GROUP_FLOW,
}

# Checks whose severity for THIS instance is a question that an answer could turn
# into a real blocker -- these get an EXTRA line in GROUP_ANSWER, on top of (never
# instead of) their normal `CHECK_TO_GROUP` line: "do you ship on Android" up top,
# the missing product ID still listed as the user's to add, because the fix is worth
# doing whether or not the answer turns out to matter. `flow-untitled`,
# `catalog-not-fetched` and `publication-failed` are deliberately excluded: none of
# them is a question whose ANSWER changes whether the finding is a problem.
VERDICT_CONDITIONAL = {'no-terms-link', 'no-privacy-link', 'no-escape-in-flow',
                        'product-store-gap'}

# The Flow Builder's own status labels, so the header says what the dashboard says.
# `dirty` reads as "Dirty" there, which means nothing to a newcomer, so it carries
# its meaning beside it.
STATUS_LABELS = {'draft': 'Draft', 'dirty': 'Dirty (unpublished changes)',
                 'publishing': 'Publishing', 'publication_failed': 'Failed',
                 'published': 'Published', 'archived': 'Archived'}


def _next_step_groups(f):
    """Which next-step group(s) get this finding. Never zero."""
    groups = []
    if f['check'] in VERDICT_CONDITIONAL and f['severity'] == 'question':
        groups.append(GROUP_ANSWER)
    groups.append(CHECK_TO_GROUP.get(f['check'], GROUP_FLOW))
    return groups


def _answer_prompt(f, n):
    """The yes/no question for GROUP_ANSWER. Reads `message` for the one word that
    decides the phrasing (which store) -- display detail, not a routing decision, so
    it does not reopen the message-parsing rule above.
    """
    check = f['check']
    if check == 'product-store-gap':
        platform = 'Android' if 'Google Play' in f['message'] else 'iOS'
        return f'Do you ship on {platform}? If yes, finding {n} is a blocker.'
    if check in ('no-terms-link', 'no-privacy-link'):
        doc = 'Terms of Use' if check == 'no-terms-link' else 'Privacy Policy'
        return (f'Is one of the links in finding {n} really your {doc}? If not, you '
                f'need to add one.')
    if check == 'no-escape-in-flow':
        return ('Does your app show this flow with its own close button or '
                f'swipe-to-dismiss? If not, finding {n} needs a close button.')
    return f'Look at finding {n}: your answer may change the verdict.'


def _nums(ns):
    """'finding 3' / 'findings 1, 2 and 6' -- a bare number reads as a count."""
    ns = list(ns)
    return ('finding ' if len(ns) == 1 else 'findings ') + _join_and(str(n) for n in ns)


def _legal_needs(f):
    """Which legal pages an agent needs the ADDRESS of before it can fix `f` --
    the one input a flow edit here cannot invent. A link the flow already has (the
    question form of `no-terms-link`) needs nothing new."""
    if f['severity'] == 'blocker' and f['check'] in LEGAL_NAME:
        return [LEGAL_NAME[f['check']]]
    return list(f.get('_needs') or [])


def check_placements(placements, flow_id, status=None):
    """Is any placement showing this flow, and is it switched on?

    `placements` is a list of `placements get` bodies (the list endpoint carries no
    audiences, so the caller fetches each one), or None when they were not fetched.
    A flow audience is `{"content_type": "flow", "flow_id": ...}`. Returns
    `(findings, shown_by)`: `shown_by` is the developer IDs of the active placements
    that show this flow, for the report header.

    Neither finding blocks: a flow is attached AFTER it is published, so "no
    placement yet" is the normal state of a flow being checked before its first
    publish -- a next step, not a defect.
    """
    if placements is None or not flow_id:
        return [], None
    shown_by, out = [], []
    for p in placements:
        hit = any(a.get('content_type') == 'flow' and a.get('flow_id') == flow_id
                  for a in (p.get('audiences') or []))
        if not hit:
            continue
        dev = p.get('developer_id') or p.get('id')
        if p.get('is_active') is False:
            out.append(finding(
                'risk', 'placement', 'placement-inactive',
                f'Placement "{dev}" shows this flow but is switched off, so nobody '
                f'sees it yet.',
                'Turn the placement on in the Adapty dashboard when you are ready: '
                f'https://app.adapty.io/placements/flows/{p.get("id")}'))
        else:
            shown_by.append(dev)
    if not shown_by and not out:
        out.append(finding(
            'risk', 'placement', 'no-placement',
            'No placement shows this flow yet, so your app cannot fetch it and nobody '
            'will see it.',
            'Attach it to a placement.' if status in ('published', 'dirty')
            else 'Once it is published, attach it to a placement.'))
    return out, shown_by


def render(findings, config, meta=None, stores=None):
    """The user-facing report, in the order a reader acts on it: the verdict as one
    bold line, the flow it is about, the numbered findings grouped by how much they
    matter, the languages table when there is more than one, the advisory
    store-review section, then WHAT HAPPENS NEXT (what the agent can do, what only
    the user can, what to answer first) and the checks nobody can make from here.

    Every numbered finding appears exactly once with its fix; the next-step section
    only points back at numbers, never restates a finding. The agent relays this
    in the user's language -- it is the content of the report, not its final
    wording -- so the numbering, the verdict and the grouping are the parts that
    must survive translation.

    Deliberately prints NO gate-status section: a passing `verify-config.py` or
    `flows config validate` run tells a client nothing, and a failing one is already
    reported as a blocker, in the user's own terms.

    `stores` is the same set `main()` builds from `--stores`, or None when unknown;
    it exists ONLY so the check-it-yourself list can drop a reminder that cannot
    apply. `meta['shown_by']` is None when placements were not fetched (the list
    then asks the user to check), or the developer IDs of the placements showing it.
    """
    meta = meta or {}
    findings = _collapse_for_report(findings, config)
    store = [f for f in findings if f['check'] in STORE_REVIEW_CHECKS]
    findings = [f for f in findings if f['check'] not in STORE_REVIEW_CHECKS]
    blockers = [f for f in findings if f['severity'] == 'blocker']
    questions = [f for f in findings if f['severity'] == 'question']

    lines = []
    if blockers:
        k = len(blockers)
        lines.append(f'**Not ready to publish yet: {k} thing{"s" if k != 1 else ""} '
                     f'to fix first.**')
    elif questions:
        k = len(questions)
        lines.append(f'**Almost ready: {k} thing{"s" if k != 1 else ""} I could not '
                     f'check.**')
    else:
        lines.append('**Ready to publish.**')

    locales = locale_ids(config)
    n_products = len({pid for _, _, pid in bound_products(config)})
    n_screens = len(config.get('screens') or [])
    bits = []
    if meta.get('name'):
        bits.append(meta['name'])
    if meta.get('status'):
        bits.append(STATUS_LABELS.get(meta['status'], meta['status']))
    bits.append(f'{n_screens} screen{"s" if n_screens != 1 else ""}')
    if locales:
        bits.append(f'{len(locales)} language{"s" if len(locales) != 1 else ""}')
    if n_products:
        bits.append(f'{n_products} product{"s" if n_products != 1 else ""}')
    lines.append(' · '.join(bits))
    if meta.get('flow_id'):
        lines.append(f'https://app.adapty.io/flows/{meta["flow_id"]}/builder')
    shown_by = meta.get('shown_by')
    if shown_by:
        lines.append(f'Your app fetches it through placement '
                     f'{_join_and(chr(96) + d + chr(96) for d in shown_by)}.')

    n = 0
    numbered = []

    def emit(f):
        nonlocal n
        n += 1
        numbered.append((n, f))
        lines.append(f'{n}. {f["message"]}')
        # Skip the location line when the message already names the screen (the
        # product checks list every screen a product is on).
        if (f['screen'] and n_screens > 1
                and f'"{screen_name(config, f["screen"])}"' not in f['message']):
            lines.append(f'   On the "{screen_name(config, f["screen"])}" screen.')
        lines.append(f'   Fix: {f["fix"]}')
        lines.append('')

    for sev, heading in (('blocker', 'Fix before publishing'),
                         ('risk', 'Worth fixing'),
                         ('question', 'I could not check these')):
        group = [f for f in findings if f['severity'] == sev]
        if not group:
            continue
        lines += ['', f'**{heading}**', '']
        for f in group:
            emit(f)

    if len(locales) > 1:
        lname = locale_names(config)
        stat, examples = locale_coverage(config)
        base = default_locale(config)
        total = len(_localizable_values(config, locales))
        lines += ['', f'**Languages** ({total} text fields)', '',
                  f'  {"language":20}{"missing":>9}{"empty":>8}{"same as " + lname.get(base, base):>20}']
        for code in locales:
            st = stat[code]
            same = '-' if code == base else str(st['same'])
            lines.append(f'  {lname.get(code, code):20}{st["missing"]:>9}{st["empty"]:>8}{same:>20}')
        lines.append('')
        # The sentence the table alone cannot carry: WHICH values repeat and whether
        # that is expected (a brand name), plus a plain yes/no on missing text.
        same_total = sum(st['same'] for st in stat.values())
        gap_total = sum(st['missing'] + st['empty'] for st in stat.values())
        if same_total or gap_total:
            parts = []
            if same_total:
                uniq = []
                for code in locales:
                    for ex in examples[code]:
                        if ex not in uniq:
                            uniq.append(ex)
                quoted = _join_and(f'"{x}"' for x in uniq)
                verb = 'is' if len(uniq) == 1 else 'are'
                parts.append(f'{quoted} {verb} the same in every language, which is '
                             f'right for a brand or product name.')
            parts.append('Nothing is missing.' if not gap_total
                         else f'{gap_total} field(s) are missing or empty above.')
            lines.append('  ' + ' '.join(parts))
            lines.append('')

    if store:
        # The heading carries the disclaimer. Its other half -- "a clean section is
        # not a pass" -- has nothing to attach to, because a clean section is never
        # printed; what a reader needs next to a finding is that it is not a verdict.
        lines += ['', f'**{STORE_REVIEW_HEADING}**', '']
        for f in store:
            emit(f)

    if numbered:
        groups = {g: [] for g in NEXT_STEP_ORDER}
        for num, f in numbered:
            for g in _next_step_groups(f):
                groups[g].append((num, f))
        lines += ['', '**What happens next**', '']
        if groups[GROUP_ANSWER]:
            lines.append('Answer these first, they change the verdict:')
            # One question per store, not one per product: "Do you ship on Android?"
            # asked twice reads like a form, and one answer settles both findings.
            asked = {}
            for num, f in groups[GROUP_ANSWER]:
                if f['check'] == 'product-store-gap':
                    key = 'Android' if 'Google Play' in f['message'] else 'iOS'
                    asked.setdefault(key, []).append(num)
                else:
                    asked[(num,)] = [num, f]
            for key, val in asked.items():
                if isinstance(key, tuple):
                    lines.append(f'- {_answer_prompt(val[1], val[0])}')
                elif len(val) == 1:
                    lines.append(f'- Do you ship on {key}? If yes, finding {val[0]} is a '
                                 f'blocker.')
                else:
                    lines.append(f'- Do you ship on {key}? If yes, {_nums(val)} are '
                                 f'blockers.')
            lines.append('')
        if groups[GROUP_FLOW]:
            nums = [num for num, _ in groups[GROUP_FLOW]]
            needs = []
            for _num, f in groups[GROUP_FLOW]:
                for x in _legal_needs(f):
                    if x not in needs:
                        needs.append(x)
            ask = (f' For the links, send me the web addresses of your '
                   f'{_join_and(needs)} page{"s" if len(needs) != 1 else ""}.'
                   if needs else '')
            everything = len(nums) == len(numbered)
            what = (('it for you' if len(nums) == 1 else 'all of these') if everything
                    else f'{_nums(nums)} for you')
            flow_line = (f'I can fix {what}.{ask} I will show you the '
                         f'screen before and after, and change nothing until you say '
                         f'yes. Want me to?')
        # The questions are a list; everything after them is prose, one short
        # paragraph each, ending on the offer so the report's last line is the one
        # question the user has to answer.
        if groups[GROUP_DASHBOARD]:
            nums = [num for num, _ in groups[GROUP_DASHBOARD]]
            verb = 'is' if len(nums) == 1 else 'are'
            where = 'it' if len(nums) == 1 else 'each'
            lines += [f'{_nums(nums).capitalize()} {verb} yours to do in the Adapty '
                      f'dashboard; the steps are under {where}.', '']
        if groups[GROUP_OPTIONAL]:
            nums = [num for num, _ in groups[GROUP_OPTIONAL]]
            verb = 'is' if len(nums) == 1 else 'are'
            lines += [f'{_nums(nums).capitalize()} {verb} optional.', '']
        if groups[GROUP_FLOW]:
            lines += [flow_line, '']

    # Every bullet here is something no config and no catalog can show, and each one
    # says where to look -- "confirm X" with no place to confirm it is not advice.
    # Gated so a flow that sells nothing is not told to get products approved
    # (measured on `tests/fixtures/vpn-timer-draft.json`, where the old ungated list
    # nearly doubled the report).
    # Only once nothing blocks: while there are blockers, these are advice for a later
    # moment that the reader has to scroll past now. The audit that comes back clean is
    # the one that shows them.
    checks = []
    if blockers:
        pass
    elif shown_by is None:
        target = f'"{meta["name"]}"' if meta.get('name') else 'this flow'
        checks.append(f'Your app can reach this flow: open '
                      f'https://app.adapty.io/placements and check that a placement '
                      f'shows {target}.')
    ios = stores is None or 'ios' in stores
    if not blockers and bound_products(config) and ios:
        checks.append('Your subscriptions are ready for review: in App Store Connect '
                      'each one should read "Ready to Submit", and when you submit the '
                      'app version, add them under "In-App Purchases and '
                      'Subscriptions". Otherwise the reviewer sees empty prices and '
                      'rejects the build.')
    if not blockers and ios and (bound_products(config) or selling_screens(config)):
        checks.append('Your Terms of Use and Privacy Policy are also in your App Store '
                      'listing, not only on the screen: in App Store Connect, put the '
                      'privacy policy URL in the Privacy Policy field, and Terms of Use '
                      'in the app description or the License Agreement field. Apple '
                      'checks both.')
    if checks:
        lines += ['', '**Check these yourself, I cannot see them from here**', '']
        lines += [f'- {c}' for c in checks]
        lines.append('')

    header, body = lines[:2], lines[2:]
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(header + [_voice(l) for l in body]))
    return text.strip('\n') + '\n'


# Contractions, applied at render time only: the report is read by a person, the
# `--json` findings by code and tests, so the finding text itself stays plain and
# only the rendered report reads the way a colleague talks. Never inside double
# quotes or backticks -- those hold the user's own copy, product titles and
# placement IDs, which must reach them exactly as they wrote them.
CONTRACTIONS = (
    ('There is', "There's"), ('there is', "there's"),
    ('cannot', "can't"), ('Cannot', "Can't"), ('does not', "doesn't"),
    ('do not', "don't"), ('Do not', "Don't"), ('is not', "isn't"), ('are not', "aren't"),
    ('will not', "won't"), ('could not', "couldn't"), ('has not', "hasn't"),
    ('I will', "I'll"), ('It is', "It's"), ('it is', "it's"), ('you are', "you're"),
    ('That is', "That's"), ('that is', "that's"), ('They are', "They're"),
    ('they are', "they're"),
)
_PROTECTED = re.compile(r'("[^"\n]*"|`[^`\n]*`|https?://\S+)')


def _voice(line):
    parts = _PROTECTED.split(line)
    for i in range(0, len(parts), 2):
        for a, b in CONTRACTIONS:
            parts[i] = re.sub(rf'\b{a}\b', b, parts[i])
    return ''.join(parts)


VALUE_FLAGS = ('--catalog', '--stores', '--name', '--flow-id', '--status',
               '--placements', '--sibling-locales')


def parse_args(argv):
    """Split argv into (positional, flags). Returns (None, None, error) on a usage error.

    The positional is collected by INDEX as the scan proceeds, never by filtering argv
    for values that "look like" a flag's argument -- a positional equal in VALUE to a
    flag's value (e.g. the same path passed as both the config and the catalog) must
    not be mistaken for that flag's argument, or vice versa. A value-flag (`--catalog`,
    `--stores`) that is the last token, or is immediately followed by another `--flag`,
    has no value to take: that is a usage error, not a silent no-op.
    """
    positional = []
    flags = {}
    i = 0
    n = len(argv)
    while i < n:
        a = argv[i]
        if a.startswith('--'):
            if '=' in a:
                key, val = a.split('=', 1)
                flags[key] = val
                i += 1
            elif a in VALUE_FLAGS:
                if i + 1 >= n or argv[i + 1].startswith('--'):
                    return None, None, f'{a} requires a value'
                flags[a] = argv[i + 1]
                i += 2
            else:
                flags[a] = True
                i += 1
        else:
            positional.append(a)
            i += 1
    return positional, flags, None


def main(argv):
    args, flags, err = parse_args(argv)
    if err:
        print(err, file=sys.stderr)
        return 2
    if len(args) != 1:
        print(__doc__.strip().split('Usage:')[1].strip(), file=sys.stderr)
        return 2
    if flags.get('--report') and flags.get('--json'):
        print('--report and --json are mutually exclusive -- pick one output format',
              file=sys.stderr)
        return 2
    try:
        config = load_config(args[0])
        catalog = json.load(open(flags['--catalog'])) if isinstance(
            flags.get('--catalog'), str) else None
        placements = json.load(open(flags['--placements'])) if isinstance(
            flags.get('--placements'), str) else None
        siblings = json.load(open(flags['--sibling-locales'])) if isinstance(
            flags.get('--sibling-locales'), str) else None
    except (OSError, ValueError) as exc:
        print(f'cannot read input: {exc}', file=sys.stderr)
        return 2
    if isinstance(catalog, dict):
        catalog = catalog.get('data') or []
    if isinstance(placements, dict):
        placements = placements.get('data') or []
    stores = (set(flags['--stores'].split(','))
              if isinstance(flags.get('--stores'), str) else None)

    findings = audit(config, catalog, stores)
    meta = {'name': flags.get('--name') if isinstance(flags.get('--name'), str) else None,
            'flow_id': flags.get('--flow-id') if isinstance(flags.get('--flow-id'), str)
            else None,
            'status': flags.get('--status') if isinstance(flags.get('--status'), str)
            else None}
    findings += check_meta(meta)
    placement_findings, meta['shown_by'] = check_placements(placements, meta['flow_id'],
                                                                meta['status'])
    findings += placement_findings
    findings += check_sibling_locales(config, siblings)
    if flags.get('--report'):
        print(render(findings, config, meta, stores))
    elif flags.get('--json'):
        print(json.dumps({'findings': [{k: v for k, v in f.items() if not k.startswith('_')}
                                       for f in findings]}, indent=1))
    else:
        for f in findings:
            where = ' / '.join(x for x in (f['screen'], f['element']) if x)
            print(f'{f["severity"].upper():9} [{f["family"]}] {f["message"]}'
                  + (f'\n          {where}' if where else ''))
        if not findings:
            print('no findings')
    return 1 if any(f['severity'] == 'blocker' for f in findings) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
