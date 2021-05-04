.PHONY: app

BACKGROUND=
FORCE=
FILE=
TOPIC=

# Local developement
TOPIC_INPUT:=input
TOPIC_RESULT:=result

DAEMON:=$(if $(BACKGROUND),-d)

########################### app tasks ###########################

app:
ifeq ($(FORCE),)
	docker-compose -f deploy/local/app/docker-compose.yml up $(DAEMON)
else
	docker-compose -f deploy/local/app/docker-compose.yml up --build
endif

app-down:
	docker-compose -f deploy/local/app/docker-compose.yml down --remove-orphans

########################### kafka tasks ###########################

kafka:
	@echo ">>> 🚀 Spinning up Kafka and Zookeeper..." && \
	docker-compose -f deploy/local/kafka/docker-compose.yml up -d


kafka-down:
	@echo ">>> 💣 Tearing down Kafka and Zookeeper..." && \
	docker-compose -f deploy/local/kafka/docker-compose.yml down --remove-orphans

list-topics:
	@docker exec kafka_kafka_1 bash -c \
		"kafka-topics --list --zookeeper zookeeper:2181"

produce-input:
ifneq ($(FILE),)
	@echo ">>> Sending messages from deploy/local/$(FILE) to topic $(TOPIC_INPUT)..."
	@docker exec kafka_kafka_1 bash -c \
		"kafka-console-producer --broker-list localhost:9092 --topic $(TOPIC_INPUT) < /data/$(FILE)"
	@echo "\n>>> Done sending messages."
else
	@echo ">>> A FILE mnust be specified."
endif

consume-result:
	@docker exec kafka_kafka_1 bash -c \
		"kafka-console-consumer --bootstrap-server localhost:9092 --topic $(TOPIC_RESULT) --from-beginning"
