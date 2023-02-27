import pytest
from tritonclient.grpc import service_pb2, InferInput, InferResult
from google.protobuf.json_format import ParseDict
from azureml_inference_server_http.prepost_server.clients.triton_grpc_client import (
    TritonGrpcClient,
)


def test_parse_grpc_request(pullover_bytes, basic_context, script_loader):
    pullover_request = script_loader.preprocess(pullover_bytes, basic_context)
    triton_client = TritonGrpcClient()
    inputs, outputs = triton_client.parse_request(pullover_request)

    assert type(inputs[0]) is InferInput
    assert inputs[0].name() == "Conv1_input"
    assert inputs[0].datatype() == "FP32"
    assert inputs[0].shape() == [1, 28, 28, 1]


def test_parse_grpc_response(basic_context, script_loader):
    triton_client = TritonGrpcClient()
    dict = {
        "model_name": "fashion",
        "model_version": "1",
        "outputs": [{"name": "Dense", "datatype": "FP32", "shape": ["1", "10"]}],
        "raw_output_contents": ["MA6KwEMlpME+1ThAx0MPwSlKE8AvwdTBZwgOwPKuA8J8rQPBHojEwQ=="],
    }
    infer_response = ParseDict(dict, service_pb2.ModelInferResponse())
    result = InferResult(infer_response)
    data = triton_client.parse_response(result)
    out, content_type = script_loader.postprocess(data, basic_context)
    assert out == "Pullover"
    assert content_type == "text/plain"
