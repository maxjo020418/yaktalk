"""
PDF 문서 처리 및 ChromaDB 저장 모듈
"""

import os
import sys
import warnings
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

# 모듈 경로 추가 (직접 실행 시)
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
import chromadb
from chromadb.config import Settings

from utils.custom_embeddings import get_pdf_embeddings

warnings.filterwarnings("ignore")


@dataclass
class PDFConfig:
    """PDF 처리 설정"""
    chunk_size: int = 1024
    chunk_overlap: int = 100
    max_content_length: int = 500
    collection_name: str = "pdf_documents"
    search_k: int = 5


class PDFVectorStore:
    """PDF 벡터 스토어 관리자"""
    
    def __init__(self, config: PDFConfig | None = None):
        self.config = config or PDFConfig()
        self.vectorstore: Optional[Chroma] = None
        self.pdf_file_path: Optional[str] = None
        self.retriever: Optional[ContextualCompressionRetriever] = None
    
    def initialize(self, pdf_file_path: str) -> None:
        """PDF를 로드하여 ChromaDB 초기화"""
        self.pdf_file_path = pdf_file_path
        
        # PDF 로드
        documents = self._load_pdf_documents(pdf_file_path)
        
        # 문서 분할
        splits = self._split_documents(documents)
        
        # 벡터스토어 초기화
        self._initialize_vectorstore(splits)
        
        print(f"✅ PDF ChromaDB 초기화 완료: {len(splits)}개 청크, {os.path.basename(pdf_file_path)}")
    
    def _load_pdf_documents(self, pdf_file_path: str) -> List[Document]:
        """PDF 문서 로드"""
        loader = PyMuPDFLoader(pdf_file_path)
        return loader.load()
    
    def _split_documents(self, documents: List[Document]) -> List[Document]:
        """문서를 청크로 분할"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        return text_splitter.split_documents(documents)
    
    def _initialize_vectorstore(self, splits: List[Document]) -> None:
        """벡터스토어 초기화 및 문서 추가"""
        # 로컬 임베딩 사용
        embeddings = get_pdf_embeddings()
        
        # ChromaDB 클라이언트 생성
        persist_directory = Path(__file__).parent.parent / "database" / "pdf_chroma_db"
        persist_directory.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 기존 컬렉션 삭제 (새로운 PDF용)
        try:
            client.delete_collection(name=self.config.collection_name)
        except:
            pass
        
        # 벡터스토어 생성
        self.vectorstore = Chroma(
            client=client,
            collection_name=self.config.collection_name,
            embedding_function=embeddings,
            persist_directory=str(persist_directory)
        )
        
        # 문서 추가
        self.vectorstore.add_documents(splits)
    
    def get_retriever(self, llm=None, use_compression: bool = False):
        """리트리버 반환 (압축 옵션)"""
        if not self.is_initialized() or not self.vectorstore:
            raise ValueError("ChromaDB가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        
        base_retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": self.config.search_k}
        )
        
        if use_compression and llm:
            compressor = LLMChainExtractor.from_llm(llm)
            self.retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=base_retriever
            )
            return self.retriever
        
        return base_retriever
    
    def search(self, query: str) -> List[Document]:
        """벡터스토어에서 검색"""
        if not self.is_initialized():
            return []
        
        retriever = self.get_retriever(use_compression=False)
        try:
            return retriever.invoke(query) or []
        except Exception as e:
            print(f"PDF 검색 오류: {e}")
            return []
    
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self.vectorstore is not None
    
    def get_metadata(self) -> dict:
        """PDF 메타데이터 반환"""
        if not self.is_initialized() or not self.vectorstore:
            print("ChromaDB가 초기화되지 않았습니다.")
            return {}
        
        collection = self.vectorstore._collection
        return {
            'pdf_file': os.path.basename(self.pdf_file_path) if self.pdf_file_path else 'Unknown',
            'total_chunks': collection.count(),
            'collection_name': collection.name,
            'storage_type': 'ChromaDB (Persistent)'
        }


class PDFService:
    """PDF 서비스 메인 클래스"""
    
    def __init__(self):
        self.config = PDFConfig()
        self.vector_store = PDFVectorStore(self.config)
    
    def initialize_pdf(self, pdf_file_path: str) -> None:
        """PDF 초기화"""
        self.vector_store.initialize(pdf_file_path)
    
    def search_content(self, query: str) -> str:
        """PDF 내용 검색"""
        if not self.vector_store.is_initialized():
            return "PDF가 로드되지 않았습니다. 먼저 PDF를 로드해주세요."
        
        docs = self.vector_store.search(query)
        
        if not docs:
            return "관련 내용을 찾을 수 없습니다."
        
        return self._format_search_results(docs)
    
    def get_metadata(self) -> str:
        """PDF 메타데이터 반환"""
        if not self.vector_store.is_initialized():
            return "PDF가 로드되지 않았습니다."
        
        metadata = self.vector_store.get_metadata()

        s = f"PDF 파일: {metadata['pdf_file']}\n" \
            f"총 청크 수: {metadata['total_chunks']}\n" \
            f"컬렉션 이름: {metadata['collection_name']}\n" \
            f"저장 방식: {metadata['storage_type']}\n"
        
        return s.strip()
    
    def _format_search_results(self, docs: List[Document]) -> str:
        """검색 결과 포맷팅"""
        results = []
        
        for i, doc in enumerate(docs, 1):
            page_num = doc.metadata.get('page', 'Unknown')
            content = doc.page_content[:self.config.max_content_length]
            
            # 내용이 잘렸는지 표시
            if len(doc.page_content) > self.config.max_content_length:
                content += "..."
            
            results.append(f"[검색결과 {i} - 페이지 {page_num}]\n{content}")
        
        return "\n\n".join(results)
    
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self.vector_store.is_initialized()


# 전역 서비스 인스턴스
_pdf_service = PDFService()


# 기존 함수들 (하위 호환)
def initialize_chromadb(
    pdf_file_path: str,
    embed_model: str = "nomic-embed-text",
    chunk_size: int = 1024,
    chunk_overlap: int = 100,
    collection_name: str = "pdf_documents"
) -> None:
    """ChromaDB 초기화 (하위 호환성)"""
    global _pdf_service
    
    # 설정 업데이트
    _pdf_service.config.chunk_size = chunk_size
    _pdf_service.config.chunk_overlap = chunk_overlap
    _pdf_service.config.collection_name = collection_name
    
    # PDF 초기화
    _pdf_service.initialize_pdf(pdf_file_path)


def get_retriever(llm=None, use_compression: bool = False):
    """리트리버 반환 (하위 호환성)"""
    return _pdf_service.vector_store.get_retriever(llm, use_compression)


def is_chromadb_initialized() -> bool:
    """초기화 상태 확인 (하위 호환성)"""
    return _pdf_service.is_initialized()


@tool
def search_pdf_content(query: str) -> str:
    """
    Search for relevant content in the PDF.
    
    Args:
        query: Search query
    
    Returns:
        Relevant PDF content
    """
    return _pdf_service.search_content(query)


@tool
def get_pdf_metadata() -> str:
    """
    Return metadata of the currently loaded PDF.
    
    Returns:
        PDF metadata information
    """
    return _pdf_service.get_metadata()


# Export tools
tools = [search_pdf_content, get_pdf_metadata]