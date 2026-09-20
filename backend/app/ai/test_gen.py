import difflib
import os
import re
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.ai.provider import get_llm_provider
from backend.app.ai.rag import RAGService
from backend.app.models.workspace_file import WorkspaceFile
from backend.app.schemas.ai import TestGenResponse


class TestGenerationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rag_service = RAGService(db)
        self.llm = get_llm_provider()

    async def generate_tests(
        self,
        project_id: uuid.UUID,
        file: WorkspaceFile,
        function_name: Optional[str] = None,
        code_snippet: Optional[str] = None,
    ) -> TestGenResponse:
        # Determine test filename and test framework
        base_name = os.path.basename(file.path)
        name_no_ext, ext = os.path.splitext(base_name)

        if ext == ".py":
            test_path = f"/tests/test_{name_no_ext}.py"
            framework = "pytest"
        elif ext in [".ts", ".tsx", ".js", ".jsx"]:
            test_path = f"/tests/{name_no_ext}.test{ext}"
            framework = "vitest/jest"
        else:
            test_path = f"/tests/{name_no_ext}.test{ext}"
            framework = "standard unit test"

        # Context retrieval
        query = f"test {function_name or name_no_ext} dependencies and usage"
        contexts = await self.rag_service.retrieve_relevant_context(project_id, query, limit=3)
        context_str = "\n---\n".join([f"// {c['path']}\n{c['content']}" for c in contexts])

        target_code = code_snippet or file.content

        system_prompt = f"""You are a Test Automation Architect.
Generate a comprehensive, production-ready test suite using {framework}.
Include:
1. Happy path tests with assertions
2. Boundary and edge-case tests
3. Exception and error handling tests
4. Necessary mocks and fixtures

Output ONLY the executable test code wrapped in ```{file.language or 'python'} ... ```."""

        user_prompt = f"""Source File: {file.path}
Target Function/Code: {function_name or 'Entire Module'}

Related Project Context:
{context_str}

Source Code:
```
{target_code}
```"""

        raw_response = await self.llm.generate_completion(system_prompt, user_prompt)

        # Extract code from response
        code_match = re.search(r"```(?:\w+)?\n(.*?)```", raw_response, re.DOTALL)
        generated_code = code_match.group(1).strip() if code_match else raw_response.strip()

        # Compute unified diff
        diff_lines = list(
            difflib.unified_diff(
                "".splitlines(keepends=True),
                generated_code.splitlines(keepends=True),
                fromfile=f"a{test_path}",
                tofile=f"b{test_path}",
            )
        )
        diff_text = "".join(diff_lines)

        dependencies = ["pytest", "pytest-asyncio"] if ext == ".py" else ["@testing-library/react", "vitest"]

        return TestGenResponse(
            test_file_path=test_path,
            generated_code=generated_code,
            diff=diff_text,
            dependencies=dependencies,
            explanation=f"Generated {framework} test suite for `{function_name or base_name}` with mocks and edge-case coverage.",
        )
