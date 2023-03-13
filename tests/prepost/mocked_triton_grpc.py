import grpc
import logging
from concurrent.futures import ThreadPoolExecutor
from tritonclient.grpc import service_pb2, service_pb2_grpc
from google.protobuf.json_format import ParseDict


class TritonServer(service_pb2_grpc.GRPCInferenceServiceServicer):
    """
    Mock the gRPC server
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)

    def ModelInfer(self, request, context):
        self.logger.debug("ModelInfer called")
        if request.model_version == "3":
            grpc.ServicerContext.abort(code=grpc.StatusCode.INVALID_ARGUMENT, details="Incorrect inputs")
        data = {
            "model_name": "fashion",
            "model_version": "1",
            "outputs": [{"name": "Dense", "datatype": "FP32", "shape": ["1", "10"]}],
            "raw_output_contents": ["MA6KwEMlpME+1ThAx0MPwSlKE8AvwdTBZwgOwPKuA8J8rQPBHojEwQ=="],
        }
        return ParseDict(data, service_pb2.ModelInferResponse())


def create_fake_grpc_triton():
    server = grpc.server(ThreadPoolExecutor(max_workers=1))
    service_pb2_grpc.add_GRPCInferenceServiceServicer_to_server(TritonServer("localhost", 8001), server)
    server.add_insecure_port("[::]:8001")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    create_fake_grpc_triton()

    with grpc.insecure_channel("localhost:8001") as channel:
        stub = service_pb2_grpc.GRPCInferenceServiceStub(channel)
        request = service_pb2.ModelInferRequest(
            id="1",
            model_version="3",
            model_name="test",
            inputs=[{"name": "input", "datatype": "FP32", "shape": [1, 10]}],
        )
        response = stub.ModelInfer(request)
        print(response)
