"""Mock CodeAnalysisService for testing."""

from edcraft_backend.schemas.code_info import (
    BranchElement,
    CodeInfo,
    CodeTree,
    FunctionElement,
    LoopElement,
)


class MockCodeAnalysisService:
    """
    Mock for CodeAnalysisService that returns predictable code analysis.

    This mock replaces the actual static code analysis service
    with deterministic responses for testing purposes.
    """

    def analyse_code(self, code: str) -> CodeInfo:
        """
        Analyze code and return mock CodeInfo object.

        Args:
            code: Code to analyze (basic analysis performed)

        Returns:
            Mock CodeInfo object with basic structure
        """
        # Create mock code tree
        code_tree = CodeTree(
            id=0,
            type="module",
            variables=[],
            function_indices=[],
            loop_indices=[],
            branch_indices=[],
            children=[],
        )

        # Detect basic code features
        functions: list[FunctionElement] = []
        if "def " in code:
            functions.append(
                FunctionElement(
                    name="mock_function",
                    type="function",
                    line_number=1,
                    parameters=[],
                    is_definition=True,
                )
            )

        loops: list[LoopElement] = []
        if "for " in code or "while " in code:
            loops.append(
                LoopElement(
                    type="loop",
                    line_number=2,
                    loop_type="for" if "for " in code else "while",
                    condition="mock_condition",
                )
            )

        branches: list[BranchElement] = []
        if "if " in code:
            branches.append(
                BranchElement(
                    type="branch",
                    line_number=3,
                    condition="mock_condition",
                )
            )

        return CodeInfo(
            code_tree=code_tree,
            functions=functions,
            loops=loops,
            branches=branches,
            variables=[],
        )
