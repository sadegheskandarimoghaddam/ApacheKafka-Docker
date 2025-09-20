import os
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import time
import socket

KAFKA_BROKER = 'kafka:9092'
TOPIC_NAME = os.getenv('TOPIC_NAME', 'my-topic')
PRODUCER_NAME = f"producer_{socket.gethostname()}"
#PRODUCER_NAME = os.getenv('PRODUCER_NAME', 'producer_default')
#PRODUCER_NAME = f"{os.getenv('COMPOSE_PROJECT_NAME','kafka_bash')}_{os.getenv('SERVICE_NAME','producer')}_{os.getenv('HOSTNAME')}"
#PRODUCER_NAME = os.getenv('PRODUCER_NAME', f'producer_{os.getenv("HOSTNAME","unknown")}')
for _ in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: v.encode('utf-8')
        )
        break
    except NoBrokersAvailable:
        print("Kafka broker not available yet, retrying...")
        time.sleep(5)
else:
    raise Exception("Kafka broker not available after several retries.")

print(f"Sending messages to Kafka from producer {PRODUCER_NAME}... Press Ctrl+C to stop.")
try:
    count = 0
    while True:
        message = f"Hello Kafka {count}  from {PRODUCER_NAME}"
        producer.send(TOPIC_NAME, value=message)
        print(f"Sent: {message}")
        count += 1
        time.sleep(2)
except KeyboardInterrupt:
    print("Stopped by user.")
finally:
    producer.flush()
    producer.close()
