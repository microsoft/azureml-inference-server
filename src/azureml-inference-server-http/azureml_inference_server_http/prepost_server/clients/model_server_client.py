from abc import ABC, abstractmethod
from aiohttp import ClientSession
from typing import Dict


class ModelServerClient(ABC):
    def __init__(self, addr_: str = "localhost", port_: int = 8000):
        self.addr = addr_
        self.port = port_

    @abstractmethod
    async def infer_async(self, data: Dict, aiohttp_session: ClientSession) -> Dict:
        pass
