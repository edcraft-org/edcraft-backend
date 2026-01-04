"""Mock for QuestionGenerator in EdCraft Engine."""

from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    Question,
    QuestionSpec,
)


class MockQuestionGenerator:
    """
    Mock QuestionGenerator that returns predictable questions.

    This mock allows for:
    1. Default predictable behavior based on question_type
    2. Custom question injection for specific test scenarios

    Args:
        custom_questions: Optional dict mapping question_type to custom Question objects.
                         Useful for testing edge cases or specific scenarios.

    Example:
        # Default behavior
        mock_gen = MockQuestionGenerator()

        # Custom behavior for specific test
        custom_mcq = Question(text="Custom question?", ...)
        mock_gen = MockQuestionGenerator(custom_questions={"mcq": custom_mcq})
    """

    def __init__(self, custom_questions: dict[str, Question] | None = None) -> None:
        """
        Initialize mock question generator.

        Args:
            custom_questions: Optional dict mapping question_type to custom Question
        """
        self._custom_questions = custom_questions or {}

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
            code: The code to generate questions from (ignored in mock)
            question_spec: Specification for the question type and target
            execution_spec: Execution configuration (ignored in mock)
            generation_options: Generation options (ignored in mock)

        Returns:
            Question: A mock question object based on question_type
        """
        question_type = question_spec.question_type

        if question_type in self._custom_questions:
            return self._custom_questions[question_type]

        return self._get_default_question(question_type)

    def _get_default_question(self, question_type: str) -> Question:
        """
        Get default mock question for a given question type.

        Args:
            question_type: The type of question (mcq, mrq, short_answer, etc.)

        Returns:
            Question: A default mock question for the specified type
        """
        if question_type == "mcq":
            return self._get_mock_mcq()
        elif question_type == "mrq":
            return self._get_mock_mrq()
        elif question_type == "short_answer":
            return self._get_mock_short_answer()
        else:
            # Default to MCQ for unknown types
            return self._get_mock_mcq()

    def _get_mock_mcq(self) -> Question:
        return Question(
            text="What is the output of this code?",
            answer="Option A",
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_indices=[0],
            question_type="mcq",
        )

    def _get_mock_mrq(self) -> Question:
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

    def _get_mock_short_answer(self) -> Question:
        return Question(
            text="What is the purpose of this code?",
            question_type="short_answer",
            answer="To sort an array using bubble sort.",
            options=None,
            correct_indices=None,
        )
