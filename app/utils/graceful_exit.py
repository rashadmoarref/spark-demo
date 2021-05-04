#!/usr/bin/env python
# -*- coding: utf-8 -*-
import signal
from abc import ABC, abstractmethod
from typing import List


class AbstractGracefullyExitableClass(ABC):
    """
    Abstract class representing an object that must be gracefully terminated
    """

    @abstractmethod
    def shutdown(self):
        """
        Shut down the class
        """
        raise NotImplementedError(
            "This method must be implemented in the derived class"
        )


class GracefulExit:
    """
    Class for capturing interruption signals and performing clean-up
    """

    def __init__(self, object_list: List[AbstractGracefullyExitableClass]) -> None:
        """
        Args:
            object_list: List of AbstractGracefullyExitableClass objects with a shutdown method
        """
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        self.object_list = object_list

    def exit_gracefully(self, signum, frame) -> None:
        """
        Gracefully shut down items in object_list

        Args:
            object_list: List of AbstractGracefullyExitableClass objects with a shutdown method
        """
        for item in self.object_list:
            item.shutdown()
