#!/bin/bash

# Ollama 서버 상태 확인 스크립트
# 원격 서버에서 실행하세요

echo "=== Ollama 서버 상태 확인 ==="
echo ""

# 1. 현재 Ollama 프로세스 확인
echo "1. Ollama 프로세스 확인:"
ps aux | grep -E "[o]llama|[O]llama" | grep -v grep
echo ""

# 2. 포트 11434 사용 상태 확인
echo "2. 포트 11434 사용 상태:"
sudo lsof -i :11434 2>/dev/null || netstat -tlnp 2>/dev/null | grep :11434
echo ""

# 3. Ollama 서비스 상태 확인 (systemd)
echo "3. Ollama 서비스 상태 (systemd):"
sudo systemctl status ollama 2>/dev/null || echo "systemd 서비스 없음"
echo ""

# 4. 현재 OLLAMA_HOST 환경변수 확인
echo "4. OLLAMA_HOST 환경변수:"
echo "현재 셸: $OLLAMA_HOST"
cat ~/.bashrc ~/.zshrc ~/.profile 2>/dev/null | grep OLLAMA_HOST || echo "설정 파일에 OLLAMA_HOST 없음"
echo ""

# 5. 방화벽 상태 확인
echo "5. 방화벽 상태:"
sudo ufw status 2>/dev/null | grep 11434 || echo "UFW 방화벽 규칙 없음"
sudo iptables -L -n 2>/dev/null | grep 11434 || echo "iptables 규칙 없음"
echo ""

# 6. Ollama API 테스트
echo "6. Ollama API 테스트:"
echo "  - localhost:11434 연결:"
curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && echo "    ✅ 성공" || echo "    ❌ 실패"
echo "  - 0.0.0.0:11434 연결:"
curl -s http://0.0.0.0:11434/api/tags >/dev/null 2>&1 && echo "    ✅ 성공" || echo "    ❌ 실패"
echo ""

echo "=== 해결 방법 ==="
echo ""
echo "만약 Ollama가 localhost에서만 접속 가능하다면:"
echo ""
echo "방법 1: 기존 Ollama 프로세스 종료 후 재시작"
echo "  sudo pkill ollama"
echo "  OLLAMA_HOST=0.0.0.0 ollama serve"
echo ""
echo "방법 2: systemd 서비스 설정 (영구적)"
echo "  sudo mkdir -p /etc/systemd/system/ollama.service.d"
echo "  echo '[Service]' | sudo tee /etc/systemd/system/ollama.service.d/override.conf"
echo "  echo 'Environment=\"OLLAMA_HOST=0.0.0.0\"' | sudo tee -a /etc/systemd/system/ollama.service.d/override.conf"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart ollama"
echo ""
echo "방법 3: Docker 사용"
echo "  docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama"
echo ""
echo "방화벽 포트 열기:"
echo "  sudo ufw allow 11434/tcp"
echo "  또는"
echo "  sudo iptables -A INPUT -p tcp --dport 11434 -j ACCEPT"