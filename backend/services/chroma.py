"""
ChromaDB service for vector storage and similarity search
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional, Any
from backend.config import settings
from backend.services.embeddings import generate_embedding, batch_embed
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Global ChromaDB client
_chroma_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """
    Get or create ChromaDB persistent client
    """
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        logger.info(f"ChromaDB client initialized at {settings.CHROMA_PERSIST_DIR}")
    return _chroma_client


def init_chroma() -> chromadb.Collection:
    """
    Initialize ChromaDB collection for SIS knowledge base
    
    Returns:
        ChromaDB Collection object
    """
    global _collection
    
    if _collection is not None:
        return _collection
    
    client = get_chroma_client()
    
    try:
        # Get or create collection
        _collection = client.get_or_create_collection(
            name="sis_knowledge_base",
            metadata={"description": "SIS Officer knowledge base for RAG"}
        )
        logger.info(f"Collection 'sis_knowledge_base' initialized with {_collection.count()} documents")
        return _collection
    except Exception as e:
        logger.error(f"Error initializing ChromaDB collection: {e}")
        raise


def add_documents(docs: List[Dict[str, Any]]) -> None:
    """
    Add documents to ChromaDB collection
    
    Args:
        docs: List of documents with structure:
            {
                "id": str,
                "content": str,
                "metadata": dict (document_name, section, category, source, language, page_number)
            }
    """
    collection = init_chroma()
    
    if not docs:
        logger.warning("No documents to add")
        return
    
    try:
        # Extract components
        ids = [doc["id"] for doc in docs]
        contents = [doc["content"] for doc in docs]
        metadatas = [doc["metadata"] for doc in docs]
        
        # Generate embeddings in batch
        logger.info(f"Generating embeddings for {len(contents)} documents...")
        embeddings = batch_embed(contents)
        
        # Add to collection
        collection.add(
            ids=ids,
            documents=contents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        logger.info(f"Successfully added {len(docs)} documents to ChromaDB")
    except Exception as e:
        logger.error(f"Error adding documents to ChromaDB: {e}")
        raise


def similarity_search(
    query: str,
    n_results: int = 5,
    where_filter: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Perform similarity search on ChromaDB
    
    Args:
        query: Search query text
        n_results: Number of results to return
        where_filter: Optional metadata filter (e.g., {"language": "en"})
        
    Returns:
        List of documents with content, metadata, and distance
    """
    collection = init_chroma()
    
    try:
        # Generate query embedding
        query_embedding = generate_embedding(query)
        
        # Perform search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })
        
        logger.info(f"Similarity search returned {len(formatted_results)} results")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error in similarity search: {e}")
        raise


def delete_collection() -> None:
    """
    Delete the ChromaDB collection (use with caution)
    """
    global _collection
    client = get_chroma_client()
    
    try:
        client.delete_collection(name="sis_knowledge_base")
        _collection = None
        logger.warning("ChromaDB collection 'sis_knowledge_base' deleted")
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise


def get_collection_stats() -> Dict[str, Any]:
    """
    Get statistics about the ChromaDB collection
    
    Returns:
        Dictionary with collection statistics
    """
    collection = init_chroma()
    
    try:
        count = collection.count()
        return {
            "collection_name": "sis_knowledge_base",
            "document_count": count,
            "status": "initialized" if count > 0 else "empty"
        }
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        return {
            "collection_name": "sis_knowledge_base",
            "document_count": 0,
            "status": "error",
            "error": str(e)
        }
