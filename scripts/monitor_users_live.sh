#!/bin/bash
# Live monitoring of LLM endpoint users

LOG_FILE="logs/nemo_gateway.log"

# Function to display current stats
show_stats() {
    clear
    echo "=== LLM Endpoint Live Monitor ==="
    echo "=================================="
    echo "Last Updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # Show unique users in the last 200 lines
    echo "Active Users (recent activity):"
    tail -500 "$LOG_FILE" | \
      grep -E "\[llm-gateway\].*\[[^]]+\] Request:" | \
      grep -oE "\[[0-9.a-zA-Z-]+\] Request:" | \
      sed 's/ Request://' | \
      sort | uniq -c | sort -rn | \
      awk '{printf "  %-30s %5d requests\n", $2, $1}'

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Recent Requests (last 15) - with API Keys:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -500 "$LOG_FILE" | \
      grep -E "\[llm-gateway\].*\[(.*)\] Request:" | \
      tail -15 | \
      sed 's/\[llm-gateway\] \[INFO\] //' | \
      awk '{
        timestamp = $1 " " $2;
        user = $3;

        # Extract API key if present
        key = "";
        for (i=1; i<=NF; i++) {
          if ($i == "Key:") {
            key = $(i+1);
            break;
          }
        }

        if (key != "") {
          printf "  %s %-20s Model: %-20s Key: %s\n", timestamp, user, $5, key;
        } else {
          printf "  %s %-20s %s %s %s\n", timestamp, user, $4, $5, $6;
        }
      }'

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "API Key Usage Summary:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -500 "$LOG_FILE" | \
      grep -E "Key: " | \
      grep -oE "Key: [A-Z0-9a-z.-]+" | \
      sort | uniq -c | sort -rn | \
      awk '{printf "  %-35s %5d requests\n", $2 " " $3, $1}'

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Live Stream (new requests appear here):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Show initial stats
show_stats

# Follow the log file and show new requests
tail -f "$LOG_FILE" | grep --line-buffered -E "\[llm-gateway\].*\[(.*)\] (Request|Response):" | while read line; do
    # Extract timestamp, user, and message
    timestamp=$(echo "$line" | awk '{print $1, $2}')
    user=$(echo "$line" | grep -oE "\[[0-9.a-zA-Z-]+\] (Request|Response):" | head -1 | sed 's/ Request://' | sed 's/ Response://')
    message=$(echo "$line" | sed 's/.*\[INFO\] //')

    # Display the live event
    echo "  $timestamp $message"

    # Refresh stats every 10 requests (optional)
    if [ $((RANDOM % 10)) -eq 0 ]; then
        show_stats
    fi
done
