"""
Local and Ollama embedding utilities
"""

from typing import List
from langchain_community.embeddings import OllamaEmbeddings
from sentence_transformers import SentenceTransformer
from langchain_core.embeddings import Embeddings

class LocalEmbeddings(Embeddings):
    """Local embeddings using sentence-transformers for PDF processing"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents locally"""
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query text locally"""
        embedding = self.model.encode([text], convert_to_tensor=False)
        return embedding[0].tolist()

class SafeOllamaEmbeddings(OllamaEmbeddings):
    """Safe Ollama embeddings with single document processing"""
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Process documents one by one to avoid batch issues"""
        embeddings = []
        for i, text in enumerate(texts):
            try:
                # Process one document at a time
                embedding = super().embed_documents([text])
                embeddings.extend(embedding)
                if i % 10 == 0 and i > 0:
                    print(f"Processed {i}/{len(texts)} documents")
            except Exception as e:
                print(f"Error embedding document {i}: {e}")
                # Skip failed embeddings or use zero vector
                if embeddings:
                    embeddings.append([0.0] * len(embeddings[0]))
                else:
                    embeddings.append([0.0] * 768)  # Default dimension
        return embeddings

def get_pdf_embeddings():
    """Get Ollama embeddings for PDF processing (using same model as law)"""
    from utils.get_env import OLLAMA_SERVER_URL
    server_url = OLLAMA_SERVER_URL
    
    # Handle missing URL scheme
    if not server_url.startswith(('http://', 'https://')):
        server_url = f"https://{server_url}"
    
    return SafeOllamaEmbeddings(
        base_url=server_url,
        model="nomic-embed-text"
    )

def get_law_embeddings(server_url: str, model_name: str):
    """Get Ollama embeddings for law processing"""
    # Handle missing URL scheme
    if not server_url.startswith(('http://', 'https://')):
        server_url = f"https://{server_url}"
    
    return SafeOllamaEmbeddings(
        base_url=server_url,
        model=model_name
    )