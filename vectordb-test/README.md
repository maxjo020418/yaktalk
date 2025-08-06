# KB구매론 계약서 분석 시스템 (Ollama Vector DB)

Ollama 임베딩을 사용한 금융 계약서 분석 시스템입니다. 계약서의 중요 내용을 자동으로 하이라이트하고, 모르는 용어에 대한 설명과 관련 법령을 제공합니다.

## 주요 기능

- **In-Memory 벡터 DB**: Ollama 기반 빠른 검색을 위한 메모리 저장
- **자동 하이라이트**: 이자율, 연체, 위약금, 담보 등 중요 조항 자동 감지
- **용어 설명**: 금융 전문 용어 즉시 설명 (드래그/클릭 시)
- **법령 연결**: 관련 법령 자동 매칭 및 제시
- **위험도 평가**: 계약 조건의 위험 요소 자동 분석
- **시각화**: HTML 기반 분석 결과 시각화

## 설치 방법

### 1. Ollama 설치
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Ollama 실행
```bash
# 별도 터미널에서 실행
ollama serve
```

### 3. 필요한 모델 다운로드
```bash
ollama pull qwen3:14b
```

### 4. Python 패키지 설치
```bash
cd vectordb
pip install -r requirements.txt
```

## 실행 방법

### 기본 실행
```bash
# KB구매론 계약서 분석 실행
python kb_contract_analysis_example.py
```

### 실행 결과
프로그램 실행 시 다음과 같은 분석 결과를 확인할 수 있습니다:

1. **중요 내용 하이라이트**
   - 이자율 조항 (예: "연 5.5%", "최고 연15.0%")
   - 연체 관련 조항
   - 수수료 및 위약금 조항
   - 담보 설정 조항

2. **용어 설명 및 법령 매칭**
   - 지급보증, CD수익률, COFIX 등 전문 용어 설명
   - 이자제한법, 전자금융거래법 등 관련 법령 자동 제시

3. **위험도 평가**
   - 계약서의 잠재적 위험 요소 분석
   - 위험도 레벨 표시 (낮음/보통/높음)

4. **저장 파일**
   - `kb_contract_analysis_result_vectordb.json`: 벡터 DB 데이터
   - `kb_contract_analysis_result_analysis.json`: 분석 결과

## 코드에서 사용하기

### 기본 사용법
```python
from financial_contract_analyzer import FinancialContractAnalyzer

# 분석기 초기화
analyzer = FinancialContractAnalyzer()

# 계약서 분석
contract_text = "계약서 내용..."
result = analyzer.analyze_contract(contract_text)

# 특정 용어 설명
explanation = analyzer.explain_term("담보권설정", context="계약서 3조")
print(explanation['definition'])
print(explanation['relevant_laws'])
```

### 법령 API 연동
```python
# 법령 데이터 로드 (실제 API 사용 시)
analyzer.load_laws_to_vectordb(
    law_api_url="https://your-law-api.com",
    law_codes=["민법", "상법", "전자금융거래법"]
)
```

### 시각화
```python
from contract_visualization import ContractVisualization

# 분석 결과 시각화
visualizer = ContractVisualization()
html_content = visualizer.create_visualization(
    analysis_result, 
    term_explanations, 
    contract_text
)
visualizer.save_visualization(html_content, "analysis_result.html")
```

## 파일 구조

```
vectordb/
├── ollama_vectordb.py          # 핵심 벡터 DB 클래스
├── financial_contract_analyzer.py  # 금융 계약서 분석기
├── kb_contract_analysis_example.py # KB구매론 분석 예제
├── contract_visualization.py    # 분석 결과 시각화
├── requirements.txt            # 필요 패키지
├── README.md                   # 사용 가이드
└── 20240621_contract8.pdf      # KB구매론 계약서 샘플
```

## API 참조

### `FinancialContractAnalyzer`
금융 계약서 분석을 위한 메인 클래스

#### 주요 메서드
- `analyze_contract(contract_text)`: 계약서 전체 분석
- `explain_term(term, context)`: 특정 용어 설명
- `load_laws_to_vectordb(api_url, law_codes)`: 법령 데이터 로드
- `add_financial_terms(terms_dict)`: 금융 용어 사전 추가

### `OllamaInMemoryVectorDB`
Ollama 기반 벡터 데이터베이스

#### 주요 메서드
- `add_documents(documents, metadata)`: 문서 추가
- `search(query, top_k)`: 유사도 검색
- `save_to_file(filepath)`: DB 저장
- `load_from_file(filepath)`: DB 로드

## 활용 시나리오

1. **계약서 업로드 시**
   - 자동으로 중요 조항 추출 및 하이라이트
   - 위험 요소 사전 경고

2. **용어 드래그/클릭 시**
   - 즉시 용어 설명 팝업
   - 관련 법령 조항 표시

3. **계약서 비교**
   - 여러 계약서의 조건 비교
   - 유리/불리한 조항 식별

## 주의사항

- Ollama 서버가 실행 중이어야 합니다
- qwen3:14b 모델은 약 8GB의 저장 공간이 필요합니다
- 대용량 계약서의 경우 처리 시간이 길어질 수 있습니다

## 문제 해결

### Ollama 연결 오류
```bash
# Ollama 서버 상태 확인
ollama list

# 서버 재시작
ollama serve
```

### 모델 다운로드 실패
```bash
# 다른 모델 사용 (더 작은 크기)
ollama pull qwen2.5:7b
# 코드에서 모델명 변경 필요
```

## 라이선스

이 프로젝트는 KB국민은행 AI 경진대회를 위해 개발되었습니다.