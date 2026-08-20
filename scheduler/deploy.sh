#!/bin/bash
# 每日刷新後部署到 Vercel。需先完成一次 `npx vercel login` 與 `npx vercel link`。
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/web"
if [ ! -d .vercel ]; then
  echo "尚未連結 Vercel 專案。請先在 $ROOT/web 執行："
  echo "  npx vercel login && npx vercel link"
  exit 1
fi
npx --yes vercel deploy --prod --yes
