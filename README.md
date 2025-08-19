## A Setting up a Apache Kafka using docker with Python 


![Dockerfile](image/1.png)

### Understanding Kafka

Before the hands-on, let’s understand how Kafka works and why it’s so different from other solutions.
Kafka is a publish-subscribe messaging platform that could (normally) have many producers feeding data in it, while consumers are receiving that data. Ok, but there’s a lot of similar applications doing the same thing, why use Kafka?
That’s simple. Kafka can handle trillions of messages a day, and in the big data world, that everything is generating data, a platform that handles data of this magnitude is vital.
- **Real-Time** Data Processing: Data flows through Kafka almost instantly, making it perfect for live data streams.
- **Reliable and Scalable**: Kafka can handle millions of data messages every second, which makes it great for both small and large systems.
- **Fault-Tolerant**: If something goes wrong, Kafka won’t lose your data – it’s designed to recover and keep things moving.
- **Decouples Systems**: Kafka allows systems to send and receive data without needing to know too much about each other, which keeps everything flexible.


Now we will see a few concepts that will be important for the understanding of this material.



#### Producer
Is every application that publishes data to a Kafka topic

#### Consumer
Is every application that subscribes to a Kafka topic to receive data from this.

#### Broker
A Kafka broker is a node in a cluster that hosts partitions.

#### Topic
A topic is a category or feed name to which records are published. Topics in Kafka are always multi-subscriber; that is, a topic can have zero, one, or many consumer groups that subscribe to the data written to it.

#### Partitions
Kafka topics are divided into partitions. Each message in a partition has an offset that is used to order them into the partition. Partitions are really important because this enables to distribute a topic in different servers and creates replicas.

<p align="center">
  <img src="image/3.png" alt="Kafka Architecture" width="500"/>
</p>

So when a partition receives a new message, it will create a new offset to index it. On the other side, when a consumer confirms that received a message from a given partition, the Kafka broker updates the last offset consumed in this partition by this consumer, thereat Kafka knows the last message consumed in each partition for a given consumer group avoiding duplicity.

#### Replicas
Replicas are partitions copies for fault tolerance, it means that if one broker is down and will have multiple replicas, no data will be lost, because Kafka will use another replica for each partition, that has the same data of the first one.

#### ConsumerGroup
Each consumer has a consumer group ID, that means that each message from a topic will be delivered to only one consumer in a certain consumer group. To assure this, Kafka only allows that one consumer for each group can consume from a certain partition. This means that if a consumer group has more consumers than the topic has partitions, will have consumers idle in this consumer group.

<p align="center">
  <img src="image/4.png" alt="Kafka Architecture" width="500"/>
</p>

---

## Setting Up Kafka in KRaft Mode Using Docker
Now that we have a basic understanding, let’s set up Kafka in KRaft mode using Docker. If you’re not familiar with Docker, don’t worry! It’s a tool that lets us run programs in containers, which are like isolated environments, without needing to install everything directly on our computer.

### Requirements
- ##### Install Docker
   Make sure you have the latest versions of **[Docker](https://docs.docker.com/engine/install/)** installed on your machine.
   Make sure to [add your user to the `docker` group](https://docs.docker.com/install/linux/linux-postinstall/#manage-docker-as-a-non-root-user) when using Linux.
- ##### Clone this repository
   Clone this repository or copy the files from this repository into a new folder. 

  kafka/
├── docker-compose.yml
├── producer/
│ ├── Dockerfile
│ └── producer.py
└├── producer/
│ ├── Dockerfile
│ └── producer.py


### Project Structure

- A **Kafka broker** in KRaft (no ZooKeeper) mode
- A **Kafka UI** for visualizing and managing Kafka
- A custom **Producer** written in Python (or your language)
- A custom **Consumer** written in Python (or your language)

This project sets up a local Apache Kafka environment using Docker Compose. It includes:
Then, from the root of the project:

```bash
docker compose up --build


```