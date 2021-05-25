## Description

This demo intends to provide an end-to-end example of deploying an NLP inference project using [Apache Spark Structured Streaming](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html). The setup includes ready-to-use local deployment for testing and cloud deployment on [Databricks](https://databricks.com/) using [Drone](https://www.drone.io/). Please also see accompanying [Medium blog post](https://medium.com/gumgum-tech/real-time-machine-learning-inference-at-scale-using-spark-structured-streaming-fa8790314319). For the purpose of this demo, we use [spaCy](https://spacy.io/)'s open-source Named Entity Recognition model.

To clone the repo, run `git clone https://github.com/rashadmoarref/spark-demo.git`

## Deploy locally

- create local demo network to be used by kafka and app docker containers

```
docker network create demo
```

- create kafka service

```
make kafka
```

- run app

```
make app
```

Note: use `make app FORCE=true` if need to re-build the app after changing `Dockerfile` or `reqiurements.txt`

- send input to app's input topic

```
make produce-input FILE=input.json
```

- consume from app's result topic

```
make consume-result
```

- tear down local deployment

```
make app-down
make kafka-down
docker network rm demo
```
- Note: If running into memory issues, increase the allocated memory of your Docker Engine to 10GB.

## Deploy on Databricks using Drone

- drone steps are defined in `.drone.yml`
- deployment on databricks is handled using REST API in `deploy/databricks/deploy-job.sh`


##  Setup `pre-commit` if you like to contribute

- The configs are defined in `.pre-commit-config.yaml`
- [black](https://github.com/psf/black) and [flake8](https://github.com/PyCQA/flake8) are tools for enforcing code style

```
pip install black flake8 pre-commit
pre-commit install
```
