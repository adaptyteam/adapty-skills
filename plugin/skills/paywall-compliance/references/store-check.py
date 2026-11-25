#!/usr/bin/env python3
"""Would the stores reject this flow?

The checker of the `paywall-compliance` skill. Takes an Adapty flow config and, when there is
one, the app's product catalog; returns the store-review findings. No CLI calls -- `SKILL.md`
owns those, so this script stays testable against fixtures. No network reads.

Two kinds of finding, and the difference is the point:
  blocker  -- a mechanism the store requires is missing (Restore, Terms, Privacy, a way out
              of a paywall). App Store 3.1.1 and 3.1.2 name them; a flow without them is
              rejected, and `flow-audit` counts them against its verdict.
  risk / question -- a shape that has drawn a rejection notice, or a disclosure the
              guidelines ask for. Store review is a human process that changes without
              announcement, so these name a hazard and never issue a verdict. Evidence and
              calibration: `store-review.md`.

Usage:
  store-check.py <config.json> [--catalog <catalog.json>] [--stores ios,android]
                 [--custom-actions id=kind,...] [--json | --report] [--name <name>]
  store-check.py <config.json> --screens
Exit: 0 no blockers, 1 at least one blocker, 2 usage or unreadable input.

`--screens` prints each screen's text and what each button does, in the order people reach
them, and exits 0: the input for the rules the agent applies by reading.

`--json` prints the findings (the shape `flow-audit` merges into its own report);
`--report` prints the user-facing report; the two are mutually exclusive. `--stores` names
the stores the app ships on; without it the iOS-only checks speak in "if" form.
`--custom-actions` maps each custom action ID to what it does (`permission`, `tracking`,
`review`, `sign-in`, `other`, `none`), as the user answered.
"""
import json, os, re, sys

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
FAMILIES = ('compliance',)


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


def load_config(path):
    """Accept either the `config get` envelope or a bare config, and return the READ VIEW:
    every catalog ref inlined, `locales`/`defaultLocale` copied to the top level."""
    doc = json.load(open(path, encoding='utf-8'))
    doc = doc['config'] if isinstance(doc, dict) and 'config' in doc else doc
    return _loc.resolve(doc) if isinstance(doc, dict) else doc


def elements(config):
    """Yield (screen, element_id, element) over every screen element."""
    for s in config.get('screens') or []:
        for eid, e in ((s.get('elements') or {}).get('map') or {}).items():
            yield s, eid, e


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


def branch_text(value, locale=None):
    """`flat_text`, plus the text of every branch of a conditional-text `switch`.

    `flat_text` renders a switch as '' (see `_has_content`), so a price line written as
    "7 days free, then $4.99/week" inside a switch on the trial flag was invisible to the
    disclosure checks and `trial-terms-incomplete` fired on a screen that states its terms.
    Used by `check_disclosure` and `_is_neutral_field` only: the other text readers are
    calibrated against `flat_text` as it is. Branches are joined with ' | ', as elements are, so a term in one
    branch never runs into the next. Recursed the way `_has_content` recurses, so a switch
    nested in a branch is read too.
    """
    parts = [flat_text(value, locale)]
    v = value
    if isinstance(v, dict) and 'values' in v:
        vals = v['values'] or {}
        v = vals.get(locale) if locale in vals else next(iter(vals.values()), None)
    if isinstance(v, dict) and v.get('type') == 'switch':
        branches = [c[1] for c in (v.get('cases') or [])
                    if isinstance(c, (list, tuple)) and len(c) == 2]
        if 'default' in v:
            branches.append(v['default'])
        parts += [branch_text(b.get('value'), locale) for b in branches if isinstance(b, dict)]
    return ' | '.join(p for p in parts if p)


def default_locale(config):
    return config.get('defaultLocale') or next(
        (l.get('id') for l in (config.get('locales') or [])), None)


def actions_of(element):
    for i in (element.get('interactions') or []):
        for a in (i.get('actions') or []):
            yield i, a


ESCAPE_ACTIONS = ('closeFlow', 'navigateBack')

# Legal-link detection starts from the openUrl action's URL PAYLOAD. A label is a
# design choice -- measured: 7 of 9 real escape affordances (`escape_labels` above) are
# icon-only with no text at all. A button labeled "Legal" that opens
# https://example.com/terms is a real terms link, so a label never makes a link ABSENT.
# It can make one PRESENT: a button reading "Privacy Policy" that opens a url is that
# link, whatever the url's path says (`/tc`, a shortlink). Two small, separate
# vocabularies of URL tokens, matched case-insensitively against the url itself, and
# two of label words, matched against the text of the element carrying the action:
TERMS_URL_WORDS = ('terms', 'tos', 'eula', 'legal', 'conditions')
PRIVACY_URL_WORDS = ('privacy', 'policy')
TERMS_LABEL_WORDS = ('terms', 'eula', 'conditions', 'tos')
PRIVACY_LABEL_WORDS = ('privacy',)
# No ordinary word contains this one, so it also matches inside a run-together path
# segment (`/privacypolicy`); the short words stay exact tokens -- see `_url_tokens`.
URL_STEMS = ('privacy',)


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
    toks = set(re.split(r'[^a-z0-9]+', url.lower()))
    return toks | {stem for stem in URL_STEMS for t in toks if stem in t}


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


def _runs_in(node):
    """The values of `node` that can run. A web purchase's `onResult` never does: the
    checkout reports only whether it opened, so its outcomes are not compiled."""
    if node.get('type') == 'purchase' and (node.get('payload') or {}).get('type') == 'web':
        payload = {k: v for k, v in node['payload'].items() if k != 'onResult'}
        return [v for k, v in node.items() if k != 'payload'] + [payload]
    return list(node.values())


def _nav_targets(node, sid, order):
    """Every screen a navigate or navigateNext anywhere inside `node` can lead to,
    including inside a conditional's branches and a purchase's or restore's outcomes --
    each is still a way off the screen, and missing branches made the reachability walk
    blind to quiz routing."""
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
        for v in _runs_in(node):
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


def openurl_links(config):
    """(url, label) for every openUrl action with a url: `label` is the default-locale
    text of the element that carries the action and of everything inside it."""
    dl = default_locale(config)
    out = []
    for s, eid, e in elements(config):
        for _, a in actions_of(e):
            if a.get('type') != 'openUrl':
                continue
            url = (a.get('payload') or {}).get('url')
            text = url if isinstance(url, str) else flat_text(url, dl)
            if text:
                label = ' '.join(filter(None, (
                    flat_text((e.get('props') or {}).get('content'), dl),
                    card_text(config, s, eid, dl))))
                out.append((text, label))
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
    links = openurl_links(config)
    urls = [u for u, _ in links]
    url_token_sets = [_url_tokens(u) for u in urls]
    label_token_sets = [set(re.split(r'[^a-z0-9]+', lb.lower())) for _, lb in links]
    for words, label_words, name, label in (
            (TERMS_URL_WORDS, TERMS_LABEL_WORDS, 'no-terms-link', 'Terms of Use'),
            (PRIVACY_URL_WORDS, PRIVACY_LABEL_WORDS, 'no-privacy-link', 'Privacy Policy')):
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
        if any(w in toks for toks in label_token_sets for w in label_words):
            continue  # the button that opens a url says what it is
        shown = ', '.join(sorted(set(urls)))
        # (4) Every link is plainly something else -- the other legal page or a
        # checkout -- so none can be this one: a blocker, like having no link at all.
        # `legal` and `policy` never count as "something else": a /legal page often
        # serves both documents.
        other = (OTHER_THAN_PRIVACY if name == 'no-privacy-link' else OTHER_THAN_TERMS)
        if all(other & (ut | lt) for ut, lt in zip(url_token_sets, label_token_sets)):
            out.append(finding(
                'blocker', 'compliance', name,
                f'There is no link to your {label}: every link in the flow opens '
                f'something else ({shown}).',
                f'Add a link with an "Open URL" action that opens your {label} page. '
                '(App Store 3.1.2)'))
            continue
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
    no card copy to read -- docs/maintainers/flow-generator.md documents the shape (verified against
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
                    'for example billed amount bold at 14 pt and the per-'
                    f'{derived[0][2].rsplit("_", 1)[-1]} price at 12 pt. '
                    '(App Store 3.1.2(c), Google Play)',
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
        # `branch_text`, not `flat_text`: a disclosure written inside a conditional-text
        # switch (the price line switching on the trial flag) is still on the screen.
        blob = ' | '.join(
            branch_text((e.get('props') or {}).get('content'), dl)
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
        # CODE: `blob` comes from `branch_text`/`flat_text`, which render a variable node as '' by
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
# A link whose url or label carries one of these is plainly not the other legal page.
OTHER_THAN_PRIVACY = {'terms', 'tos', 'eula', 'conditions'} | set(PURCHASE_URL_WORDS)
OTHER_THAN_TERMS = {'privacy'} | set(PURCHASE_URL_WORDS)


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
            + '. Apple allows a link to pay outside the app only on the US storefront, or '
            'with an Apple external purchase entitlement where one exists (the EU and a '
            'few other regions); elsewhere it has rejected such links.',
            'If it is a payment page, show it only where Apple allows it, or remove it. '
            'If it is a help page, you are fine. (App Store 3.1.1)',
            s['id']))
    return out


# --- CUSTOM ACTIONS. Apart from push notifications (`requestPermission`), a flow cannot ask
# for a permission, open the rating sheet or sign anyone in: a button that does any of these
# fires a `custom` action whose ID the app's
# code matches, and an ID the app does not handle does nothing at all (Adapty's actions
# doc: "A custom action does nothing on its own"). So every ID is put to the user once,
# and the answers (`--custom-actions`) decide which store rules apply to which screen.
#
# Before an answer, a guess from the ID and the button's text lets the store checks
# speak in "if" form. An answer always replaces the guess.
# Read on the ID's words (split on `_`, `-`, spaces and camelCase), never on substrings:
# `\b` treats `_` as a word character, so `rate_us` and `request_att` read as nothing, while
# a bare "tracking" or "location" also matches a habit tracker or a city picker. A word that
# names the thing outright counts alone; one that is ambiguous counts only beside a word
# that asks for something.
ASKING = {'request', 'ask', 'allow', 'enable', 'permission', 'prompt', 'grant', 'access'}
CUSTOM_GUESS = (
    ('tracking', {'att', 'idfa'}, {'tracking', 'track'}),
    ('permission', {'notification', 'notifications', 'notif', 'notify', 'camera', 'microphone',
                    'mic', 'contacts', 'healthkit'},
     {'push', 'location', 'photo', 'photos', 'health', 'reminders'}),
    ('review', {'rate', 'rating', 'review'}, set()),
    ('sign-in', {'login', 'signin', 'signup', 'register'}, set()),
)


def _id_words(cid):
    spaced = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', cid)
    return [w for w in re.split(r'[_\-\s.]+', spaced.lower()) if w]


def _guess_kind(cid):
    words = _id_words(cid)
    joined = set(words) | {a + b for a, b in zip(words, words[1:])}  # sign_in -> signin
    if {'create', 'new'} & joined and 'account' in joined:
        return 'sign-in'
    for kind, alone, beside in CUSTOM_GUESS:
        if alone & joined or (beside & joined and ASKING & joined):
            return kind
    return 'unknown'


def _custom_ids(node):
    """Every custom action ID inside `node`, conditional branches included -- a quiz
    answer can fire one, and missing it would leave that button out of the question."""
    out = []
    if isinstance(node, dict):
        if node.get('type') == 'custom' and isinstance(node.get('payload'), dict):
            cid = node['payload'].get('id')
            if isinstance(cid, str) and cid:
                out.append(cid)
        for v in node.values():
            out += _custom_ids(v)
    elif isinstance(node, list):
        for v in node:
            out += _custom_ids(v)
    return out


def custom_sites(config):
    """custom action ID -> [(screen id, element id, label)], one entry per element.

    A button is a `stack` whose words live in descendant `text` elements, so the label
    is `card_text`'s descendant walk in the default locale; an icon-only button gets
    the same wording `escape_labels` uses."""
    dl = default_locale(config)
    screens = {s['id']: s for s in config.get('screens') or []}
    out = {}
    for s, eid, e in elements(config):
        for _, a in actions_of(e):
            for cid in _custom_ids(a):
                sites = out.setdefault(cid, [])
                if any(x[:2] == (s['id'], eid) for x in sites):
                    continue
                label = (card_text(config, screens[s['id']], eid, dl)
                         or flat_text((e.get('props') or {}).get('content'), dl)
                         or 'an icon with no text')
                sites.append((s['id'], eid, label))
    return out


def custom_kinds(config, answers=None):
    """custom action ID -> (kind, answered). An answer wins; otherwise the first guess
    the ID matches; otherwise ('unknown', False).

    The ID only, never the button's text: measured on a real activity onboarding, an
    "Add a pregnancy" button naming a health app (ID `add_pregnancy`) read as a permission prompt
    from its label and put a Skip finding on a screen that asks for nothing. An ID is
    the developer naming what the code does; a label is copy."""
    answers = answers or {}
    out = {}
    for cid in custom_sites(config):
        if cid in answers:
            out[cid] = (answers[cid], True)
            continue
        guess = _guess_kind(cid)
        out[cid] = (guess, False)
    return out


# --- PERMISSION SCREENS (store review, advisory). A flow never shows a system permission
# prompt itself; it shows the screen before it, whose button fires a Request permission
# action (push) or a custom action, and the app turns either into the prompt. Apple's HIG wants that screen to have ONE button, worded
# like "Continue" or "Next", never "Allow", and no way round it: the person declines in
# the system prompt. 2023-2026 rejections under 5.1.1(iv) removed a "Skip"/"Not now"
# or an "Enable" button. Google's guidance asks the opposite (always offer a cancel), so
# every check here is iOS-only and never tells anyone to add a Skip. Evidence and
# calibration: `store-review.md`, "Onboarding".
PERMISSION_KINDS = ('permission', 'tracking')
GRANT_WORDS = re.compile(r'\b(allow|enable|turn on|grant)\b', re.I)
# An OFFER, not a word: "feel free", "ad-free", "deals and discounts" and "unlock daily
# reminders" are ordinary primer copy and fired on bare `free`/`discount`/`unlock`.
REWARD_WORDS = re.compile(
    r'\b\d+\s*(day|week|month|year)s?\s+free\b|\bfree\s+(trial|day|week|month|year)\b|'
    r'\ba\s+free\b|\d+\s*%\s*off\b|\b(bonus|gift|reward)\b', re.I)
SYSTEM_ALERT_WORDS = re.compile(r'ask app not to track|allow tracking|'
                                r'\b(tap|press|click)\s+["“]?allow\b', re.I)


def screen_text(config, screen):
    dl = default_locale(config)
    return ' '.join(flat_text((e.get('props') or {}).get('content'), dl)
                    for e in ((screen.get('elements') or {}).get('map') or {}).values()
                    if e.get('type') == 'text')


# The key a Request permission action takes among the custom action IDs: a push prompt for
# certain, so it is answered and never put to the user.
NATIVE_PERMISSION = 'Request permission'


def _requests_permission(node):
    if isinstance(node, dict):
        return node.get('type') == 'requestPermission' or any(
            _requests_permission(v) for v in node.values())
    if isinstance(node, list):
        return any(_requests_permission(v) for v in node)
    return False


def native_permission_sites(config):
    """[(screen id, element id, label)] for each element whose actions request a permission."""
    dl = default_locale(config)
    screens = {s['id']: s for s in config.get('screens') or []}
    out = []
    for s, eid, e in elements(config):
        if any(_requests_permission(a) for _, a in actions_of(e)):
            out.append((s['id'], eid,
                        card_text(config, screens[s['id']], eid, dl)
                        or flat_text((e.get('props') or {}).get('content'), dl)
                        or 'an icon with no text'))
    return out


def primer_screens(config, kinds, sites=None):
    """screen id -> the permission/tracking action IDs fired on it."""
    out = {}
    for cid, sites in (sites if sites is not None else custom_sites(config)).items():
        if kinds.get(cid, ('unknown',))[0] in PERMISSION_KINDS:
            for sid, _, _ in sites:
                out.setdefault(sid, [])
                if cid not in out[sid]:
                    out[sid].append(cid)
    return out


def _if_unanswered(kinds, cid, what):
    """The conditional opening a finding takes while the user has not said what `cid`
    does -- the guess may be wrong, so the sentence must not state it as fact."""
    return '' if kinds[cid][1] else f'If "{cid}" {what}, '


def _cap(text):
    """The first letter upper-cased: a message that may start after an empty `lead`."""
    return text[:1].upper() + text[1:]


def check_permission_screens(config, answers=None, stores=None):
    if stores is not None and 'ios' not in stores:
        return []
    kinds = custom_kinds(config, answers)
    sites = custom_sites(config)
    native = native_permission_sites(config)
    if native:
        sites = {**sites, NATIVE_PERMISSION: native}
        kinds = {**kinds, NATIVE_PERMISSION: ('permission', True)}
    screens = {s['id']: s for s in config.get('screens') or []}
    out = []
    for sid, cids in primer_screens(config, kinds, sites).items():
        s = screens[sid]
        cid = cids[0]
        lead = _if_unanswered(kinds, cid, 'shows a system permission prompt')
        carriers = {eid for c in cids for x, eid, _ in sites[c] if x == sid}
        m = (s.get('elements') or {}).get('map') or {}
        around = [eid for eid, e in m.items() if eid not in carriers and any(
            t in ('navigate', 'navigateNext', 'closeFlow') for _, a in actions_of(e)
            for t in _action_types(a))]
        if around:
            # Named by its own words: a round's agents told users to "remove the other way
            # out" when the finding did not say which button that was.
            way = (card_text(config, s, around[0], default_locale(config))
                   or flat_text((m[around[0]].get('props') or {}).get('content'),
                                default_locale(config)))
            way = f'"{way[:40]}"' if way else 'an icon with no text'
            out.append(finding(
                'risk', 'compliance', 'primer-skip',
                _cap(f'{lead}{way} on the "{screen_name(config, sid)}" screen lets people go '
                f'past the permission prompt without seeing it. Apple has rejected onboardings '
                f'for a "Skip" or "Not now" on the screen before a permission prompt: people '
                f'are meant to decline in the prompt itself.'),
                f'Keep one button on this screen, worded like "Continue", that always shows '
                f'the prompt, and remove {way}. (App Store 5.1.1(iv))',
                sid, around[0]))
        for c in cids:
            for x, eid, label in sites[c]:
                if x == sid and GRANT_WORDS.search(label):
                    out.append(finding(
                        'risk', 'compliance', 'primer-grant-wording',
                        _cap(f'{_if_unanswered(kinds, c, "shows a system permission prompt")}'
                        f'the button that leads to the permission prompt says "{label[:40]}". '
                        f'Apple asks for a word like "Continue" or "Next" here, because the '
                        f'real choice is made in the prompt that follows.'),
                        'Change the button text to "Continue". (Apple Human Interface '
                        'Guidelines, Privacy)', sid, eid))
        reward = REWARD_WORDS.search(screen_text(config, s))
        if reward:
            out.append(finding(
                'risk', 'compliance', 'permission-incentive',
                _cap(f'{lead}the "{screen_name(config, sid)}" screen offers something '
                f'("{reward.group(0)}") for turning the permission on. Apple does not allow a '
                f'reward for granting notifications, location or tracking.'),
                'Take the offer off this screen. (App Store 5.1.2(i))', sid))
    for s in config.get('screens') or []:
        alert = SYSTEM_ALERT_WORDS.search(screen_text(config, s))
        if alert:
            out.append(finding(
                'risk', 'compliance', 'att-fake-alert',
                f'The "{screen_name(config, s["id"])}" screen says "{alert.group(0)}", which '
                f'copies or points at the system permission prompt. Apple says a screen like '
                f'this before the tracking prompt leads to rejection.',
                'Explain what the permission is for in your own words, and leave the '
                'choice to the prompt. (App Store 5.1.2(i))', s['id']))
    return out


def check_rating_and_signup(config, answers=None, stores=None):
    """Two onboarding steps that have drawn rejections (store review, advisory).

    `rating-in-onboarding`: Apple's HIG says not to ask for a rating during onboarding,
    5.6.1 disallows custom review prompts, and 2026 rejections removed a rating step
    shown before the person had used the app; Google's in-app review guidance also says
    not to trigger it from a button. Both stores, so it is not store-gated. Only a flow
    of two or more screens is an onboarding: a rating button on a one-screen flow is not
    a step anybody is walked through.

    `signup-wall`: 5.1.1(v) -- an app may not require an account unless its core
    features need one. Whether they do is the user's answer, so it is a question, and
    it fires only when signing in is the ONLY way past the screen."""
    kinds = custom_kinds(config, answers)
    sites = custom_sites(config)
    out = []
    if len(config.get('screens') or []) > 1:
        rated = []
        for cid, (kind, answered) in kinds.items():
            if kind == 'review':
                for sid, eid, _ in sites[cid]:
                    rated.append((sid, eid, _if_unanswered(kinds, cid,
                                                           'opens the rating sheet')))
        for s, eid, e in elements(config):
            for _, a in actions_of(e):
                url = (a.get('payload') or {}).get('url') if a.get('type') == 'openUrl' else None
                if isinstance(url, str) and 'write-review' in url:
                    rated.append((s['id'], eid, ''))
        for sid, eid, lead in rated:
            out.append(finding(
                'risk', 'compliance', 'rating-in-onboarding',
                _cap(f'{lead}the "{screen_name(config, sid)}" screen asks for a rating while '
                f'people are still going through the onboarding, before they have used '
                f'your app. Apple has rejected onboardings for this.'),
                'Take the rating step out of the onboarding and ask later, once people '
                'have used the app, through the store\'s own rating prompt. (App Store '
                '5.6.1; Apple Human Interface Guidelines, Ratings and reviews)', sid, eid))
    if stores is None or 'ios' in stores:
        # A way past is a navigate or close, or a custom action that is not itself a
        # sign-in: a "Continue as guest" button wired to the app's own code is still one.
        forward = {}
        for s, eid, e in elements(config):
            for _, a in actions_of(e):
                if any(t in ('navigate', 'navigateNext', 'closeFlow')
                       for t in _action_types(a)) or any(
                        kinds.get(c, ('unknown',))[0] != 'sign-in' for c in _custom_ids(a)):
                    forward.setdefault(s['id'], set()).add(eid)
        # One finding per screen: a sign-in screen with Apple, Google and email buttons is
        # one wall, and every one of those buttons is a carrier, not a way past it.
        walls = {}
        for cid, (kind, _) in kinds.items():
            if kind == 'sign-in':
                for sid, eid, _ in sites[cid]:
                    walls.setdefault(sid, []).append((cid, eid))
        for sid, carried in walls.items():
            if forward.get(sid, set()) - {eid for _, eid in carried}:
                continue
            cid, eid = carried[0]
            out.append(finding(
                'question', 'compliance', 'signup-wall',
                _cap(f'{_if_unanswered(kinds, cid, "signs people in")}signing in is the only '
                f'way past the "{screen_name(config, sid)}" screen. Apple allows that '
                f'only when the app\'s core features need an account.'),
                'If your app works without an account, add a way to continue without '
                'one, such as "Continue as guest" or "Skip". (App Store 5.1.1(v))',
                sid, eid))
    return out


CLOSE_WORDS = re.compile(r'\b(close|no thanks|not now|maybe later|skip)\b', re.I)


def _norm_label(text):
    return re.sub(r'\s+', ' ', text or '').strip().lower()


def _shown_selling(screen, element):
    """Elements this element's showElement actions reveal whose subtree sells: a purchase
    action or a bound product. A sheet opened from a close is the same exit offer as a
    second screen."""
    emap = (screen.get('elements') or {}).get('map') or {}
    kids = {}

    def walk(n):
        kids[n.get('id')] = [c.get('id') for c in n.get('children') or []]
        for c in n.get('children') or []:
            walk(c)
    walk((screen.get('elements') or {}).get('hierarchy') or {})

    def sells(x, seen):
        if x in seen:
            return False
        seen.add(x)
        e = emap.get(x) or {}
        if ((e.get('props') or {}).get('product') or {}).get('id') or any(
                a.get('type') == 'purchase' for _, a in actions_of(e)):
            return True
        return any(sells(k, seen) for k in kids.get(x, []))

    def shown(node):
        if isinstance(node, dict):
            got = []
            if node.get('type') == 'showElement':
                got += [x for x in (node.get('payload') or {}).get('elements') or []
                        if isinstance(x, str)]
            return got + [x for v in node.values() for x in shown(v)]
        if isinstance(node, list):
            return [x for v in node for x in shown(v)]
        return []
    return [x for x in dict.fromkeys(shown(element.get('interactions')))
            if x in emap and sells(x, set())]


def check_exit_and_cta(config, stores=None):
    """Two paywall-in-onboarding shapes (store review, advisory).

    `exit-offer-on-dismiss` (iOS): closing a selling screen opens another selling
    screen. Rejected under 5.6 with the reviewer's own words about manipulating people
    into purchases (Nov 2024); the same shape had passed earlier versions, so it is a
    risk on any update, not a certainty. Not the deferred `escape-gated` idea: that
    names any close that does not close, which has no rejection behind it yet.

    `purchase-looks-like-continue` (Android): Google Play's Subscriptions policy lists
    "multiple screens in the purchase flow that lead users into accidentally clicking
    the subscribe button". The observable form is the purchase button carrying the same
    words as the forward buttons on the two screens before it."""
    out = []
    selling = selling_screens(config)
    if not selling:
        return out
    screens = {s['id']: s for s in config.get('screens') or []}
    dl = default_locale(config)

    def label(sid, eid):
        e = (screens[sid].get('elements') or {}).get('map', {}).get(eid) or {}
        return (card_text(config, screens[sid], eid, dl)
                or flat_text((e.get('props') or {}).get('content'), dl))

    if stores is None or 'ios' in stores:
        for s, eid, e in elements(config):
            if s['id'] not in selling:
                continue
            types, targets = [], []
            for _, a in actions_of(e):
                types += _action_types(a)
                targets += _nav_targets(a, s['id'], list(screens))
            text = label(s['id'], eid)
            offers = [screen_name(config, t) for t in targets
                      if t in selling and t != s['id']]
            offers += [(s['elements']['map'][x].get('caption') or 'a sheet')
                       for x in _shown_selling(s, e)]
            if offers and 'purchase' not in types and (not text or CLOSE_WORDS.search(text)):
                out.append(finding(
                    'risk', 'compliance', 'exit-offer-on-dismiss',
                    f'Closing the "{screen_name(config, s["id"])}" screen opens another '
                    f'offer ("{offers[0]}") instead of letting people '
                    f'leave. Apple has rejected this as pushing people into a purchase they '
                    f'did not want.',
                    'Make the close button close the flow ("Close Flow"), and show the '
                    'second offer somewhere people choose to open it. (App Store 5.6)',
                    s['id'], eid))
    if stores is None or 'android' in stores:
        forward = {}
        for s, eid, e in elements(config):
            if s['id'] in selling:
                continue
            if any(t in ('navigate', 'navigateNext') for _, a in actions_of(e)
                   for t in _action_types(a)):
                forward.setdefault(s['id'], set()).add(_norm_label(label(s['id'], eid)))
        path = _reachable(config)
        for s, eid, e in elements(config):
            if s['id'] not in selling or not any(
                    a.get('type') == 'purchase' for _, a in actions_of(e)):
                continue
            before = [x for x in path[:path.index(s['id'])] if x in forward][-2:] if (
                s['id'] in path) else []
            words = _norm_label(label(s['id'], eid))
            if len(before) == 2 and words and all(words in forward[x] for x in before):
                out.append(finding(
                    'risk', 'compliance', 'purchase-looks-like-continue',
                    f'The purchase button on the "{screen_name(config, s["id"])}" screen '
                    f'says "{label(s["id"], eid)[:40]}", the same as the buttons that moved '
                    f'people through the screens before it, so someone tapping through can '
                    f'subscribe without meaning to. Google Play lists this as a policy '
                    f'violation.',
                    'Word the purchase button for what it does, such as "Subscribe" or '
                    '"Start free trial". (Google Play Subscriptions policy)', s['id'], eid))
    return out


def _action_types(node):
    out = []
    if isinstance(node, dict):
        if isinstance(node.get('type'), str):
            out.append(node['type'])
        for v in _runs_in(node):
            out += _action_types(v)
    elif isinstance(node, list):
        for v in node:
            out += _action_types(v)
    return out


def _reachable(config):
    order = [s['id'] for s in config.get('screens') or []]
    if not order:
        return []
    edges, seen, queue = nav_graph(config), [order[0]], [order[0]]
    while queue:
        for nxt in sorted(edges.get(queue.pop(0), ())):
            if nxt in edges and nxt not in seen:
                seen.append(nxt)
                queue.append(nxt)
    return seen




def _does(node, config, locale):
    """What an action does, in words, for `screens_outline`: each kind once, in order."""
    names = {s['id']: s.get('caption') or s['id'] for s in config.get('screens') or []}
    out = []

    def walk(n):
        if isinstance(n, list):
            for x in n:
                walk(x)
            return
        if not isinstance(n, dict):
            return
        t, p = n.get('type'), n.get('payload') or {}
        if t == 'navigate' and p.get('screen'):
            out.append(f'goes to "{names.get(p["screen"], p["screen"])}"')
        elif t == 'navigateNext':
            out.append('goes to the next screen')
        elif t == 'navigateBack':
            out.append('goes back')
        elif t == 'closeFlow':
            out.append('closes the flow')
        elif t == 'purchase':
            out.append('opens a web checkout' if p.get('type') == 'web' else 'starts a purchase')
        elif t == 'restorePurchases':
            out.append('restores purchases')
        elif t == 'openUrl':
            url = p.get('url')
            out.append(f'opens {url if isinstance(url, str) else flat_text(url, locale)}')
        elif t == 'custom' and p.get('id'):
            out.append(f'fires the custom action "{p["id"]}"')
        elif t == 'requestPermission':
            out.append('shows the push-notification prompt')
        elif t == 'selectProduct':
            out.append('selects a plan')
        elif t == 'showElement':
            out.append('shows a hidden part of the screen')
        for v in _runs_in(n):
            walk(v)
    walk(node)
    return list(dict.fromkeys(out))


# Element kinds the consumer-law and app-level rules ask about; text and buttons are printed
# by themselves.
OUTLINE_KINDS = {'spinner': 'a loader',
                 'carousel': 'a carousel', 'text-input': 'a text field',
                 'email-input': 'an email field', 'password-input': 'a password field',
                 'number-input': 'a number field', 'phone-input': 'a phone number field',
                 'date-picker': 'a date picker', 'product': 'a plan card'}
# What a countdown does when it reaches zero is the app's; when it starts is the config's.
TIMER_STARTS = {'start_at_every_appear': 'starts over every time the screen appears',
                'start_at_first_appear': 'starts the first time the screen appears',
                'start_at_first_appear_persisted':
                    'starts the first time the screen appears and keeps running after',
                'until_date': 'counts down to a set date',
                'developer_defined': 'ends when the app says'}


def outline_text(value, locale=None):
    """`flat_text` that keeps each variable as `{field}` (a price, the user's name) and each
    conditional text's branches, so a line like "{prod_price_per_month}/month" still reads."""
    if isinstance(value, dict) and 'values' in value:
        vals = value['values'] or {}
        value = vals.get(locale) if locale in vals else next(iter(vals.values()), None)
    out = []

    def walk(n):
        if isinstance(n, list):
            for x in n:
                walk(x)
        elif isinstance(n, str):
            out.append(n)
        elif isinstance(n, dict):
            if n.get('type') == 'text':
                out.append(n.get('text', ''))
            elif n.get('type') == 'variable':
                attrs = n.get('attrs') or {}
                ref = attrs.get('productRef') or {}
                name = ref.get('field') or str(attrs.get('variableId') or 'value')
                out.append('{' + re.sub(r'\.value$', '', name) + '}')
            elif n.get('type') == 'switch':
                branches = [c[1].get('value') for c in (n.get('cases') or [])
                            if isinstance(c, (list, tuple)) and len(c) == 2
                            and isinstance(c[1], dict)]
                if isinstance(n.get('default'), dict):
                    branches.append(n['default'].get('value'))
                out.append(' | '.join(filter(None, (outline_text(b, locale) for b in branches))))
            for x in (n.get('content') or []):
                walk(x)
            if n.get('type') in ('paragraph', 'hardBreak'):
                out.append(' ')
    walk(value)
    return ' '.join(''.join(out).split())


def screens_outline(config):
    """Each screen's text and what each button does, in the order people reach them, for the
    rules the agent applies by reading (`consumer-law.md`, `app-level.md`). No findings."""
    dl = default_locale(config)
    order = [s['id'] for s in config.get('screens') or []]
    reached = _reachable(config)
    screens = {s['id']: s for s in config.get('screens') or []}
    lines = []
    for n, sid in enumerate(reached + [s for s in order if s not in reached], 1):
        s = screens[sid]
        els = s.get('elements') or {}
        emap = els.get('map') or {}
        tail = '' if sid in reached else ' (not reached from the first screen)'
        lines.append(f'Screen {n}: "{screen_name(config, sid)}"{tail}')
        done = set()
        for eid in _descendants(els.get('hierarchy') or {}):
            e = emap.get(eid)
            if not e or eid in done:
                continue
            acts = [a for _, a in actions_of(e)]
            if acts:
                inside = _descendants(_find_node(els.get('hierarchy') or {}, eid) or {}) or [eid]
                label = ' | '.join(filter(None, (
                    outline_text(((emap.get(i) or {}).get('props') or {}).get('content'), dl)
                    for i in inside if (emap.get(i) or {}).get('type') == 'text'
                    or i == eid))) or 'an icon with no text'
                done.update(inside)
                does = '; '.join(_does(acts, config, dl)) or 'does nothing'
                lines.append(f'  - button "{label}": {does}')
            elif e.get('type') == 'text':
                text = outline_text((e.get('props') or {}).get('content'), dl)
                if text:
                    lines.append(f'  - text: {text}')
            elif e.get('type') == 'timer':
                starts = TIMER_STARTS.get((e.get('props') or {}).get('behavior'))
                lines.append('  - a countdown timer' + (f' that {starts}' if starts else ''))
            elif e.get('type') in OUTLINE_KINDS:
                lines.append(f'  - {OUTLINE_KINDS[e["type"]]}')
        lines.append('')
    return '\n'.join(lines).strip()


VALUE_FLAGS = ('--catalog', '--stores', '--custom-actions', '--name')

# What the user said each custom action ID does. A flow cannot request a permission,
# show the rating sheet or sign anyone in: each of those is a `custom` action whose
# meaning only the app's code knows, so the store rules for those screens can only be
# applied once the user has named it.
CUSTOM_KINDS = ('permission', 'tracking', 'review', 'sign-in', 'other', 'none')


def parse_custom_actions(value):
    """`id=kind[,id=kind...]` -> {id: kind}. Spaces are trimmed and empty items skipped;
    a missing `=` or an unknown kind raises ValueError naming the item."""
    out = {}
    for item in value.split(','):
        if not item.strip():
            continue
        cid, sep, kind = item.partition('=')
        cid, kind = cid.strip(), kind.strip()
        if not sep or not cid or kind not in CUSTOM_KINDS:
            raise ValueError(f'--custom-actions: "{item.strip()}" is not id=kind, where '
                             f'kind is one of {", ".join(CUSTOM_KINDS)}')
        out[cid] = kind
    return out


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


# The mechanisms the stores require; an open question about one of them holds the verdict.
MECHANISM_CHECKS = ('no-escape-in-flow', 'no-restore', 'no-terms-link', 'no-privacy-link',
                    'no-escape-from-paywall')


def store_check(config, catalog=None, stores=None, answers=None):
    """Every store check, in the order `flow-audit` has always printed them: the required
    mechanisms first, then the paywall shapes, then the onboarding around it."""
    findings = []
    findings += check_compliance(config)
    findings += check_price_prominence(config, catalog)
    findings += check_trial_toggle(config, stores)
    findings += check_disclosure(config, catalog)
    findings += check_external_purchase(config, stores)
    findings += check_permission_screens(config, answers, stores)
    findings += check_rating_and_signup(config, answers, stores)
    findings += check_exit_and_cta(config, stores)
    return findings


# Verbatim, both halves: a clean run is not an approval, and a finding is not a rejection.
DISCLAIMER = ('Store review is done by people and changes without notice: a clean check '
              'is not an approval, and a finding is not a rejection.')
GUIDE_URL = 'https://adapty.io/docs/prepare-your-app-for-store-review'


def render(findings, config, meta=None):
    """The standalone report: a verdict line about the required mechanisms only, the
    numbered findings by kind, the disclaimer and the one page to read next. Inside
    `flow-audit` this report is never printed -- `flow-audit` merges `--json` into its own.
    """
    meta = meta or {}
    blockers = [f for f in findings if f['severity'] == 'blocker']
    n_screens = len(config.get('screens') or [])

    def things(n):
        return f'{n} {"thing" if n == 1 else "things"}'

    risks = [f for f in findings if f['severity'] == 'risk']
    open_mechanisms = [f for f in findings if f['severity'] == 'question'
                       and f['check'] in MECHANISM_CHECKS]
    if blockers:
        verdict = (f'**The stores will reject this as it is: {things(len(blockers))} '
                   'to fix first.**')
    elif open_mechanisms:
        verdict = ('**I could not confirm everything the stores require: '
                   f'{things(len(open_mechanisms))} to answer first.**')
    elif risks:
        verdict = ('**Nothing the stores require is missing, but '
                   f'{things(len(risks))} here {"has" if len(risks) == 1 else "have"} '
                   'drawn rejections before.**')
    else:
        verdict = ('**Nothing the stores require is missing, and nothing here has drawn a '
                   'rejection before.**')
    lines = [verdict]
    if meta.get('name'):
        lines.append(meta['name'])
    n = 0
    for sev, heading in (('blocker', 'Fix before you submit'),
                         ('risk', 'Has drawn rejections'),
                         ('question', 'Tell me, and I can check')):
        group = [f for f in findings if f['severity'] == sev]
        if not group:
            continue
        lines += ['', f'**{heading}**', '']
        for f in group:
            n += 1
            lines.append(f'{n}. {f["message"]}')
            if f['screen'] and n_screens > 1:
                lines.append(f'   On the "{screen_name(config, f["screen"])}" screen.')
            lines.append(f'   Fix: {f["fix"]}')
            lines.append('')
    lines += ['', DISCLAIMER, f'What the stores look at: {GUIDE_URL}']
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


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
        catalog = json.load(open(flags['--catalog'], encoding='utf-8')) if isinstance(
            flags.get('--catalog'), str) else None
    except (OSError, ValueError) as exc:
        print(f'cannot read input: {exc}', file=sys.stderr)
        return 2
    if isinstance(catalog, dict):
        catalog = catalog.get('data') or []
    stores = (set(flags['--stores'].split(','))
              if isinstance(flags.get('--stores'), str) else None)
    try:
        answers = (parse_custom_actions(flags['--custom-actions'])
                   if isinstance(flags.get('--custom-actions'), str) else None)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    if flags.get('--screens'):
        print(screens_outline(config))
        return 0
    findings = store_check(config, catalog, stores, answers)
    if flags.get('--report'):
        name = flags.get('--name') if isinstance(flags.get('--name'), str) else None
        print(render(findings, config, {'name': name}))
    elif flags.get('--json'):
        print(json.dumps({'findings': findings}, indent=1))
    else:
        for f in findings:
            where = ' / '.join(x for x in (f['screen'], f['element']) if x)
            print(f'{f["severity"].upper():9} {f["check"]}: {f["message"]}'
                  + (f'\n          {where}' if where else ''))
        if not findings:
            print('no findings')
    return 1 if any(f['severity'] == 'blocker' for f in findings) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
