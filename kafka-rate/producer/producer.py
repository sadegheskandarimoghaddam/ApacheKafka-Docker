import os
import time
import socket
import signal
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

KAFKA_BROKER = 'kafka:9092'
TOPIC_NAME = os.getenv('TOPIC_NAME', 'my-topic')
MESSAGE_TEXT = os.getenv('MESSAGE_TEXT', 'Hello Kafka')

RATE_PER_SEC = int(os.getenv('RATE_PER_SEC', '1'))
DURATION = os.getenv('DURATION') 
DURATION = float(DURATION) if DURATION not in [None, "", "0"] else None

PRODUCER_NAME = f"producer_{socket.gethostname()}"

count_dir = "/app/message_counts"
os.makedirs(count_dir, exist_ok=True)
file_path = os.path.join(count_dir, f"{PRODUCER_NAME}_sent.txt")

sent_count = 0

stop_requested = False

def handle_stop_signal(signum, frame):
    global stop_requested
    stop_requested = True
    print("🛑 Stop signal received. Will send __END__ and exit cleanly...")

signal.signal(signal.SIGTERM, handle_stop_signal)
signal.signal(signal.SIGINT, handle_stop_signal)

for _ in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: v.encode('utf-8'),
            linger_ms=5
        )
        break
    except NoBrokersAvailable:
        print("⏳ Kafka broker not available yet, retrying...")
        time.sleep(5)
else:
    raise Exception("❌ Kafka broker not available after several retries.")


BATCH_INTERVAL = 0.2
batch_size = max(1, int(RATE_PER_SEC * BATCH_INTERVAL))

total_messages = int(RATE_PER_SEC * DURATION) if DURATION else None

if DURATION:
    print(f"🚀 Running for {DURATION}s, sending {total_messages} messages...")
else:
    print(f"🚀 Running WITHOUT duration. Infinite mode at {RATE_PER_SEC} msg/s")

start_time = time.time()
last_report_time = start_time
last_sent_snapshot = 0
report_interval = 5

try:
    while True:
        if stop_requested:
            break

        if DURATION:
            elapsed = time.time() - start_time
            if elapsed >= DURATION or sent_count >= total_messages:
                break

        for _ in range(batch_size):
            if DURATION and sent_count >= total_messages:
                break

            message = f"{MESSAGE_TEXT} {sent_count} from {PRODUCER_NAME}"
            producer.send(TOPIC_NAME, value=message)
            sent_count += 1

        producer.flush()

        with open(file_path, "w") as f:
            f.write(f"Producer: {PRODUCER_NAME}\n")
            f.write(f"Total messages sent: {sent_count}\n")

        now = time.time()
        if now - last_report_time >= report_interval:
            msgs_in_window = sent_count - last_sent_snapshot
            rate = msgs_in_window / (now - last_report_time)
            print(f"📊 Sent {msgs_in_window} msgs in {report_interval}s → {rate:.2f} msg/s "
                  f"(total {sent_count})")
            last_report_time = now
            last_sent_snapshot = sent_count

        next_batch_time = start_time + (sent_count / RATE_PER_SEC)
        sleep_time = next_batch_time - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)

    print("🎯 Sending __END__ marker...")
    producer.send(TOPIC_NAME, value="__END__")
    producer.flush()

except Exception as e:
    print(f"❌ Error: {e}")

finally:
    producer.close()
    print(f"✅ Producer finished. Total messages sent: {sent_count}")
