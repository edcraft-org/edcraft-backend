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

        assert response.status_code == 202
        job_id = response.json()["job_id"]

        result_resp = await test_client.get(f"/jobs/{job_id}")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"] == "completed"
        inputs = data["result"]["inputs"]
        assert "num" in inputs
        assert isinstance(inputs["num"], int)
        assert 1 <= inputs["num"] <= 50

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

        assert response.status_code == 202
        job_id = response.json()["job_id"]

        result_resp = await test_client.get(f"/jobs/{job_id}")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"] == "completed"
        inputs = data["result"]["inputs"]
        assert "count" in inputs
        assert "flag" in inputs
        assert isinstance(inputs["count"], int)
        assert 0 <= inputs["count"] <= 100
        assert isinstance(inputs["flag"], bool)

    @pytest.mark.asyncio
    async def test_generate_inputs_invalid_schema(
        self, test_client: AsyncClient
    ) -> None:
        """Test that an unknown schema type is accepted as a job and processed."""
        response = await test_client.post(
            "/input-generator/generate",
            json={"inputs": {"num": {"type": "invalid_type"}}},
        )

        assert response.status_code == 202
        job_id = response.json()["job_id"]

        result_resp = await test_client.get(f"/jobs/{job_id}")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"] in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_generate_inputs_empty_inputs(
        self, test_client: AsyncClient
    ) -> None:
        """Test generating with empty inputs returns empty result."""
        response = await test_client.post(
            "/input-generator/generate",
            json={"inputs": {}},
        )

        assert response.status_code == 202
        job_id = response.json()["job_id"]

        result_resp = await test_client.get(f"/jobs/{job_id}")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"] == "completed"
        assert data["result"]["inputs"] == {}
