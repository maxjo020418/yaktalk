from langchain_core.tools import tool
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document

from langchain_ollama import OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

from utils.get_env import OLLAMA_SERVER_URL

async def db_init(pdf_file_path: str, embed_model: str = 'llama3.1:8b') -> InMemoryVectorStore:
    """Initializes the vector store for the provided PDF file."""
    embeddings = OllamaEmbeddings(
        base_url=OLLAMA_SERVER_URL,
        model=embed_model,
    )
    loader = PyMuPDFLoader(pdf_file_path)
    pages = []
    for page in loader.load():
        pages.append(page)

    return InMemoryVectorStore.from_documents(pages, embeddings)

