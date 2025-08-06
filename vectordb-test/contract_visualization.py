import json
from typing import Dict, List, Any


class ContractVisualization:
    """계약서 분석 결과를 시각화하기 위한 HTML 생성 클래스"""
    
    def __init__(self):
        self.html_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KB구매론 계약서 분석 결과</title>
    <style>
        body {
            font-family: 'Noto Sans KR', sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #ffb800;
            padding-bottom: 10px;
        }
        .highlight {
            background-color: #fff3cd;
            padding: 2px 5px;
            border-radius: 3px;
            font-weight: bold;
        }
        .term-explanation {
            background-color: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .law-reference {
            background-color: #f3e5f5;
            border-left: 4px solid #9c27b0;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .risk-assessment {
            background-color: #fff8e1;
            border: 2px solid #ffc107;
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
        }
        .category-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
            margin-right: 5px;
        }
        .interest-rate { background-color: #ff5252; color: white; }
        .penalty { background-color: #ff9800; color: white; }
        .guarantee { background-color: #4caf50; color: white; }
        .fee { background-color: #2196f3; color: white; }
        .termination { background-color: #9c27b0; color: white; }
        .tooltip {
            position: relative;
            display: inline-block;
            border-bottom: 2px dotted #666;
            cursor: help;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        .tooltiptext {
            visibility: hidden;
            width: 300px;
            background-color: #333;
            color: #fff;
            text-align: left;
            padding: 10px;
            border-radius: 6px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -150px;
            opacity: 0;
            transition: opacity 0.3s;
        }
        .contract-text {
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            font-family: monospace;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>KB구매론 계약서 분석 결과</h1>
        
        <div class="risk-assessment">
            <h2>⚠️ 위험도 평가</h2>
            {risk_assessment}
        </div>
        
        <h2>📌 중요 내용 하이라이트</h2>
        <div class="highlights-section">
            {highlights}
        </div>
        
        <h2>📚 주요 용어 설명</h2>
        <div class="terms-section">
            {terms}
        </div>
        
        <h2>📖 관련 법령</h2>
        <div class="laws-section">
            {laws}
        </div>
        
        <h2>📄 계약서 원문 (주요 조항)</h2>
        <div class="contract-text">
            {contract_text}
        </div>
    </div>
</body>
</html>
"""
    
    def create_visualization(self, analysis_result: Dict[str, Any], 
                           term_explanations: List[Dict[str, Any]], 
                           contract_text: str) -> str:
        """분석 결과를 HTML로 시각화"""
        
        # 위험도 평가 섹션
        risk_assessment = self._create_risk_assessment(analysis_result)
        
        # 하이라이트 섹션
        highlights = self._create_highlights(analysis_result['highlights'])
        
        # 용어 설명 섹션
        terms = self._create_terms_section(term_explanations)
        
        # 법령 섹션
        laws = self._create_laws_section(analysis_result.get('relevant_laws', []))
        
        # 계약서 원문 (하이라이트 적용)
        highlighted_contract = self._highlight_contract_text(
            contract_text, 
            analysis_result['highlights']
        )
        
        # HTML 생성
        html = self.html_template.format(
            risk_assessment=risk_assessment,
            highlights=highlights,
            terms=terms,
            laws=laws,
            contract_text=highlighted_contract
        )
        
        return html
    
    def _create_risk_assessment(self, analysis_result: Dict[str, Any]) -> str:
        """위험도 평가 섹션 생성"""
        risk_factors = []
        
        for highlight in analysis_result['highlights']:
            if highlight['category'] in ['interest_rate', 'penalty', 'fee']:
                risk_factors.append(f"• {highlight['text']}")
        
        risk_level = "낮음" if len(risk_factors) <= 2 else "보통" if len(risk_factors) <= 4 else "높음"
        
        html = f"""
        <p><strong>전체 위험도:</strong> <span style="color: {'green' if risk_level == '낮음' else 'orange' if risk_level == '보통' else 'red'}">{risk_level}</span></p>
        <p><strong>주요 위험 요소:</strong></p>
        <ul>
            {''.join(f'<li>{factor}</li>' for factor in risk_factors)}
        </ul>
        """
        return html
    
    def _create_highlights(self, highlights: List[Dict[str, Any]]) -> str:
        """하이라이트 섹션 생성"""
        html_parts = []
        
        for highlight in highlights:
            category_class = highlight['category'].replace('_', '-')
            html_parts.append(f"""
            <div style="margin: 15px 0;">
                <span class="category-badge {category_class}">{highlight['category'].upper()}</span>
                <span class="highlight">{highlight['text']}</span>
                <p style="color: #666; font-size: 14px; margin: 5px 0;">
                    문맥: {highlight['context']}
                </p>
            </div>
            """)
        
        return ''.join(html_parts)
    
    def _create_terms_section(self, term_explanations: List[Dict[str, Any]]) -> str:
        """용어 설명 섹션 생성"""
        html_parts = []
        
        for explanation in term_explanations:
            html_parts.append(f"""
            <div class="term-explanation">
                <h3>{explanation['term']}</h3>
                <p>{explanation['definition']}</p>
                {self._create_mini_laws_section(explanation.get('relevant_laws', []))}
            </div>
            """)
        
        return ''.join(html_parts)
    
    def _create_laws_section(self, laws: List[Dict[str, Any]]) -> str:
        """법령 섹션 생성"""
        html_parts = []
        
        for law in laws:
            html_parts.append(f"""
            <div class="law-reference">
                <h3>{law['law_name']} {law['article_no']}조</h3>
                <p>{law['content']}</p>
                <p style="color: #666; font-size: 14px;">관련도: {law['relevance_score']:.2%}</p>
            </div>
            """)
        
        return ''.join(html_parts)
    
    def _create_mini_laws_section(self, laws: List[Dict[str, Any]]) -> str:
        """용어 설명 내 작은 법령 섹션"""
        if not laws:
            return ""
        
        html_parts = ["<div style='margin-top: 10px; font-size: 14px;'><strong>관련 법령:</strong><ul>"]
        
        for law in laws[:2]:  # 최대 2개만
            html_parts.append(f"<li>{law['law_name']} {law['article_no']}조</li>")
        
        html_parts.append("</ul></div>")
        return ''.join(html_parts)
    
    def _highlight_contract_text(self, text: str, highlights: List[Dict[str, Any]]) -> str:
        """계약서 원문에 하이라이트 적용"""
        # 간단한 구현 - 실제로는 더 정교한 처리 필요
        highlighted_text = text
        
        for highlight in highlights:
            highlighted_text = highlighted_text.replace(
                highlight['text'],
                f'<span class="highlight">{highlight["text"]}</span>'
            )
        
        return highlighted_text
    
    def save_visualization(self, html_content: str, filepath: str):
        """HTML 파일로 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"시각화 결과가 {filepath}에 저장되었습니다.")