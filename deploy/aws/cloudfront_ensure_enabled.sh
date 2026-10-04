#!/usr/bin/env bash
# Check that the stage's CloudFront distribution exists and is enabled; enable it if it is not.
#
#   usage: cloudfront_ensure_enabled.sh <distribution-id-or-empty> <stack-name>
#
# When the stack was deployed without a custom domain there is no distribution: say so and
# exit 0 (the Function URL is the public endpoint). When there is one and it is disabled —
# someone disabled it in the console, or a previous teardown half-finished — re-enable it and
# wait for the change to deploy, so a "green" pipeline never leaves a dark edge behind.
set -euo pipefail

DIST_ID="${1:-}"
STACK="${2:-}"

if [ -z "$DIST_ID" ] || [ "$DIST_ID" = "None" ]; then
  echo "No CloudFront distribution for $STACK (no custom domain configured) — the Function URL is the public endpoint."
  exit 0
fi

STATUS=$(aws cloudfront get-distribution --id "$DIST_ID" --query 'Distribution.Status' --output text)
ENABLED=$(aws cloudfront get-distribution --id "$DIST_ID" --query 'Distribution.DistributionConfig.Enabled' --output text)
DOMAIN=$(aws cloudfront get-distribution --id "$DIST_ID" --query 'Distribution.DomainName' --output text)
echo "Distribution $DIST_ID ($DOMAIN): status=$STATUS enabled=$ENABLED"

if [ "$ENABLED" != "True" ]; then
  echo "Distribution is disabled — enabling."
  aws cloudfront get-distribution-config --id "$DIST_ID" > /tmp/dist.json
  ETAG=$(python3 -c "import json;print(json.load(open('/tmp/dist.json'))['ETag'])")
  python3 - <<'PY'
import json
d = json.load(open('/tmp/dist.json'))['DistributionConfig']
d['Enabled'] = True
json.dump(d, open('/tmp/dist-config.json', 'w'))
PY
  aws cloudfront update-distribution --id "$DIST_ID" --if-match "$ETAG" --distribution-config file:///tmp/dist-config.json > /dev/null
  echo "Waiting for the distribution to deploy…"
  aws cloudfront wait distribution-deployed --id "$DIST_ID"
  echo "Enabled."
fi

# The one thing we never want silently: an error-response rewrite on /api/* (pack Q11).
REWRITES=$(aws cloudfront get-distribution-config --id "$DIST_ID" --query 'DistributionConfig.CustomErrorResponses.Quantity' --output text)
if [ "$REWRITES" != "0" ]; then
  echo "::warning::Distribution $DIST_ID has $REWRITES custom error responses — API status codes may be rewritten at the edge."
fi
echo "CloudFront OK."
