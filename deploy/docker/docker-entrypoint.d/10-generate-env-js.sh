#!/usr/bin/env sh
set -eu

ENV_JS_PATH="/usr/share/nginx/html/env.js"

BACKEND_URL="${BACKEND_URL:-}"
API_TOKEN="${API_TOKEN:-}"

if [ -n "${BACKEND_URL}" ]; then
  # escape for JS double-quoted string
  BACKEND_URL_ESCAPED="$(printf '%s' "${BACKEND_URL}" | sed 's/\\/\\\\/g; s/\"/\\"/g')"
  BACKEND_URL_JS="\"${BACKEND_URL_ESCAPED}\""
else
  BACKEND_URL_JS="\"\""
fi

# 访问令牌：与后端 API_AUTH_TOKEN 对应；未设置时输出空串。
API_TOKEN_ESCAPED="$(printf '%s' "${API_TOKEN}" | sed 's/\\/\\\\/g; s/\"/\\"/g')"
API_TOKEN_JS="\"${API_TOKEN_ESCAPED}\""

cat > "${ENV_JS_PATH}" <<EOF
window.__ENV = window.__ENV || {};
window.__ENV.BACKEND_URL = ${BACKEND_URL_JS};
window.__ENV.API_TOKEN = ${API_TOKEN_JS};
EOF

