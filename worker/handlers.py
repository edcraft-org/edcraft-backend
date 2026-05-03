"""Job handlers for the Nomad worker."""

import codecs
from collections.abc import Callable
from typing import Any

from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    QuestionSpec,
    TargetElement,
)
from edcraft_engine.question_generator.question_generator import QuestionGenerator
from edcraft_engine.static_analyser import StaticAnalyser
from edcraft_engine.static_analyser.models import CodeAnalysis, CodeElement


class JobHandlers:
    def __init__(
        self,
        question_generator: QuestionGenerator,
        static_analyser: StaticAnalyser,
        generate_input: Callable[[dict], Any],
    ) -> None:
        self._qg = question_generator
        self._analyser = static_analyser
        self._generate_input = generate_input

    def _decode_code(self, code: str) -> str:
        return codecs.decode(code, "unicode_escape")

    def _build_specs(
        self, params: dict[str, Any]
    ) -> tuple[str, QuestionSpec, ExecutionSpec, GenerationOptions]:
        decoded_code = self._decode_code(params["code"])
        question_spec = QuestionSpec(**params["question_spec"])
        execution_spec = ExecutionSpec(**params["execution_spec"])
        generation_options = GenerationOptions(**params["generation_options"])
        return decoded_code, question_spec, execution_spec, generation_options

    def _build_question_from_template(
        self,
        template: dict[str, Any],
        input_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        decoded_code = self._decode_code(template["code"])

        target_elements = [
            TargetElement(
                type=el["element_type"],
                id=el["id_list"],
                name=el["name"],
                line_number=el["line_number"],
                modifier=el.get("modifier"),
                argument_keys=el.get("argument_keys"),
            )
            for el in template["target_elements"]
        ]

        question_spec = QuestionSpec(
            question_type=template["question_type"],
            target=target_elements,
            output_type=template["output_type"],
        )
        execution_spec = ExecutionSpec(
            entry_function=template["entry_function"],
            input_data=input_data,
        )
        generation_options = GenerationOptions(
            num_distractors=template["num_distractors"]
        )

        question = self._qg.generate_question(
            code=decoded_code,
            question_spec=question_spec,
            execution_spec=execution_spec,
            generation_options=generation_options,
        )

        return {
            "question": question.model_dump(),
            "question_text_template": template["question_text_template"],
            "text_template_type": template["text_template_type"],
            "input_data": input_data,
        }

    def dispatch(self, job_type: str, params: dict[str, Any]) -> Any:
        handlers = {
            "analyse_code": self.handle_analyse_code,
            "generate_question": self.handle_generate_question,
            "generate_template": self.handle_generate_template,
            "question_from_template": self.handle_question_from_template,
            "assessment_from_template": self.handle_assessment_from_template,
            "generate_inputs": self.handle_generate_inputs,
        }

        if job_type not in handlers:
            raise ValueError(f"Unknown job type: {job_type!r}")
        return handlers[job_type](params)

    def handle_generate_inputs(self, params: dict[str, Any]) -> dict[str, Any]:
        inputs = params["inputs"]
        return {
            "inputs": {
                var: self._generate_input(schema) for var, schema in inputs.items()
            }
        }

    def handle_analyse_code(self, params: dict[str, Any]) -> dict[str, Any]:
        decoded_code = self._decode_code(params["code"])
        code_analysis = self._analyser.analyse(decoded_code)
        return {"code_info": self._build_code_info(code_analysis)}

    def _build_code_info(self, code_analysis: CodeAnalysis) -> dict[str, Any]:
        code_tree = self._build_code_tree(code_analysis.root_element, code_analysis)

        functions = [
            {
                "name": func.name,
                "type": "function",
                "line_number": func.lineno,
                "parameters": func.parameters,
                "is_definition": func.is_definition,
            }
            for func in code_analysis.functions
        ]

        loops = [
            {
                "type": "loop",
                "line_number": loop.lineno,
                "loop_type": loop.loop_type,
                "condition": loop.condition,
            }
            for loop in code_analysis.loops
        ]

        branches = [
            {
                "type": "branch",
                "line_number": branch.lineno,
                "condition": branch.condition,
            }
            for branch in code_analysis.branches
        ]

        return {
            "code_tree": code_tree,
            "functions": functions,
            "loops": loops,
            "branches": branches,
            "variables": list(code_analysis.variables),
        }

    def _build_code_tree(
        self, node: CodeElement, code_analysis: CodeAnalysis
    ) -> dict[str, Any]:
        return {
            "id": node.id,
            "type": node.type,
            "variables": (
                list(code_analysis.variables)
                if node is code_analysis.root_element
                else list(node.scope.variables)
            ),
            "function_indices": [func.id for func in node.functions],
            "loop_indices": [loop.id for loop in node.loops],
            "branch_indices": [branch.id for branch in node.branches],
            "children": [
                self._build_code_tree(child, code_analysis)
                for child in node.children or []
            ],
        }

    def handle_generate_question(self, params: dict[str, Any]) -> dict[str, Any]:
        decoded_code, question_spec, execution_spec, generation_options = (
            self._build_specs(params)
        )

        result = self._qg.generate_question(
            code=decoded_code,
            question_spec=question_spec,
            execution_spec=execution_spec,
            generation_options=generation_options,
        )
        return result.model_dump()

    def _generate_question_text_template(
        self, question_spec: QuestionSpec, func_params: list[str]
    ) -> str:
        question_text_template = self._qg.text_generator.generate_question(
            question_spec=question_spec,
            input_data=None,
        )

        if func_params:
            input_fmt = ", ".join(f"{p} = {{{p}}}" for p in func_params)
            question_text_template = (
                f"{question_text_template}\nGiven input: {input_fmt}"
            )
        return question_text_template

    def handle_generate_template(self, params: dict[str, Any]) -> dict[str, Any]:
        decoded_code, question_spec, execution_spec, generation_options = (
            self._build_specs(params)
        )

        preview_question = self._qg.generate_template_preview(
            code=decoded_code,
            question_spec=question_spec,
            generation_options=generation_options,
            execution_spec=execution_spec,
        )

        question_text_template: str | None = params.get("question_text_template")
        if question_text_template is None:
            func_params: list[str] = params.get("func_params", [])
            question_text_template = self._generate_question_text_template(
                question_spec, func_params
            )

        return {
            "preview_question": preview_question.model_dump(),
            "question_text_template": question_text_template,
            "func_params": params.get("func_params", []),
            "text_template_type": params["text_template_type"],
            "input_data": params["execution_spec"].get("input_data"),
            "question_spec": params["question_spec"],
            "code": decoded_code,
            "entry_function": params["execution_spec"]["entry_function"],
            "output_type": params["question_spec"]["output_type"],
            "num_distractors": params["generation_options"].get("num_distractors", 4),
        }

    def handle_question_from_template(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._build_question_from_template(params, params["input_data"])

    def handle_assessment_from_template(self, params: dict[str, Any]) -> dict[str, Any]:
        questions = []

        num_templates = len(params["question_templates"])
        num_inputs = len(params["question_inputs"])
        if num_templates != num_inputs:
            raise ValueError(f"expected {num_templates}, got {num_inputs}")

        for template, input_data in zip(
            params["question_templates"], params["question_inputs"], strict=True
        ):
            questions.append(
                {
                    **self._build_question_from_template(template, input_data),
                    "template_id": template["id"],
                }
            )

        return {
            "questions": questions,
            "user_id": params["user_id"],
            "assessment_metadata": params["assessment_metadata"],
        }
