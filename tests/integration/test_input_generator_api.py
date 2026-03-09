"""Integration tests for Input Generator API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.input_generator
class TestGenerateInputs:
    """Tests for POST /input-generator/generate endpoint."""

    @pytest.mark.asyncio
    async def test_generate_inputs_single_variable(
        self, test_client: AsyncClient
    ) -> None:
        """Test generating a single integer variable."""
        response = await test_client.post(
            "/input-generator/generate",
            json={"inputs": {"num": {"type": "integer", "minimum": 1, "maximum": 50}}},
        )

        assert response.status_code == 200
        data = response.json()
        assert "inputs" in data
        assert "num" in data["inputs"]
        assert isinstance(data["inputs"]["num"], int)
        assert 1 <= data["inputs"]["num"] <= 50

    @pytest.mark.asyncio
    async def test_generate_inputs_multiple_variables(
        self, test_client: AsyncClient
    ) -> None:
        """Test generating multiple variables with different types."""
        response = await test_client.post(
            "/input-generator/generate",
            json={
                "inputs": {
                    "count": {"type": "integer", "minimum": 0, "maximum": 100},
                    "flag": {"type": "boolean"},
                }
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "inputs" in data
        assert "count" in data["inputs"]
        assert "flag" in data["inputs"]
        assert isinstance(data["inputs"]["count"], int)
        assert 0 <= data["inputs"]["count"] <= 100
        assert isinstance(data["inputs"]["flag"], bool)

    @pytest.mark.asyncio
    async def test_generate_inputs_invalid_schema(
        self, test_client: AsyncClient
    ) -> None:
        """Test that an invalid schema returns a 422 error."""
        response = await test_client.post(
            "/input-generator/generate",
            json={"inputs": {"num": {"type": "invalid_type"}}},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_inputs_empty_inputs(
        self, test_client: AsyncClient
    ) -> None:
        """Test generating with empty inputs returns empty result."""
        response = await test_client.post(
            "/input-generator/generate",
            json={"inputs": {}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["inputs"] == {}
