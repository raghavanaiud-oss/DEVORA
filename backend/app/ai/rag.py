import re
import uuid
from typing import Any, Dict, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.ai.embeddings import embedding_generator
from backend.app.models.ai import Embedding, ProjectDocument
from backend.app.models.workspace_file import WorkspaceFile
from backend.app.repositories.ai_repo import AIRepository


class CodeChunker:
    """Chunks source code and markdown into semantically coherent blocks."""

    @staticmethod
    def chunk_content(content: str, max_chunk_size: int = 800, overlap: int = 150) -> List[str]:
        if not content.strip():
            return []

        lines = content.splitlines(keepends=True)
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line)
            if current_size + line_size > max_chunk_size and current_chunk:
                chunks.append("".join(current_chunk))
                # Retain last few lines for overlap context
                overlap_chunk = []
                overlap_size = 0
                for prev_line in reversed(current_chunk):
                    if overlap_size + len(prev_line) <= overlap:
                        overlap_chunk.insert(0, prev_line)
                        overlap_size += len(prev_line)
                    else:
                        break
                current_chunk = overlap_chunk
                current_size = overlap_size

            current_chunk.append(line)
            current_size += line_size

        if current_chunk:
            chunks.append("".join(current_chunk))

        return chunks


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_repo = AIRepository(db)

    async def index_file(self, project_id: uuid.UUID, file: WorkspaceFile) -> None:
        """Chunk a workspace file, generate embeddings, and store in pgvector."""
        if file.is_directory or not file.content:
            return

        # Check existing document
        existing_doc = await self.ai_repo.get_document_by_file_id(file.id)
        if existing_doc:
            if existing_doc.content_hash == file.content_hash:
                return  # Content has not changed
            await self.ai_repo.delete_document_embeddings(existing_doc.id)
            existing_doc.content = file.content
            existing_doc.content_hash = file.content_hash or ""
            doc = existing_doc
        else:
            doc = ProjectDocument(
                project_id=project_id,
                file_id=file.id,
                path=file.path,
                language=file.language,
                content=file.content,
                content_hash=file.content_hash or "",
                doc_type="CODE" if not file.path.endswith(".md") else "DOCS",
            )
            doc = await self.ai_repo.save_document(doc)

        # Generate chunks and embeddings
        chunks = CodeChunker.chunk_content(file.content)
        embeddings_to_save = []

        for idx, chunk in enumerate(chunks):
            vector = await embedding_generator.generate_embedding(chunk)
            emb = Embedding(
                project_id=project_id,
                document_id=doc.id,
                chunk_index=idx,
                chunk_content=chunk,
                embedding=vector,
            )
            embeddings_to_save.append(emb)

        if embeddings_to_save:
            await self.ai_repo.save_embeddings(embeddings_to_save)

    async def retrieve_relevant_context(
        self, project_id: uuid.UUID, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve most relevant chunks for a project query with strict project scoping."""
        query_vector = await embedding_generator.generate_embedding(query)
        results = await self.ai_repo.search_similar_chunks(project_id, query_vector, limit=limit)

        contexts = []
        for emb, score in results:
            doc = emb.document if hasattr(emb, "document") and emb.document else None
            path = doc.path if doc else "unknown"
            contexts.append({
                "path": path,
                "content": emb.chunk_content,
                "chunk_index": emb.chunk_index,
                "score": float(score),
            })
        return contexts
