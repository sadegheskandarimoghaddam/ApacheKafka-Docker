import os
import time
import socket
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

TOPIC_NAME = os.getenv('TOPIC_NAME', 'my-topic')

BROKERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092")
BROKER_LIST = BROKERS.split(",")

hostname = socket.gethostname()
GROUP_ID = f"group_{hostname}"
max_retries = 10
retry_delay = 5

os.makedirs("/app/message_counts", exist_ok=True)
file_path = f"/app/message_counts/{GROUP_ID}_received.txt"

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

consumer = None

for attempt in range(1, max_retries + 1):
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=BROKER_LIST,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=GROUP_ID,
            consumer_timeout_ms=500
        )
        print(f"✅ Connected to Kafka cluster on attempt {attempt} with group {GROUP_ID}")
        break
    except NoBrokersAvailable:
        print(f"❌ Kafka broker not available. Retry {attempt}/{max_retries} in {retry_delay} seconds...")
        time.sleep(retry_delay)
else:
    print("❌ Failed to connect to Kafka cluster after several retries.")
    exit(1)

print("🔄 Reading messages... Press Ctrl+C to stop.")

last_report_time = time.time()
last_received_snapshot = received_count
report_interval = 5

end_received = False
end_time = None
start_time = time.time()

try:
    while True:
        any_message = False
        for message in consumer:
            any_message = True
            msg_text = message.value.decode()

            if msg_text == "__END__":
                print("🛑 __END__ marker received, draining extra messages...")
                end_received = True
                end_time = time.time()
                break

            received_count += 1

            now = time.time()
            if now - last_report_time >= report_interval:
                msgs_in_window = received_count - last_received_snapshot
                rate = msgs_in_window / (now - last_report_time)
                print(f"🟢 [{GROUP_ID}] Received {msgs_in_window} msgs in {report_interval:.0f}s → {rate:.2f} msg/s (total {received_count})")
                last_report_time = now
                last_received_snapshot = received_count

        if end_received:
            if time.time() - end_time >= 2:
                print("✅ Drain completed. Stopping consumer.")
                break

        if not any_message:
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
