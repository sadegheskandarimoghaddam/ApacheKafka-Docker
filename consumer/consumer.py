from kafka import KafkaConsumer
import time
time.sleep(10)
consumer = KafkaConsumer(
    'my-topic',
    bootstrap_servers='kafka:9092',
    auto_offset_reset='earliest',
    enable_auto_commit= True,
    group_id='my_group'
)

print("🔄 Waiting for messages... (Ctrl+C to exit))")

for message in consumer:
    print(f"📩 Message received: {message.value.decode('utf-8')}", flush=True)
