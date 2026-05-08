#!/bin/bash
# List all user requests from the logs

LOG_FILE="logs/nemo_gateway.log"

echo "=== All User Requests History ==="
echo "=================================="
echo ""

# Count total requests
TOTAL=$(grep -c "\[llm-gateway\].*Request:" "$LOG_FILE" 2>/dev/null || echo "0")
echo "Total Requests: $TOTAL"
echo ""

# Show all unique users
echo "All Users (entire history):"
grep -E "\[llm-gateway\].*\[[^]]+\] Request:" "$LOG_FILE" | \
  grep -oE "\[[0-9.a-zA-Z-]+\] Request:" | \
  sed 's/ Request://' | \
  sort | uniq -c | sort -rn | \
  awk '{printf "  %-30s %5d requests\n", $2, $1}'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Requests by Model:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -E "\[llm-gateway\].*Request:" "$LOG_FILE" | \
  grep -oE "Request: [a-zA-Z0-9.-]+ -" | \
  sed 's/Request: //' | sed 's/ -//' | \
  sort | uniq -c | sort -rn | \
  awk '{printf "  %-30s %5d requests\n", $2, $1}'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "User → Model Breakdown:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -E "\[llm-gateway\].*\[[^]]+\] Request:" "$LOG_FILE" | \
  awk -F'[][]' '{user=$2; match($0, /Request: ([a-z0-9.-]+)/, model); print user, model[1]}' | \
  sort | uniq -c | sort -rn | \
  awk '{printf "  %-25s → %-25s %5d requests\n", $2, $3, $1}'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Token Usage by User:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -E "\[llm-gateway\].*Response:.*tokens" "$LOG_FILE" | \
  awk -F'[][]' '{user=$2; match($0, /([0-9]+) tokens/, tokens); match($0, /Input: ([0-9]+)/, inp); match($0, /Output: ([0-9]+)/, out); print user, tokens[1], inp[1], out[1]}' | \
  awk '{users[$1]+=$2; input[$1]+=$3; output[$1]+=$4; count[$1]++}
       END {for (u in users) printf "  %-25s %10d tokens (%d requests) | Input: %d | Output: %d\n", u, users[u], count[u], input[u], output[u]}' | \
  sort -k2 -rn

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Recent 20 Requests (with API Keys):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -E "\[llm-gateway\].*\[(.*)\] Request:" "$LOG_FILE" | \
  tail -20 | \
  sed 's/\[llm-gateway\] \[INFO\] //' | \
  awk '{
    # Extract timestamp, user, and check for "Key:" field
    timestamp = $1 " " $2;
    user = $3;

    # Find "Key:" in the line
    key_idx = 0;
    for (i=1; i<=NF; i++) {
      if ($i == "Key:") {
        key_idx = i+1;
        break;
      }
    }

    if (key_idx > 0) {
      printf "  %s %-20s Model: %-20s Key: %s\n", timestamp, user, $5, $key_idx;
    } else {
      printf "  %s %-20s %s %s %s\n", timestamp, user, $4, $5, $6;
    }
  }'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "API Key Usage Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -E "\[llm-gateway\].*Key:" "$LOG_FILE" | \
  grep -oE "Key: [A-Z0-9.-]+" | \
  sort | uniq -c | sort -rn | \
  awk '{printf "  %-30s %5d requests\n", $2 " " $3, $1}'

echo ""
