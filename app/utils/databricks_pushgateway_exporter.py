# Borrowed from: https://gist.github.com/Lowess/3a71792d2d09e38bf8f524644bbf8349#file-databrickspushgatewayexporter-py

import logging
import threading
import urllib.request
from time import sleep

from app.utils.graceful_exit import AbstractGracefullyExitableClass


class DatabricksPushgatewayExporter(AbstractGracefullyExitableClass):
    """
    Pushgateway exporter to be used in Databricks
    """

    __logger = logging.getLogger(__name__)

    def __init__(
        self,
        ui_ip: str,
        ui_port: str,
        job: str = "ner",
        frequency: int = 5,
        pushgateway_endpoint: str = "<pushgateway-endpoint>",
    ) -> None:
        self._job = job
        self._instance = ui_ip
        self._frequency = frequency

        # Configure pushgateway endpoint with job and instance
        self._pushgateway = (
            f"{pushgateway_endpoint}/metrics/job/{self._job}/instance/{self._instance}"
        )
        self._prometheus = f"http://{ui_ip}:{ui_port}"

        # Threading
        self._closed = False
        self._reporter = threading.Thread(target=self._send_to_pushgateway)
        self._reporter.start()

    def __repr__(self) -> str:
        return f"{__class__.__name__} initialiazed with prometheus endpoint {self._prometheus}"

    def _send_to_pushgateway(self) -> None:
        while not self._closed:
            metrics = None

            try:
                # NOTE: you can try these endpoints
                # /metrics/prometheus -> set spark.metrics.namespace (defaults to spark.app.id that varies for each deployment)
                # /metrics/executors/prometheus
                with urllib.request.urlopen(
                    f"{self._prometheus}/metrics/executors/prometheus"
                ) as response:
                    # metrics is in bytes already (pushgateway requires bytes)
                    metrics = response.read()
            except Exception:
                self.__logger.exception(
                    f"Failed retrieving metrics from {self._prometheus}"
                )

            if metrics:
                self.__logger.debug(metrics)

                req = urllib.request.Request(
                    url=self._pushgateway, method="PUT", data=metrics
                )
                try:
                    with urllib.request.urlopen(req) as f:
                        self.__logger.debug(
                            f"Successfully reported {len(metrics)} of bytes - {f.status} - {f.reason}"
                        )
                except Exception:
                    self.__logger.exception(
                        f"Failed reporting metrics to {self._pushgateway}"
                    )

            sleep(self._frequency)

    def shutdown(self) -> None:
        """
        Shutdown and terminate the DatabricksPushgatewayExporter.
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
