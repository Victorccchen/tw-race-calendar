#!/bin/bash
# 每日刷新進入點。由 launchd 呼叫，輸出寫入 logs/。
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs
STAMP=$(date +%F)
{
  echo "════════ $(date '+%F %T') ════════"
  /usr/bin/python3 refresh.py
  echo "退出碼: $?"
  if [ -d "$ROOT/web/.vercel" ]; then
    echo "--- 部署 ---"; "$ROOT/scheduler/deploy.sh"
  else
    echo "--- 略過部署（web/ 尚未連結 Vercel 專案）---"
  fi
} >> "logs/$STAMP.log" 2>&1

# 只保留 90 天的日誌與快照，異動清單永久保留
find logs -name '*.log' -mtime +90 -delete 2>/dev/null
find data/snapshots -name '*.json' -mtime +90 -delete 2>/dev/null
