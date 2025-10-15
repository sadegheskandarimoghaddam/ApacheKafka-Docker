#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while getopts ":c:p:t:m:" opt; do
  case $opt in
    c) consumer_count=$OPTARG ;;
    p) producer_count=$OPTARG ;;
    t) topic_name=$OPTARG ;;
    m) message_text=$OPTARG ;;
    \?) echo "Usage: run.sh -c <num_consumers> -p <num_producers> -t <topic_name> -m <message_text>"
        exit 1 ;;
  esac
done

if [ -z "$consumer_count" ] || [ -z "$producer_count" ] || [ -z "$topic_name" ] || [ -z "$message_text" ]; then
  echo "All parameters (-c, -p, -t, -m) are required"
  exit 1
fi

export TOPIC_NAME=$topic_name
export MESSAGE_TEXT=$message_text

# start kafka & kafka-ui
docker compose up -d kafka kafka-ui

# wait a few seconds for Kafka to be ready
echo "⏳ Waiting for Kafka to start..."
sleep 5

# scale consumers and producers
docker compose up -d --scale consumer=$consumer_count --scale producer=$producer_count

echo "All services started!"

echo "📂 Data will be saved in: $PROJECT_DIR/data/message_counts"