#!/usr/bin/env bash
set -euo pipefail

# ----------------------------
# Parse command-line arguments
# ----------------------------
# Added 'i:' to the getopts string
while getopts ":c:p:t:m:r:x:f:k:b:l:i:" opt; do
  case $opt in
    i) history_id=$OPTARG ;;
    c) consumer_count=$OPTARG ;;
    p) producer_count=$OPTARG ;;
    t) topic_name=$OPTARG ;;
    m) message_text=$OPTARG ;;
    r) rate_per_sec=$OPTARG ;;
    x) partitions=$OPTARG ;;
    f) replication_factor=$OPTARG ;;
    k) kafka_count=$OPTARG ;;
    b) BATCH_SIZE_BYTES=$OPTARG ;;
    l) LINGER_MS=$OPTARG ;;
    \?) exit 1 ;;
  esac
done

# ----------------------------
# Defaults & Exports
# ----------------------------
history_id=${history_id:-"manual"}
kafka_count=${kafka_count:-3}
producer_count=${producer_count:-1}
consumer_count=${consumer_count:-1}
partitions=${partitions:-6}
replication_factor=${replication_factor:-3}

export TOPIC_NAME=${topic_name:-test-topic}
export MESSAGE_TEXT=${message_text:-"hello"}
export RATE_PER_SEC=${rate_per_sec:-1}
export BATCH_SIZE_BYTES=${BATCH_SIZE_BYTES:-16384}
export LINGER_MS=${LINGER_MS:-5}

# ----------------------------
# Folder Management
# ----------------------------
BASE_DATA_DIR="$(pwd)/data"
HISTORY_DIR="$BASE_DATA_DIR/$history_id"

echo "📁 Creating and cleaning history directory: $HISTORY_DIR"
mkdir -p "$HISTORY_DIR"
# Give full permissions so the Docker user (appuser) can write results
chmod -R 777 "$HISTORY_DIR"

# ----------------------------
# Generate docker-compose.override.yml
# ----------------------------
# We use this to force Kafka to be ephemeral and Producer/Consumer to use the History folder
OVERRIDE="$HISTORY_DIR/docker-compose.override.yml"
echo "services:" > "$OVERRIDE"

# 1. Force Kafka 1-3 to be volume-less (no host folders)
for i in $(seq 1 3); do
  cat >> "$OVERRIDE" <<EOF
  kafka${i}:
    volumes: []
    environment:
      - KAFKA_LOG_DIRS=/tmp/kafka-logs
EOF
done

# 2. Map Producer/Consumer to the specific History folder
cat >> "$OVERRIDE" <<EOF
  producer:
    volumes:
      - ${HISTORY_DIR}:/app/message_counts
  consumer:
    volumes:
      - ${HISTORY_DIR}:/app/message_counts
EOF

# 3. Add extra brokers if k > 3
QUORUM="1@kafka1:9093,2@kafka2:9093,3@kafka3:9093"
if [ "$kafka_count" -gt 3 ]; then
    for i in $(seq 4 $kafka_count); do
        host_port=$((9092 + i - 1))
        cat >> "$OVERRIDE" <<EOF
  kafka${i}:
    image: apache/kafka:latest
    container_name: kafka${i}
    ports:
      - "${host_port}:9092"
    environment:
      KAFKA_NODE_ID: ${i}
      KAFKA_PROCESS_ROLES: broker
      KAFKA_CLUSTER_ID: "BfCkSkDsTt-Ro0Gd2J3s1Q"
      KAFKA_CONTROLLER_QUORUM_VOTERS: ${QUORUM}
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka${i}:9092
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LOG_DIRS: /tmp/kafka-logs
EOF
    done
fi

# ----------------------------
# Start Services
# ----------------------------
echo "🚀 Starting services (using override for isolation)..."
# We must include the -f override in ALL commands
docker compose -f docker-compose.yml -f "$OVERRIDE" down --remove-orphans
docker compose -f docker-compose.yml -f "$OVERRIDE" up -d kafka1 kafka2 kafka3

echo "⏳ Waiting for kafka1..."
tries=0
until docker exec kafka1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092 --list > /dev/null 2>&1; do
  tries=$((tries+1))
  if [ $tries -gt 20 ]; then exit 1; fi
  sleep 2
done

echo "📌 Creating topic $TOPIC_NAME..."
docker exec kafka1 /opt/kafka/bin/kafka-topics.sh \
  --create --topic "$TOPIC_NAME" --partitions "$partitions" \
  --replication-factor "$replication_factor" --bootstrap-server kafka1:9092 --if-not-exists

echo "🚀 Scaling producers/consumers..."
docker compose -f docker-compose.yml -f "$OVERRIDE" up -d --scale producer="$producer_count" --scale consumer="$consumer_count"


echo "🎉 Done. Results in $HISTORY_DIR"

# ----------------------------
# Mark system as ready
# ----------------------------
READY_FILE="$HISTORY_DIR/ready.flag"

echo "✅ All containers are up. Marking system as ready."
touch "$READY_FILE"
