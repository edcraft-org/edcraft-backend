"""Utilities for rendering question text templates."""

from typing import Any

import pymustache

from edcraft_backend.exceptions import TemplateRenderError
from edcraft_backend.models.enums import TextTemplateType


def render_question_text(
    template: str,
    template_type: TextTemplateType,
    input_data: dict[str, Any],
) -> str:
    """Render a question text template with the provided input data.

    Args:
        template: The template string to render
        template_type: The type of template
        input_data: The input data to substitute into the template

    Returns:
        Rendered question text string

    Raises:
        TemplateRenderError: If rendering fails
    """
    if template_type == TextTemplateType.BASIC:
        try:
            return template.format_map(input_data)
        except (KeyError, ValueError) as e:
            raise TemplateRenderError(f"Template rendering failed: {e}") from e
    elif template_type == TextTemplateType.MUSTACHE:
        try:
            return pymustache.render(template, input_data)
        except Exception as e:
            raise TemplateRenderError(f"Mustache template rendering failed: {e}") from e
    else:
        raise TemplateRenderError(f"Unknown template type: {template_type}")
