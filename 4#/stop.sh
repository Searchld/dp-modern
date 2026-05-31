#!/bin/bash
set -euo pipefail

APP_HOME="${APP_HOME:-/home/user/project/4#}"
PID_FILE="${PID_FILE:-$APP_HOME/infer.pid}"
ENTRYPOINT="${ENTRYPOINT:-$APP_HOME/infer.py}"

echo "========== 停止 yolov8-infer =========="

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  kill "$(cat "$PID_FILE")"
  rm -f "$PID_FILE"
  echo "进程已关闭"
  exit 0
fi

pkill -f "$ENTRYPOINT" 2>/dev/null || true
rm -f "$PID_FILE"
echo "未找到 PID 文件，已执行兜底停止"
