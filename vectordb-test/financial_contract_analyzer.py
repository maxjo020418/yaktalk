import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import requests
import json
from ollama_vectordb import OllamaInMemoryVectorDB


class FinancialContractAnalyzer:
    def __init__(self, model_name: str = "qwen3:14b"):
        """
        금융 계약서 분석기 초기화
        
        Args:
            model_name: Ollama 모델명
        """
        self.vectordb = OllamaInMemoryVectorDB(model_name=model_name)
        self.law_cache = {}  # 법령 API 캐시
        self.term_definitions = {}  # 용어 정의 캐시
        self.highlighted_sections = []  # 중요 섹션 저장
        
    def load_laws_to_vectordb(self, law_api_url: str, law_codes: List[str]):
        """
        법령 API에서 법령을 가져와 벡터 DB에 저장
        
        Args:
            law_api_url: 법령 API URL
            law_codes: 로드할 법령 코드 리스트
        """
        documents = []
        metadata = []
        
        for law_code in law_codes:
            # 법령 API 호출 (예시)
            try:
                response = requests.get(f"{law_api_url}/law/{law_code}")
                if response.status_code == 200:
                    law_data = response.json()
                    
                    # 법령 조항별로 분리하여 저장
                    for article in law_data.get('articles', []):
                        doc_text = f"{law_data['law_name']} {article['article_no']}조: {article['content']}"
                        documents.append(doc_text)
                        metadata.append({
                            "law_code": law_code,
                            "law_name": law_data['law_name'],
                            "article_no": article['article_no'],
                            "article_title": article.get('title', ''),
                            "effective_date": law_data.get('effective_date', ''),
                            "type": "law"
                        })
                    
                    # 캐시에 저장
                    self.law_cache[law_code] = law_data
                    
            except Exception as e:
                print(f"법령 {law_code} 로드 실패: {e}")
                
        # 벡터 DB에 추가
        if documents:
            self.vectordb.add_documents(documents, metadata)
            print(f"{len(documents)}개의 법령 조항을 벡터 DB에 추가했습니다.")
            
    def add_financial_terms(self, terms_dict: Dict[str, str]):
        """
        금융 용어 사전을 벡터 DB에 추가
        
        Args:
            terms_dict: {용어: 설명} 형태의 딕셔너리
        """
        documents = []
        metadata = []
        
        for term, definition in terms_dict.items():
            doc_text = f"{term}: {definition}"
            documents.append(doc_text)
            metadata.append({
                "term": term,
                "type": "definition",
                "category": "financial_term"
            })
            self.term_definitions[term] = definition
            
        self.vectordb.add_documents(documents, metadata)
        print(f"{len(documents)}개의 금융 용어를 벡터 DB에 추가했습니다.")
        
    def analyze_contract(self, contract_text: str) -> Dict[str, Any]:
        """
        계약서 전체 분석 및 중요 내용 하이라이트
        
        Args:
            contract_text: 계약서 전문
            
        Returns:
            분석 결과 딕셔너리
        """
        # 중요 패턴 정의
        important_patterns = [
            (r'이자율.*?%', 'interest_rate'),
            (r'연체.*?일', 'overdue'),
            (r'위약금.*?원', 'penalty'),
            (r'보증.*?범위', 'guarantee'),
            (r'해지.*?조건', 'termination'),
            (r'수수료.*?%', 'fee'),
            (r'원금.*?상환', 'principal'),
            (r'담보.*?설정', 'collateral')
        ]
        
        highlights = []
        
        # 패턴 매칭으로 중요 내용 추출
        for pattern, category in important_patterns:
            matches = re.finditer(pattern, contract_text, re.IGNORECASE)
            for match in matches:
                context_start = max(0, match.start() - 50)
                context_end = min(len(contract_text), match.end() + 50)
                context = contract_text[context_start:context_end]
                
                highlights.append({
                    "text": match.group(),
                    "category": category,
                    "position": (match.start(), match.end()),
                    "context": context,
                    "importance": "high"
                })
                
        # 관련 법령 검색
        relevant_laws = self._find_relevant_laws(contract_text)
        
        return {
            "highlights": highlights,
            "relevant_laws": relevant_laws,
            "analysis_date": datetime.now().isoformat()
        }
        
    def explain_term(self, term: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        드래그한 용어 설명 및 관련 법령 제공
        
        Args:
            term: 설명이 필요한 용어
            context: 용어가 사용된 문맥 (선택사항)
            
        Returns:
            용어 설명 및 관련 정보
        """
        # 용어 정의 검색
        if term in self.term_definitions:
            definition = self.term_definitions[term]
        else:
            # 벡터 DB에서 유사한 용어 검색
            query = f"금융 용어 {term} 정의 설명"
            results = self.vectordb.search(query, top_k=3)
            definition = results[0]['document'] if results else "정의를 찾을 수 없습니다."
            
        # 관련 법령 검색
        law_query = f"{term} 관련 법령 조항"
        if context:
            law_query += f" {context}"
            
        law_results = self.vectordb.search(law_query, top_k=5)
        
        # 법령 결과 필터링 (법령 타입만)
        relevant_laws = [
            {
                "law_name": r['metadata'].get('law_name', ''),
                "article_no": r['metadata'].get('article_no', ''),
                "content": r['document'],
                "relevance_score": r['score']
            }
            for r in law_results
            if r['metadata'].get('type') == 'law'
        ]
        
        return {
            "term": term,
            "definition": definition,
            "relevant_laws": relevant_laws,
            "context": context
        }
        
    def _find_relevant_laws(self, text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        텍스트와 관련된 법령 조항 찾기
        
        Args:
            text: 분석할 텍스트
            top_k: 반환할 법령 수
            
        Returns:
            관련 법령 리스트
        """
        # 주요 키워드 추출
        keywords = self._extract_keywords(text)
        query = " ".join(keywords) + " 관련 법령 조항"
        
        results = self.vectordb.search(query, top_k=top_k)
        
        return [
            {
                "law_name": r['metadata'].get('law_name', ''),
                "article_no": r['metadata'].get('article_no', ''),
                "article_title": r['metadata'].get('article_title', ''),
                "content": r['document'],
                "relevance_score": r['score']
            }
            for r in results
            if r['metadata'].get('type') == 'law'
        ]
        
    def _extract_keywords(self, text: str) -> List[str]:
        """
        텍스트에서 주요 키워드 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            키워드 리스트
        """
        # 금융 관련 주요 키워드
        financial_keywords = [
            '대출', '이자', '원금', '상환', '연체', '담보', '보증', '신용',
            '계약', '해지', '위약금', '수수료', '변제', '채권', '채무'
        ]
        
        found_keywords = []
        for keyword in financial_keywords:
            if keyword in text:
                found_keywords.append(keyword)
                
        return found_keywords[:5]  # 상위 5개만 반환
        
    def save_analysis(self, filepath: str):
        """
        분석 결과 및 벡터 DB 저장
        
        Args:
            filepath: 저장할 파일 경로
        """
        self.vectordb.save_to_file(f"{filepath}_vectordb.json")
        
        # 추가 분석 데이터 저장
        analysis_data = {
            "law_cache": self.law_cache,
            "term_definitions": self.term_definitions,
            "highlighted_sections": self.highlighted_sections
        }
        
        with open(f"{filepath}_analysis.json", 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            
        print(f"분석 결과가 {filepath}에 저장되었습니다.")