#!/bin/bash


while getopts ":c:p:t:" opt; do
  case $opt in
    c) consumer_count=$OPTARG ;;
    p) producer_count=$OPTARG ;;
    t) topic_name=$OPTARG ;;
    \?) echo "Usage: run.sh -c <num_consumers> -p <num_producers> -t <topic_name>"
        exit 1 ;;
  esac
done


if [ -z "$consumer_count" ] || [ -z "$producer_count" ] || [ -z "$topic_name" ]; then
    echo "All parameters (-c, -p, -t) are required"
    exit 1
fi

export TOPIC_NAME=$topic_name
#export GROUP_ID="group" 

# create network if not exists
#docker network ls | grep kafka-net &>/dev/null || docker network create kafka-net

# start kafka & kafka-ui
docker-compose up -d kafka kafka-ui

# wait a few seconds for Kafka to be ready
echo "⏳ Waiting for Kafka to start..."
sleep 5

# scale consumers and producers
docker-compose up -d --scale consumer=$consumer_count --scale producer=$producer_count




# docker compose up -d --scale producer=$producer_count
#docker-compose up -d --scale consumer=$consumer_count --scale producer=$producer_count
# sed -i "s/my-topic/$topic_name/g" docker-compose.yml



echo "All services started!"
