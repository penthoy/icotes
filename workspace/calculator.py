#!/usr/bin/env python3
"""
A small, safe arithmetic calculator that evaluates simple expressions passed
on the command line.

Usage:
  python calculator.py 1+1
  python calculator.py "(2+3)*4/5"

Only arithmetic expressions are allowed (numbers, +, -, *, /, %, //, **,
parentheses, and unary +/−). No names, function calls, or other Python
syntax is permitted.
"""
import ast
import operator as op
import sys

# Supported binary operators
_BIN_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.FloorDiv: op.floordiv,
}

# Supported unary operators
_UNARY_OPS = {
    ast.UAdd: lambda x: x,
    ast.USub: lambda x: -x,
}


def _eval_node(node):
    """Recursively evaluate an AST node, only allowing safe arithmetic."""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    # Handle numeric constants. ast.Constant is used on modern Python;
    # older Pythons used ast.Num. Avoid referencing ast.Num directly to prevent
    # DeprecationWarning on Python versions where ast.Num exists but is
    # deprecated. Detect older numeric nodes by class name instead.
    ConstantNode = getattr(ast, "Constant", None)

    if ConstantNode is not None and isinstance(node, ConstantNode):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")

    # Older ASTs may represent numbers using a node class named 'Num'. To avoid
    # touching ast.Num directly (which can emit a DeprecationWarning), detect it
    # by name on the node's class instead.
    if node.__class__.__name__ == "Num":
        # node.n is the numeric value on older AST nodes
        return getattr(node, "n")

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op_type = type(node.op)
        if op_type in _BIN_OPS:
            try:
                return _BIN_OPS[op_type](left, right)
            except ZeroDivisionError:
                raise
        raise ValueError(f"Unsupported binary operator: {op_type}")

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        op_type = type(node.op)
        if op_type in _UNARY_OPS:
            return _UNARY_OPS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type}")

    # Parentheses are represented by nesting; no special node needed.
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def evaluate_expression(expr):
    """Parse and safely evaluate an arithmetic expression string."""
    try:
        parsed = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Syntax error in expression: {e}")

    # Walk AST to ensure there are no Name, Call, Attribute, etc.
    for node in ast.walk(parsed):
        if isinstance(node, (ast.Call, ast.Name, ast.Attribute, ast.Subscript, ast.Lambda, ast.Dict, ast.List, ast.Set, ast.Tuple)):
            raise ValueError(f"Disallowed expression element: {type(node).__name__}")

    return _eval_node(parsed)


def main(argv):
    if len(argv) <= 1 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0

    expr = " ".join(argv[1:])
    try:
        result = evaluate_expression(expr)
    except ZeroDivisionError:
        print("Error: division by zero", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Print integers without a decimal point when possible
    if isinstance(result, float) and result.is_integer():
        result = int(result)

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
