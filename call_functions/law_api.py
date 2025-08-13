"""
법령 정보 API 호출 및 ChromaDB 저장 모듈
"""

import os
import sys
import requests
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 모듈 경로 추가 (직접 실행 시)
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

from utils.custom_embeddings import get_law_embeddings
from utils.get_env import OLLAMA_SERVER_URL, OPEN_LAW_GO_ID


@dataclass
class LawConfig:
    """법령 API 설정"""
    api_base_url: str = "http://www.law.go.kr/DRF/lawService.do"
    search_base_url: str = "http://www.law.go.kr/DRF/lawSearch.do"
    chunk_size: int = 1024
    chunk_overlap: int = 100
    max_articles: int = 50
    search_threshold: int = 2
    max_distance_score: float = 350.0  # 최대 거리 점수 (낮을수록 유사) - Ollama embeddings scale
    timeout: int = 10


@dataclass
class ArticleInfo:
    """조문 정보"""
    jo: str = ''
    hang: str = ''
    ho: str = ''
    
    def format_reference(self, law_name: str) -> str:
        """조항 정보를 읽기 쉬운 형태로 포맷"""
        reference = law_name
        if self.jo:
            reference += f" 제{self.jo}조"
        if self.hang:
            reference += f" 제{self.hang}항"
        if self.ho:
            reference += f" 제{self.ho}호"
        return reference


class LawAPIClient:
    """법령 API 클라이언트"""
    
    def __init__(self, config: LawConfig | None = None):
        self.config = config or LawConfig()
        self.api_key = OPEN_LAW_GO_ID
    
    def search_laws(self, query: str) -> Optional[Dict]:
        """법령 검색"""
        params = {
            'OC': self.api_key,
            'target': 'law',
            'type': 'JSON',
            'query': query,
            'display': '10'
        }
        
        return self._make_request(self.config.search_base_url, params)
    
    def get_law_by_id(self, law_id: str) -> Optional[Dict]:
        """법령 ID로 상세 정보 조회"""
        params = {
            'OC': self.api_key,
            'target': 'law',
            'type': 'JSON',
            'ID': law_id
        }
        
        return self._make_request(self.config.api_base_url, params)
    
    def get_law_by_mst(self, mst: str) -> Optional[Dict]:
        """법령 일련번호로 상세 정보 조회"""
        params = {
            'OC': self.api_key,
            'target': 'law',
            'type': 'JSON',
            'MST': mst
        }
        
        return self._make_request(self.config.api_base_url, params)
    
    def _make_request(self, url: str, params: Dict) -> Optional[Dict]:
        """API 요청 실행"""
        try:
            response = requests.get(url, params=params, timeout=self.config.timeout)
            if response.status_code == 200:
                print(f"request success: {response.request.url}")
                return response.json()
        except Exception as e:
            print(f"API 호출 실패: {e}")
        return None


class LawDocumentProcessor:
    """법령 문서 처리기"""
    
    def __init__(self, config: LawConfig | None = None):
        self.config = config or LawConfig()
    
    def parse_article_number(self, article_num: str) -> ArticleInfo:
        """조문번호를 파싱하여 조/항/호 정보 추출"""
        if not article_num:
            return ArticleInfo()
        
        jo_match = re.search(r'제(\d+)조', article_num)
        hang_match = re.search(r'제(\d+)항', article_num)
        ho_match = re.search(r'제(\d+)호', article_num)
        
        return ArticleInfo(
            jo=jo_match.group(1) if jo_match else '',
            hang=hang_match.group(1) if hang_match else '',
            ho=ho_match.group(1) if ho_match else ''
        )
    
    def create_law_documents(self, law_data: Dict) -> List[Document]:
        """법령 데이터를 Document 객체로 변환"""
        documents = []
        
        if '법령' not in law_data:
            return documents
            
        law_info = law_data['법령']
        
        # 기본 정보 문서 생성
        basic_info = self._create_basic_info(law_info)
        documents.append(basic_info)
        
        # 조문 정보 문서 생성
        article_docs = self._create_article_documents(law_info)
        documents.extend(article_docs)
        
        return documents
    
    def _create_basic_info(self, law_info: Dict) -> Document:
        """법령 기본 정보 문서 생성"""
        # 기본정보가 중첩되어 있는 경우 처리
        basic_info = law_info.get('기본정보', law_info)
        
        # 소관부처 정보 처리 - 중첩된 객체인 경우와 단순 문자열인 경우 모두 처리
        department = basic_info.get('소관부처')
        if isinstance(department, dict):
            department_name = department.get('content', 'N/A')
        else:
            department_name = department or basic_info.get('소관부처명', 'N/A')
        
        content = f"""
        법령명: {basic_info.get('법령명_한글', 'N/A')}
        법령ID: {basic_info.get('법령ID', 'N/A')}
        공포일자: {basic_info.get('공포일자', 'N/A')}
        시행일자: {basic_info.get('시행일자', 'N/A')}
        소관부처: {department_name}
        """
        
        return Document(
            page_content=content.strip(),
            metadata={
                'type': 'law_basic',
                'law_id': basic_info.get('법령ID', ''),
                'law_name': basic_info.get('법령명_한글', '')
            }
        )
    
    def _create_article_documents(self, law_info: Dict) -> List[Document]:
        """조문 정보 문서들 생성"""
        documents = []
        
        # 조문 구조 처리: 조문.조문단위 또는 직접 조문
        articles_container = law_info.get('조문', {})
        if isinstance(articles_container, dict) and '조문단위' in articles_container:
            articles = articles_container['조문단위']
        else:
            articles = law_info.get('조문', [])
            
        if isinstance(articles, dict):
            articles = [articles]
        
        # 기본정보에서 법령 정보 가져오기
        basic_info = law_info.get('기본정보', law_info)
        
        for article in articles[:self.config.max_articles]:
            if isinstance(article, dict):
                doc = self._create_single_article_document(article, basic_info)
                if doc:
                    documents.append(doc)
        
        return documents
    
    def _create_single_article_document(self, article: Dict, basic_info: Dict) -> Optional[Document]:
        """단일 조문 문서 생성"""
        article_num = article.get('조문번호', '')
        article_title = article.get('조문제목', '')
        article_content = article.get('조문내용', '')
        
        if not article_content:
            return None
        
        article_info = self.parse_article_number(article_num)
        
        content = f"""
        조문번호: {article_num}
        조문제목: {article_title}
        조문내용: {article_content}
        """.strip()
        
        return Document(
            page_content=content,
            metadata={
                'type': 'law_article',
                'law_id': basic_info.get('법령ID', ''),
                'law_name': basic_info.get('법령명_한글', ''),
                'article_title': article_title,
                'article_number': article_num,
                'jo': article_info.jo,
                'hang': article_info.hang,
                'ho': article_info.ho
            }
        )


class LawVectorStore:
    """법령 벡터 스토어 관리"""
    
    def __init__(self, config: LawConfig | None = None):
        self.config = config or LawConfig()
        self.processor = LawDocumentProcessor(config)
        self.vectorstore = None
        self._initialize()
    
    def _initialize(self):
        """벡터스토어 초기화"""
        try:
            embeddings = get_law_embeddings(OLLAMA_SERVER_URL, "nomic-embed-text")
            
            persist_directory = Path(__file__).parent.parent / "database" / "law_chroma_db"
            persist_directory.mkdir(parents=True, exist_ok=True)
            
            # langchain-chroma의 새로운 API 사용
            self.vectorstore = Chroma(
                collection_name="law_documents",
                embedding_function=embeddings,
                persist_directory=str(persist_directory)
            )

            assert self.vectorstore is not None, f"Vectorstore must be initialized"
            print(f"✅ 법령 ChromaDB 초기화 완료: {persist_directory}")
        except Exception as e:
            print(f"⚠️ 법령 ChromaDB 초기화 실패: {e}")
            print("환경 설정을 확인해주세요. (OLLAMA_SERVER_URL, 모델 가용성 등)")
            self.vectorstore = None
    
    def add_law_data(self, law_data: Dict) -> int:
        """법령 데이터를 벡터스토어에 추가"""
        if not self.vectorstore:
            print("❌ 벡터스토어가 초기화되지 않았습니다.")
            return 0
            
        documents = self.processor.create_law_documents(law_data)
        
        if not documents:
            return 0
        
        # 텍스트 분할
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        
        splits = text_splitter.split_documents(documents)
        
        if splits:
            self.vectorstore.add_documents(splits)
            print(f"✅ {len(splits)}개의 법령 청크 추가 완료")
        
        return len(splits)
    
    def search(self, query: str, k: int = 5) -> List[Document]:
        """벡터스토어에서 검색"""
        if not self.vectorstore:
            print("❌ 벡터스토어가 초기화되지 않았습니다.")
            return []
            
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
        return retriever.invoke(query) or []
    
    def search_with_scores(self, query: str, k: int = 5) -> List[tuple[Document, float]]:
        """벡터스토어에서 점수와 함께 검색"""
        if not self.vectorstore:
            print("❌ 벡터스토어가 초기화되지 않았습니다.")
            return []
        
        # Ollama embeddings에서는 similarity_search_with_score가 더 안정적
        return self.vectorstore.similarity_search_with_score(query, k=k) or []
    
    def is_sufficient_result(self, docs_with_scores: List[tuple[Document, float]], query: str) -> bool:
        """검색 결과가 충분한지 판단 (점수 기반)"""
        if not docs_with_scores or len(docs_with_scores) < self.config.search_threshold:
            print(f"🔍 결과 부족: {len(docs_with_scores) if docs_with_scores else 0}개 (최소 {self.config.search_threshold}개 필요)")
            return False
        
        # 거리 점수가 충분히 낮은(유사한) 결과가 충분한지 확인
        # 거리가 작을수록 더 유사함 (0에 가까울수록 더 유사)
        high_quality_results = [
            (doc, score) for doc, score in docs_with_scores 
            if score <= self.config.max_distance_score  # 거리 점수가 임계값보다 낮음(더 유사)
        ]
        
        print(f"🔍 점수 평가: {len(high_quality_results)}개 상위 결과 (거리 ≤{self.config.max_distance_score})")
        if docs_with_scores:
            scores = [score for _, score in docs_with_scores[:3]]
            print(f"🔍 상위 3개 점수: {scores}")
        
        return len(high_quality_results) >= self.config.search_threshold


class LawService:
    """법령 서비스 메인 클래스"""
    
    def __init__(self):
        self.config = LawConfig()
        self.api_client = LawAPIClient(self.config)
        self.vector_store = LawVectorStore(self.config)
        self.processor = LawDocumentProcessor(self.config)
        self.cache: Dict[str, Any] = {}
    
    def search_laws(self, query: str) -> str:
        """법령 검색 메인 로직"""
        print(f"🔍 법령 검색: '{query}'")
        
        # 1단계: ChromaDB에서 기존 법령 검색 (점수와 함께)
        existing_docs_with_scores = self.vector_store.search_with_scores(query)
        
        # 2단계: 검색 결과가 충분한지 확인
        if self.vector_store.is_sufficient_result(existing_docs_with_scores, query):
            print("✅ ChromaDB에서 충분한 법령 정보 발견")
            # 거리 점수 기반 정렬 (낮은 거리가 더 유사함)
            existing_docs_with_scores.sort(key=lambda x: x[1])  # 거리 낮은 순 (더 유사한 순)
            existing_docs = [doc for doc, score in existing_docs_with_scores[:5]]
            return self._format_results(existing_docs, "근거법령")
        
        # 3단계: API 호출로 새로운 법령 가져오기
        print("⚡ ChromaDB에 관련 법령이 부족하여 API 호출 중...")
        
        law_data = self._fetch_law_data_by_query(query)
        
        if law_data:
            print("✅ 새로운 법령 데이터 획득, ChromaDB에 저장 중...")
            
            # 캐시 저장
            cache_key = query[:50]
            self.cache[cache_key] = law_data
            
            # 벡터스토어에 추가
            self.vector_store.add_law_data(law_data)
            
            # 업데이트된 DB에서 다시 검색
            updated_docs = self.vector_store.search(query)
            if updated_docs:
                return self._format_results(updated_docs, "새로 추가된 근거법령")
        
        # 최종 단계: 기존 결과라도 반환
        if existing_docs_with_scores:
            print("⚠️ 새 법령 추가 실패, 기존 결과 반환")
            existing_docs = [doc for doc, score in existing_docs_with_scores[:3]]
            return self._format_results(existing_docs, "기존 근거법령")
        
        return "관련 법령 정보를 찾을 수 없습니다."

    def load_law_by_id(self, law_id: str | None = None, mst: str | None = None) -> str:
        """특정 법령 ID로 법령 정보 로드"""
        law_data = None
        
        if law_id:
            law_data = self.api_client.get_law_by_id(law_id)
        elif mst:
            law_data = self.api_client.get_law_by_mst(mst)
        
        if law_data and '법령' in law_data:
            law_info = law_data['법령']
            # 기본정보에서 정보 추출
            basic_info = law_info.get('기본정보', law_info)
            
            # 소관부처 정보 처리
            department = basic_info.get('소관부처')
            if isinstance(department, dict):
                department_name = department.get('content', 'N/A')
            else:
                department_name = department or basic_info.get('소관부처명', 'N/A')
                
            # 조문 수 계산
            articles_container = law_info.get('조문', {})
            if isinstance(articles_container, dict) and '조문단위' in articles_container:
                articles = articles_container['조문단위']
            else:
                articles = law_info.get('조문', [])
            
            if isinstance(articles, dict):
                articles = [articles]
                
            article_count = len(articles) if isinstance(articles, list) else 0
            
            self.vector_store.add_law_data(law_data)

            return f"법령명: {basic_info.get('법령명_한글', 'N/A')}" \
                   f"\n법령ID: {basic_info.get('법령ID', 'N/A')}" \
                   f"\n공포일자: {basic_info.get('공포일자', 'N/A')}" \
                   f"\n시행일자: {basic_info.get('시행일자', 'N/A')}" \
                   f"\n소관부처: {department_name}" \
                   f"\n조문 수: {article_count}개" \
                   f"\n법령 정보가 벡터스토어에 저장되었습니다.".strip()
        
        return "법령 정보를 찾을 수 없습니다."
    
    def _fetch_law_data_by_query(self, query: str) -> Optional[Dict]:
        """쿼리로 법령 데이터 가져오기"""
        # 먼저 검색으로 법령 찾기
        search_result = self.api_client.search_laws(query) or {}
        search_result = search_result.get('LawSearch', [])

        if search_result and 'law' in search_result:
            laws = search_result.get('law', [])
            if laws:
                first_law = laws[0]  # only the first one
                law_id = first_law.get('법령ID')
                if law_id:
                    # 상세 정보 가져오기
                    return self.api_client.get_law_by_id(law_id)

        print('⚠️ 법령 검색 결과가 없습니다. [_fetch_law_data_by_query]')
        return None
    
    def _format_results(self, docs: List[Document], prefix: str, show_scores: bool = False, docs_with_scores: Optional[List[tuple[Document, float]]] = None) -> str:
        """검색 결과를 포맷팅"""
        results = []
        
        # 점수 정보가 있으면 사용
        if docs_with_scores:
            score_map = {id(doc): score for doc, score in docs_with_scores}
        else:
            score_map = {}
        
        for i, doc in enumerate(docs[:5], 1):
            # 조항 정보 포맷팅
            article_info = ArticleInfo(
                jo=doc.metadata.get('jo', ''),
                hang=doc.metadata.get('hang', ''),
                ho=doc.metadata.get('ho', '')
            )
            
            law_name = doc.metadata.get('law_name', 'Unknown')
            article_ref = article_info.format_reference(law_name)
            content = doc.page_content[:500]
            
            # 점수 표시 (디버깅용)
            score_info = ""
            if show_scores and id(doc) in score_map:
                score = score_map[id(doc)]
                score_info = f" (점수: {score:.3f})"
            
            results.append(f"[{prefix} {i}]{score_info} {article_ref}\n{content}")
        
        return "\n\n".join(results)


# 전역 서비스 인스턴스
_law_service = LawService()


@tool
def search_law_by_query(query: str) -> str:
    """
    Search online for legal information and return relevant content.
    Use only one or two keywords to query.
    
    Returns:
        Relevant legal information
    """
    return _law_service.search_laws(query.split()[0])


@tool
def load_law_by_id(law_id: str | None = None, mst: str | None = None) -> str:
    """
    Load legal information by specific law ID or serial number.
    
    Returns:
        Legal information
    """
    return _law_service.load_law_by_id(law_id, mst)


# Export tools
tools = [search_law_by_query, load_law_by_id]