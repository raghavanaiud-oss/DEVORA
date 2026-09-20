import json
import pytest
from backend.app.ai.provider import CodeOrbitEngine
from backend.app.ai.rag import CodeChunker


@pytest.mark.asyncio
async def test_codeorbit_engine_review():
    engine = CodeOrbitEngine()
    response = await engine.generate_completion(
        system_prompt="Review code",
        user_prompt="Review this security and performance in my code",
    )
    assert response is not None
    data = json.loads(response)
    assert "summary" in data
    assert "items" in data
    assert len(data["items"]) > 0
    assert "severity" in data["items"][0]
    assert "suggested_code" in data["items"][0]


@pytest.mark.asyncio
async def test_codeorbit_engine_test_generation():
    engine = CodeOrbitEngine()
    response = await engine.generate_completion(
        system_prompt="Generate tests",
        user_prompt="Generate pytest tests for this function",
    )
    assert "def test_" in response
    assert "pytest" in response


@pytest.mark.asyncio
async def test_codeorbit_engine_explain():
    engine = CodeOrbitEngine()
    response = await engine.generate_completion(
        system_prompt="Explain code",
        user_prompt="Explain how this module operates",
    )
    assert "Architecture" in response or "Flow" in response


def test_code_chunker():
    content = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    chunks = CodeChunker.chunk_content(content, max_chunk_size=15, overlap=5)
    assert len(chunks) >= 2
    assert "line 1" in chunks[0]
