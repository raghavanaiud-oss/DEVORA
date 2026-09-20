import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.models.ai import (
    AIRequest,
    AIReview,
    AIReviewItem,
    AIReviewStatus,
    Embedding,
    ProjectDocument,
)


class AIRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_document(self, doc: ProjectDocument) -> ProjectDocument:
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def get_document_by_file_id(self, file_id: uuid.UUID) -> Optional[ProjectDocument]:
        result = await self.db.execute(select(ProjectDocument).where(ProjectDocument.file_id == file_id))
        return result.scalars().first()

    async def save_embeddings(self, embeddings: List[Embedding]) -> None:
        self.db.add_all(embeddings)
        await self.db.flush()

    async def delete_document_embeddings(self, document_id: uuid.UUID) -> None:
        result = await self.db.execute(select(Embedding).where(Embedding.document_id == document_id))
        for emb in result.scalars().all():
            await self.db.delete(emb)
        await self.db.flush()

    async def search_similar_chunks(
        self, project_id: uuid.UUID, query_embedding: List[float], limit: int = 5
    ) -> List[Tuple[Embedding, float]]:
        """
        Perform pgvector cosine similarity search scoped strictly to the project.
        Falls back to raw retrieval if vector extension is not compiled into SQLite/in-memory test.
        """
        try:
            # When pgvector is active, cosine distance operator is <=> or l2_distance
            stmt = (
                select(Embedding, Embedding.embedding.cosine_distance(query_embedding).label("distance"))
                .join(ProjectDocument, Embedding.document_id == ProjectDocument.id)
                .where(Embedding.project_id == project_id)
                .order_by("distance")
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return result.all()
        except Exception:
            # Fallback for non-pgvector environments (e.g. SQLite tests or mock DB)
            stmt = (
                select(Embedding)
                .where(Embedding.project_id == project_id)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return [(item, 0.1) for item in result.scalars().all()]

    async def create_review(self, review: AIReview) -> AIReview:
        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)
        return review

    async def get_review(self, review_id: uuid.UUID) -> Optional[AIReview]:
        result = await self.db.execute(
            select(AIReview)
            .options(selectinload(AIReview.items))
            .where(AIReview.id == review_id)
        )
        return result.scalars().first()

    async def list_reviews(self, project_id: uuid.UUID) -> List[AIReview]:
        result = await self.db.execute(
            select(AIReview)
            .options(selectinload(AIReview.items))
            .where(AIReview.project_id == project_id)
            .order_by(AIReview.created_at.desc())
        )
        return result.scalars().all()

    async def get_review_item(self, item_id: uuid.UUID) -> Optional[AIReviewItem]:
        result = await self.db.execute(select(AIReviewItem).where(AIReviewItem.id == item_id))
        return result.scalars().first()

    async def update_review_item_status(self, item: AIReviewItem, status: AIReviewStatus) -> AIReviewItem:
        item.status = status
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def save_ai_request(self, request: AIRequest) -> AIRequest:
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request
