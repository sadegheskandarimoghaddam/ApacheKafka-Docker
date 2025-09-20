import os
import time
import socket
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

TOPIC_NAME = os.getenv('TOPIC_NAME', 'my-topic')
BROKER = 'kafka:9092'
#GROUP_ID = os.getenv('GROUP_ID', f"group_{socket.gethostname()}")
hostname = socket.gethostname()
GROUP_ID = f"group_{hostname}"
max_retries = 10
retry_delay = 5  

consumer = None

for attempt in range(1, max_retries + 1):
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=[BROKER],
            auto_offset_reset='earliest',
            enable_auto_commit=True ,
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
        print(f"🟢 [{GROUP_ID}] Received: {message.value.decode()}")
except KeyboardInterrupt:
    print("🛑 Stopped by user.")
finally:
    if consumer:
        consumer.close()
