from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_ollama import OllamaEmbeddings
# from langchain_experimental.text_splitter import SemanticChunker

from utils.get_env import OLLAMA_SERVER_URL, DATA_DIR

import warnings
import tqdm
# from kss import split_sentences


vector_store: InMemoryVectorStore | None = None


async def db_init(pdf_file_path: str, 
                  embed_model: str = "llama3.1:8b",
                  chunk_size: int = 512,
                  chunk_overlap: int = 20
                  ) -> None:
    """Initializes the vector store for the provided PDF file."""
    global vector_store
    embeddings = OllamaEmbeddings(
        base_url=OLLAMA_SERVER_URL,
        model=embed_model,
        num_ctx=4096,
    )
    loader = PyMuPDFLoader(pdf_file_path)
    docs = loader.load()

    with open(DATA_DIR + '/debug_data/' + pdf_file_path.split("/")[-1][:-3] + ".txt", 
              "w") as f:
        f.write('\n\n'.join([doc.page_content for doc in docs]))

    splitter = RecursiveCharacterTextSplitter(  # SpaCy's ko_core_news_sm doesn't seem to work...
        separators=[
            "\n\n", # "\n",
            ".",
            # ",",
            # "\u200b",  # Zero-width space
            # "\uff0c",  # Fullwidth comma
            # "\u3001",  # Ideographic comma
            # "\uff0e",  # Fullwidth full stop
            # "\u3002",  # Ideographic full stop
        ],  
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )

    chunks = list()
    for doc in docs:
        if not doc.page_content.strip():
            warnings.warn(f"Document {doc.metadata.get('source', 'unknown')} is empty.")
            continue
        chunks.extend(splitter.split_text(doc.page_content))

    vector_store = None
    for chunk in tqdm.tqdm(chunks, desc="Embedding documents"):
        if vector_store is None:  # first document
            vector_store = InMemoryVectorStore.from_texts([chunk], embedding=embeddings)
        else:  # subsequent documents
            vector_store.add_texts([chunk], embedding=embeddings)


@tool
def query_pdf(query: str) -> list[Document] | None:
    """Returns the most relevant chunks of text from the PDF file based on the query from a vector store."""
    TOP_K = 5

    if vector_store is None:
        warnings.warn("Vector store is not initialized.")
        return None
    docs = vector_store.similarity_search(query, k=TOP_K)
    return docs if docs else None


tools = [query_pdf]
tool_map = {t.name: t for t in tools}
