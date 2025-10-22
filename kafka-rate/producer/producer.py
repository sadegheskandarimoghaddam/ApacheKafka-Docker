import os
import time
import socket
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

KAFKA_BROKER = 'kafka:9092'
TOPIC_NAME = os.getenv('TOPIC_NAME', 'my-topic')
MESSAGE_TEXT = os.getenv('MESSAGE_TEXT', 'Hello Kafka')
RATE_PER_SEC = int(os.getenv('RATE_PER_SEC', '1'))
DURATION = int(os.getenv('DURATION', '60'))
PRODUCER_NAME = f"producer_{socket.gethostname()}"

count_dir = "/app/message_counts"
os.makedirs(count_dir, exist_ok=True)
file_path = os.path.join(count_dir, f"{PRODUCER_NAME}_sent.txt")

sent_count = 0
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

# اتصال به Kafka
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

print(f"🚀 Sending {RATE_PER_SEC} messages/sec from {PRODUCER_NAME} for {DURATION} seconds...")

interval = 1.0 / RATE_PER_SEC
start_time = time.time()
last_report_time = start_time
last_sent_snapshot = sent_count
report_interval = 5

try:
    while True:
        now = time.time()
        elapsed_total = now - start_time
        if elapsed_total >= DURATION:
            break

        next_send_time = now
        for _ in range(RATE_PER_SEC):
            message = f"{MESSAGE_TEXT} {sent_count} from {PRODUCER_NAME}"
            producer.send(TOPIC_NAME, value=message)
            sent_count += 1
            next_send_time += interval
            sleep_time = next_send_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

        producer.flush()

        # ثبت تعداد پیام‌ها
        with open(file_path, "w") as f:
            f.write(f"Producer: {PRODUCER_NAME}\n")
            f.write(f"Total messages sent: {sent_count}\n")

        now = time.time()
        if now - last_report_time >= report_interval:
            msgs_sent_in_window = sent_count - last_sent_snapshot
            rate = msgs_sent_in_window / (now - last_report_time)
            print(f"📊 {PRODUCER_NAME}: Sent {msgs_sent_in_window} msgs in {report_interval:.0f}s → {rate:.2f} msg/s (total {sent_count})")
            last_report_time = now
            last_sent_snapshot = sent_count

    # ارسال پیام پایانی
    producer.send(TOPIC_NAME, value="__END__")
    producer.flush()
    print("✅ All messages sent, __END__ marker sent")

except KeyboardInterrupt:
    print(f"🛑 Producer stopped by user. Total messages sent: {sent_count}")

finally:
    producer.flush()
    producer.close()
    print(f"✅ Message count saved to {file_path}")
