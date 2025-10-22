#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while getopts ":c:p:t:m:r:d:" opt; do
  case $opt in
    c) consumer_count=$OPTARG ;;
    p) producer_count=$OPTARG ;;
    t) topic_name=$OPTARG ;;
    m) message_text=$OPTARG ;;
    r) rate_per_sec=$OPTARG ;;
    d) duration=$OPTARG ;;
    \?) echo "Usage: run.sh -c <num_consumers> -p <num_producers> -t <topic_name> -m <message_text> -r <messages_per_sec> -d <duration_seconds>"
        exit 1 ;;
  esac
done

if [ -z "$consumer_count" ] || [ -z "$producer_count" ] || [ -z "$topic_name" ] || [ -z "$message_text" ] || [ -z "$rate_per_sec" ] || [ -z "$duration" ]; then
  echo "Usage: run.sh -c <num_consumers> -p <num_producers> -t <topic_name> -m <message_text> -r <messages_per_sec> -d <duration_seconds>"
  exit 1
fi

export TOPIC_NAME=$topic_name
export MESSAGE_TEXT=$message_text
export RATE_PER_SEC=$rate_per_sec
export DURATION=$duration

# راه‌اندازی Kafka و UI
docker compose up -d kafka kafka-ui
echo "⏳ Waiting for Kafka to start..."
sleep 5

# راه‌اندازی producers و consumers
docker compose up -d --scale consumer=$consumer_count --scale producer=$producer_count
echo "✅ All services started!"
echo "📂 Data will be saved in: $PROJECT_DIR/data/message_counts"
echo "🚀 Sending $RATE_PER_SEC messages per second per producer for $DURATION seconds"

# 🛑 در نهایت بعد از زمان مشخص، سرویس‌ها را پایین می‌آورد
sleep "$duration"
echo "🛑 Stopping all services after $duration seconds..."
docker compose down
echo "✅ All services stopped."
