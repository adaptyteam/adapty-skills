"""Repo-only test helper: turn a synthetic config into the stored v13 form.

Suites build their documents inline (`{"_localizable": true, "values": ...}`, top-level
`locales`) because that is the readable way to write one. A checker is then run on what a real
flow looks like, which is the catalogued form -- so every suite that hands a synthetic document
to a shipped script passes it through `catalogued()` first. It is the shipped
`localization.catalog()`, the port of the builder's own migration 013, so the document is the
one the builder would store.

A migration WARNING means the synthetic document lost a value on the way (a locale nobody
declared, a conditional branch of the wrong shape). That is a broken fixture, not a pass, so it
raises -- unless the suite is testing exactly that and passes `allow_drops=True`.
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'skills', 'flow-generator', 'references'))
_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    import localization  # noqa: E402
finally:
    sys.dont_write_bytecode = _bytecode


def catalogued(doc, allow_drops=False):
    if isinstance(doc, dict) and 'screens' not in doc and isinstance(doc.get('config'), dict):
        return dict(doc, config=catalogued(doc['config'], allow_drops))
    if not isinstance(doc, dict) or 'screens' not in doc:
        return doc
    d = copy.deepcopy(doc)
    if not isinstance(d.get('schemaVersion'), int) or d['schemaVersion'] < 12:
        d['schemaVersion'] = localization.MIN_SOURCE_VERSION
    out, warnings = localization.catalog(d)
    # Canonicalizing a code-valued defaultLocale is a repair, not a loss.
    dropped = [w for w in warnings if w['code'] != 'default-locale-code-canonicalized']
    if dropped and not allow_drops:
        raise AssertionError('synthetic fixture lost values in the catalog migration: '
                             + '; '.join(w['message'] for w in dropped))
    return out


def values_of(doc, stored):
    """The per-locale `values` dict a stored `{_lid}` field names, for a suite to mutate."""
    return doc['localization']['content'][stored['_lid']]['values']
