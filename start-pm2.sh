#!/bin/bash

# PM2로 VeriFit Backend 시작 스크립트

echo "🚀 VeriFit Backend PM2 시작 중..."

# 기존 프로세스 정리
pm2 delete verifit-backend 2>/dev/null || true

# Conda 환경용 설정으로 PM2 시작
pm2 start ecosystem-conda.config.js

# PM2 상태 확인
pm2 status

echo "✅ VeriFit Backend가 PM2로 시작되었습니다!"
echo "📊 상태 확인: pm2 status"
echo "📝 로그 확인: pm2 logs verifit-backend"
echo "🛑 중지: pm2 stop verifit-backend"
echo "🔄 재시작: pm2 restart verifit-backend"
