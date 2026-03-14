import os
from pgvector.psycopg2 import register_vector
from api.db import get_connection

def _get_embeddings_model():
    provider = (os.environ.get("EMBEDDING_PROVIDER") or os.environ.get("LLM_PROVIDER") or "openai").strip().lower()
    if provider == "gemini" and os.environ.get("GOOGLE_API_KEY"):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore[reportMissingImports]
        # 1536 to match pgvector column (same as OpenAI text-embedding-3-small)
        # gemini-embedding-2 supports output_dimensionality 768, 1536, 3072
        # text-embedding-004 is deprecated; use Gemini embedding (supports 768, 1536, 3072)
        return GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-2-preview",
            output_dimensionality=1536,
        )
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model="text-embedding-3-small")

embeddings_model = _get_embeddings_model()

def embed_reviews(asin: str, reviews: list[str], timestamp: str):
    """
    Generates embeddings for reviews using OpenAI and stores them in Neon DB (pgvector).
    """
    if not reviews:
        return
    
    # Generate embeddings via OpenAI API
    # langchain handles batching automatically
    embeddings = embeddings_model.embed_documents(reviews)
    
    conn = get_connection()
    # Register the vector type with psycopg2
    register_vector(conn)
    cursor = conn.cursor()
    
    for review, embedding in zip(reviews, embeddings):
        cursor.execute(
            """
            INSERT INTO review_embeddings (asin, document, metadata, embedding)
            VALUES (%s, %s, %s, %s)
            """,
            (asin, review, '{"source": "amazon"}', embedding)
        )
        
    conn.commit()
    conn.close()

def list_embeddings(asin: str | None = None, limit: int = 500):
    """
    List stored review embeddings from pgvector (for inspection).
    Returns id, asin, document (review text), metadata, created_at; no raw vector.
    """
    conn = get_connection()
    register_vector(conn)
    cursor = conn.cursor()
    if asin:
        cursor.execute(
            """
            SELECT id, asin, document, metadata, created_at
            FROM review_embeddings
            WHERE asin = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (asin, limit),
        )
    else:
        cursor.execute(
            """
            SELECT id, asin, document, metadata, created_at
            FROM review_embeddings
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "asin": r[1],
            "document": r[2],
            "metadata": r[3],
            "created_at": str(r[4]) if r[4] else None,
        }
        for r in rows
    ]


def search_reviews(query: str, asin: str, n_results: int = 15):
    """
    Performs a semantic similarity search using pgvector's cosine distance operator (<=>).
    Returns a dictionary structured similarly to Chroma for backward compatibility in nodes.py.
    """
    # 1. Embed the search query
    query_embedding = embeddings_model.embed_query(query)
    
    conn = get_connection()
    register_vector(conn)
    cursor = conn.cursor()
    
    # 2. Query Neon DB for the closest vectors using cosine distance operator (<=>)
    # The smaller the resulting distance, the more similar the vectors.
    cursor.execute(
        """
        SELECT document, metadata, id, (embedding <=> %s::vector) AS distance
        FROM review_embeddings
        WHERE asin = %s
        ORDER BY distance ASC
        LIMIT %s
        """,
        (query_embedding, asin, n_results)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    # 3. Format results to match the expected interface in `detective_node`
    # Chroma returns lists of lists.
    documents = []
    metadatas = []
    ids = []
    distances = []
    
    for row in rows:
        documents.append(row[0])  # document
        metadatas.append(row[1])  # metadata JSONB
        ids.append(str(row[2]))   # id
        distances.append(row[3])  # distance
        
    return {
        "documents": [documents],
        "metadatas": [metadatas],
        "ids": [ids],
        "distances": [distances]
    }
