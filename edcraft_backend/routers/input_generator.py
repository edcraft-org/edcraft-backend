"""Input generator endpoints."""

from fastapi import APIRouter, Depends

from edcraft_backend.exceptions import InputGenerationError
from edcraft_backend.schemas.input_generator import (
    GenerateInputsRequest,
    GenerateInputsResponse,
)
from edcraft_backend.services.input_generator_service import InputGeneratorService

router = APIRouter(prefix="/input-generator", tags=["input-generator"])


@router.post("/generate", response_model=GenerateInputsResponse)
async def generate_inputs(
    request: GenerateInputsRequest,
    service: InputGeneratorService = Depends(InputGeneratorService),
) -> GenerateInputsResponse:
    """Generate values for each variable based on its JSON Schema definition."""
    try:
        result = service.generate_inputs(request.inputs)
        return GenerateInputsResponse(inputs=result)
    except Exception as e:
        raise InputGenerationError(f"Input generation failed: {str(e)}") from e
