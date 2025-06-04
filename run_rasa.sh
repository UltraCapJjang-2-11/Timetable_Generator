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

# 사용 가능한 최신 모델 찾기
LATEST_MODEL=$(ls -t models/*.tar.gz | head -n 1)
if [ -z "$LATEST_MODEL" ]; then
    echo "모델을 찾을 수 없습니다. 먼저 모델을 학습합니다..."
    rasa train
    LATEST_MODEL=$(ls -t models/*.tar.gz | head -n 1)
fi

echo "사용할 모델: $LATEST_MODEL"

# Rasa 액션 서버 실행 (백그라운드)
echo "Rasa 액션 서버를 실행합니다 (포트 5056)..."
rasa run actions -p 5056 &
ACTION_PID=$!
sleep 5  # 액션 서버가 시작될 때까지 기다림

# Rasa 서버 실행 (백그라운드)
echo "Rasa 서버를 실행합니다 (포트 5006)..."
rasa run --enable-api --cors "*" -m "$LATEST_MODEL" -p 5006 --endpoints endpoints.yml &
RASA_PID=$!

echo "완료. Rasa 서버가 실행 중입니다."
echo "  - 메인 서버: http://localhost:5006"
echo "  - 액션 서버: http://localhost:5056"
echo ""
echo "현재 실행 중인 프로세스:"
echo "  - Rasa 서버 PID: $RASA_PID"
echo "  - 액션 서버 PID: $ACTION_PID"
echo ""
echo "스크립트를 종료하려면 Ctrl+C를 누른 후, 다음 명령어로 프로세스를 종료하세요:"
echo "  pkill -f 'rasa run'" 