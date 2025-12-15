import os
import time
import socket
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

# -------------------------------
# Configuration
# -------------------------------
TOPIC_NAME = os.getenv('TOPIC_NAME', 'my-topic')
BROKERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092")

BROKER_LIST = BROKERS.split(",")

hostname = socket.gethostname()
GROUP_ID = f"group_{hostname}"

# Consumer retries
max_retries = 10
retry_delay = 5

# Message count file
os.makedirs("/app/message_counts", exist_ok=True)
file_path = f"/app/message_counts/{GROUP_ID}_received.txt"

# -------------------------------
# Resume previous count if exists
# -------------------------------
received_count = 0
if os.path.exists(file_path):
    try:
        with open(file_path, "r") as f:
            for line in f:
                if "Total messages received:" in line:
                    received_count = int(line.split(":")[1].strip())
                    print(f"🔁 Resuming from previous count: {received_count}")
                    break
    except Exception as e:
        print(f"⚠️ Could not read previous count ({e}), starting from 0")

# -------------------------------
# Connect to Kafka
# -------------------------------
consumer = None
for attempt in range(1, max_retries + 1):
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=BROKER_LIST,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=GROUP_ID,
            max_poll_records=500  
        )
        print(f"✅ Connected to Kafka cluster on attempt {attempt} with group {GROUP_ID}")
        break
    except NoBrokersAvailable:
        print(f"❌ Kafka broker not available. Retry {attempt}/{max_retries} in {retry_delay}s...")
        time.sleep(retry_delay)
else:
    print("❌ Failed to connect to Kafka cluster after several retries.")
    exit(1)

print("🔄 Reading messages... Press Ctrl+C to stop.")

start_time = time.time()

# -------------------------------
# Consume messages safely
# -------------------------------
try:
    while True:
        # Poll for a batch of messages
        messages = consumer.poll(timeout_ms=1000, max_records=500)
        batch_count = 0

        for tp, msgs in messages.items():
            for message in msgs:
                batch_count += 1
                received_count += 1

        if batch_count > 0:
            # Write updated count to file after each batch
            runtime_sec = time.time() - start_time
            with open(file_path, "w") as f:
                f.write(f"Consumer group: {GROUP_ID}\n")
                f.write(f"Total messages received: {received_count}\n")
                f.write(f"Total runtime_seconds: {runtime_sec:.3f}\n")
                f.write(f"Total runtime_human: {int(runtime_sec//3600)}h {int((runtime_sec%3600)//60)}m {int(runtime_sec%60)}s\n")
            print(f"🟢 [{GROUP_ID}] Received {batch_count} msgs → total {received_count}")

        else:
            # No messages, short sleep to avoid busy loop
            time.sleep(0.05)

except KeyboardInterrupt:
    print(f"🛑 Consumer stopped by user. Total messages received: {received_count}")

finally:
    if consumer:
        consumer.close()

    runtime_sec = time.time() - start_time
    with open(file_path, "w") as f:
        f.write(f"Consumer group: {GROUP_ID}\n")
        f.write(f"Total messages received: {received_count}\n")
        f.write(f"Total runtime_seconds: {runtime_sec:.3f}\n")
        f.write(f"Total runtime_human: {int(runtime_sec//3600)}h {int((runtime_sec%3600)//60)}m {int(runtime_sec%60)}s\n")

    print(f"✅ Message count saved to {file_path}")
