from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    Question,
    QuestionSpec,
)
from edcraft_engine.question_generator.question_generator import QuestionGenerator


class QuestionGenerationService:
    def __init__(self) -> None:
        self.question_generator = QuestionGenerator()

    def generate_question(
        self,
        code: str,
        question_spec: QuestionSpec,
        execution_spec: ExecutionSpec,
        generation_options: GenerationOptions,
    ) -> Question:

        return self.question_generator.generate_question(
            code=code,
            question_spec=question_spec,
            execution_spec=execution_spec,
            generation_options=generation_options,
        )
