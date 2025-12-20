from pydantic import BaseModel, Field


class FunctionElement(BaseModel):
    """Model representing a function element in the code."""

    name: str = Field(..., description="Name of the function.")
    type: str = Field("function", description="Type of the code element.")
    line_number: int = Field(
        ..., description="Line number where the function is defined."
    )
    parameters: list[str] = Field(
        ..., description="List of parameters for the function."
    )
    is_definition: bool = Field(
        ..., description="Indicates if this is a function definition."
    )


class LoopElement(BaseModel):
    """Model representing a loop element in the code."""

    type: str = Field("loop", description="Type of the code element.")
    line_number: int = Field(..., description="Line number where the loop is located.")
    loop_type: str = Field(..., description="Type of the loop (e.g., for, while).")
    condition: str = Field(..., description="Condition of the loop.")


class BranchElement(BaseModel):
    """Model representing a branch element in the code."""

    type: str = Field("branch", description="Type of the code element.")
    line_number: int = Field(
        ..., description="Line number where the branch is located."
    )
    condition: str = Field(..., description="Condition of the branch.")


class CodeTree(BaseModel):
    """Model representing a node in the code tree."""

    id: int = Field(..., description="Unique identifier for the code element.")
    type: str = Field(
        ..., description="Type of the code element (function, loop, branch)."
    )
    variables: list[str] = Field(
        ..., description="List of variable names in the current code element."
    )
    function_indices: list[int] = Field(
        ..., description="List of indices of functions within this code element."
    )
    loop_indices: list[int] = Field(
        ..., description="List of indices of loops within this code element."
    )
    branch_indices: list[int] = Field(
        ..., description="List of indices of branches within this code element."
    )
    children: list["CodeTree"] = Field(..., description="List of child code elements.")


class CodeInfo(BaseModel):
    """Model representing code structure and code elements."""

    code_tree: CodeTree = Field(
        ..., description="A hierarchical representation of the code structure."
    )
    functions: list[FunctionElement] = Field(
        ..., description="List of available functions in the code."
    )
    loops: list[LoopElement] = Field(
        ..., description="List of available loops in the code."
    )
    branches: list[BranchElement] = Field(
        ..., description="List of available branches in the code."
    )
    variables: list[str] = Field(
        ..., description="List of variable names used in the code."
    )
