from typing import Dict
from aiohttp import ClientSession

from .model_server_client import ModelServerClient
from ..user.exceptions import TritonInferenceException


class TritonRestClient(ModelServerClient):
    def __init__(self, addr_="localhost", port_=8000):
        super().__init__(addr_, port_)

    async def infer_async(self, data, aiohttp_session: ClientSession) -> Dict:
        model_name = data["model_name"]
        model_version = data["model_version"]

        for kf_input in data["inputs"]:
            kf_input["data"] = kf_input["data"].tolist()

        headers = {"Content-Type": "application/json"}
        async with aiohttp_session.post(
            f"http://{self.addr}:{self.port}/v2/models/{model_name}/versions/{model_version}/infer",
            headers=headers,
            json=data,
        ) as r:
            if r.status == 200:
                return await r.json()
            else:
                json = await r.json()
                if "error" in json:
                    raise TritonInferenceException(json["error"], r.status)
                raise TritonInferenceException(await r.text(), r.status)
