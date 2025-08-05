from kafka import KafkaProducer
import time
time.sleep(10)
producer = KafkaProducer(bootstrap_servers='kafka:9092')

topic = 'my-topic'

print("برای خروج 'exit' وارد کن.")

while True:
    message = input("پیام را وارد کن: ")
    if message.lower() == 'exit':
        break
    producer.send(topic, message.encode('utf-8'))
    producer.flush()
    print("✅ پیام ارسال شد.")
