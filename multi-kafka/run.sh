#!/usr/bin/env bash
set -euo pipefail

# Usage example:
# ./run.sh -c 2 -p 2 -t test-topic -m "Hello" -r 200 -d 30 -x 6 -f 3 -k 5

# ----------------------------
# Parse command-line arguments
# ----------------------------
while getopts ":c:p:t:m:r:d:x:f:k:b:l:" opt; do
  case $opt in
    c) consumer_count=$OPTARG ;;
    p) producer_count=$OPTARG ;;
    t) topic_name=$OPTARG ;;
    m) message_text=$OPTARG ;;
    r) rate_per_sec=$OPTARG ;;
    d) duration=$OPTARG ;;
    x) partitions=$OPTARG ;;
    f) replication_factor=$OPTARG ;;
    k) kafka_count=$OPTARG ;;
    b) BATCH_SIZE_BYTES=$OPTARG ;;   # Kafka producer batch size in bytes
    l) LINGER_MS=$OPTARG ;;          # Kafka producer linger.ms

    \?) 
      echo "Usage: run.sh -c <cons> -p <prod> -t <topic> -m <msg> -r <rate> -d <dur> -x <part> -f <rf> -k <kafka_count>"
      exit 1
      ;;
  esac
done

# ----------------------------
# Defaults
# ----------------------------
kafka_count=${kafka_count:-3}
producer_count=${producer_count:-1}
consumer_count=${consumer_count:-1}
partitions=${partitions:-6}
replication_factor=${replication_factor:-3}


if [ "$kafka_count" -lt 3 ]; then
  echo "⚠️ kafka_count < 3 — حداقل 3 نود برای quorum لازم است. استفاده از 3."
  kafka_count=3
fi

export TOPIC_NAME=${topic_name:-test-topic}
export MESSAGE_TEXT=${message_text:-"hello"}
export RATE_PER_SEC=${rate_per_sec:-1}
export DURATION=${duration:-""}
export BATCH_SIZE_BYTES=${BATCH_SIZE_BYTES:-16384}  # default 16 KB
export LINGER_MS=${LINGER_MS:-5}                    # default 5 ms




echo "🔧 Requested brokers: $kafka_count (first 3 => controllers)"
echo "🔧 Partitions: $partitions  Replication: $replication_factor"
echo "🔧 Producers: $producer_count  Consumers: $consumer_count"

# ----------------------------
# Ensure data directories exist with correct permissions
# ----------------------------
BASE_DATA_DIR="$(pwd)/data"
mkdir -p "$BASE_DATA_DIR"

echo "📁 Ensuring $BASE_DATA_DIR exists and writable..."
for i in $(seq 1 $kafka_count); do
  dir="$BASE_DATA_DIR/kafka${i}"
  mkdir -p "$dir"
  sudo chown -R "$USER":"$USER" "$dir" || true
  sudo chmod -R 0777 "$dir" || true
done

# message_counts dir
mkdir -p "$BASE_DATA_DIR/message_counts"
sudo chown -R "$USER":"$USER" "$BASE_DATA_DIR/message_counts" || true
sudo chmod -R 0777 "$BASE_DATA_DIR/message_counts" || true

# ----------------------------
# Build controller quorum (first 3 only)
# ----------------------------
QUORUM=""
for i in $(seq 1 3); do
  if [ $i -eq 1 ]; then
    QUORUM="${i}@kafka${i}:9093"
  else
    QUORUM="${QUORUM},${i}@kafka${i}:9093"
  fi
done
echo "🧩 Controller quorum: $QUORUM"

# ----------------------------
# Generate docker-compose.override.yml for extra brokers
# ----------------------------
OVERRIDE="docker-compose.override.yml"

if [ "$kafka_count" -gt 3 ]; then
    echo "services:" > "$OVERRIDE"

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
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka${i}:9092
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_LOG_DIRS: /kafka/data
    volumes:
      - ./data/kafka${i}:/kafka/data

EOF
    done
else
    rm -f "$OVERRIDE"
fi

# ----------------------------
# Start base services (kafka1..3 + producer/consumer)
# ----------------------------
echo "🚀 Starting kafka1..kafka3 and base services..."
docker compose up -d kafka1 kafka2 kafka3 || { echo "docker compose up failed"; exit 1; }

# ----------------------------
# Start additional brokers (4..N)
# ----------------------------
if [ "$kafka_count" -gt 3 ]; then
  echo "🚀 Starting additional brokers (4..$kafka_count)..."
  docker compose -f docker-compose.yml -f "$OVERRIDE" up -d $(for i in $(seq 4 $kafka_count); do echo -n "kafka${i} "; done)
fi

# ----------------------------
# Wait for kafka1 to be ready
# ----------------------------
echo "⏳ Waiting for kafka1..."
tries=0
until docker exec kafka1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092 --list > /dev/null 2>&1; do
  tries=$((tries+1))
  if [ $tries -gt 20 ]; then
    echo "❌ kafka1 not ready; check docker logs kafka1"
    exit 1
  fi
  sleep 2
done
echo "✅ kafka1 ready."

# ----------------------------
# Create topic if provided
# ----------------------------
if [ -n "${topic_name:-}" ]; then
  echo "📌 Creating topic $topic_name (p=$partitions rf=$replication_factor) if not exists..."
  docker exec kafka1 /opt/kafka/bin/kafka-topics.sh \
    --create \
    --topic "$topic_name" \
    --partitions "$partitions" \
    --replication-factor "$replication_factor" \
    --config min.insync.replicas=2 \
    --bootstrap-server kafka1:9092 \
    --if-not-exists
fi

# ----------------------------
# Start producers/consumers scaled
# ----------------------------
echo "🚀 Starting producers/consumers (producer=$producer_count consumer=$consumer_count)..."
docker compose up -d --scale producer="$producer_count" --scale consumer="$consumer_count"

# ----------------------------
# Optional: stop cluster after $DURATION seconds
# ----------------------------
if [ -n "$DURATION" ]; then
    echo "⏳ Running for $DURATION seconds..."
    sleep "$DURATION"

    echo "🛑 Stopping Kafka cluster and producers/consumers..."
    docker compose down
fi

echo "🎉 Done. Cluster up with $kafka_count brokers."
echo "  Topic: ${topic_name:-<none>}"
echo "  Producers: $producer_count  Consumers: $consumer_count"
echo "  Message-count files under: $BASE_DATA_DIR/message_counts"