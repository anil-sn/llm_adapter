#!/bin/bash
# Monitor users accessing the LLM endpoint

LOG_FILE="logs/nemo_gateway.log"

echo "=== LLM Endpoint User Monitor ==="
echo "=================================="
echo ""

# Show unique users in the last N lines
echo "Active Users (last 100 requests):"
tail -1000 "$LOG_FILE" | \
  grep -E "\[llm-gateway\].*\[[^]]+\] Request:" | \
  grep -oE "\[[0-9.a-zA-Z-]+\] Request:" | \
  sed 's/ Request://' | \
  sort | uniq -c | sort -rn | \
  awk '{printf "  %-20s %5d requests\n", $2, $1}'

echo ""
echo "Recent Activity (with API Keys):"
tail -500 "$LOG_FILE" | \
  grep -E "\[llm-gateway\].*\[(.*)\] (Request|Response):" | \
  tail -10 | \
  sed 's/\[llm-gateway\] \[INFO\] //' | \
  awk '{
    # Print timestamp, user, and look for "Key:" field
    printf "  [%s %s] %-15s ", $1, $2, $3;

    # Find and print the rest, highlighting Key if present
    for (i=4; i<=NF; i++) {
      printf "%s ", $i;
    }
    printf "\n";
  }'

echo ""
echo "API Key Usage:"
tail -1000 "$LOG_FILE" | \
  grep -E "Key: " | \
  grep -oE "Key: [A-Z0-9a-z.-]+" | \
  sort | uniq -c | sort -rn | \
  awk '{printf "  %-35s %5d uses\n", $2 " " $3, $1}'

echo ""
echo "Token Usage by User:"
tail -1000 "$LOG_FILE" | \
  grep -E "\[llm-gateway\].*Response:.*tokens" | \
  awk -F'[][]' '{user=$2; match($0, /([0-9]+) tokens/, tokens); print user, tokens[1]}' | \
  awk '{users[$1]+=$2; count[$1]++} END {for (u in users) printf "  %-20s %8d tokens (%d requests)\n", u, users[u], count[u]}' | \
  sort -k2 -rn

echo ""
echo "Live monitoring: tail -f $LOG_FILE | grep '\[.*\] Request:'"
