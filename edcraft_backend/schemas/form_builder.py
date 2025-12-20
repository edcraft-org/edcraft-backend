from typing import Any

from pydantic import BaseModel, Field


class FormOption(BaseModel):
    """A form option with its details."""

    id: str = Field(..., description="Unique identifier for the form option.")
    label: str = Field(..., description="Display label")
    value: Any = Field(..., description="Option value")
    description: str = Field(..., description="Description of the form option.")
    depends_on: str | None = Field(
        default=None, description="Id of the option that this option depends on."
    )


class FormElement(BaseModel):
    """A form element with available options."""

    element_type: str = Field(..., description="Type of the form element")
    label: str = Field(..., description="Display label for this element")
    description: str | None = Field(None, description="Help text")
    options: list[FormOption] = Field(..., description="Available options")
    is_required: bool = Field(default=True, description="Whether selection is required")
