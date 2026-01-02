"""Integration tests for Question Generation API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.question_generation
class TestAnalyseCode:
    """Tests for POST /question-generation/analyse-code endpoint."""

    @pytest.mark.asyncio
    async def test_analyse_code_success(self, test_client: AsyncClient) -> None:
        """Test code analysis successfully returns code info and form schema."""
        code_data = {
            "code": "def hello():\\n    print('Hello World')",
        }
        response = await test_client.post("/question-generation/analyse-code", json=code_data)

        assert response.status_code == 200
        data = response.json()
        assert "code_info" in data
        assert "form_elements" in data
        # Verify code_info structure
        assert "code_tree" in data["code_info"]
        assert "functions" in data["code_info"]
        assert "loops" in data["code_info"]
        assert "branches" in data["code_info"]
        assert "variables" in data["code_info"]

    @pytest.mark.asyncio
    async def test_analyse_code_empty_code(self, test_client: AsyncClient) -> None:
        """Test code analysis with empty code."""
        code_data = {"code": ""}
        response = await test_client.post("/question-generation/analyse-code", json=code_data)

        assert response.status_code == 200
        data = response.json()
        # Empty code should still return valid structure
        assert "code_info" in data
        assert "form_elements" in data
        # Verify code_info structure
        assert "code_tree" in data["code_info"]
        assert "functions" in data["code_info"]
        assert "loops" in data["code_info"]
        assert "branches" in data["code_info"]
        assert "variables" in data["code_info"]

    @pytest.mark.asyncio
    async def test_analyse_code_with_invalid_encoding(self, test_client: AsyncClient) -> None:
        """Test that invalid code encoding raises appropriate error."""
        code_data = {
            "code": "\\x",  # Invalid escape sequence
        }

        response = await test_client.post("/question-generation/analyse-code", json=code_data)

        assert response.status_code == 400
        assert "Invalid code format" in response.json()["detail"]
