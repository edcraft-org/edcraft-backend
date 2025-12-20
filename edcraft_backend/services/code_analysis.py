from edcraft_engine.static_analyser.models import CodeAnalysis, CodeElement
from edcraft_engine.static_analyser.static_analyser import StaticAnalyser

from edcraft_backend.schemas.code_info import (
    BranchElement,
    CodeInfo,
    CodeTree,
    FunctionElement,
    LoopElement,
)


class CodeAnalysisService:
    def __init__(self) -> None:
        self.static_analyser = StaticAnalyser()

    def analyse_code(self, code: str) -> CodeInfo:
        code_analysis = self.static_analyser.analyse(code)
        return self._build_code_info(code_analysis)

    def _build_code_info(self, code_analysis: CodeAnalysis) -> CodeInfo:
        code_tree = self._build_code_tree(code_analysis.root_element, code_analysis)

        functions: list[FunctionElement] = []
        for func in code_analysis.functions:
            functions.append(
                FunctionElement(
                    name=func.name,
                    type="function",
                    line_number=func.lineno,
                    parameters=func.parameters,
                    is_definition=func.is_definition,
                )
            )

        loops: list[LoopElement] = []
        for loop in code_analysis.loops:
            loops.append(
                LoopElement(
                    type="loop",
                    line_number=loop.lineno,
                    loop_type=loop.loop_type,
                    condition=loop.condition,
                )
            )

        branches: list[BranchElement] = []
        for branch in code_analysis.branches:
            branches.append(
                BranchElement(
                    type="branch",
                    line_number=branch.lineno,
                    condition=branch.condition,
                )
            )

        variables: list[str] = list(code_analysis.variables)

        return CodeInfo(
            code_tree=code_tree,
            functions=functions,
            loops=loops,
            branches=branches,
            variables=variables,
        )

    def _build_code_tree(
        self, node: CodeElement, code_analysis: CodeAnalysis
    ) -> CodeTree:
        return CodeTree(
            id=node.id,
            type=node.type,
            variables=(
                list(node.scope.variables)
                if node != code_analysis.root_element
                else list(code_analysis.variables)
            ),
            function_indices=[func.id for func in node.functions],
            loop_indices=[loop.id for loop in node.loops],
            branch_indices=[branch.id for branch in node.branches],
            children=[
                self._build_code_tree(child, code_analysis)
                for child in node.children or []
            ],
        )
