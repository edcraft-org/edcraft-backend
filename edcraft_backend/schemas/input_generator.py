"""Schemas for input generator endpoints."""

from typing import Any

from pydantic import BaseModel


class GenerateInputsRequest(BaseModel):
    inputs: dict[str, dict]  # variable name -> JSON Schema


class GenerateInputsResponse(BaseModel):
    inputs: dict[str, Any]  # variable name -> generated value
