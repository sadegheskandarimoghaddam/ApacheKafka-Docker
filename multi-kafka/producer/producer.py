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

BATCH_SIZE = int(os.getenv("BATCH_SIZE_BYTES", 16384))  # 16 KB default
LINGER_MS = int(os.getenv("LINGER_MS", 5))               # 5 ms default


PRODUCER_NAME = f"producer_{socket.gethostname()}"

# =========================
# State
# =========================
created_count = 0
enqueued_count = 0
acked_count = 0
stop_requested = False


# =========================
# Metrics file
# =========================
count_dir = "/app/message_counts"
os.makedirs(count_dir, exist_ok=True)
file_path = os.path.join(count_dir, f"{PRODUCER_NAME}_sent.txt")

# =========================
# Signal handling
# =========================
def handle_stop_signal(signum, frame):
    global stop_requested
    stop_requested = True
    print("🛑 Stop signal received")

signal.signal(signal.SIGTERM, handle_stop_signal)
signal.signal(signal.SIGINT, handle_stop_signal)

# =========================
# ACK callbacks
# =========================
def on_send_success(record_metadata):
    global acked_count
    acked_count += 1

def on_send_error(excp):
    print(f"❌ Send failed: {excp}")

# =========================
# Kafka Producer
# =========================
for _ in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers=BROKER_LIST,
            value_serializer=lambda v: v.encode("utf-8"),
            batch_size=BATCH_SIZE,
            linger_ms=LINGER_MS,
            acks="all",
            retries=5,
            max_in_flight_requests_per_connection=5,
        )
        break
    except NoBrokersAvailable:
        print("⏳ Kafka not ready, retrying...")
        time.sleep(5)
else:
    raise RuntimeError("Kafka broker not available")

total_messages = int(RATE_PER_SEC * DURATION) if DURATION else None

print(
    f"🚀 Producer started | rate={RATE_PER_SEC}/s "
    f"| linger_ms={LINGER_MS}"
    f"| batch_size={BATCH_SIZE} bytes"
)

# =========================
# Time control
# =========================
start_time = time.monotonic()
next_send_time = start_time
last_report = start_time
REPORT_INTERVAL = 5.0

# =========================
# Main loop
# =========================
try:
    while True:
        now = time.monotonic()

        if stop_requested:
            break
        if DURATION and (now - start_time) >= DURATION:
            break
        if total_messages and created_count >= total_messages:
            break

        if now < next_send_time:
            time.sleep(next_send_time - now)
            continue
        next_send_time += 1.0 / RATE_PER_SEC

        msg = f"{MESSAGE_TEXT} {created_count} from {PRODUCER_NAME}"
        created_count += 1

        future = producer.send(TOPIC_NAME, value=msg)
        future.add_callback(on_send_success)
        future.add_errback(on_send_error)
        enqueued_count += 1


        if now - last_report >= REPORT_INTERVAL:
            with open(file_path, "w") as f:
                f.write(f"Producer: {PRODUCER_NAME}\n")
                f.write(f"Created:  {created_count}\n")
                f.write(f"Enqueued: {enqueued_count}\n")
                f.write(f"Acked:    {acked_count}\n")

            print(
                f"📊 created={created_count} "
                f"enqueued={enqueued_count} "
                f"acked={acked_count}"
            )
            last_report = now
finally:
    print("⏳ SIGTERM or exit detected — flushing Kafka producer")

    try:
        producer.flush(timeout=30)
    finally:
        producer.close()

    with open(file_path, "w") as f:
        f.write(f"Producer: {PRODUCER_NAME}\n")
        f.write(f"Created:  {created_count}\n")
        f.write(f"Enqueued: {enqueued_count}\n")
        f.write(f"Acked:    {acked_count}\n")

    print(
        f"✅ Producer stopped safely → "
        f"created={created_count}, "
        f"enqueued={enqueued_count}, "
        f"acked={acked_count}"
    )
    
