from abc import ABCMeta, abstractmethod
from typing import Any, Dict

from hamilton.async_driver import AsyncDriver
from hamilton.driver import Driver

class BasicPipeline(metaclass=ABCMeta):
    def __init__(self, pipe: AsyncDriver | Driver):
        self._pipe = pipe

    @abstractmethod
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        ...
