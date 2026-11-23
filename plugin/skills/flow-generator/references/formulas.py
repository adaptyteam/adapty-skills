"""Formula and Date variables: the checks the publish runs on them, run locally.

A `formula` variable is `{"id", "name", "valueType": "formula", "expression"}` with no `value`:
the app calculates it from other values and nothing can write it. Its result is a Number, or a
Date when the top level is a date function. A `date` variable holds a calendar day,
`"value": "YYYY-MM-DD"`. flow-schema.md trap 27 teaches both; this module is the gate.

`issues(config)` returns `(code, path, message)` tuples, each one a publish refusal. The codes
are the service's own, so a local finding and a 422 read the same:

    formula_syntax_error, formula_argument_count, formula_operand_type,
    formula_unknown_reference, formula_ambiguous_reference, formula_cycle,
    set_variable_formula_target, date_or_formula_in_action_text, invalid_formula_variable

Mirrors the formula language as the builder and the transformer check it: read from their
source, and the codes and messages checked against the live validate endpoint. When the
service and this module disagree, the service is right and this module is the bug.

    python3 formulas.py <config.json>   # prints the issues, exits 1 if there are any
"""

import json
import re
import sys

# name -> (min args, max args)
FUNCTIONS = {
    'round': (1, 2), 'floor': (1, 1), 'mod': (2, 2), 'today': (0, 0),
    'addDays': (2, 2), 'addWeeks': (2, 2), 'addMonths': (2, 2), 'addYears': (2, 2),
    'addOfferDuration': (2, 2),
}
DATE_SHIFTS = ('addDays', 'addWeeks', 'addMonths', 'addYears')
# What a text shows a Date as: on the variable (`dateFormat`) or on its text node.
DATE_FORMATS = ('short', 'medium', 'long', 'month-day', 'month-day-short')
# An answer a formula can read, and what it reads as. Keyed by the element's customId.
ANSWER_TYPES = {'text-input': 'number', 'number-input': 'number', 'wheel-range-picker': 'number',
                'date-picker': 'date', 'date-time-picker': 'date'}
NUMERIC_PRODUCT_FIELDS = ('prod_price', 'offer_price')
CALCULATED = ('formula', 'date')

_TOKEN = re.compile(r'\s*(?:(\{\{[^{}]*\}\})|(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(.))')


class FormulaError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _tokens(expression):
    out = []
    for m in _TOKEN.finditer(expression):
        ref, num, ident, other = m.groups()
        if ref is not None:
            out.append(('ref', ref[2:-2].strip()))
        elif num is not None:
            out.append(('num', num))
        elif ident is not None:
            out.append(('ident', ident))
        elif other is not None and other.strip():
            if other not in '+-*/(),':
                raise FormulaError('formula_syntax_error', f'unexpected {other!r}')
            out.append(('op', other))
    return out


class _Scope:
    def __init__(self, config):
        self.variables = [v for v in (config.get('variables') or []) if isinstance(v, dict)]
        self.answers = {}
        self.product_groups = set()
        for host in _hosts(config):
            for e in (((host.get('elements') or host).get('map')) or {}).values():
                cid = (e.get('props') or {}).get('customId') if isinstance(e, dict) else None
                if isinstance(cid, str) and cid:
                    self.answers.setdefault(cid, e.get('type'))
        for s in config.get('screens') or []:
            for g in s.get('selectableGroups') or []:
                if g.get('type') == 'product':
                    self.product_groups.add(g.get('id'))

    def resolve(self, path):
        """The builder's rule: an id first, then the name; one source, or it is an error."""
        by_id = next((v for v in self.variables if v.get('id') == path), None)
        name = by_id.get('name') if by_id else path
        sources = [('variable', v) for v in self.variables if v.get('name') == name]
        if name.endswith('.value') and name[:-len('.value')] in self.answers:
            sources.append(('answer', self.answers[name[:-len('.value')]]))
        head, sep, rest = name.partition('.selectedProduct')
        if sep and head in self.product_groups:
            if rest == '':
                sources.append(('product', head))
            elif rest.startswith('.'):
                sources.append(('field', rest[1:]))
        if not sources:
            raise FormulaError('formula_unknown_reference',
                               f'{{{{{path}}}}} is not a variable, an answer or a product field of '
                               f'this flow')
        if len(sources) > 1:
            raise FormulaError('formula_ambiguous_reference',
                               f'{{{{{path}}}}} names more than one thing (a custom variable named '
                               f'like an answer or a product field); rename the variable')
        return sources[0]


class _Checker:
    """One formula: parses it, returns its type ('number' or 'date')."""

    def __init__(self, scope, types):
        self.scope, self.types = scope, types

    def check(self, expression):
        self.toks, self.i = _tokens(expression), 0
        if not self.toks:
            raise FormulaError('formula_syntax_error', 'the formula is empty')
        t = self.expr()
        if self.i < len(self.toks):
            tok = self.toks[self.i]
            if tok == ('op', ','):
                raise FormulaError('formula_syntax_error',
                                   'use a dot in a decimal number, like 1.5 (a comma separates '
                                   'only the arguments of a function)')
            raise FormulaError('formula_syntax_error', f'unexpected {tok[1]!r}')
        return t

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self, kind=None, value=None):
        tok = self.peek()
        if (kind and tok[0] != kind) or (value and tok[1] != value):
            raise FormulaError('formula_syntax_error',
                               f'expected {value or kind}, found {tok[1] or "the end"}')
        self.i += 1
        return tok

    def expr(self):
        t = self.term()
        while self.peek() in (('op', '+'), ('op', '-')):
            self.i += 1
            self.number(t, 'arithmetic')
            self.number(self.term(), 'arithmetic')
            t = 'number'
        return t

    def term(self):
        t = self.unary()
        while self.peek() in (('op', '*'), ('op', '/')):
            self.i += 1
            self.number(t, 'arithmetic')
            self.number(self.unary(), 'arithmetic')
            t = 'number'
        return t

    def unary(self):
        if self.peek() == ('op', '-'):
            self.i += 1
            return self.number(self.unary(), 'a minus')
        return self.primary()

    def primary(self, product_ok=False):
        kind, val = self.peek()
        if kind == 'num':
            self.i += 1
            return 'number'
        if kind == 'ref':
            self.i += 1
            return self.ref_type(val, product_ok)
        if kind == 'ident':
            return self.call()
        if (kind, val) == ('op', '('):
            self.i += 1
            t = self.expr()
            self.take('op', ')')
            return t
        raise FormulaError('formula_syntax_error', f'unexpected {val or "end of the formula"}')

    def call(self):
        _, name = self.take('ident')
        if name not in FUNCTIONS:
            raise FormulaError('formula_syntax_error',
                               f'{name}() is not a function; the functions are '
                               f'{", ".join(FUNCTIONS)} (names are case-sensitive)')
        self.take('op', '(')
        args, raw = [], []
        if self.peek() != ('op', ')'):
            while True:
                start = self.i
                if name == 'addOfferDuration' and len(args) == 1:
                    args.append(self.primary(product_ok=True))
                else:
                    args.append(self.expr())
                raw.append(self.toks[start:self.i])
                if self.peek() == ('op', ','):
                    self.i += 1
                    continue
                break
        self.take('op', ')')
        lo, hi = FUNCTIONS[name]
        if not lo <= len(args) <= hi:
            raise FormulaError('formula_argument_count',
                               f'{name}() takes {lo if lo == hi else f"{lo} or {hi}"} '
                               f'argument(s), got {len(args)}')
        if name in ('round', 'floor', 'mod'):
            for a in args[:1] if name == 'round' else args:
                self.number(a, f'{name}()')
            if name == 'round' and len(args) == 2:
                lit = raw[1]
                if not (len(lit) == 1 and lit[0][0] == 'num' and '.' not in lit[0][1]
                        and 0 <= int(lit[0][1]) <= 6):
                    raise FormulaError('formula_operand_type',
                                       'the decimals of round() are a whole number from 0 to 6, '
                                       'written as a number')
            return 'number'
        if name == 'today':
            return 'date'
        if args[0] != 'date':
            raise FormulaError('formula_operand_type', f'{name}() needs a date first')
        if name in DATE_SHIFTS:
            self.number(args[1], f'{name}()')
        elif args[1] != 'product':
            raise FormulaError('formula_operand_type',
                               'addOfferDuration() needs a selected product second: '
                               '{{<group id>.selectedProduct}}')
        return 'date'

    def ref_type(self, path, product_ok):
        kind, what = self.scope.resolve(path)
        if kind == 'product':
            if not product_ok:
                raise FormulaError('formula_operand_type',
                                   f'{{{{{path}}}}} is a product: it goes only into '
                                   f'addOfferDuration(); read a price as .prod_price or '
                                   f'.offer_price')
            return 'product'
        if kind == 'field':
            if what not in NUMERIC_PRODUCT_FIELDS:
                raise FormulaError('formula_operand_type',
                                   f'{{{{{path}}}}}: a formula reads only prod_price and '
                                   f'offer_price of a product')
            return 'number'
        if kind == 'answer':
            t = ANSWER_TYPES.get(what)
            if not t:
                raise FormulaError('formula_operand_type',
                                   f'{{{{{path}}}}}: a formula can read the answer of a text, '
                                   f'number or date field only, not a {what}')
            return t
        vt = what.get('valueType')
        if vt in ('number', 'date'):
            return vt
        if vt == 'formula':
            t = self.types(what)
            if t is None:
                raise FormulaError('formula_operand_type', f'{{{{{path}}}}} has an error: fix it '
                                   f'first')
            return t
        raise FormulaError('formula_operand_type',
                           f'{{{{{path}}}}} is a {vt} variable: use a number or a date')

    def number(self, t, where):
        if t != 'number':
            raise FormulaError('formula_operand_type', f'{where} needs a number, got a {t}')
        return 'number'


def _hosts(config):
    hosts = list(config.get('screens') or [])
    comps = config.get('components') or {}
    hosts += list(comps.values()) if isinstance(comps, dict) else list(comps)
    return [h for h in hosts if isinstance(h, dict)]


def _deps(expression, scope):
    out = []
    for path in re.findall(r'\{\{([^{}]*)\}\}', expression):
        path = path.strip()
        by_id = next((v for v in scope.variables if v.get('id') == path), None)
        name = by_id.get('name') if by_id else path
        out += [v['id'] for v in scope.variables
                if v.get('name') == name and v.get('valueType') == 'formula']
    return out


def formula_types(config):
    """{variable id: 'number' | 'date' | None} for every formula; None = it has an error."""
    scope = _Scope(config)
    formulas = {v['id']: v for v in scope.variables if v.get('valueType') == 'formula'}
    deps = {fid: _deps(f.get('expression') or '', scope) for fid, f in formulas.items()}
    in_cycle = set()

    def reaches(a, b, seen):
        for d in deps.get(a, ()):
            if d == b or (d not in seen and (seen.add(d) or reaches(d, b, seen))):
                return True
        return False
    for fid in formulas:
        if reaches(fid, fid, set()):
            in_cycle.add(fid)
    types, errors = {}, {}

    def type_of(variable):
        fid = variable['id']
        if fid in types:
            return types[fid]
        types[fid] = None
        if fid in in_cycle:
            errors[fid] = FormulaError('formula_cycle', 'this formula reads itself, directly or '
                                       'through another formula')
            return None
        try:
            types[fid] = _Checker(scope, type_of).check(variable.get('expression') or '')
        except FormulaError as e:
            errors[fid] = e
        return types[fid]
    for f in formulas.values():
        type_of(f)
    return types, errors


def _walk(o, path, visit, id_keyed=False):
    """Paths as the service prints them: the keys of an id-keyed map (`map`, `values`) quoted."""
    visit(o, path)
    if isinstance(o, dict):
        for k, v in o.items():
            plain = not id_keyed and re.fullmatch(r'[A-Za-z_]\w*', k)
            _walk(v, f'{path}.{k}' if plain else f'{path}[{json.dumps(k)}]', visit,
                  not id_keyed and k in ('map', 'values'))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _walk(v, f'{path}[{i}]', visit)


def _var_ids(o, out):
    if isinstance(o, dict):
        if o.get('type') == 'var' and isinstance(o.get('variableId'), str):
            out.add(o['variableId'])
        if o.get('type') == 'variable' and isinstance(o.get('attrs'), dict):
            out.add(o['attrs'].get('variableId'))
        for v in o.values():
            _var_ids(v, out)
    elif isinstance(o, list):
        for v in o:
            _var_ids(v, out)
    return out


def issues(config):
    variables = [v for v in (config.get('variables') or []) if isinstance(v, dict)]
    by_id = {v.get('id'): (i, v) for i, v in enumerate(variables)}
    out = []
    for i, v in enumerate(variables):
        vt = v.get('valueType')
        where = f'variables[{i}]'
        if vt == 'formula':
            for key in ('value', 'external', 'productRef'):
                if key in v:
                    out.append(('invalid_formula_variable', f'{where}.{key}',
                                f'formula {v.get("name")!r} carries {key!r}: a formula has only '
                                f'an expression, and its value is calculated'))
            if not isinstance(v.get('expression'), str):
                out.append(('invalid_formula_variable', f'{where}.expression',
                            f'formula {v.get("name")!r} has no expression string'))
        if vt in CALCULATED and v.get('dateFormat') not in (None, *DATE_FORMATS):
            out.append(('invalid_formula_variable', f'{where}.dateFormat',
                        f'dateFormat {v.get("dateFormat")!r} is not one of {", ".join(DATE_FORMATS)}'))
        if vt == 'date' and v.get('value') is not None and not (
                isinstance(v['value'], str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v['value'])):
            out.append(('invalid_formula_variable', f'{where}.value',
                        f'date {v.get("name")!r} has the value {v["value"]!r}; a date is '
                        f'"YYYY-MM-DD", no time and no zone'))
    types, errors = formula_types(config)
    for fid, e in errors.items():
        i, v = by_id[fid]
        out.append((e.code, f'variables[{i}].expression', f'Formula "{v.get("name")}": {e}'))

    formula_ids = {v['id'] for v in variables if v.get('valueType') == 'formula'}
    calculated = {v['id']: v for v in variables
                  if v.get('valueType') == 'date'
                  or (v.get('valueType') == 'formula')}

    def visit(o, path):
        if not isinstance(o, dict):
            return
        t = o.get('type')
        if t == 'setVariable' and isinstance(o.get('payload'), list):
            for k, a in enumerate(o['payload']):
                left = (a or {}).get('left') or {}
                if left.get('variableId') in formula_ids:
                    out.append(('set_variable_formula_target',
                                f'{path}.payload[{k}].left.variableId',
                                f'Set Variable writes the formula '
                                f'"{calculated[left["variableId"]].get("name")}": a formula is '
                                f'calculated, nothing can write it'))
                right = (a or {}).get('right')
                if isinstance(right, dict) and right.get('type') == 'concat':
                    for vid in sorted(_var_ids(right, set()) & set(calculated)):
                        out.append(('date_or_formula_in_action_text', f'{path}.payload[{k}].right',
                                    _action_text(calculated[vid], 'Set Variable value')))
        for kind, fields in (('alert', ('title', 'message')), ('openUrl', ('url',))):
            if t == kind and isinstance(o.get('payload'), dict):
                for f in fields:
                    for vid in sorted(_var_ids(o['payload'].get(f), set()) & set(calculated)):
                        label = {'title': 'alert title', 'message': 'alert message',
                                 'url': 'Open URL address'}[f]
                        out.append(('date_or_formula_in_action_text', f'{path}.payload.{f}',
                                    _action_text(calculated[vid], label)))
    for s in config.get('screens') or []:
        _walk(s, f'screens[{json.dumps(s.get("id"))}]', visit)
    comps = config.get('components') or {}
    for cid, c in (comps.items() if isinstance(comps, dict) else []):
        _walk(c, f'components[{json.dumps(cid)}]', visit)
    return out


def _action_text(variable, label):
    kind = 'a Formula' if variable.get('valueType') == 'formula' else 'a Date'
    return (f'Variable "{variable.get("name")}" is {kind} and cannot show in the {label}: an action '
            f'builds a plain string, so it would show a raw number or nothing')


if __name__ == '__main__':
    found = issues(json.load(open(sys.argv[1])))
    for code, path, message in found:
        print(f'{code}  {path}  {message}')
    sys.exit(1 if found else 0)
