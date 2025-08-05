from langchain_core.tools import tool
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document

from langchain_ollama import OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

from utils.get_env import OLLAMA_SERVER_URL

import warnings


vector_store: InMemoryVectorStore | None = None


async def db_init(pdf_file_path: str, embed_model: str = "llama3.1:8b") -> None:
    """Initializes the vector store for the provided PDF file."""
    global vector_store
    embeddings = OllamaEmbeddings(
        base_url=OLLAMA_SERVER_URL,
        model=embed_model,
    )
    loader = PyMuPDFLoader(pdf_file_path)
    pages = [page for page in loader.load()]
    vector_store = InMemoryVectorStore.from_documents(pages, embeddings)


@tool
def query_pdf(query: str) -> list[Document] | None:
    """Returns the most relevant text from the PDF file based on the query."""
    if vector_store is None:
        warnings.warn("Vector store is not initialized.")
        return None
    docs = vector_store.similarity_search(query)
    return docs if docs else None


tools = [query_pdf]
tool_map = {t.name: t for t in tools}


