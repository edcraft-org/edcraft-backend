"""Utilities for parsing Python code."""

import ast

from pydantic import BaseModel


class EntryFunctionParams(BaseModel):
    """Schema for entry function parameters."""

    parameters: list[str]
    has_var_args: bool = False
    has_var_kwargs: bool = False


def parse_function_parameters(code: str, function_name: str) -> EntryFunctionParams:
    """Parse function parameters from Python code.

    Args:
        code: Python source code containing the function
        function_name: Name of the function to parse

    Returns:
        EntryFunctionParams containing:
        - parameters: List of parameter names (excluding *args and **kwargs)
        - has_var_args: Whether the function accepts *args
        - has_var_kwargs: Whether the function accepts **kwargs

    Raises:
        ValueError: If the function is not found or code cannot be parsed
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Invalid Python code: {e}") from e

    # Find the function definition
    function_def = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            function_def = node
            break

    if not function_def:
        raise ValueError(f"Function '{function_name}' not found in code")

    args = function_def.args
    parameters = []

    # Collect regular positional and keyword arguments
    for arg in args.args:
        parameters.append(arg.arg)

    # Collect keyword-only arguments
    for arg in args.kwonlyargs:
        parameters.append(arg.arg)

    # Check for *args and **kwargs
    has_var_args = args.vararg is not None
    has_var_kwargs = args.kwarg is not None

    return EntryFunctionParams(
        parameters=parameters,
        has_var_args=has_var_args,
        has_var_kwargs=has_var_kwargs,
    )
