"""Service for building form elements from configuration."""

import json
from pathlib import Path

from edcraft_backend.schemas.form_builder import FormElement, FormOption


class FormBuilderService:
    """Service to build form elements from JSON configuration."""

    def __init__(self) -> None:
        """Initialize the form builder service."""
        config_path = Path(__file__).parent.parent / "forms_config.json"
        with open(config_path) as f:
            self._config = json.load(f)

    def build_form_elements(self) -> list[FormElement]:
        """
        Build form elements from configuration.

        Returns:
            List of FormElement objects for the UI.
        """
        elements: list[FormElement] = []

        for element_config in self._config.values():
            options = [
                FormOption(**option_data) for option_data in element_config["options"]
            ]

            element = FormElement(
                element_type=element_config["element_type"],
                label=element_config["label"],
                description=element_config["description"],
                options=options,
                is_required=element_config["is_required"],
            )
            elements.append(element)

        return elements
