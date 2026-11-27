"""The comparison and read-only rules for the two device locale operands."""
import re

CODES = {
    'system.region': re.compile(r'[A-Z]{2}'),
    'system.language': re.compile(r'[a-z]{2,3}'),
}
SHAPES = {
    'system.region': 'two upper-case letters (ISO 3166-1 alpha-2), like "US"',
    'system.language': 'two or three lower-case letters (ISO 639), like "en"',
}
LEGACY_LANGUAGE = {'iw': 'he', 'in': 'id', 'ji': 'yi'}
LIST_COMPARISONS = ('in', 'notIn')
COMPARISONS = ('==', '!=') + LIST_COMPARISONS


def value_issue(vid, value):
    """Why one authored code is refused, or None."""
    if value is None:
        return 'has no value'
    if not isinstance(value, str):
        return f'is compared with {value!r}, which is not a string'
    if vid == 'system.language' and value in LEGACY_LANGUAGE:
        return (f'is compared with the legacy code {value!r}; use {LEGACY_LANGUAGE[value]!r}, '
                f'which the SDK reports for it')
    if not CODES[vid].fullmatch(value):
        return f'is compared with {value!r}; a value is {SHAPES[vid]}'
    return None


def operand_id(node, reserved):
    if isinstance(node, dict) and node.get('type') == 'var':
        vid = node.get('variableId')
        if isinstance(vid, str) and vid in reserved:
            return vid
    return None


def _comparison_issues(node, vid, path):
    kind = node.get('type')
    if kind not in COMPARISONS:
        yield path, f'{vid} cannot be compared with {kind!r}; use `==`, `!=`, `in` or `notIn`'
        return

    other = node.get('right')
    if other is None or (isinstance(other, dict) and other.get('type') == 'const'
                         and other.get('value') is None):
        yield path, f'{vid} has no value: pick one before you publish'
        return
    if not isinstance(other, dict) or other.get('type') != 'const':
        yield path, f'{vid} must be compared with a constant on the right'
        return

    value = other['value']
    if kind in LIST_COMPARISONS:
        if not isinstance(value, list) or not value:
            yield path, f'{vid} takes a non-empty list of codes with `{kind}`, got {value!r}'
            return
        for index, code in enumerate(value):
            problem = value_issue(vid, code)
            if problem:
                yield f'{path}.right.value[{index}]', f'{vid} {problem}'
    elif isinstance(value, list):
        yield path, f'{vid} takes one string with `{kind}`, got a list; use `in` or `notIn`'
    else:
        problem = value_issue(vid, value)
        if problem:
            yield path, f'{vid} {problem}'


def issues(screens, components, reserved):
    """Yield (code, path, message) for reserved reads and writes in the Flow's content."""
    if not reserved:
        return

    def visit(node, path, assignment=False):
        if isinstance(node, list):
            for index, item in enumerate(node):
                yield from visit(item, f'{path}[{index}]', assignment)
            return
        if not isinstance(node, dict):
            return

        vid = operand_id(node, reserved)
        if vid:
            yield ('invalid_locale_condition', path,
                   f'{vid} can only be the left operand of `==`, `!=`, `in` or `notIn`')
            return

        kind = node.get('type')
        attrs = node.get('attrs')
        if kind == 'variable' and isinstance(attrs, dict):
            vid = attrs.get('variableId')
            if isinstance(vid, str) and vid in reserved:
                yield ('unsupported_system_variable_use', path,
                       f'{vid} is in text; a device locale works only in a condition')

        left = operand_id(node.get('left'), reserved)
        if left and assignment:
            yield ('write_to_reserved_locale', f'{path}.left',
                   f'{left} is read-only device context; a setVariable cannot write it')
        elif left:
            for location, message in _comparison_issues(node, left, path):
                yield 'invalid_locale_condition', location, message

        for key, value in node.items():
            if key == 'left' and left:
                continue
            is_assignment = kind == 'setVariable' and key == 'payload' and isinstance(value, list)
            separator = '' if path.endswith(': ') else '.'
            yield from visit(value, f'{path}{separator}{key}', is_assignment)

    for screen in screens:
        if isinstance(screen, dict):
            yield from visit(screen, f'screen {screen.get("id")}: ')
    yield from visit(components or {}, 'flow: components')
