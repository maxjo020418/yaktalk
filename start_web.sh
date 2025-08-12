#!/bin/bash

# Yaktalk Web UI 시작 스크립트

cd /home/maxjo/Projects/yaktalk

# Virtual environment 활성화
source .venv/bin/activate

# 환경 변수 로드 확인
if [ -f .env ]; then
    echo "✅ .env 파일 발견"
else
    echo "⚠️  .env 파일이 없습니다. 환경 설정을 확인하세요."
fi

# Ollama 서버 상태 확인
echo "🔍 Ollama 서버 상태 확인 중..."
if curl -s http://localhost:11434/api/version > /dev/null; then
    echo "✅ Ollama 서버가 실행 중입니다"
else
    echo "⚠️  Ollama 서버가 실행되지 않았습니다. 'ollama serve' 명령으로 시작하세요."
fi

# 기존 chainlit 프로세스 종료
echo "🔄 기존 프로세스 정리 중..."
pkill -f "chainlit run" 2>/dev/null || true

echo ""
echo "🚀 법률 AI 어시스턴트 웹 인터페이스를 시작합니다..."
echo "📋 브라우저에서 http://localhost:8001 으로 접속하세요"
echo "💡 파일 업로드가 수정되어 이제 PDF를 정상적으로 업로드할 수 있습니다"
echo ""

# Chainlit 애플리케이션 실행
chainlit run app.py --port 8001
