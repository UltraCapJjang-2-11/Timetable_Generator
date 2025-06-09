#!/bin/bash

# 작업 디렉토리 설정
BASE_DIR=$(pwd)
RASA_DIR="$BASE_DIR/rasa"
VENV_DIR="$BASE_DIR/venv310"

# 환경 활성화
echo "가상환경을 활성화합니다..."
source "$VENV_DIR/bin/activate"

# Rasa 디렉토리로 이동
cd "$RASA_DIR"

# 기존 프로세스 종료
echo "기존 Rasa 프로세스를 종료합니다..."
pkill -f "rasa run" || true
pkill -f "rasa run actions" || true
sleep 2

# 모델 재학습
echo "Rasa 모델을 학습합니다..."
rasa train

echo "학습이 완료되었습니다. 서버를 시작하려면 ./run_rasa.sh 를 실행하세요." 