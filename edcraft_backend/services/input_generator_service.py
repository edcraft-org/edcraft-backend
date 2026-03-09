"""Service for generating inputs from JSON Schema definitions."""

from typing import Any

from input_gen import generate


class InputGeneratorService:
    def generate_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Generate a value for each variable using its JSON Schema definition."""
        return {var: generate(schema) for var, schema in inputs.items()}
