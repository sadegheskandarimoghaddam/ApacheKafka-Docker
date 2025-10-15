import os
import time
import socket
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

KAFKA_BROKER = 'kafka:9092'
TOPIC_NAME = os.getenv('TOPIC_NAME', 'my-topic')
MESSAGE_TEXT = os.getenv('MESSAGE_TEXT', 'Hello Kafka')
PRODUCER_NAME = f"producer_{socket.gethostname()}"

count_dir = "/app/message_counts"
os.makedirs(count_dir, exist_ok=True)
file_path = os.path.join(count_dir, f"{PRODUCER_NAME}_sent.txt")


try:
    os.chmod(count_dir, 0o777)
except PermissionError:
    print("⚠️ Warning: Could not change permission for message_counts folder.")

if os.path.exists(file_path):
    try:
        with open(file_path, "r") as f:
            for line in f:
                if "Total messages sent:" in line:
                    sent_count = int(line.split(":")[1].strip())
                    print(f"🔁 Resuming from previous count: {sent_count}")
                    break
    except Exception as e:
        print(f"⚠️ Could not read previous count ({e}), starting from 0")
        
for _ in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: v.encode('utf-8')
        )
        break
    except NoBrokersAvailable:
        print("⏳ Kafka broker not available yet, retrying...")
        time.sleep(5)
else:
    raise Exception("❌ Kafka broker not available after several retries.")

print(f"🚀 Sending messages to Kafka from {PRODUCER_NAME}... Press Ctrl+C to stop.")

sent_count = 0

try:
    while True:
        message = f"{MESSAGE_TEXT} {sent_count} from {PRODUCER_NAME}"
        producer.send(TOPIC_NAME, value=message).get(timeout=10)
        sent_count += 1

        with open(file_path, "w") as f:
            f.write(f"Producer: {PRODUCER_NAME}\n")
            f.write(f"Total messages sent: {sent_count}\n")

        print(f"📤 Sent ({sent_count}): {message}")
        time.sleep(2)

except KeyboardInterrupt:
    print(f"🛑 Producer stopped by user. Total messages sent: {sent_count}")

finally:
    producer.flush()
    producer.close()
    print(f"✅ Message count saved to {file_path}")
