from financial_contract_analyzer import FinancialContractAnalyzer
import json
from datetime import datetime


def main():
    print("=== KB구매론 계약서 분석 시스템 ===\n")
    
    # 1. 분석기 초기화
    print("금융 계약서 분석기 초기화 중...")
    analyzer = FinancialContractAnalyzer()
    
    # 2. 금융 용어 사전 추가 (KB구매론 관련 용어)
    kb_financial_terms = {
        "KB구매론": "구매기업이 판매기업에게 구매대금을 지급하는 KB국민은행의 결제제도",
        "매출승인명세": "구매대금 지급을 위해 구매기업이 전송하는 구매자료로, 은행의 지급승인이 필요함",
        "매출승인금액": "승인명세 상 구매기업이 판매기업에게 지급할 구매대금",
        "구매기업결제일": "구매기업이 구매대금을 결제하여야 하는 일자로서, 승인금액의 상환일",
        "선입금": "판매기업 입금일 전에 판매기업이 대금의 조기회수를 위하여 할인하는 행위",
        "지급보증": "승인금액에 대하여 은행이 대금지급을 보증하는 것",
        "기한이익상실": "채무자가 약정을 위반하여 분할상환 등의 이익을 잃는 것",
        "연대보증": "주채무자와 연대하여 채무 이행 책임을 지는 보증",
        "CD수익률": "AAA 이상 신용등급 시중은행이 발행한 91일물 CD의 발행수익률",
        "COFIX": "Cost of Funds Index, 자금조달비용지수",
        "MOR": "Market Opportunity Rate, 시장기회금리",
        "지연배상금": "채무이행지체 등에 따른 배상금",
        "근저당권": "담보물에 설정하는 저당권의 일종",
        "기업인터넷뱅킹": "기업뱅킹, 프리미엄뱅킹 등을 포함하는 온라인 뱅킹 서비스"
    }
    
    print("\nKB구매론 관련 금융 용어 추가 중...")
    analyzer.add_financial_terms(kb_financial_terms)
    
    # 3. 법령 데이터 추가 (실제로는 API 호출)
    financial_laws = [
        {
            "text": "전자금융거래법 제21조: 금융회사 또는 전자금융업자는 전자금융거래와 관련하여 손실이 발생한 경우 그 손해를 배상할 책임을 진다.",
            "metadata": {
                "law_code": "전자금융거래법",
                "law_name": "전자금융거래법",
                "article_no": "21",
                "article_title": "손실부담 및 면책",
                "type": "law"
            }
        },
        {
            "text": "상법 제57조: 상인간의 거래에 있어서 상사법정이율은 연 6%로 한다.",
            "metadata": {
                "law_code": "상법",
                "law_name": "상법",
                "article_no": "57",
                "article_title": "상사법정이율",
                "type": "law"
            }
        },
        {
            "text": "이자제한법 제2조: 금전대차에 관한 계약상의 최고이자율은 연 20%를 초과하지 아니하는 범위 내에서 대통령령으로 정한다.",
            "metadata": {
                "law_code": "이자제한법",
                "law_name": "이자제한법",
                "article_no": "2",
                "article_title": "최고이자율",
                "type": "law"
            }
        },
        {
            "text": "민법 제428조: 보증인은 주채무자가 이행하지 아니하는 채무를 이행할 의무가 있다.",
            "metadata": {
                "law_code": "민법",
                "law_name": "민법",
                "article_no": "428",
                "article_title": "보증채무의 내용",
                "type": "law"
            }
        }
    ]
    
    print("\n법령 데이터 추가 중...")
    law_documents = [law["text"] for law in financial_laws]
    law_metadata = [law["metadata"] for law in financial_laws]
    analyzer.vectordb.add_documents(law_documents, law_metadata)
    
    # 4. 실제 KB구매론 계약서 텍스트 (PDF에서 추출한 주요 조항)
    kb_contract_text = """
    KB구매론 계약서 (기업용)
    
    제1조(목적)
    이 계약은 구매기업이 은행의 "KB구매론" 결제제도를 이용하여 판매기업에게 구매대금을 지급함에 있어 필요한 사항을 정함을 목적으로 합니다.
    
    제4조(이용한도 및 지급보증)
    구매기업이 판매기업으로부터 구매한 물품 등의 구매대금 지급을 위해 전송하는 승인금액에 대하여 제6조 제2항에 해당하지 않는 한, 은행이 지급을 보증하며, 승인금액의 총잔액은 원 약정서의 "여신(한도)금액" 범위를 초과할 수 없습니다.
    
    제5조(신용공여기간)
    구매기업이 본 계약을 통하여 이용할 수 있는 신용공여기간은 아래와 같이 하기로 합니다.
    구분: 지급승인기간
    신용공여기간: 최장180일 범위내 운용
    
    제8조(대출의 이자)
    ① 대출이자의 계산은 아래와 같이 기준금리와 가산금리를 합하여 적용하기로 합니다.
    - CD수익률(91일물) 또는 단기COFIX 또는 기간별MOR
    - 선입금이자: 1~30일, 31~60일, 61~91일, 92~180일 구간별 가산금리 적용
    - 이자계산방법: 1년을 365일로보고 1일 단위로 계산합니다
    
    제9조(지연배상금)
    ① 채무이행지체 등에 따른 지연배상금률은 약정이자율에 연3.0%P를 더하여 최고 연15.0%이내로 적용합니다. 
    다만, 이자율이 최고 지연배상금률 이상인 경우에는 이자율에 연2.0%P를 가산하여 적용합니다.
    
    제11조(개별대출의 상환)
    ① 개별대출금의 상환자원은 은행영업시간까지 제10조에서 지정한 결제계좌에 입금하여야 합니다.
    ② 개별대출금의 만기일에 제10조에서 지정한 결제계좌에서 자동상환처리함을 원칙으로 합니다.
    ④ 허위매출, 현금융통성거래 등 상거래와 무관한 승인명세에 대하여 선입금이 실행된 경우에는 그 만기일에도 불구하고 즉시 상환하여야 합니다.
    """
    
    # 5. 계약서 분석 실행
    print("\n=== KB구매론 계약서 분석 시작 ===\n")
    analysis_result = analyzer.analyze_contract(kb_contract_text)
    
    # 6. 중요 내용 하이라이트 출력
    print("📌 발견된 중요 내용:")
    print("-" * 50)
    for i, highlight in enumerate(analysis_result['highlights'], 1):
        print(f"\n{i}. [{highlight['category'].upper()}]")
        print(f"   내용: {highlight['text']}")
        print(f"   문맥: ...{highlight['context']}...")
    
    # 7. 특정 용어 드래그 시뮬레이션
    print("\n\n=== 용어 드래그 시뮬레이션 ===")
    print("-" * 50)
    
    # 사용자가 모르는 용어를 드래그했다고 가정
    dragged_terms = [
        ("지급보증", "은행이 지급을 보증하며"),
        ("CD수익률", "CD수익률(91일물) 또는 단기COFIX"),
        ("지연배상금", "지연배상금률은 약정이자율에 연3.0%P를 더하여"),
        ("선입금", "선입금이자: 1~30일")
    ]
    
    for term, context in dragged_terms:
        print(f"\n\n🔍 드래그한 용어: \"{term}\"")
        print(f"📍 문맥: \"{context}\"")
        
        explanation = analyzer.explain_term(term, context)
        
        print(f"\n📚 용어 설명:")
        print(f"   {explanation['definition']}")
        
        if explanation['relevant_laws']:
            print(f"\n📖 관련 법령:")
            for law in explanation['relevant_laws'][:2]:
                print(f"\n   • {law['law_name']} {law['article_no']}조")
                print(f"     {law['content'][:80]}...")
                print(f"     관련도: {law['relevance_score']:.2%}")
    
    # 8. 계약서 주요 조항과 관련 법령 매칭
    print("\n\n=== 주요 조항별 관련 법령 ===")
    print("-" * 50)
    
    key_clauses = [
        ("이자율 제한", "최고 연15.0%이내로 적용합니다"),
        ("허위매출 금지", "허위매출, 현금융통성거래 등 상거래와 무관한"),
        ("자동상환처리", "결제계좌에서 자동상환처리함을 원칙으로")
    ]
    
    for clause_title, clause_text in key_clauses:
        print(f"\n\n📋 {clause_title}")
        print(f"   조항: \"{clause_text}\"")
        
        relevant_laws = analyzer._find_relevant_laws(clause_text, top_k=2)
        if relevant_laws:
            print(f"\n   관련 법령:")
            for law in relevant_laws:
                print(f"   • {law['law_name']} {law['article_no']}조")
                print(f"     {law['content'][:60]}...")
    
    # 9. 분석 결과 저장
    print("\n\n=== 분석 결과 저장 ===")
    analyzer.save_analysis("kb_contract_analysis_result")
    print("✅ 분석이 완료되었습니다!")
    
    # 10. 계약서 위험도 평가 (추가 기능)
    print("\n\n=== 계약서 위험도 평가 ===")
    print("-" * 50)
    
    risk_factors = {
        "높은 지연배상금": "연15.0%" in kb_contract_text,
        "긴 신용공여기간": "최장180일" in kb_contract_text,
        "허위매출 조항": "허위매출" in kb_contract_text,
        "자동상환 조항": "자동상환처리" in kb_contract_text
    }
    
    risk_score = sum(1 for factor, exists in risk_factors.items() if exists)
    risk_level = "낮음" if risk_score <= 1 else "보통" if risk_score <= 2 else "주의필요"
    
    print(f"\n위험도 평가: {risk_level} (점수: {risk_score}/4)")
    print("\n발견된 위험 요소:")
    for factor, exists in risk_factors.items():
        if exists:
            print(f"  ⚠️  {factor}")


if __name__ == "__main__":
    main()