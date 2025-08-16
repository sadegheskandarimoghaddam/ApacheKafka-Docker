from kafka import KafkaProducer
import time
time.sleep(10)
producer = KafkaProducer(bootstrap_servers='kafka:9092')

topic = 'my-topic'

print("Enter 'exit' to exit.")

while True:
    message = input("Enter the message: ")
    if message.lower() == 'exit':
        break
    producer.send(topic, message.encode('utf-8'))
    producer.flush()
    print("✅ The message was sent.")
