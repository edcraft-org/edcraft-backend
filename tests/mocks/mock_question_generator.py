"""Mock QuestionGenerationService for testing."""

from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    Question,
    QuestionSpec,
)


class MockQuestionGenerationService:
    """
    Mock for QuestionGenerationService that returns predictable questions.

    This mock replaces the actual question generation service
    with deterministic responses for testing purposes.
    """

    def generate_question(
        self,
        code: str,
        question_spec: QuestionSpec,
        execution_spec: ExecutionSpec,
        generation_options: GenerationOptions,
    ) -> Question:
        """
        Generate a mock question based on question_spec.question_type.

        Args:
            code: Code to generate question from (not used in mock)
            question_spec: Specification for the question
            execution_spec: Execution specification (not used in mock)
            generation_options: Generation options (not used in mock)

        Returns:
            Mock Question object with predictable data
        """
        question_type = question_spec.question_type

        if question_type == "mcq":
            return self._generate_mock_mcq()
        elif question_type == "mrq":
            return self._generate_mock_mrq()
        elif question_type == "short_answer":
            return self._generate_mock_short_answer()
        else:
            # Default to MCQ for unknown types
            return self._generate_mock_mcq()

    def _generate_mock_mcq(self) -> Question:
        """Generate a mock multiple-choice question."""
        return Question(
            text="What is the output of this code?",
            answer="Option A",
            options=[
                "Option A",
                "Option B",
                "Option C",
                "Option D",
            ],
            correct_indices=[0],
            question_type="mcq",
        )

    def _generate_mock_mrq(self) -> Question:
        """Generate a mock multiple-response question."""
        return Question(
            text="Which statements are true about this code?",
            answer=["Statement A", "Statement B"],
            options=[
                "Statement A",
                "Statement B",
                "Statement C",
                "Statement D",
                "Statement E",
            ],
            correct_indices=[0, 1],
            question_type="mrq",
        )

    def _generate_mock_short_answer(self) -> Question:
        """Generate a mock short answer question."""
        return Question(
            text="What is the purpose of this code?",
            question_type="short_answer",
            answer="To sort an array using bubble sort.",
            options=None,
            correct_indices=None,
        )
