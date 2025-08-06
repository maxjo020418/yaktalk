import ollama
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json


class OllamaInMemoryVectorDB:
    def __init__(self, model_name: str = "qwen3:14b"):
        """
        Initialize in-memory vector database using Ollama embeddings
        
        Args:
            model_name: Ollama model name for embeddings
        """
        self.model_name = model_name
        self.embeddings = []
        self.documents = []
        self.metadata = []
        
    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for given text using Ollama
        
        Args:
            text: Input text to embed
            
        Returns:
            List of float values representing the embedding
        """
        response = ollama.embeddings(
            model=self.model_name,
            prompt=text
        )
        return response['embedding']
    
    def add_documents(self, documents: List[str], metadata: Optional[List[Dict[str, Any]]] = None):
        """
        Add documents to the vector database
        
        Args:
            documents: List of text documents
            metadata: Optional metadata for each document
        """
        if metadata and len(metadata) != len(documents):
            raise ValueError("Metadata list must have same length as documents")
            
        for i, doc in enumerate(documents):
            embedding = self._get_embedding(doc)
            self.embeddings.append(embedding)
            self.documents.append(doc)
            
            if metadata:
                self.metadata.append(metadata[i])
            else:
                self.metadata.append({"index": len(self.documents) - 1})
                
        print(f"Added {len(documents)} documents to the database")
        
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar documents using cosine similarity
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            
        Returns:
            List of dictionaries containing document, score, and metadata
        """
        if not self.embeddings:
            return []
            
        query_embedding = self._get_embedding(query)
        query_vector = np.array(query_embedding).reshape(1, -1)
        
        embeddings_matrix = np.array(self.embeddings)
        
        similarities = cosine_similarity(query_vector, embeddings_matrix)[0]
        
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "document": self.documents[idx],
                "score": similarities[idx],
                "metadata": self.metadata[idx]
            })
            
        return results
    
    def save_to_file(self, filepath: str):
        """
        Save the vector database to a file
        
        Args:
            filepath: Path to save the database
        """
        data = {
            "model_name": self.model_name,
            "embeddings": self.embeddings,
            "documents": self.documents,
            "metadata": self.metadata
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"Saved database to {filepath}")
        
    def load_from_file(self, filepath: str):
        """
        Load the vector database from a file
        
        Args:
            filepath: Path to load the database from
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.model_name = data["model_name"]
        self.embeddings = data["embeddings"]
        self.documents = data["documents"]
        self.metadata = data["metadata"]
        
        print(f"Loaded {len(self.documents)} documents from {filepath}")
        
    def clear(self):
        """Clear all data from the database"""
        self.embeddings = []
        self.documents = []
        self.metadata = []
        print("Database cleared")
        
    def get_size(self) -> int:
        """Get the number of documents in the database"""
        return len(self.documents)