import time

from aiohttp import web
import json
import os
import logging
import time

from aiohttp.web_request import Request


async def infer(request: Request):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/pullover_triton_response.json")
    with open(path, "r") as f:
        logging.debug(f"Request received {request}")
        return web.json_response(json.load(f))


async def slow(request: Request):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/pullover_triton_response.json")
    with open(path, "r") as f:
        logging.debug(f"Slow request {request}. Pausing 2 seconds...")
        time.sleep(2)
        return web.json_response(json.load(f))


async def incorrect_inputs(request: Request):
    return web.json_response({"error": "Incorrect inputs"}, status=400)


def create_fake_triton():
    app = web.Application()
    app.add_routes([web.post("/v2/models/fashion/versions/1/infer", infer)])
    app.add_routes([web.post("/v2/models/fashion/versions/2/infer", slow)])
    app.add_routes([web.post("/v2/models/fashion/versions/3/infer", incorrect_inputs)])
    web.run_app(app, port=8000, host="0.0.0.0")


if __name__ == "__main__":
    create_fake_triton()
