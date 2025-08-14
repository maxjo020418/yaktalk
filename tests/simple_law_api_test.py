"""
간단한 법령 API 테스트
"""

import requests
from dotenv import load_dotenv

load_dotenv()

import os
import sys
import requests
from pathlib import Path

# 모듈 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from utils.get_env import OPEN_LAW_GO_ID

def test_law_api():
    """
    법령 정보 API 기본 연결 테스트
    """
    print("🔍 법령 API 연결 테스트 시작")
    
    # 문서에 따르면 OC는 사용자 이메일 ID (예: test)
    # 실제 서비스에서는 정식 키 필요하지만 테스트는 가능
    api_key = OPEN_LAW_GO_ID
    
    print(f"✅ OC 값 사용: {api_key}")
    
    # 기본 URL
    base_url = "http://www.law.go.kr/DRF/lawService.do"
    
    # 문서 예시에 따라 특정 법령 ID로 테스트
    print(f"\n📖 문서 샘플 URL 테스트")
    print("-" * 30)
    
    # 샘플 1: 민법 (ID=009682)
    sample_tests = [
        {"name": "민법 샘플", "ID": "009682"},
        {"name": "민법 샘플", "MST": "261457"}
    ]
    
    for test in sample_tests:
        print(f"\n🔍 테스트: {test['name']}")
        
        # 파라미터 설정
        params = {
            'OC': api_key,  # 사용자 ID
            'target': 'law',
            'type': 'JSON'
        }
        
        # ID 또는 MST 추가
        if 'ID' in test:
            params['ID'] = test['ID']
        elif 'MST' in test:
            params['MST'] = test['MST']
        
        try:
            # API 요청
            response = requests.get(base_url, params=params)
            print(f"HTTP 상태: {response.status_code}")
            
            if response.status_code == 200:
                print(f"Content-Type: {response.headers.get('content-type')}")
                print(f"응답 전체 길이: {len(response.text)}")
                
                try:
                    # JSON으로 파싱 시도
                    data = response.json()
                    print(f"✅ JSON 파싱 성공!")
                    print(f"응답 키들: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    
                    if isinstance(data, dict) and '법령' in data:
                        law_data = data['법령']
                        print(f"📋 법령 데이터 구조:")
                        
                        # 법령 기본 정보 확인
                        if isinstance(law_data, dict):
                            print(f"  법령 키들: {list(law_data.keys())[:10]}")
                            
                            # 기본 정보 찾기
                            basic_fields = ['법령명_한글', '법령ID', '공포일자', '시행일자', '소관부처명']
                            for field in basic_fields:
                                if field in law_data:
                                    print(f"  {field}: {law_data[field]}")
                            
                            # 조문 정보 확인
                            if '조문' in law_data:
                                articles = law_data['조문']
                                if isinstance(articles, list):
                                    print(f"  📜 조문 수: {len(articles)}개")
                                    if len(articles) > 0:
                                        first_article = articles[0]
                                        if isinstance(first_article, dict):
                                            print(f"  첫 번째 조문: {first_article.get('조문제목', 'N/A')}")
                                            print(f"  조문내용: {str(first_article.get('조문내용', ''))[:100]}...")
                        
                        # 파일로 저장
                        import json
                        with open(f'law_sample_{test.get("ID", test.get("MST"))}.json', 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        print(f"  💾 데이터를 파일로 저장했습니다.")
                    
                except Exception as json_error:
                    print(f"❌ JSON 파싱 실패: {json_error}")
                    print(f"응답 내용: {response.text[:500]}...")
                
            else:
                print(f"❌ HTTP 오류: {response.status_code}")
                print(f"오류 내용: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
    
    # API 정보 안내
    print(f"\n" + "=" * 50)
    print("📚 API 문서 및 정보:")
    print("- 가이드: https://www.law.go.kr/LSW/openApi/openApiGuide.do")
    print("- 호출 제한: 일일 1000회 (무료)")
    print("- 응답 형식: JSON, XML 지원")
    print("- 검색 대상: law(법령), article(조문), prec(판례)")

if __name__ == "__main__":
    test_law_api()