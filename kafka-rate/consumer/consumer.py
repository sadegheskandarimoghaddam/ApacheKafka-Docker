import os
import time
import socket
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

TOPIC_NAME = os.getenv('TOPIC_NAME', 'my-topic')
BROKER = 'kafka:9092'
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

# اتصال به Kafka
consumer = None
for attempt in range(1, max_retries + 1):
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=[BROKER],
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=GROUP_ID
        )
        print(f"✅ Connected to Kafka on attempt {attempt} with group {GROUP_ID}")
        break
    except NoBrokersAvailable:
        print(f"❌ Kafka broker not available. Retry {attempt}/{max_retries} in {retry_delay} seconds...")
        time.sleep(retry_delay)
else:
    print("❌ Failed to connect to Kafka broker after several retries.")
    exit(1)

print("🔄 Reading messages from beginning... Press Ctrl+C to stop.")

try:
    for message in consumer:
        msg_text = message.value.decode()
        if msg_text == "__END__":
            print("🛑 __END__ marker received, stopping consumer")
            break

        received_count += 1
        print(f"🟢 [{GROUP_ID}] Received ({received_count}): {msg_text}")

        # ذخیره تعداد پیام‌ها
        with open(file_path, "w") as f:
            f.write(f"Consumer group: {GROUP_ID}\n")
            f.write(f"Total messages received: {received_count}\n")

except KeyboardInterrupt:
    print(f"🛑 Consumer stopped by user. Total messages received: {received_count}")

finally:
    if consumer:
        consumer.close()
    print(f"✅ Message count saved to {file_path}")
