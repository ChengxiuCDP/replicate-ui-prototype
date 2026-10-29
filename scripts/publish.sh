#!/bin/bash
# 上传 HTML 原型到内网静态站点，输出可分享 URL
# 用法: publish.sh <html文件> [已有id]
#   不传 id = 首次上传，从返回 JSON 里记住 id
#   传 id   = 复用该 id 更新内容，URL 保持不变（已发出去的链接仍有效）
set -e

: "${UPLOAD_ENDPOINT:?Set UPLOAD_ENDPOINT to your HTML upload service URL}"

HTML="$1"
ID="$2"

[ -f "$HTML" ] || { echo "file not found: $HTML" >&2; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cp "$HTML" "$TMP/index.html"
(cd "$TMP" && zip -qr bundle.zip index.html)

if [ -n "$ID" ]; then
  curl -s -F "file=@$TMP/bundle.zip" "$UPLOAD_ENDPOINT?id=$ID"
else
  curl -s -F "file=@$TMP/bundle.zip" "$UPLOAD_ENDPOINT"
fi
echo
