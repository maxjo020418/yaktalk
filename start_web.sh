#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# venv 실핼
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
    echo "Virtual environment 활성화됨"
else
    echo "Virtual environment를 찾을 수 없습니다. '.venv/bin/activate' 파일이 없습니다."
    exit 1
fi

# 환경 변수 로드
if [ -f .env ]; then
    echo ".env 파일 발견"
else
    echo ".env 파일이 없습니다. 환경 설정을 확인하세요."
    echo "    .env.example 파일을 참고하여 .env 파일을 생성하세요."
fi

echo "Python 패키지 확인 중..."
if python -c "import chainlit" 2>/dev/null; then
    echo "Chainlit 패키지 확인됨"
else
    echo "Chainlit 패키지가 설치되지 않았습니다."
    echo "    requirements.txt 참조"
    exit 1
fi

# Ollama 서버 상태 확인 (선택적)
echo "Ollama 서버 상태 확인 중..."
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "Ollama 서버가 실행 중입니다"
else
    echo "Ollama 서버가 실행되지 않았습니다."
    echo "    OpenAI API를 사용하는 경우 무시해도 됩니다."
    echo "    Ollama를 사용하려면 'ollama serve' 명령으로 시작하세요."
fi

# 포트 설정 (기본값: 8000)
PORT=${1:-8000}

# 기존 chainlit 프로세스 종료
echo "기존 프로세스 정리 중..."
pkill -f "chainlit run" 2>/dev/null || true
sleep 1

echo ""
echo "YakTalk 법률 AI 어시스턴트를 시작합니다..."
echo ""

# Chainlit 애플리케이션 실행
chainlit run app.py --port $PORT
