import os
import time
import socket
import signal
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# =========================
# Configuration
# =========================
BROKERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092")
BROKER_LIST = BROKERS.split(",")
TOPIC_NAME = os.getenv("TOPIC_NAME", "my-topic")
MESSAGE_TEXT = os.getenv("MESSAGE_TEXT", "Hello Kafka")
RATE_PER_SEC = int(os.getenv("RATE_PER_SEC", "1"))
DURATION = os.getenv("DURATION")
DURATION = float(DURATION) if DURATION not in (None, "", "0") else None
BATCH_SIZE = int(os.getenv("BATCH_SIZE_BYTES", 16384))
LINGER_MS = int(os.getenv("LINGER_MS", 5))
PRODUCER_NAME = f"producer_{socket.gethostname()}"

# =========================
# State
# =========================
created_count = 0
acked_count = 0
stop_requested = False

# Metrics file setup
count_dir = "/app/message_counts"
os.makedirs(count_dir, exist_ok=True)
file_path = os.path.join(count_dir, f"{PRODUCER_NAME}_sent.txt")

# =========================
# Signal handling & Callbacks
# =========================
def handle_stop_signal(signum, frame):
    global stop_requested
    stop_requested = True
    print("🛑 Stop signal received")

signal.signal(signal.SIGTERM, handle_stop_signal)
signal.signal(signal.SIGINT, handle_stop_signal)

def on_send_success(record_metadata):
    global acked_count
    acked_count += 1

def on_send_error(excp):
    print(f"❌ Send failed: {excp}")

# =========================
# Kafka Producer (Single, Clean Block)
# =========================
producer = None
for i in range(1, 11):
    try:
        producer = KafkaProducer(
            bootstrap_servers=BROKER_LIST,
            value_serializer=lambda v: v.encode("utf-8"),
            batch_size=BATCH_SIZE,
            linger_ms=LINGER_MS,
            acks="all",
            retries=999999,              
            request_timeout_ms=5000,     
            metadata_max_age_ms=1000,    
            max_in_flight_requests_per_connection=1 
        )
        print("✅ Connected to Kafka")
        break
    except NoBrokersAvailable:
        print(f"⏳ Kafka not ready (attempt {i}/10), retrying...")
        time.sleep(5)

if producer is None:
    print("❌ Failed to connect to Kafka.")
    exit(1)

# =========================
# Main loop
# =========================
print(f"🚀 Producer started | rate={RATE_PER_SEC}/s")
start_time = time.monotonic()
next_send_time = start_time
last_report = start_time

try:
    while not stop_requested:
        now = time.monotonic()
        if DURATION and (now - start_time) >= DURATION:
            break

        if now < next_send_time:
            time.sleep(max(0, next_send_time - now))
            continue
        
        next_send_time += 1.0 / RATE_PER_SEC

        # GAP CONTROL: Wait if Kafka is struggling to keep up
        while (created_count - acked_count) > 5 and not stop_requested:
            time.sleep(0.1)

        unique_id = f"{PRODUCER_NAME}:{created_count}"
        msg = f"{unique_id}|{MESSAGE_TEXT}"

        try:
            producer.send(TOPIC_NAME, value=msg).add_callback(on_send_success).add_errback(on_send_error)
            created_count += 1 
        except Exception as e:
            print(f"⚠️ Producer error: {e}")
            time.sleep(1)

        if now - last_report >= 5.0:
            print(f"📊 Created: {created_count} | Acked: {acked_count}")
            last_report = now

finally:
    print(f"⏳ Finalizing... Created: {created_count}, Acked: {acked_count}")
    if producer:
        producer.flush(timeout=30)
        producer.close()

    with open(file_path, "w") as f:
        f.write(f"Producer: {PRODUCER_NAME}\n")
        f.write(f"Created:  {created_count}\n")
        f.write(f"Acked:    {acked_count}\n")
    
    print(f"✅ Final Result: {acked_count} confirmed.")