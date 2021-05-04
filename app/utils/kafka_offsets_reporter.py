import logging
import threading
from time import sleep

from confluent_kafka import Consumer, TopicPartition

from app.utils.graceful_exit import AbstractGracefullyExitableClass


class KafkaOffsetsReporter(AbstractGracefullyExitableClass):
    """
    Commits processed kafka offsets using a dummy kafka consumer
    """

    __logger = logging.getLogger(__name__)

    def __init__(
        self,
        streaming_query: str,
        bootstrap_servers: str,
        consumer_group_id: str,
        frequency: str = 10,
    ) -> None:
        self._streaming_query = streaming_query
        self._last_batch_id = None
        self._frequency = frequency
        self._dummy_consumer = Consumer(
            {"group.id": consumer_group_id, "bootstrap.servers": bootstrap_servers}
        )

        # Threading
        self._closed = False
        self._reporter = threading.Thread(target=self._commit_offsets)
        self._reporter.start()

    def __repr__(self) -> str:
        return f"{__class__.__name__} initialiazed with dummy consumer {self._dummy_consumer}"

    def _commit_offsets(self) -> None:
        while not self._closed:

            try:
                last_progress = self._streaming_query.lastProgress
                if last_progress:
                    batch_id = last_progress.get("batchId")
                    # report offsets when a new batch is processed
                    if batch_id != self._last_batch_id:
                        self._last_batch_id = batch_id
                        numInputRows = last_progress.get("numInputRows")
                        inputRowsPerSecond = last_progress.get("inputRowsPerSecond")
                        processedRowsPerSecond = last_progress.get(
                            "processedRowsPerSecond"
                        )
                        self.__logger.info(
                            f"Progress: batchId: {batch_id}, "
                            f"numInputRows: {numInputRows}, "
                            f"inputRowsPerSecond: {inputRowsPerSecond}, "
                            f"processedRowsPerSecond: {processedRowsPerSecond}"
                        )
                        # extract end offsets
                        sources = last_progress.get("sources")
                        for source in sources:
                            end_offsets = source.get("endOffset")
                            offset_list = []
                            for topic, partition_offset_dict in end_offsets.items():
                                for partition, offset in partition_offset_dict.items():
                                    offset_list.append(
                                        TopicPartition(topic, int(partition), offset)
                                    )
                            # commit offsets
                            self._dummy_consumer.commit(offsets=offset_list)
            except Exception:
                self.__logger.exception(
                    f"Failed reporting offsets for {self._streaming_query}"
                )

            sleep(self._frequency)

    def shutdown(self) -> None:
        """
        Shutdown and terminate the KafkaOffsetsReporter.
        """
        self._closed = True

        try:
            self._reporter.join()
            self.__logger.info(
                f"{self.__class__.__name__} thread {self._reporter} successfully joint"
            )
        except RuntimeError:
            self.__logger.warning(
                f"{self.__class__.__name__} future {self._reporter} shutdown timed out"
            )
