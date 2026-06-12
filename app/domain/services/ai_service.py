import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY,
        )
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.0,
            api_key=settings.OPENAI_API_KEY,
        )

    async def query_vendor_evidence(
        self,
        tenant_id: str,
        vendor_id: str,
        question: str,
    ) -> dict:
        """
        RAG pipeline:
        1. Embed the question
        2. Vector similarity search against pgvector (HNSW cosine)
        3. Feed top-5 chunks + question to GPT-4o
        4. Return answer with page citations
        """

        # 1. Embed the question
        query_vector = self.embeddings.embed_query(question)
        vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"

        # 2. pgvector cosine similarity search
        # <=> is cosine distance; lower = more similar
        stmt = text("""
            SELECT
                c.content_payload,
                c.page_number,
                e.file_name,
                1 - (c.embedding_vector <=> :vector::vector) AS similarity
            FROM document_chunks c
            JOIN evidence_documents e ON c.evidence_document_id = e.id
            WHERE c.tenant_id = :tenant_id
              AND e.vendor_id = :vendor_id
              AND e.processing_status = 'COMPLETED'
            ORDER BY c.embedding_vector <=> :vector::vector
            LIMIT 5
        """)

        result = await self.session.execute(
            stmt,
            {
                "vector": vector_str,
                "tenant_id": tenant_id,
                "vendor_id": vendor_id,
            },
        )
        chunks = result.fetchall()

        if not chunks:
            return {
                "answer": "No processed evidence documents found for this vendor.",
                "citations": [],
            }

        # 3. Build context string for the LLM
        context_text = "\n\n---\n\n".join([
            f"Source: {c.file_name} (Page {c.page_number})\n"
            f"Relevance: {round(c.similarity, 2)}\n"
            f"Content: {c.content_payload}"
            for c in chunks
        ])

        # 4. GRC-tuned prompt
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert GRC (Governance, Risk, and Compliance) Security Analyst. "
                "Your job is to analyze vendor evidence documents and answer compliance questions. "
                "Rules:\n"
                "- Answer ONLY based on the provided context.\n"
                "- If the context does not contain the answer, explicitly state: 'Evidence not provided in uploaded documents.'\n"
                "- Always cite the exact Source File and Page Number for every claim.\n"
                "- Be concise and precise. This is a compliance assessment, not a conversation.",
            ),
            (
                "human",
                "Evidence Context:\n{context}\n\nCompliance Question: {question}",
            ),
        ])

        chain = prompt | self.llm
        ai_response = chain.invoke({
            "context": context_text,
            "question": question,
        })

        logger.info(
            f"RAG query completed for vendor {vendor_id}",
            extra={"tenant_id": tenant_id, "question": question[:50]},
        )

        return {
            "answer": ai_response.content,
            "citations": [
                {
                    "file": c.file_name,
                    "page": c.page_number,
                    "relevance_score": round(c.similarity, 2),
                }
                for c in chunks
            ],
        }