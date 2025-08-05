from kafka import KafkaConsumer
import time
time.sleep(10)
consumer = KafkaConsumer(
    'my-topic',
    bootstrap_servers='kafka:9092',
    auto_offset_reset='earliest',
    enable_auto_commit= True,
    group_id='my-group'
)

print("🔄 منتظر دریافت پیام‌ها... (Ctrl+C برای خروج)")

for message in consumer:
    print(f"📩 پیام دریافت شد: {message.value.decode('utf-8')}")
