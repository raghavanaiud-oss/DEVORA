import json
import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_llm_provider
from app.ai.rag import RAGService
from app.ai.review import CodeReviewService
from app.ai.test_gen import TestGenerationService
from app.models.activity import ActivityEvent, ActivityType
from app.models.ai import (
    AIRequest,
    AIRequestType,
    AIReviewItem,
    AIReviewStatus,
)
from app.repositories.activity_repo import ActivityRepository
from app.repositories.ai_repo import AIRepository
from app.repositories.file_repo import FileRepository
from app.schemas.ai import (
    AIReviewItemResponse,
    AIReviewResponse,
    AskProjectRequest,
    AskProjectResponse,
    CodeExplainRequest,
    CodeReviewCreate,
    ReviewItemActionRequest,
    SourceFileReference,
    TestGenRequest,
    TestGenResponse,
)


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_repo = AIRepository(db)
        self.file_repo = FileRepository(db)
        self.activity_repo = ActivityRepository(db)
        self.review_service = CodeReviewService(db)
        self.test_service = TestGenerationService(db)
        self.rag_service = RAGService(db)
        self.llm = get_llm_provider()

    async def explain_code(
        self, project_id: uuid.UUID, user_id: uuid.UUID, req: CodeExplainRequest
    ) -> str:
        file = await self.file_repo.get_by_path(project_id, req.file_path)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "FILE_NOT_FOUND", "message": f"File '{req.file_path}' not found."}},
            )

        code_to_explain = req.code_snippet or file.content or ""
        system_prompt = (
            "You are a Principal Software Architect. Provide a clear, structured, and insightful "
            "explanation of the provided code snippet. Detail the logic flow, key architectural patterns, "
            "and any non-obvious design decisions."
        )
        user_prompt = (
            f"File: {req.file_path}\n"
            f"Question: {req.question or 'Explain this code.'}\n\n"
            f"Code:\n```\n{code_to_explain}\n```"
        )

        explanation = await self.llm.generate_completion(system_prompt, user_prompt)

        # Record AI request
        await self.ai_repo.save_ai_request(
            AIRequest(
                project_id=project_id,
                user_id=user_id,
                request_type=AIRequestType.EXPLAIN,
                prompt=f"Explain {req.file_path}",
                response=explanation,
            )
        )

        return explanation

    async def create_review(
        self, project_id: uuid.UUID, user_id: uuid.UUID, req: CodeReviewCreate
    ) -> AIReviewResponse:
        # Determine file to review
        if req.file_path:
            file = await self.file_repo.get_by_path(project_id, req.file_path)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": {"code": "FILE_NOT_FOUND", "message": f"File '{req.file_path}' not found."}},
                )
        else:
            files = await self.file_repo.list_by_project(project_id)
            code_files = [f for f in files if not f.is_directory and f.content]
            if not code_files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": {"code": "NO_FILES_TO_REVIEW", "message": "No code files found in project to review."}},
                )
            file = code_files[0]

        review = await self.review_service.review_file(project_id, user_id, file)

        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=project_id,
                user_id=user_id,
                event_type=ActivityType.AI_REVIEW_CREATED,
                description=f"AI Code Review completed for {file.path}",
                event_metadata={"review_id": str(review.id), "file_path": file.path},
            )
        )

        return AIReviewResponse.model_validate(review)

    async def list_reviews(self, project_id: uuid.UUID) -> List[AIReviewResponse]:
        reviews = await self.ai_repo.list_reviews(project_id)
        return [AIReviewResponse.model_validate(r) for r in reviews]

    async def get_review(self, project_id: uuid.UUID, review_id: uuid.UUID) -> AIReviewResponse:
        review = await self.ai_repo.get_review(review_id)
        if not review or review.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "REVIEW_NOT_FOUND", "message": "AI Review not found."}},
            )
        return AIReviewResponse.model_validate(review)

    async def take_review_item_action(
        self,
        project_id: uuid.UUID,
        review_id: uuid.UUID,
        item_id: uuid.UUID,
        req: ReviewItemActionRequest,
    ) -> AIReviewItemResponse:
        review = await self.ai_repo.get_review(review_id)
        if not review or review.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "REVIEW_NOT_FOUND", "message": "Review not found."}},
            )

        item = await self.ai_repo.get_review_item(item_id)
        if not item or item.review_id != review_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "ITEM_NOT_FOUND", "message": "Review item not found."}},
            )

        status_mapping = {
            "ACCEPT": AIReviewStatus.ACCEPTED,
            "REJECT": AIReviewStatus.REJECTED,
            "DISMISS": AIReviewStatus.DISMISSED,
        }
        target_status = status_mapping.get(req.action.upper(), AIReviewStatus.ACCEPTED)
        updated_item = await self.ai_repo.update_review_item_status(item, target_status)
        return AIReviewItemResponse.model_validate(updated_item)

    async def generate_tests(
        self, project_id: uuid.UUID, user_id: uuid.UUID, req: TestGenRequest
    ) -> TestGenResponse:
        file = await self.file_repo.get_by_path(project_id, req.file_path)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "FILE_NOT_FOUND", "message": f"File '{req.file_path}' not found."}},
            )

        test_response = await self.test_service.generate_tests(
            project_id=project_id,
            file=file,
            function_name=req.function_name,
            code_snippet=req.code_snippet,
        )

        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=project_id,
                user_id=user_id,
                event_type=ActivityType.AI_TEST_GENERATED,
                description=f"Generated unit tests for {file.path}",
                event_metadata={"test_file_path": test_response.test_file_path},
            )
        )

        return test_response

    async def ask_project(
        self, project_id: uuid.UUID, user_id: uuid.UUID, req: AskProjectRequest
    ) -> AskProjectResponse:
        # Retrieve relevant contexts using RAG
        contexts = await self.rag_service.retrieve_relevant_context(project_id, req.query, limit=5)
        context_str = "\n---\n".join([f"File: {c['path']}\n{c['content']}" for c in contexts])

        system_prompt = (
            "You are CodeOrbit AI, an expert software engineer with deep understanding of this repository. "
            "Answer the user's question accurately using the provided project files. "
            "Cite relevant file paths and offer concrete next steps."
        )
        user_prompt = (
            f"User Question: {req.query}\n"
            f"Active File: {req.active_file or 'None'}\n\n"
            f"Project Code Context:\n{context_str or 'No indexed documents found.'}"
        )

        answer = await self.llm.generate_completion(system_prompt, user_prompt)

        source_files = [
            SourceFileReference(
                path=c["path"],
                line_start=1,
                line_end=len(c["content"].splitlines()),
                snippet=c["content"][:200],
                relevance_score=c.get("score", 0.9),
            )
            for c in contexts
        ]

        suggested_actions = [
            "Run unit tests to verify behavior",
            "Generate automated code review on related files",
            "Explore symbol references across the workspace",
        ]

        return AskProjectResponse(
            answer=answer,
            source_files=source_files,
            suggested_actions=suggested_actions,
        )
