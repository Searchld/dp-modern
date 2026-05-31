#!/bin/bash
set -euo pipefail

APP_HOME="${APP_HOME:-/home/user/project/4#}"
PYTHON_BIN="${PYTHON_BIN:-/opt/anaconda3/envs/yunnan/bin/python3}"
ENTRYPOINT="${ENTRYPOINT:-$APP_HOME/infer.py}"
LOG_DIR="${LOG_DIR:-$APP_HOME/logs}"
PID_FILE="${PID_FILE:-$APP_HOME/infer.pid}"
RUNTIME_ENV_FILE_PATH="${RUNTIME_ENV_FILE:-$APP_HOME/config/runtime.env}"

mkdir -p "$LOG_DIR"
cd "$APP_HOME"

# 优先按 ENTRYPOINT 判断，避免 PID 文件丢失/误写导致重复启动。
if pgrep -f "$ENTRYPOINT" >/dev/null 2>&1; then
  RUNNING_PID="$(pgrep -f "$ENTRYPOINT" | head -n 1)"
  echo "$RUNNING_PID" > "$PID_FILE" 2>/dev/null || true
  echo "服务已在运行，PID: $RUNNING_PID"
  exit 0
fi

if [[ -f "$PID_FILE" ]] && ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  rm -f "$PID_FILE"
fi

echo "========== 配置预检 =========="
echo "========== 启动 yolov8-infer =========="
#(yunnan) user@user-Rack-Server:~$ nvidia-smi -L
#GPU 0: Tesla T4 (UUID: GPU-b1fbc62d-8487-4b7c-aa64-23e2d5b7d88d)
#GPU 1: Tesla T4 (UUID: GPU-2c2f618b-6555-0366-b120-f0fce722bc6a)
#(yunnan) user@user-Rack-Server:~$ 

CUDA_VISIBLE_DEVICES=GPU-2c2f618b-6555-0366-b120-f0fce722bc6a nohup "$PYTHON_BIN" "$ENTRYPOINT" >> "$LOG_DIR/stdout.log" 2>&1 &
echo $! > "$PID_FILE"

echo "启动成功，进程PID: $(cat "$PID_FILE")"
echo "日志路径：$LOG_DIR"
