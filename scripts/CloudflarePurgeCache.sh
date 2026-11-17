#!/bin/bash

set -euo pipefail

if [[ -n "${CLOUDFLARE_KEY:-}" ]]; then
  if [[ -z "${CLOUDFLARE_EMAIL:-}" ]]; then
    echo "CLOUDFLARE_EMAIL is required when using a Global API Key." >&2
    exit 1
  fi
  AUTH_HEADERS=(-H "X-Auth-Email: ${CLOUDFLARE_EMAIL}" -H "X-Auth-Key: ${CLOUDFLARE_KEY}")
elif [[ -n "${CLOUDFLARE_TOKEN:-}" ]]; then
  AUTH_HEADERS=(-H "Authorization: Bearer ${CLOUDFLARE_TOKEN}")
else
  echo "CLOUDFLARE_TOKEN (or CLOUDFLARE_KEY and CLOUDFLARE_EMAIL) is required." >&2
  exit 1
fi

if [[ -z "${CLOUDFLARE_ZONE:-}" ]]; then
  echo "CLOUDFLARE_ZONE is required." >&2
  exit 1
fi

if [[ -n "${PURGE_URLS:-}" ]]; then
  BODY=$(python3 -c '
import json, os, sys
try:
    urls = json.loads(os.environ["PURGE_URLS"])
    if not isinstance(urls, list) or not urls or not all(isinstance(u, str) and u for u in urls):
        raise ValueError("expected a non-empty JSON array of URL strings")
except (ValueError, TypeError) as error:
    print(f"Invalid PURGE_URLS: {error}", file=sys.stderr)
    sys.exit(1)
print(json.dumps({"files": urls}))
')
else
  BODY='{"purge_everything":true}'
fi

HTTP_RESPONSE=$(curl --silent --show-error \
  --connect-timeout 10 --max-time 60 \
  --retry 2 --retry-delay 1 --retry-max-time 120 \
  "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE}/purge_cache" \
  -H "Content-Type: application/json" \
  "${AUTH_HEADERS[@]}" \
  --write-out "HTTP_STATUS:%{http_code}" \
  --data "$BODY")

HTTP_STATUS="${HTTP_RESPONSE##*HTTP_STATUS:}"
HTTP_BODY="${HTTP_RESPONSE%HTTP_STATUS:*}"

if [[ "$HTTP_STATUS" == "200" ]] && printf '%s' "$HTTP_BODY" | python3 -c '
import json, sys
try:
    response = json.load(sys.stdin)
    valid = isinstance(response, dict) and response.get("success") is True
except (ValueError, TypeError):
    valid = False
sys.exit(0 if valid else 1)
'; then
  echo "Cloudflare accepted the cache purge."
else
  echo "Cache purge failed (HTTP ${HTTP_STATUS}): ${HTTP_BODY}" >&2
  exit 1
fi
