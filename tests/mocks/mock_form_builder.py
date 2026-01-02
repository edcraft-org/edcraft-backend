"""Mock FormBuilderService for testing."""

from edcraft_backend.schemas.form_builder import FormElement, FormOption


class MockFormBuilderService:
    """
    Mock for FormBuilderService that returns predictable form schema.

    This mock replaces the actual form builder service
    with deterministic responses for testing purposes.
    """

    def build_form_elements(self) -> list[FormElement]:
        """
        Build mock form elements schema.

        Returns:
            List of FormElement objects
        """
        # Return predictable form schema
        return [
            FormElement(
                element_type="target_selector",
                label="Target Element",
                description="Select the type of code element you want to target.",
                options=[
                    FormOption(
                        id="function",
                        label="Function",
                        value="function",
                        description="Select function from the code.",
                        depends_on=None,
                    ),
                    FormOption(
                        id="loop",
                        label="Loop",
                        value="loop",
                        description="Select loop from the code.",
                        depends_on=None,
                    ),
                    FormOption(
                        id="branch",
                        label="Branch",
                        value="branch",
                        description="Select branch from the code.",
                        depends_on=None,
                    ),
                    FormOption(
                        id="variable",
                        label="Variable",
                        value="variable",
                        description="Select variable from the code.",
                        depends_on=None,
                    ),
                ],
                is_required=False,
            ),
            FormElement(
                element_type="output_type_selector",
                label="Output Type",
                description="Select the type of output you want.",
                options=[
                    FormOption(
                        id="list",
                        label="List",
                        value="list",
                        description="Return a list of all matching elements.",
                        depends_on=None,
                    ),
                    FormOption(
                        id="count",
                        label="Count",
                        value="count",
                        description="Return the count of matching elements.",
                        depends_on=None,
                    ),
                    FormOption(
                        id="first",
                        label="First",
                        value="first",
                        description="Return the first matching element.",
                        depends_on=None,
                    ),
                    FormOption(
                        id="last",
                        label="Last",
                        value="last",
                        description="Return the last matching element.",
                        depends_on=None,
                    ),
                ],
                is_required=True,
            ),
            FormElement(
                element_type="question_type_selector",
                label="Question Type",
                description="Select the type of question you want to create.",
                options=[
                    FormOption(
                        id="mcq",
                        label="Multiple Choice Question",
                        value="mcq",
                        description="Select this for multiple choice questions.",
                        depends_on=None,
                    ),
                    FormOption(
                        id="mrq",
                        label="Multiple Response Question",
                        value="mrq",
                        description="Select this for multiple response questions.",
                        depends_on=None,
                    ),
                    FormOption(
                        id="short_answer",
                        label="Short Answer",
                        value="short_answer",
                        description="Select this for short answer questions.",
                        depends_on=None,
                    ),
                ],
                is_required=True,
            ),
        ]
