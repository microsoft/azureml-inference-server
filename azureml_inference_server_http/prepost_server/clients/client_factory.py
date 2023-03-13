from .triton_rest_client import TritonRestClient
from .triton_grpc_client import TritonGrpcClient
from .model_server_client import ModelServerClient


class ClientFactory:
    @staticmethod
    def create_client(addr: str = "localhost", port: int = 8000, protocol: str = "rest") -> ModelServerClient:
        if protocol == "grpc":
            return TritonGrpcClient(addr, port)
        else:
            return TritonRestClient(addr, port)
