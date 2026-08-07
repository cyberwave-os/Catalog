"""Regression tests for safe_eval — run with `pytest` from this directory.

Covers the literal types seed_controllers.py actually uses, plus the
dict-unpacking case that used to be silently dropped (see the fix in
export_controller_policy.py: safe_eval used to filter `if k is not None`,
which is exactly how ast.Dict represents a `{**expr, ...}` merge — silently
losing every field from the unpacked expression).
"""

import ast

import pytest

from export_controller_policy import UnsupportedNode, safe_eval


def _eval_expr(source: str):
    tree = ast.parse(source, mode="eval")
    return safe_eval(tree.body)


def test_constants():
    assert _eval_expr("'hello'") == "hello"
    assert _eval_expr("42") == 42
    assert _eval_expr("True") is True
    assert _eval_expr("None") is None


def test_negative_number():
    assert _eval_expr("-1.5") == -1.5


def test_list_and_nested_dict():
    result = _eval_expr("{'a': [1, 2, {'b': 3}], 'c': (4, 5)}")
    assert result == {"a": [1, 2, {"b": 3}], "c": [4, 5]}


def test_dotted_enum_reference():
    assert _eval_expr("ControllerType.TELEOP") == "ControllerType.TELEOP"


def test_dict_unpacking_raises_instead_of_dropping_fields():
    """The bug: {**base, 'key': 'value'} used to silently evaluate to just
    {'key': 'value'} -- base's fields vanished with no error. Now it must
    raise so the caller knows extraction was incomplete, not export a
    quietly-wrong policy.
    """
    with pytest.raises(UnsupportedNode):
        _eval_expr("{**base_config, 'key': 'value'}")


def test_unsupported_node_raises():
    with pytest.raises(UnsupportedNode):
        _eval_expr("some_function_call()")
