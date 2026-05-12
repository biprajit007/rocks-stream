#!/usr/bin/env bash
set -euo pipefail

: "${AWS_ROUTE53_ZONE_ID:?Set AWS_ROUTE53_ZONE_ID}"
: "${PUBLIC_DOMAIN:?Set PUBLIC_DOMAIN}"

TARGET_IP="${1:-206.189.128.172}"
TMP_JSON="$(mktemp)"

cat > "$TMP_JSON" <<JSON
{
  "Comment": "UPSERT A record for Rocks Stream",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "${PUBLIC_DOMAIN}",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{ "Value": "${TARGET_IP}" }]
      }
    }
  ]
}
JSON

aws route53 change-resource-record-sets --hosted-zone-id "$AWS_ROUTE53_ZONE_ID" --change-batch "file://$TMP_JSON"
rm -f "$TMP_JSON"
