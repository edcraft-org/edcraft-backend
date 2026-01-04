"""Mock for StaticAnalyser in EdCraft Engine."""

from edcraft_engine.static_analyser.models import (
    Branch,
    CodeAnalysis,
    CodeElement,
    Function,
    Loop,
    Scope,
)


class MockStaticAnalyser:
    """
    Mock StaticAnalyser that returns predictable code analysis.

    This mock provides:
    1. Simple default behavior (minimal analysis)
    2. Custom analysis injection for specific test scenarios

    Args:
        analysis: Optional CodeAnalysis object to return instead of default.
                 Useful for testing specific code structures or edge cases.

    Example:
        # Default behavior (minimal analysis)
        mock_analyser = MockStaticAnalyser()

        # Custom analysis for specific test
        custom_analysis = CodeAnalysis(...)
        mock_analyser = MockStaticAnalyser(analysis=custom_analysis)
    """

    def __init__(self, analysis: CodeAnalysis | None = None) -> None:
        """
        Initialize mock static analyser.

        Args:
            analysis: Optional custom CodeAnalysis to return
        """
        self._custom_analysis = analysis

    def analyse(self, code: str) -> CodeAnalysis:
        """
        Analyze code and return mock CodeAnalysis.

        Args:
            code: The code to analyze (ignored in default mock)

        Returns:
            CodeAnalysis: Custom analysis if provided, otherwise minimal default analysis
        """
        if self._custom_analysis:
            return self._custom_analysis

        return self._create_default_analysis()

    def _create_default_analysis(self) -> CodeAnalysis:
        """
        Create minimal default code analysis.

        Returns:
            CodeAnalysis: A simple analysis with just a root module element
        """
        root_element = self._create_root_element()

        return CodeAnalysis(
            root_scope=Scope(variables=set()),
            root_element=root_element,
            functions=[],
            loops=[],
            branches=[],
        )

    def _create_root_element(self) -> CodeElement:
        """
        Create root module element.

        Returns:
            CodeElement: Root element representing the module
        """
        return CodeElement(
            id=0,
            type="module",
            lineno=0,
            scope=Scope(variables=set()),
            parent=None,
            children=[],
        )

    # Helper methods for creating specific code elements
    # These can be used by factory functions or custom analysis builders

    @staticmethod
    def create_function_element(
        func_id: int = 1,
        name: str = "mock_function",
        lineno: int = 1,
        parameters: list[str] | None = None,
    ) -> Function:
        """
        Create a mock function element.

        Args:
            func_id: ID for the function element
            name: Function name
            lineno: Line number where function is defined
            parameters: List of parameter names

        Returns:
            Function: Mock function element
        """
        return Function(
            id=func_id,
            type="function",
            lineno=lineno,
            scope=Scope(variables=set()),
            parent=None,
            children=[],
            name=name,
            parameters=parameters or [],
            is_definition=True,
        )

    @staticmethod
    def create_loop_element(
        loop_id: int = 2,
        loop_type: str = "for",
        lineno: int = 2,
        condition: str = "mock_condition",
    ) -> Loop:
        """
        Create a mock loop element.

        Args:
            loop_id: ID for the loop element
            loop_type: Type of loop ('for' or 'while')
            lineno: Line number where loop starts
            condition: Loop condition

        Returns:
            Loop: Mock loop element
        """
        return Loop(
            id=loop_id,
            type="loop",
            lineno=lineno,
            scope=Scope(variables=set()),
            parent=None,
            children=[],
            loop_type=loop_type,
            condition=condition,
        )

    @staticmethod
    def create_branch_element(
        branch_id: int = 3,
        lineno: int = 3,
        condition: str = "mock_condition",
    ) -> Branch:
        """
        Create a mock branch element.

        Args:
            branch_id: ID for the branch element
            lineno: Line number where branch starts
            condition: Branch condition

        Returns:
            Branch: Mock branch element
        """
        return Branch(
            id=branch_id,
            type="branch",
            lineno=lineno,
            scope=Scope(variables=set()),
            parent=None,
            children=[],
            condition=condition,
        )
