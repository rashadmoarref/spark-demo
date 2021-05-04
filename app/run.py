# -*- coding: utf-8 -*-

import os
import math
import logging

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, struct, to_json, from_json

import app.udfs as udfs
import app.schemas as schemas
from app.config import settings

__logger = logging.getLogger(__name__)


def foreach_batch_process(df: DataFrame, batch_id: int) -> None:
    """The main query function that will be applied to each micro-batch
    Args:
        df: dataframe of input micro-batch.
        batch_id: Not used here, but can be used if needed.
    """
    # parse input in kafka topic
    df = df.select(
        col("key").cast("string"),
        from_json(col("value").cast("string"), schemas.input_schema).alias("value"),
    ).select("key", "value.*")

    # cache df
    df.persist(StorageLevel.MEMORY_AND_DISK)

    # get ner entities
    df = df.repartition(
        max(1, math.ceil(df.count() / settings.PARTITION_SIZE))
    ).withColumn("ner", from_json(udfs.process(col("text")), schemas.ner_schema))

    # send results message to kafka
    df.withColumn(
        "result", udfs.generate_result_message(col("ner"), col("uuid"), col("lang"))
    ).select("key", "result.*").select(
        "key",
        to_json(struct(schemas.result_schema.names)).cast("string").alias("value"),
    ).write.format(
        "kafka"
    ).option(
        "kafka.bootstrap.servers", settings.KAFKA_CONFIGS["bootstrap.servers"]
    ).option(
        "topic", settings.KAFKA_CONFIGS["topic_out"]
    ).save()

    # release cache
    df.unpersist()


def read_input_stream(spark: SparkSession) -> DataFrame:
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", settings.KAFKA_CONFIGS["bootstrap.servers"])
        .option("subscribe", settings.KAFKA_CONFIGS["topic_in"])
        .option("startingOffsets", settings.KAFKA_CONFIGS["starting_offsets"])
        .option("kafkaConsumer.pollTimeoutMs", settings.CONSUMPTION_TIMEOUT)
        .option(
            "maxOffsetsPerTrigger",
            settings.PARTITION_SIZE * int(os.getenv("MAX_WORKERS", 1)),
        )
        .load()
    )


def start_structured_streaming(df: DataFrame) -> None:
    return (
        df.writeStream.option("checkpointLocation", settings.CHECKPOINT_LOCATION)
        .foreachBatch(foreach_batch_process)
        .trigger(processingTime=f"{settings.STREAMING_TRIGGER_SECONDS} seconds")
        .queryName("process")
        .start()
    )


if __name__ == "__main__":

    # create spark session if doesn't exist; session will be created only for local development
    spark = SparkSession.builder.master("local").getOrCreate()

    # start streaming query
    streaming_df = read_input_stream(spark)
    streaming_query = start_structured_streaming(streaming_df)

    # report metrics and lag only when in cluster mode
    if spark.sparkContext.master != "local":
        from app.utils.databricks_pushgateway_exporter import (
            DatabricksPushgatewayExporter,
        )
        from app.utils.kafka_offsets_reporter import KafkaOffsetsReporter
        from app.utils.graceful_exit import GracefulExit

        # start push gateway exporter for prometheus
        databricks_pushgateway_exporter = DatabricksPushgatewayExporter(
            ui_ip=os.getenv("SPARK_LOCAL_IP"),
            ui_port=spark.conf.get("spark.ui.port"),
            job=os.getenv("CLUSTER_NAME"),
        )
        # start kafka offsets reporter for lag reporting
        kafka_offsets_reporter = KafkaOffsetsReporter(
            streaming_query=streaming_query,
            bootstrap_servers=settings.KAFKA_CONFIGS["bootstrap.servers"],
            consumer_group_id=settings.KAFKA_CONFIGS["dummy.group.id"],
        )
        # setup graceful termination of above reporters
        GracefulExit([databricks_pushgateway_exporter, kafka_offsets_reporter])

    streaming_query.awaitTermination()
