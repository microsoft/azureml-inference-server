from typing import Dict

import numpy as np
from typing import Dict
from functools import partial
import asyncio
from tritonclient.grpc import InferInput, InferenceServerClient, InferRequestedOutput
from sanic.log import logger

from .model_server_client import ModelServerClient
from ..log_settings import get_custom_dimensions
from ..user.exceptions import TritonInferenceException


class TritonGrpcClient(ModelServerClient):
    def __init__(self, addr_="localhost", port_=8001):
        super().__init__(addr_, port_)
        url = f"{self.addr}:{self.port}"
        self.client = InferenceServerClient(url)

    def completion_callback(self, loop, fut, result, error):
        if error:
            logger.debug(f"Exception from Triton: {error}", extra=get_custom_dimensions())
            raise TritonInferenceException(error.message)
        loop.call_soon_threadsafe(self.on_result, fut, result)

    def on_result(self, fut, result):
        if not fut.done():
            fut.set_result(result)

    async def infer_async(self, data, aiohttp_session) -> Dict:
        inputs, outputs = self.parse_request(data)
        name = data["model_name"]

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.client.async_infer(
            model_name=name, inputs=inputs, outputs=outputs, callback=partial(self.completion_callback, loop, fut)
        )

        result = await fut
        parsed = self.parse_response(result)
        return parsed

    @staticmethod
    def parse_request(data: Dict):
        inputs, outputs = [], []

        for kf_input in data["inputs"]:
            infer_input = InferInput(kf_input["name"], kf_input["shape"], kf_input["datatype"])
            infer_input.set_data_from_numpy(kf_input["data"])
            inputs.append(infer_input)

        if "outputs" in data:
            for kf_output in data["outputs"]:
                requested_output = InferRequestedOutput(kf_output["name"])
                outputs.append(requested_output)

        return inputs, outputs

    @staticmethod
    def parse_response(infer_response) -> Dict:
        data = infer_response.get_response(as_json=True)
        for kf_output in data["outputs"]:
            kf_output["shape"] = [int(i) for i in kf_output["shape"]]
            kf_output["data"] = infer_response.as_numpy(kf_output["name"])
        del data["raw_output_contents"]
        return data
